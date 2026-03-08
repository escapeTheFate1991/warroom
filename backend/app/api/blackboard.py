"""Shared Blackboard — inter-agent state sharing via PostgreSQL.

Agents post entries (facts, status updates, context) that any other agent can
read.  Entries are namespaced by topic so consumers can subscribe to only what
they care about.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.crm_db import get_crm_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Table setup ──────────────────────────────────────────────────

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS blackboard (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    agent_id TEXT,
    ttl_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(topic, key)
)
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_blackboard_topic ON blackboard(topic)",
    "CREATE INDEX IF NOT EXISTS idx_blackboard_agent ON blackboard(agent_id)",
]

_ensured = False


async def ensure_table(db):
    global _ensured
    if _ensured:
        return
    await db.execute(text(CREATE_TABLE))
    for idx in CREATE_INDEXES:
        await db.execute(text(idx))
    await db.commit()
    _ensured = True


# ── Models ───────────────────────────────────────────────────────

class BlackboardEntry(BaseModel):
    topic: str
    key: str
    value: dict | list | str | int | float | bool
    agent_id: Optional[str] = None
    ttl_seconds: Optional[int] = None


class BlackboardQuery(BaseModel):
    topic: Optional[str] = None
    key: Optional[str] = None
    agent_id: Optional[str] = None
    limit: int = 50


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/blackboard")
async def write_entry(body: BlackboardEntry, db=Depends(get_crm_db)):
    """Write or update a blackboard entry. Upserts on (topic, key)."""
    await ensure_table(db)

    entry_id = str(uuid.uuid4())[:12]
    value_json = json.dumps(body.value) if not isinstance(body.value, str) else json.dumps(body.value)

    await db.execute(text("""
        INSERT INTO blackboard (id, topic, key, value, agent_id, ttl_seconds)
        VALUES (:id, :topic, :key, CAST(:value AS jsonb), :agent_id, :ttl)
        ON CONFLICT (topic, key) DO UPDATE SET
            value = CAST(EXCLUDED.value AS jsonb),
            agent_id = COALESCE(EXCLUDED.agent_id, blackboard.agent_id),
            ttl_seconds = EXCLUDED.ttl_seconds,
            updated_at = NOW()
    """), {
        "id": entry_id,
        "topic": body.topic,
        "key": body.key,
        "value": value_json,
        "agent_id": body.agent_id,
        "ttl": body.ttl_seconds,
    })
    await db.commit()

    return {"id": entry_id, "topic": body.topic, "key": body.key, "written": True}


@router.get("/blackboard")
async def read_entries(
    topic: Optional[str] = None,
    key: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db=Depends(get_crm_db),
):
    """Read blackboard entries with optional filters."""
    await ensure_table(db)

    # Clean expired entries
    await db.execute(text("""
        DELETE FROM blackboard
        WHERE ttl_seconds IS NOT NULL
          AND updated_at + (ttl_seconds || ' seconds')::interval < NOW()
    """))

    clauses = []
    params: dict = {"limit": limit}

    if topic:
        clauses.append("topic = :topic")
        params["topic"] = topic
    if key:
        clauses.append("key = :key")
        params["key"] = key
    if agent_id:
        clauses.append("agent_id = :agent_id")
        params["agent_id"] = agent_id

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM blackboard {where} ORDER BY updated_at DESC LIMIT :limit"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()

    return [dict(r) for r in rows]


@router.get("/blackboard/{topic}/{key}")
async def read_single(topic: str, key: str, db=Depends(get_crm_db)):
    """Read a single blackboard entry by topic + key."""
    await ensure_table(db)

    result = await db.execute(text(
        "SELECT * FROM blackboard WHERE topic = :topic AND key = :key"
    ), {"topic": topic, "key": key})
    row = result.mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")

    return dict(row)


@router.delete("/blackboard/{topic}/{key}")
async def delete_entry(topic: str, key: str, db=Depends(get_crm_db)):
    """Delete a single blackboard entry."""
    await ensure_table(db)

    result = await db.execute(text(
        "DELETE FROM blackboard WHERE topic = :topic AND key = :key RETURNING id"
    ), {"topic": topic, "key": key})
    if not result.first():
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.commit()

    return {"topic": topic, "key": key, "deleted": True}


@router.delete("/blackboard")
async def clear_topic(topic: str = Query(...), db=Depends(get_crm_db)):
    """Delete all entries for a topic."""
    await ensure_table(db)

    result = await db.execute(text(
        "DELETE FROM blackboard WHERE topic = :topic"
    ), {"topic": topic})
    await db.commit()

    return {"topic": topic, "deleted": result.rowcount}
