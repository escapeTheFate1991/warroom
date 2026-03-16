"""Unified Entity Model — single table for leads, prospects, deals, clients.

Replaces fragmented lead/contact/deal tables with a unified `crm.entities`
table that uses stage progression: lead → prospect → qualified → deal → client → churned.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_STAGES = {"lead", "prospect", "qualified", "deal", "client", "churned"}
VALID_DEAL_STATUSES = {"open", "won", "lost"}


# ── Pydantic schemas ────────────────────────────────────────────

class EntityCreate(BaseModel):
    stage: str = "lead"
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    business_category: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    deal_value: Optional[float] = None
    deal_status: Optional[str] = None
    expected_close_date: Optional[str] = None
    pipeline_stage_id: Optional[int] = None
    lead_source: Optional[str] = None
    lead_score: Optional[int] = None
    lead_tier: Optional[str] = None
    google_place_id: Optional[str] = None
    tags: Optional[list] = Field(default_factory=list)
    metadata: Optional[dict] = Field(default_factory=dict)
    assigned_user_id: Optional[int] = None
    assigned_agent_id: Optional[int] = None
    goal_id: Optional[int] = None


class EntityUpdate(BaseModel):
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    business_category: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    deal_value: Optional[float] = None
    deal_status: Optional[str] = None
    lost_reason: Optional[str] = None
    expected_close_date: Optional[str] = None
    pipeline_stage_id: Optional[int] = None
    lead_source: Optional[str] = None
    lead_score: Optional[int] = None
    lead_tier: Optional[str] = None
    outreach_status: Optional[str] = None
    contacted_by: Optional[str] = None
    contact_outcome: Optional[str] = None
    contact_notes: Optional[str] = None
    tags: Optional[list] = None
    metadata: Optional[dict] = None
    assigned_user_id: Optional[int] = None
    assigned_agent_id: Optional[int] = None
    goal_id: Optional[int] = None


class StageAdvance(BaseModel):
    stage: str


# ── Endpoints ────────────────────────────────────────────────────

@router.get("")
async def list_entities(
    request: Request,
    stage: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List entities with optional stage/search/sort filters."""
    org_id = get_org_id(request)

    conditions = ["org_id = :org_id"]
    params: dict = {"org_id": org_id}

    if stage:
        if stage not in VALID_STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")
        conditions.append("stage = :stage")
        params["stage"] = stage

    if search:
        conditions.append(
            "(business_name ILIKE :search OR contact_name ILIKE :search OR email ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    # Whitelist sortable columns
    allowed_sorts = {
        "created_at", "updated_at", "stage_changed_at",
        "business_name", "contact_name", "email", "deal_value", "lead_score",
    }
    if sort not in allowed_sorts:
        sort = "created_at"
    if order.lower() not in ("asc", "desc"):
        order = "desc"

    where = " AND ".join(conditions)
    offset = (page - 1) * limit

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM crm.entities WHERE {where}"),
        params,
    )
    total = count_result.scalar()

    result = await db.execute(
        text(
            f"SELECT * FROM crm.entities WHERE {where} "
            f"ORDER BY {sort} {order} NULLS LAST "
            f"LIMIT :limit OFFSET :offset"
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


@router.get("/{entity_id}")
async def get_entity(
    request: Request,
    entity_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a single entity by ID."""
    org_id = get_org_id(request)

    result = await db.execute(
        text("SELECT * FROM crm.entities WHERE id = :id AND org_id = :org_id"),
        {"id": entity_id, "org_id": org_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {"status": "success", "data": dict(row._mapping)}


@router.post("", status_code=201)
async def create_entity(
    request: Request,
    body: EntityCreate,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new entity."""
    org_id = get_org_id(request)

    if body.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {body.stage}")
    if body.deal_status and body.deal_status not in VALID_DEAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid deal_status: {body.deal_status}")

    import json

    result = await db.execute(
        text("""
            INSERT INTO crm.entities (
                org_id, stage, stage_changed_at,
                business_name, contact_name, email, phone, website,
                business_category, address, city, state, zip,
                deal_value, deal_status, expected_close_date, pipeline_stage_id,
                lead_source, lead_score, lead_tier, google_place_id,
                tags, metadata, assigned_user_id, assigned_agent_id, goal_id
            ) VALUES (
                :org_id, :stage, NOW(),
                :business_name, :contact_name, :email, :phone, :website,
                :business_category, :address, :city, :state, :zip,
                :deal_value, :deal_status, :expected_close_date, :pipeline_stage_id,
                :lead_source, :lead_score, :lead_tier, :google_place_id,
                :tags::jsonb, :metadata::jsonb, :assigned_user_id, :assigned_agent_id, :goal_id
            )
            RETURNING *
        """),
        {
            "org_id": org_id,
            "stage": body.stage,
            "business_name": body.business_name,
            "contact_name": body.contact_name,
            "email": body.email,
            "phone": body.phone,
            "website": body.website,
            "business_category": body.business_category,
            "address": body.address,
            "city": body.city,
            "state": body.state,
            "zip": body.zip,
            "deal_value": body.deal_value,
            "deal_status": body.deal_status,
            "expected_close_date": body.expected_close_date,
            "pipeline_stage_id": body.pipeline_stage_id,
            "lead_source": body.lead_source,
            "lead_score": body.lead_score,
            "lead_tier": body.lead_tier,
            "google_place_id": body.google_place_id,
            "tags": json.dumps(body.tags),
            "metadata": json.dumps(body.metadata),
            "assigned_user_id": body.assigned_user_id,
            "assigned_agent_id": body.assigned_agent_id,
            "goal_id": body.goal_id,
        },
    )
    row = result.fetchone()
    await db.commit()

    return {"status": "success", "data": dict(row._mapping)}


@router.patch("/{entity_id}")
async def update_entity(
    request: Request,
    entity_id: int,
    body: EntityUpdate,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update an entity (partial update)."""
    org_id = get_org_id(request)

    if body.deal_status and body.deal_status not in VALID_DEAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid deal_status: {body.deal_status}")

    # Build dynamic SET clause from non-None fields
    import json

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Handle JSONB fields
    set_parts = []
    params = {"id": entity_id, "org_id": org_id}

    for key, value in updates.items():
        if key in ("tags", "metadata"):
            set_parts.append(f"{key} = :{key}::jsonb")
            params[key] = json.dumps(value)
        else:
            set_parts.append(f"{key} = :{key}")
            params[key] = value

    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(
            f"UPDATE crm.entities SET {set_clause} "
            f"WHERE id = :id AND org_id = :org_id RETURNING *"
        ),
        params,
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {"status": "success", "data": dict(row._mapping)}


@router.patch("/{entity_id}/stage")
async def advance_stage(
    request: Request,
    entity_id: int,
    body: StageAdvance,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Advance entity stage. Auto-sets stage_changed_at and deal timestamps."""
    org_id = get_org_id(request)

    if body.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {body.stage}")

    extra_sets = ""
    if body.stage == "deal":
        extra_sets = ", deal_status = COALESCE(deal_status, 'open')"
    elif body.stage == "client":
        extra_sets = ", deal_status = 'won', closed_at = NOW()"
    elif body.stage == "churned":
        extra_sets = ", deal_status = 'lost', closed_at = COALESCE(closed_at, NOW())"

    result = await db.execute(
        text(
            f"UPDATE crm.entities "
            f"SET stage = :stage, stage_changed_at = NOW(), updated_at = NOW(){extra_sets} "
            f"WHERE id = :id AND org_id = :org_id RETURNING *"
        ),
        {"stage": body.stage, "id": entity_id, "org_id": org_id},
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {"status": "success", "data": dict(row._mapping)}


@router.delete("/{entity_id}")
async def delete_entity(
    request: Request,
    entity_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Soft-delete not implemented — hard deletes the entity."""
    org_id = get_org_id(request)

    result = await db.execute(
        text(
            "DELETE FROM crm.entities WHERE id = :id AND org_id = :org_id RETURNING id"
        ),
        {"id": entity_id, "org_id": org_id},
    )
    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {"status": "success", "message": f"Entity {entity_id} deleted"}
