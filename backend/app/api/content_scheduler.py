"""Content Scheduler API — Full lifecycle content management.

Provides endpoints for scheduling, publishing, and tracking social media content.
Integrates with Video Copycat pipeline for automated content distribution.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import get_leadgen_db
from app.api.auth import get_current_user
from app.models.crm.user import User
from app.services.tenant import get_org_id
from app.services import content_scheduler, performance_tracker

router = APIRouter()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════

class CreatePostRequest(BaseModel):
    """Request to create/schedule a post."""
    platform: str = Field(..., description="Target platform")
    content_type: str = Field(default="video", description="Content type")
    media_path: str = Field(..., description="Path to media file")
    caption: str = Field(..., description="Post caption")
    scheduled_for: datetime = Field(..., description="When to publish")
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags")
    storyboard_id: Optional[int] = Field(default=None, description="Link to video copycat")
    cloud_url: Optional[str] = Field(default=None, description="Cloud storage URL")


class UpdatePostRequest(BaseModel):
    """Request to update a scheduled post."""
    caption: Optional[str] = Field(default=None, description="Updated caption")
    scheduled_for: Optional[datetime] = Field(default=None, description="Updated schedule")
    hashtags: Optional[List[str]] = Field(default=None, description="Updated hashtags")
    cloud_url: Optional[str] = Field(default=None, description="Updated cloud URL")


class MetricsRequest(BaseModel):
    """Request to record performance metrics."""
    post_id: int = Field(..., description="Post ID")
    views: int = Field(default=0, description="View count")
    likes: int = Field(default=0, description="Like count")
    comments: int = Field(default=0, description="Comment count")
    shares: int = Field(default=0, description="Share count")
    saves: int = Field(default=0, description="Save count")
    watch_time_avg: float = Field(default=0.0, description="Average watch time")
    hook_retention: float = Field(default=0.0, description="Hook retention rate")


# ═══════════════════════════════════════════════════════════════════
# Post Management Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/posts")
async def create_scheduled_post(
    post_data: CreatePostRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Create and schedule a post for future publication."""
    logger.info(f"Creating scheduled post for {post_data.platform}")
    org_id = get_org_id(request)
    
    try:
        post_id = await content_scheduler.schedule_post(
            db=db,
            org_id=org_id,
            user_id=user.id,
            platform=post_data.platform,
            media_path=post_data.media_path,
            caption=post_data.caption,
            scheduled_for=post_data.scheduled_for,
            storyboard_id=post_data.storyboard_id,
            hashtags=post_data.hashtags or [],
            content_type=post_data.content_type,
            cloud_url=post_data.cloud_url
        )
        
        return {
            "success": True,
            "post_id": post_id,
            "platform": post_data.platform,
            "scheduled_for": post_data.scheduled_for.isoformat(),
            "message": f"Post scheduled for {post_data.platform}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create scheduled post: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule post: {str(e)}")


