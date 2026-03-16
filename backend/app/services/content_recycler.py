"""Content Recycler Service — Intelligent content reposting.

Identifies high-performing content and automatically schedules recycled posts
to maximize engagement and extend content lifecycle.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_recyclable_content(
    db: AsyncSession,
    org_id: int,
    platform: str,
    min_engagement: float = 0.5,
    limit: int = 10,
    min_age_days: int = 30
) -> List[Dict]:
    """
    Find top-performing past posts eligible for recycling.
    
    Args:
        db: Database session
        org_id: Organization ID
        platform: Platform to search (instagram, tiktok, etc.)
        min_engagement: Minimum engagement score (0.0 - 1.0)
        limit: Maximum posts to return
        min_age_days: Minimum age in days before content can be recycled
        
    Returns:
        List of recyclable posts with metadata
    """
    query = text("""
        SELECT 
            id,
            platform,
            content_type,
            media_path,
            cloud_url,
            caption,
            hashtags,
            engagement_score,
            published_at,
            published_url,
            storyboard_id,
            recycle_count
        FROM public.scheduled_posts
        WHERE 
            org_id = :org_id
            AND platform = :platform
            AND status = 'published'
            AND is_recycled = false
            AND engagement_score >= :min_engagement
            AND published_at < :min_date
            AND original_post_id IS NULL  -- Only original posts, not previous recycles
        ORDER BY engagement_score DESC, published_at ASC
        LIMIT :limit
    """)
    
    min_date = datetime.now(timezone.utc) - timedelta(days=min_age_days)
    
    result = await db.execute(query, {
        "org_id": org_id,
        "platform": platform,
        "min_engagement": min_engagement,
        "min_date": min_date,
        "limit": limit
    })
    
    posts = []
    for row in result.fetchall():
        posts.append({
            "id": row.id,
            "platform": row.platform,
            "content_type": row.content_type,
            "media_path": row.media_path,
            "cloud_url": row.cloud_url,
            "caption": row.caption,
            "hashtags": row.hashtags or [],
            "engagement_score": float(row.engagement_score),
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "published_url": row.published_url,
            "storyboard_id": row.storyboard_id,
            "recycle_count": row.recycle_count or 0,
            "recycling_potential": _calculate_recycling_potential(row)
        })
    
    return posts


async def create_recycled_post(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    original_post_id: int,
    account_id: Optional[int],
    scheduled_for: datetime,
    caption_variation: Optional[str] = None
) -> int:
    """
    Clone a past post for reposting.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID creating the recycle
        original_post_id: ID of original post to recycle
        account_id: Social account to post to (optional)
        scheduled_for: When to publish the recycled post
        caption_variation: Modified caption (optional, uses original if None)
        
    Returns:
        ID of the new recycled post
    """
    # Get original post data
    query = text("""
        SELECT 
            platform, content_type, media_path, cloud_url, caption, 
            hashtags, storyboard_id, engagement_score
        FROM public.scheduled_posts
        WHERE id = :original_id AND org_id = :org_id
    """)
    
    result = await db.execute(query, {"original_id": original_post_id, "org_id": org_id})
    original = result.fetchone()
    
    if not original:
        raise ValueError(f"Original post {original_post_id} not found")
    
    # Create recycled post
    insert_query = text("""
        INSERT INTO public.scheduled_posts (
            org_id, user_id, platform, content_type, media_path, cloud_url,
            caption, hashtags, scheduled_for, status, is_recycled, 
            original_post_id, social_account_id, storyboard_id,
            created_at, updated_at
        ) VALUES (
            :org_id, :user_id, :platform, :content_type, :media_path, :cloud_url,
            :caption, CAST(:hashtags AS jsonb), :scheduled_for, 'scheduled', true,
            :original_post_id, :account_id, :storyboard_id,
            :now, :now
        )
        RETURNING id
    """)
    
    now = datetime.now(timezone.utc)
    final_caption = caption_variation or original.caption
    
    result = await db.execute(insert_query, {
        "org_id": org_id,
        "user_id": user_id,
        "platform": original.platform,
        "content_type": original.content_type,
        "media_path": original.media_path,
        "cloud_url": original.cloud_url,
        "caption": final_caption,
        "hashtags": json.dumps(original.hashtags or []),
        "scheduled_for": scheduled_for,
        "original_post_id": original_post_id,
        "account_id": account_id,
        "storyboard_id": original.storyboard_id,
        "now": now
    })
    
    recycle_id = result.scalar()
    
    # Update original post recycle count
    update_query = text("""
        UPDATE public.scheduled_posts 
        SET recycle_count = recycle_count + 1, updated_at = :now
        WHERE id = :original_id
    """)
    
    await db.execute(update_query, {"original_id": original_post_id, "now": now})
    await db.commit()
    
    logger.info(f"Created recycled post {recycle_id} from original {original_post_id}")
    return recycle_id


async def should_recycle_now(
    db: AsyncSession,
    org_id: int,
    account_id: Optional[int] = None,
    cadence_every_n_posts: int = 10
) -> bool:
    """
    Check if it's time to recycle content based on posting cadence.
    
    Args:
        db: Database session
        org_id: Organization ID
        account_id: Specific account ID (optional)
        cadence_every_n_posts: Recycle every N new posts
        
    Returns:
        True if it's time to recycle
    """
    # Count recent posts (last 30 days) and recycled posts ratio
    query = text("""
        WITH recent_posts AS (
            SELECT 
                COUNT(*) as total_posts,
                COUNT(*) FILTER (WHERE is_recycled = true) as recycled_posts
            FROM public.scheduled_posts
            WHERE 
                org_id = :org_id
                AND (:account_id IS NULL OR social_account_id = :account_id)
                AND created_at >= :since_date
        ),
        latest_posts AS (
            SELECT COUNT(*) as recent_new_posts
            FROM (
                SELECT id 
                FROM public.scheduled_posts
                WHERE 
                    org_id = :org_id
                    AND (:account_id IS NULL OR social_account_id = :account_id)
                    AND is_recycled = false
                    AND status IN ('scheduled', 'published')
                ORDER BY created_at DESC
                LIMIT :cadence
            ) recent
        )
        SELECT 
            rp.total_posts,
            rp.recycled_posts,
            lp.recent_new_posts,
            (rp.recycled_posts::float / NULLIF(rp.total_posts, 0)) as recycle_ratio
        FROM recent_posts rp, latest_posts lp
    """)
    
    since_date = datetime.now(timezone.utc) - timedelta(days=30)
    
    result = await db.execute(query, {
        "org_id": org_id,
        "account_id": account_id,
        "since_date": since_date,
        "cadence": cadence_every_n_posts
    })
    
    row = result.fetchone()
    if not row:
        return False
    
    # Recycle if:
    # 1. We've posted N new posts since last recycle check
    # 2. Recycle ratio is below 20% (don't over-recycle)
    recycle_ratio = row.recycle_ratio or 0
    should_recycle = (
        row.recent_new_posts >= cadence_every_n_posts and
        recycle_ratio < 0.2 and
        row.total_posts > 5  # Need some content to recycle
    )
    
    logger.info(f"Recycle check for org {org_id}, account {account_id}: "
               f"ratio={recycle_ratio:.2f}, recent={row.recent_new_posts}, "
               f"should_recycle={should_recycle}")
    
    return should_recycle


async def auto_schedule_recycle(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    account_id: Optional[int] = None
) -> Optional[int]:
    """
    Automatically pick best content and schedule for recycling.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID for the recycle
        account_id: Specific account to recycle for
        
    Returns:
        ID of scheduled recycled post, or None if no suitable content
    """
    # Get account platform if specific account provided
    platform = None
    if account_id:
        platform_query = text("""
            SELECT platform FROM crm.social_accounts 
            WHERE id = :account_id AND org_id = :org_id
        """)
        result = await db.execute(platform_query, {"account_id": account_id, "org_id": org_id})
        row = result.fetchone()
        if row:
            platform = row.platform
    
    # Find top recyclable content
    recyclable = await get_recyclable_content(
        db=db,
        org_id=org_id,
        platform=platform or "instagram",  # Default to Instagram
        min_engagement=0.3,  # Lower threshold for auto-recycle
        limit=3
    )
    
    if not recyclable:
        logger.info(f"No recyclable content found for org {org_id}")
        return None
    
    # Pick the highest-scoring post that hasn't been recycled too much
    best_post = None
    for post in recyclable:
        if post["recycle_count"] < 3:  # Max 3 recycles per post
            best_post = post
            break
    
    if not best_post:
        logger.info(f"No suitable content for auto-recycle (all content over-recycled)")
        return None
    
    # Schedule for optimal time (next week, peak hours)
    from .optimal_timing import suggest_next_slot
    
    next_slot = await suggest_next_slot(
        db=db,
        org_id=org_id,
        account_id=account_id,
        content_type=best_post["content_type"]
    )
    
    # Create recycled post
    recycled_id = await create_recycled_post(
        db=db,
        org_id=org_id,
        user_id=user_id,
        original_post_id=best_post["id"],
        account_id=account_id,
        scheduled_for=next_slot
    )
    
    logger.info(f"Auto-scheduled recycle {recycled_id} from post {best_post['id']} "
               f"for {next_slot.isoformat()}")
    
    return recycled_id


def _calculate_recycling_potential(post_row) -> str:
    """Calculate recycling potential based on engagement and age."""
    engagement = float(post_row.engagement_score or 0)
    recycle_count = post_row.recycle_count or 0
    
    if engagement >= 0.8 and recycle_count < 2:
        return "high"
    elif engagement >= 0.5 and recycle_count < 3:
        return "medium"
    elif engagement >= 0.3 and recycle_count < 2:
        return "low"
    else:
        return "not_recommended"