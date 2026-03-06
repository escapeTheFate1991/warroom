"""Task Execution Engine — executes AI-assigned tasks via OpenClaw sub-agents."""
import asyncio
import logging
import os
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db.leadgen_db import leadgen_engine

logger = logging.getLogger(__name__)
router = APIRouter()

KANBAN_API_URL = os.getenv("KANBAN_API_URL", "http://10.0.0.11:18794")
OPENCLAW_API = os.getenv("OPENCLAW_API_URL", "http://10.0.0.1:18789")
AUTH_TOKEN = os.getenv("OPENCLAW_AUTH_TOKEN", "")

# In-memory execution state (one active execution at a time)
_active_execution: Optional[dict] = None
_execution_lock = asyncio.Lock()

_table_ensured = False

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.task_executions (
    id SERIAL PRIMARY KEY,
    execution_id TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'running',
    queue JSONB NOT NULL,
    current_index INTEGER DEFAULT 0,
    results JSONB DEFAULT '[]',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
"""


async def ensure_table():
    """Create the executions table if it doesn't exist (once per process)."""
    global _table_ensured
    if _table_ensured:
        return
    async with leadgen_engine.begin() as conn:
        await conn.execute(text(CREATE_TABLE_SQL))
    _table_ensured = True


# ── Helpers ──────────────────────────────────────────────────────────


async def fetch_all_tasks() -> list[dict]:
    """Fetch all tasks from the kanban API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{KANBAN_API_URL}/tasks")
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("tasks", [])


async def fetch_dependencies() -> list[dict]:
    """Fetch all dependency rows from our own DB."""
    await ensure_table()
    async with leadgen_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT task_id, depends_on FROM public.task_dependencies")
        )
        return [dict(r._mapping) for r in result]


def topological_sort(task_ids: set[int], deps: list[dict]) -> list[int]:
    """Kahn's algorithm — returns task_ids in dependency order."""
    graph: dict[int, list[int]] = defaultdict(list)
    in_degree: dict[int, int] = {tid: 0 for tid in task_ids}

    for dep in deps:
        tid, dep_on = dep["task_id"], dep["depends_on"]
        if tid in task_ids and dep_on in task_ids:
            graph[dep_on].append(tid)
            in_degree[tid] = in_degree.get(tid, 0) + 1

    queue: deque[int] = deque(
        tid for tid, deg in in_degree.items() if deg == 0
    )
    ordered: list[int] = []

    while queue:
        node = queue.popleft()
        ordered.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Append remaining (cycles or orphans)
    for tid in task_ids:
        if tid not in ordered:
            ordered.append(tid)

    return ordered


async def execute_task_via_openclaw(title: str, description: str) -> dict:
    """Send a task to OpenClaw for execution and return the result."""
    prompt = (
        f"Execute this task: {title}\n\n"
        f"Description: {description}\n\n"
        "Complete this task and report back with what was done."
    )
    try:
        headers = {"Content-Type": "application/json"}
        if AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{OPENCLAW_API}/v1/chat/completions",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Extract assistant message from OpenAI-compatible response
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                return {"success": True, "output": content}
            return {"success": True, "output": str(data)}
    except Exception as e:
        logger.error("OpenClaw execution failed for '%s': %s", title, e)
        return {"success": False, "output": f"Error: {e}"}


async def mark_task_done(task_id: int):
    """Update the task status to 'done' on the kanban API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(
                f"{KANBAN_API_URL}/tasks/{task_id}",
                json={"status": "done"},
            )
            resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to mark task %d as done: %s", task_id, e)


async def persist_execution(execution: dict):
    """Upsert execution state to database."""
    await ensure_table()
    async with leadgen_engine.begin() as conn:
        await conn.execute(
            text("""
                INSERT INTO public.task_executions
                    (execution_id, status, queue, current_index, results, started_at, completed_at)
                VALUES
                    (:eid, :status, CAST(:queue AS jsonb), :idx, CAST(:results AS jsonb), :started, :completed)
                ON CONFLICT (execution_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    queue = EXCLUDED.queue,
                    current_index = EXCLUDED.current_index,
                    results = EXCLUDED.results,
                    completed_at = EXCLUDED.completed_at
            """),
            {
                "eid": execution["execution_id"],
                "status": execution["status"],
                "queue": _json_dumps(execution["queue"]),
                "idx": execution["current_index"],
                "results": _json_dumps(execution["results"]),
                "started": execution["started_at"],
                "completed": execution.get("completed_at"),
            },
        )


def _json_dumps(obj) -> str:
    import json
    return json.dumps(obj)


# ── Background runner ────────────────────────────────────────────────


async def run_execution(execution: dict):
    """Background coroutine that executes tasks sequentially."""
    global _active_execution

    queue = execution["queue"]
    results = execution["results"]

    for i, item in enumerate(queue):
        # Check for cancellation
        if execution["status"] == "cancelled":
            for j in range(i, len(queue)):
                queue[j]["status"] = "cancelled"
            break

        execution["current_index"] = i
        item["status"] = "running"
        await persist_execution(execution)

        result = await execute_task_via_openclaw(item["title"], item.get("description", ""))

        if result["success"]:
            item["status"] = "done"
            item["output"] = result["output"]
            results.append({
                "task_id": item["task_id"],
                "status": "done",
                "output": result["output"],
            })
            await mark_task_done(item["task_id"])
        else:
            item["status"] = "failed"
            item["output"] = result["output"]
            results.append({
                "task_id": item["task_id"],
                "status": "failed",
                "output": result["output"],
            })

        execution["results"] = results
        await persist_execution(execution)

    # Finalize
    if execution["status"] != "cancelled":
        failed = any(r["status"] == "failed" for r in results)
        execution["status"] = "failed" if failed and all(
            r["status"] in ("failed", "cancelled") for r in results
        ) else "completed"

    execution["completed_at"] = datetime.now(timezone.utc).isoformat()
    await persist_execution(execution)

    async with _execution_lock:
        _active_execution = None

    logger.info(
        "Execution %s finished: %s (%d tasks)",
        execution["execution_id"],
        execution["status"],
        len(queue),
    )


# ── Schemas ──────────────────────────────────────────────────────────


class StartRequest(BaseModel):
    task_ids: Optional[list[int]] = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/task-execution/start")
async def start_execution(body: StartRequest):
    """Start executing tasks. Returns immediately; execution runs in background."""
    global _active_execution

    async with _execution_lock:
        if _active_execution is not None:
            raise HTTPException(409, "An execution is already running")

    await ensure_table()

    # Gather tasks
    all_tasks = await fetch_all_tasks()
    task_map = {t["id"]: t for t in all_tasks}

    if body.task_ids:
        selected_ids = set(body.task_ids)
        missing = selected_ids - set(task_map.keys())
        if missing:
            raise HTTPException(404, f"Tasks not found: {sorted(missing)}")
    else:
        # All non-done tasks assigned to "friday"
        selected_ids = {
            t["id"]
            for t in all_tasks
            if t.get("assignee", "").lower() == "friday"
            and t.get("status", "") != "done"
        }
        if not selected_ids:
            raise HTTPException(404, "No pending tasks assigned to friday")

    # Sort by dependencies
    deps = await fetch_dependencies()
    ordered_ids = topological_sort(selected_ids, deps)

    # Build queue
    queue = []
    for order, tid in enumerate(ordered_ids):
        task = task_map[tid]
        queue.append({
            "task_id": tid,
            "title": task.get("title", f"Task #{tid}"),
            "description": task.get("description", ""),
            "status": "pending",
            "order": order,
        })

    execution = {
        "execution_id": str(uuid.uuid4()),
        "status": "running",
        "queue": queue,
        "current_index": 0,
        "results": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    await persist_execution(execution)

    async with _execution_lock:
        _active_execution = execution

    # Fire and forget
    asyncio.create_task(run_execution(execution))

    return {
        "execution_id": execution["execution_id"],
        "queue": [
            {"task_id": q["task_id"], "title": q["title"], "status": q["status"], "order": q["order"]}
            for q in queue
        ],
    }


@router.get("/task-execution/status")
async def execution_status():
    """Return current execution status."""
    if _active_execution is None:
        return {
            "active": False,
            "execution_id": None,
            "current_task_index": 0,
            "total_tasks": 0,
            "queue": [],
        }

    ex = _active_execution
    return {
        "active": True,
        "execution_id": ex["execution_id"],
        "current_task_index": ex["current_index"],
        "total_tasks": len(ex["queue"]),
        "queue": [
            {
                "task_id": q["task_id"],
                "title": q["title"],
                "status": q["status"],
                "order": q["order"],
                "output": q.get("output"),
            }
            for q in ex["queue"]
        ],
    }


@router.post("/task-execution/cancel")
async def cancel_execution():
    """Cancel the active execution after the current task finishes."""
    if _active_execution is None:
        raise HTTPException(404, "No active execution to cancel")

    _active_execution["status"] = "cancelled"
    return {"ok": True, "execution_id": _active_execution["execution_id"]}


@router.get("/task-execution/history")
async def execution_history():
    """Return past execution runs."""
    await ensure_table()
    async with leadgen_engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT execution_id, status, queue, current_index, results,
                       started_at, completed_at
                FROM public.task_executions
                ORDER BY started_at DESC
                LIMIT 50
            """)
        )
        rows = []
        for r in result:
            rows.append({
                "execution_id": r.execution_id,
                "status": r.status,
                "queue": r.queue,
                "current_index": r.current_index,
                "results": r.results,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            })
        return {"executions": rows}
