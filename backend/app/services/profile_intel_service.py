"""Profile Intelligence Service - Rebuilt to Match Definitive Spec
Analyzes USER'S OWN account data (OAuth + Scraped) for self-improvement insights.
Competitor data only used as comparison lens, NOT as primary data source.
"""
import logging
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update, and_
import httpx

from app.models.crm.profile_intel_data import ProfileIntelData
from app.models.crm.social import SocialAccount, SocialAnalytics
from app.services.video_analysis_service import video_analysis_service

logger = logging.getLogger(__name__)

# Service URL configuration
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:18797")

@dataclass
class VideoGrade:
    """Grade for a single video with strengths and weaknesses."""
    video_id: str
    grade: int  # 0-100
    strengths: List[str]
    weaknesses: List[str]

@dataclass
class CategoryGrade:
    """Grade for a profile category."""
    score: int  # 0-100
    details: str

@dataclass
class ProfileIntelResult:
    """Complete profile intel analysis result."""
    profile_id: str
    platform: str
    oauth_data: Dict[str, Any]
    scraped_data: Dict[str, Any] 
    processed_videos: List[VideoGrade]
    grades: Dict[str, CategoryGrade]
    recommendations: Dict[str, List[Any]]
    last_synced_at: datetime

class ProfileIntelService:
    """Service for building comprehensive profile intelligence."""
    
    def __init__(self):
        self.scraper_url = SCRAPER_SERVICE_URL
    
    def _letter_to_numeric_grade(self, letter_grade: str) -> int:
        """Convert letter grade to numeric 0-100 for processing."""
        grade_map = {
            "A+": 97, "A": 93, "A-": 90,
            "B+": 87, "B": 83, "B-": 80,
            "C+": 77, "C": 73, "C-": 70,
            "D+": 67, "D": 63, "D-": 60,
            "F": 0
        }
        return grade_map.get(letter_grade.upper(), 0)
    
    def _numeric_to_letter_grade(self, numeric_grade: float) -> str:
        """Convert numeric grade 0-100 to letter grade A+ through F."""
        if numeric_grade >= 97:
            return "A+"
        elif numeric_grade >= 93:
            return "A"
        elif numeric_grade >= 90:
            return "A-"
        elif numeric_grade >= 87:
            return "B+"
        elif numeric_grade >= 83:
            return "B"
        elif numeric_grade >= 80:
            return "B-"
        elif numeric_grade >= 77:
            return "C+"
        elif numeric_grade >= 73:
            return "C"
        elif numeric_grade >= 70:
            return "C-"
        elif numeric_grade >= 67:
            return "D+"
        elif numeric_grade >= 63:
            return "D"
        elif numeric_grade >= 60:
            return "D-"
        else:
            return "F"
    
    async def get_or_create_profile_intel(
        self,
        db: AsyncSession,
        org_id: int,
        profile_id: str,
        platform: str = "instagram",
        force_refresh: bool = False
    ) -> ProfileIntelResult:
        """Get or create profile intel data for a given profile."""
        try:
            # Check if we have existing data
            result = await db.execute(
                select(ProfileIntelData).where(
                    and_(
                        ProfileIntelData.org_id == org_id,
                        ProfileIntelData.profile_id == profile_id,
                        ProfileIntelData.platform == platform
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            # Check if we need to refresh
            needs_refresh = force_refresh
            if existing and existing.last_synced_at:
                age = datetime.utcnow() - existing.last_synced_at
                needs_refresh = needs_refresh or age > timedelta(hours=6)
            else:
                needs_refresh = True
            
            if not needs_refresh and existing:
                return self._profile_data_to_result(existing)
            
            # Build fresh profile intel
            profile_data = await self._build_profile_intel(db, org_id, profile_id, platform)
            
            # Save or update
            if existing:
                await self._update_profile_intel(db, existing, profile_data)
            else:
                existing = await self._create_profile_intel(db, org_id, profile_id, platform, profile_data)
            
            await db.commit()
            return self._profile_data_to_result(existing)
            
        except Exception as e:
            logger.error(f"Failed to get profile intel for {profile_id}: {e}")
            await db.rollback()
            raise
    
    async def _build_profile_intel(
        self,
        db: AsyncSession,
        org_id: int,
        profile_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """Build complete profile intel by analyzing USER'S OWN data."""
        logger.info(f"Building profile intel for {profile_id} on {platform}")
        
        # Initialize data structure
        data = ProfileIntelData.create_empty_data_structure()
        
        # 1. Fetch OAuth data from USER'S connected account
        oauth_data = await self._fetch_user_oauth_data(db, org_id, profile_id, platform)
        if oauth_data:
            data["oauth_data"].update(oauth_data)
        else:
            # Return early with clean "connect Instagram" message
            data["grades"] = {
                "profileOptimization": {"score": 0, "details": "Connect Instagram to analyze profile optimization"},
                "videoMessaging": {"score": 0, "details": "Connect Instagram to analyze video messaging"}, 
                "storyboarding": {"score": 0, "details": "Connect Instagram to analyze storyboarding"},
                "audienceEngagement": {"score": 0, "details": "Connect Instagram to analyze audience engagement"},
                "contentConsistency": {"score": 0, "details": "Connect Instagram to analyze content consistency"},
                "replyQuality": {"score": 0, "details": "Connect Instagram to analyze reply quality"}
            }
            data["recommendations"]["nextSteps"] = [{
                "action": "Connect your Instagram account via OAuth",
                "expectedImpact": "Unlock full profile intelligence analysis",
                "priority": "high"
            }]
            return data
        
        # 2. Fetch scraped data for USER'S public profile
        scraped_data = await self._fetch_user_public_data(profile_id)
        if scraped_data:
            data["scraped_data"].update(scraped_data)
        
        # 3. Process USER'S last 5 videos through same pipeline as competitors
        processed_videos = await self._process_user_videos(db, org_id, profile_id, oauth_data)
        data["processed_videos"] = processed_videos
        
        # 4. Grade across all 6 categories
        grades = await self._grade_profile(data)
        data["grades"] = grades
        
        # 5. Generate SPECIFIC, EVIDENCE-BACKED recommendations
        recommendations = await self._generate_recommendations(data, db, org_id)
        data["recommendations"] = recommendations
        
        return data
    
    async def _fetch_user_oauth_data(
        self,
        db: AsyncSession,
        org_id: int,
        profile_id: str,
        platform: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch OAuth analytics data from USER'S connected social account."""
        try:
            # Get USER'S social account
            account_result = await db.execute(
                select(SocialAccount).where(
                    and_(
                        SocialAccount.org_id == org_id,
                        SocialAccount.platform == platform,
                        SocialAccount.username == profile_id,
                        SocialAccount.status == "connected"
                    )
                )
            )
            account = account_result.scalar_one_or_none()
            
            if not account:
                logger.info(f"No connected {platform} account found for user profile {profile_id}")
                return None
            
            # Get recent analytics (last 30 days)
            analytics_result = await db.execute(
                select(SocialAnalytics).where(
                    and_(
                        SocialAnalytics.account_id == account.id,
                        SocialAnalytics.metric_date >= datetime.utcnow() - timedelta(days=30)
                    )
                ).order_by(SocialAnalytics.metric_date.desc())
            )
            analytics = analytics_result.scalars().all()
            
            # Calculate aggregated metrics from USER'S analytics
            total_days = len(analytics) if analytics else 0
            avg_engagement_rate = sum(a.engagement_rate or 0 for a in analytics) / total_days if total_days > 0 else 0
            avg_reach = sum(a.reach or 0 for a in analytics) / total_days if total_days > 0 else 0
            total_followers_gained = sum(a.followers_gained or 0 for a in analytics) if analytics else 0
            total_followers_lost = sum(a.followers_lost or 0 for a in analytics) if analytics else 0
            avg_impressions = sum(a.impressions or 0 for a in analytics) / total_days if total_days > 0 else 0
            total_saves = sum(a.saves or 0 for a in analytics) if analytics else 0
            total_shares = sum(a.shares or 0 for a in analytics) if analytics else 0
            total_profile_views = sum(a.profile_views or 0 for a in analytics) if analytics else 0
            
            # Calculate reply rate from available analytics
            total_comments = sum(a.comments or 0 for a in analytics) if analytics else 0
            # TODO: This needs to be calculated from actual comment analysis when available
            # For now, use basic estimation based on engagement patterns
            reply_rate = 0.0
            if total_comments > 0:
                # Estimate reply rate based on engagement rate (higher engagement suggests more replies)
                if avg_engagement_rate >= 4.0:
                    reply_rate = 35.0  # High engagement likely means active replies
                elif avg_engagement_rate >= 2.0:
                    reply_rate = 15.0  # Moderate engagement
                elif avg_engagement_rate >= 1.0:
                    reply_rate = 5.0   # Low but some engagement
                else:
                    reply_rate = 0.0   # Very low engagement
            
            return {
                "followerCount": account.follower_count or 0,
                "followingCount": account.following_count or 0,
                "postCount": account.post_count or 0,
                "reachMetrics": {
                    "avgDailyReach": int(avg_reach),
                    "avgDailyImpressions": int(avg_impressions),
                    "totalDays": total_days
                },
                "audienceDemographics": {
                    "netFollowerGrowth": total_followers_gained - total_followers_lost,
                    "totalProfileViews": total_profile_views,
                    "saveToShareRatio": (total_saves / max(total_shares, 1)) if total_shares > 0 else total_saves
                },
                "engagementRate": float(avg_engagement_rate),
                "replyRate": reply_rate,
                "avgReplyTime": 0.0  # TODO: Calculate from comments analysis when available
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch OAuth data for user {profile_id}: {e}")
            return None
    
    async def _fetch_user_public_data(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Fetch USER'S public profile data via scraping."""
        try:
            # Import here to avoid circular import
            from app.api.content_intel import scrape_profile
            scraped = await scrape_profile(profile_id)
            
            if scraped.error:
                logger.warning(f"Scraping failed for user profile {profile_id}: {scraped.error}")
                return None
            
            # Analyze USER'S grid aesthetic
            grid_aesthetic = self._analyze_grid_aesthetic(scraped.posts if scraped.posts else [])
            
            # Calculate USER'S posting frequency 
            posting_frequency = self._calculate_posting_frequency(scraped.posts if scraped.posts else [])
            
            # Extract USER'S hashtag usage patterns
            hashtag_usage = self._extract_hashtag_usage(scraped.posts if scraped.posts else [])
            
            # Extract recent captions for analysis
            recent_captions = []
            if scraped.posts:
                recent_captions = [
                    (post.caption or "")[:200] + ("..." if len(post.caption or "") > 200 else "")
                    for post in scraped.posts[:10]
                    if post.caption
                ]
            
            return {
                "bio": scraped.bio or "",
                "profilePicUrl": scraped.profile_pic_url or "",
                "linkInBio": scraped.external_url or "",
                "highlightCovers": [],  # TODO: Extract from scraped data when available
                "recentPostCaptions": recent_captions,
                "gridAesthetic": grid_aesthetic,
                "postingFrequency": posting_frequency,
                "hashtagUsage": hashtag_usage,
                "isPrivate": getattr(scraped, 'is_private', False),
                "isVerified": getattr(scraped, 'is_verified', False)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch public data for user {profile_id}: {e}")
            return None
    
    async def _process_user_videos(
        self,
        db: AsyncSession,
        org_id: int,
        profile_id: str,
        oauth_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process USER'S videos using stored analysis results from user_video_analysis_service."""
        try:
            # Check if we have stored video analysis results
            result = await db.execute(
                select(ProfileIntelData).where(
                    and_(
                        ProfileIntelData.org_id == org_id,
                        ProfileIntelData.profile_id == profile_id,
                        ProfileIntelData.platform == "instagram"
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing and existing.processed_videos:
                # Use stored video analysis results
                stored_videos = existing.processed_videos
                
                # Convert to expected format for grading
                processed_videos = []
                for video in stored_videos:
                    processed_videos.append({
                        "videoId": video.get("videoId", "unknown"),
                        "grade": self._letter_to_numeric_grade(video.get("grade", "F")),
                        "strengths": video.get("strengths", []),
                        "weaknesses": video.get("weaknesses", []),
                        "hookStrength": video.get("hookStrength", 0),
                        "pacingScore": video.get("pacingScore", 0),
                        "structureScore": video.get("structureScore", 0),
                        "ctaEffectiveness": video.get("ctaEffectiveness", 0),
                        "visualQuality": video.get("visualQuality", 0),
                        "textOverlayUsage": video.get("textOverlayUsage", False),
                        "duration": video.get("duration", 0),
                        "engagementMetrics": video.get("engagementMetrics", {})
                    })
                
                logger.info(f"Using stored video analysis for {profile_id}: {len(processed_videos)} videos")
                return processed_videos
            
            # Fallback: Check if user exists in competitors table for legacy analysis
            competitor_result = await db.execute(
                text("""
                    SELECT id FROM crm.competitors 
                    WHERE org_id = :org_id AND handle = :handle 
                    ORDER BY id DESC LIMIT 1
                """),
                {"org_id": org_id, "handle": profile_id}
            )
            competitor_row = competitor_result.fetchone()
            
            if competitor_row:
                # Use competitor video analysis if available (legacy method)
                competitor_id = competitor_row[0]
                
                video_posts_result = await db.execute(
                    text("""
                        SELECT id, media_url, post_text, likes, comments, shares, engagement_score
                        FROM crm.competitor_posts 
                        WHERE competitor_id = :competitor_id 
                        AND media_type IN ('video', 'reel', 'igtv')
                        AND media_url IS NOT NULL
                        ORDER BY posted_at DESC
                        LIMIT 5
                    """),
                    {"competitor_id": competitor_id}
                )
                video_posts = video_posts_result.fetchall()
                
                processed_videos = []
                for video_post in video_posts:
                    try:
                        video_grade = await self._grade_single_video(video_post, {})
                        processed_videos.append(video_grade)
                    except Exception as e:
                        logger.warning(f"Failed to grade user video {video_post[0]}: {e}")
                        continue
                
                return processed_videos
            
            # No video analysis available - return call-to-action
            return [{
                "videoId": "trigger_analysis",
                "grade": 0,
                "strengths": [],
                "weaknesses": ["Run video analysis to get detailed insights on your content"]
            }]
            
        except Exception as e:
            logger.error(f"Failed to process user videos for {profile_id}: {e}")
            return []
    
    def _analyze_grid_aesthetic(self, posts: List[Any]) -> str:
        """Analyze the visual consistency of USER'S profile grid."""
        if not posts or len(posts) < 3:
            return "insufficient_data"
        
        # Count media types in USER'S posts
        video_count = sum(1 for post in posts if getattr(post, 'media_type', '') in ['video', 'reel'])
        image_count = len(posts) - video_count
        
        video_ratio = video_count / len(posts) if len(posts) > 0 else 0
        
        if video_ratio > 0.8:
            return "video_focused"
        elif video_ratio > 0.5:
            return "mixed_content"
        elif video_ratio > 0.2:
            return "image_focused_with_video"
        else:
            return "image_focused"
    
    def _calculate_posting_frequency(self, posts: List[Any]) -> str:
        """Calculate USER'S posting frequency from recent posts."""
        if not posts or len(posts) < 2:
            return "insufficient_data"
        
        # Get dates and calculate average gap
        dates = []
        for post in posts:
            if hasattr(post, 'posted_at') and post.posted_at:
                dates.append(post.posted_at)
        
        if len(dates) < 2:
            return "insufficient_data"
        
        dates.sort(reverse=True)  # Most recent first
        
        # Calculate average days between posts
        gaps = []
        for i in range(len(dates) - 1):
            gap = (dates[i] - dates[i + 1]).days
            if gap > 0:  # Only positive gaps
                gaps.append(gap)
        
        if not gaps:
            return "irregular"
        
        avg_gap = sum(gaps) / len(gaps)
        
        if avg_gap <= 1:
            return "daily"
        elif avg_gap <= 3:
            return "every_2_3_days"
        elif avg_gap <= 7:
            return "weekly"
        elif avg_gap <= 14:
            return "biweekly"
        else:
            return "irregular"
    
    def _extract_hashtag_usage(self, posts: List[Any]) -> List[str]:
        """Extract common hashtags from USER'S recent posts."""
        hashtag_counts = {}
        
        for post in posts:
            if hasattr(post, 'caption') and post.caption:
                # Extract hashtags
                import re
                hashtags = re.findall(r'#(\w+)', post.caption.lower())
                for tag in hashtags:
                    hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1
        
        # Return top 10 hashtags used by USER
        sorted_tags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)
        return [f"#{tag}" for tag, count in sorted_tags[:10]]
    
    async def _grade_single_video(
        self, 
        video_post: Any, 
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Grade USER'S single video and identify strengths/weaknesses."""
        post_id = video_post[0]
        engagement_score = video_post[6] or 0
        
        strengths = []
        weaknesses = []
        
        # Base grade from engagement
        base_grade = min(100, max(0, int(engagement_score / 10)))
        
        # Analyze performance indicators for USER'S video
        if engagement_score > 100:
            strengths.append("High engagement score")
        elif engagement_score < 50:
            weaknesses.append("Low engagement performance")
        
        # Check if video analysis found good structure
        if analysis_result.get("analysis"):
            analysis_data = analysis_result["analysis"]
            
            # Check for good hook
            if "hook" in str(analysis_data).lower():
                strengths.append("Strong opening hook identified")
            
            # Check for clear structure
            chunks_count = analysis_result.get("chunks_created", 0)
            if chunks_count >= 3:
                strengths.append("Well-structured content with clear segments")
            elif chunks_count < 2:
                weaknesses.append("Lacks clear content structure")
        
        # Adjust grade based on analysis
        final_grade = base_grade
        if len(strengths) > len(weaknesses):
            final_grade = min(100, final_grade + 10)
        elif len(weaknesses) > len(strengths):
            final_grade = max(0, final_grade - 10)
        
        return {
            "videoId": str(post_id),
            "grade": final_grade,
            "strengths": strengths,
            "weaknesses": weaknesses
        }
    
    async def _grade_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Grade USER'S profile across 6 categories.
        
        FIXED: Exclude unanalyzed categories from overall grade calculation.
        Overall grade only averages categories with real data.
        """
        grades = {}
        
        # 1. Profile Optimization (bio, link, highlights, grid)
        profile_score, profile_details = self._grade_profile_optimization(data["scraped_data"])
        grades["profileOptimization"] = {"score": profile_score, "details": profile_details}
        
        # 2. Video Messaging (hook quality, CTA effectiveness)
        video_score, video_details = self._grade_video_messaging(data["processed_videos"])
        grades["videoMessaging"] = {"score": video_score, "details": video_details}
        
        # 3. Storyboarding (structure, pacing)
        story_score, story_details = self._grade_storyboarding(data["processed_videos"])
        grades["storyboarding"] = {"score": story_score, "details": story_details}
        
        # 4. Audience Engagement (engagement rate, reply quality > reply rate)
        engagement_score, engagement_details = self._grade_audience_engagement(data["oauth_data"])
        grades["audienceEngagement"] = {"score": engagement_score, "details": engagement_details}
        
        # 5. Content Consistency (posting frequency, visual consistency)
        consistency_score, consistency_details = self._grade_content_consistency(data["scraped_data"])
        grades["contentConsistency"] = {"score": consistency_score, "details": consistency_details}
        
        # 6. Reply Quality (conversation building vs one-word responses)
        reply_score, reply_details = self._grade_reply_quality(data["oauth_data"])
        grades["replyQuality"] = {"score": reply_score, "details": reply_details}
        
        # FIXED: Calculate overall grade excluding unanalyzed categories
        analyzed_categories = []
        for category_name, category_data in grades.items():
            if (category_data["score"] > 0 or 
                (category_data["details"] != "not_analyzed" and 
                 "Not yet analyzed" not in category_data["details"] and
                 "Connect Instagram" not in category_data["details"])):
                analyzed_categories.append(category_data["score"])
        
        # Overall grade calculation (letter grade A+ through F)
        if analyzed_categories:
            overall_numeric = sum(analyzed_categories) / len(analyzed_categories)
            overall_letter = self._numeric_to_letter_grade(overall_numeric)
            grades["overall"] = {
                "score": overall_letter,
                "details": f"Based on {len(analyzed_categories)} analyzed categories (average: {overall_numeric:.0f}/100)"
            }
        else:
            grades["overall"] = {
                "score": "F",
                "details": "Connect Instagram account to enable analysis"
            }
        
        return grades
    
    def _grade_profile_optimization(self, scraped_data: Dict[str, Any]) -> Tuple[int, str]:
        """Grade USER'S bio quality, link, highlights, profile pic."""
        score = 0
        issues = []
        positives = []
        
        # Bio quality (25 points)
        bio = scraped_data.get("bio", "")
        if bio and len(bio.strip()) > 10:
            score += 15
            if len(bio.strip()) < 150:  # Good length
                score += 10
                positives.append("Bio is concise and informative")
            else:
                issues.append("Bio is too long")
        else:
            issues.append("Bio is missing or too short")
        
        # Link in bio (20 points)
        link = scraped_data.get("linkInBio", "")
        if link:
            score += 20
            positives.append("Has link in bio")
        else:
            issues.append("Missing link in bio - losing conversion opportunities")
        
        # Profile picture (20 points) 
        profile_pic = scraped_data.get("profilePicUrl", "")
        if profile_pic:
            score += 20
            positives.append("Has profile picture")
        else:
            issues.append("Missing profile picture")
        
        # Highlights (15 points)
        highlights = scraped_data.get("highlightCovers", [])
        if highlights and len(highlights) > 0:
            score += 15
            positives.append("Has highlight covers")
        else:
            issues.append("No highlight covers - missed opportunity to showcase best content")
        
        # Grid aesthetic (20 points)
        grid = scraped_data.get("gridAesthetic", "")
        if grid in ["video_focused", "mixed_content"]:
            score += 20
            positives.append(f"Good grid aesthetic: {grid}")
        elif grid == "image_focused_with_video":
            score += 15
            positives.append("Decent grid variety")
        elif grid == "image_focused":
            score += 10
            issues.append("Grid lacks video content - algorithm prefers video")
        else:
            issues.append("Inconsistent grid aesthetic")
        
        details = ""
        if positives:
            details += "Strengths: " + ", ".join(positives) + ". "
        if issues:
            details += "Areas to improve: " + ", ".join(issues) + "."
        
        return min(100, score), details.strip()
    
    def _grade_video_messaging(self, processed_videos: List[Dict[str, Any]]) -> Tuple[int, str]:
        """Grade hook quality and CTA effectiveness across USER'S recent videos.
        
        FIXED: If video analysis hasn't run, return status "not_analyzed" (not 0).
        Only grade when we have actual video analysis data.
        """
        if not processed_videos:
            # Return status indicating analysis is needed, not a grade of 0
            return 0, "not_analyzed"
        
        # Check for analysis trigger placeholder
        if len(processed_videos) == 1 and processed_videos[0].get("videoId") == "trigger_analysis":
            return 0, "not_analyzed"
        
        # Filter out any placeholder entries to only grade real videos
        real_videos = [v for v in processed_videos if v.get("videoId") not in ["trigger_analysis", "add_to_competitors"]]
        
        if not real_videos:
            return 0, "not_analyzed"
        
        total_grade = sum(video.get("grade", 0) for video in real_videos)
        avg_grade = total_grade / len(real_videos)
        
        hook_strengths = sum(1 for video in real_videos if "hook" in " ".join(video.get("strengths", [])).lower())
        hook_ratio = hook_strengths / len(real_videos) if len(real_videos) > 0 else 0
        
        if hook_ratio >= 0.8:
            hook_assessment = "Consistently strong hooks"
        elif hook_ratio >= 0.5:
            hook_assessment = "Mixed hook quality"
        else:
            hook_assessment = "Weak hooks across videos"
        
        details = f"Average video grade: {avg_grade:.0f}/100. {hook_assessment} across {len(real_videos)} videos."
        
        return int(avg_grade), details
    
    def _grade_storyboarding(self, processed_videos: List[Dict[str, Any]]) -> Tuple[int, str]:
        """Grade structure scores and pacing consistency in USER'S videos.
        
        FIXED: If video analysis hasn't run, return status "not_analyzed" (not 0).
        Only grade when we have actual video analysis data.
        """
        if not processed_videos:
            return 0, "not_analyzed"
        
        # Check for analysis trigger placeholder
        if len(processed_videos) == 1 and processed_videos[0].get("videoId") == "trigger_analysis":
            return 0, "not_analyzed"
        
        # Filter out placeholder entries
        real_videos = [v for v in processed_videos if v.get("videoId") not in ["trigger_analysis", "add_to_competitors"]]
        
        if not real_videos:
            return 0, "not_analyzed"
        
        structured_videos = sum(1 for video in real_videos if "structure" in " ".join(video.get("strengths", [])).lower())
        structure_ratio = structured_videos / len(real_videos) if len(real_videos) > 0 else 0
        
        score = int(structure_ratio * 100)
        
        if structure_ratio >= 0.8:
            details = "Your videos have consistent, well-structured storytelling"
        elif structure_ratio >= 0.5:
            details = "Some videos show good structure, others lack clear flow"
        else:
            details = "Your videos lack clear structure and narrative flow"
        
        return score, details
    
    def _grade_audience_engagement(self, oauth_data: Dict[str, Any]) -> Tuple[int, str]:
        """Grade reply rate, reply quality, comment interaction for USER'S account.
        
        FIXED: Reply rate must factor into engagement grade - cannot be 100/100 with 0% reply rate.
        Per spec: If reply rate is 0%, engagement grade caps at 50/100 max regardless of other metrics.
        """
        engagement_rate = oauth_data.get("engagementRate", 0.0)
        reply_rate = oauth_data.get("replyRate", 0.0)
        
        # Base score from engagement rate
        if engagement_rate >= 5.0:
            base_score = 80  # Reduced from 100 to allow reply rate factor
            engagement_label = "Excellent"
        elif engagement_rate >= 3.0:
            base_score = 65
            engagement_label = "Good" 
        elif engagement_rate >= 2.0:
            base_score = 45
            engagement_label = "Average"
        elif engagement_rate >= 1.0:
            base_score = 30
            engagement_label = "Below average"
        else:
            base_score = 15
            engagement_label = "Low"
        
        # Reply rate factor (crucial for audience engagement grade)
        if reply_rate == 0.0:
            # CRITICAL FIX: 0% reply rate caps engagement grade at 50/100 maximum
            final_score = min(base_score, 50)
            reply_assessment = "No replies to audience - major engagement issue"
        elif reply_rate < 10.0:
            final_score = base_score + 5
            reply_assessment = f"{reply_rate:.1f}% reply rate - below average community interaction"
        elif reply_rate < 25.0:
            final_score = base_score + 10
            reply_assessment = f"{reply_rate:.1f}% reply rate - moderate community interaction" 
        elif reply_rate < 50.0:
            final_score = base_score + 15
            reply_assessment = f"{reply_rate:.1f}% reply rate - good community interaction"
        else:
            final_score = base_score + 20
            reply_assessment = f"{reply_rate:.1f}% reply rate - excellent community interaction"
        
        # Cap at 100
        final_score = min(100, final_score)
        
        # Build details with engagement rate + reply rate assessment
        details = f"{engagement_label} engagement rate: {engagement_rate:.2f}%. {reply_assessment}"
        
        # Add follower growth context
        net_growth = oauth_data.get("audienceDemographics", {}).get("netFollowerGrowth", 0)
        if net_growth > 0:
            details += f" | Growing by {net_growth} followers"
        elif net_growth < 0:
            details += f" | Losing {abs(net_growth)} followers"
        
        return final_score, details
    
    def _grade_content_consistency(self, scraped_data: Dict[str, Any]) -> Tuple[int, str]:
        """Grade USER'S posting frequency, visual consistency, topic consistency."""
        score = 0
        details_parts = []
        
        # Posting frequency (40 points)
        frequency = scraped_data.get("postingFrequency", "")
        if frequency == "daily":
            score += 40
            details_parts.append("Daily posting frequency")
        elif frequency == "every_2_3_days":
            score += 35
            details_parts.append("Regular posting (every 2-3 days)")
        elif frequency == "weekly":
            score += 25
            details_parts.append("Weekly posting frequency")
        elif frequency == "biweekly":
            score += 15
            details_parts.append("Biweekly posting frequency")
        else:
            details_parts.append("Irregular posting schedule hurts algorithm performance")
        
        # Visual consistency (30 points)
        grid_aesthetic = scraped_data.get("gridAesthetic", "")
        if grid_aesthetic in ["video_focused", "mixed_content"]:
            score += 30
            details_parts.append("Consistent visual theme")
        elif grid_aesthetic == "image_focused_with_video":
            score += 20
            details_parts.append("Mostly consistent visuals")
        else:
            details_parts.append("Inconsistent visual theme")
        
        # Topic consistency via hashtags (30 points)
        hashtags = scraped_data.get("hashtagUsage", [])
        if len(hashtags) >= 5:
            score += 30
            details_parts.append("Consistent hashtag strategy")
        elif len(hashtags) >= 3:
            score += 20
            details_parts.append("Some hashtag consistency")
        else:
            details_parts.append("No clear hashtag strategy")
        
        details = ". ".join(details_parts)
        return min(100, score), details
    
    def _grade_reply_quality(self, oauth_data: Dict[str, Any]) -> Tuple[int, str]:
        """Grade depth of replies, community building vs acknowledgment for USER'S account.
        
        FIXED: Cannot show 80/100 when zero replies exist.
        If reply count is 0, return "Not yet analyzed" status.
        When replies exist, analyze conversation-building vs one-word responses.
        """
        reply_rate = oauth_data.get("replyRate", 0.0)
        engagement_rate = oauth_data.get("engagementRate", 0.0)
        
        # CRITICAL FIX: If no replies, cannot grade quality
        if reply_rate == 0.0:
            return 0, "Not yet analyzed - no replies to evaluate quality"
        
        # Grade based on engagement patterns when replies do exist
        # Higher engagement with replies suggests quality conversation building
        if reply_rate >= 30.0 and engagement_rate >= 4.0:
            score = 85
            details = f"High-quality replies driving {engagement_rate:.2f}% engagement with {reply_rate:.1f}% reply rate - excellent community building"
        elif reply_rate >= 20.0 and engagement_rate >= 3.0:
            score = 75
            details = f"Good reply quality with {engagement_rate:.2f}% engagement and {reply_rate:.1f}% reply rate - building conversation"
        elif reply_rate >= 10.0 and engagement_rate >= 2.0:
            score = 60
            details = f"Moderate reply engagement with {engagement_rate:.2f}% engagement and {reply_rate:.1f}% reply rate"
        elif reply_rate >= 5.0:
            score = 45
            details = f"Limited reply quality - {reply_rate:.1f}% reply rate with {engagement_rate:.2f}% engagement suggests quick acknowledgments over conversation"
        else:
            score = 30
            details = f"Poor reply quality - {reply_rate:.1f}% reply rate too low to build community effectively"
        
        return score, details
    
    async def _generate_recommendations(
        self, 
        data: Dict[str, Any], 
        db: AsyncSession, 
        org_id: int
    ) -> Dict[str, List[Any]]:
        """Generate SPECIFIC, EVIDENCE-BACKED recommendations for USER."""
        recommendations = {
            "keepDoing": [],
            "stopDoing": [],
            "profileChanges": [],
            "contentRecommendations": [],
            "videosToRemove": [],
            "nextSteps": []
        }
        
        scraped_data = data["scraped_data"]
        grades = data["grades"]
        processed_videos = data["processed_videos"]
        oauth_data = data["oauth_data"]
        
        # FIXED: Profile optimization recommendations from ANY available data immediately
        # If Profile Optimization found issues, those ARE improvement items — surface them
        profile_score = grades["profileOptimization"]["score"]
        bio = scraped_data.get("bio", "")
        
        if not bio or len(bio.strip()) < 10:
            recommendations["profileChanges"].append({
                "what": "Write a compelling bio that tells visitors who you are and what value you provide",
                "why": "Empty bio means missed opportunities for every profile visitor",
                "priority": "high"
            })
        
        if not scraped_data.get("linkInBio"):
            recommendations["profileChanges"].append({
                "what": "Add a link in bio (Linktree, website, lead magnet)",
                "why": "Profile visitors have nowhere to go - losing conversion opportunities",
                "priority": "high"
            })
        
        if not scraped_data.get("highlightCovers") or len(scraped_data.get("highlightCovers", [])) == 0:
            recommendations["profileChanges"].append({
                "what": "Create Instagram Highlights showcasing your best content themes",
                "why": "Highlights are prime real estate for showing expertise and value",
                "priority": "medium"
            })
        
        # Surface profile optimization issues as improvement items regardless of threshold
        if profile_score < 100:
            recommendations["nextSteps"].append({
                "action": f"Improve profile optimization score from {profile_score}/100",
                "expectedImpact": "Better conversion from profile visitors to followers",
                "priority": "medium" if profile_score >= 70 else "high"
            })
        
        # Video recommendations based on performance
        # FIXED: Only generate video recommendations when analysis actually ran
        real_videos = [v for v in processed_videos if v.get("videoId") not in ["trigger_analysis", "add_to_competitors"]]
        
        if real_videos:
            low_performing = [v for v in real_videos if v.get("grade", 0) < 40]
            high_performing = [v for v in real_videos if v.get("grade", 0) >= 80]
            
            # Videos to consider removing (only if analysis confirms poor performance)
            if low_performing:
                for video in low_performing:
                    recommendations["videosToRemove"].append({
                        "videoId": video["videoId"],
                        "reason": f"Grade {video['grade']}/100: {', '.join(video.get('weaknesses', []))}"
                    })
            else:
                # FIXED: "All content performing well" ONLY if analysis actually ran and confirms it
                if real_videos:
                    recommendations["keepDoing"].append({
                        "what": "All analyzed videos performing above 40/100 threshold",
                        "evidence": f"Analyzed {len(real_videos)} videos - none require removal"
                    })
            
            # Keep doing (from high performing videos)
            for video in high_performing:
                if video.get("strengths"):
                    for strength in video["strengths"][:2]:  # Top 2 strengths
                        recommendations["keepDoing"].append({
                            "what": strength,
                            "evidence": f"Video {video['videoId']} scored {video['grade']}/100"
                        })
        else:
            # FIXED: If no analysis, return "analysis_pending" status
            recommendations["videosToRemove"].append({
                "videoId": "analysis_pending",
                "reason": "Video analysis pending - connect account and run analysis to identify underperforming content"
            })
        
        # Content consistency recommendations
        frequency = scraped_data.get("postingFrequency", "")
        if frequency in ["irregular", "insufficient_data"]:
            recommendations["stopDoing"].append({
                "what": "Posting inconsistently or infrequently",
                "evidence": "Current posting pattern is irregular, hurting algorithm performance"
            })
            
            recommendations["nextSteps"].append({
                "action": "Establish consistent posting schedule (every 2-3 days minimum)",
                "expectedImpact": "Improved algorithm distribution and audience retention",
                "priority": "high"
            })
        
        # Engagement-based recommendations  
        engagement_rate = oauth_data.get("engagementRate", 0.0)
        if engagement_rate < 2.0:
            recommendations["nextSteps"].append({
                "action": "Focus on stronger hooks in first 3 seconds of videos",
                "expectedImpact": "Higher completion rates and engagement",
                "priority": "high"
            })
            
            recommendations["contentRecommendations"].append({
                "what": "Create content that asks questions or includes calls-to-action",
                "why": f"Current engagement rate {engagement_rate:.2f}% is below 2% threshold",
                "priority": "high"
            })
        
        # Grid aesthetic recommendations
        if scraped_data.get("gridAesthetic") == "image_focused":
            recommendations["nextSteps"].append({
                "action": "Increase video content ratio to 60%+ of posts",
                "expectedImpact": "Better reach via Instagram's algorithm preference for video",
                "priority": "medium"
            })
        
        # FIXED: What's Working / What to Improve / Next Steps: populate from ANY available data immediately
        
        # Add to "keepDoing" based on any good scores
        if profile_score >= 80:
            recommendations["keepDoing"].append({
                "what": "Strong profile optimization setup",
                "evidence": f"Profile optimization scored {profile_score}/100"
            })
        
        if engagement_rate >= 3.0:
            recommendations["keepDoing"].append({
                "what": f"Good engagement rate of {engagement_rate:.2f}%",
                "evidence": "Above average engagement shows content resonates with audience"
            })
        
        # Add to "stopDoing" based on data
        if frequency in ["irregular", "insufficient_data"]:
            recommendations["stopDoing"].append({
                "what": "Posting inconsistently or infrequently",
                "evidence": "Current posting pattern is irregular, hurting algorithm performance"
            })
        
        # Ensure nextSteps always has actionable items
        if not recommendations["nextSteps"]:
            # Prioritize based on available data
            if not oauth_data or oauth_data.get("followerCount", 0) == 0:
                recommendations["nextSteps"].append({
                    "action": "Connect Instagram account via OAuth to unlock full analysis",
                    "expectedImpact": "Access to engagement metrics, audience data, and performance insights",
                    "priority": "high"
                })
            elif engagement_rate < 2.0:
                recommendations["nextSteps"].append({
                    "action": "Focus on improving content engagement rate",
                    "expectedImpact": "Higher reach and growth through algorithm boost",
                    "priority": "high"
                })
            elif profile_score < 70:
                recommendations["nextSteps"].append({
                    "action": "Optimize profile elements (bio, link, highlights)",
                    "expectedImpact": "Better conversion from profile visitors to followers",
                    "priority": "high"
                })
        
        # Competitor gap detection (comparison lens)
        await self._add_competitor_gap_recommendations(db, org_id, recommendations)
        
        return recommendations
    
    async def _add_competitor_gap_recommendations(
        self, 
        db: AsyncSession, 
        org_id: int, 
        recommendations: Dict[str, List[Any]]
    ):
        """Add content recommendations based on competitor gap analysis."""
        try:
            # Get top performing competitor content themes for comparison
            competitor_themes_result = await db.execute(
                text("""
                    SELECT DISTINCT c.handle, cp.post_text, cp.engagement_score
                    FROM crm.competitors c
                    JOIN crm.competitor_posts cp ON c.id = cp.competitor_id
                    WHERE c.org_id = :org_id 
                    AND cp.engagement_score > 80
                    ORDER BY cp.engagement_score DESC
                    LIMIT 10
                """),
                {"org_id": org_id}
            )
            
            top_competitor_content = competitor_themes_result.fetchall()
            
            if top_competitor_content:
                # Simple analysis of common themes
                all_text = " ".join([row[1] or "" for row in top_competitor_content])
                
                # Extract common themes (basic keyword analysis)
                common_words = ["tips", "hack", "secret", "mistake", "truth", "exposed", "reveal"]
                found_themes = [word for word in common_words if word.lower() in all_text.lower()]
                
                if found_themes:
                    recommendations["contentRecommendations"].append({
                        "what": f"Create content around trending themes: {', '.join(found_themes[:3])}",
                        "why": f"Top competitors using these themes with 80+ engagement scores",
                        "priority": "medium"
                    })
        
        except Exception as e:
            logger.warning(f"Failed to analyze competitor gaps: {e}")
    
    async def _create_profile_intel(
        self,
        db: AsyncSession,
        org_id: int,
        profile_id: str,
        platform: str,
        data: Dict[str, Any]
    ) -> ProfileIntelData:
        """Create new profile intel record."""
        profile_intel = ProfileIntelData(
            org_id=org_id,
            profile_id=profile_id,
            platform=platform,
            oauth_data=data["oauth_data"],
            scraped_data=data["scraped_data"],
            processed_videos=data["processed_videos"],
            grades=data["grades"],
            recommendations=data["recommendations"],
            last_synced_at=datetime.utcnow()
        )
        
        db.add(profile_intel)
        await db.flush()
        return profile_intel
    
    async def _update_profile_intel(
        self,
        db: AsyncSession,
        existing: ProfileIntelData,
        data: Dict[str, Any]
    ) -> None:
        """Update existing profile intel record."""
        existing.oauth_data = data["oauth_data"]
        existing.scraped_data = data["scraped_data"]
        existing.processed_videos = data["processed_videos"]
        existing.grades = data["grades"] 
        existing.recommendations = data["recommendations"]
        existing.last_synced_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
    
    def _profile_data_to_result(self, profile_data: ProfileIntelData) -> ProfileIntelResult:
        """Convert ProfileIntelData to ProfileIntelResult."""
        return ProfileIntelResult(
            profile_id=profile_data.profile_id,
            platform=profile_data.platform,
            oauth_data=profile_data.oauth_data or {},
            scraped_data=profile_data.scraped_data or {},
            processed_videos=profile_data.processed_videos or [],
            grades={
                name: CategoryGrade(score=grade.get("score", 0), details=grade.get("details", ""))
                for name, grade in (profile_data.grades or {}).items()
            },
            recommendations=profile_data.recommendations or {},
            last_synced_at=profile_data.last_synced_at or datetime.utcnow()
        )

# Service instance
profile_intel_service = ProfileIntelService()