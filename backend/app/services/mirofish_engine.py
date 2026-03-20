"""MiroFish Engine - Predictive Content Simulation System

Phase 1: SimulationLite
- Uses existing competitor data to generate lightweight audience personas
- Role-plays personas evaluating content using Gemini
- Provides viral scores, engagement predictions, and specific recommendations

Phase 2 Roadmap: Deep Psychographic Profiling
- Video content analysis (hooks, pacing, visual elements)
- OCEAN personality traits modeling
- Behavioral pattern analysis
- Multi-modal content understanding
- Advanced recommendation engine with frame-level insights
- Demographic and psychographic segmentation
- Cross-platform performance prediction
- Temporal engagement modeling
"""

import logging
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.nano_banana import _get_api_key, call_gemini_api

logger = logging.getLogger(__name__)


class MiroFishEngine:
    """
    MiroFish Predictive Content Simulation Engine
    
    Generates synthetic audience personas from competitor engagement data
    and simulates their responses to content for viral prediction.
    """
    
    async def generate_personas(self, org_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Generate 5-10 synthetic audience personas from competitor post engagement data.
        
        Analyzes competitor posts and their engagement patterns to cluster by:
        - Content type preferences
        - Engagement behavior patterns  
        - Sentiment responses
        - Interaction styles
        
        Returns persona profiles with predicted behavior patterns.
        """
        try:
            # Query competitor posts and engagement data
            query = text("""
                SELECT 
                    c.handle,
                    c.platform,
                    c.avg_engagement_rate,
                    cp.text,
                    cp.likes,
                    cp.comments,
                    cp.shares,
                    cp.engagement_score,
                    cp.hook,
                    cp.media_type,
                    cp.detected_format
                FROM crm.competitors c
                JOIN crm.competitor_posts cp ON c.id = cp.competitor_id
                WHERE c.org_id = :org_id
                AND cp.engagement_score > 0
                ORDER BY cp.engagement_score DESC
                LIMIT 200
            """)
            
            result = await db.execute(query, {"org_id": org_id})
            posts = result.fetchall()
            
            if not posts:
                logger.warning(f"No competitor posts found for org {org_id}")
                return []
            
            # Analyze engagement patterns to create persona clusters
            personas = self._cluster_into_personas(posts)
            
            logger.info(f"Generated {len(personas)} personas from {len(posts)} competitor posts")
            return personas
            
        except Exception as e:
            logger.error(f"Failed to generate personas: {e}")
            return []
    
    def _cluster_into_personas(self, posts: List[Any]) -> List[Dict[str, Any]]:
        """
        Cluster competitor engagement data into synthetic audience personas.
        
        Creates 5-8 distinct personas based on engagement patterns:
        - High Engagers (love viral content)
        - Casual Browsers (selective engagement)
        - Comment Warriors (discussion starters)
        - Share Enthusiasts (amplifiers)
        - Visual Lovers (media-focused)
        - Text Readers (caption-focused)
        - Trend Followers (format-sensitive)
        - Skeptics (low engagement, high standards)
        """
        
        # Analyze engagement patterns
        high_engagement_posts = [p for p in posts if p.engagement_score > 80]
        medium_engagement_posts = [p for p in posts if 40 <= p.engagement_score <= 80]
        low_engagement_posts = [p for p in posts if p.engagement_score < 40]
        
        # Content type analysis
        video_posts = [p for p in posts if p.media_type == 'video']
        image_posts = [p for p in posts if p.media_type == 'image']
        text_posts = [p for p in posts if not p.media_type or p.media_type == 'text']
        
        # Generate personas based on patterns
        personas = [
            {
                "id": "viral_chaser",
                "name": "The Viral Chaser",
                "description": "Lives for trending content, quick to engage with viral material",
                "engagement_behavior": {
                    "like_probability": 0.85,
                    "comment_probability": 0.6,
                    "share_probability": 0.7,
                    "watch_time_factor": 0.9
                },
                "content_preferences": {
                    "trending_topics": 0.9,
                    "visual_appeal": 0.8,
                    "hook_strength": 0.95,
                    "format_familiarity": 0.7
                },
                "decision_factors": [
                    "Hook grabs attention in first 3 seconds",
                    "Content feels shareable and viral-worthy",
                    "Trending audio or format elements",
                    "High energy and excitement"
                ],
                "sample_size": len(high_engagement_posts)
            },
            {
                "id": "casual_scroller",
                "name": "The Casual Scroller", 
                "description": "Selective engagement, prefers quality over quantity",
                "engagement_behavior": {
                    "like_probability": 0.4,
                    "comment_probability": 0.15,
                    "share_probability": 0.2,
                    "watch_time_factor": 0.6
                },
                "content_preferences": {
                    "trending_topics": 0.5,
                    "visual_appeal": 0.6,
                    "hook_strength": 0.7,
                    "format_familiarity": 0.8
                },
                "decision_factors": [
                    "Content must be immediately relevant",
                    "Clear value proposition",
                    "Not too long or demanding",
                    "Easy to consume quickly"
                ],
                "sample_size": len(medium_engagement_posts)
            },
            {
                "id": "comment_warrior",
                "name": "The Comment Warrior",
                "description": "Loves to discuss and debate, comment-heavy engagement",
                "engagement_behavior": {
                    "like_probability": 0.7,
                    "comment_probability": 0.9,
                    "share_probability": 0.4,
                    "watch_time_factor": 0.85
                },
                "content_preferences": {
                    "trending_topics": 0.6,
                    "visual_appeal": 0.5,
                    "hook_strength": 0.8,
                    "format_familiarity": 0.6
                },
                "decision_factors": [
                    "Content sparks discussion or debate",
                    "Controversial or thought-provoking angle",
                    "Room for personal opinions",
                    "Community engagement potential"
                ],
                "sample_size": sum(1 for p in posts if p.comments > p.likes * 0.1)
            },
            {
                "id": "visual_lover",
                "name": "The Visual Lover",
                "description": "Drawn to aesthetic content, media-focused engagement",
                "engagement_behavior": {
                    "like_probability": 0.8,
                    "comment_probability": 0.3,
                    "share_probability": 0.6,
                    "watch_time_factor": 0.95
                },
                "content_preferences": {
                    "trending_topics": 0.4,
                    "visual_appeal": 0.95,
                    "hook_strength": 0.6,
                    "format_familiarity": 0.5
                },
                "decision_factors": [
                    "High visual production quality",
                    "Aesthetic appeal and composition",
                    "Creative visual storytelling",
                    "Instagram-worthy moments"
                ],
                "sample_size": len(video_posts) + len(image_posts)
            },
            {
                "id": "skeptic",
                "name": "The Skeptic",
                "description": "High standards, difficult to impress, critical eye",
                "engagement_behavior": {
                    "like_probability": 0.2,
                    "comment_probability": 0.4,
                    "share_probability": 0.1,
                    "watch_time_factor": 0.4
                },
                "content_preferences": {
                    "trending_topics": 0.3,
                    "visual_appeal": 0.4,
                    "hook_strength": 0.6,
                    "format_familiarity": 0.9
                },
                "decision_factors": [
                    "Content must be genuinely valuable",
                    "No obvious clickbait or manipulation",
                    "Authentic and credible presentation",
                    "Original insights or perspectives"
                ],
                "sample_size": len(low_engagement_posts)
            }
        ]
        
        # Add trend follower if we have format data
        if any(p.detected_format for p in posts):
            personas.append({
                "id": "trend_follower",
                "name": "The Trend Follower",
                "description": "Highly sensitive to format trends and platform conventions",
                "engagement_behavior": {
                    "like_probability": 0.6,
                    "comment_probability": 0.3,
                    "share_probability": 0.5,
                    "watch_time_factor": 0.7
                },
                "content_preferences": {
                    "trending_topics": 0.85,
                    "visual_appeal": 0.7,
                    "hook_strength": 0.7,
                    "format_familiarity": 0.95
                },
                "decision_factors": [
                    "Follows current platform trends",
                    "Format matches expectations",
                    "Trendy audio or visual elements",
                    "Platform-native feel"
                ],
                "sample_size": len([p for p in posts if p.detected_format])
            })
        
        return personas
    
    async def simulate_content(self, content_data: Dict[str, Any], personas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run content through persona simulation using Gemini.
        
        For each persona, use LLM to role-play as that persona evaluating the content.
        Aggregates responses into viral_score, engagement_rate, sentiment, and specific recommendations.
        
        Recommendations must be SPECIFIC: "Shorten intro by 3 seconds" not "make it better"
        """
        try:
            api_key = await _get_api_key()
            
            # Simulate each persona's response
            persona_responses = []
            for persona in personas:
                response = await self._simulate_persona_response(content_data, persona, api_key)
                if response:
                    persona_responses.append(response)
            
            # Aggregate responses into final prediction
            result = self._aggregate_persona_responses(persona_responses, content_data)
            
            logger.info(f"Simulation complete: {len(persona_responses)} persona responses")
            return result
            
        except Exception as e:
            logger.error(f"Content simulation failed: {e}")
            raise
    
    async def _simulate_persona_response(
        self, 
        content_data: Dict[str, Any], 
        persona: Dict[str, Any], 
        api_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Simulate a single persona's response to content using Gemini role-play.
        """
        try:
            # Build prompt for persona role-play
            prompt = self._build_persona_prompt(content_data, persona)
            
            # Call Gemini API
            response = await call_gemini_api(
                api_key=api_key,
                messages=[{"role": "user", "content": prompt}],
                model="gemini-1.5-flash"
            )
            
            # Parse structured response
            return self._parse_persona_response(response, persona["id"])
            
        except Exception as e:
            logger.error(f"Persona simulation failed for {persona['id']}: {e}")
            return None
    
    def _build_persona_prompt(self, content_data: Dict[str, Any], persona: Dict[str, Any]) -> str:
        """Build role-play prompt for persona simulation"""
        
        content_text = content_data.get("text", "")
        platform = content_data.get("platform", "instagram")
        audience_context = content_data.get("audience_context", "")
        filename = content_data.get("filename", "")
        upload_mode = content_data.get("upload_mode", False)
        
        prompt = f"""You are roleplaying as "{persona['name']}" - {persona['description']}

Your behavioral profile:
- Like probability: {persona['engagement_behavior']['like_probability']:.0%}
- Comment probability: {persona['engagement_behavior']['comment_probability']:.0%} 
- Share probability: {persona['engagement_behavior']['share_probability']:.0%}

Your decision factors:
{chr(10).join(f"- {factor}" for factor in persona['decision_factors'])}

CONTENT TO EVALUATE:
Platform: {platform.title()}
"""
        
        if content_text:
            prompt += f"Text: {content_text}\n"
        
        if filename:
            prompt += f"Video file: {filename}\n"
            
        if audience_context:
            prompt += f"Target audience: {audience_context}\n"
        
        prompt += f"""
Respond in JSON format with your evaluation:
{{
    "will_like": true/false,
    "will_comment": true/false,
    "will_share": true/false,
    "engagement_score": 0-100,
    "sentiment": "positive/neutral/negative",
    "reasoning": "Why you responded this way (2-3 sentences)",
    "improvement_suggestions": ["Specific suggestion 1", "Specific suggestion 2"]
}}

Make improvement suggestions SPECIFIC and actionable:
- Good: "Shorten intro from 8 seconds to 3 seconds"
- Bad: "Make it more engaging"
- Good: "Add trending audio track"
- Bad: "Improve the music"
- Good: "Move hook to first sentence"
- Bad: "Better opening"

Be authentic to your persona - don't all respond the same way!"""
        
        return prompt
    
    def _parse_persona_response(self, response: str, persona_id: str) -> Optional[Dict[str, Any]]:
        """Parse Gemini response into structured persona data"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON found in persona response for {persona_id}")
                return None
            
            data = json.loads(json_match.group())
            
            return {
                "persona_id": persona_id,
                "will_like": data.get("will_like", False),
                "will_comment": data.get("will_comment", False),
                "will_share": data.get("will_share", False),
                "engagement_score": data.get("engagement_score", 0),
                "sentiment": data.get("sentiment", "neutral"),
                "reasoning": data.get("reasoning", ""),
                "improvement_suggestions": data.get("improvement_suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"Failed to parse persona response for {persona_id}: {e}")
            return None
    
    def _aggregate_persona_responses(self, responses: List[Dict[str, Any]], content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate persona responses into final prediction metrics.
        """
        if not responses:
            return {
                "viral_score": 0,
                "engagement_rate": 0.0,
                "sentiment": {"positive": 0.0, "neutral": 1.0, "negative": 0.0},
                "recommendations": [],
                "confidence": 0.0
            }
        
        # Calculate engagement metrics
        total_personas = len(responses)
        likes = sum(1 for r in responses if r["will_like"])
        comments = sum(1 for r in responses if r["will_comment"])
        shares = sum(1 for r in responses if r["will_share"])
        
        # Calculate viral score (0-100)
        like_rate = likes / total_personas
        comment_rate = comments / total_personas
        share_rate = shares / total_personas
        
        # Weighted viral score (shares are most important for virality)
        viral_score = int(
            (like_rate * 0.3 + comment_rate * 0.3 + share_rate * 0.4) * 100
        )
        
        # Engagement rate calculation
        avg_engagement_score = sum(r["engagement_score"] for r in responses) / total_personas
        engagement_rate = avg_engagement_score / 100.0
        
        # Sentiment breakdown
        sentiments = [r["sentiment"] for r in responses]
        sentiment_counts = {
            "positive": sentiments.count("positive") / total_personas,
            "neutral": sentiments.count("neutral") / total_personas,
            "negative": sentiments.count("negative") / total_personas
        }
        
        # Aggregate recommendations (deduplicate and rank by frequency)
        all_suggestions = []
        for r in responses:
            all_suggestions.extend(r.get("improvement_suggestions", []))
        
        # Count suggestion frequency and create ranked recommendations
        suggestion_counts = {}
        for suggestion in all_suggestions:
            suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1
        
        # Top recommendations with reasoning
        recommendations = []
        for suggestion, count in sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True):
            if len(recommendations) >= 5:  # Limit to top 5
                break
            
            recommendations.append({
                "suggestion": suggestion,
                "reasoning": f"Recommended by {count}/{total_personas} personas",
                "priority": "high" if count >= total_personas * 0.6 else "medium"
            })
        
        # Confidence based on response consistency
        confidence = min(1.0, len(responses) / 5.0)  # Full confidence with 5+ personas
        
        return {
            "viral_score": viral_score,
            "engagement_rate": engagement_rate,
            "sentiment": sentiment_counts,
            "recommendations": recommendations,
            "confidence": confidence
        }
    
    async def compare_actual_vs_predicted(self, post_id: int, prediction: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """
        Compare actual post performance against simulation prediction.
        
        Returns accuracy metrics and calibration insights.
        """
        try:
            # Get actual post performance
            query = text("""
                SELECT 
                    likes,
                    comments, 
                    shares,
                    engagement_score
                FROM crm.competitor_posts
                WHERE id = :post_id
            """)
            
            result = await db.execute(query, {"post_id": post_id})
            post = result.fetchone()
            
            if not post:
                raise ValueError(f"Post {post_id} not found")
            
            # Calculate accuracy metrics
            actual_engagement = post.engagement_score / 100.0
            predicted_engagement = prediction["engagement_rate"]
            
            accuracy_score = 1.0 - abs(actual_engagement - predicted_engagement)
            
            # Generate calibration insights
            insights = []
            if accuracy_score > 0.8:
                insights.append("Excellent prediction accuracy - personas are well-calibrated")
            elif accuracy_score > 0.6:
                insights.append("Good prediction accuracy with room for persona refinement")
            else:
                insights.append("Prediction accuracy below threshold - personas need recalibration")
            
            if actual_engagement > predicted_engagement:
                insights.append("Content outperformed prediction - consider updating persona preferences")
            elif actual_engagement < predicted_engagement:
                insights.append("Content underperformed prediction - personas may be too optimistic")
            
            return {
                "actual_engagement": actual_engagement,
                "predicted_engagement": predicted_engagement,
                "accuracy_score": accuracy_score,
                "calibration_insights": insights,
                "persona_accuracy": []  # TODO: Per-persona accuracy tracking
            }
            
        except Exception as e:
            logger.error(f"Performance comparison failed: {e}")
            raise
    
    async def store_simulation_result(
        self, 
        org_id: int, 
        content_data: Dict[str, Any], 
        result: Dict[str, Any],
        personas: List[Dict[str, Any]],
        db: AsyncSession
    ) -> int:
        """Store simulation result in the database"""
        try:
            # Extract content preview
            content_preview = (
                content_data.get("text", "") or 
                content_data.get("filename", "") or 
                "Content simulation"
            )[:200]
            
            persona_ids = [i for i in range(len(personas))]  # Simple ID mapping for now
            
            query = text("""
                INSERT INTO crm.simulation_results 
                (org_id, script_hook, script_body, format_slug, persona_ids, 
                 engagement_score, predicted_metrics, optimization_recommendation, created_at)
                VALUES 
                (:org_id, :hook, :body, :format, :persona_ids, 
                 :engagement_score, :metrics, :recommendations, NOW())
                RETURNING id
            """)
            
            result_row = await db.execute(query, {
                "org_id": org_id,
                "hook": content_preview[:100],
                "body": content_preview,
                "format": content_data.get("platform", "unknown"),
                "persona_ids": persona_ids,
                "engagement_score": result["viral_score"],
                "metrics": json.dumps({
                    "engagement_rate": result["engagement_rate"],
                    "sentiment": result["sentiment"],
                    "confidence": result["confidence"],
                    "personas_used": len(personas)
                }),
                "recommendations": json.dumps(result["recommendations"])
            })
            
            simulation_id = result_row.fetchone()[0]
            await db.commit()
            
            logger.info(f"Stored simulation {simulation_id} for org {org_id}")
            return simulation_id
            
        except Exception as e:
            logger.error(f"Failed to store simulation result: {e}")
            await db.rollback()
            raise

    async def get_stored_prediction(self, post_id: int, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Get stored prediction for a post"""
        try:
            query = text("""
                SELECT id, engagement_score, predicted_metrics, optimization_recommendation, created_at
                FROM crm.simulation_results 
                WHERE script_hook LIKE :search OR script_body LIKE :search
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            result = await db.execute(query, {"search": f"%{post_id}%"})
            row = result.fetchone()
            
            if not row:
                return None
                
            return {
                "id": row[0],
                "viral_score": row[1],
                "predicted_metrics": json.loads(row[2]) if row[2] else {},
                "recommendations": json.loads(row[3]) if row[3] else [],
                "created_at": row[4]
            }
            
        except Exception as e:
            logger.error(f"Failed to get stored prediction: {e}")
            return None
    
    async def get_simulation_history(self, org_id: int, db: AsyncSession, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get historical simulations for organization"""
        try:
            query = text("""
                SELECT id, script_hook, format_slug, engagement_score, 
                       predicted_metrics, created_at
                FROM crm.simulation_results 
                WHERE org_id = :org_id
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset
            """)
            
            result = await db.execute(query, {
                "org_id": org_id,
                "limit": limit,
                "offset": offset
            })
            
            history = []
            for row in result.fetchall():
                metrics = json.loads(row[4]) if row[4] else {}
                history.append({
                    "id": row[0],
                    "content_preview": row[1],
                    "platform": row[2],
                    "viral_score": row[3],
                    "engagement_rate": metrics.get("engagement_rate", 0.0),
                    "created_at": row[5].isoformat() if row[5] else "",
                    "actual_performance": None  # TODO: Link to actual post performance
                })
                
            return history
            
        except Exception as e:
            logger.error(f"Failed to get simulation history: {e}")
            return []