"""Budget Caps — per-agent monthly spending limits and cost tracking.

Provides budget check helpers and cost event logging so agents can
verify budget availability before expensive operations.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────

class CostEventCreate(BaseModel):
    task_id: Optional[str] = None
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: int


class BudgetUpdate(BaseModel):
    budget_monthly_cents: Optional[int] = None
    budget_reset_day: Optional[int] = None


# ── Helper — importable by other modules ─────────────────────────

async def check_budget(db: AsyncSession, agent_id: str, org_id: int) -> dict:
    """Check an agent's budget status. Returns budget info + whether spending is allowed.

    Can be imported and called by other modules before expensive operations:

        from app.api.budget import check_budget
        budget = await check_budget(db, agent_id, org_id)
        if not budget["allowed"]:
            raise HTTPException(403, budget["reason"])
    """
    result = await db.execute(
        text("""
            SELECT id, name, budget_monthly_cents, spent_monthly_cents, budget_reset_day
            FROM agents
            WHERE id = :agent_id AND org_id = :org_id
        """),
        {"agent_id": agent_id, "org_id": org_id},
    )
    row = result.fetchone()
    if not row:
        return {"allowed": False, "reason": "Agent not found"}

    row_dict = dict(row._mapping)
    budget = row_dict.get("budget_monthly_cents") or 0
    spent = row_dict.get("spent_monthly_cents") or 0

    # 0 budget = unlimited
    if budget == 0:
        return {
            "allowed": True,
            "budget_monthly_cents": 0,
            "spent_monthly_cents": spent,
            "remaining_cents": None,
            "unlimited": True,
        }

    remaining = budget - spent
    return {
        "allowed": remaining > 0,
        "budget_monthly_cents": budget,
        "spent_monthly_cents": spent,
        "remaining_cents": max(0, remaining),
        "unlimited": False,
        "reason": "Budget exhausted" if remaining <= 0 else None,
    }


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/{agent_id}/budget")
async def get_agent_budget(
    request: Request,
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get an agent's current budget status."""
    org_id = get_org_id(request)
    budget_info = await check_budget(db, agent_id, org_id)

    if budget_info.get("reason") == "Agent not found":
        raise HTTPException(status_code=404, detail="Agent not found")

    # Also fetch recent cost events
    events = await db.execute(
        text("""
            SELECT * FROM crm.agent_cost_events
            WHERE agent_id = :agent_id AND org_id = :org_id
            ORDER BY occurred_at DESC
            LIMIT 20
        """),
        {"agent_id": agent_id, "org_id": org_id},
    )
    recent_events = [dict(r._mapping) for r in events.fetchall()]

    return {
        "status": "success",
        "data": {
            **budget_info,
            "recent_events": recent_events,
        },
    }


@router.patch("/{agent_id}/budget")
async def update_agent_budget(
    request: Request,
    agent_id: str,
    body: BudgetUpdate,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update an agent's budget configuration."""
    org_id = get_org_id(request)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_parts = []
    params = {"agent_id": agent_id, "org_id": org_id}

    for key, value in updates.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(
            f"UPDATE agents SET {set_clause} "
            f"WHERE id = :agent_id AND org_id = :org_id RETURNING id, name, budget_monthly_cents, spent_monthly_cents, budget_reset_day"
        ),
        params,
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"status": "success", "data": dict(row._mapping)}


@router.post("/{agent_id}/cost-event", status_code=201)
async def record_cost_event(
    request: Request,
    agent_id: str,
    body: CostEventCreate,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Record a cost event and update the agent's spent total."""
    org_id = get_org_id(request)

    # Verify agent exists
    agent = await db.execute(
        text("SELECT id FROM agents WHERE id = :agent_id AND org_id = :org_id"),
        {"agent_id": agent_id, "org_id": org_id},
    )
    if not agent.fetchone():
        raise HTTPException(status_code=404, detail="Agent not found")

    # Insert cost event
    event_result = await db.execute(
        text("""
            INSERT INTO crm.agent_cost_events (
                org_id, agent_id, task_id, provider, model,
                input_tokens, output_tokens, cost_cents
            ) VALUES (
                :org_id, :agent_id, :task_id, :provider, :model,
                :input_tokens, :output_tokens, :cost_cents
            )
            RETURNING *
        """),
        {
            "org_id": org_id,
            "agent_id": agent_id,
            "task_id": body.task_id,
            "provider": body.provider,
            "model": body.model,
            "input_tokens": body.input_tokens,
            "output_tokens": body.output_tokens,
            "cost_cents": body.cost_cents,
        },
    )
    event_row = event_result.fetchone()

    # Update agent's spent total
    await db.execute(
        text("""
            UPDATE agents
            SET spent_monthly_cents = COALESCE(spent_monthly_cents, 0) + :cost_cents,
                updated_at = NOW()
            WHERE id = :agent_id AND org_id = :org_id
        """),
        {"agent_id": agent_id, "org_id": org_id, "cost_cents": body.cost_cents},
    )
    await db.commit()

    return {"status": "success", "data": dict(event_row._mapping)}
