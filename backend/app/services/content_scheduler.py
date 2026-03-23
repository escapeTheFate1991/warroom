"""Content Scheduler Service — Full lifecycle content management.

Manages create → schedule → post → track for social media content.
Dispatches to per-platform publishers (Instagram, TikTok, YouTube, Facebook, X).
Set MOCK_PUBLISHING=true to use the mock publisher for development.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ScheduledPost:
    """Scheduled social media post with metadata."""
    id: int
    org_id: int
    user_id: int
    platform: str  # "instagram", "tiktok", "youtube-shorts", "facebook", "x", "twitter"
    content_type: str  # "video", "image", "carousel"
    media_path: str
    caption: str
    hashtags: List[str]
    scheduled_for: datetime
    status: str  # "draft", "scheduled", "publishing", "published", "failed"
    published_url: str  # URL after posting
    storyboard_id: Optional[int]  # link back to video copycat pipeline
    cloud_url: Optional[str] = None
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row) -> "ScheduledPost":
        """Create ScheduledPost from database row."""
        return cls(
            id=row.id,
            org_id=row.org_id,
            user_id=row.user_id,
            platform=row.platform,
            content_type=row.content_type,
            media_path=row.media_path or "",
            caption=row.caption or "",
            hashtags=row.hashtags or [],
            scheduled_for=row.scheduled_for,
            status=row.status,
            published_url=row.published_url or "",
            storyboard_id=row.storyboard_id,
            cloud_url=row.cloud_url,
            published_at=row.published_at,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "platform": self.platform,
            "content_type": self.content_type,
            "media_path": self.media_path,
            "cloud_url": self.cloud_url,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "status": self.status,
            "published_url": self.published_url,
            "storyboard_id": self.storyboard_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


async def schedule_post(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    platform: str,
    media_path: str,
    caption: str,
    scheduled_for: datetime,
    storyboard_id: Optional[int] = None,
    hashtags: Optional[List[str]] = None,
    content_type: str = "video",
    cloud_url: Optional[str] = None
) -> int:
    """
    Schedule a post for future publication.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID who scheduled the post
        platform: Target platform
        media_path: Local path to media file
        caption: Post caption/description
        scheduled_for: When to publish
        storyboard_id: Optional link to video copycat pipeline
        hashtags: Optional list of hashtags
        content_type: Type of content
        cloud_url: Optional cloud storage URL
        
    Returns:
        ID of created scheduled post
    """
    logger.info(f"Scheduling {content_type} post for {platform} at {scheduled_for}")
    
    if hashtags is None:
        hashtags = []
    
    # Validate platform
    valid_platforms = ["instagram", "tiktok", "youtube-shorts", "facebook", "x", "twitter"]
    if platform not in valid_platforms:
        raise ValueError(f"Invalid platform: {platform}. Must be one of {valid_platforms}")
    
    # Validate content type
    valid_content_types = ["video", "image", "carousel"]
    if content_type not in valid_content_types:
        raise ValueError(f"Invalid content type: {content_type}. Must be one of {valid_content_types}")
    
    query = text("""
        INSERT INTO public.scheduled_posts (
            org_id, user_id, platform, content_type, media_path, 
            cloud_url, caption, hashtags, scheduled_for, storyboard_id, 
            status, created_at, updated_at
        ) VALUES (
            :org_id, :user_id, :platform, :content_type, :media_path,
            :cloud_url, :caption, CAST(:hashtags AS jsonb), :scheduled_for, :storyboard_id,
            'scheduled', NOW(), NOW()
        ) RETURNING id
    """)
    
    result = await db.execute(query, {
        "org_id": org_id,
        "user_id": user_id,
        "platform": platform,
        "content_type": content_type,
        "media_path": media_path,
        "cloud_url": cloud_url,
        "caption": caption,
        "hashtags": json.dumps(hashtags) if hashtags else "[]",
        "scheduled_for": scheduled_for,
        "storyboard_id": storyboard_id,
    })
    
    post_id = result.scalar()
    await db.commit()
    
    logger.info(f"Scheduled post {post_id} for {platform}")
    return post_id


async def get_scheduled_posts(
    db: AsyncSession,
    org_id: int,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[ScheduledPost]:
    """
    Get scheduled posts with optional filters.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: Optional filter by user
        status: Optional filter by status
        platform: Optional filter by platform
        limit: Maximum results
        offset: Results offset
        
    Returns:
        List of scheduled posts
    """
    logger.info(f"Getting scheduled posts for org {org_id}")
    
    # Build dynamic WHERE clause
    conditions = ["org_id = :org_id"]
    params = {"org_id": org_id}
    
    if user_id is not None:
        conditions.append("user_id = :user_id")
        params["user_id"] = user_id
    
    if status:
        conditions.append("status = :status")
        params["status"] = status
    
    if platform:
        conditions.append("platform = :platform")
        params["platform"] = platform
    
    where_clause = " AND ".join(conditions)
    
    query = text(f"""
        SELECT 
            id, org_id, user_id, platform, content_type, media_path, 
            cloud_url, caption, hashtags, scheduled_for, published_at,
            status, published_url, storyboard_id, error_message,
            created_at, updated_at
        FROM public.scheduled_posts 
        WHERE {where_clause}
        ORDER BY scheduled_for DESC
        LIMIT :limit OFFSET :offset
    """)
    
    params.update({"limit": limit, "offset": offset})
    result = await db.execute(query, params)
    rows = result.fetchall()
    
    posts = [ScheduledPost.from_row(row) for row in rows]
    logger.info(f"Found {len(posts)} scheduled posts")
    
    return posts


async def get_post_by_id(db: AsyncSession, org_id: int, post_id: int) -> Optional[ScheduledPost]:
    """Get specific scheduled post by ID."""
    query = text("""
        SELECT 
            id, org_id, user_id, platform, content_type, media_path, 
            cloud_url, caption, hashtags, scheduled_for, published_at,
            status, published_url, storyboard_id, error_message,
            created_at, updated_at
        FROM public.scheduled_posts 
        WHERE id = :post_id AND org_id = :org_id
    """)
    
    result = await db.execute(query, {"post_id": post_id, "org_id": org_id})
    row = result.fetchone()
    
    return ScheduledPost.from_row(row) if row else None


async def update_post(
    db: AsyncSession,
    org_id: int,
    post_id: int,
    **updates
) -> bool:
    """
    Update scheduled post fields.
    
    Args:
        db: Database session
        org_id: Organization ID
        post_id: Post ID to update
        **updates: Fields to update
        
    Returns:
        True if post was updated, False if not found
    """
    logger.info(f"Updating post {post_id} with {list(updates.keys())}")
    
    # Validate allowed fields
    allowed_fields = {
        "caption", "hashtags", "scheduled_for", "status", 
        "published_url", "published_at", "error_message",
        "cloud_url", "media_path"
    }
    
    # Filter to only allowed fields
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not filtered_updates:
        logger.warning("No valid fields to update")
        return False
    
    # Handle JSONB fields
    if "hashtags" in filtered_updates:
        filtered_updates["hashtags"] = json.dumps(filtered_updates["hashtags"])
    
    # Build SET clause
    set_clauses = []
    params = {"post_id": post_id, "org_id": org_id}
    
    for field, value in filtered_updates.items():
        if field == "hashtags":
            set_clauses.append(f"{field} = CAST(:{field} AS jsonb)")
        else:
            set_clauses.append(f"{field} = :{field}")
        params[field] = value
    
    set_clauses.append("updated_at = NOW()")
    set_clause = ", ".join(set_clauses)
    
    query = text(f"""
        UPDATE public.scheduled_posts 
        SET {set_clause}
        WHERE id = :post_id AND org_id = :org_id
    """)
    
    result = await db.execute(query, params)
    await db.commit()
    
    updated = result.rowcount > 0
    logger.info(f"Post {post_id} update: {'success' if updated else 'not found'}")
    
    return updated


async def publish_post(db: AsyncSession, org_id: int, post_id: int) -> Dict[str, any]:
    """
    Publish a scheduled post immediately.

    Dispatches to real platform publishers unless MOCK_PUBLISHING=true.

    Args:
        db: Database session
        org_id: Organization ID
        post_id: Post ID to publish

    Returns:
        Publication result with status and details
    """
    logger.info(f"Publishing post {post_id}")

    # Get the post
    post = await get_post_by_id(db, org_id, post_id)
    if not post:
        return {"success": False, "error": "Post not found"}

    if post.status == "published":
        return {"success": False, "error": "Post already published"}

    if post.status == "publishing":
        return {"success": False, "error": "Post is currently being published"}

    try:
        # Mark as publishing
        await update_post(db, org_id, post_id, status="publishing")

        # Use mock publisher if MOCK_PUBLISHING=true, otherwise real publishers
        if os.getenv("MOCK_PUBLISHING", "").lower() in ("true", "1", "yes"):
            success, result = await _mock_publish_to_platform(post)
        else:
            success, result = await _publish_to_platform(db, post)

        if success:
            # Update as published
            await update_post(db, org_id, post_id,
                            status="published",
                            published_at=datetime.now(timezone.utc),
                            published_url=result.get("url", ""))

            logger.info(f"Post {post_id} published successfully to {post.platform}")
            return {
                "success": True,
                "platform": post.platform,
                "url": result.get("url", ""),
                "published_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Mark as failed
            await update_post(db, org_id, post_id,
                            status="failed",
                            error_message=result.get("error", "Unknown error"))

            logger.error(f"Post {post_id} publication failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Publication failed")
            }

    except Exception as e:
        logger.error(f"Post {post_id} publication error: {e}")
        await update_post(db, org_id, post_id,
                        status="failed",
                        error_message=str(e))
        return {"success": False, "error": str(e)}


async def cancel_post(db: AsyncSession, org_id: int, post_id: int) -> bool:
    """
    Cancel a scheduled post.
    
    Args:
        db: Database session
        org_id: Organization ID
        post_id: Post ID to cancel
        
    Returns:
        True if cancelled, False if not found or already published
    """
    logger.info(f"Cancelling post {post_id}")
    
    post = await get_post_by_id(db, org_id, post_id)
    if not post:
        return False
    
    if post.status in ["published", "publishing"]:
        logger.warning(f"Cannot cancel post {post_id} with status {post.status}")
        return False
    
    return await update_post(db, org_id, post_id, status="cancelled")


async def get_post_performance(db: AsyncSession, org_id: int, post_id: int) -> Dict[str, any]:
    """
    Get performance metrics for a published post.
    
    For MVP: returns mock metrics
    Future: fetches real metrics from platform APIs
    
    Args:
        db: Database session
        org_id: Organization ID
        post_id: Post ID
        
    Returns:
        Performance metrics dictionary
    """
    logger.info(f"Getting performance for post {post_id}")
    
    post = await get_post_by_id(db, org_id, post_id)
    if not post:
        return {"error": "Post not found"}
    
    if post.status != "published":
        return {"error": "Post not published yet"}
    
    # Check if we have metrics in content_metrics table
    query = text("""
        SELECT 
            views, likes, comments, shares, saves, engagement_rate,
            watch_time_avg, hook_retention, viral_score, snapshot_at
        FROM public.content_metrics 
        WHERE post_id = :post_id AND org_id = :org_id
        ORDER BY snapshot_at DESC
        LIMIT 1
    """)
    
    result = await db.execute(query, {"post_id": post_id, "org_id": org_id})
    row = result.fetchone()
    
    if row:
        return {
            "post_id": post_id,
            "views": row.views,
            "likes": row.likes,
            "comments": row.comments,
            "shares": row.shares,
            "saves": row.saves,
            "engagement_rate": float(row.engagement_rate),
            "watch_time_avg": float(row.watch_time_avg),
            "hook_retention": float(row.hook_retention),
            "viral_score": float(row.viral_score),
            "last_updated": row.snapshot_at.isoformat()
        }
    
    # MVP: Return mock metrics for demonstration
    return _generate_mock_metrics(post)


async def get_calendar_view(
    db: AsyncSession,
    org_id: int,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, List[dict]]:
    """
    Get calendar view of scheduled posts.
    
    Args:
        db: Database session
        org_id: Organization ID
        start_date: Calendar start date
        end_date: Calendar end date
        
    Returns:
        Dictionary with dates as keys and posts as values
    """
    logger.info(f"Getting calendar view for org {org_id}")
    
    query = text("""
        SELECT 
            id, platform, content_type, caption, scheduled_for, status
        FROM public.scheduled_posts 
        WHERE org_id = :org_id 
        AND scheduled_for BETWEEN :start_date AND :end_date
        ORDER BY scheduled_for ASC
    """)
    
    # Strip timezone info for naive TIMESTAMP columns
    start_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
    end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
    
    result = await db.execute(query, {
        "org_id": org_id,
        "start_date": start_naive,
        "end_date": end_naive
    })
    rows = result.fetchall()
    
    # Group by date
    calendar = {}
    for row in rows:
        date_key = row.scheduled_for.date().isoformat()
        if date_key not in calendar:
            calendar[date_key] = []
        
        calendar[date_key].append({
            "id": row.id,
            "platform": row.platform,
            "content_type": row.content_type,
            "caption": row.caption[:100] + "..." if len(row.caption) > 100 else row.caption,
            "scheduled_for": row.scheduled_for.isoformat(),
            "status": row.status
        })
    
    return calendar


async def _publish_to_platform(db: AsyncSession, post: ScheduledPost) -> tuple[bool, dict]:
    """Dispatch to the correct per-platform publisher.

    Each publisher handles its own token refresh on 401.
    Media URL is resolved from cloud_url (preferred) or media_path.
    """
    from app.services.platform_publishers.instagram import InstagramPublisher
    from app.services.platform_publishers.facebook import FacebookPublisher
    from app.services.platform_publishers.tiktok import TikTokPublisher
    from app.services.platform_publishers.youtube import YouTubePublisher
    from app.services.platform_publishers.twitter import TwitterPublisher

    # Resolve the media URL — prefer cloud_url, fall back to media_path
    media_url = post.cloud_url or post.media_path
    if not media_url:
        return False, {"error": "No media URL available for publishing"}

    platform = post.platform
    publishers = {
        "instagram": InstagramPublisher(),
        "facebook": FacebookPublisher(),
        "tiktok": TikTokPublisher(),
        "youtube-shorts": YouTubePublisher(),
        "x": TwitterPublisher(),
        "twitter": TwitterPublisher(),
    }

    publisher = publishers.get(platform)
    if not publisher:
        return False, {"error": f"No publisher available for platform: {platform}"}

    logger.info(f"Publishing post {post.id} to {platform} via real API")
    return await publisher.publish(
        db=db,
        org_id=post.org_id,
        media_url=media_url,
        caption=post.caption,
        content_type=post.content_type,
        hashtags=post.hashtags,
    )


async def _mock_publish_to_platform(post: ScheduledPost) -> tuple[bool, dict]:
    """
    Mock platform publication for MVP.
    
    Future: Replace with actual platform API calls
    """
    # Simulate API call delay
    import asyncio
    await asyncio.sleep(0.5)
    
    # Mock success/failure based on platform
    if post.platform == "instagram":
        success_rate = 0.95
        mock_url = f"https://instagram.com/p/mock_{post.id}"
    elif post.platform == "tiktok":
        success_rate = 0.90
        mock_url = f"https://tiktok.com/@user/video/{post.id}"
    elif post.platform == "youtube-shorts":
        success_rate = 0.85
        mock_url = f"https://youtube.com/shorts/mock_{post.id}"
    elif post.platform == "facebook":
        success_rate = 0.92
        mock_url = f"https://facebook.com/video.php?v={post.id}"
    elif post.platform in ("x", "twitter"):
        success_rate = 0.90
        mock_url = f"https://x.com/i/status/mock_{post.id}"
    else:
        success_rate = 0.85
        mock_url = f"https://example.com/post/{post.id}"
    
    import random
    if random.random() < success_rate:
        return True, {"url": mock_url, "platform_id": f"mock_{post.id}"}
    else:
        return False, {"error": f"Mock {post.platform} API error"}


def _generate_mock_metrics(post: ScheduledPost) -> dict:
    """Generate realistic mock metrics for demonstration."""
    import random
    from datetime import timedelta
    
    # Base metrics vary by platform
    if post.platform == "instagram":
        base_views = random.randint(500, 5000)
    elif post.platform == "tiktok":
        base_views = random.randint(1000, 50000)
    elif post.platform == "youtube-shorts":
        base_views = random.randint(800, 20000)
    else:  # facebook
        base_views = random.randint(300, 3000)
    
    views = base_views
    likes = int(views * random.uniform(0.05, 0.15))
    comments = int(views * random.uniform(0.01, 0.05))
    shares = int(views * random.uniform(0.005, 0.02))
    saves = int(views * random.uniform(0.01, 0.08))
    
    engagement_rate = (likes + comments + shares + saves) / views * 100
    watch_time_avg = random.uniform(3.5, 25.0)
    hook_retention = random.uniform(0.60, 0.90)
    
    return {
        "post_id": post.id,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "engagement_rate": round(engagement_rate, 2),
        "watch_time_avg": round(watch_time_avg, 1),
        "hook_retention": round(hook_retention * 100, 1),
        "viral_score": round(engagement_rate * hook_retention, 1),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "is_mock": True
    }