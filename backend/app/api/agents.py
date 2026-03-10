"""Agents — CRUD for permanent AI agents with skill assignment.

Agents are stored in the warroom DB and can be mapped to OpenClaw multi-agent
instances. Each agent has a role, model preference, assigned skills, and
configuration for task dispatch.
"""

import logging
import json
import uuid
from typing import Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.api.agent_contract import (
    ASSIGNABLE_ENTITY_TYPES,
    ASSIGNMENT_STATUSES,
    AgentAssignmentCreate,
    AgentAssignmentUpdate,
    TASK_ASSIGNMENT_ENTITY_TYPE,
)
from app.db.crm_db import get_crm_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Table setup ──────────────────────────────────────────────────

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    emoji TEXT DEFAULT '🤖',
    role TEXT NOT NULL DEFAULT 'generalist',
    description TEXT DEFAULT '',
    model TEXT DEFAULT 'anthropic/claude-sonnet-4-20250514',
    skills JSONB DEFAULT '[]'::jsonb,
    config JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'idle',
    openclaw_agent_id TEXT,
    soul_md TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_TASK_ASSIGNMENTS = """
CREATE TABLE IF NOT EXISTS agent_task_assignments (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued',
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB DEFAULT '{}'::jsonb
);
"""

CREATE_ASSIGNMENTS = """
CREATE TABLE IF NOT EXISTS agent_assignments (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    title TEXT,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued',
    metadata JSONB DEFAULT '{}'::jsonb,
    result JSONB DEFAULT '{}'::jsonb,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_ASSIGNMENTS_AGENT_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_agent_assignments_agent_id "
    "ON agent_assignments(agent_id)"
)
CREATE_ASSIGNMENTS_ENTITY_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_agent_assignments_entity "
    "ON agent_assignments(entity_type, entity_id)"
)
CREATE_ASSIGNMENTS_STATUS_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_agent_assignments_status "
    "ON agent_assignments(status)"
)

MIGRATE_LEGACY_TASK_ASSIGNMENTS = """
INSERT INTO agent_assignments (
    id,
    agent_id,
    entity_type,
    entity_id,
    priority,
    status,
    assigned_at,
    started_at,
    completed_at,
    result,
    updated_at
)
SELECT
    legacy.id,
    legacy.agent_id,
    'kanban_task',
    legacy.task_id,
    legacy.priority,
    legacy.status,
    legacy.assigned_at,
    legacy.started_at,
    legacy.completed_at,
    COALESCE(legacy.result, '{}'::jsonb),
    NOW()
