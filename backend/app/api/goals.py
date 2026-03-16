"""Goal Hierarchy — cascading goals from company-level down to individual tasks.

Levels: company → campaign → project → task
Status: planned → active → completed → archived
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_LEVELS = {"company", "campaign", "project", "task"}
VALID_STATUSES = {"planned", "active", "completed", "archived"}


# ── Schemas ──────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    level: str = "task"
    status: str = "planned"
    parent_id: Optional[int] = None
    owner_agent_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    target_metric: Optional[str] = None
    target_value: Optional[float] = None
    deadline: Optional[str] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    status: Optional[str] = None
    parent_id: Optional[int] = None
    owner_agent_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    target_metric: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    deadline: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────

@router.get("")
async def list_goals(
    request: Request,
    level: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    parent_id: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List goals with optional level/status/parent filters."""
    org_id = get_org_id(request)

    conditions = ["org_id = :org_id"]
    params: dict = {"org_id": org_id}

    if level:
        if level not in VALID_LEVELS:
            raise HTTPException(status_code=400, detail=f"Invalid level: {level}")
        conditions.append("level = :level")
        params["level"] = level

    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        conditions.append("status = :status")
        params["status"] = status

    if parent_id is not None:
        conditions.append("parent_id = :parent_id")
        params["parent_id"] = parent_id

    where = " AND ".join(conditions)
    offset = (page - 1) * limit

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM crm.goals WHERE {where}"), params
    )
    total = count_result.scalar()

    result = await db.execute(
        text(
            f"SELECT * FROM crm.goals WHERE {where} "
            f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": limit, "offset": offset},
    )
    rows = [dict(r._mapping) for r in result.fetchall()]

    return {
        "status": "success",
        "data": rows,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": max(1, (total + limit - 1) // limit),
        },
    }


@router.get("/tree")
async def goal_tree(
    request: Request,
    root_id: Optional[int] = Query(default=None, description="Root goal ID; omit for all top-level"),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Return goal hierarchy as a tree using recursive CTE."""
    org_id = get_org_id(request)

    if root_id:
        query = """
            WITH RECURSIVE tree AS (
                SELECT *, 0 AS depth FROM crm.goals
                WHERE id = :root_id AND org_id = :org_id
                UNION ALL
                SELECT g.*, t.depth + 1 FROM crm.goals g
                INNER JOIN tree t ON g.parent_id = t.id
                WHERE g.org_id = :org_id
            )
            SELECT * FROM tree ORDER BY depth, created_at
        """
        params = {"root_id": root_id, "org_id": org_id}
    else:
        query = """
            WITH RECURSIVE tree AS (
                SELECT *, 0 AS depth FROM crm.goals
                WHERE parent_id IS NULL AND org_id = :org_id
                UNION ALL
                SELECT g.*, t.depth + 1 FROM crm.goals g
                INNER JOIN tree t ON g.parent_id = t.id
                WHERE g.org_id = :org_id
            )
            SELECT * FROM tree ORDER BY depth, created_at
        """
        params = {"org_id": org_id}

    result = await db.execute(text(query), params)
    rows = [dict(r._mapping) for r in result.fetchall()]

    return {"status": "success", "data": rows}


@router.get("/{goal_id}")
async def get_goal(
    request: Request,
    goal_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a single goal by ID."""
    org_id = get_org_id(request)

    result = await db.execute(
        text("SELECT * FROM crm.goals WHERE id = :id AND org_id = :org_id"),
        {"id": goal_id, "org_id": org_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {"status": "success", "data": dict(row._mapping)}


@router.post("", status_code=201)
async def create_goal(
    request: Request,
    body: GoalCreate,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new goal."""
    org_id = get_org_id(request)

    if body.level not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid level: {body.level}")
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    # Validate parent exists in same org
    if body.parent_id:
        parent = await db.execute(
            text("SELECT id FROM crm.goals WHERE id = :id AND org_id = :org_id"),
            {"id": body.parent_id, "org_id": org_id},
        )
        if not parent.fetchone():
            raise HTTPException(status_code=400, detail="Parent goal not found")

    result = await db.execute(
        text("""
            INSERT INTO crm.goals (
                org_id, title, description, level, status, parent_id,
                owner_agent_id, owner_user_id, target_metric, target_value, deadline
            ) VALUES (
                :org_id, :title, :description, :level, :status, :parent_id,
                :owner_agent_id, :owner_user_id, :target_metric, :target_value,
                :deadline::timestamptz
            )
            RETURNING *
        """),
        {
            "org_id": org_id,
            "title": body.title,
            "description": body.description,
            "level": body.level,
            "status": body.status,
            "parent_id": body.parent_id,
            "owner_agent_id": body.owner_agent_id,
            "owner_user_id": body.owner_user_id,
            "target_metric": body.target_metric,
            "target_value": body.target_value,
            "deadline": body.deadline,
        },
    )
    row = result.fetchone()
    await db.commit()

    return {"status": "success", "data": dict(row._mapping)}


@router.patch("/{goal_id}")
async def update_goal(
    request: Request,
    goal_id: int,
    body: GoalUpdate,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update a goal (partial update)."""
    org_id = get_org_id(request)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "level" in updates and updates["level"] not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid level: {updates['level']}")
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {updates['status']}")

    set_parts = []
    params = {"id": goal_id, "org_id": org_id}

    for key, value in updates.items():
        if key == "deadline":
            set_parts.append(f"{key} = :{key}::timestamptz")
        else:
            set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(
            f"UPDATE crm.goals SET {set_clause} "
            f"WHERE id = :id AND org_id = :org_id RETURNING *"
        ),
        params,
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {"status": "success", "data": dict(row._mapping)}


@router.delete("/{goal_id}")
async def delete_goal(
    request: Request,
    goal_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Delete a goal. Fails if it has children."""
    org_id = get_org_id(request)

    # Check for children
    children = await db.execute(
        text("SELECT COUNT(*) FROM crm.goals WHERE parent_id = :id AND org_id = :org_id"),
        {"id": goal_id, "org_id": org_id},
    )
    if children.scalar() > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete goal with children. Delete or reassign children first.",
        )

    result = await db.execute(
        text("DELETE FROM crm.goals WHERE id = :id AND org_id = :org_id RETURNING id"),
        {"id": goal_id, "org_id": org_id},
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {"status": "success", "message": f"Goal {goal_id} deleted"}
