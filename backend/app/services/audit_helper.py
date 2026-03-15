"""Audit Helper - Easy integration for existing endpoints."""

import logging
from typing import Any, Dict, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tenant import get_org_id, get_user_id
from app.services.audit_trail import log_action

logger = logging.getLogger(__name__)


async def audit_action(
    db: AsyncSession,
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    target_user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    actor_email: Optional[str] = None
) -> None:
    """
    Convenient wrapper for logging audit actions from endpoints.
    
    Automatically extracts org_id, user_id from request state.
    Fire-and-forget - never raises exceptions.
    
    Example usage:
        # In a settings update endpoint
        await audit_action(
            db, request, "update", "setting", 
            resource_id="api_key", 
            details={"field": "openai_key", "masked_new_value": "sk-..."}
        )
        
        # In a user management endpoint
        await audit_action(
            db, request, "role_change", "user",
            resource_id=str(target_user.id),
            target_user_id=target_user.id,
            details={"old_role": old_role.name, "new_role": new_role.name}
        )
    """
    try:
        org_id = get_org_id(request)
        actor_id = get_user_id(request)
        
        if not org_id or not actor_id:
            logger.warning("Skipping audit log - missing org_id or actor_id")
            return
        
        await log_action(
            db=db,
            org_id=org_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            target_user_id=target_user_id,
            details=details or {},
            request=request,
            actor_email=actor_email
        )
        
    except Exception as e:
        logger.error("Failed to log audit action: %s", e)
        # Never re-raise - this is fire-and-forget


# Common audit action templates for consistency

async def audit_settings_change(
    db: AsyncSession, 
    request: Request, 
    setting_key: str, 
    old_value: Any = None, 
    new_value: Any = None
) -> None:
    """Audit a settings change with consistent format."""
    # Mask sensitive values
    if "key" in setting_key.lower() or "secret" in setting_key.lower():
        old_display = "***" if old_value else None
        new_display = "***" if new_value else None
    else:
        old_display = str(old_value) if old_value is not None else None
        new_display = str(new_value) if new_value is not None else None
    
    await audit_action(
        db, request, "update", "setting",
        resource_id=setting_key,
        details={
            "setting": setting_key,
            "old_value": old_display,
            "new_value": new_display
        }
    )


async def audit_user_management(
    db: AsyncSession,
    request: Request,
    action: str,  # "create", "update", "deactivate", "role_change"
    target_user_id: int,
    details: Dict[str, Any]
) -> None:
    """Audit user management actions."""
    await audit_action(
        db, request, action, "user",
        resource_id=str(target_user_id),
        target_user_id=target_user_id,
        details=details
    )


async def audit_data_export(
    db: AsyncSession,
    request: Request,
    export_type: str,
    record_count: int,
    filters: Optional[Dict[str, Any]] = None
) -> None:
    """Audit data export operations."""
    await audit_action(
        db, request, "export", export_type,
        details={
            "export_type": export_type,
            "record_count": record_count,
            "filters": filters or {}
        }
    )


async def audit_cross_user_view(
    db: AsyncSession,
    request: Request,
    resource_type: str,
    resource_id: str,
    viewed_user_id: int
) -> None:
    """Audit when admin/manager views another user's data."""
    await audit_action(
        db, request, "view", resource_type,
        resource_id=resource_id,
        target_user_id=viewed_user_id,
        details={"cross_user_access": True}
    )