FROM agent_task_assignments legacy
WHERE NOT EXISTS (
    SELECT 1 FROM agent_assignments current WHERE current.id = legacy.id
);
"""


MIGRATE_SOUL_MD = """
ALTER TABLE agents ADD COLUMN IF NOT EXISTS soul_md TEXT DEFAULT '';
"""


_tables_ready = False


async def ensure_tables(db):
    global _tables_ready
    if _tables_ready:
        return
    try:
        await db.execute(text(CREATE_TABLE))
        await db.execute(text(CREATE_TASK_ASSIGNMENTS))
        await db.execute(text(CREATE_ASSIGNMENTS))
        await db.execute(text(CREATE_ASSIGNMENTS_AGENT_INDEX))
        await db.execute(text(CREATE_ASSIGNMENTS_ENTITY_INDEX))
        await db.execute(text(CREATE_ASSIGNMENTS_STATUS_INDEX))
        await db.execute(text(MIGRATE_LEGACY_TASK_ASSIGNMENTS))
        await db.execute(text(MIGRATE_SOUL_MD))
        await db.commit()
        _tables_ready = True
    except Exception as e:
        logger.warning("ensure_tables failed (will retry next request): %s", e)
        await db.rollback()


def _decode_json(value: Any, fallback: Any):
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


def _normalize_agent_row(row) -> dict[str, Any]:
    agent = dict(row)
    agent["skills"] = _decode_json(agent.get("skills"), [])
    agent["config"] = _decode_json(agent.get("config"), {})
    return agent


def _normalize_assignment_row(row) -> dict[str, Any]:
    assignment = dict(row)
    assignment["metadata"] = _decode_json(assignment.get("metadata"), {})
    assignment["result"] = _decode_json(assignment.get("result"), {})
    return assignment


async def _ensure_agent_exists(db, agent_id: str):
    existing = await db.execute(text("SELECT id FROM agents WHERE id = :id"), {"id": agent_id})
    if not existing.first():
        raise HTTPException(status_code=404, detail="Agent not found")


async def _create_assignment_record(db, agent_id: str, body: AgentAssignmentCreate) -> dict[str, Any]:
    await _ensure_agent_exists(db, agent_id)

    assignment_id = str(uuid.uuid4())[:12]
    result = await db.execute(text("""
        INSERT INTO agent_assignments (
            id, agent_id, entity_type, entity_id, title, priority, status, metadata
        )
        VALUES (
            :id, :agent_id, :entity_type, :entity_id, :title, :priority, :status, :metadata
        )
        RETURNING *
    """), {
        "id": assignment_id,
        "agent_id": agent_id,
        "entity_type": body.entity_type,
        "entity_id": str(body.entity_id),
        "title": body.title,
        "priority": body.priority,
        "status": body.status,
        "metadata": json.dumps(body.metadata),
    })
    await db.commit()

    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create assignment")
    return _normalize_assignment_row(row)


async def _update_assignment_record(
    db,
    agent_id: str,
    assignment_id: str,
    body: AgentAssignmentUpdate,
    entity_type: Optional[str] = None,
) -> dict[str, Any]:
    await _ensure_agent_exists(db, agent_id)

    updates = []
    params = {"id": assignment_id, "agent_id": agent_id}

    if body.title is not None:
        updates.append("title = :title")
        params["title"] = body.title
    if body.priority is not None:
        updates.append("priority = :priority")
        params["priority"] = body.priority
    if body.metadata is not None:
        updates.append("metadata = :metadata")
        params["metadata"] = json.dumps(body.metadata)
    if body.result is not None:
        updates.append("result = :result")
        params["result"] = json.dumps(body.result)
    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status
        if body.status == "running":
            updates.append("started_at = COALESCE(started_at, NOW())")
        elif body.status in {"completed", "failed", "cancelled"}:
            updates.append("completed_at = NOW()")

    if not updates:
        raise HTTPException(status_code=400, detail="No assignment fields to update")

    updates.append("updated_at = NOW()")
    where_clause = "WHERE id = :id AND agent_id = :agent_id"
    if entity_type is not None:
        where_clause += " AND entity_type = :entity_type"
        params["entity_type"] = entity_type

    result = await db.execute(text(
        f"UPDATE agent_assignments SET {', '.join(updates)} {where_clause} RETURNING *"
    ), params)
    await db.commit()

    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return _normalize_assignment_row(row)


async def _delete_assignment_record(
    db,
    agent_id: str,
    assignment_id: str,
    entity_type: Optional[str] = None,
):
    await _ensure_agent_exists(db, agent_id)
    params = {"id": assignment_id, "agent_id": agent_id}
    query = "DELETE FROM agent_assignments WHERE id = :id AND agent_id = :agent_id"
    if entity_type is not None:
        query += " AND entity_type = :entity_type"
        params["entity_type"] = entity_type
    query += " RETURNING id"
    result = await db.execute(text(query), params)
    await db.commit()
    if not result.first():
        raise HTTPException(status_code=404, detail="Assignment not found")


# ── Models ───────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    emoji: str = "🤖"
    role: str = "generalist"
    description: str = ""
    model: str = "anthropic/claude-sonnet-4-20250514"
    skills: List[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    soul_md: str = ""


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    skills: Optional[List[str]] = None
    config: Optional[dict] = None
    status: Optional[str] = None
    soul_md: Optional[str] = None


class TaskAssignment(BaseModel):
    task_id: str
    title: Optional[str] = None
    priority: int = 0
    metadata: dict = Field(default_factory=dict)


# ── CRUD Endpoints ───────────────────────────────────────────────

@router.get("/agents")
async def list_agents(db=Depends(get_crm_db)):
    await ensure_tables(db)
    result = await db.execute(text(
        "SELECT * FROM agents ORDER BY created_at ASC"
    ))
    rows = result.mappings().all()
    agents = []
    for row in rows:
        agent = _normalize_agent_row(row)
        counts_result = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status IN ('queued', 'running')) AS active_assignments,
                COUNT(*) FILTER (
                    WHERE entity_type = :task_entity_type AND status IN ('queued', 'running')
                ) AS active_tasks
            FROM agent_assignments
            WHERE agent_id = :agent_id
        """), {"agent_id": agent["id"], "task_entity_type": TASK_ASSIGNMENT_ENTITY_TYPE})
        counts = counts_result.mappings().first() or {}
        agent["active_assignments"] = counts.get("active_assignments") or 0
        agent["active_tasks"] = counts.get("active_tasks") or 0
        agents.append(agent)
    return agents


@router.get("/agents/assignment-types")
async def list_assignment_types():
    return {
        "entity_types": list(ASSIGNABLE_ENTITY_TYPES),
        "statuses": list(ASSIGNMENT_STATUSES),
    }


