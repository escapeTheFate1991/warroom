"""Approval Gates — human-in-the-loop approval for agent actions.

Types: cold_email, cold_call, social_dm, contract, budget
Status: pending → approved | rejected
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_TYPES = {"cold_email", "cold_call", "social_dm", "contract", "budget"}
VALID_STATUSES = {"pending", "approved", "rejected"}


# ── Schemas ──────────────────────────────────────────────────────

class ApprovalCreate(BaseModel):
    type: str
    payload: dict
    requested_by_agent_id: Optional[int] = None
    requested_by_user_id: Optional[int] = None
    entity_id: Optional[int] = None


class ApprovalDecision(BaseModel):
    decision_note: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────

@router.get("")
async def list_approvals(
    request: Request,
    status: Optional[str] = Query(default="pending"),
    type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List approvals, defaulting to pending."""
    org_id = get_org_id(request)

    conditions = ["org_id = :org_id"]
    params: dict = {"org_id": org_id}

    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        conditions.append("status = :status")
        params["status"] = status

    if type:
        if type not in VALID_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid type: {type}")
        conditions.append("type = :type")
        params["type"] = type

    where = " AND ".join(conditions)
    offset = (page - 1) * limit

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM crm.approvals WHERE {where}"), params
    )
    total = count_result.scalar()

    result = await db.execute(
        text(
            f"SELECT * FROM crm.approvals WHERE {where} "
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


@router.get("/{approval_id}")
async def get_approval(
    request: Request,
    approval_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a single approval by ID."""
    org_id = get_org_id(request)

    result = await db.execute(
        text("SELECT * FROM crm.approvals WHERE id = :id AND org_id = :org_id"),
        {"id": approval_id, "org_id": org_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")

    return {"status": "success", "data": dict(row._mapping)}


@router.post("", status_code=201)
async def create_approval(
    request: Request,
    body: ApprovalCreate,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new approval request (typically called by an agent)."""
    org_id = get_org_id(request)

    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {body.type}")

    import json

    result = await db.execute(
        text("""
            INSERT INTO crm.approvals (
                org_id, type, requested_by_agent_id, requested_by_user_id,
                status, payload, entity_id
            ) VALUES (
                :org_id, :type, :requested_by_agent_id, :requested_by_user_id,
                'pending', :payload::jsonb, :entity_id
            )
            RETURNING *
        """),
        {
            "org_id": org_id,
            "type": body.type,
            "requested_by_agent_id": body.requested_by_agent_id,
            "requested_by_user_id": body.requested_by_user_id,
            "payload": json.dumps(body.payload),
            "entity_id": body.entity_id,
        },
    )
    row = result.fetchone()
    await db.commit()

    return {"status": "success", "data": dict(row._mapping)}


@router.patch("/{approval_id}/approve")
async def approve(
    request: Request,
    approval_id: int,
    body: ApprovalDecision = ApprovalDecision(),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Approve an approval request."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)

    result = await db.execute(
        text("""
            UPDATE crm.approvals
            SET status = 'approved',
                decided_by_user_id = :user_id,
                decided_at = NOW(),
                decision_note = :note,
                updated_at = NOW()
            WHERE id = :id AND org_id = :org_id AND status = 'pending'
            RETURNING *
        """),
        {
            "id": approval_id,
            "org_id": org_id,
            "user_id": user_id,
            "note": body.decision_note,
        },
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Approval not found or already decided",
        )

    return {"status": "success", "data": dict(row._mapping)}


@router.patch("/{approval_id}/reject")
async def reject(
    request: Request,
    approval_id: int,
    body: ApprovalDecision = ApprovalDecision(),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Reject an approval request."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)

    result = await db.execute(
        text("""
            UPDATE crm.approvals
            SET status = 'rejected',
                decided_by_user_id = :user_id,
                decided_at = NOW(),
                decision_note = :note,
                updated_at = NOW()
            WHERE id = :id AND org_id = :org_id AND status = 'pending'
            RETURNING *
        """),
        {
            "id": approval_id,
            "org_id": org_id,
            "user_id": user_id,
            "note": body.decision_note,
        },
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Approval not found or already decided",
        )

    return {"status": "success", "data": dict(row._mapping)}
