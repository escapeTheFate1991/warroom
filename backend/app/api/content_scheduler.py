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
from app.services import content_scheduler, performance_tracker, content_recycler, optimal_timing, multi_account_poster

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


class BulkPostRequest(BaseModel):
    """Request to create multiple posts at once."""
    posts: List[CreatePostRequest] = Field(..., description="List of posts to schedule")
    distribution_strategy: str = Field(default="staggered", description="How to distribute posts")


class RecyclePostRequest(BaseModel):
    """Request to recycle a post."""
    original_post_id: int = Field(..., description="ID of post to recycle")
    account_id: Optional[int] = Field(default=None, description="Target social account")
    scheduled_for: Optional[datetime] = Field(default=None, description="When to publish recycle")
    caption_variation: Optional[str] = Field(default=None, description="Modified caption")


class SeriesRequest(BaseModel):
    """Request to create a multi-part story series."""
    title: str = Field(..., description="Series title")
    posts: List[CreatePostRequest] = Field(..., description="Posts in the series")
    schedule_strategy: str = Field(default="daily", description="How to schedule series")
    start_date: Optional[datetime] = Field(default=None, description="Series start date")


class DistributeContentRequest(BaseModel):
    """Request to distribute content across accounts."""
    content: CreatePostRequest = Field(..., description="Content to distribute")
    account_ids: List[int] = Field(..., description="Accounts to post to")
    schedule_strategy: str = Field(default="staggered", description="Distribution strategy")


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


# ═══════════════════════════════════════════════════════════════════
# Content Recycling Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/recycle/candidates")
async def get_recyclable_content(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    platform: str = Query(..., description="Platform to get candidates for"),
    min_engagement: float = Query(default=0.5, description="Minimum engagement score"),
    limit: int = Query(default=10, description="Maximum candidates to return"),
):
    """Get recyclable content candidates."""
    org_id = get_org_id(request)
    
    try:
        candidates = await content_recycler.get_recyclable_content(
            db=db,
            org_id=org_id,
            platform=platform,
            min_engagement=min_engagement,
            limit=limit
        )
        
        return {
            "success": True,
            "candidates": candidates,
            "platform": platform,
            "count": len(candidates)
        }
        
    except Exception as e:
        logger.error(f"Failed to get recyclable content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get candidates: {str(e)}")


@router.post("/recycle/auto")
async def trigger_auto_recycle(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    account_id: Optional[int] = Query(default=None, description="Specific account to recycle for"),
):
    """Trigger automatic content recycling."""
    org_id = get_org_id(request)
    
    try:
        recycled_id = await content_recycler.auto_schedule_recycle(
            db=db,
            org_id=org_id,
            user_id=user.id,
            account_id=account_id
        )
        
        if recycled_id:
            return {
                "success": True,
                "recycled_post_id": recycled_id,
                "message": "Content recycled and scheduled automatically"
            }
        else:
            return {
                "success": False,
                "message": "No suitable content found for recycling"
            }
        
    except Exception as e:
        logger.error(f"Failed to auto-recycle content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to recycle: {str(e)}")


