"""Atomic Task Checkout — prevents double-work by agents.

Provides checkout/release semantics for agent_task_assignments.
An agent must checkout a task before working on it. If already
checked out by another agent, the checkout fails (0 rows returned).
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id

logger = logging.getLogger(__name__)
router = APIRouter()


class CheckoutRequest(BaseModel):
    agent_id: str


class ReleaseRequest(BaseModel):
    agent_id: str
    status: str = "done"  # done | failed | cancelled


@router.post("/{task_id}/checkout")
async def checkout_task(
    request: Request,
    task_id: str,
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Atomically checkout a task for an agent.

    Uses UPDATE...WHERE locked_by_agent_id IS NULL to prevent races.
    Returns 409 if task is already checked out.
    """
    org_id = get_org_id(request)
    run_id = str(uuid.uuid4())

    result = await db.execute(
        text("""
            UPDATE agent_task_assignments
            SET locked_by_agent_id = :agent_id,
                locked_at = NOW(),
                execution_run_id = :run_id,
                status = 'in_progress',
                started_at = COALESCE(started_at, NOW()),
                updated_at = NOW()
            WHERE id = :task_id
              AND org_id = :org_id
              AND locked_by_agent_id IS NULL
            RETURNING *
        """),
        {
            "agent_id": body.agent_id,
            "task_id": task_id,
            "org_id": org_id,
            "run_id": run_id,
        },
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        # Check if task exists at all
        exists = await db.execute(
            text(
                "SELECT id, locked_by_agent_id FROM agent_task_assignments "
                "WHERE id = :task_id AND org_id = :org_id"
            ),
            {"task_id": task_id, "org_id": org_id},
        )
        existing = exists.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(
            status_code=409,
            detail=f"Task already checked out by agent {existing.locked_by_agent_id}",
        )

    return {
        "status": "success",
        "data": dict(row._mapping),
        "execution_run_id": run_id,
    }


@router.post("/{task_id}/release")
async def release_task(
    request: Request,
    task_id: str,
    body: ReleaseRequest,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Release a checked-out task. Only the locking agent can release."""
    org_id = get_org_id(request)

    final_status = body.status if body.status in ("done", "failed", "cancelled") else "done"

    result = await db.execute(
        text("""
            UPDATE agent_task_assignments
            SET locked_by_agent_id = NULL,
                locked_at = NULL,
                status = :final_status,
                completed_at = CASE WHEN :final_status = 'done' THEN NOW() ELSE completed_at END,
                updated_at = NOW()
            WHERE id = :task_id
              AND org_id = :org_id
              AND locked_by_agent_id = :agent_id
            RETURNING *
        """),
        {
            "task_id": task_id,
            "org_id": org_id,
            "agent_id": body.agent_id,
            "final_status": final_status,
        },
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Task not found or not checked out by this agent",
        )

    return {"status": "success", "data": dict(row._mapping)}