@router.get("/agents/assignments")
async def list_assignments(
    agent_id: Optional[str] = None,
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = None,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db=Depends(get_crm_db),
):
    await ensure_tables(db)

    if entity_type is not None and entity_type not in ASSIGNABLE_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported entity_type")
    if status is not None and status not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported assignment status")

    query = """
        SELECT aa.*, a.name AS agent_name, a.emoji AS agent_emoji, a.role AS agent_role
        FROM agent_assignments aa
        JOIN agents a ON a.id = aa.agent_id
        WHERE 1 = 1
    """
    params: dict[str, Any] = {"limit": limit}

    if agent_id:
        query += " AND aa.agent_id = :agent_id"
        params["agent_id"] = agent_id
    if entity_type:
        query += " AND aa.entity_type = :entity_type"
        params["entity_type"] = entity_type
    if entity_id:
        query += " AND aa.entity_id = :entity_id"
        params["entity_id"] = entity_id
    if status:
        query += " AND aa.status = :status"
        params["status"] = status

    query += " ORDER BY aa.priority DESC, aa.assigned_at ASC LIMIT :limit"
    result = await db.execute(text(query), params)
    return [_normalize_assignment_row(row) for row in result.mappings().all()]


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, db=Depends(get_crm_db)):
    await ensure_tables(db)
    result = await db.execute(text(
        "SELECT * FROM agents WHERE id = :id"
    ), {"id": agent_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = _normalize_agent_row(row)

    assignments = await db.execute(text(
        "SELECT * FROM agent_assignments WHERE agent_id = :aid ORDER BY priority DESC, assigned_at ASC"
    ), {"aid": agent_id})
    agent_assignments = [_normalize_assignment_row(t) for t in assignments.mappings().all()]
    agent["assignments"] = agent_assignments
    agent["task_assignments"] = [
        assignment
        for assignment in agent_assignments
        if assignment["entity_type"] == TASK_ASSIGNMENT_ENTITY_TYPE
    ]

    return agent


@router.post("/agents")
async def create_agent(body: AgentCreate, db=Depends(get_crm_db)):
    await ensure_tables(db)

    agent_id = str(uuid.uuid4())[:8]
    slug = body.name.lower().replace(" ", "-").replace("_", "-")

    await db.execute(text("""
        INSERT INTO agents (id, name, emoji, role, description, model, skills, config, soul_md)
        VALUES (:id, :name, :emoji, :role, :description, :model, :skills, :config, :soul_md)
    """), {
        "id": agent_id,
        "name": body.name,
        "emoji": body.emoji,
        "role": body.role,
        "description": body.description,
        "model": body.model,
        "skills": json.dumps(body.skills),
        "config": json.dumps(body.config),
        "soul_md": body.soul_md,
    })
    await db.commit()

    logger.info("Created agent %s (%s) with role=%s, skills=%s", agent_id, body.name, body.role, body.skills)
    return {"id": agent_id, "name": body.name, "slug": slug, "status": "created"}


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentUpdate, db=Depends(get_crm_db)):
    await ensure_tables(db)

    # Check exists
    existing = await db.execute(text("SELECT id FROM agents WHERE id = :id"), {"id": agent_id})
    if not existing.first():
        raise HTTPException(status_code=404, detail="Agent not found")

    updates = []
    params = {"id": agent_id}

    for field in ["name", "emoji", "role", "description", "model", "status", "soul_md"]:
        val = getattr(body, field, None)
        if val is not None:
            updates.append(f"{field} = :{field}")
            params[field] = val

    if body.skills is not None:
        updates.append("skills = :skills")
        params["skills"] = json.dumps(body.skills)

    if body.config is not None:
        updates.append("config = :config")
        params["config"] = json.dumps(body.config)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")
    query = f"UPDATE agents SET {', '.join(updates)} WHERE id = :id"
    await db.execute(text(query), params)
    await db.commit()

    return {"id": agent_id, "updated": True}


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, db=Depends(get_crm_db)):
    await ensure_tables(db)

    result = await db.execute(text("DELETE FROM agents WHERE id = :id RETURNING id"), {"id": agent_id})
    if not result.first():
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.commit()

    logger.info("Deleted agent %s", agent_id)
    return {"id": agent_id, "deleted": True}


# ── Skill Assignment ─────────────────────────────────────────────

@router.post("/agents/{agent_id}/skills")
async def assign_skills(agent_id: str, body: dict, db=Depends(get_crm_db)):
    """Replace all skills for an agent. Body: { skills: ["skill-name-1", ...] }"""
    await ensure_tables(db)

    skills = body.get("skills", [])
    await db.execute(text(
        "UPDATE agents SET skills = :skills, updated_at = NOW() WHERE id = :id"
    ), {"id": agent_id, "skills": json.dumps(skills)})
    await db.commit()

    return {"id": agent_id, "skills": skills}


@router.post("/agents/{agent_id}/assignments")
async def create_assignment(agent_id: str, body: AgentAssignmentCreate, db=Depends(get_crm_db)):
    await ensure_tables(db)
    return await _create_assignment_record(db, agent_id, body)


