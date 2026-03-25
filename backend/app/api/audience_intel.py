"""Enhanced audience intelligence API with commenter profiles and cross-competitor analysis."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import Counter

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id
from app.models.crm.audience_profile import AudienceProfile
from app.models.crm.competitor import Competitor
# audience_psychology removed - replaced with audience_intelligence
from app.services.audience_deduplication import audience_deduplicator
from app.services.comment_analyzer import analyze_comments_ml

logger = logging.getLogger(__name__)
router = APIRouter()


class TopEngager(BaseModel):
    """Top audience member by interaction count."""
    username: str
    profile_url: Optional[str] = None
    interaction_count: int
    engagement_level: str
    first_seen_at: datetime
    last_seen_at: datetime
    followers: Optional[int] = None
    is_verified: bool = False
    is_business: bool = False
    competitors_engaged_with: List[str] = Field(default_factory=list)


class CrossCompetitorOverlap(BaseModel):
    """Audience member who engages with multiple competitors."""
    username: str
    profile_url: Optional[str] = None
    competitors: List[str]
    total_interactions: int
    engagement_level: str
    profile_summary: Optional[str] = None


class AudienceIntelSummaryResponse(BaseModel):
    """Enhanced audience intelligence summary with commenter profiles."""
    top_engagers: List[TopEngager]
    cross_competitor_overlap: List[CrossCompetitorOverlap]
    engagement_distribution: Dict[str, int]
    comment_sentiment_by_commenter: Dict[str, Dict[str, int]]
    top_content_creators: List[TopEngager]  # High follower count commenters
    total_unique_commenters: int
    total_interactions_analyzed: int


@router.get("/api/audience-intel/summary", response_model=AudienceIntelSummaryResponse)
async def get_audience_intel_summary(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Enhanced audience intelligence API with commenter profiles and cross-competitor analysis."""
    org_id = get_org_id(request)
    
    try:
        # Get top 20 most active commenters
        top_engagers_result = await db.execute(
            select(AudienceProfile)
            .where(AudienceProfile.org_id == org_id)
            .order_by(AudienceProfile.interaction_count.desc())
            .limit(20)
        )
        top_engagers = top_engagers_result.scalars().all()
        
        # Get commenter overlap between competitors
        overlap_result = await db.execute(
            text("""
            WITH competitor_interactions AS (
                SELECT 
                    ap.username,
                    ap.profile_url,
                    ap.interaction_count,
                    ap.engagement_level,
                    ap.bio,
                    c.handle as competitor_handle,
                    COUNT(*) as interactions_with_competitor
                FROM crm.audience_profiles ap
                JOIN crm.competitor_posts cp ON ap.username = ANY(
                    SELECT DISTINCT commenter_username 
                    FROM crm.competitor_posts 
                    WHERE competitor_id = (
                        SELECT id FROM crm.competitors 
                        WHERE org_id = :org_id 
                        AND handle = c.handle 
                        LIMIT 1
                    )
                    AND commenter_username = ap.username
                )
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE ap.org_id = :org_id
                GROUP BY ap.username, ap.profile_url, ap.interaction_count, ap.engagement_level, ap.bio, c.handle
            ),
            multi_competitor_users AS (
                SELECT 
                    username,
                    profile_url,
                    SUM(interaction_count) as total_interactions,
                    MAX(engagement_level) as engagement_level,
                    MAX(bio) as bio,
                    ARRAY_AGG(DISTINCT competitor_handle) as competitors,
                    COUNT(DISTINCT competitor_handle) as competitor_count
                FROM competitor_interactions
                GROUP BY username, profile_url
                HAVING COUNT(DISTINCT competitor_handle) > 1
            )
            SELECT * FROM multi_competitor_users
            ORDER BY total_interactions DESC, competitor_count DESC
            LIMIT 15
            """),
            {"org_id": org_id}
        )
        overlap_data = overlap_result.fetchall()
        
        # Get engagement distribution
        distribution_result = await db.execute(
            select(
                AudienceProfile.engagement_level,
                func.count(AudienceProfile.id).label('count')
            )
            .where(AudienceProfile.org_id == org_id)
            .group_by(AudienceProfile.engagement_level)
        )
        distribution_raw = distribution_result.fetchall()
        engagement_distribution = {row.engagement_level: row.count for row in distribution_raw}
        
        # Get comment sentiment by commenter (from competitor_posts comments_data)
        sentiment_result = await db.execute(
            text("""
            SELECT 
                commenter_username,
                AVG(CASE WHEN (comments_data->>'sentiment') = 'positive' THEN 1 ELSE 0 END) as positive_rate,
                AVG(CASE WHEN (comments_data->>'sentiment') = 'negative' THEN 1 ELSE 0 END) as negative_rate,
                COUNT(*) as comment_count
            FROM crm.competitor_posts 
            WHERE org_id = :org_id 
              AND commenter_username IS NOT NULL 
              AND comments_data IS NOT NULL
            GROUP BY commenter_username
            HAVING COUNT(*) >= 3
            ORDER BY COUNT(*) DESC
            LIMIT 50
            """),
            {"org_id": org_id}
        )
        sentiment_raw = sentiment_result.fetchall()
        
        # Get top content creators (commenters with high follower counts)
        content_creators_result = await db.execute(
            select(AudienceProfile)
            .where(
                AudienceProfile.org_id == org_id,
                AudienceProfile.followers.is_not(None),
                AudienceProfile.followers >= 1000  # At least 1K followers
            )
            .order_by(AudienceProfile.followers.desc())
            .limit(10)
        )
        content_creators = content_creators_result.scalars().all()
        
        # Get total stats
        total_stats_result = await db.execute(
            select(
                func.count(AudienceProfile.id).label('total_commenters'),
                func.sum(AudienceProfile.interaction_count).label('total_interactions')
            )
            .where(AudienceProfile.org_id == org_id)
        )
        total_stats = total_stats_result.first()
        
        # Build response
        top_engagers_list = []
        for engager in top_engagers:
            # Get competitors they've engaged with
            competitor_result = await db.execute(
                text("""
                SELECT DISTINCT c.handle
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE cp.commenter_username = :username
                  AND c.org_id = :org_id
                """),
                {"username": engager.username, "org_id": org_id}
            )
            competitors_engaged = [row[0] for row in competitor_result.fetchall()]
            
            top_engagers_list.append(TopEngager(
                username=engager.username,
                profile_url=engager.profile_url,
                interaction_count=engager.interaction_count,
                engagement_level=engager.engagement_level,
                first_seen_at=engager.first_seen_at,
                last_seen_at=engager.last_seen_at,
                followers=engager.followers,
                is_verified=engager.is_verified,
                is_business=engager.is_business,
                competitors_engaged_with=competitors_engaged
            ))
        
        cross_competitor_list = []
        for row in overlap_data:
            cross_competitor_list.append(CrossCompetitorOverlap(
                username=row.username,
                profile_url=row.profile_url,
                competitors=list(row.competitors),
                total_interactions=int(row.total_interactions),
                engagement_level=row.engagement_level,
                profile_summary=row.bio[:100] + "..." if row.bio and len(row.bio) > 100 else row.bio
            ))
        
        comment_sentiment_by_commenter = {}
        for row in sentiment_raw:
            username = row.commenter_username
            comment_sentiment_by_commenter[username] = {
                "positive": round(float(row.positive_rate) * 100, 1),
                "negative": round(float(row.negative_rate) * 100, 1),
                "neutral": round((1 - float(row.positive_rate) - float(row.negative_rate)) * 100, 1),
                "comment_count": int(row.comment_count)
            }
        
        top_content_creators_list = []
        for creator in content_creators:
            # Get competitors they've engaged with
            competitor_result = await db.execute(
                text("""
                SELECT DISTINCT c.handle
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE cp.commenter_username = :username
                  AND c.org_id = :org_id
                """),
                {"username": creator.username, "org_id": org_id}
            )
            competitors_engaged = [row[0] for row in competitor_result.fetchall()]
            
            top_content_creators_list.append(TopEngager(
                username=creator.username,
                profile_url=creator.profile_url,
                interaction_count=creator.interaction_count,
                engagement_level=creator.engagement_level,
                first_seen_at=creator.first_seen_at,
                last_seen_at=creator.last_seen_at,
                followers=creator.followers,
                is_verified=creator.is_verified,
                is_business=creator.is_business,
                competitors_engaged_with=competitors_engaged
            ))
        
        return AudienceIntelSummaryResponse(
            top_engagers=top_engagers_list,
            cross_competitor_overlap=cross_competitor_list,
            engagement_distribution=engagement_distribution,
            comment_sentiment_by_commenter=comment_sentiment_by_commenter,
            top_content_creators=top_content_creators_list,
            total_unique_commenters=total_stats.total_commenters or 0,
            total_interactions_analyzed=total_stats.total_interactions or 0
        )
        
    except Exception as e:
        logger.error("Failed to get audience intel summary: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get audience intelligence summary")