"""API endpoints for Instagram CDN → Garage S3 migration job."""

import logging
from typing import Dict, Any, Optional, List, Union

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.models.crm.user import User
from app.jobs.cdn_migration import migrate_cdn_urls, get_migration_status, test_migration_sample

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Background Jobs"])


class MigrationResponse(BaseModel):
    message: str
    status: str


class MigrationStatusResponse(BaseModel):
    status: str  # idle, running, complete, error
    progress: int
    total: int
    success_count: int
    error_count: int
    started_at: Union[str, None] = None
    completed_at: Union[str, None] = None
    errors: List[str] = []
    last_error: Union[str, None] = None


@router.post("/migrate-cdn-urls", response_model=MigrationResponse)
async def start_cdn_migration(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Start the CDN → S3 migration job.
    
    This will download all 616 Instagram CDN URLs and store them in Garage S3,
    then update the database to point to the permanent S3 URLs.
    """
    try:
        # Check if already running
        status = get_migration_status()
        if status["status"] == "running":
            raise HTTPException(
                status_code=409, 
                detail="Migration job is already running"
            )
        
        # Start the background task
        background_tasks.add_task(migrate_cdn_urls)
        
        logger.info(f"CDN migration started by user {current_user.id}")
        
        return MigrationResponse(
            message="CDN migration job started. Use GET /api/jobs/cdn-migration/status to monitor progress.",
            status="started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start CDN migration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start migration: {str(e)}"
        )


@router.post("/migrate-cdn-urls/test", response_model=MigrationResponse)
async def test_cdn_migration(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Test the CDN → S3 migration with 5 posts only.
    
    This will test the migration process with a small subset to verify everything works.
    """
    try:
        # Check if already running
        status = get_migration_status()
        if status["status"] == "running":
            raise HTTPException(
                status_code=409, 
                detail="Migration job is already running"
            )
        
        # Start the test migration
        background_tasks.add_task(test_migration_sample)
        
        logger.info(f"CDN migration test started by user {current_user.id}")
        
        return MigrationResponse(
            message="CDN migration test started with 5 posts. Use GET /api/jobs/cdn-migration/status to monitor progress.",
            status="started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start CDN migration test: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start test migration: {str(e)}"
        )


@router.get("/cdn-migration/status")
async def get_cdn_migration_status(
    current_user: User = Depends(get_current_user)
):
    """Get the current status of the CDN migration job."""
    try:
        status = get_migration_status()
        
        return {
            "status": status["status"],
            "progress": status["progress"],
            "total": status["total"],
            "success_count": status["success_count"],
            "error_count": status["error_count"],
            "started_at": status.get("started_at"),
            "completed_at": status.get("completed_at"),
            "errors": status.get("errors", [])[-10:],  # Only return last 10 errors
            "last_error": status.get("last_error")
        }
        
    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration status: {str(e)}"
        )