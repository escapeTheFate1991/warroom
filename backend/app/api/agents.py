"""Agents — CRUD for permanent AI agents with skill assignment.

Agents are stored in the warroom DB and can be mapped to OpenClaw multi-agent
instances. Each agent has a role, model preference, assigned skills, and
configuration for task dispatch.
"""

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

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


async def ensure_tables(db):
    await db.execute(text(CREATE_TABLE))
    await db.execute(text(CREATE_TASK_ASSIGNMENTS))
    await db.commit()


# ── Models ───────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    emoji: str = "🤖"
    role: str = "generalist"
    description: str = ""
    model: str = "anthropic/claude-sonnet-4-20250514"
    skills: List[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    skills: Optional[List[str]] = None
    config: Optional[dict] = None
    status: Optional[str] = None


class TaskAssignment(BaseModel):
    task_id: str
    priority: int = 0


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
        agent = dict(row)
        # Get active task count
        task_result = await db.execute(text(
            "SELECT COUNT(*) as count FROM agent_task_assignments "
            "WHERE agent_id = :aid AND status IN ('queued', 'running')"
        ), {"aid": agent["id"]})
        agent["active_tasks"] = task_result.scalar() or 0
        agents.append(agent)
    return agents


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, db=Depends(get_crm_db)):
    await ensure_tables(db)
    result = await db.execute(text(
        "SELECT * FROM agents WHERE id = :id"
    ), {"id": agent_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = dict(row)

    # Get task assignments
    tasks = await db.execute(text(
        "SELECT * FROM agent_task_assignments WHERE agent_id = :aid ORDER BY priority DESC, assigned_at ASC"
    ), {"aid": agent_id})
    agent["task_assignments"] = [dict(t) for t in tasks.mappings().all()]

    return agent


@router.post("/agents")
async def create_agent(body: AgentCreate, db=Depends(get_crm_db)):
    await ensure_tables(db)

    agent_id = str(uuid.uuid4())[:8]
    slug = body.name.lower().replace(" ", "-").replace("_", "-")

    await db.execute(text("""
        INSERT INTO agents (id, name, emoji, role, description, model, skills, config)
        VALUES (:id, :name, :emoji, :role, :description, :model, :skills, :config)
    """), {
        "id": agent_id,
        "name": body.name,
        "emoji": body.emoji,
        "role": body.role,
        "description": body.description,
        "model": body.model,
        "skills": json.dumps(body.skills),
        "config": json.dumps(body.config),
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

    for field in ["name", "emoji", "role", "description", "model", "status"]:
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


# ── Task Assignment ──────────────────────────────────────────────

@router.post("/agents/{agent_id}/tasks")
async def assign_task(agent_id: str, body: TaskAssignment, db=Depends(get_crm_db)):
    """Assign a kanban task to an agent with priority."""
    await ensure_tables(db)

    assignment_id = str(uuid.uuid4())[:12]
    await db.execute(text("""
        INSERT INTO agent_task_assignments (id, agent_id, task_id, priority)
        VALUES (:id, :aid, :tid, :priority)
    """), {
        "id": assignment_id,
        "aid": agent_id,
        "tid": body.task_id,
        "priority": body.priority,
    })
    await db.commit()

    return {"assignment_id": assignment_id, "agent_id": agent_id, "task_id": body.task_id}


@router.get("/agents/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str, db=Depends(get_crm_db)):
    """Get all task assignments for an agent."""
    await ensure_tables(db)

    result = await db.execute(text(
        "SELECT * FROM agent_task_assignments WHERE agent_id = :aid ORDER BY priority DESC, assigned_at ASC"
    ), {"aid": agent_id})
    return [dict(r) for r in result.mappings().all()]


@router.put("/agents/{agent_id}/tasks/{assignment_id}")
async def update_task_assignment(agent_id: str, assignment_id: str, body: dict, db=Depends(get_crm_db)):
    """Update task assignment status. Body: { status: "running"|"completed"|"failed" }"""
    await ensure_tables(db)

    status = body.get("status", "queued")
    extra = ""
    params = {"id": assignment_id, "aid": agent_id, "status": status}

    if status == "running":
        extra = ", started_at = NOW()"
    elif status in ("completed", "failed"):
        extra = ", completed_at = NOW()"
        if "result" in body:
            extra += ", result = :result"
            params["result"] = json.dumps(body["result"])

    await db.execute(text(
        f"UPDATE agent_task_assignments SET status = :status{extra} WHERE id = :id AND agent_id = :aid"
    ), params)
    await db.commit()

    return {"assignment_id": assignment_id, "status": status}


@router.delete("/agents/{agent_id}/tasks/{assignment_id}")
async def remove_task_assignment(agent_id: str, assignment_id: str, db=Depends(get_crm_db)):
    await ensure_tables(db)

    await db.execute(text(
        "DELETE FROM agent_task_assignments WHERE id = :id AND agent_id = :aid"
    ), {"id": assignment_id, "aid": agent_id})
    await db.commit()

    return {"deleted": True}
