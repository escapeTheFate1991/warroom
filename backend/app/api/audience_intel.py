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
from app.services.audience_psychology import analyze_audience_psychology
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


class PsychologyAnalysisRequest(BaseModel):
    """Request model for behavioral psychology analysis."""
    competitor_id: int
    post_shortcode: Optional[str] = None  # Analyze specific post, or all posts if None
    include_related_competitors: bool = True  # Remove shared audience with related competitors
    min_comment_length: int = Field(default=10, ge=5)  # Minimum comment length for analysis
    max_profiles: int = Field(default=100, ge=10, le=500)  # Max psychological profiles to analyze


class PsychologyAnalysisResponse(BaseModel):
    """Comprehensive behavioral psychology analysis response."""
    analysis_metadata: Dict[str, Any]
    psychological_profiles: List[Dict[str, Any]]
    content_psychology: Dict[str, Any]
    behavioral_insights: Dict[str, Any] 
    sharing_psychology: Dict[str, Any]
    optimization_recommendations: List[Dict[str, str]]
    audience_uniqueness: Dict[str, Any]
    excluded_profiles: Dict[str, int]


@router.post("/api/audience-intel/psychology-analysis", response_model=PsychologyAnalysisResponse)
async def analyze_audience_psychology_endpoint(
    request: PsychologyAnalysisRequest,
    db_request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Deep behavioral psychology analysis of audience.
    
    Analyzes WHY people engage and share content, removes shared audience members,
    and provides insights for viral content creation.
    """
    org_id = get_org_id(db_request)
    
    try:
        # Get competitor details
        competitor_result = await db.execute(
            select(Competitor).where(
                Competitor.id == request.competitor_id,
                Competitor.org_id == org_id
            )
        )
        competitor = competitor_result.scalar_one_or_none()
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        # Get posts and comments for analysis
        if request.post_shortcode:
            # Analyze specific post
            posts_query = text("""
                SELECT id, post_text, likes, comments, engagement_score, 
                       post_url, posted_at, comment_analysis
                FROM crm.competitor_posts 
                WHERE competitor_id = :competitor_id 
                AND org_id = :org_id
                AND post_url LIKE :shortcode_pattern
                AND comment_analysis IS NOT NULL
                ORDER BY posted_at DESC
                LIMIT 1
            """)
            posts_result = await db.execute(posts_query, {
                "competitor_id": request.competitor_id,
                "org_id": org_id,
                "shortcode_pattern": f"%{request.post_shortcode}%"
            })
        else:
            # Analyze all recent posts
            posts_query = text("""
                SELECT id, post_text, likes, comments, engagement_score,
                       post_url, posted_at, comment_analysis
                FROM crm.competitor_posts 
                WHERE competitor_id = :competitor_id 
                AND org_id = :org_id
                AND comment_analysis IS NOT NULL
                AND posted_at >= NOW() - INTERVAL '30 days'
                ORDER BY engagement_score DESC
                LIMIT 5
            """)
            posts_result = await db.execute(posts_query, {
                "competitor_id": request.competitor_id,
                "org_id": org_id
            })
        
        posts = posts_result.fetchall()
        if not posts:
            raise HTTPException(
                status_code=404, 
                detail="No posts with comment analysis found"
            )
        
        # Aggregate comments from all selected posts
        all_comments = []
        post_captions = []
        post_metrics = {"total_likes": 0, "total_comments": 0}
        
        for post in posts:
            if post.comment_analysis and isinstance(post.comment_analysis, dict):
                # Extract raw comment data from the stored analysis
                stored_comments = post.comment_analysis.get("raw_comments", [])
                if stored_comments:
                    # Filter by minimum length
                    filtered_comments = [
                        comment for comment in stored_comments
                        if len(comment.get("text", "")) >= request.min_comment_length
                    ]
                    all_comments.extend(filtered_comments)
                
            if post.post_text:
                post_captions.append(post.post_text)
            
            post_metrics["total_likes"] += post.likes or 0
            post_metrics["total_comments"] += post.comments or 0
        
        if not all_comments:
            raise HTTPException(
                status_code=404,
                detail="No comments found matching minimum length criteria"
            )
        
        # Limit comments for performance
        if len(all_comments) > 1000:
            # Sort by likes and take top comments
            all_comments.sort(key=lambda c: c.get("likes", 0), reverse=True)
            all_comments = all_comments[:1000]
        
        logger.info(f"Analyzing {len(all_comments)} comments for competitor {request.competitor_id}")
        
        # Perform deep psychology analysis
        combined_caption = " ".join(post_captions)
        psychology_analysis = await analyze_audience_psychology(
            comments=all_comments,
            post_caption=combined_caption,
            creator_username=competitor.handle,
            post_metrics=post_metrics
        )
        
        # Get related competitors for deduplication
        related_competitor_ids = []
        if request.include_related_competitors:
            related_query = text("""
                SELECT id FROM crm.competitors 
                WHERE org_id = :org_id 
                AND id != :competitor_id
                AND (platform = :platform OR niche = :niche)
                LIMIT 10
            """)
            related_result = await db.execute(related_query, {
                "org_id": org_id,
                "competitor_id": request.competitor_id,
                "platform": competitor.platform,
                "niche": competitor.niche
            })
            related_competitor_ids = [row.id for row in related_result.fetchall()]
        
        # Apply audience deduplication
        deduplicated_analysis = await audience_deduplicator.deduplicate_audience_analysis(
            db=db,
            psychology_analysis=psychology_analysis,
            competitor_id=request.competitor_id,
            related_competitor_ids=related_competitor_ids
        )
        
        # Prepare response
        return PsychologyAnalysisResponse(
            analysis_metadata={
                "competitor_handle": competitor.handle,
                "competitor_platform": competitor.platform,
                "total_comments_analyzed": len(all_comments),
                "posts_analyzed": len(posts),
                "analysis_date": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "min_comment_length": request.min_comment_length,
                    "deduplication_enabled": request.include_related_competitors,
                    "related_competitors_checked": len(related_competitor_ids)
                }
            },
            psychological_profiles=deduplicated_analysis.get("psychological_profiles", [])[:request.max_profiles],
            content_psychology=deduplicated_analysis.get("content_psychology", {}),
            behavioral_insights=deduplicated_analysis.get("behavioral_insights", {}),
            sharing_psychology=deduplicated_analysis.get("sharing_psychology", {}),
            optimization_recommendations=deduplicated_analysis.get("optimization_recommendations", []),
            audience_uniqueness=deduplicated_analysis.get("audience_uniqueness", {}),
            excluded_profiles=deduplicated_analysis.get("excluded_profiles", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to analyze audience psychology: %s", e)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze audience psychology: {str(e)}"
        )


@router.get("/api/audience-intel/psychology-analysis/{competitor_id}/quick")
async def quick_psychology_analysis(
    competitor_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Quick psychology analysis for a competitor using existing comment analysis data.
    
    Returns simplified insights without full reprocessing.
    """
    org_id = get_org_id(request)
    
    try:
        # Get competitor
        competitor_result = await db.execute(
            select(Competitor).where(
                Competitor.id == competitor_id,
                Competitor.org_id == org_id
            )
        )
        competitor = competitor_result.scalar_one_or_none()
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        # Get existing comment analysis
        analysis_query = text("""
            SELECT comment_analysis, post_text, engagement_score, posted_at
            FROM crm.competitor_posts 
            WHERE competitor_id = :competitor_id 
            AND org_id = :org_id
            AND comment_analysis IS NOT NULL
            ORDER BY engagement_score DESC
            LIMIT 3
        """)
        
        result = await db.execute(analysis_query, {
            "competitor_id": competitor_id,
            "org_id": org_id
        })
        posts = result.fetchall()
        
        if not posts:
            return {
                "error": "No analyzed posts found",
                "recommendation": "Run full scraping and analysis first"
            }
        
        # Aggregate insights from existing analyses
        total_questions = 0
        total_pain_points = 0
        themes = Counter()
        content_gaps = []
        
        for post in posts:
            if post.comment_analysis:
                analysis = post.comment_analysis
                total_questions += len(analysis.get("questions", []))
                total_pain_points += len(analysis.get("pain_points", []))
                
                for theme in analysis.get("themes", []):
                    if isinstance(theme, dict):
                        themes[theme.get("theme", "")] += theme.get("count", 0)
                
                content_gaps.extend(analysis.get("content_gaps", []))
        
        # Simple psychological insights
        insights = {
            "competitor_handle": competitor.handle,
            "platform": competitor.platform,
            "posts_analyzed": len(posts),
            "engagement_signals": {
                "question_volume": total_questions,
                "pain_point_indicators": total_pain_points,
                "content_gap_opportunities": len(content_gaps)
            },
            "top_themes": dict(themes.most_common(5)),
            "quick_recommendations": []
        }
        
        # Generate quick recommendations
        if total_questions > total_pain_points * 2:
            insights["quick_recommendations"].append({
                "type": "Content Strategy",
                "insight": "High question volume - audience seeks educational content",
                "action": "Create tutorial and how-to content"
            })
        
        if total_pain_points > 10:
            insights["quick_recommendations"].append({
                "type": "Pain Point Addressing",
                "insight": "Significant pain points expressed",
                "action": "Create solution-focused content addressing common struggles"
            })
        
        if len(content_gaps) > 5:
            insights["quick_recommendations"].append({
                "type": "Content Gaps", 
                "insight": "Multiple unanswered questions identified",
                "action": "Fill content gaps with targeted responses"
            })
        
        return insights
        
    except Exception as e:
        logger.error("Failed quick psychology analysis: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed quick analysis: {str(e)}"
        )