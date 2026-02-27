"""CRM Audit Log API endpoints."""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.audit import AuditLog
from app.models.crm.user import User
from .schemas import AuditLogResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/audit-log", response_model=List[AuditLogResponse])
async def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """Get filterable audit trail."""
    query = select(AuditLog)
    
    # Apply filters
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    # Date range filtering
    if date_from:
        query = query.where(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))
    
    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/audit-log/stats")
async def get_audit_stats(
    days_back: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_crm_db),
):
    """Get audit log statistics."""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Total actions in period
    total_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= cutoff_date)
    )
    total_actions = total_result.scalar() or 0
    
    # Actions by type
    actions_result = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.created_at >= cutoff_date)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
    )
    actions_by_type = [{"action": row[0], "count": row[1]} for row in actions_result.all()]
    
    # Actions by entity type
    entities_result = await db.execute(
        select(AuditLog.entity_type, func.count(AuditLog.id))
        .where(AuditLog.created_at >= cutoff_date)
        .group_by(AuditLog.entity_type)
        .order_by(func.count(AuditLog.id).desc())
    )
    actions_by_entity = [{"entity_type": row[0], "count": row[1]} for row in entities_result.all()]
    
    # Most active users
    users_result = await db.execute(
        select(AuditLog.user_id, func.count(AuditLog.id))
        .where(and_(AuditLog.created_at >= cutoff_date, AuditLog.user_id.isnot(None)))
        .group_by(AuditLog.user_id)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    
    # Get user names for the active users
    active_users = []
    for user_id, count in users_result.all():
        user_result = await db.execute(select(User.name).where(User.id == user_id))
        user_name = user_result.scalar() or f"User {user_id}"
        active_users.append({"user_id": user_id, "user_name": user_name, "count": count})
    
    # Daily activity for last 7 days
    daily_activity = []
    for i in range(7):
        day_start = (datetime.now() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_result = await db.execute(
            select(func.count(AuditLog.id))
            .where(and_(AuditLog.created_at >= day_start, AuditLog.created_at < day_end))
        )
        count = day_result.scalar() or 0
        daily_activity.append({
            "date": day_start.date().isoformat(),
            "count": count
        })
    
    daily_activity.reverse()  # Show oldest to newest
    
    return {
        "period_days": days_back,
        "total_actions": total_actions,
        "actions_by_type": actions_by_type,
        "actions_by_entity": actions_by_entity,
        "most_active_users": active_users,
        "daily_activity": daily_activity
    }


@router.get("/audit-log/{audit_id}")
async def get_audit_entry(audit_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get detailed audit entry."""
    result = await db.execute(select(AuditLog).where(AuditLog.id == audit_id))
    audit_entry = result.scalar_one_or_none()
    
    if not audit_entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    
    # Get user name if available
    user_name = None
    if audit_entry.user_id:
        user_result = await db.execute(select(User.name).where(User.id == audit_entry.user_id))
        user_name = user_result.scalar()
    
    return {
        "id": audit_entry.id,
        "entity_type": audit_entry.entity_type,
        "entity_id": audit_entry.entity_id,
        "action": audit_entry.action,
        "user_id": audit_entry.user_id,
        "user_name": user_name,
        "old_values": audit_entry.old_values,
        "new_values": audit_entry.new_values,
        "created_at": audit_entry.created_at,
        "changes": _analyze_changes(audit_entry.old_values, audit_entry.new_values)
    }


@router.get("/audit-log/entity/{entity_type}/{entity_id}")
async def get_entity_history(entity_type: str, entity_id: int, 
                            limit: int = Query(default=50, le=200),
                            db: AsyncSession = Depends(get_crm_db)):
    """Get audit history for a specific entity."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    
    entries = result.scalars().all()
    
    # Enhance entries with user names and change analysis
    enhanced_entries = []
    for entry in entries:
        user_name = None
        if entry.user_id:
            user_result = await db.execute(select(User.name).where(User.id == entry.user_id))
            user_name = user_result.scalar()
        
        enhanced_entries.append({
            "id": entry.id,
            "action": entry.action,
            "user_id": entry.user_id,
            "user_name": user_name,
            "created_at": entry.created_at,
            "changes": _analyze_changes(entry.old_values, entry.new_values),
            "old_values": entry.old_values,
            "new_values": entry.new_values
        })
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "history": enhanced_entries
    }


@router.get("/audit-log/actions")
async def get_available_actions(db: AsyncSession = Depends(get_crm_db)):
    """Get list of available audit actions for filtering."""
    result = await db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    )
    actions = [row[0] for row in result.all()]
    return {"actions": actions}


@router.get("/audit-log/entity-types")
async def get_available_entity_types(db: AsyncSession = Depends(get_crm_db)):
    """Get list of available entity types for filtering."""
    result = await db.execute(
        select(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type)
    )
    entity_types = [row[0] for row in result.all()]
    return {"entity_types": entity_types}


def _analyze_changes(old_values: dict, new_values: dict) -> List[dict]:
    """Analyze changes between old and new values."""
    if not old_values and not new_values:
        return []
    
    changes = []
    
    # Handle creation (no old values)
    if not old_values and new_values:
        for field, value in new_values.items():
            changes.append({
                "field": field,
                "change_type": "created",
                "old_value": None,
                "new_value": value
            })
        return changes
    
    # Handle deletion (no new values)
    if old_values and not new_values:
        for field, value in old_values.items():
            changes.append({
                "field": field,
                "change_type": "deleted",
                "old_value": value,
                "new_value": None
            })
        return changes
    
    # Handle updates
    if old_values and new_values:
        all_fields = set(old_values.keys()) | set(new_values.keys())
        
        for field in all_fields:
            old_val = old_values.get(field)
            new_val = new_values.get(field)
            
            if old_val != new_val:
                if field not in old_values:
                    change_type = "added"
                elif field not in new_values:
                    change_type = "removed"
                else:
                    change_type = "modified"
                
                changes.append({
                    "field": field,
                    "change_type": change_type,
                    "old_value": old_val,
                    "new_value": new_val
                })
    
    return changes


@router.delete("/audit-log/cleanup")
async def cleanup_old_audit_logs(
    days_to_keep: int = Query(default=365, ge=30, le=3650),
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Clean up old audit log entries (admin only)."""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Count entries to be deleted
    count_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at < cutoff_date)
    )
    entries_to_delete = count_result.scalar() or 0
    
    if entries_to_delete == 0:
        return {"status": "no_cleanup_needed", "days_to_keep": days_to_keep}
    
    # Delete old entries
    from sqlalchemy import delete
    result = await db.execute(
        delete(AuditLog).where(AuditLog.created_at < cutoff_date)
    )
    
    await db.commit()
    
    # Log the cleanup action
    cleanup_audit = AuditLog(
        entity_type="audit_log",
        entity_id=0,
        action="cleanup",
        user_id=user_id,
        new_values={
            "days_to_keep": days_to_keep,
            "entries_deleted": entries_to_delete,
            "cutoff_date": cutoff_date.isoformat()
        }
    )
    db.add(cleanup_audit)
    await db.commit()
    
    logger.info("Audit log cleanup: deleted %d entries older than %d days", entries_to_delete, days_to_keep)
    
    return {
        "status": "cleanup_completed",
        "days_to_keep": days_to_keep,
        "entries_deleted": entries_to_delete,
        "cutoff_date": cutoff_date.isoformat()
    }