"""CRM Deals API endpoints."""

import json
import logging
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.api.agent_assignment_helpers import load_assignment_summaries


def _first_contact_value(contacts_jsonb) -> str | None:
    """Extract the first value from a JSONB array of contacts [{value: ...}]."""
    if not contacts_jsonb:
        return None
    try:
        items = contacts_jsonb if isinstance(contacts_jsonb, list) else json.loads(contacts_jsonb)
        if items and isinstance(items, list) and len(items) > 0:
            first = items[0]
            if isinstance(first, dict):
                return first.get("value") or first.get("primary") or None
            return str(first)
    except (json.JSONDecodeError, TypeError, IndexError):
        pass
    return None
from app.db.crm_db import get_crm_db
from app.models.crm.deal import Deal, Pipeline, PipelineStage, LeadSource, LeadType
from app.models.crm.contact import Person, Organization
from app.models.crm.activity import Activity, DealActivity
from app.models.crm.audit import AuditLog
from .schemas import (
    DealResponse, DealCreate, DealUpdate, DealStageMove, DealForecast,
    ConvertFromLeadRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()


class DealActivityLinkRequest(BaseModel):
    activity_id: int


DEAL_RELATION_OPTIONS = (
    selectinload(Deal.user),
    selectinload(Deal.person),
    selectinload(Deal.organization),
    selectinload(Deal.source),
    selectinload(Deal.type),
    selectinload(Deal.pipeline),
    selectinload(Deal.stage),
)


def serialize_deal(deal: Deal, agent_assignments=None) -> DealResponse:
    reference_time = deal.updated_at or deal.created_at
    if reference_time is None:
        days_in_stage = 0
    else:
        now = datetime.now(reference_time.tzinfo) if reference_time.tzinfo else datetime.utcnow()
        days_in_stage = max((now - reference_time).days, 0)

    rotten_days = deal.pipeline.rotten_days if deal.pipeline and deal.pipeline.rotten_days is not None else 30
    is_rotten = deal.status is None and days_in_stage > rotten_days

    return DealResponse(
        id=deal.id,
        title=deal.title,
        description=deal.description,
        deal_value=deal.deal_value,
        status=deal.status,
        lost_reason=deal.lost_reason,
        expected_close_date=deal.expected_close_date,
        closed_at=deal.closed_at,
        user_id=deal.user_id,
        person_id=deal.person_id,
        organization_id=deal.organization_id,
        source_id=deal.source_id,
        type_id=deal.type_id,
        pipeline_id=deal.pipeline_id,
        stage_id=deal.stage_id,
        leadgen_lead_id=deal.leadgen_lead_id,
        person_name=deal.person.name if deal.person else None,
        person_phone=_first_contact_value(deal.person.contact_numbers if deal.person else None),
        person_email=_first_contact_value(deal.person.email_addresses if deal.person else None),
        organization_name=deal.organization.name if deal.organization else None,
        source_name=deal.source.name if deal.source else None,
        type_name=deal.type.name if deal.type else None,
        pipeline_name=deal.pipeline.name if deal.pipeline else None,
        stage_name=deal.stage.name if deal.stage else None,
        stage_probability=deal.stage.probability if deal.stage and deal.stage.probability is not None else 0,
        user_name=deal.user.name if deal.user else None,
        agent_assignments=agent_assignments or [],
        days_in_stage=days_in_stage,
        is_rotten=is_rotten,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
    )


async def serialize_deal_list(db: AsyncSession, deals: List[Deal]) -> List[DealResponse]:
    assignment_map = await load_assignment_summaries(
        db,
        entity_type="crm_deal",
        entity_ids=[deal.id for deal in deals],
    )
    return [serialize_deal(deal, assignment_map.get(str(deal.id), [])) for deal in deals]


async def serialize_single_deal(db: AsyncSession, deal: Deal) -> DealResponse:
    assignment_map = await load_assignment_summaries(
        db,
        entity_type="crm_deal",
        entity_ids=[deal.id],
    )
    return serialize_deal(deal, assignment_map.get(str(deal.id), []))


async def load_deal_with_related(db: AsyncSession, deal_id: int) -> Optional[Deal]:
    result = await db.execute(
        select(Deal).options(*DEAL_RELATION_OPTIONS).where(Deal.id == deal_id)
    )
    return result.scalar_one_or_none()


async def log_audit(db: AsyncSession, entity_type: str, entity_id: int, action: str, 
                   user_id: Optional[int] = None, old_values: dict = None, new_values: dict = None):
    """Log audit trail for CRM operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        old_values=old_values,
        new_values=new_values
    )
    db.add(audit_log)


@router.get("/deals", response_model=List[DealResponse])
async def list_deals(
    pipeline_id: Optional[int] = None,
    stage_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,  # "open", "won", "lost"
    search: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List deals with filtering options."""
    query = select(Deal).options(*DEAL_RELATION_OPTIONS)
    
    if pipeline_id:
        query = query.where(Deal.pipeline_id == pipeline_id)
    if stage_id:
        query = query.where(Deal.stage_id == stage_id)
    if user_id:
        query = query.where(Deal.user_id == user_id)
    if status:
        if status == "open":
            query = query.where(Deal.status.is_(None))
        elif status == "won":
            query = query.where(Deal.status == True)
        elif status == "lost":
            query = query.where(Deal.status == False)
    if search:
        query = query.where(Deal.title.ilike(f"%{search}%"))
    
    query = query.order_by(Deal.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    deals = result.scalars().all()
    return await serialize_deal_list(db, deals)


@router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single deal with related data."""
    deal = await load_deal_with_related(db, deal_id)
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return await serialize_single_deal(db, deal)


@router.post("/deals", response_model=DealResponse)
async def create_deal(deal_data: DealCreate, db: AsyncSession = Depends(get_crm_db)):
    """Create a new deal."""
    # If no pipeline/stage specified, use default
    if not deal_data.pipeline_id:
        default_pipeline = await db.execute(
            select(Pipeline).where(Pipeline.is_default == True)
        )
        pipeline = default_pipeline.scalar_one_or_none()
        if pipeline:
            deal_data.pipeline_id = pipeline.id
            
            if not deal_data.stage_id:
                # Get first stage of default pipeline
                first_stage = await db.execute(
                    select(PipelineStage)
                    .where(PipelineStage.pipeline_id == pipeline.id)
                    .order_by(PipelineStage.sort_order)
                )
                stage = first_stage.scalar_one_or_none()
                if stage:
                    deal_data.stage_id = stage.id
    
    deal = Deal(**deal_data.model_dump(exclude_unset=True))
    db.add(deal)
    await db.commit()
    await db.refresh(deal)
    
    # Log audit
    await log_audit(db, "deal", deal.id, "created", deal_data.user_id, new_values=deal_data.model_dump())
    await db.commit()

    # Fire workflow triggers (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    fire_triggers_background(
        entity_type="deal",
        event="created",
        entity_data={
            **deal_data.model_dump(),
            "id": deal.id,
            "deal_value": str(deal.deal_value) if deal.deal_value else None,
            "event": "created",
        },
        entity_id=deal.id,
    )
    
    serialized_deal = await load_deal_with_related(db, deal.id)
    if not serialized_deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return await serialize_single_deal(db, serialized_deal)


@router.put("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(deal_id: int, deal_data: DealUpdate, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing deal."""
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Store old values for audit
    old_values = {
        "title": deal.title,
        "description": deal.description,
        "deal_value": str(deal.deal_value) if deal.deal_value else None,
        "status": deal.status,
        "stage_id": deal.stage_id,
        "pipeline_id": deal.pipeline_id
    }
    
    # Update fields
    update_data = deal_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deal, field, value)
    
    # Handle status changes
    if deal_data.status is not None:
        if deal_data.status:  # Won
            deal.closed_at = datetime.now()
        elif deal_data.status is False:  # Lost
            deal.closed_at = datetime.now()
    
    deal.updated_at = datetime.now()
    await db.commit()
    await db.refresh(deal)
    
    # Log audit
    await log_audit(db, "deal", deal.id, "updated", deal_data.user_id, old_values, update_data)
    await db.commit()

    # Fire workflow triggers (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    trigger_data = {
        **update_data,
        "id": deal.id,
        "deal_value": str(deal.deal_value) if deal.deal_value else None,
        "old_values": old_values,
        "event": "updated",
    }
    fire_triggers_background(
        entity_type="deal",
        event="updated",
        entity_data=trigger_data,
        entity_id=deal.id,
    )
    # Also fire stage_changed if stage was updated
    if "stage_id" in update_data and old_values.get("stage_id") != update_data["stage_id"]:
        fire_triggers_background(
            entity_type="deal",
            event="stage_changed",
            entity_data={
                **trigger_data,
                "old_stage_id": old_values.get("stage_id"),
                "new_stage_id": update_data["stage_id"],
                "event": "stage_changed",
            },
            entity_id=deal.id,
        )
    
    serialized_deal = await load_deal_with_related(db, deal.id)
    if not serialized_deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return await serialize_single_deal(db, serialized_deal)


