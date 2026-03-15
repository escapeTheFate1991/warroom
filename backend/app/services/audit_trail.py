"""Audit Trail Service - Platform-wide activity logging."""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta

from fastapi import Request
from sqlalchemy import text, select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = logging.getLogger(__name__)


async def init_audit_trail_table(engine: AsyncEngine) -> bool:
    """Initialize the audit trail table."""
    try:
        async with engine.begin() as conn:
            # Read and execute the migration SQL
            import os
            migration_path = os.path.join(os.path.dirname(__file__), "../db/audit_trail_migration.sql")
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(migration_sql)
            logger.info("Audit trail table initialized successfully")
            return True
    except Exception as e:
        logger.error("Failed to initialize audit trail table: %s", e)
        return False


async def log_action(
    db: AsyncSession,
    org_id: int,
    actor_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    target_user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    actor_email: Optional[str] = None
) -> bool:
    """
    Log an action to the audit trail.
    
    Fire-and-forget pattern: logs errors but never blocks the calling code.
    
    Args:
        db: Database session
        org_id: Organization ID for tenant isolation
        actor_id: ID of the user performing the action
        action: Action type (e.g., 'view', 'create', 'update', 'delete', 'export', 'login')
        resource_type: Type of resource affected (e.g., 'deal', 'contact', 'setting', 'user', 'agent')
        resource_id: ID of the affected resource (optional)
        target_user_id: ID of user affected by admin actions (optional)
        details: Additional action-specific metadata (optional)
        request: FastAPI request for extracting IP/user-agent (optional)
        actor_email: Actor's email for denormalized display (optional)
    
    Returns:
        bool: True if logged successfully, False if failed (but error is logged, not raised)
    """
    try:
        # Extract request metadata
        ip_address = None
        user_agent = None
        if request:
            # Get real IP from X-Forwarded-For or X-Real-IP headers (reverse proxy)
            ip_address = request.headers.get("x-forwarded-for")
            if ip_address:
                ip_address = ip_address.split(",")[0].strip()  # Take first IP if multiple
            else:
                ip_address = request.headers.get("x-real-ip") or str(request.client.host)
            
            user_agent = request.headers.get("user-agent")
        
        # Ensure details is JSON-serializable
        if details is None:
            details = {}
        
        # Convert any non-serializable objects to strings
        sanitized_details = _sanitize_details(details)
        
        # Insert audit record
        insert_sql = text("""
            INSERT INTO public.audit_trail 
            (org_id, actor_id, actor_email, action, resource_type, resource_id, 
             target_user_id, details, ip_address, user_agent, created_at)
            VALUES (:org_id, :actor_id, :actor_email, :action, :resource_type, :resource_id,
                    :target_user_id, CAST(:details AS jsonb), :ip_address, :user_agent, NOW())
        """)
        
        await db.execute(insert_sql, {
            "org_id": org_id,
            "actor_id": actor_id,
            "actor_email": actor_email,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "target_user_id": target_user_id,
            "details": json.dumps(sanitized_details),
            "ip_address": ip_address,
            "user_agent": user_agent
        })
        
        await db.commit()
        
        logger.debug(
            "Audit logged: org=%d actor=%d action=%s resource=%s/%s",
            org_id, actor_id, action, resource_type, resource_id or "N/A"
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to log audit action [org=%d actor=%d action=%s resource=%s]: %s",
            org_id, actor_id, action, resource_type, e
        )
        # Don't re-raise - this is fire-and-forget
        try:
            await db.rollback()
        except Exception:
            pass  # Best effort rollback
        return False


