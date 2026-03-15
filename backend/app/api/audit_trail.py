"""Audit Trail API endpoints - Platform-wide activity logging."""

import logging
import csv
import io
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id
from app.api.auth import require_superadmin
from app.services.audit_trail import get_audit_log, get_audit_summary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/audit")
async def list_audit_entries(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=1000),
    action: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    actor_id: Optional[int] = Query(default=None),
    from_date: Optional[date] = Query(alias="from", default=None),
    to_date: Optional[date] = Query(alias="to", default=None),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_superadmin())
):
    """
    List audit trail entries with filtering and pagination.
    Admin only.
    """
    org_id = get_org_id(request)
    
    try:
        result = await get_audit_log(
            db=db,
            org_id=org_id,
            page=page,
            limit=limit,
            action=action,
            resource_type=resource_type,
            actor_id=actor_id,
            date_from=from_date,
            date_to=to_date
        )
        
        return {
            "status": "success",
            "data": result,
            "pagination": {
                "page": result["page"],
                "limit": result["limit"],
                "total": result["total"],
                "pages": (result["total"] + result["limit"] - 1) // result["limit"]  # Ceiling division
            }
        }
        
    except Exception as e:
        logger.error("Failed to list audit entries: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve audit entries")


@router.get("/audit/summary")
async def audit_summary(
    request: Request,
    days_back: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_superadmin())
):
    """
    Get aggregated audit statistics.
    Admin only.
    """
    org_id = get_org_id(request)
    
    try:
        summary = await get_audit_summary(
            db=db,
            org_id=org_id,
            days_back=days_back
        )
        
        return {
            "status": "success",
            "data": summary
        }
        
    except Exception as e:
        logger.error("Failed to generate audit summary: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate audit summary")


@router.get("/audit/export")
async def export_audit_log(
    request: Request,
    format: str = Query(default="csv", regex="^csv$"),  # Only CSV for now
    from_date: Optional[date] = Query(alias="from", default=None),
    to_date: Optional[date] = Query(alias="to", default=None),
    action: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_superadmin())
):
    """
    Export audit log as CSV.
    Admin only.
    """
    org_id = get_org_id(request)
    
    try:
        # Get all matching entries (no pagination for export)
        result = await get_audit_log(
            db=db,
            org_id=org_id,
            page=1,
            limit=100000,  # Large limit for export
            action=action,
            resource_type=resource_type,
            date_from=from_date,
            date_to=to_date
        )
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "ID",
            "Timestamp",
            "Actor ID",
            "Actor Email",
            "Action",
            "Resource Type",
            "Resource ID",
            "Target User ID",
            "IP Address",
            "User Agent",
            "Details"
        ])
        
        # Write data rows
        for entry in result["entries"]:
            writer.writerow([
                entry.get("id", ""),
                entry.get("created_at", ""),
                entry.get("actor_id", ""),
                entry.get("actor_email", ""),
                entry.get("action", ""),
                entry.get("resource_type", ""),
                entry.get("resource_id", ""),
                entry.get("target_user_id", ""),
                entry.get("ip_address", ""),
                entry.get("user_agent", ""),
                str(entry.get("details", "{}"))  # JSON as string
            ])
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_trail_{timestamp}.csv"
        
        # Return as streaming response
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error("Failed to export audit log: %s", e)
        raise HTTPException(status_code=500, detail="Failed to export audit log")


@router.get("/audit/actions")
async def get_available_actions(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_superadmin())
):
    """
    Get list of available audit actions for filtering.
    Admin only.
    """
    org_id = get_org_id(request)
    
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT DISTINCT action 
            FROM public.audit_trail 
            WHERE org_id = :org_id 
            ORDER BY action
        """)
        
        result = await db.execute(query, {"org_id": org_id})
        actions = [row[0] for row in result.fetchall()]
        
        return {
            "status": "success",
            "data": {
                "actions": actions
            }
        }
        
    except Exception as e:
        logger.error("Failed to get available actions: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve available actions")


@router.get("/audit/resource-types")
async def get_available_resource_types(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_superadmin())
):
    """
    Get list of available resource types for filtering.
    Admin only.
    """
    org_id = get_org_id(request)
    
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT DISTINCT resource_type 
            FROM public.audit_trail 
            WHERE org_id = :org_id 
            ORDER BY resource_type
        """)
        
        result = await db.execute(query, {"org_id": org_id})
        resource_types = [row[0] for row in result.fetchall()]
        
        return {
            "status": "success",
            "data": {
                "resource_types": resource_types
            }
        }
        
    except Exception as e:
        logger.error("Failed to get available resource types: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve available resource types")