@router.get("/agents/{agent_id}/assignments")
async def get_agent_assignments(
    agent_id: str,
    entity_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db=Depends(get_crm_db),
):
    await ensure_tables(db)
    await _ensure_agent_exists(db, agent_id)

    if entity_type is not None and entity_type not in ASSIGNABLE_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported entity_type")
    if status is not None and status not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported assignment status")

    query = "SELECT * FROM agent_assignments WHERE agent_id = :aid"
    params: dict[str, Any] = {"aid": agent_id}
    if entity_type:
        query += " AND entity_type = :entity_type"
        params["entity_type"] = entity_type
    if status:
        query += " AND status = :status"
        params["status"] = status
    query += " ORDER BY priority DESC, assigned_at ASC"

    result = await db.execute(text(query), params)
    return [_normalize_assignment_row(r) for r in result.mappings().all()]


@router.put("/agents/{agent_id}/assignments/{assignment_id}")
async def update_assignment(
    agent_id: str,
    assignment_id: str,
    body: AgentAssignmentUpdate,
    db=Depends(get_crm_db),
):
    await ensure_tables(db)
    return await _update_assignment_record(db, agent_id, assignment_id, body)


@router.delete("/agents/{agent_id}/assignments/{assignment_id}")
async def remove_assignment(agent_id: str, assignment_id: str, db=Depends(get_crm_db)):
    await ensure_tables(db)
    await _delete_assignment_record(db, agent_id, assignment_id)
    return {"deleted": True}


# ── Task Assignment ──────────────────────────────────────────────

@router.post("/agents/{agent_id}/tasks")
async def assign_task(agent_id: str, body: TaskAssignment, db=Depends(get_crm_db)):
    """Assign a kanban task to an agent with priority."""
    await ensure_tables(db)

    assignment = await _create_assignment_record(db, agent_id, AgentAssignmentCreate(
        entity_type=TASK_ASSIGNMENT_ENTITY_TYPE,
        entity_id=str(body.task_id),
        title=body.title,
        priority=body.priority,
        metadata=body.metadata,
    ))
    return {
        "assignment_id": assignment["id"],
        "agent_id": agent_id,
        "task_id": body.task_id,
        "entity_type": assignment["entity_type"],
        "status": assignment["status"],
    }


@router.get("/agents/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str, db=Depends(get_crm_db)):
    """Get all task assignments for an agent."""
    await ensure_tables(db)

    result = await db.execute(text(
        "SELECT * FROM agent_assignments WHERE agent_id = :aid AND entity_type = :entity_type "
        "ORDER BY priority DESC, assigned_at ASC"
    ), {"aid": agent_id, "entity_type": TASK_ASSIGNMENT_ENTITY_TYPE})
    return [_normalize_assignment_row(r) for r in result.mappings().all()]


@router.put("/agents/{agent_id}/tasks/{assignment_id}")
async def update_task_assignment(agent_id: str, assignment_id: str, body: dict, db=Depends(get_crm_db)):
    """Update task assignment status. Body: { status: "running"|"completed"|"failed" }"""
    await ensure_tables(db)

    if "status" in body and body["status"] not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported assignment status")

    assignment = await _update_assignment_record(db, agent_id, assignment_id, AgentAssignmentUpdate(
        status=body.get("status"),
        result=body.get("result"),
        title=body.get("title"),
        priority=body.get("priority"),
        metadata=body.get("metadata"),
    ), entity_type=TASK_ASSIGNMENT_ENTITY_TYPE)
    return {"assignment_id": assignment_id, "status": assignment["status"]}


@router.delete("/agents/{agent_id}/tasks/{assignment_id}")
async def remove_task_assignment(agent_id: str, assignment_id: str, db=Depends(get_crm_db)):
    await ensure_tables(db)

    await _delete_assignment_record(db, agent_id, assignment_id, entity_type=TASK_ASSIGNMENT_ENTITY_TYPE)

    return {"deleted": True}


# ── Per-Agent Soul ───────────────────────────────────────────────

class AgentSoulUpdate(BaseModel):
    soul_md: str


@router.get("/agents/{agent_id}/soul")
async def get_agent_soul(agent_id: str, db=Depends(get_crm_db)):
    await ensure_tables(db)
    result = await db.execute(text(
        "SELECT soul_md FROM agents WHERE id = :id"
    ), {"id": agent_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "soul_md": row["soul_md"] or ""}


@router.put("/agents/{agent_id}/soul")
async def update_agent_soul(agent_id: str, body: AgentSoulUpdate, db=Depends(get_crm_db)):
    await ensure_tables(db)
    result = await db.execute(text(
        "UPDATE agents SET soul_md = :soul_md, updated_at = NOW() WHERE id = :id RETURNING id"
    ), {"id": agent_id, "soul_md": body.soul_md})
    await db.commit()
    if not result.first():
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "updated": True}