async def get_audit_log(
    db: AsyncSession,
    org_id: int,
    page: int = 1,
    limit: int = 50,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    actor_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Query audit log with filters and pagination.
    
    Returns:
        Dict with 'total', 'page', 'limit', 'entries' keys
    """
    try:
        # Build base query with tenant isolation
        base_query = text("""
            SELECT * FROM public.audit_trail 
            WHERE org_id = :org_id
        """)
        
        count_query = text("""
            SELECT COUNT(*) FROM public.audit_trail 
            WHERE org_id = :org_id
        """)
        
        # Build dynamic WHERE conditions
        where_conditions = []
        params = {"org_id": org_id}
        
        if action:
            where_conditions.append("action = :action")
            params["action"] = action
        
        if resource_type:
            where_conditions.append("resource_type = :resource_type")
            params["resource_type"] = resource_type
        
        if actor_id:
            where_conditions.append("actor_id = :actor_id")
            params["actor_id"] = actor_id
        
        if date_from:
            where_conditions.append("created_at >= :date_from")
            params["date_from"] = datetime.combine(date_from, datetime.min.time())
        
        if date_to:
            where_conditions.append("created_at <= :date_to")
            params["date_to"] = datetime.combine(date_to, datetime.max.time())
        
        # Add conditions to queries
        if where_conditions:
            additional_where = " AND " + " AND ".join(where_conditions)
            base_query = text(str(base_query) + additional_where)
            count_query = text(str(count_query) + additional_where)
        
        # Add ordering and pagination
        base_query = text(str(base_query) + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
        params["limit"] = limit
        params["offset"] = (page - 1) * limit
        
        # Execute queries
        result = await db.execute(base_query, params)
        entries = [dict(row._mapping) for row in result.fetchall()]
        
        count_result = await db.execute(count_query, {k: v for k, v in params.items() if k != "limit" and k != "offset"})
        total = count_result.scalar()
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "entries": entries
        }
        
    except Exception as e:
        logger.error("Failed to query audit log: %s", e)
        return {
            "total": 0,
            "page": page,
            "limit": limit,
            "entries": []
        }


async def get_audit_summary(
    db: AsyncSession,
    org_id: int,
    days_back: int = 30
) -> Dict[str, Any]:
    """Get aggregated audit statistics."""
    try:
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total actions in period
        total_query = text("""
            SELECT COUNT(*) FROM public.audit_trail 
            WHERE org_id = :org_id AND created_at >= :cutoff_date
        """)
        
        total_result = await db.execute(total_query, {
            "org_id": org_id,
            "cutoff_date": cutoff_date
        })
        total_actions = total_result.scalar() or 0
        
        # Top actions
        actions_query = text("""
            SELECT action, COUNT(*) as count
            FROM public.audit_trail 
            WHERE org_id = :org_id AND created_at >= :cutoff_date
            GROUP BY action
            ORDER BY count DESC
            LIMIT 10
        """)
        
        actions_result = await db.execute(actions_query, {
            "org_id": org_id,
            "cutoff_date": cutoff_date
        })
        top_actions = [{"action": row[0], "count": row[1]} for row in actions_result.fetchall()]
        
        # Top resource types
        resources_query = text("""
            SELECT resource_type, COUNT(*) as count
            FROM public.audit_trail 
            WHERE org_id = :org_id AND created_at >= :cutoff_date
            GROUP BY resource_type
            ORDER BY count DESC
            LIMIT 10
        """)
        
        resources_result = await db.execute(resources_query, {
            "org_id": org_id,
            "cutoff_date": cutoff_date
        })
        top_resources = [{"resource_type": row[0], "count": row[1]} for row in resources_result.fetchall()]
        
        # Top actors
        actors_query = text("""
            SELECT actor_id, actor_email, COUNT(*) as count
            FROM public.audit_trail 
            WHERE org_id = :org_id AND created_at >= :cutoff_date
            GROUP BY actor_id, actor_email
            ORDER BY count DESC
            LIMIT 10
        """)
        
        actors_result = await db.execute(actors_query, {
            "org_id": org_id,
            "cutoff_date": cutoff_date
        })
        top_actors = [
            {"actor_id": row[0], "actor_email": row[1], "count": row[2]} 
            for row in actors_result.fetchall()
        ]
        
        # Daily activity (last 7 days)
        daily_activity = []
        for i in range(7):
            day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_query = text("""
                SELECT COUNT(*) FROM public.audit_trail 
                WHERE org_id = :org_id AND created_at >= :day_start AND created_at < :day_end
            """)
            
            day_result = await db.execute(day_query, {
                "org_id": org_id,
                "day_start": day_start,
                "day_end": day_end
            })
            count = day_result.scalar() or 0
            
            daily_activity.append({
                "date": day_start.date().isoformat(),
                "count": count
            })
        
        daily_activity.reverse()  # Oldest to newest
        
        return {
            "period_days": days_back,
            "total_actions": total_actions,
            "top_actions": top_actions,
            "top_resources": top_resources,
            "top_actors": top_actors,
            "daily_activity": daily_activity
        }
        
    except Exception as e:
        logger.error("Failed to generate audit summary: %s", e)
        return {
            "period_days": days_back,
            "total_actions": 0,
            "top_actions": [],
            "top_resources": [],
            "top_actors": [],
            "daily_activity": []
        }


def _sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize details dict to be JSON-serializable."""
    sanitized = {}
    
    for key, value in details.items():
        try:
            # Test if value is JSON serializable
            json.dumps(value)
            sanitized[key] = value
        except (TypeError, ValueError):
            # Convert non-serializable to string representation
            sanitized[key] = str(value)
    
    return sanitized