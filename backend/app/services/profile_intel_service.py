"""Profile Intelligence Service
Merges OAuth data, scraped data, and video analysis into comprehensive profile intelligence.
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
class Recommendation:
    """Single actionable recommendation."""
    what: str
    why: str
    priority: str  # high, medium, low

@dataclass
class NextStep:
    """Next action step."""
    action: str
    expected_impact: str
    priority: str

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
        """Build complete profile intel by merging all data sources."""
        logger.info(f"Building profile intel for {profile_id} on {platform}")
        
        # Initialize data structure
        data = ProfileIntelData.create_empty_data_structure()
        
        # 1. Fetch OAuth data
        oauth_data = await self._fetch_oauth_data(db, org_id, profile_id, platform)
        if oauth_data:
            data["oauth_data"].update(oauth_data)
        
        # 2. Fetch scraped data
        scraped_data = await self._fetch_scraped_data(profile_id)
        if scraped_data:
            data["scraped_data"].update(scraped_data)
        
        # 3. Process recent videos 
        processed_videos = await self._process_recent_videos(db, org_id, profile_id)
        data["processed_videos"] = processed_videos
        
        # 4. Grade across all categories
        grades = await self._grade_profile(data)
        data["grades"] = grades
        
        # 5. Generate recommendations
        recommendations = await self._generate_recommendations(data)
        data["recommendations"] = recommendations
        
        return data
    
    async def _fetch_oauth_data(
        self,
        db: AsyncSession,
        org_id: int,
        profile_id: str,
        platform: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch OAuth analytics data from connected social accounts."""
        try:
            # Get social account
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
                logger.warning(f"No connected {platform} account found for {profile_id}")
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
            
            if not analytics:
                logger.warning(f"No analytics data found for account {account.id}")
                return None
            
            # Calculate aggregated metrics
            total_days = len(analytics)
            avg_engagement_rate = sum(a.engagement_rate or 0 for a in analytics) / total_days if total_days > 0 else 0
            avg_reach = sum(a.reach or 0 for a in analytics) / total_days if total_days > 0 else 0
            total_followers_gained = sum(a.followers_gained or 0 for a in analytics)
            total_followers_lost = sum(a.followers_lost or 0 for a in analytics)
            
            # Get top performing posts data from competitor posts table (if this is a competitor)
            top_posts_result = await db.execute(
                text("""
                    SELECT cp.id, cp.post_text, cp.likes, cp.comments, cp.shares, cp.engagement_score, cp.post_url
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE c.org_id = :org_id AND c.handle = :handle AND c.platform = :platform
                    ORDER BY cp.engagement_score DESC
                    LIMIT 5
                """),
                {"org_id": org_id, "handle": profile_id, "platform": platform}
            )
            top_posts = [dict(row._mapping) for row in top_posts_result.fetchall()]
            
            return {
                "followerCount": account.follower_count or 0,
                "followingCount": account.following_count or 0,
                "postCount": account.post_count or 0,
                "reachMetrics": {
                    "avgDailyReach": int(avg_reach),
                    "totalDays": total_days
                },
                "audienceDemographics": {
                    "netFollowerGrowth": total_followers_gained - total_followers_lost
                },
                "topPerformingPosts": top_posts,
                "engagementRate": float(avg_engagement_rate),
                "replyRate": 0.0,  # TODO: Calculate from comments analysis
                "avgReplyTime": 0.0  # TODO: Calculate from comments analysis
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch OAuth data for {profile_id}: {e}")
            return None
    
    async def _fetch_scraped_data(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Fetch public profile data via scraping."""
        try:
            # Import here to avoid circular import
            from app.api.content_intel import scrape_profile
            scraped = await scrape_profile(profile_id)
            
            if scraped.error:
                logger.warning(f"Scraping failed for {profile_id}: {scraped.error}")
                return None
            
            # Extract highlight covers info
            highlight_covers = []
            # TODO: Extract from scraped.posts if available
            
            # Extract recent post captions
            recent_captions = []
            if scraped.posts:
                recent_captions = [
                    (post.caption or "")[:200] + ("..." if len(post.caption or "") > 200 else "")
                    for post in scraped.posts[:10]
                    if post.caption
                ]
            
            # Analyze grid aesthetic
            grid_aesthetic = self._analyze_grid_aesthetic(scraped.posts if scraped.posts else [])
            
            # Calculate posting frequency 
            posting_frequency = self._calculate_posting_frequency(scraped.posts if scraped.posts else [])
            
            # Extract hashtag usage
            hashtag_usage = self._extract_hashtag_usage(scraped.posts if scraped.posts else [])
            
            return {
                "bio": scraped.bio or "",
                "profilePicUrl": scraped.profile_pic_url or "",
                "linkInBio": scraped.external_url or "",
                "highlightCovers": highlight_covers,
                "recentPostCaptions": recent_captions,
                "gridAesthetic": grid_aesthetic,
                "postingFrequency": posting_frequency,
                "hashtagUsage": hashtag_usage
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch scraped data for {profile_id}: {e}")
            return None
    
    def _analyze_grid_aesthetic(self, posts: List[Any]) -> str:
        """Analyze the visual consistency of the profile grid."""
        if not posts or len(posts) < 3:
            return "insufficient_data"
        
        # Count media types
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
        """Calculate posting frequency from recent posts."""
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
        """Extract common hashtags from recent posts."""
        hashtag_counts = {}
        
        for post in posts:
            if hasattr(post, 'caption') and post.caption:
                # Extract hashtags
                import re
                hashtags = re.findall(r'#(\w+)', post.caption.lower())
                for tag in hashtags:
                    hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1
        
        # Return top 10 hashtags
        sorted_tags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)
        return [f"#{tag}" for tag, count in sorted_tags[:10]]
    
    async def _process_recent_videos(
        self,
        db: AsyncSession,
        org_id: int,
        profile_id: str
    ) -> List[Dict[str, Any]]:
        """Process the last 5 videos through the competitor video analysis pipeline."""
        try:
            # Get competitor ID for this profile
            competitor_result = await db.execute(
                text("""
                    SELECT id FROM crm.competitors 
                    WHERE org_id = :org_id AND handle = :handle 
                    ORDER BY id DESC LIMIT 1
                """),
                {"org_id": org_id, "handle": profile_id}
            )
            competitor_row = competitor_result.fetchone()
            
            if not competitor_row:
                logger.warning(f"No competitor found for profile {profile_id}")
                return []
            
            competitor_id = competitor_row[0]
            
            # Get last 5 video posts
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
                post_id = video_post[0]
                media_url = video_post[1]
                
                try:
                    # Run through video analysis pipeline
                    analysis_result = await video_analysis_service.analyze_competitor_video(
                        db, post_id, media_url, force_reanalysis=False
                    )
                    
                    if analysis_result.get("success"):
                        # Grade this video
                        video_grade = await self._grade_single_video(video_post, analysis_result)
                        processed_videos.append(video_grade)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze video {post_id}: {e}")
                    continue
            
            return processed_videos
            
        except Exception as e:
            logger.error(f"Failed to process recent videos for {profile_id}: {e}")
            return []
    
    async def _grade_single_video(
        self, 
        video_post: Any, 
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Grade a single video and identify strengths/weaknesses."""
        post_id = video_post[0]
        engagement_score = video_post[6]
        
        strengths = []
        weaknesses = []
        
        # Base grade from engagement
        base_grade = min(100, max(0, int(engagement_score / 10)))  # Scale engagement to 0-100
        
        # Analyze performance indicators
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
        """Grade profile across 6 categories."""
        grades = {}
        
        # Profile Optimization
        profile_score, profile_details = self._grade_profile_optimization(data["scraped_data"])
        grades["profileOptimization"] = {"score": profile_score, "details": profile_details}
        
        # Video Messaging  
        video_score, video_details = self._grade_video_messaging(data["processed_videos"])
        grades["videoMessaging"] = {"score": video_score, "details": video_details}
        
        # Storyboarding
        story_score, story_details = self._grade_storyboarding(data["processed_videos"])
        grades["storyboarding"] = {"score": story_score, "details": story_details}
        
        # Audience Engagement
        engagement_score, engagement_details = self._grade_audience_engagement(data["oauth_data"])
        grades["audienceEngagement"] = {"score": engagement_score, "details": engagement_details}
        
        # Content Consistency
        consistency_score, consistency_details = self._grade_content_consistency(data["scraped_data"])
        grades["contentConsistency"] = {"score": consistency_score, "details": consistency_details}
        
        # Reply Quality  
        reply_score, reply_details = self._grade_reply_quality(data["oauth_data"])
        grades["replyQuality"] = {"score": reply_score, "details": reply_details}
        
        return grades
    
    def _grade_profile_optimization(self, scraped_data: Dict[str, Any]) -> Tuple[int, str]:
        """Grade bio quality, link, highlights, profile pic."""
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
            issues.append("Missing link in bio")
        
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
            issues.append("No highlight covers")
        
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
            issues.append("Grid lacks video content")
        else:
            issues.append("Inconsistent grid aesthetic")
        
        details = ""
        if positives:
            details += "Strengths: " + ", ".join(positives) + ". "
        if issues:
            details += "Areas to improve: " + ", ".join(issues) + "."
        
        return min(100, score), details.strip()
    
    def _grade_video_messaging(self, processed_videos: List[Dict[str, Any]]) -> Tuple[int, str]:
        """Grade hook quality and CTA effectiveness across recent videos."""
        if not processed_videos:
            return 0, "No videos analyzed yet"
        
        total_grade = sum(video.get("grade", 0) for video in processed_videos)
        avg_grade = total_grade / len(processed_videos)
        
        hook_strengths = sum(1 for video in processed_videos if "hook" in " ".join(video.get("strengths", [])).lower())
        hook_ratio = hook_strengths / len(processed_videos)
        
        if hook_ratio >= 0.8:
            hook_assessment = "Consistently strong hooks"
        elif hook_ratio >= 0.5:
            hook_assessment = "Mixed hook quality"
        else:
            hook_assessment = "Weak hooks across videos"
        
        details = f"Average video grade: {avg_grade:.0f}/100. {hook_assessment} across {len(processed_videos)} videos."
        
        return int(avg_grade), details
    
    def _grade_storyboarding(self, processed_videos: List[Dict[str, Any]]) -> Tuple[int, str]:
        """Grade structure scores and pacing consistency."""
        if not processed_videos:
            return 0, "No videos analyzed for structure"
        
        structured_videos = sum(1 for video in processed_videos if "structure" in " ".join(video.get("strengths", [])).lower())
        structure_ratio = structured_videos / len(processed_videos)
        
        score = int(structure_ratio * 100)
        
        if structure_ratio >= 0.8:
            details = "Videos have consistent, well-structured storytelling"
        elif structure_ratio >= 0.5:
            details = "Some videos show good structure, others lack clear flow"
        else:
            details = "Videos lack clear structure and narrative flow"
        
        return score, details
    
    def _grade_audience_engagement(self, oauth_data: Dict[str, Any]) -> Tuple[int, str]:
        """Grade reply rate, reply quality, comment interaction."""
        engagement_rate = oauth_data.get("engagementRate", 0.0)
        
        # Convert engagement rate to 0-100 score
        if engagement_rate >= 5.0:
            score = 100
            details = f"Excellent engagement rate: {engagement_rate:.2f}%"
        elif engagement_rate >= 3.0:
            score = 80
            details = f"Good engagement rate: {engagement_rate:.2f}%"
        elif engagement_rate >= 2.0:
            score = 60
            details = f"Average engagement rate: {engagement_rate:.2f}%"
        elif engagement_rate >= 1.0:
            score = 40
            details = f"Below average engagement rate: {engagement_rate:.2f}%"
        else:
            score = 20
            details = f"Low engagement rate: {engagement_rate:.2f}%"
        
        # TODO: Factor in reply rate and reply quality when available
        
        return score, details
    
    def _grade_content_consistency(self, scraped_data: Dict[str, Any]) -> Tuple[int, str]:
        """Grade posting frequency, visual consistency, topic consistency."""
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
            details_parts.append("Irregular posting schedule")
        
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
        """Grade depth of replies, community building vs acknowledgment."""
        # TODO: Implement when comment analysis data is available
        # For now, use a placeholder based on engagement rate
        
        engagement_rate = oauth_data.get("engagementRate", 0.0)
        
        if engagement_rate >= 4.0:
            score = 80
            details = "High engagement suggests active community interaction"
        elif engagement_rate >= 2.0:
            score = 60  
            details = "Moderate engagement suggests some community building"
        else:
            score = 40
            details = "Low engagement suggests limited community interaction"
        
        return score, details
    
    async def _generate_recommendations(self, data: Dict[str, Any]) -> Dict[str, List[Any]]:
        """Generate specific, evidence-based recommendations."""
        recommendations = {
            "profileChanges": [],
            "videosToDelete": [],
            "keepDoing": [],
            "stopDoing": [],
            "nextSteps": []
        }
        
        scraped_data = data["scraped_data"]
        grades = data["grades"]
        processed_videos = data["processed_videos"]
        oauth_data = data["oauth_data"]
        
        # Profile optimization recommendations
        if grades["profileOptimization"]["score"] < 70:
            bio = scraped_data.get("bio", "")
            if not bio or len(bio.strip()) < 10:
                recommendations["profileChanges"].append({
                    "what": "Add a compelling bio",
                    "why": "Empty bio means missed opportunities for every profile visitor",
                    "priority": "high"
                })
            
            if not scraped_data.get("linkInBio"):
                recommendations["profileChanges"].append({
                    "what": "Add link in bio",
                    "why": "Profile visitors have nowhere to go - losing conversion opportunities",
                    "priority": "high"
                })
        
        # Video recommendations based on performance
        if processed_videos:
            low_performing = [v for v in processed_videos if v.get("grade", 0) < 40]
            high_performing = [v for v in processed_videos if v.get("grade", 0) >= 80]
            
            # Videos to delete
            for video in low_performing:
                recommendations["videosToDelete"].append({
                    "videoId": video["videoId"],
                    "reason": f"Grade {video['grade']}/100: {', '.join(video.get('weaknesses', []))}"
                })
            
            # Keep doing (from high performing videos)
            for video in high_performing:
                if video.get("strengths"):
                    for strength in video["strengths"][:2]:  # Top 2 strengths
                        recommendations["keepDoing"].append({
                            "what": strength,
                            "evidence": f"Video {video['videoId']} scored {video['grade']}/100"
                        })
        
        # Content consistency recommendations
        frequency = scraped_data.get("postingFrequency", "")
        if frequency in ["irregular", "insufficient_data"]:
            recommendations["stopDoing"].append({
                "what": "Inconsistent posting schedule",
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
        
        # Grid aesthetic recommendations
        if scraped_data.get("gridAesthetic") == "image_focused":
            recommendations["nextSteps"].append({
                "action": "Increase video content ratio to 60%+ of posts",
                "expectedImpact": "Better reach via Instagram's algorithm preference for video",
                "priority": "medium"
            })
        
        return recommendations
    
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