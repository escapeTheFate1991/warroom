"""CRM Marketing API endpoints."""

from copy import deepcopy
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.agent_contract import load_agent_assignment_map
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.marketing import MarketingCampaign, MarketingEvent
from app.models.crm.audit import AuditLog
from .schemas import (
    MarketingCampaignResponse, MarketingCampaignCreate, MarketingCampaignUpdate,
    MarketingEventResponse, MarketingEventCreate, MarketingEventUpdate
)

logger = logging.getLogger(__name__)
router = APIRouter()

CAMPAIGN_CHANNEL_OPTIONS = [
    {"value": "email", "label": "Email"},
    {"value": "sms", "label": "SMS"},
    {"value": "voice", "label": "Voice"},
    {"value": "social", "label": "Social"},
]

CAMPAIGN_CHANNEL_DEFAULTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "email": {
        "content": {"subject": None, "body": None, "stages": []},
        "channel_config": {"sender_profile": None, "reply_to": None, "track_opens": True},
    },
    "sms": {
        "content": {"message": None, "stages": []},
        "channel_config": {"sender_number": None, "track_clicks": True},
    },
    "voice": {
        "content": {"script": None, "stages": []},
        "channel_config": {"caller_id": None, "voice_profile": None},
    },
    "social": {
        "content": {"posts": [], "stages": []},
        "channel_config": {"platforms": [], "profile_id": None},
    },
}

DEFAULT_CAMPAIGN_SCHEDULE = {"mode": "manual", "stages": []}


def _normalize_channel(channel: Optional[str]) -> str:
    return channel if channel in CAMPAIGN_CHANNEL_DEFAULTS else "email"


def _build_campaign_defaults(channel: str, subject: Optional[str], mail_to: Optional[str]):
    channel_defaults = CAMPAIGN_CHANNEL_DEFAULTS[channel]
    audience = {"segment": mail_to, "recipients": []}
    schedule = deepcopy(DEFAULT_CAMPAIGN_SCHEDULE)
    content = deepcopy(channel_defaults["content"])
    channel_config = deepcopy(channel_defaults["channel_config"])

    if channel == "email":
        content["subject"] = subject

    return audience, schedule, content, channel_config


def _normalize_campaign_payload(campaign_data, existing: Optional[MarketingCampaign] = None) -> Dict[str, Any]:
    data = campaign_data.model_dump(exclude_unset=True)
    channel = _normalize_channel(data.get("channel") or getattr(existing, "channel", None))
    subject = data.get("subject", getattr(existing, "subject", None))
    mail_to = data.get("mail_to", getattr(existing, "mail_to", None))

    audience, schedule, content, channel_config = _build_campaign_defaults(channel, subject, mail_to)
    existing_channel = _normalize_channel(getattr(existing, "channel", None)) if existing else None

    if existing and getattr(existing, "audience", None):
        audience.update(existing.audience)
    if existing and getattr(existing, "schedule", None):
        schedule.update(existing.schedule)
    if existing and existing_channel == channel and getattr(existing, "content", None):
        content.update(existing.content)
    if existing and existing_channel == channel and getattr(existing, "channel_config", None):
        channel_config.update(existing.channel_config)

    if data.get("audience"):
        audience.update(data["audience"])
    if data.get("schedule"):
        schedule.update(data["schedule"])
    if data.get("content"):
        content.update(data["content"])
    if data.get("channel_config"):
        channel_config.update(data["channel_config"])

    if channel == "email" and subject and not content.get("subject"):
        content["subject"] = subject
    if mail_to and not audience.get("segment"):
        audience["segment"] = mail_to

    data["channel"] = channel
    if existing is None or {"channel", "mail_to", "audience"} & set(data.keys()):
        data["audience"] = audience
    if existing is None or {"channel", "schedule"} & set(data.keys()):
        data["schedule"] = schedule
    if existing is None or {"channel", "subject", "content"} & set(data.keys()):
        data["content"] = content
    if existing is None or {"channel", "channel_config"} & set(data.keys()):
        data["channel_config"] = channel_config

    return data


