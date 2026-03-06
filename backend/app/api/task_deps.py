"""Task Dependencies API — stores dependency graph in our own PostgreSQL."""
import os
from collections import defaultdict, deque
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db.leadgen_db import leadgen_engine

router = APIRouter()

KANBAN_API_URL = os.getenv("KANBAN_API_URL", "http://10.0.0.11:18794")

_table_ensured = False

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.task_dependencies (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    depends_on INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(task_id, depends_on)
);
"""


async def ensure_table():
    """Create the dependencies table if it doesn't exist (once per process)."""
    global _table_ensured
    if _table_ensured:
        return
    async with leadgen_engine.begin() as conn:
        await conn.execute(text(CREATE_TABLE_SQL))
    _table_ensured = True


async def fetch_all_tasks() -> list[dict]:
    """Fetch all tasks from the kanban API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{KANBAN_API_URL}/tasks")
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("tasks", [])


async def fetch_task(task_id: int) -> Optional[dict]:
    """Fetch a single task from the kanban API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{KANBAN_API_URL}/tasks/{task_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        return None


async def get_all_deps() -> list[dict]:
    """Return all dependency rows."""
    await ensure_table()
    async with leadgen_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, task_id, depends_on FROM public.task_dependencies")
        )
        return [dict(r._mapping) for r in result]


def detect_cycle(all_deps: list[dict], new_task_id: int, new_depends_on: int) -> bool:
    """Return True if adding new_task_id -> new_depends_on would create a cycle."""
    graph: dict[int, set[int]] = defaultdict(set)
    for dep in all_deps:
        graph[dep["task_id"]].add(dep["depends_on"])
    graph[new_task_id].add(new_depends_on)

    # DFS from new_depends_on — if we can reach new_task_id, it's a cycle
    visited: set[int] = set()
    stack = [new_depends_on]
    while stack:
        node = stack.pop()
        if node == new_task_id:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph.get(node, set()))
    return False


# ── Schemas ──────────────────────────────────────────────────────────

class AddDependency(BaseModel):
    depends_on: int


class ValidateDependency(BaseModel):
    task_id: int
    depends_on: int


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/tasks/{task_id}/dependencies")
async def get_dependencies(task_id: int):
    """Return what this task depends on and what it blocks."""
    await ensure_table()
    async with leadgen_engine.connect() as conn:
        depends_on_rows = await conn.execute(
            text("SELECT id, depends_on FROM public.task_dependencies WHERE task_id = :tid"),
            {"tid": task_id},
        )
        depends_on = [{"id": r.id, "task_id": r.depends_on} for r in depends_on_rows]

        blocked_by_rows = await conn.execute(
            text("SELECT id, task_id FROM public.task_dependencies WHERE depends_on = :tid"),
            {"tid": task_id},
        )
        blocks = [{"id": r.id, "task_id": r.task_id} for r in blocked_by_rows]

    return {"depends_on": depends_on, "blocks": blocks}


@router.post("/tasks/{task_id}/dependencies", status_code=201)
async def add_dependency(task_id: int, body: AddDependency):
    """Add a dependency: task_id depends on body.depends_on."""
    if task_id == body.depends_on:
        raise HTTPException(400, "A task cannot depend on itself")

    await ensure_table()
    all_deps = await get_all_deps()

    if detect_cycle(all_deps, task_id, body.depends_on):
        raise HTTPException(400, "Adding this dependency would create a circular chain")

    async with leadgen_engine.connect() as conn:
        try:
            result = await conn.execute(
                text(
                    "INSERT INTO public.task_dependencies (task_id, depends_on) "
                    "VALUES (:tid, :dep) RETURNING id"
                ),
                {"tid": task_id, "dep": body.depends_on},
            )
            await conn.commit()
            row = result.fetchone()
            return {"id": row.id, "task_id": task_id, "depends_on": body.depends_on}
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise HTTPException(409, "Dependency already exists")
            raise


@router.delete("/tasks/{task_id}/dependencies/{dep_id}")
async def remove_dependency(task_id: int, dep_id: int):
    """Remove a dependency by its row id."""
    await ensure_table()
    async with leadgen_engine.connect() as conn:
        result = await conn.execute(
            text(
                "DELETE FROM public.task_dependencies WHERE id = :did AND task_id = :tid RETURNING id"
            ),
            {"did": dep_id, "tid": task_id},
        )
        await conn.commit()
        if not result.fetchone():
            raise HTTPException(404, "Dependency not found")
    return {"ok": True}


@router.get("/tasks/execution-order")
async def execution_order():
    """Return tasks sorted by topological order (Kahn's algorithm)."""
    await ensure_table()

    all_deps = await get_all_deps()
    tasks = await fetch_all_tasks()
    task_map = {t["id"]: t for t in tasks}
    task_ids = set(task_map.keys())

    # Build adjacency and in-degree from deps that reference real tasks
    graph: dict[int, list[int]] = defaultdict(list)
    in_degree: dict[int, int] = {tid: 0 for tid in task_ids}

    for dep in all_deps:
        tid, dep_on = dep["task_id"], dep["depends_on"]
        if tid in task_ids and dep_on in task_ids:
            graph[dep_on].append(tid)
            in_degree[tid] = in_degree.get(tid, 0) + 1

    # Kahn's algorithm
    queue: deque[int] = deque(tid for tid, deg in in_degree.items() if deg == 0)
    ordered: list[dict] = []

    while queue:
        node = queue.popleft()
        if node in task_map:
            ordered.append(task_map[node])
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Append any tasks not covered (orphaned or in cycles)
    seen_ids = {t["id"] for t in ordered}
    for t in tasks:
        if t["id"] not in seen_ids:
            ordered.append(t)

    return {"tasks": ordered}


@router.post("/tasks/validate-dependencies")
async def validate_dependency(body: ValidateDependency):
    """Check if adding a dependency would create a cycle."""
    if body.task_id == body.depends_on:
        return {"valid": False, "reason": "A task cannot depend on itself"}

    await ensure_table()
    all_deps = await get_all_deps()

    if detect_cycle(all_deps, body.task_id, body.depends_on):
        return {"valid": False, "reason": "Would create a circular dependency"}

    return {"valid": True}
