"""CRM Activities API endpoints."""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_crm_db
from app.models.crm.activity import Activity, ActivityParticipant
from app.models.crm.audit import AuditLog
from .schemas import ActivityResponse, ActivityCreate, ActivityUpdate

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
    
    # Filter by linked entities (would need junction table queries for deal/person)
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
    
    query = query.order_by(Activity.schedule_from.desc().nulls_last(), Activity.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


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
    
    # Add common types if not in use yet
    common_types = ["call", "meeting", "note", "task", "email", "lunch"]
    for activity_type in common_types:
        if activity_type not in types:
            types.append(activity_type)
    
    return {"types": sorted(types)}