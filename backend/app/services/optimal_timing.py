"""Optimal Timing Service — Data-driven posting schedule optimization.

Analyzes past performance to identify peak engagement windows and suggests
optimal posting times for maximum reach and interaction.
"""

import logging
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Platform-specific optimal times (fallback when no data available)
PLATFORM_PEAK_TIMES = {
    "instagram": [
        {"hour": 9, "minute": 0, "day_weight": {"1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 0.9, "6": 0.7, "0": 0.6}},
        {"hour": 14, "minute": 0, "day_weight": {"1": 0.9, "2": 0.9, "3": 0.9, "4": 0.9, "5": 1.0, "6": 0.8, "0": 0.7}},
        {"hour": 19, "minute": 30, "day_weight": {"1": 0.8, "2": 0.8, "3": 0.8, "4": 0.8, "5": 0.9, "6": 1.0, "0": 1.0}}
    ],
    "tiktok": [
        {"hour": 8, "minute": 0, "day_weight": {"1": 0.9, "2": 0.9, "3": 0.9, "4": 0.9, "5": 0.9, "6": 1.0, "0": 1.0}},
        {"hour": 12, "minute": 0, "day_weight": {"1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 1.0, "6": 0.9, "0": 0.8}},
        {"hour": 20, "minute": 0, "day_weight": {"1": 0.8, "2": 0.8, "3": 0.8, "4": 0.8, "5": 0.9, "6": 1.0, "0": 1.0}}
    ],
    "facebook": [
        {"hour": 10, "minute": 0, "day_weight": {"1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 0.9, "6": 0.8, "0": 0.7}},
        {"hour": 15, "minute": 0, "day_weight": {"1": 0.9, "2": 0.9, "3": 0.9, "4": 0.9, "5": 1.0, "6": 0.9, "0": 0.8}},
        {"hour": 21, "minute": 0, "day_weight": {"1": 0.7, "2": 0.7, "3": 0.7, "4": 0.7, "5": 0.8, "6": 1.0, "0": 0.9}}
    ],
    "youtube": [
        {"hour": 11, "minute": 0, "day_weight": {"1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 0.9, "6": 0.8, "0": 0.8}},
        {"hour": 16, "minute": 0, "day_weight": {"1": 0.8, "2": 0.8, "3": 0.8, "4": 0.8, "5": 0.9, "6": 1.0, "0": 0.9}},
        {"hour": 20, "minute": 30, "day_weight": {"1": 0.7, "2": 0.7, "3": 0.7, "4": 0.7, "5": 0.8, "6": 1.0, "0": 1.0}}
    ]
}


async def get_best_posting_times(
    db: AsyncSession,
    org_id: int,
    platform: str,
    account_id: Optional[int] = None,
    days_lookback: int = 90
) -> List[Dict]:
    """
    Analyze past performance to find peak engagement windows.
    
    Args:
        db: Database session
        org_id: Organization ID
        platform: Platform to analyze
        account_id: Specific account (optional)
        days_lookback: Days of history to analyze
        
    Returns:
        List of optimal time windows with engagement scores
    """
    # Try to get data-driven insights first
    data_driven = await _get_data_driven_times(
        db=db,
        org_id=org_id,
        platform=platform,
        account_id=account_id,
        days_lookback=days_lookback
    )
    
    if data_driven and len(data_driven) >= 3:
        logger.info(f"Using data-driven optimal times for {platform}")
        return data_driven
    
    # Fall back to platform defaults
    logger.info(f"Using default optimal times for {platform} (insufficient data)")
    return _get_platform_default_times(platform)


async def suggest_next_slot(
    db: AsyncSession,
    org_id: int,
    account_id: Optional[int] = None,
    content_type: str = "video",
    days_ahead: int = 7
) -> datetime:
    """
    Suggest the next best time slot for posting.
    
    Args:
        db: Database session
        org_id: Organization ID
        account_id: Specific account (optional)
        content_type: Type of content being posted
        days_ahead: Look ahead this many days
        
    Returns:
        Suggested posting datetime
    """
    # Get platform for account
    platform = "instagram"  # Default
    if account_id:
        platform_query = text("""
            SELECT platform FROM crm.social_accounts 
            WHERE id = :account_id AND org_id = :org_id
        """)
        result = await db.execute(platform_query, {"account_id": account_id, "org_id": org_id})
        row = result.fetchone()
        if row:
            platform = row.platform.lower()
    
    # Get optimal times for platform
    optimal_times = await get_best_posting_times(
        db=db,
        org_id=org_id,
        platform=platform,
        account_id=account_id
    )
    
    # Find next available slot that's not already taken
    now = datetime.now(timezone.utc)
    for day_offset in range(days_ahead):
        check_date = now + timedelta(days=day_offset)
        
        for time_slot in optimal_times:
            candidate = datetime.combine(
                check_date.date(),
                time(hour=time_slot["hour"], minute=time_slot["minute"])
            ).replace(tzinfo=timezone.utc)
            
            # Skip past times
            if candidate <= now:
                continue
            
            # Check if slot is available
            is_available = await _is_slot_available(
                db=db,
                org_id=org_id,
                account_id=account_id,
                candidate_time=candidate,
                buffer_minutes=30
            )
            
            if is_available:
                # Apply day-of-week weighting
                day_weight = time_slot["day_weight"].get(str(candidate.weekday()), 1.0)
                if day_weight >= 0.8:  # Only suggest high-weight days
                    logger.info(f"Suggested slot: {candidate.isoformat()} "
                               f"(weight: {day_weight:.2f})")
                    return candidate
    
    # Fallback: next weekday at 2 PM
    fallback = now + timedelta(days=1)
    while fallback.weekday() >= 5:  # Skip weekends
        fallback += timedelta(days=1)
    
    return fallback.replace(hour=14, minute=0, second=0, microsecond=0)


async def get_engagement_heatmap(
    db: AsyncSession,
    org_id: int,
    platform: str,
    days: int = 30
) -> Dict:
    """
    Generate hour-by-day engagement heatmap data.
    
    Args:
        db: Database session
        org_id: Organization ID
        platform: Platform to analyze
        days: Days of history to include
        
    Returns:
        Heatmap data with engagement scores by hour and day
    """
    query = text("""
        SELECT 
            EXTRACT(DOW FROM published_at) as day_of_week,
            EXTRACT(HOUR FROM published_at) as hour,
            AVG(engagement_score) as avg_engagement,
            COUNT(*) as post_count
        FROM public.scheduled_posts
        WHERE 
            org_id = :org_id
            AND platform = :platform
            AND published_at IS NOT NULL
            AND published_at >= :since_date
            AND engagement_score > 0
        GROUP BY 
            EXTRACT(DOW FROM published_at),
            EXTRACT(HOUR FROM published_at)
        HAVING COUNT(*) >= 2  -- At least 2 posts for reliable data
        ORDER BY day_of_week, hour
    """)
    
    since_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(query, {
        "org_id": org_id,
        "platform": platform,
        "since_date": since_date
    })
    
    # Build heatmap structure
    heatmap = {
        "platform": platform,
        "days_analyzed": days,
        "data": {}
    }
    
    # Initialize grid (7 days x 24 hours)
    for day in range(7):
        heatmap["data"][day] = {}
        for hour in range(24):
            heatmap["data"][day][hour] = {
                "engagement": 0.0,
                "post_count": 0,
                "confidence": "none"
            }
    
    # Fill with actual data
    for row in result.fetchall():
        day = int(row.day_of_week)
        hour = int(row.hour)
        engagement = float(row.avg_engagement)
        count = int(row.post_count)
        
        confidence = "low" if count < 5 else "medium" if count < 10 else "high"
        
        heatmap["data"][day][hour] = {
            "engagement": engagement,
            "post_count": count,
            "confidence": confidence
        }
    
    return heatmap


async def _get_data_driven_times(
    db: AsyncSession,
    org_id: int,
    platform: str,
    account_id: Optional[int],
    days_lookback: int
) -> List[Dict]:
    """Get optimal times based on actual performance data."""
    query = text("""
        SELECT 
            EXTRACT(HOUR FROM published_at) as hour,
            AVG(engagement_score) as avg_engagement,
            COUNT(*) as post_count
        FROM public.scheduled_posts
        WHERE 
            org_id = :org_id
            AND platform = :platform
            AND (:account_id IS NULL OR social_account_id = :account_id)
            AND published_at >= :since_date
            AND engagement_score > 0
        GROUP BY EXTRACT(HOUR FROM published_at)
        HAVING COUNT(*) >= 5  -- Need at least 5 posts per hour for reliability
        ORDER BY avg_engagement DESC
        LIMIT 5
    """)
    
    since_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
    
    result = await db.execute(query, {
        "org_id": org_id,
        "platform": platform,
        "account_id": account_id,
        "since_date": since_date
    })
    
    times = []
    for row in result.fetchall():
        hour = int(row.hour)
        engagement = float(row.avg_engagement)
        count = int(row.post_count)
        
        # Calculate confidence and day weights based on performance
        confidence = min(1.0, count / 20.0)  # Max confidence at 20+ posts
        
        times.append({
            "hour": hour,
            "minute": 0,
            "engagement_score": engagement,
            "post_count": count,
            "confidence": confidence,
            "day_weight": {"0": 0.9, "1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 0.8, "6": 0.8}
        })
    
    return times


def _get_platform_default_times(platform: str) -> List[Dict]:
    """Get default optimal times for platform."""
    defaults = PLATFORM_PEAK_TIMES.get(platform.lower(), PLATFORM_PEAK_TIMES["instagram"])
    
    return [{
        "hour": slot["hour"],
        "minute": slot["minute"],
        "engagement_score": 0.7,  # Default medium engagement
        "post_count": 0,
        "confidence": 0.5,  # Medium confidence
        "day_weight": slot["day_weight"],
        "source": "platform_default"
    } for slot in defaults]


async def _is_slot_available(
    db: AsyncSession,
    org_id: int,
    account_id: Optional[int],
    candidate_time: datetime,
    buffer_minutes: int = 30
) -> bool:
    """Check if a time slot is available (not already scheduled)."""
    start_buffer = candidate_time - timedelta(minutes=buffer_minutes)
    end_buffer = candidate_time + timedelta(minutes=buffer_minutes)
    
    query = text("""
        SELECT COUNT(*) 
        FROM public.scheduled_posts
        WHERE 
            org_id = :org_id
            AND (:account_id IS NULL OR social_account_id = :account_id)
            AND status IN ('scheduled', 'publishing')
            AND scheduled_for BETWEEN :start_time AND :end_time
    """)
    
    result = await db.execute(query, {
        "org_id": org_id,
        "account_id": account_id,
        "start_time": start_buffer,
        "end_time": end_buffer
    })
    
    count = result.scalar()
    return count == 0