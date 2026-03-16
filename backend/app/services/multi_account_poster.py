"""Multi-Account Posting Service — Coordinated content distribution.

Manages posting across multiple social accounts with intelligent timing,
cadence control, and cross-platform content adaptation.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_posting_accounts(
    db: AsyncSession,
    org_id: int,
    platform: Optional[str] = None,
    active_only: bool = True
) -> List[Dict]:
    """
    List all connected social accounts available for posting.
    
    Args:
        db: Database session
        org_id: Organization ID
        platform: Filter by platform (optional)
        active_only: Only return active accounts
        
    Returns:
        List of social accounts with posting metadata
    """
    where_clauses = ["org_id = :org_id"]
    params = {"org_id": org_id}
    
    if platform:
        where_clauses.append("platform = :platform")
        params["platform"] = platform
    
    if active_only:
        where_clauses.append("status = 'connected'")
    
    query = text(f"""
        SELECT 
            id,
            platform,
            username,
            profile_url,
            follower_count,
            following_count,
            post_count,
            connected_at,
            last_synced,
            status
        FROM crm.social_accounts
        WHERE {' AND '.join(where_clauses)}
        ORDER BY platform, username
    """)
    
    result = await db.execute(query, params)
    
    accounts = []
    for row in result.fetchall():
        # Get posting cadence and recent activity
        cadence = await get_account_cadence(db, org_id, row.id)
        recent_posts = await _get_recent_post_count(db, org_id, row.id, days=7)
        
        accounts.append({
            "id": row.id,
            "platform": row.platform,
            "username": row.username,
            "profile_url": row.profile_url,
            "follower_count": row.follower_count or 0,
            "following_count": row.following_count or 0,
            "post_count": row.post_count or 0,
            "connected_at": row.connected_at.isoformat() if row.connected_at else None,
            "last_synced": row.last_synced.isoformat() if row.last_synced else None,
            "status": row.status,
            "cadence": cadence,
            "recent_posts": recent_posts,
            "posting_capacity": _calculate_posting_capacity(cadence, recent_posts)
        })
    
    return accounts


async def distribute_content(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    content: Dict,
    accounts: List[int],
    schedule_strategy: str = "staggered"
) -> List[int]:
    """
    Distribute one piece of content across multiple accounts with staggered timing.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID creating the posts
        content: Content to distribute (media_path, caption, etc.)
        accounts: List of account IDs to post to
        schedule_strategy: "staggered", "simultaneous", or "optimal"
        
    Returns:
        List of scheduled post IDs
    """
    from .optimal_timing import suggest_next_slot
    
    scheduled_posts = []
    base_time = datetime.utcnow()
    
    for i, account_id in enumerate(accounts):
        # Get account details
        account_query = text("""
            SELECT platform FROM crm.social_accounts 
            WHERE id = :account_id AND org_id = :org_id
        """)
        result = await db.execute(account_query, {"account_id": account_id, "org_id": org_id})
        account_row = result.fetchone()
        
        if not account_row:
            logger.warning(f"Account {account_id} not found, skipping")
            continue
        
        platform = account_row.platform.lower()
        
        # Calculate posting time based on strategy
        if schedule_strategy == "simultaneous":
            scheduled_for = base_time + timedelta(minutes=5)  # Small delay for processing
        elif schedule_strategy == "staggered":
            # Stagger by 2-4 hours between accounts
            stagger_hours = 2 + (i * 2)
            scheduled_for = base_time + timedelta(hours=stagger_hours)
        elif schedule_strategy == "optimal":
            # Use optimal timing service
            scheduled_for = await suggest_next_slot(
                db=db,
                org_id=org_id,
                account_id=account_id,
                content_type=content.get("content_type", "video")
            )
            # Add small offset for each account to avoid collisions
            scheduled_for += timedelta(minutes=i * 15)
        else:
            raise ValueError(f"Unknown schedule strategy: {schedule_strategy}")
        
        # Adapt content for platform
        adapted_content = _adapt_content_for_platform(content, platform)
        
        # Create scheduled post
        insert_query = text("""
            INSERT INTO public.scheduled_posts (
                org_id, user_id, platform, content_type, media_path, cloud_url,
                caption, hashtags, scheduled_for, status, social_account_id,
                storyboard_id, optimal_time_used, created_at, updated_at
            ) VALUES (
                :org_id, :user_id, :platform, :content_type, :media_path, :cloud_url,
                :caption, CAST(:hashtags AS jsonb), :scheduled_for, 'scheduled', :account_id,
                :storyboard_id, :optimal_time_used, :now, :now
            )
            RETURNING id
        """)
        
        now = datetime.utcnow()
        
        result = await db.execute(insert_query, {
            "org_id": org_id,
            "user_id": user_id,
            "platform": platform,
            "content_type": adapted_content["content_type"],
            "media_path": adapted_content["media_path"],
            "cloud_url": adapted_content.get("cloud_url"),
            "caption": adapted_content["caption"],
            "hashtags": json.dumps(adapted_content.get("hashtags", [])),
            "scheduled_for": scheduled_for,
            "account_id": account_id,
            "storyboard_id": content.get("storyboard_id"),
            "optimal_time_used": schedule_strategy == "optimal",
            "now": now
        })
        
        post_id = result.scalar()
        scheduled_posts.append(post_id)
        
        logger.info(f"Scheduled post {post_id} for account {account_id} "
                   f"at {scheduled_for.isoformat()}")
    
    await db.commit()
    
    return scheduled_posts


async def get_account_cadence(
    db: AsyncSession,
    org_id: int,
    account_id: int
) -> Dict:
    """
    Get posting cadence settings for an account.
    
    Args:
        db: Database session
        org_id: Organization ID
        account_id: Account ID
        
    Returns:
        Cadence configuration
    """
    # Check if cadence settings exist in a settings table
    # For now, return platform defaults
    platform_query = text("""
        SELECT platform FROM crm.social_accounts 
        WHERE id = :account_id AND org_id = :org_id
    """)
    result = await db.execute(platform_query, {"account_id": account_id, "org_id": org_id})
    row = result.fetchone()
    
    if not row:
        return _get_default_cadence("unknown")
    
    return _get_default_cadence(row.platform.lower())


async def set_account_cadence(
    db: AsyncSession,
    org_id: int,
    account_id: int,
    posts_per_day: float,
    recycle_every_n: int
) -> bool:
    """
    Configure posting cadence for an account.
    
    Args:
        db: Database session
        org_id: Organization ID
        account_id: Account ID
        posts_per_day: Target posts per day
        recycle_every_n: Recycle content every N new posts
        
    Returns:
        Success status
    """
    # TODO: Store in dedicated cadence settings table
    # For now, this would store in account metadata or a settings table
    
    logger.info(f"Cadence set for account {account_id}: "
               f"{posts_per_day} posts/day, recycle every {recycle_every_n}")
    
    # This is a placeholder - in production, you'd store these settings
    # in a dedicated table or as JSON metadata on the account
    
    return True


async def _get_recent_post_count(
    db: AsyncSession,
    org_id: int,
    account_id: int,
    days: int
) -> int:
    """Get count of recent posts for an account."""
    query = text("""
        SELECT COUNT(*) 
        FROM public.scheduled_posts
        WHERE 
            org_id = :org_id
            AND social_account_id = :account_id
            AND created_at >= :since_date
    """)
    
    since_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(query, {
        "org_id": org_id,
        "account_id": account_id,
        "since_date": since_date
    })
    
    return result.scalar() or 0


def _calculate_posting_capacity(cadence: Dict, recent_posts: int) -> Dict:
    """Calculate how much posting capacity is available."""
    target_per_week = cadence["posts_per_day"] * 7
    capacity_used = recent_posts / target_per_week if target_per_week > 0 else 0
    
    return {
        "target_weekly": target_per_week,
        "posted_this_week": recent_posts,
        "capacity_used": min(1.0, capacity_used),
        "remaining_capacity": max(0, target_per_week - recent_posts),
        "status": "overposting" if capacity_used > 1.2 else 
                 "at_capacity" if capacity_used > 0.9 else
                 "under_capacity"
    }


def _get_default_cadence(platform: str) -> Dict:
    """Get default posting cadence for platform."""
    defaults = {
        "instagram": {
            "posts_per_day": 1.5,
            "recycle_every_n": 12,
            "max_posts_per_day": 3,
            "min_hours_between": 4
        },
        "tiktok": {
            "posts_per_day": 2.0,
            "recycle_every_n": 10,
            "max_posts_per_day": 4,
            "min_hours_between": 3
        },
        "facebook": {
            "posts_per_day": 1.0,
            "recycle_every_n": 15,
            "max_posts_per_day": 2,
            "min_hours_between": 6
        },
        "youtube": {
            "posts_per_day": 0.5,
            "recycle_every_n": 8,
            "max_posts_per_day": 1,
            "min_hours_between": 24
        }
    }
    
    return defaults.get(platform, defaults["instagram"])


def _adapt_content_for_platform(content: Dict, platform: str) -> Dict:
    """Adapt content for specific platform requirements."""
    adapted = content.copy()
    
    # Platform-specific adaptations
    if platform == "tiktok":
        # TikTok prefers shorter captions
        if len(adapted["caption"]) > 300:
            adapted["caption"] = adapted["caption"][:297] + "..."
        
        # Add TikTok-specific hashtags if not present
        hashtags = adapted.get("hashtags", [])
        if not any("fyp" in tag.lower() for tag in hashtags):
            hashtags.append("#fyp")
            adapted["hashtags"] = hashtags
    
    elif platform == "instagram":
        # Instagram allows longer captions but has hashtag limits
        hashtags = adapted.get("hashtags", [])
        if len(hashtags) > 30:
            adapted["hashtags"] = hashtags[:30]
    
    elif platform == "facebook":
        # Facebook prefers more descriptive text
        caption = adapted["caption"]
        if len(caption) < 50 and not caption.endswith("."):
            adapted["caption"] = caption + "."
    
    elif platform == "youtube":
        # YouTube Shorts need specific formatting
        if "content_type" in adapted and adapted["content_type"] == "video":
            adapted["content_type"] = "short"  # Specify as YouTube Short
    
    return adapted