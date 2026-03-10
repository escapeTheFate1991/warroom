"""CRM Activities API endpoints."""

import logging
from datetime import datetime, date, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_crm_db
from app.models.crm.activity import Activity, ActivityParticipant, DealActivity, PersonActivity
from app.models.crm.audit import AuditLog
from app.models.crm.contact import Person
from app.models.crm.deal import Deal
from app.models.crm.email import Email
from .schemas import (
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    CommunicationHistoryItem,
    CommunicationHistoryResponse,
    CommunicationHistoryScope,
    CommunicationHistoryTarget,
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


def parse_leadgen_prospect_id(prospect_id: str) -> int:
    """Resolve a prospects API id into the linked leadgen lead id."""
    normalized = (prospect_id or "").strip()
    source, separator, raw_id = normalized.partition("-")
    if separator != "-" or source not in {"lead", "leadgen"} or not raw_id.isdigit():
        raise ValueError("Prospect communications history is only available for lead-backed prospects like lead-123")
    return int(raw_id)


def compact_history_metadata(values: dict[str, Any]) -> dict[str, Any] | None:
    """Drop empty values from metadata blocks for a cleaner AI contract."""
    compacted = {
        key: value
        for key, value in values.items()
        if value not in (None, "", [], {})
    }
    return compacted or None


def history_item_sort_timestamp(item: CommunicationHistoryItem) -> datetime:
    """Sort history items by the best available timeline timestamp."""
    return item.occurred_at or item.created_at


def serialize_activity_history_item(activity: Activity) -> CommunicationHistoryItem:
    """Convert a CRM activity into the unified communications history contract."""
    additional = activity.additional if isinstance(activity.additional, dict) else {}
    channel = activity.type or "activity"
    content = activity.comment
    if channel == "sms" and isinstance(additional.get("body"), str):
        content = additional["body"]
    elif channel == "call" and isinstance(additional.get("transcript"), str):
        content = additional["transcript"] or activity.comment

    return CommunicationHistoryItem(
        entry_id=f"activity:{activity.id}",
        source="activity",
        channel=channel,
        occurred_at=activity.schedule_from or activity.created_at,
        created_at=activity.created_at,
        title=activity.title,
        content=content,
        linked_person_ids=sorted(
            person.id for person in getattr(activity, "persons", []) if getattr(person, "id", None) is not None
        ),
        linked_deal_ids=sorted(
            deal.id for deal in getattr(activity, "deals", []) if getattr(deal, "id", None) is not None
        ),
        participant_person_ids=sorted(
            participant.id
            for participant in getattr(activity, "participants", [])
            if getattr(participant, "id", None) is not None
        ),
        direction=additional.get("direction") if isinstance(additional.get("direction"), str) else None,
        status=additional.get("status") if isinstance(additional.get("status"), str) else None,
        from_number=additional.get("from_number") if isinstance(additional.get("from_number"), str) else None,
        to_number=additional.get("to_number") if isinstance(additional.get("to_number"), str) else None,
        recording_url=additional.get("recording_url") if isinstance(additional.get("recording_url"), str) else None,
        transcript=additional.get("transcript") if isinstance(additional.get("transcript"), str) else None,
        metadata=compact_history_metadata(
            {
                "type": activity.type,
                "comment": activity.comment,
                "location": activity.location,
                "schedule_to": activity.schedule_to.isoformat() if activity.schedule_to else None,
                "is_done": activity.is_done,
                "user_id": activity.user_id,
                "additional": additional or None,
            }
        ),
    )


def serialize_email_history_item(email: Email) -> CommunicationHistoryItem:
    """Convert a CRM email into the unified communications history contract."""
    attachments = [
        {
            "name": attachment.name,
            "content_type": attachment.content_type,
            "size": attachment.size,
            "filepath": attachment.filepath,
        }
        for attachment in getattr(email, "attachments", [])
    ]
    addresses = compact_history_metadata(
        {
            "from_addr": email.from_addr,
            "sender": email.sender,
            "reply_to": email.reply_to,
            "cc": email.cc,
            "bcc": email.bcc,
        }
    )
    return CommunicationHistoryItem(
        entry_id=f"email:{email.id}",
        source="email",
        channel="email",
        occurred_at=email.created_at,
        created_at=email.created_at,
        title=email.subject,
        content=email.reply,
        linked_person_ids=[email.person_id] if email.person_id is not None else [],
        linked_deal_ids=[email.deal_id] if email.deal_id is not None else [],
        addresses=addresses,
        attachments=attachments,
        metadata=compact_history_metadata(
            {
                "source": email.source,
                "name": email.name,
                "folders": email.folders,
                "message_id": email.message_id,
                "reference_ids": email.reference_ids,
                "parent_id": email.parent_id,
                "is_read": email.is_read,
            }
        ),
    )


async def resolve_communication_scope(
    db: AsyncSession,
    *,
    person_id: int | None = None,
    deal_id: int | None = None,
    prospect_id: str | None = None,
) -> CommunicationHistoryScope:
    """Resolve the exact person/deal scope for unified communications history reads."""
    person_ids: set[int] = set()
    deal_ids: set[int] = set()
    leadgen_lead_id: int | None = None

    if person_id is not None:
        result = await db.execute(select(Person.id).where(Person.id == person_id).limit(1))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Person not found")
        person_ids.add(person_id)
        person_deal_ids = await db.execute(select(Deal.id).where(Deal.person_id == person_id))
        deal_ids.update(person_deal_ids.scalars().all())

    if deal_id is not None:
        result = await db.execute(select(Deal.id, Deal.person_id).where(Deal.id == deal_id).limit(1))
        row = result.first()
        if row is None:
            raise HTTPException(status_code=404, detail="Deal not found")
        deal_ids.add(row.id)
        if row.person_id is not None:
            person_ids.add(row.person_id)

    if prospect_id is not None:
        leadgen_lead_id = parse_leadgen_prospect_id(prospect_id)
        result = await db.execute(select(Deal.id, Deal.person_id).where(Deal.leadgen_lead_id == leadgen_lead_id))
        for row in result.all():
            deal_ids.add(row.id)
            if row.person_id is not None:
                person_ids.add(row.person_id)

    return CommunicationHistoryScope(
        person_ids=sorted(person_ids),
        deal_ids=sorted(deal_ids),
        leadgen_lead_id=leadgen_lead_id,
    )


async def load_history_activities(
    db: AsyncSession,
    scope: CommunicationHistoryScope,
    *,
    limit: int,
) -> list[Activity]:
    """Load activity-backed communication records for the resolved scope."""
    filters = []
    if scope.deal_ids:
        filters.append(
            Activity.id.in_(select(DealActivity.activity_id).where(DealActivity.deal_id.in_(scope.deal_ids)))
        )
    if scope.person_ids:
        filters.append(
            Activity.id.in_(select(PersonActivity.activity_id).where(PersonActivity.person_id.in_(scope.person_ids)))
        )
    if not filters:
        return []

    result = await db.execute(
        select(Activity)
        .options(
            selectinload(Activity.participants),
            selectinload(Activity.persons),
            selectinload(Activity.deals),
        )
        .where(or_(*filters))
        .distinct()
        .order_by(Activity.schedule_from.desc().nulls_last(), Activity.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def load_history_emails(
    db: AsyncSession,
    scope: CommunicationHistoryScope,
    *,
    limit: int,
) -> list[Email]:
    """Load email communication records for the resolved scope."""
    filters = []
    if scope.deal_ids:
        filters.append(Email.deal_id.in_(scope.deal_ids))
    if scope.person_ids:
        filters.append(Email.person_id.in_(scope.person_ids))
    if not filters:
        return []

    result = await db.execute(
        select(Email)
        .options(selectinload(Email.attachments))
        .where(or_(*filters))
        .order_by(Email.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/activities", response_model=List[ActivityResponse])
async def list_activities(
    deal_id: Optional[int] = None,
    person_id: Optional[int] = None,
    activity_type: Optional[str] = None,
    is_done: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user_id: Optional[int] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List activities with filtering options."""
    query = select(Activity).options(selectinload(Activity.participants))

    if deal_id:
        query = query.join(DealActivity, DealActivity.activity_id == Activity.id).where(DealActivity.deal_id == deal_id)
    if person_id:
        query = query.join(PersonActivity, PersonActivity.activity_id == Activity.id).where(PersonActivity.person_id == person_id)
    if user_id:
        query = query.where(Activity.user_id == user_id)
    if activity_type:
        query = query.where(Activity.type == activity_type)
    if is_done is not None:
        query = query.where(Activity.is_done == is_done)
    
    # Date range filtering
    if date_from:
        query = query.where(
            or_(
                Activity.schedule_from >= datetime.combine(date_from, datetime.min.time()),
                Activity.created_at >= datetime.combine(date_from, datetime.min.time())
            )
        )
    if date_to:
        end_of_day = datetime.combine(date_to, datetime.max.time())
        query = query.where(
            or_(
                Activity.schedule_to <= end_of_day,
                and_(
                    Activity.schedule_to.is_(None),
                    Activity.schedule_from <= end_of_day
                ),
                and_(
                    Activity.schedule_from.is_(None),
                    Activity.created_at <= end_of_day
                )
            )
        )
    
    query = query.distinct().order_by(Activity.schedule_from.desc().nulls_last(), Activity.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/activities/upcoming", response_model=List[ActivityResponse])
async def get_upcoming_activities(
    days_ahead: int = Query(default=7, le=30),
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db),
):
    """Get upcoming scheduled activities."""
    now = datetime.now()
    future_date = now + timedelta(days=days_ahead)

    query = select(Activity).where(
        and_(
            Activity.is_done == False,
            Activity.schedule_from >= now,
            Activity.schedule_from <= future_date
        )
    )

    if user_id:
        query = query.where(Activity.user_id == user_id)

    query = query.order_by(Activity.schedule_from)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/activities/overdue", response_model=List[ActivityResponse])
async def get_overdue_activities(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db),
):
    """Get overdue activities (past schedule_to date and not done)."""
    now = datetime.now()

    query = select(Activity).where(
        and_(
            Activity.is_done == False,
            Activity.schedule_to < now
        )
    )

    if user_id:
        query = query.where(Activity.user_id == user_id)

    query = query.order_by(Activity.schedule_to.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/activities/types")
async def get_activity_types(db: AsyncSession = Depends(get_crm_db)):
    """Get list of activity types in use."""
    result = await db.execute(
        select(Activity.type).distinct().where(Activity.type.isnot(None))
    )
    types = [row[0] for row in result.all()]

    common_types = ["call", "meeting", "note", "task", "email", "lunch"]
    for activity_type in common_types:
        if activity_type not in types:
            types.append(activity_type)

    return {"types": sorted(types)}


@router.get("/communications/history", response_model=CommunicationHistoryResponse)
async def get_communications_history(
    person_id: Optional[int] = None,
    deal_id: Optional[int] = None,
    prospect_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_crm_db),
):
    """Return a unified AI-readable communications timeline for a CRM entity."""
    selectors = [person_id is not None, deal_id is not None, prospect_id is not None]
    if sum(selectors) != 1:
        raise HTTPException(status_code=400, detail="Provide exactly one of person_id, deal_id, or prospect_id")

    try:
        scope = await resolve_communication_scope(
            db,
            person_id=person_id,
            deal_id=deal_id,
            prospect_id=prospect_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    activities = await load_history_activities(db, scope, limit=limit)
    emails = await load_history_emails(db, scope, limit=limit)
    items = [serialize_activity_history_item(activity) for activity in activities]
    items.extend(serialize_email_history_item(email) for email in emails)
    items.sort(key=history_item_sort_timestamp, reverse=True)

    return CommunicationHistoryResponse(
        target=CommunicationHistoryTarget(person_id=person_id, deal_id=deal_id, prospect_id=prospect_id),
        resolved_scope=scope,
        items=items[:limit],
    )


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
async def get_activity(activity_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single activity by ID."""
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.participants))
        .where(Activity.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return activity


@router.post("/activities", response_model=ActivityResponse)
async def create_activity(activity_data: ActivityCreate, db: AsyncSession = Depends(get_crm_db)):
    """Create a new activity."""
    activity = Activity(**activity_data.model_dump(exclude_unset=True))
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    
    # Log audit
    await log_audit(db, "activity", activity.id, "created", activity_data.user_id, 
                   new_values=activity_data.model_dump())
    await db.commit()

    # Fire workflow triggers (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    fire_triggers_background(
        entity_type="activity",
        event="created",
        entity_data={
            **activity_data.model_dump(),
            "id": activity.id,
            "event": "created",
        },
        entity_id=activity.id,
    )
    
    return activity


@router.put("/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(activity_id: int, activity_data: ActivityUpdate, 
                         db: AsyncSession = Depends(get_crm_db)):
    """Update an existing activity."""
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Store old values for audit
    old_values = {
        "title": activity.title,
        "type": activity.type,
        "comment": activity.comment,
        "schedule_from": activity.schedule_from.isoformat() if activity.schedule_from else None,
        "schedule_to": activity.schedule_to.isoformat() if activity.schedule_to else None,
        "is_done": activity.is_done
    }
    
    # Update fields
    update_data = activity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)
    
    activity.updated_at = datetime.now()
    await db.commit()
    await db.refresh(activity)
    
    # Log audit
    await log_audit(db, "activity", activity.id, "updated", activity_data.user_id, old_values, update_data)
    await db.commit()

    # Fire workflow triggers (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    fire_triggers_background(
        entity_type="activity",
        event="updated",
        entity_data={
            **update_data,
            "id": activity.id,
            "old_values": old_values,
            "event": "updated",
        },
        entity_id=activity.id,
    )
    
    return activity


@router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: int, user_id: Optional[int] = None, 
                         db: AsyncSession = Depends(get_crm_db)):
    """Delete an activity."""
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    old_values = {
        "title": activity.title,
        "type": activity.type,
        "is_done": activity.is_done
    }
    
    await db.execute(delete(Activity).where(Activity.id == activity_id))
    
    # Log audit
    await log_audit(db, "activity", activity_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "activity_id": activity_id}


@router.put("/activities/{activity_id}/done", response_model=ActivityResponse)
async def mark_activity_done(activity_id: int, user_id: Optional[int] = None, 
                           db: AsyncSession = Depends(get_crm_db)):
    """Mark activity as done."""
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    old_done_status = activity.is_done
    activity.is_done = True
    activity.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(activity)
    
    # Log audit
    await log_audit(db, "activity", activity.id, "marked_done", user_id, 
                   {"is_done": old_done_status}, {"is_done": True})
    await db.commit()
    
    return activity

