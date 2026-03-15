"""Performance Tracker Service — Content analytics and optimization.

Tracks how copycat content performs to improve future generation.
Provides viral pattern analysis and AI-powered recommendations.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ContentPerformance:
    """Content performance metrics snapshot."""
    post_id: int
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float
    watch_time_avg: float  # seconds
    hook_retention: float  # % who watch past 3 seconds
    is_viral: bool  # engagement_rate > threshold


async def record_metrics(db: AsyncSession, post_id: int, metrics: dict) -> None:
    """
    Store metrics snapshot for a published post.
    
    Args:
        db: Database session
        post_id: Post ID
        metrics: Performance metrics dictionary
    """
    logger.info(f"Recording metrics for post {post_id}")
    
    # Get org_id from the post
    post_query = text("""
        SELECT org_id FROM public.scheduled_posts 
        WHERE id = :post_id
    """)
    post_result = await db.execute(post_query, {"post_id": post_id})
    post_row = post_result.fetchone()
    
    if not post_row:
        logger.error(f"Post {post_id} not found")
        return
    
    org_id = post_row.org_id
    
    # Calculate derived metrics
    views = metrics.get("views", 0)
    likes = metrics.get("likes", 0)
    comments = metrics.get("comments", 0)
    shares = metrics.get("shares", 0)
    saves = metrics.get("saves", 0)
    
    engagement_rate = calculate_engagement_rate(views, likes, comments, shares, saves)
    viral_score = calculate_viral_score(metrics)
    
    # Insert metrics snapshot
    query = text("""
        INSERT INTO public.content_metrics (
            org_id, post_id, views, likes, comments, shares, saves,
            engagement_rate, watch_time_avg, hook_retention, viral_score,
            raw_data, snapshot_at
        ) VALUES (
            :org_id, :post_id, :views, :likes, :comments, :shares, :saves,
            :engagement_rate, :watch_time_avg, :hook_retention, :viral_score,
            CAST(:raw_data AS jsonb), NOW()
        )
    """)
    
    await db.execute(query, {
        "org_id": org_id,
        "post_id": post_id,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "engagement_rate": engagement_rate,
        "watch_time_avg": metrics.get("watch_time_avg", 0.0),
        "hook_retention": metrics.get("hook_retention", 0.0),
        "viral_score": viral_score,
        "raw_data": json.dumps(metrics)
    })
    
    await db.commit()
    logger.info(f"Metrics recorded for post {post_id} (viral_score: {viral_score})")


async def get_performance_history(
    db: AsyncSession, 
    org_id: int, 
    days: int = 30,
    platform: Optional[str] = None
) -> List[dict]:
    """
    Get all content performance for organization.
    
    Args:
        db: Database session
        org_id: Organization ID
        days: Number of days to look back
        platform: Optional platform filter
        
    Returns:
        List of performance records
    """
    logger.info(f"Getting performance history for org {org_id} ({days} days)")
    
    # Build dynamic WHERE clause
    conditions = [
        "m.org_id = :org_id",
        "m.snapshot_at >= :since_date"
    ]
    params = {
        "org_id": org_id,
        "since_date": datetime.now(timezone.utc) - timedelta(days=days)
    }
    
    if platform:
        conditions.append("p.platform = :platform")
        params["platform"] = platform
    
    where_clause = " AND ".join(conditions)
    
    query = text(f"""
        SELECT 
            m.post_id, m.views, m.likes, m.comments, m.shares, m.saves,
            m.engagement_rate, m.watch_time_avg, m.hook_retention, 
            m.viral_score, m.snapshot_at,
            p.platform, p.content_type, p.caption, p.published_at,
            p.storyboard_id
        FROM public.content_metrics m
        JOIN public.scheduled_posts p ON m.post_id = p.id
        WHERE {where_clause}
        ORDER BY m.snapshot_at DESC
    """)
    
    result = await db.execute(query, params)
    rows = result.fetchall()
    
    history = []
    for row in rows:
        history.append({
            "post_id": row.post_id,
            "platform": row.platform,
            "content_type": row.content_type,
            "caption": row.caption[:100] + "..." if len(row.caption) > 100 else row.caption,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "storyboard_id": row.storyboard_id,
            "views": row.views,
            "likes": row.likes,
            "comments": row.comments,
            "shares": row.shares,
            "saves": row.saves,
            "engagement_rate": float(row.engagement_rate),
            "watch_time_avg": float(row.watch_time_avg),
            "hook_retention": float(row.hook_retention),
            "viral_score": float(row.viral_score),
            "snapshot_at": row.snapshot_at.isoformat()
        })
    
    logger.info(f"Found {len(history)} performance records")
    return history


async def get_viral_patterns(db: AsyncSession, org_id: int) -> dict:
    """
    Analyze what makes content go viral for this organization.
    
    Args:
        db: Database session
        org_id: Organization ID
        
    Returns:
        Analysis of viral content patterns
    """
    logger.info(f"Analyzing viral patterns for org {org_id}")
    
    # Get viral content (top 20% by viral score)
    viral_query = text("""
        WITH ranked_content AS (
            SELECT 
                m.post_id, m.viral_score, m.engagement_rate, m.watch_time_avg,
                m.hook_retention, p.platform, p.caption, p.published_at,
                EXTRACT(HOUR FROM p.published_at) as publish_hour,
                LENGTH(p.caption) as caption_length,
                PERCENT_RANK() OVER (ORDER BY m.viral_score) as viral_rank
            FROM public.content_metrics m
            JOIN public.scheduled_posts p ON m.post_id = p.id
            WHERE m.org_id = :org_id
            AND p.published_at >= NOW() - INTERVAL '90 days'
        )
        SELECT *
        FROM ranked_content
        WHERE viral_rank >= 0.8  -- Top 20%
        ORDER BY viral_score DESC
    """)
    
    result = await db.execute(viral_query, {"org_id": org_id})
    viral_content = result.fetchall()
    
    if not viral_content:
        return {
            "viral_content_count": 0,
            "insights": ["Not enough data to analyze viral patterns"],
            "recommendations": ["Create more content to build pattern analysis"]
        }
    
    # Analyze patterns
    patterns = _analyze_viral_patterns(viral_content)
    
    # Get platform performance comparison
    platform_query = text("""
        SELECT 
            p.platform,
            COUNT(*) as post_count,
            AVG(m.viral_score) as avg_viral_score,
            AVG(m.engagement_rate) as avg_engagement_rate,
            AVG(m.hook_retention) as avg_hook_retention
        FROM public.content_metrics m
        JOIN public.scheduled_posts p ON m.post_id = p.id
        WHERE m.org_id = :org_id
        AND p.published_at >= NOW() - INTERVAL '90 days'
        GROUP BY p.platform
        ORDER BY avg_viral_score DESC
    """)
    
    platform_result = await db.execute(platform_query, {"org_id": org_id})
    platform_stats = platform_result.fetchall()
    
    return {
        "viral_content_count": len(viral_content),
        "patterns": patterns,
        "platform_performance": [
            {
                "platform": row.platform,
                "post_count": row.post_count,
                "avg_viral_score": round(float(row.avg_viral_score), 2),
                "avg_engagement_rate": round(float(row.avg_engagement_rate), 2),
                "avg_hook_retention": round(float(row.avg_hook_retention), 2)
            }
            for row in platform_stats
        ],
        "insights": patterns.get("insights", []),
        "recommendations": patterns.get("recommendations", [])
    }


def calculate_viral_score(metrics: dict) -> float:
    """
    Calculate 0-100 viral score based on engagement.
    
    Args:
        metrics: Performance metrics dictionary
        
    Returns:
        Viral score (0-100)
    """
    views = max(metrics.get("views", 0), 1)  # Avoid division by zero
    likes = metrics.get("likes", 0)
    comments = metrics.get("comments", 0)
    shares = metrics.get("shares", 0)
    saves = metrics.get("saves", 0)
    hook_retention = metrics.get("hook_retention", 0.0)
    
    # Engagement rate
    engagement_rate = (likes + comments + shares + saves) / views
    
    # Weighted score (shares and saves count more)
    weighted_engagement = (
        likes * 1.0 +
        comments * 2.0 +
        shares * 3.0 +
        saves * 2.5
    ) / views
    
    # Hook retention bonus
    retention_bonus = hook_retention * 0.3
    
    # Calculate score (0-100)
    raw_score = (weighted_engagement * 50) + (retention_bonus * 50)
    return min(100.0, max(0.0, raw_score))


def calculate_engagement_rate(views: int, likes: int, comments: int, shares: int, saves: int) -> float:
    """Calculate standard engagement rate."""
    if views == 0:
        return 0.0
    
    total_engagements = likes + comments + shares + saves
    return (total_engagements / views) * 100


async def get_content_recommendations(db: AsyncSession, org_id: int) -> List[dict]:
    """
    Get AI-powered recommendations based on performance data.
    
    Args:
        db: Database session
        org_id: Organization ID
        
    Returns:
        List of actionable recommendations
    """
    logger.info(f"Generating content recommendations for org {org_id}")
    
    # Get recent performance data
    recent_query = text("""
        SELECT 
            p.platform,
            AVG(m.viral_score) as avg_viral_score,
            AVG(m.engagement_rate) as avg_engagement_rate,
            AVG(m.hook_retention) as avg_hook_retention,
            AVG(m.watch_time_avg) as avg_watch_time,
            COUNT(*) as post_count
        FROM public.content_metrics m
        JOIN public.scheduled_posts p ON m.post_id = p.id
        WHERE m.org_id = :org_id
        AND p.published_at >= NOW() - INTERVAL '30 days'
        GROUP BY p.platform
    """)
    
    result = await db.execute(recent_query, {"org_id": org_id})
    platform_data = result.fetchall()
    
    recommendations = []
    
    for row in platform_data:
        platform = row.platform
        avg_viral = float(row.avg_viral_score)
        avg_engagement = float(row.avg_engagement_rate)
        avg_retention = float(row.avg_hook_retention)
        avg_watch_time = float(row.avg_watch_time)
        post_count = row.post_count
        
        # Platform-specific recommendations
        if avg_engagement < 2.0:
            recommendations.append({
                "type": "engagement",
                "platform": platform,
                "priority": "high",
                "title": f"Improve {platform} engagement",
                "description": f"Your {platform} engagement rate ({avg_engagement:.1f}%) is below average. Try more interactive content, stronger hooks, or trending topics.",
                "action": "Create content with clear calls-to-action and trending hashtags"
            })
        
        if avg_retention < 0.6:
            recommendations.append({
                "type": "hook",
                "platform": platform,
                "priority": "high",
                "title": f"Strengthen {platform} hooks",
                "description": f"Only {avg_retention*100:.0f}% viewers stay past 3 seconds. Your opening needs to be more compelling.",
                "action": "Start with a question, bold statement, or preview of what's coming"
            })
        
        if avg_watch_time < 10.0 and platform in ["tiktok", "youtube-shorts"]:
            recommendations.append({
                "type": "retention",
                "platform": platform,
                "priority": "medium",
                "title": f"Increase {platform} watch time",
                "description": f"Average watch time is {avg_watch_time:.1f}s. Longer retention boosts algorithm visibility.",
                "action": "Add visual changes every 2-3 seconds, use text overlays, create suspense"
            })
        
        if post_count < 5:
            recommendations.append({
                "type": "volume",
                "platform": platform,
                "priority": "medium",
                "title": f"Post more on {platform}",
                "description": f"Only {post_count} posts this month. Consistent posting improves algorithmic reach.",
                "action": "Aim for 3-5 posts per week on this platform"
            })
    
    # Overall recommendations
    if not recommendations:
        recommendations.append({
            "type": "optimization",
            "platform": "all",
            "priority": "low",
            "title": "Your content is performing well!",
            "description": "Keep doing what you're doing. Consider experimenting with new formats to find even higher performing content.",
            "action": "Test new content styles, formats, or trending topics"
        })
    
    logger.info(f"Generated {len(recommendations)} recommendations")
    return recommendations


def _analyze_viral_patterns(viral_content) -> dict:
    """Analyze patterns in viral content."""
    if not viral_content:
        return {"insights": [], "recommendations": []}
    
    # Analyze timing patterns
    publish_hours = [row.publish_hour for row in viral_content if row.publish_hour is not None]
    most_common_hour = max(set(publish_hours), key=publish_hours.count) if publish_hours else None
    
    # Analyze caption length patterns
    caption_lengths = [row.caption_length for row in viral_content if row.caption_length is not None]
    avg_caption_length = sum(caption_lengths) / len(caption_lengths) if caption_lengths else 0
    
    # Analyze platform patterns
    platforms = [row.platform for row in viral_content]
    platform_counts = {platform: platforms.count(platform) for platform in set(platforms)}
    top_platform = max(platform_counts, key=platform_counts.get) if platform_counts else None
    
    # Analyze engagement patterns
    avg_engagement = sum(row.engagement_rate for row in viral_content) / len(viral_content)
    avg_hook_retention = sum(row.hook_retention for row in viral_content) / len(viral_content)
    
    insights = []
    recommendations = []
    
    if most_common_hour is not None:
        insights.append(f"Viral content often posts around {most_common_hour}:00")
        recommendations.append(f"Schedule content between {most_common_hour-1}:00-{most_common_hour+1}:00 for best reach")
    
    if avg_caption_length > 0:
        if avg_caption_length < 50:
            insights.append("Viral content tends to have short captions")
            recommendations.append("Keep captions under 50 characters for maximum impact")
        elif avg_caption_length > 150:
            insights.append("Viral content tends to have detailed captions")
            recommendations.append("Include detailed descriptions and relevant hashtags")
    
    if top_platform:
        insights.append(f"{top_platform} generates the most viral content")
        recommendations.append(f"Focus content creation efforts on {top_platform}")
    
    if avg_hook_retention > 0.7:
        insights.append(f"Viral content has {avg_hook_retention*100:.0f}% hook retention")
        recommendations.append("Study your viral content hooks and replicate successful patterns")
    
    return {
        "timing": {
            "best_hour": most_common_hour,
            "hour_distribution": publish_hours
        },
        "content": {
            "avg_caption_length": round(avg_caption_length),
            "top_platform": top_platform,
            "platform_distribution": platform_counts
        },
        "performance": {
            "avg_engagement_rate": round(avg_engagement, 2),
            "avg_hook_retention": round(avg_hook_retention, 3)
        },
        "insights": insights,
        "recommendations": recommendations
    }