@router.post("/deals/{deal_id}/activities")
async def link_activity_to_deal(
    deal_id: int,
    payload: DealActivityLinkRequest,
    db: AsyncSession = Depends(get_crm_db),
):
    """Link an existing activity to a deal."""
    deal_result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = deal_result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    activity_result = await db.execute(select(Activity).where(Activity.id == payload.activity_id))
    activity = activity_result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    existing_link = await db.execute(
        select(DealActivity).where(
            DealActivity.deal_id == deal_id,
            DealActivity.activity_id == payload.activity_id,
        )
    )
    if existing_link.scalar_one_or_none():
        return {"status": "already_linked", "deal_id": deal_id, "activity_id": payload.activity_id}

    db.add(DealActivity(deal_id=deal_id, activity_id=payload.activity_id))
    await db.commit()
    return {"status": "linked", "deal_id": deal_id, "activity_id": payload.activity_id}


@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: int, user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Delete a deal."""
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Store values for audit
    old_values = {
        "title": deal.title,
        "deal_value": str(deal.deal_value) if deal.deal_value else None,
        "stage_id": deal.stage_id
    }
    
    await db.execute(delete(Deal).where(Deal.id == deal_id))
    
    # Log audit
    await log_audit(db, "deal", deal_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "deal_id": deal_id}


@router.put("/deals/{deal_id}/stage", response_model=DealResponse)
async def move_deal_stage(deal_id: int, stage_move: DealStageMove, user_id: Optional[int] = None, 
                         db: AsyncSession = Depends(get_crm_db)):
    """Move deal to different stage (for kanban drag)."""
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Verify stage exists and belongs to same pipeline
    stage_result = await db.execute(select(PipelineStage).where(PipelineStage.id == stage_move.stage_id))
    new_stage = stage_result.scalar_one_or_none()
    
    if not new_stage:
        raise HTTPException(status_code=400, detail="Stage not found")
    
    if new_stage.pipeline_id != deal.pipeline_id:
        raise HTTPException(status_code=400, detail="Stage does not belong to deal's pipeline")
    
    old_stage_id = deal.stage_id
    deal.stage_id = stage_move.stage_id
    deal.updated_at = datetime.now()
    
    # Auto-close if moved to won/lost stage
    if new_stage.code in ("won", "lost"):
        deal.status = True if new_stage.code == "won" else False
        deal.closed_at = datetime.now()

    # Sync linked leadgen lead
    if new_stage.code in ("won", "lost"):
        from app.services.lead_deal_sync import sync_lead_from_deal
        await sync_lead_from_deal(db, deal_id, deal.status, lost_reason=deal.lost_reason)

    await db.commit()
    await db.refresh(deal)
    
    # Log audit
    await log_audit(db, "deal", deal.id, "stage_changed", user_id, 
                   {"stage_id": old_stage_id}, {"stage_id": stage_move.stage_id})
    await db.commit()

    # Fire workflow triggers (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    stage_trigger_data = {
        "id": deal.id,
        "title": deal.title,
        "deal_value": str(deal.deal_value) if deal.deal_value else None,
        "pipeline_id": deal.pipeline_id,
        "old_stage_id": old_stage_id,
        "new_stage_id": stage_move.stage_id,
        "stage_id": stage_move.stage_id,
        "status": deal.status,
        "event": "stage_changed",
    }
    fire_triggers_background(
        entity_type="deal",
        event="stage_changed",
        entity_data=stage_trigger_data,
        entity_id=deal.id,
    )
    # Also fire generic "updated" trigger
    fire_triggers_background(
        entity_type="deal",
        event="updated",
        entity_data={**stage_trigger_data, "event": "updated"},
        entity_id=deal.id,
    )
    
    serialized_deal = await load_deal_with_related(db, deal.id)
    if not serialized_deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return await serialize_single_deal(db, serialized_deal)


@router.get("/deals/forecast", response_model=List[DealForecast])
async def get_deals_forecast(pipeline_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Get deal forecast - aggregate deal values by stage with win probability."""
    query = select(
        PipelineStage.id.label("stage_id"),
        PipelineStage.name.label("stage_name"),
        func.count(Deal.id).label("deals_count"),
        func.coalesce(func.sum(Deal.deal_value), 0).label("total_value"),
        PipelineStage.probability
    ).select_from(
        PipelineStage
    ).outerjoin(
        Deal, (Deal.stage_id == PipelineStage.id) & (Deal.status.is_(None))  # Only open deals
    )
    
    if pipeline_id:
        query = query.where(PipelineStage.pipeline_id == pipeline_id)
    else:
        # Use default pipeline if none specified
        default_pipeline = await db.execute(select(Pipeline).where(Pipeline.is_default == True))
        pipeline = default_pipeline.scalar_one_or_none()
        if pipeline:
            query = query.where(PipelineStage.pipeline_id == pipeline.id)
    
    query = query.group_by(PipelineStage.id, PipelineStage.name, PipelineStage.probability)
    query = query.order_by(PipelineStage.sort_order)
    
    result = await db.execute(query)
    forecasts = []
    
    for row in result.all():
        total_value = Decimal(str(row.total_value or 0))
        weighted_value = total_value * Decimal(str(row.probability)) / 100
        
        forecasts.append(DealForecast(
            stage_id=row.stage_id,
            stage_name=row.stage_name,
            deals_count=row.deals_count or 0,
            total_value=total_value,
            weighted_value=weighted_value,
            probability=row.probability
        ))
    
    return forecasts


