"""AI Planning — Generate structured task plans from natural language descriptions."""
import json
import logging
import os
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db.leadgen_db import leadgen_engine

logger = logging.getLogger(__name__)
router = APIRouter()

OPENCLAW_API = os.getenv("OPENCLAW_API_URL", "http://10.0.0.1:18789")
AUTH_TOKEN = os.getenv("OPENCLAW_AUTH_TOKEN", "")
KANBAN_API_URL = os.getenv("KANBAN_API_URL", "http://10.0.0.11:18794")

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS public.ai_plans (
    id SERIAL PRIMARY KEY,
    plan_id TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    analysis JSONB,
    tasks JSONB NOT NULL,
    status TEXT DEFAULT 'draft',
    created_task_ids INTEGER[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


async def ensure_table():
    """Create the ai_plans table if it doesn't exist."""
    async with leadgen_engine.begin() as conn:
        await conn.execute(text(TABLE_DDL))


# --- Models ---

class GenerateRequest(BaseModel):
    description: str
    board_context: Optional[str] = None


class ExecuteRequest(BaseModel):
    selected_task_indices: Optional[list[int]] = None


# --- Prompt ---

SYSTEM_PROMPT = """You are a project planning assistant. Given a project description, break it into actionable tasks.

Return ONLY valid JSON (no markdown fences) with this exact structure:
{
  "analysis": {
    "project_type": "string — e.g. 'Web Application', 'DevOps', 'Research'",
    "key_challenges": ["challenge1", "challenge2"],
    "success_metrics": ["metric1", "metric2"]
  },
  "tasks": [
    {
      "title": "Short task title",
      "description": "Detailed description of what to do",
      "priority": "critical|high|medium|low",
      "category": "backend|frontend|devops|design|research|testing|documentation",
      "tags": ["tag1", "tag2"],
      "execution_order": 1,
      "depends_on_title": null,
      "estimated_hours": 2.0
    }
  ]
}

Rules:
- Order tasks by logical execution sequence
- Set depends_on_title to the exact title of a prerequisite task, or null
- Be specific and actionable in descriptions
- Assign realistic hour estimates
- Use priority: critical for blockers, high for core features, medium for important, low for nice-to-have
- Keep task count reasonable (5-20 tasks depending on scope)"""


async def call_ai(description: str, board_context: Optional[str] = None) -> dict:
    """Call OpenClaw gateway to generate a task plan."""
    user_msg = f"Break this project into tasks:\n\n{description}"
    if board_context:
        user_msg += f"\n\nExisting board context:\n{board_context}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OPENCLAW_API}/v1/chat/completions",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            json={
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "stream": False,
            },
            timeout=120.0,
        )

    if resp.status_code != 200:
        logger.error("OpenClaw API error %s: %s", resp.status_code, resp.text[:500])
        raise HTTPException(502, "AI service unavailable")

    data = resp.json()
    # Extract content from OpenAI-compatible response
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Strip markdown fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response: %s\nContent: %s", e, content[:500])
        raise HTTPException(502, "AI returned invalid JSON")


# --- Endpoints ---

@router.post("/ai-planning/generate")
async def generate_plan(req: GenerateRequest):
    """Generate a structured plan from a project description."""
    await ensure_table()

    result = await call_ai(req.description, req.board_context)
    plan_id = str(uuid.uuid4())[:8]

    analysis = result.get("analysis", {})
    tasks = result.get("tasks", [])

    async with leadgen_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO public.ai_plans (plan_id, description, analysis, tasks) "
                "VALUES (:plan_id, :description, :analysis, :tasks)"
            ),
            {
                "plan_id": plan_id,
                "description": req.description,
                "analysis": json.dumps(analysis),
                "tasks": json.dumps(tasks),
            },
        )

    return {"plan_id": plan_id, "tasks": tasks, "analysis": analysis}


@router.get("/ai-planning/plans")
async def list_plans():
    """List all saved plans."""
    await ensure_table()
    async with leadgen_engine.begin() as conn:
        rows = await conn.execute(
            text(
                "SELECT plan_id, description, analysis, tasks, status, created_task_ids, created_at "
                "FROM public.ai_plans ORDER BY created_at DESC"
            )
        )
        plans = []
        for r in rows:
            plans.append({
                "plan_id": r[0],
                "description": r[1],
                "analysis": r[2],
                "tasks": r[3],
                "status": r[4],
                "created_task_ids": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            })
    return {"plans": plans}


@router.get("/ai-planning/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get a specific plan."""
    await ensure_table()
    async with leadgen_engine.begin() as conn:
        row = await conn.execute(
            text("SELECT plan_id, description, analysis, tasks, status, created_task_ids, created_at FROM public.ai_plans WHERE plan_id = :pid"),
            {"pid": plan_id},
        )
        r = row.fetchone()
        if not r:
            raise HTTPException(404, "Plan not found")
        return {
            "plan_id": r[0],
            "description": r[1],
            "analysis": r[2],
            "tasks": r[3],
            "status": r[4],
            "created_task_ids": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
        }


@router.post("/ai-planning/plans/{plan_id}/execute")
async def execute_plan(plan_id: str, req: ExecuteRequest):
    """Create kanban tasks from a plan (or selected subset)."""
    await ensure_table()

    async with leadgen_engine.begin() as conn:
        row = await conn.execute(
            text("SELECT tasks, status FROM public.ai_plans WHERE plan_id = :pid"),
            {"pid": plan_id},
        )
        r = row.fetchone()
        if not r:
            raise HTTPException(404, "Plan not found")

        tasks = r[0] if isinstance(r[0], list) else json.loads(r[0])
        current_status = r[1]

    if current_status == "executed":
        raise HTTPException(400, "Plan already fully executed")

    # Filter to selected indices if provided
    if req.selected_task_indices is not None:
        selected = [tasks[i] for i in req.selected_task_indices if 0 <= i < len(tasks)]
    else:
        selected = tasks

    if not selected:
        raise HTTPException(400, "No tasks selected")

    created_ids: list[int] = []
    errors: list[str] = []

    async with httpx.AsyncClient() as client:
        for task in selected:
            payload = {
                "title": task["title"],
                "description": task.get("description", ""),
                "status": "todo",
                "assignee": "friday",
                "priority": task.get("priority", "medium"),
                "tags": task.get("tags", []),
            }
            try:
                resp = await client.post(f"{KANBAN_API_URL}/tasks", json=payload, timeout=15.0)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    created_ids.append(data.get("id", 0))
                else:
                    errors.append(f"Failed to create '{task['title']}': {resp.status_code}")
            except Exception as e:
                errors.append(f"Error creating '{task['title']}': {str(e)}")

    # Update plan status
    new_status = "executed" if len(selected) == len(tasks) else "partial"
    async with leadgen_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE public.ai_plans SET status = :status, created_task_ids = :ids WHERE plan_id = :pid"
            ),
            {"status": new_status, "ids": created_ids, "pid": plan_id},
        )

    return {"created_task_ids": created_ids, "errors": errors, "status": new_status}


@router.delete("/ai-planning/plans/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete a plan."""
    await ensure_table()
    async with leadgen_engine.begin() as conn:
        result = await conn.execute(
            text("DELETE FROM public.ai_plans WHERE plan_id = :pid"),
            {"pid": plan_id},
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Plan not found")
    return {"deleted": plan_id}
