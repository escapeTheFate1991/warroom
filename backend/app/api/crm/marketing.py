"""CRM Marketing API endpoints."""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.marketing import MarketingCampaign, MarketingEvent
from app.models.crm.audit import AuditLog
from .schemas import (
    MarketingCampaignResponse, MarketingCampaignCreate, MarketingCampaignUpdate,
    MarketingEventResponse, MarketingEventCreate, MarketingEventUpdate
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


# ===== Marketing Campaigns =====

@router.get("/campaigns", response_model=List[MarketingCampaignResponse])
async def list_campaigns(
    status: Optional[bool] = None,
    campaign_type: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List marketing campaigns."""
    query = select(MarketingCampaign)
    
    if status is not None:
        query = query.where(MarketingCampaign.status == status)
    if campaign_type:
        query = query.where(MarketingCampaign.type == campaign_type)
    
    query = query.order_by(MarketingCampaign.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/campaigns/{campaign_id}", response_model=MarketingCampaignResponse)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single marketing campaign."""
    result = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign


@router.post("/campaigns", response_model=MarketingCampaignResponse)
async def create_campaign(campaign_data: MarketingCampaignCreate, user_id: Optional[int] = None,
                         db: AsyncSession = Depends(get_crm_db)):
    """Create a new marketing campaign."""
    campaign = MarketingCampaign(**campaign_data.model_dump(exclude_unset=True))
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    
    # Log audit
    await log_audit(db, "marketing_campaign", campaign.id, "created", user_id, 
                   new_values=campaign_data.model_dump())
    await db.commit()
    
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=MarketingCampaignResponse)
async def update_campaign(campaign_id: int, campaign_data: MarketingCampaignUpdate,
                         user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing marketing campaign."""
    result = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Store old values for audit
    old_values = {
        "name": campaign.name,
        "subject": campaign.subject,
        "status": campaign.status,
        "type": campaign.type,
        "mail_to": campaign.mail_to
    }
    
    # Update fields
    update_data = campaign_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    campaign.updated_at = datetime.now()
    await db.commit()
    await db.refresh(campaign)
    
    # Log audit
    await log_audit(db, "marketing_campaign", campaign.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return campaign


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: int, user_id: Optional[int] = None,
                         db: AsyncSession = Depends(get_crm_db)):
    """Delete a marketing campaign."""
    result = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    old_values = {
        "name": campaign.name,
        "type": campaign.type,
        "status": campaign.status
    }
    
    await db.execute(delete(MarketingCampaign).where(MarketingCampaign.id == campaign_id))
    
    # Log audit
    await log_audit(db, "marketing_campaign", campaign_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "campaign_id": campaign_id}


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: int, user_id: Optional[int] = None,
                       db: AsyncSession = Depends(get_crm_db)):
    """Send/activate a marketing campaign."""
    result = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status:
        raise HTTPException(status_code=400, detail="Campaign is already active/sent")
    
    # Activate the campaign
    campaign.status = True
    campaign.spooling = "sent"
    campaign.updated_at = datetime.now()
    
    await db.commit()
    
    # Log audit
    await log_audit(db, "marketing_campaign", campaign_id, "sent", user_id)
    await db.commit()
    
    # TODO: Implement actual email sending logic here
    logger.info("Campaign %d marked as sent (actual sending not implemented)", campaign_id)
    
    return {"status": "sent", "campaign_id": campaign_id}


# ===== Marketing Events =====

@router.get("/events", response_model=List[MarketingEventResponse])
async def list_events(
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List marketing events."""
    query = (
        select(MarketingEvent)
        .order_by(MarketingEvent.date.desc().nulls_last(), MarketingEvent.name)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/events/{event_id}", response_model=MarketingEventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single marketing event."""
    result = await db.execute(
        select(MarketingEvent).where(MarketingEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event


@router.post("/events", response_model=MarketingEventResponse)
async def create_event(event_data: MarketingEventCreate, user_id: Optional[int] = None,
                      db: AsyncSession = Depends(get_crm_db)):
    """Create a new marketing event."""
    event = MarketingEvent(**event_data.model_dump(exclude_unset=True))
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    # Log audit
    await log_audit(db, "marketing_event", event.id, "created", user_id, 
                   new_values=event_data.model_dump())
    await db.commit()
    
    return event


@router.put("/events/{event_id}", response_model=MarketingEventResponse)
async def update_event(event_id: int, event_data: MarketingEventUpdate,
                      user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing marketing event."""
    result = await db.execute(
        select(MarketingEvent).where(MarketingEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Store old values for audit
    old_values = {
        "name": event.name,
        "description": event.description,
        "date": event.date.isoformat() if event.date else None
    }
    
    # Update fields
    update_data = event_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    await db.commit()
    await db.refresh(event)
    
    # Log audit
    await log_audit(db, "marketing_event", event.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return event


@router.delete("/events/{event_id}")
async def delete_event(event_id: int, user_id: Optional[int] = None,
                      db: AsyncSession = Depends(get_crm_db)):
    """Delete a marketing event."""
    result = await db.execute(
        select(MarketingEvent).where(MarketingEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if event is linked to campaigns
    campaigns_using_event = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.event_id == event_id)
    )
    if campaigns_using_event.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cannot delete event that is linked to campaigns")
    
    old_values = {
        "name": event.name,
        "date": event.date.isoformat() if event.date else None
    }
    
    await db.execute(delete(MarketingEvent).where(MarketingEvent.id == event_id))
    
    # Log audit
    await log_audit(db, "marketing_event", event_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "event_id": event_id}


@router.get("/campaign-types")
async def get_campaign_types():
    """Get available campaign types."""
    return {
        "types": [
            {"value": "newsletter", "label": "Newsletter"},
            {"value": "event", "label": "Event Promotion"},
            {"value": "product", "label": "Product Launch"},
            {"value": "followup", "label": "Follow-up"},
            {"value": "nurture", "label": "Lead Nurture"},
            {"value": "announcement", "label": "Announcement"}
        ]
    }