"""
User's Own Audience Intelligence Service

Extracts audience insights from USER'S OWN comments and DMs.
Uses the same extraction pipeline as competitor audience intelligence,
but focuses on USER'S content and audience.

Stores results separately from competitor intelligence for Profile Intel consumption.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audience_intelligence import analyze_audience_intelligence
from app.models.crm.social import SocialAccount

logger = logging.getLogger(__name__)

# Instagram Graph API configuration
INSTAGRAM_GRAPH_API_BASE = "https://graph.instagram.com"


class UserAudienceIntelligenceService:
    """Service for extracting audience intelligence from USER'S OWN posts."""

    def __init__(self):
        self.graph_api_base = INSTAGRAM_GRAPH_API_BASE

    async def get_user_audience_intelligence(
        self,
        db: AsyncSession,
        org_id: int,
        user_id: int,
        platform: str = "instagram",
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Main method: Get comprehensive audience intelligence from USER'S comments.
        
        Returns:
        - objections: What USER'S audience resists or questions  
        - desires: What USER'S audience wants (with verbatim language)
        - questions: Unanswered questions from USER'S audience (content ideas)
        - emotional_triggers: What makes USER'S audience share/save/comment
        - competitor_gaps: What USER'S audience wants that competitors don't address
        - sentiment_trends: Comment sentiment over last 30 days
        - content_opportunities: Most requested topics from audience
        """
        try:
            # 1. Get user's connected social account
            account = await self._get_user_social_account(db, org_id, user_id, platform)
            if not account:
                return {
                    "error": "No connected Instagram account found",
                    "connect_required": True,
                    "total_comments_analyzed": 0
                }

            # 2. Pull user's own comments via OAuth or scraping
            user_comments = await self._fetch_user_comments(db, account, days_back)
            if not user_comments:
                return {
                    "error": "No comments found on user's posts",
                    "suggestion": "Run comment extraction if user has recent posts",
                    "total_comments_analyzed": 0
                }

            # 3. Extract insights using same pipeline as competitor intelligence
            base_intelligence = await analyze_audience_intelligence(user_comments)

            # 4. Add user-specific extractions
            user_specific_insights = await self._extract_user_specific_insights(
                user_comments, account, days_back
            )

            # 5. Combine and enhance results
            combined_intelligence = {
                **base_intelligence,
                **user_specific_insights,
                "source": "user_own_content",
                "account_username": account.username,
                "extraction_period_days": days_back,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }

            # 6. Store results for Profile Intel access
            await self._store_user_audience_intelligence(
                db, org_id, account.username, combined_intelligence
            )

            return combined_intelligence

        except Exception as e:
            logger.error(f"Failed to get user audience intelligence: {e}")
            return {
                "error": f"Failed to extract audience intelligence: {str(e)}",
                "total_comments_analyzed": 0
            }

    async def _get_user_social_account(
        self,
        db: AsyncSession,
        org_id: int,
        user_id: int,
        platform: str
    ) -> Optional[SocialAccount]:
        """Get user's connected social account with OAuth token."""
        try:
            result = await db.execute(
                text("""
                    SELECT id, username, access_token, refresh_token, platform, status
                    FROM crm.social_accounts 
                    WHERE user_id = :user_id 
                    AND org_id = :org_id 
                    AND platform = :platform 
                    AND status = 'connected'
                    AND access_token IS NOT NULL
                    ORDER BY last_synced DESC NULLS LAST
                    LIMIT 1
                """),
                {"user_id": user_id, "org_id": org_id, "platform": platform}
            )
            
            row = result.first()
            if not row:
                return None

            # Convert row to SocialAccount-like object
            class AccountInfo:
                def __init__(self, row_data):
                    self.id = row_data[0]
                    self.username = row_data[1]
                    self.access_token = row_data[2]
                    self.refresh_token = row_data[3]
                    self.platform = row_data[4]
                    self.status = row_data[5]

            return AccountInfo(row)

        except Exception as e:
            logger.error(f"Failed to get user social account: {e}")
            return None

    async def _fetch_user_comments(
        self,
        db: AsyncSession,
        account: Any,
        days_back: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch comments on USER'S posts via Instagram Graph API or scraping fallback.
        
        Strategy:
        1. Try Instagram Graph API with OAuth token (best data quality)
        2. Fallback to scraping user's public posts (if API unavailable)
        3. Check if user exists in competitors table (legacy data)
        """
        try:
            # Method 1: Instagram Graph API (OAuth)
            if account.access_token and account.platform == "instagram":
                api_comments = await self._fetch_via_instagram_api(account, days_back)
                if api_comments:
                    logger.info(f"Fetched {len(api_comments)} comments via Instagram API")
                    return api_comments

            # Method 2: Scraping fallback  
            scraped_comments = await self._fetch_via_scraping(db, account.username)
            if scraped_comments:
                logger.info(f"Fetched {len(scraped_comments)} comments via scraping")
                return scraped_comments

            # Method 3: Check competitors table (legacy)
            competitor_comments = await self._fetch_from_competitors_table(
                db, account.username, days_back
            )
            if competitor_comments:
                logger.info(f"Found {len(competitor_comments)} comments in competitors table")
                return competitor_comments

            logger.warning(f"No comments found for user {account.username}")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch user comments: {e}")
            return []

    async def _fetch_via_instagram_api(
        self, 
        account: Any, 
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Fetch user's post comments via Instagram Graph API."""
        try:
            comments = []
            
            # Get user's recent media (posts)
            media_url = f"{self.graph_api_base}/me/media"
            params = {
                "access_token": account.access_token,
                "fields": "id,media_type,timestamp,caption,comments_count",
                "limit": 25  # Last 25 posts
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch user's posts
                response = await client.get(media_url, params=params)
                if response.status_code != 200:
                    logger.warning(f"Instagram API error: {response.status_code}")
                    return []

                media_data = response.json().get("data", [])
                
                # Filter posts within date range
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                recent_media = []
                
                for media in media_data:
                    media_timestamp = datetime.fromisoformat(
                        media.get("timestamp", "").replace("Z", "+00:00")
                    )
                    if media_timestamp >= cutoff_date:
                        recent_media.append(media)

                # Fetch comments for each recent post
                for media in recent_media:
                    media_id = media["id"]
                    comments_url = f"{self.graph_api_base}/{media_id}/comments"
                    
                    comments_params = {
                        "access_token": account.access_token,
                        "fields": "id,text,username,timestamp,like_count,replies.limit(5){text,username,timestamp}",
                        "limit": 50  # Up to 50 comments per post
                    }
                    
                    comments_response = await client.get(comments_url, params=comments_params)
                    if comments_response.status_code == 200:
                        post_comments = comments_response.json().get("data", [])
                        
                        # Convert to standard format
                        for comment in post_comments:
                            comments.append({
                                "id": comment.get("id", ""),
                                "text": comment.get("text", ""),
                                "username": comment.get("username", ""),
                                "timestamp": comment.get("timestamp"),
                                "likes": comment.get("like_count", 0),
                                "replies": len(comment.get("replies", {}).get("data", [])),
                                "post_id": media_id,
                                "source": "instagram_graph_api"
                            })

            return comments

        except Exception as e:
            logger.error(f"Instagram Graph API error: {e}")
            return []

    async def _fetch_via_scraping(
        self, 
        db: AsyncSession, 
        username: str
    ) -> List[Dict[str, Any]]:
        """Scrape user's post comments using existing scraper infrastructure."""
        try:
            # Check if user's posts exist in competitor_posts (added as competitor)
            result = await db.execute(
                text("""
                    SELECT cp.id, cp.comments_data, cp.post_url, cp.posted_at
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE c.handle = :username
                    AND cp.comments_data IS NOT NULL
                    AND cp.posted_at >= :cutoff_date
                    ORDER BY cp.posted_at DESC
                    LIMIT 20
                """),
                {
                    "username": username,
                    "cutoff_date": datetime.utcnow() - timedelta(days=30)
                }
            )

            posts = result.fetchall()
            if not posts:
                return []

            # Extract comments from stored data
            all_comments = []
            for post in posts:
                if post.comments_data:
                    post_comments = post.comments_data
                    for comment in post_comments:
                        # Add post context
                        comment["post_id"] = str(post.id)
                        comment["post_url"] = post.post_url
                        comment["source"] = "scraper_data"
                        all_comments.append(comment)

            return all_comments

        except Exception as e:
            logger.error(f"Scraping fallback error: {e}")
            return []

    async def _fetch_from_competitors_table(
        self, 
        db: AsyncSession, 
        username: str, 
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Get comments from competitors table if user was added as competitor."""
        try:
            result = await db.execute(
                text("""
                    SELECT cp.comments_data, cp.post_url, cp.posted_at
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id  
                    WHERE c.handle = :username
                    AND cp.comments_data IS NOT NULL
                    AND cp.posted_at >= :cutoff_date
                    ORDER BY cp.posted_at DESC
                    LIMIT 15
                """),
                {
                    "username": username,
                    "cutoff_date": datetime.utcnow() - timedelta(days=days_back)
                }
            )

            posts = result.fetchall()
            all_comments = []
            
            for post in posts:
                if post.comments_data:
                    for comment in post.comments_data:
                        comment["source"] = "competitor_table"
                        comment["post_url"] = post.post_url
                        all_comments.append(comment)

            return all_comments

        except Exception as e:
            logger.error(f"Competitors table lookup error: {e}")
            return []

    async def _extract_user_specific_insights(
        self,
        comments: List[Dict[str, Any]],
        account: Any,
        days_back: int
    ) -> Dict[str, Any]:
        """Extract user-specific insights beyond standard audience intelligence."""
        try:
            user_insights = {}

            # 1. Comment sentiment trend over time
            sentiment_trend = self._analyze_sentiment_trend(comments, days_back)
            user_insights["sentiment_trends"] = sentiment_trend

            # 2. Most common audience questions (content opportunities)
            content_opportunities = self._extract_content_opportunities(comments)
            user_insights["content_opportunities"] = content_opportunities

            # 3. Save vs Share vs Comment patterns (if available in data)
            engagement_patterns = self._analyze_engagement_patterns(comments)
            user_insights["engagement_patterns"] = engagement_patterns

            # 4. Audience question categories
            question_categories = self._categorize_audience_questions(comments)
            user_insights["question_categories"] = question_categories

            # 5. Repeat commenters vs new audience
            commenter_analysis = self._analyze_commenter_patterns(comments)
            user_insights["commenter_patterns"] = commenter_analysis

            return user_insights

        except Exception as e:
            logger.error(f"Failed to extract user-specific insights: {e}")
            return {}

    def _analyze_sentiment_trend(
        self, 
        comments: List[Dict[str, Any]], 
        days_back: int
    ) -> Dict[str, Any]:
        """Analyze comment sentiment over last 30 days."""
        try:
            # Simple sentiment analysis using keyword patterns
            positive_keywords = ["love", "amazing", "great", "awesome", "perfect", "helpful", "thank"]
            negative_keywords = ["hate", "bad", "terrible", "wrong", "disappointed", "boring"]
            
            # Group comments by week
            weekly_sentiment = {}
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            
            for comment in comments:
                text = comment.get("text", "").lower()
                comment_date = comment.get("timestamp")
                
                if not comment_date:
                    continue
                    
                # Parse timestamp (handle different formats)
                try:
                    if isinstance(comment_date, str):
                        comment_dt = datetime.fromisoformat(
                            comment_date.replace("Z", "+00:00")
                        )
                    else:
                        comment_dt = comment_date
                        
                    if comment_dt < cutoff:
                        continue
                        
                    # Get week bucket
                    week_start = comment_dt - timedelta(days=comment_dt.weekday())
                    week_key = week_start.strftime("%Y-%m-%d")
                    
                    if week_key not in weekly_sentiment:
                        weekly_sentiment[week_key] = {"positive": 0, "negative": 0, "neutral": 0}
                    
                    # Score sentiment
                    positive_score = sum(1 for word in positive_keywords if word in text)
                    negative_score = sum(1 for word in negative_keywords if word in text)
                    
                    if positive_score > negative_score:
                        weekly_sentiment[week_key]["positive"] += 1
                    elif negative_score > positive_score:
                        weekly_sentiment[week_key]["negative"] += 1
                    else:
                        weekly_sentiment[week_key]["neutral"] += 1
                        
                except Exception:
                    continue
            
            # Calculate trend
            weeks = sorted(weekly_sentiment.keys())
            trend = "stable"
            if len(weeks) >= 2:
                recent_week = weekly_sentiment[weeks[-1]]
                older_week = weekly_sentiment[weeks[-2]]
                
                recent_positive_ratio = recent_week["positive"] / max(sum(recent_week.values()), 1)
                older_positive_ratio = older_week["positive"] / max(sum(older_week.values()), 1)
                
                if recent_positive_ratio > older_positive_ratio + 0.1:
                    trend = "improving"
                elif recent_positive_ratio < older_positive_ratio - 0.1:
                    trend = "declining"
            
            return {
                "trend": trend,
                "weekly_breakdown": weekly_sentiment,
                "overall_sentiment": {
                    "positive": sum(w["positive"] for w in weekly_sentiment.values()),
                    "negative": sum(w["negative"] for w in weekly_sentiment.values()),
                    "neutral": sum(w["neutral"] for w in weekly_sentiment.values())
                }
            }

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {"trend": "unknown", "weekly_breakdown": {}, "overall_sentiment": {}}

    def _extract_content_opportunities(
        self, 
        comments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract most requested content topics from audience questions."""
        try:
            question_topics = {}
            
            # Look for content requests and questions
            request_patterns = [
                r"(?:can you|could you|would you).*?(?:make|create|do|show).*?(.*?)(?:\?|$)",
                r"(?:i wish you|i hope you).*?(?:would|could).*?(.*?)(?:\?|$)",
                r"(?:please).*?(?:make|do|show|create).*?(.*?)(?:\?|$)",
                r"(?:what about|how about).*?(.*?)(?:\?|$)",
                r"(?:tutorial on|video on|video about).*?(.*?)(?:\?|$)"
            ]
            
            for comment in comments:
                text = comment.get("text", "").lower()
                
                # Check for question patterns  
                if "?" in text:
                    for pattern in request_patterns:
                        import re
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            topic = match.strip()
                            if len(topic) > 3 and len(topic) < 100:
                                question_topics[topic] = question_topics.get(topic, 0) + 1

            # Sort by frequency and return top opportunities
            sorted_topics = sorted(
                question_topics.items(), 
                key=lambda x: x[1], 
                reverse=True
            )

            opportunities = []
            for topic, count in sorted_topics[:10]:
                opportunities.append({
                    "topic": topic,
                    "request_count": count,
                    "opportunity_score": min(100, count * 20),
                    "usage_hint": "Create content addressing this audience request"
                })

            return opportunities

        except Exception as e:
            logger.error(f"Content opportunity extraction failed: {e}")
            return []

    def _analyze_engagement_patterns(
        self, 
        comments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze what type of content gets saved vs shared vs commented."""
        try:
            # Look for save/share indicators in comment text
            save_indicators = ["save", "saved", "saving", "bookmark"]
            share_indicators = ["share", "sharing", "send this", "sending this", "tag"]
            
            save_comments = []
            share_comments = []
            general_comments = []

            for comment in comments:
                text = comment.get("text", "").lower()
                
                if any(indicator in text for indicator in save_indicators):
                    save_comments.append(comment)
                elif any(indicator in text for indicator in share_indicators):
                    share_comments.append(comment)
                else:
                    general_comments.append(comment)

            total = len(comments)
            if total == 0:
                return {"save_rate": 0, "share_rate": 0, "comment_rate": 0}

            return {
                "save_rate": len(save_comments) / total * 100,
                "share_rate": len(share_comments) / total * 100,
                "comment_rate": len(general_comments) / total * 100,
                "save_signals": len(save_comments),
                "share_signals": len(share_comments),
                "total_analyzed": total
            }

        except Exception as e:
            logger.error(f"Engagement pattern analysis failed: {e}")
            return {"save_rate": 0, "share_rate": 0, "comment_rate": 0}

    def _categorize_audience_questions(
        self, 
        comments: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Categorize audience questions into content themes."""
        try:
            categories = {
                "how_to": [],
                "what_is": [],
                "why_does": [], 
                "when_should": [],
                "where_can": [],
                "tools_software": [],
                "beginner": [],
                "advanced": []
            }

            for comment in comments:
                text = comment.get("text", "")
                if not text.endswith("?"):
                    continue

                text_lower = text.lower()
                
                # Categorize by question type
                if text_lower.startswith("how to") or "how do" in text_lower:
                    categories["how_to"].append(text[:100])
                elif text_lower.startswith("what is") or text_lower.startswith("what are"):
                    categories["what_is"].append(text[:100])
                elif text_lower.startswith("why does") or text_lower.startswith("why is"):
                    categories["why_does"].append(text[:100])
                elif text_lower.startswith("when should") or text_lower.startswith("when do"):
                    categories["when_should"].append(text[:100])
                elif text_lower.startswith("where can") or text_lower.startswith("where do"):
                    categories["where_can"].append(text[:100])
                elif any(word in text_lower for word in ["tool", "software", "app", "platform"]):
                    categories["tools_software"].append(text[:100])
                elif any(word in text_lower for word in ["beginner", "start", "new", "first time"]):
                    categories["beginner"].append(text[:100])
                elif any(word in text_lower for word in ["advanced", "expert", "pro", "complex"]):
                    categories["advanced"].append(text[:100])

            # Remove empty categories and limit to 5 questions each
            return {
                category: questions[:5] 
                for category, questions in categories.items() 
                if questions
            }

        except Exception as e:
            logger.error(f"Question categorization failed: {e}")
            return {}

    def _analyze_commenter_patterns(
        self, 
        comments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze repeat commenters vs new audience engagement."""
        try:
            commenter_counts = {}
            
            for comment in comments:
                username = comment.get("username", "")
                if username:
                    commenter_counts[username] = commenter_counts.get(username, 0) + 1

            total_commenters = len(commenter_counts)
            if total_commenters == 0:
                return {"repeat_commenter_rate": 0, "new_audience_rate": 0}

            # Classify commenters
            repeat_commenters = sum(1 for count in commenter_counts.values() if count > 1)
            new_commenters = sum(1 for count in commenter_counts.values() if count == 1)

            # Find most active commenters
            top_commenters = sorted(
                commenter_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]

            return {
                "repeat_commenter_rate": repeat_commenters / total_commenters * 100,
                "new_audience_rate": new_commenters / total_commenters * 100,
                "total_unique_commenters": total_commenters,
                "average_comments_per_user": sum(commenter_counts.values()) / total_commenters,
                "top_commenters": [
                    {"username": username, "comment_count": count}
                    for username, count in top_commenters
                ]
            }

        except Exception as e:
            logger.error(f"Commenter pattern analysis failed: {e}")
            return {"repeat_commenter_rate": 0, "new_audience_rate": 0}

    async def _store_user_audience_intelligence(
        self,
        db: AsyncSession,
        org_id: int,
        username: str,
        intelligence: Dict[str, Any]
    ) -> None:
        """Store user audience intelligence data for Profile Intel access."""
        try:
            # Store in profile_intel_data table as audience intelligence section
            result = await db.execute(
                text("""
                    SELECT id FROM crm.profile_intel_data
                    WHERE org_id = :org_id AND profile_id = :profile_id
                """),
                {"org_id": org_id, "profile_id": username}
            )
            
            existing = result.first()
            
            if existing:
                # Update existing record
                await db.execute(
                    text("""
                        UPDATE crm.profile_intel_data
                        SET recommendations = COALESCE(recommendations, '{}') || 
                            jsonb_build_object('audienceIntelligence', :intelligence),
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": existing[0], "intelligence": json.dumps(intelligence)}
                )
            else:
                # Create new record with audience intelligence
                await db.execute(
                    text("""
                        INSERT INTO crm.profile_intel_data 
                        (org_id, profile_id, platform, recommendations, last_synced_at)
                        VALUES 
                        (:org_id, :profile_id, 'instagram', 
                         jsonb_build_object('audienceIntelligence', :intelligence), NOW())
                    """),
                    {
                        "org_id": org_id,
                        "profile_id": username,
                        "intelligence": json.dumps(intelligence)
                    }
                )
            
            await db.commit()
            logger.info(f"Stored user audience intelligence for {username}")

        except Exception as e:
            logger.error(f"Failed to store user audience intelligence: {e}")
            await db.rollback()


# Service instance
user_audience_intelligence_service = UserAudienceIntelligenceService()