@router.post("/deals/convert-from-lead", response_model=DealResponse)
async def convert_from_lead(convert_data: ConvertFromLeadRequest,
                           db: AsyncSession = Depends(get_crm_db)):
    """Create deal + org + person from a leadgen lead. Starts the sales pipeline."""
    
    # 1. Create or find organization — include website and full address
    org = Organization(
        name=convert_data.business_name or convert_data.title,
        address={
            "street": convert_data.address or "",
            "city": convert_data.city or "",
            "state": convert_data.state or "",
            "website": convert_data.website or "",
        },
        leadgen_lead_id=convert_data.leadgen_lead_id,
    )
    db.add(org)
    await db.flush()
    
    # 2. Create person if we have contact info
    person = None
    if convert_data.emails or convert_data.phone:
        emails_json = [{"value": e, "label": "work"} for e in (convert_data.emails or [])]
        phones_json = [{"value": convert_data.phone, "label": "work"}] if convert_data.phone else None
        person = Person(
            name=convert_data.business_name or convert_data.title or "Unknown Contact",
            email_addresses=emails_json or [],
            contact_numbers=phones_json,
            organization_id=org.id,
        )
        db.add(person)
        await db.flush()
    
    # 3. Get default pipeline + first stage
    pipeline_result = await db.execute(
        select(Pipeline).where(Pipeline.is_default == True).limit(1)
    )
    pipeline = pipeline_result.scalar_one_or_none()
    if not pipeline:
        pipeline_result = await db.execute(select(Pipeline).limit(1))
        pipeline = pipeline_result.scalar_one_or_none()
    
    stage = None
    if pipeline:
        stage_result = await db.execute(
            select(PipelineStage)
            .where(PipelineStage.pipeline_id == pipeline.id)
            .order_by(PipelineStage.sort_order)
            .limit(1)
        )
        stage = stage_result.scalar_one_or_none()
    
    # 4. Get lead source "Lead Gen"
    source_result = await db.execute(
        select(LeadSource).where(LeadSource.name == "Lead Gen").limit(1)
    )
    source = source_result.scalar_one_or_none()
    
    # 5. Build lead metadata from enrichment data
    lead_metadata = {}
    if convert_data.website:
        lead_metadata["website"] = convert_data.website
    if convert_data.google_place_id:
        lead_metadata["google_place_id"] = convert_data.google_place_id
    if convert_data.google_rating is not None:
        lead_metadata["google_rating"] = convert_data.google_rating
    if convert_data.yelp_url:
        lead_metadata["yelp_url"] = convert_data.yelp_url
    if convert_data.yelp_rating is not None:
        lead_metadata["yelp_rating"] = convert_data.yelp_rating
    if convert_data.audit_lite_flags:
        lead_metadata["audit_lite_flags"] = convert_data.audit_lite_flags
    if convert_data.website_audit_score is not None:
        lead_metadata["website_audit_score"] = convert_data.website_audit_score
    if convert_data.website_audit_grade:
        lead_metadata["website_audit_grade"] = convert_data.website_audit_grade
    if convert_data.website_audit_summary:
        lead_metadata["website_audit_summary"] = convert_data.website_audit_summary
    if convert_data.website_audit_top_fixes:
        lead_metadata["website_audit_top_fixes"] = convert_data.website_audit_top_fixes
    if convert_data.review_pain_points:
        lead_metadata["review_pain_points"] = convert_data.review_pain_points
    if convert_data.review_opportunity_flags:
        lead_metadata["review_opportunity_flags"] = convert_data.review_opportunity_flags
    if convert_data.lead_score is not None:
        lead_metadata["lead_score"] = convert_data.lead_score
    if convert_data.lead_tier:
        lead_metadata["lead_tier"] = convert_data.lead_tier
    if convert_data.business_category:
        lead_metadata["business_category"] = convert_data.business_category
    if convert_data.city:
        lead_metadata["city"] = convert_data.city
    if convert_data.state:
        lead_metadata["state"] = convert_data.state

    # 6. Create the deal with metadata
    deal = Deal(
        title=convert_data.title or convert_data.business_name,
        description=f"Converted from Lead Gen — {convert_data.business_category or 'Business'}",
        person_id=person.id if person else None,
        organization_id=org.id,
        pipeline_id=pipeline.id if pipeline else None,
        stage_id=stage.id if stage else None,
        source_id=source.id if source else None,
        leadgen_lead_id=convert_data.leadgen_lead_id,
        deal_metadata=lead_metadata if lead_metadata else None,
    )
    db.add(deal)
    await db.flush()
    
    # 6. Log audit
    await log_audit(db, "deal", deal.id, "created", None,
                   new_values={"title": deal.title, "source": "leadgen", "leadgen_lead_id": convert_data.leadgen_lead_id})
    
    await db.commit()
    await db.refresh(deal)

    # Fire workflow triggers for new deal
    from app.services.workflow_triggers import fire_triggers_background
    fire_triggers_background(
        "deal", "created",
        {"id": deal.id, "title": deal.title, "source": "leadgen", "leadgen_lead_id": convert_data.leadgen_lead_id},
        entity_id=deal.id,
    )
    
    serialized_deal = await load_deal_with_related(db, deal.id)
    if not serialized_deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return await serialize_single_deal(db, serialized_deal)