def _serialize_campaign(campaign: MarketingCampaign) -> MarketingCampaignResponse:
    channel = _normalize_channel(getattr(campaign, "channel", None))
    audience, schedule, content, channel_config = _build_campaign_defaults(channel, campaign.subject, campaign.mail_to)

    if getattr(campaign, "audience", None):
        audience.update(campaign.audience)
    if getattr(campaign, "schedule", None):
        schedule.update(campaign.schedule)
    if getattr(campaign, "content", None):
        content.update(campaign.content)
    if getattr(campaign, "channel_config", None):
        channel_config.update(campaign.channel_config)

    if channel == "email" and campaign.subject and not content.get("subject"):
        content["subject"] = campaign.subject
    if campaign.mail_to and not audience.get("segment"):
        audience["segment"] = campaign.mail_to

    return MarketingCampaignResponse.model_validate(
        {
            "id": campaign.id,
            "name": campaign.name,
            "channel": channel,
            "subject": campaign.subject,
            "status": campaign.status,
            "type": campaign.type,
            "use_case": getattr(campaign, "use_case", None),
            "mail_to": campaign.mail_to,
            "spooling": campaign.spooling,
            "audience": audience,
            "schedule": schedule,
            "content": content,
            "channel_config": channel_config,
            "template_id": campaign.template_id,
            "event_id": campaign.event_id,
            "created_at": campaign.created_at,
            "updated_at": campaign.updated_at,
        }
    )