@router.get("/posts")
async def get_scheduled_posts(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    user_filter: Optional[int] = Query(default=None, description="Filter by user ID"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    limit: int = Query(default=50, description="Maximum results"),
    offset: int = Query(default=0, description="Results offset"),
):
    """List scheduled posts with optional filters."""
    org_id = get_org_id(request)
    
    try:
        posts = await content_scheduler.get_scheduled_posts(
            db=db,
            org_id=org_id,
            user_id=user_filter,
            status=status,
            platform=platform,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "posts": [post.to_dict() for post in posts],
            "count": len(posts),
            "filters": {
                "user_id": user_filter,
                "status": status,
                "platform": platform
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get scheduled posts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get posts: {str(e)}")


@router.get("/posts/{post_id}")
async def get_post_detail(
    post_id: int,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Get detailed information about a specific post."""
    org_id = get_org_id(request)
    
    try:
        post = await content_scheduler.get_post_by_id(db, org_id, post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {
            "success": True,
            "post": post.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get post: {str(e)}")


@router.put("/posts/{post_id}")
async def update_post(
    post_id: int,
    update_data: UpdatePostRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Update post details (caption, schedule, hashtags, etc.)."""
    org_id = get_org_id(request)
    
    try:
        # Build updates dict from provided fields
        updates = {}
        if update_data.caption is not None:
            updates["caption"] = update_data.caption
        if update_data.scheduled_for is not None:
            updates["scheduled_for"] = update_data.scheduled_for
        if update_data.hashtags is not None:
            updates["hashtags"] = update_data.hashtags
        if update_data.cloud_url is not None:
            updates["cloud_url"] = update_data.cloud_url
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        success = await content_scheduler.update_post(db, org_id, post_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {
            "success": True,
            "post_id": post_id,
            "updated_fields": list(updates.keys()),
            "message": "Post updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update post: {str(e)}")


@router.delete("/posts/{post_id}")
async def cancel_post(
    post_id: int,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Cancel a scheduled post."""
    org_id = get_org_id(request)
    
    try:
        success = await content_scheduler.cancel_post(db, org_id, post_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Post not found or cannot be cancelled")
        
        return {
            "success": True,
            "post_id": post_id,
            "message": "Post cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel post: {str(e)}")


@router.post("/posts/{post_id}/publish")
async def publish_post_now(
    post_id: int,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Publish a scheduled post immediately."""
    org_id = get_org_id(request)
    
    try:
        result = await content_scheduler.publish_post(db, org_id, post_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "post_id": post_id,
            "platform": result.get("platform"),
            "published_url": result.get("url"),
            "published_at": result.get("published_at"),
            "message": "Post published successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish post: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# Calendar and Planning Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/calendar")
async def get_calendar_view(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    start_date: Optional[datetime] = Query(default=None, description="Calendar start date"),
    end_date: Optional[datetime] = Query(default=None, description="Calendar end date"),
):
    """Get calendar view of scheduled posts."""
    org_id = get_org_id(request)
    
    # Default to current month if no dates provided
    if not start_date:
        now = datetime.now(timezone.utc)
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if not end_date:
        # End of current month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        end_date = end_date - timedelta(seconds=1)  # Last second of month
    
    try:
        calendar_data = await content_scheduler.get_calendar_view(db, org_id, start_date, end_date)
        
        return {
            "success": True,
            "calendar": calendar_data,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get calendar view: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get calendar: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# Performance and Analytics Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/performance")
async def get_performance_dashboard(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    days: int = Query(default=30, description="Days to look back"),
    platform: Optional[str] = Query(default=None, description="Platform filter"),
):
    """Get performance dashboard data."""
    org_id = get_org_id(request)
    
    try:
        # Get performance history
        history = await performance_tracker.get_performance_history(
            db, org_id, days, platform
        )
        
        # Get viral patterns analysis
        viral_patterns = await performance_tracker.get_viral_patterns(db, org_id)
        
        return {
            "success": True,
            "performance_history": history,
            "viral_patterns": viral_patterns,
            "summary": {
                "total_posts": len(history),
                "avg_viral_score": sum(p["viral_score"] for p in history) / len(history) if history else 0,
                "total_views": sum(p["views"] for p in history),
                "total_engagements": sum(p["likes"] + p["comments"] + p["shares"] + p["saves"] for p in history),
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance data: {str(e)}")


@router.get("/recommendations")
async def get_content_recommendations(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Get AI-powered content recommendations based on performance."""
    org_id = get_org_id(request)
    
    try:
        recommendations = await performance_tracker.get_content_recommendations(db, org_id)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.post("/metrics")
async def record_post_metrics(
    metrics_data: MetricsRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Record performance metrics for a published post."""
    org_id = get_org_id(request)
    
    try:
        # Convert request to metrics dict
        metrics = {
            "views": metrics_data.views,
            "likes": metrics_data.likes,
            "comments": metrics_data.comments,
            "shares": metrics_data.shares,
            "saves": metrics_data.saves,
            "watch_time_avg": metrics_data.watch_time_avg,
            "hook_retention": metrics_data.hook_retention,
        }
        
        await performance_tracker.record_metrics(db, metrics_data.post_id, metrics)
        
        return {
            "success": True,
            "post_id": metrics_data.post_id,
            "message": "Metrics recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to record metrics for post {metrics_data.post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record metrics: {str(e)}")


@router.get("/posts/{post_id}/performance")
async def get_post_performance(
    post_id: int,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Get performance metrics for a specific post."""
    org_id = get_org_id(request)
    
    try:
        performance = await content_scheduler.get_post_performance(db, org_id, post_id)
        
        if "error" in performance:
            raise HTTPException(status_code=404, detail=performance["error"])
        
        return {
            "success": True,
            "performance": performance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance for post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance: {str(e)}")