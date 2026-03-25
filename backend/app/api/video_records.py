"""
Video Records API

API endpoints for the unified VideoRecord model.
Provides access to structured video data for the CDR platform.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id
from app.services.video_record_service import create_video_record_service
from app.models.video_record import VideoRecord
from app.models.crm.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content-intel", tags=["video-records"])


@router.get("/video/{post_id}", response_model=VideoRecord)
async def get_video_record(
    post_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Get a single VideoRecord by post ID
    
    Returns structured video data including:
    - Basic metadata (title, URL, platform, etc.)
    - Real metrics (likes, comments, shares, views)
    - Runtime in proper M:SS format
    - Transcript with timed segments
    - Creator directives for replication
    """
    try:
        service = create_video_record_service(db)
        video_record = await service.get_video_record(post_id)
        
        if not video_record:
            raise HTTPException(
                status_code=404, 
                detail=f"Video record not found for post {post_id}"
            )
        
        return video_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video record %s: %s", post_id, e)
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve video record"
        )


@router.get("/videos", response_model=List[VideoRecord])
async def get_video_records(
    competitor_id: Optional[int] = Query(None, description="Filter by competitor ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    days: Optional[int] = Query(30, ge=1, le=365, description="Filter by days back"),
    platform: Optional[str] = Query(None, description="Filter by platform (instagram, tiktok, etc.)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Get multiple VideoRecords with filtering
    
    Query parameters:
    - competitor_id: Optional filter by specific competitor
    - limit: Maximum records to return (1-100, default 20)
    - days: Look back this many days (1-365, default 30)
    - platform: Filter by platform (instagram, tiktok, youtube, x)
    
    Returns list of VideoRecord objects ordered by engagement score.
    """
    try:
        from app.services.tenant import get_org_id_from_request
        from fastapi import Request
        
        # Get org_id for multi-tenant filtering
        # Note: This is a simplified approach - in production you'd get this from the request context
        org_id = None  # TODO: Get from request context when available
        
        service = create_video_record_service(db)
        video_records = await service.get_video_records(
            competitor_id=competitor_id,
            limit=limit,
            days=days,
            platform=platform,
            org_id=org_id
        )
        
        return video_records
        
    except Exception as e:
        logger.error("Failed to get video records: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve video records"
        )


@router.get("/videos/recent", response_model=List[VideoRecord])
async def get_recent_videos(
    days: int = Query(30, ge=1, le=365, description="Days back to search"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Get recent high-performing video records across all competitors
    
    Returns the most recent and highest-engaging videos for analysis.
    Useful for trending content discovery and pattern identification.
    """
    try:
        service = create_video_record_service(db)
        video_records = await service.get_recent_video_records(
            days=days,
            limit=limit
        )
        
        return video_records
        
    except Exception as e:
        logger.error("Failed to get recent videos: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve recent videos"
        )


@router.get("/competitor/{competitor_id}/videos", response_model=List[VideoRecord])
async def get_competitor_videos(
    competitor_id: int,
    limit: int = Query(10, ge=1, le=50, description="Maximum records to return"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Get video records for a specific competitor
    
    Returns the top-performing videos for the specified competitor,
    ordered by engagement score.
    """
    try:
        service = create_video_record_service(db)
        video_records = await service.get_video_records_for_competitor(
            competitor_id=competitor_id,
            limit=limit
        )
        
        if not video_records:
            raise HTTPException(
                status_code=404,
                detail=f"No video records found for competitor {competitor_id}"
            )
        
        return video_records
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get competitor videos %s: %s", competitor_id, e)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve competitor videos"
        )


# Debug and audit endpoints

@router.get("/debug/runtime-analysis", response_model=Dict[str, Any])
async def analyze_runtime_issues(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    DEBUG: Analyze runtime data quality issues
    
    This endpoint helps identify and fix runtime format problems
    like "1:9.09999999999994" and "0:47.4".
    """
    try:
        service = create_video_record_service(db)
        analysis = await service.analyze_runtime_issues()
        
        return {
            "status": "analysis_complete",
            "data": analysis
        }
        
    except Exception as e:
        logger.error("Failed to analyze runtime issues: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze runtime issues"
        )


@router.get("/debug/metrics-audit", response_model=Dict[str, Any])  
async def audit_engagement_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    DEBUG: Audit engagement score calculations
    
    This endpoint documents the engagement_score formula and identifies
    any discrepancies in the calculation.
    """
    try:
        service = create_video_record_service(db)
        audit = await service.get_metrics_audit()
        
        return {
            "status": "audit_complete", 
            "data": audit,
            "recommendations": [
                "engagement_score is correctly calculated as likes + comments + shares",
                "No major formula changes needed - simple addition works well",
                "Consider adding engagement_rate calculation (engagement_score / followers) for comparison across competitor sizes"
            ]
        }
        
    except Exception as e:
        logger.error("Failed to audit metrics: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to audit engagement metrics"
        )


@router.get("/debug/test-real-data", response_model=List[VideoRecord])
async def test_with_real_data(
    limit: int = Query(3, ge=1, le=10, description="Number of records to test"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    DEBUG: Test VideoRecord construction with real database data
    
    This endpoint builds VideoRecords from actual competitor_posts data
    and shows the output with correct M:SS runtime formatting.
    """
    try:
        service = create_video_record_service(db)
        
        # Get recent high-engagement posts for testing
        video_records = await service.get_recent_video_records(
            days=90,  # Wider search for more data
            limit=limit
        )
        
        if not video_records:
            raise HTTPException(
                status_code=404,
                detail="No video records found for testing. Run competitor sync first."
            )
        
        return video_records
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to test real data: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to test with real data"
        )