@router.put("/posts/{post_id}/recycle")
async def recycle_specific_post(
    post_id: int,
    recycle_data: RecyclePostRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Manually recycle a specific post."""
    org_id = get_org_id(request)
    
    try:
        # Use provided schedule or suggest optimal time
        scheduled_for = recycle_data.scheduled_for
        if not scheduled_for:
            scheduled_for = await optimal_timing.suggest_next_slot(
                db=db,
                org_id=org_id,
                account_id=recycle_data.account_id
            )
        
        recycled_id = await content_recycler.create_recycled_post(
            db=db,
            org_id=org_id,
            user_id=user.id,
            original_post_id=recycle_data.original_post_id,
            account_id=recycle_data.account_id,
            scheduled_for=scheduled_for,
            caption_variation=recycle_data.caption_variation
        )
        
        return {
            "success": True,
            "recycled_post_id": recycled_id,
            "original_post_id": recycle_data.original_post_id,
            "scheduled_for": scheduled_for.isoformat(),
            "message": "Post recycled successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to recycle post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to recycle post: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# Optimal Timing Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/optimal-times")
async def get_optimal_posting_times(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    platform: str = Query(..., description="Platform to analyze"),
    account_id: Optional[int] = Query(default=None, description="Specific account"),
):
    """Get best posting times for platform."""
    org_id = get_org_id(request)
    
    try:
        optimal_times = await optimal_timing.get_best_posting_times(
            db=db,
            org_id=org_id,
            platform=platform,
            account_id=account_id
        )
        
        return {
            "success": True,
            "platform": platform,
            "optimal_times": optimal_times,
            "account_id": account_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get optimal times: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get optimal times: {str(e)}")


@router.get("/heatmap")
async def get_engagement_heatmap(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    platform: str = Query(..., description="Platform to analyze"),
    days: int = Query(default=30, description="Days of history to include"),
):
    """Get engagement heatmap data."""
    org_id = get_org_id(request)
    
    try:
        heatmap = await optimal_timing.get_engagement_heatmap(
            db=db,
            org_id=org_id,
            platform=platform,
            days=days
        )
        
        return {
            "success": True,
            "heatmap": heatmap
        }
        
    except Exception as e:
        logger.error(f"Failed to get engagement heatmap: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get heatmap: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# Bulk and Multi-Account Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/posts/bulk")
async def schedule_bulk_posts(
    bulk_data: BulkPostRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Schedule multiple posts at once."""
    org_id = get_org_id(request)
    
    try:
        scheduled_ids = []
        
        for i, post_data in enumerate(bulk_data.posts):
            # Stagger posts based on strategy
            if bulk_data.distribution_strategy == "staggered":
                # Add hours between posts
                post_data.scheduled_for = post_data.scheduled_for + timedelta(hours=i * 2)
            elif bulk_data.distribution_strategy == "optimal":
                # Use optimal timing
                post_data.scheduled_for = await optimal_timing.suggest_next_slot(
                    db=db,
                    org_id=org_id,
                    content_type=post_data.content_type
                )
                post_data.scheduled_for += timedelta(minutes=i * 30)
            
            # Create the post
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
            
            scheduled_ids.append(post_id)
        
        return {
            "success": True,
            "scheduled_post_ids": scheduled_ids,
            "count": len(scheduled_ids),
            "strategy": bulk_data.distribution_strategy,
            "message": f"Scheduled {len(scheduled_ids)} posts successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule bulk posts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule bulk posts: {str(e)}")


@router.post("/distribute")
async def distribute_content_across_accounts(
    distribute_data: DistributeContentRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Distribute one piece of content across multiple accounts."""
    org_id = get_org_id(request)
    
    try:
        content_dict = {
            "platform": distribute_data.content.platform,
            "content_type": distribute_data.content.content_type,
            "media_path": distribute_data.content.media_path,
            "cloud_url": distribute_data.content.cloud_url,
            "caption": distribute_data.content.caption,
            "hashtags": distribute_data.content.hashtags,
            "storyboard_id": distribute_data.content.storyboard_id
        }
        
        scheduled_ids = await multi_account_poster.distribute_content(
            db=db,
            org_id=org_id,
            user_id=user.id,
            content=content_dict,
            accounts=distribute_data.account_ids,
            schedule_strategy=distribute_data.schedule_strategy
        )
        
        return {
            "success": True,
            "scheduled_post_ids": scheduled_ids,
            "account_count": len(distribute_data.account_ids),
            "strategy": distribute_data.schedule_strategy,
            "message": f"Content distributed to {len(distribute_data.account_ids)} accounts"
        }
        
    except Exception as e:
        logger.error(f"Failed to distribute content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to distribute content: {str(e)}")


@router.get("/accounts")
async def get_posting_accounts(
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
):
    """Get all available posting accounts."""
    org_id = get_org_id(request)
    
    try:
        accounts = await multi_account_poster.get_posting_accounts(
            db=db,
            org_id=org_id,
            platform=platform
        )
        
        return {
            "success": True,
            "accounts": accounts,
            "platform_filter": platform,
            "count": len(accounts)
        }
        
    except Exception as e:
        logger.error(f"Failed to get posting accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get accounts: {str(e)}")


@router.get("/accounts/{account_id}/schedule")
async def get_account_schedule(
    account_id: int,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
    days_ahead: int = Query(default=7, description="Days ahead to show"),
):
    """Get schedule for specific social account."""
    org_id = get_org_id(request)
    
    try:
        # Get scheduled posts for this account
        posts = await content_scheduler.get_scheduled_posts(
            db=db,
            org_id=org_id,
            status="scheduled",
            limit=100,
            offset=0
        )
        
        # Filter by account and date range
        end_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        account_posts = [
            post for post in posts 
            if (hasattr(post, 'social_account_id') and post.social_account_id == account_id) and
               post.scheduled_for <= end_date
        ]
        
        # Get cadence info
        cadence = await multi_account_poster.get_account_cadence(
            db=db,
            org_id=org_id,
            account_id=account_id
        )
        
        return {
            "success": True,
            "account_id": account_id,
            "scheduled_posts": [post.to_dict() for post in account_posts],
            "cadence": cadence,
            "days_ahead": days_ahead,
            "post_count": len(account_posts)
        }
        
    except Exception as e:
        logger.error(f"Failed to get account schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# Series Management Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/series")
async def create_content_series(
    series_data: SeriesRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Create a multi-part story series."""
    org_id = get_org_id(request)
    
    try:
        # Generate series ID (timestamp-based)
        series_id = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        # Determine start date
        start_date = series_data.start_date or datetime.now(timezone.utc) + timedelta(hours=2)
        
        scheduled_ids = []
        
        for i, post_data in enumerate(series_data.posts):
            # Calculate schedule based on strategy
            if series_data.schedule_strategy == "daily":
                post_schedule = start_date + timedelta(days=i)
            elif series_data.schedule_strategy == "hourly":
                post_schedule = start_date + timedelta(hours=i * 4)  # Every 4 hours
            elif series_data.schedule_strategy == "weekly":
                post_schedule = start_date + timedelta(weeks=i)
            else:
                # Default to daily
                post_schedule = start_date + timedelta(days=i)
            
            # Add series info to caption
            series_caption = f"Part {i+1}/{len(series_data.posts)}: {series_data.title}\n\n{post_data.caption}"
            
            # Schedule the post with series metadata
            post_id = await content_scheduler.schedule_post(
                db=db,
                org_id=org_id,
                user_id=user.id,
                platform=post_data.platform,
                media_path=post_data.media_path,
                caption=series_caption,
                scheduled_for=post_schedule,
                storyboard_id=post_data.storyboard_id,
                hashtags=post_data.hashtags or [],
                content_type=post_data.content_type,
                cloud_url=post_data.cloud_url
            )
            
            # Update with series info
            from sqlalchemy import text
            update_query = text("""
                UPDATE public.scheduled_posts 
                SET series_id = :series_id, series_order = :series_order
                WHERE id = :post_id
            """)
            
            await db.execute(update_query, {
                "series_id": series_id,
                "series_order": i,
                "post_id": post_id
            })
            
            scheduled_ids.append(post_id)
        
        await db.commit()
        
        return {
            "success": True,
            "series_id": series_id,
            "title": series_data.title,
            "scheduled_post_ids": scheduled_ids,
            "post_count": len(scheduled_ids),
            "strategy": series_data.schedule_strategy,
            "start_date": start_date.isoformat(),
            "message": f"Series '{series_data.title}' created with {len(scheduled_ids)} posts"
        }
        
    except Exception as e:
        logger.error(f"Failed to create content series: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create series: {str(e)}")