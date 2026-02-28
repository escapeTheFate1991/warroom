"""CRM Deals API endpoints."""

import logging
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_crm_db
from app.models.crm.deal import Deal, Pipeline, PipelineStage, LeadSource, LeadType
from app.models.crm.contact import Person, Organization
from app.models.crm.audit import AuditLog
from .schemas import (
    DealResponse, DealCreate, DealUpdate, DealStageMove, DealForecast,
    ConvertFromLeadRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()


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
    query = select(Deal).options(
        selectinload(Deal.person),
        selectinload(Deal.organization),
        selectinload(Deal.pipeline),
        selectinload(Deal.stage)
    )
    
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
    return deals


@router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single deal with related data."""
    query = select(Deal).options(
        selectinload(Deal.person),
        selectinload(Deal.organization),
        selectinload(Deal.pipeline),
        selectinload(Deal.stage),
        selectinload(Deal.source),
        selectinload(Deal.type)
    ).where(Deal.id == deal_id)
    
    result = await db.execute(query)
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return deal


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
    
    return deal


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
    
    return deal


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
    
    await db.commit()
    await db.refresh(deal)
    
    # Log audit
    await log_audit(db, "deal", deal.id, "stage_changed", user_id, 
                   {"stage_id": old_stage_id}, {"stage_id": stage_move.stage_id})
    await db.commit()
    
    return deal


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
    
    # 1. Create or find organization
    org = Organization(
        name=convert_data.business_name or convert_data.title,
        address={"street": convert_data.address or "", "city": convert_data.city or "", "state": convert_data.state or ""},
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
            name=convert_data.assigned_to or "Unknown Contact",
            emails=emails_json or [],
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
    
    # 5. Create the deal
    deal = Deal(
        title=convert_data.title or convert_data.business_name,
        description=f"Converted from Lead Gen — {convert_data.business_category or 'Business'}",
        person_id=person.id if person else None,
        organization_id=org.id,
        pipeline_id=pipeline.id if pipeline else None,
        stage_id=stage.id if stage else None,
        source_id=source.id if source else None,
        leadgen_lead_id=convert_data.leadgen_lead_id,
    )
    db.add(deal)
    await db.flush()
    
    # 6. Log audit
    await log_audit(db, "deal", deal.id, "created", None,
                   new_values={"title": deal.title, "source": "leadgen", "leadgen_lead_id": convert_data.leadgen_lead_id})
    
    await db.commit()
    await db.refresh(deal)
    
    return deal