async def _with_campaign_assignments(
    db: AsyncSession,
    campaigns: list[MarketingCampaign],
) -> list[MarketingCampaignResponse]:
    serialized_campaigns = [_serialize_campaign(campaign) for campaign in campaigns]
    assignment_map = await load_agent_assignment_map(
        db,
        entity_type="marketing_campaign",
        entity_ids=[str(campaign.id) for campaign in campaigns],
    )
    return [
        response.model_copy(update={"agent_assignments": assignment_map.get(str(campaign.id), [])})
        for campaign, response in zip(campaigns, serialized_campaigns)
    ]


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
    request: Request,
    status: Optional[bool] = None,
    campaign_type: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_db),
):
    """List marketing campaigns."""
    org_id = get_org_id(request)
    query = select(MarketingCampaign)
    
    if status is not None:
        query = query.where(MarketingCampaign.status == status)
    if campaign_type:
        query = query.where(MarketingCampaign.type == campaign_type)
    if channel:
        query = query.where(MarketingCampaign.channel == _normalize_channel(channel))
    
    query = query.order_by(MarketingCampaign.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return await _with_campaign_assignments(db, result.scalars().all())


@router.get("/campaigns/{campaign_id}", response_model=MarketingCampaignResponse)
async def get_campaign(request: Request, campaign_id: int, db: AsyncSession = Depends(get_tenant_db)):
    """Get single marketing campaign."""
    org_id = get_org_id(request)
    result = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return (await _with_campaign_assignments(db, [campaign]))[0]


@router.post("/campaigns", response_model=MarketingCampaignResponse)
async def create_campaign(request: Request, campaign_data: MarketingCampaignCreate, user_id: Optional[int] = None,
                         db: AsyncSession = Depends(get_tenant_db)):
    """Create a new marketing campaign."""
    org_id = get_org_id(request)
    payload = _normalize_campaign_payload(campaign_data)
    campaign = MarketingCampaign(**payload)
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    
    # Log audit
    await log_audit(db, "marketing_campaign", campaign.id, "created", user_id, 
                   new_values=payload)
    await db.commit()
    
    return (await _with_campaign_assignments(db, [campaign]))[0]


@router.put("/campaigns/{campaign_id}", response_model=MarketingCampaignResponse)
async def update_campaign(request: Request, campaign_id: int, campaign_data: MarketingCampaignUpdate,
                         user_id: Optional[int] = None, db: AsyncSession = Depends(get_tenant_db)):
    """Update an existing marketing campaign."""
    org_id = get_org_id(request)
    result = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Store old values for audit
    old_values = {
        "name": campaign.name,
        "channel": getattr(campaign, "channel", "email"),
        "subject": campaign.subject,
        "status": campaign.status,
        "type": campaign.type,
        "use_case": getattr(campaign, "use_case", None),
        "mail_to": campaign.mail_to,
        "audience": getattr(campaign, "audience", None),
        "schedule": getattr(campaign, "schedule", None),
        "content": getattr(campaign, "content", None),
        "channel_config": getattr(campaign, "channel_config", None),
    }
    
    # Update fields
    update_data = _normalize_campaign_payload(campaign_data, existing=campaign)
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    campaign.updated_at = datetime.now()
    await db.commit()
    await db.refresh(campaign)
    
    # Log audit
    await log_audit(db, "marketing_campaign", campaign.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return (await _with_campaign_assignments(db, [campaign]))[0]


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(request: Request, campaign_id: int, user_id: Optional[int] = None,
                         db: AsyncSession = Depends(get_tenant_db)):
    """Delete a marketing campaign."""
    org_id = get_org_id(request)
    result = await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    old_values = {
        "name": campaign.name,
        "channel": getattr(campaign, "channel", "email"),
        "type": campaign.type,
        "status": campaign.status
    }
    
    await db.execute(delete(MarketingCampaign).where(MarketingCampaign.id == campaign_id))
    
    # Log audit
    await log_audit(db, "marketing_campaign", campaign_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "campaign_id": campaign_id}


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(request: Request, campaign_id: int, user_id: Optional[int] = None,
                       db: AsyncSession = Depends(get_tenant_db)):
    """Send/activate a marketing campaign."""
    org_id = get_org_id(request)
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
    logger.info(
        "Campaign %d marked as sent for channel %s (actual delivery not implemented)",
        campaign_id,
        _normalize_channel(getattr(campaign, "channel", None)),
    )
    
    return {"status": "sent", "campaign_id": campaign_id}


# ===== Marketing Events =====

@router.get("/events", response_model=List[MarketingEventResponse])
async def list_events(
    request: Request,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_db),
):
    """List marketing events."""
    org_id = get_org_id(request)
    query = (
        select(MarketingEvent)
        .order_by(MarketingEvent.date.desc().nulls_last(), MarketingEvent.name)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/events/{event_id}", response_model=MarketingEventResponse)
async def get_event(request: Request, event_id: int, db: AsyncSession = Depends(get_tenant_db)):
    """Get single marketing event."""
    org_id = get_org_id(request)
    result = await db.execute(
        select(MarketingEvent).where(MarketingEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event


@router.post("/events", response_model=MarketingEventResponse)
async def create_event(request: Request, event_data: MarketingEventCreate, user_id: Optional[int] = None,
                      db: AsyncSession = Depends(get_tenant_db)):
    """Create a new marketing event."""
    org_id = get_org_id(request)
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
async def update_event(request: Request, event_id: int, event_data: MarketingEventUpdate,
                      user_id: Optional[int] = None, db: AsyncSession = Depends(get_tenant_db)):
    """Update an existing marketing event."""
    org_id = get_org_id(request)
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
async def delete_event(request: Request, event_id: int, user_id: Optional[int] = None,
                      db: AsyncSession = Depends(get_tenant_db)):
    """Delete a marketing event."""
    org_id = get_org_id(request)
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
    """Get available campaign types and channel options."""
    return {
        "channels": CAMPAIGN_CHANNEL_OPTIONS,
        "types": [
            {"value": "newsletter", "label": "Newsletter"},
            {"value": "event", "label": "Event Promotion"},
            {"value": "product", "label": "Product Launch"},
            {"value": "followup", "label": "Follow-up"},
            {"value": "nurture", "label": "Lead Nurture"},
            {"value": "announcement", "label": "Announcement"}
        ]
    }