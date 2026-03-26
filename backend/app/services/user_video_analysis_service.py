"""User Video Analysis Service for Profile Intel
Analyzes user's own videos using the same pipeline as competitor analysis.
Integrates with OAuth-detected Instagram account and media-understanding service.
"""

import logging
import json
import tempfile
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_
import httpx
import subprocess as sp

from app.models.crm.social import SocialAccount
from app.models.crm.profile_intel_data import ProfileIntelData

logger = logging.getLogger(__name__)

@dataclass
class VideoGradeDetails:
    """Detailed breakdown of video analysis."""
    video_id: str
    title: str
    grade: str  # A-F
    hook_strength: int  # 0-5
    pacing_score: int  # 0-100
    structure_score: int  # 0-100
    cta_effectiveness: int  # 0-100
    visual_quality: int  # 0-100
    strengths: List[str]
    weaknesses: List[str]
    engagement_metrics: Dict[str, Any]
    duration: float

class UserVideoAnalysisService:
    """Service for analyzing user's own videos through the full pipeline."""
    
    def __init__(self):
        self.media_api_url = os.getenv("MEDIA_UNDERSTANDING_URL", "http://localhost:18796")
        self.scraper_url = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:18797")
    
    async def analyze_user_videos(
        self,
        db: AsyncSession,
        org_id: int,
        user_id: int,
        platform: str = "instagram",
        force_reanalysis: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point: Auto-detect OAuth account + analyze user's videos.
        
        1. Auto-detect user's OAuth-connected Instagram handle from crm.social_accounts
        2. Scrape user's last 5 video post URLs using existing scraper infrastructure
        3. Download each video via yt-dlp
        4. Run each through media-understanding service for frame-by-frame analysis
        5. Extract per-video metrics and store results
        
        Returns analysis summary and video grades.
        """
        try:
            logger.info(f"Starting user video analysis for org_id={org_id}, user_id={user_id}, platform={platform}")
            
            # Step 1: Auto-detect user's OAuth-connected Instagram handle
            oauth_account = await self._get_oauth_account(db, org_id, user_id, platform)
            if not oauth_account:
                return {
                    "success": False,
                    "error": "No connected Instagram account found. Connect your account first.",
                    "videos_analyzed": 0
                }
            
            username = oauth_account.username
            logger.info(f"Found OAuth account: {username} on {platform}")
            
            # Step 2: Scrape user's last 5 video post URLs
            video_urls = await self._scrape_user_videos(username, limit=5)
            if not video_urls:
                return {
                    "success": False,
                    "error": "No videos found on user profile",
                    "videos_analyzed": 0
                }
            
            logger.info(f"Found {len(video_urls)} videos for user {username}")
            
            # Step 3-5: Analyze each video
            analyzed_videos = []
            for i, video_data in enumerate(video_urls):
                try:
                    video_analysis = await self._analyze_single_video(
                        video_data["url"], 
                        video_data["title"],
                        video_data.get("engagement_metrics", {})
                    )
                    analyzed_videos.append(video_analysis)
                    logger.info(f"Analyzed video {i+1}/{len(video_urls)}: {video_data['title']} -> Grade {video_analysis.grade}")
                    
                except Exception as e:
                    logger.error(f"Failed to analyze video {video_data['title']}: {e}")
                    # Create failure entry
                    analyzed_videos.append(VideoGradeDetails(
                        video_id=f"failed_{i}",
                        title=video_data.get("title", "Failed Video"),
                        grade="F",
                        hook_strength=0,
                        pacing_score=0,
                        structure_score=0,
                        cta_effectiveness=0,
                        visual_quality=0,
                        strengths=[],
                        weaknesses=[f"Analysis failed: {str(e)[:100]}"],
                        engagement_metrics=video_data.get("engagement_metrics", {}),
                        duration=0
                    ))
            
            # Store results in ProfileIntelData
            await self._store_video_analysis_results(db, org_id, username, platform, analyzed_videos)
            
            # Calculate Video Messaging + Storyboarding grades
            video_messaging_grade, storyboarding_grade = self._calculate_video_grades(analyzed_videos)
            
            return {
                "success": True,
                "username": username,
                "videos_analyzed": len(analyzed_videos),
                "video_messaging_grade": video_messaging_grade,
                "storyboarding_grade": storyboarding_grade,
                "analyzed_videos": [
                    {
                        "title": v.title,
                        "grade": v.grade,
                        "hook_strength": v.hook_strength,
                        "strengths": v.strengths,
                        "weaknesses": v.weaknesses,
                        "duration": v.duration
                    }
                    for v in analyzed_videos
                ]
            }
            
        except Exception as e:
            logger.error(f"User video analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "videos_analyzed": 0
            }
    
    async def _get_oauth_account(
        self, 
        db: AsyncSession, 
        org_id: int, 
        user_id: int, 
        platform: str
    ) -> Optional[SocialAccount]:
        """Auto-detect user's OAuth-connected social account."""
        result = await db.execute(
            select(SocialAccount).where(
                and_(
                    SocialAccount.org_id == org_id,
                    SocialAccount.user_id == user_id,
                    SocialAccount.platform == platform.lower(),
                    SocialAccount.status == "connected"
                )
            ).order_by(SocialAccount.last_synced.desc().nulls_last())
        )
        return result.scalar_one_or_none()
    
    async def _scrape_user_videos(self, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape user's video posts using existing scraper infrastructure.
        Returns list of video URLs with metadata.
        """
        try:
            # Use the same scraper service as competitor analysis
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.scraper_url}/scrape",
                    json={
                        "url": f"https://instagram.com/{username}",
                        "platform": "instagram",
                        "include_posts": True,
                        "max_posts": limit * 2  # Get extra in case some aren't videos
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("error"):
                raise Exception(f"Scraper error: {data['error']}")
            
            # Filter for video posts only
            video_posts = []
            posts = data.get("posts", [])
            
            for post in posts:
                if post.get("media_type") in ["video", "reel", "igtv"] and post.get("media_url"):
                    video_posts.append({
                        "url": post["media_url"],
                        "title": (post.get("caption") or "Untitled")[:50] + "...",
                        "post_id": post.get("id", ""),
                        "engagement_metrics": {
                            "likes": post.get("likes", 0),
                            "comments": post.get("comments", 0),
                            "views": post.get("video_views", 0),
                            "shares": post.get("shares", 0),
                            "saves": post.get("saves", 0)
                        }
                    })
                
                if len(video_posts) >= limit:
                    break
            
            return video_posts
            
        except Exception as e:
            logger.error(f"Failed to scrape user videos for {username}: {e}")
            return []
    
    async def _analyze_single_video(
        self, 
        video_url: str, 
        title: str, 
        engagement_metrics: Dict[str, Any]
    ) -> VideoGradeDetails:
        """
        Analyze single video through the full pipeline:
        1. Download via yt-dlp
        2. Media understanding analysis (/analyze, /frames, /transcript)
        3. Extract metrics and grade
        """
        # Step 1: Download video
        video_path = await self._download_video(video_url)
        
        try:
            # Step 2: Media understanding analysis
            analysis_result = await self._run_media_analysis(video_path)
            
            # Step 3: Extract detailed metrics
            video_details = await self._extract_video_metrics(
                analysis_result, title, engagement_metrics
            )
            
            return video_details
            
        finally:
            # Cleanup
            if os.path.exists(video_path):
                os.unlink(video_path)
    
    async def _download_video(self, video_url: str) -> str:
        """Download video using yt-dlp (handles Instagram)."""
        temp_path = tempfile.mktemp(suffix='.mp4', dir='/tmp')
        
        try:
            # Use yt-dlp for Instagram video downloads
            result = await asyncio.to_thread(
                sp.run,
                [
                    "yt-dlp", 
                    "--no-warnings", 
                    "--quiet", 
                    "-o", temp_path,
                    "--max-filesize", "100M", 
                    "--format", "mp4/best[ext=mp4]/best",
                    video_url
                ],
                capture_output=True, text=True, timeout=90
            )
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
                logger.info(f"Downloaded video: {os.path.getsize(temp_path) // 1024}KB")
                return temp_path
            
            logger.warning(f"yt-dlp failed for {video_url[:50]}...")
            
        except Exception as e:
            logger.error(f"Video download failed: {e}")
        
        # Fallback: Direct HTTP download
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(video_url)
                response.raise_for_status()
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                if os.path.getsize(temp_path) > 1000:
                    return temp_path
        
        except Exception as e:
            logger.error(f"HTTP download fallback failed: {e}")
        
        raise Exception(f"Could not download video from {video_url[:50]}...")
    
    async def _run_media_analysis(self, video_path: str) -> Dict[str, Any]:
        """Run full media understanding analysis."""
        analysis_data = {}
        
        # Main analysis
        analysis_data["analysis"] = await self._call_media_api("/analyze", {"file_path": video_path})
        
        # Frame-by-frame analysis
        analysis_data["frames"] = await self._call_media_api("/frames", {"file_path": video_path})
        
        # Transcript with timestamps
        analysis_data["transcript"] = await self._call_media_api("/transcript", {"file_path": video_path})
        
        # Probe for duration/metadata
        analysis_data["probe"] = await self._call_media_api("/probe", {"file_path": video_path})
        
        return analysis_data
    
    async def _call_media_api(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call media understanding API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.media_api_url}{endpoint}", json=payload)
                response.raise_for_status()
                result = response.json()
            
            if result.get("isError"):
                error_text = ""
                for item in result.get("content", []):
                    if item.get("type") == "text":
                        error_text += item.get("text", "")
                raise Exception(f"API error: {error_text[:200]}")
            
            return result
            
        except Exception as e:
            logger.error(f"Media API call failed for {endpoint}: {e}")
            return {"error": str(e)}
    
    async def _extract_video_metrics(
        self, 
        analysis_result: Dict[str, Any], 
        title: str,
        engagement_metrics: Dict[str, Any]
    ) -> VideoGradeDetails:
        """Extract detailed video metrics and assign grade."""
        
        # Get duration from probe
        duration = 0.0
        probe_data = analysis_result.get("probe", {})
        if probe_data and not probe_data.get("error"):
            duration = probe_data.get("duration", 0.0)
        
        # Analyze hook strength (first 3 seconds)
        hook_strength = await self._analyze_hook_strength(analysis_result)
        
        # Analyze pacing throughout video
        pacing_score = await self._analyze_pacing(analysis_result, duration)
        
        # Analyze structure (hook -> value -> CTA)
        structure_score = await self._analyze_structure(analysis_result)
        
        # Analyze CTA effectiveness
        cta_effectiveness = await self._analyze_cta_effectiveness(analysis_result)
        
        # Analyze visual quality
        visual_quality = await self._analyze_visual_quality(analysis_result)
        
        # Calculate overall grade
        overall_numeric = (
            hook_strength * 20 +  # Hook is crucial 
            pacing_score * 0.2 +  # Pacing
            structure_score * 0.3 +  # Structure  
            cta_effectiveness * 0.15 +  # CTA
            visual_quality * 0.15  # Visual quality
        )
        
        grade_letter = self._numeric_to_letter_grade(overall_numeric)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(
            hook_strength, pacing_score, structure_score, 
            cta_effectiveness, visual_quality, analysis_result
        )
        
        return VideoGradeDetails(
            video_id=f"user_video_{hash(title)}",
            title=title,
            grade=grade_letter,
            hook_strength=hook_strength,
            pacing_score=pacing_score,
            structure_score=structure_score,
            cta_effectiveness=cta_effectiveness,
            visual_quality=visual_quality,
            strengths=strengths,
            weaknesses=weaknesses,
            engagement_metrics=engagement_metrics,
            duration=duration
        )
    
    async def _analyze_hook_strength(self, analysis_result: Dict[str, Any]) -> int:
        """Analyze hook strength (0-5 scale) based on first 3 seconds."""
        try:
            # Get transcript data
            transcript_data = analysis_result.get("transcript", {})
            if transcript_data.get("error"):
                return 2  # Default if no transcript
            
            transcript_content = transcript_data.get("content", [])
            first_3s_text = []
            
            # Extract text from first 3 seconds
            for item in transcript_content:
                if item.get("type") == "text":
                    text_data = item.get("text", "")
                    try:
                        parsed = json.loads(text_data)
                        for entry in parsed:
                            if entry.get("start", 0) <= 3.0:
                                first_3s_text.append(entry.get("text", ""))
                    except json.JSONDecodeError:
                        # Plain text
                        first_3s_text.append(text_data[:100])
            
            hook_text = " ".join(first_3s_text).lower()
            
            # Analyze hook elements
            hook_score = 1  # Base score
            
            # Strong hook indicators
            strong_hooks = [
                "what if", "imagine", "stop", "wait", "here's why", "secret",
                "mistake", "truth", "exposed", "shocking", "revealed"
            ]
            
            if any(phrase in hook_text for phrase in strong_hooks):
                hook_score += 2
            
            # Question hooks
            if "?" in hook_text or any(word in hook_text for word in ["how", "why", "what", "when"]):
                hook_score += 1
            
            # Action/urgency
            if any(word in hook_text for word in ["now", "today", "must", "need to"]):
                hook_score += 1
            
            # Personal/direct address
            if any(word in hook_text for word in ["you", "your", "yourself"]):
                hook_score += 1
            
            return min(5, hook_score)
            
        except Exception as e:
            logger.error(f"Hook analysis failed: {e}")
            return 2
    
    async def _analyze_pacing(self, analysis_result: Dict[str, Any], duration: float) -> int:
        """Analyze pacing score (0-100) based on frame changes and speech speed."""
        try:
            # Get frames data  
            frames_data = analysis_result.get("frames", {})
            if frames_data.get("error"):
                return 50  # Default
            
            frame_content = frames_data.get("content", [])
            frame_count = 0
            
            for item in frame_content:
                if item.get("type") == "image":
                    frame_count += 1
            
            if duration == 0:
                return 50
            
            # Calculate frames per second rate
            fps_effective = frame_count / duration
            
            # Ideal range: 0.5-2 significant frames per second
            if 0.5 <= fps_effective <= 2.0:
                pacing_score = 90
            elif 0.3 <= fps_effective <= 3.0:
                pacing_score = 75
            elif fps_effective < 0.3:
                pacing_score = 40  # Too slow
            else:
                pacing_score = 60  # Too fast
            
            # Adjust based on transcript speech rate
            transcript_data = analysis_result.get("transcript", {})
            if not transcript_data.get("error"):
                transcript_content = transcript_data.get("content", [])
                total_words = 0
                
                for item in transcript_content:
                    if item.get("type") == "text":
                        text_data = item.get("text", "")
                        total_words += len(text_data.split())
                
                words_per_minute = (total_words / duration) * 60 if duration > 0 else 0
                
                # Ideal: 140-180 WPM
                if 140 <= words_per_minute <= 180:
                    pacing_score = min(100, pacing_score + 10)
                elif words_per_minute < 100:
                    pacing_score = max(0, pacing_score - 20)  # Too slow
                elif words_per_minute > 220:
                    pacing_score = max(0, pacing_score - 15)  # Too fast
            
            return min(100, max(0, pacing_score))
            
        except Exception as e:
            logger.error(f"Pacing analysis failed: {e}")
            return 50
    
    async def _analyze_structure(self, analysis_result: Dict[str, Any]) -> int:
        """Analyze video structure (0-100) for hook -> value -> CTA flow."""
        try:
            transcript_data = analysis_result.get("transcript", {})
            if transcript_data.get("error"):
                return 40  # Default
            
            transcript_content = transcript_data.get("content", [])
            all_text = []
            
            for item in transcript_content:
                if item.get("type") == "text":
                    all_text.append(item.get("text", ""))
            
            full_transcript = " ".join(all_text).lower()
            
            # Look for structure elements
            has_hook = any(word in full_transcript[:200] for word in [
                "what", "why", "how", "imagine", "secret", "mistake", 
                "truth", "revealed", "stop"
            ])
            
            has_value = any(word in full_transcript for word in [
                "tip", "hack", "way", "method", "solution", "answer",
                "because", "reason", "example", "show", "teach"
            ])
            
            has_cta = any(word in full_transcript[-200:] for word in [
                "follow", "subscribe", "like", "comment", "share",
                "check out", "link", "bio", "more"
            ])
            
            # Score based on structure components
            structure_score = 0
            if has_hook:
                structure_score += 40
            if has_value:
                structure_score += 40  
            if has_cta:
                structure_score += 20
            
            return min(100, structure_score)
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return 40
    
    async def _analyze_cta_effectiveness(self, analysis_result: Dict[str, Any]) -> int:
        """Analyze CTA effectiveness (0-100) based on clarity and placement."""
        try:
            transcript_data = analysis_result.get("transcript", {})
            if transcript_data.get("error"):
                return 30
            
            transcript_content = transcript_data.get("content", [])
            last_quarter_text = []
            
            # Get text from last 25% of video
            for item in transcript_content:
                if item.get("type") == "text":
                    text_data = item.get("text", "")
                    try:
                        parsed = json.loads(text_data)
                        # Assuming transcript entries have timestamps
                        for entry in parsed:
                            # For now, just use last portion of text
                            last_quarter_text.append(entry.get("text", ""))
                    except json.JSONDecodeError:
                        last_quarter_text.append(text_data)
            
            cta_text = " ".join(last_quarter_text[-3:]).lower()  # Last 3 chunks
            
            # Analyze CTA strength
            weak_ctas = ["follow for more", "like if you agree", "subscribe"]
            medium_ctas = ["check out", "link in bio", "dm me"]
            strong_ctas = ["download", "book a call", "get started", "try this", "click here"]
            
            if any(cta in cta_text for cta in strong_ctas):
                return 90
            elif any(cta in cta_text for cta in medium_ctas):
                return 70
            elif any(cta in cta_text for cta in weak_ctas):
                return 50
            else:
                return 20  # No clear CTA
            
        except Exception as e:
            logger.error(f"CTA analysis failed: {e}")
            return 30
    
    async def _analyze_visual_quality(self, analysis_result: Dict[str, Any]) -> int:
        """Analyze visual quality (0-100) based on frame analysis."""
        try:
            frames_data = analysis_result.get("frames", {})
            if frames_data.get("error"):
                return 60
            
            frame_content = frames_data.get("content", [])
            frame_descriptions = []
            
            for item in frame_content:
                if item.get("type") == "image" and item.get("text"):
                    frame_descriptions.append(item.get("text", "").lower())
            
            if not frame_descriptions:
                return 60
            
            all_descriptions = " ".join(frame_descriptions)
            
            # Quality indicators
            quality_score = 60  # Base score
            
            # Positive indicators
            if any(word in all_descriptions for word in [
                "clear", "bright", "professional", "good lighting", "high quality"
            ]):
                quality_score += 20
            
            # Negative indicators  
            if any(word in all_descriptions for word in [
                "blurry", "dark", "poor", "low quality", "pixelated", "grainy"
            ]):
                quality_score -= 20
            
            # Face/person visibility (good for engagement)
            if "person" in all_descriptions or "face" in all_descriptions:
                quality_score += 10
            
            # Text overlay usage
            if "text" in all_descriptions or "overlay" in all_descriptions:
                quality_score += 10
            
            return min(100, max(0, quality_score))
            
        except Exception as e:
            logger.error(f"Visual quality analysis failed: {e}")
            return 60
    
    def _identify_strengths_weaknesses(
        self, hook_strength: int, pacing_score: int, structure_score: int,
        cta_effectiveness: int, visual_quality: int, analysis_result: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Identify specific strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        # Hook analysis
        if hook_strength >= 4:
            strengths.append("Strong opening hook captures attention")
        elif hook_strength <= 2:
            weaknesses.append("Weak hook - viewers likely scroll past in first 3 seconds")
        
        # Pacing analysis
        if pacing_score >= 80:
            strengths.append("Good pacing keeps viewers engaged")
        elif pacing_score <= 40:
            weaknesses.append("Poor pacing - too slow or too fast for audience retention")
        
        # Structure analysis
        if structure_score >= 80:
            strengths.append("Well-structured content with clear hook -> value -> CTA flow")
        elif structure_score <= 50:
            weaknesses.append("Lacks clear structure - missing hook, value, or call-to-action")
        
        # CTA analysis
        if cta_effectiveness >= 80:
            strengths.append("Strong call-to-action drives specific action")
        elif cta_effectiveness <= 40:
            weaknesses.append("Weak or missing call-to-action - missed conversion opportunity")
        
        # Visual quality
        if visual_quality >= 80:
            strengths.append("High visual quality and professional appearance")
        elif visual_quality <= 50:
            weaknesses.append("Poor visual quality hurts credibility and engagement")
        
        return strengths, weaknesses
    
    def _numeric_to_letter_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90: return "A+"
        elif score >= 85: return "A"
        elif score >= 80: return "A-"
        elif score >= 75: return "B+"
        elif score >= 70: return "B"
        elif score >= 65: return "B-"
        elif score >= 60: return "C+"
        elif score >= 55: return "C"
        elif score >= 50: return "C-"
        elif score >= 45: return "D+"
        elif score >= 40: return "D"
        elif score >= 35: return "D-"
        else: return "F"
    
    async def _store_video_analysis_results(
        self,
        db: AsyncSession,
        org_id: int,
        username: str,
        platform: str,
        analyzed_videos: List[VideoGradeDetails]
    ) -> None:
        """Store video analysis results in ProfileIntelData."""
        try:
            # Convert to storage format
            video_data = []
            for video in analyzed_videos:
                video_data.append({
                    "videoId": video.video_id,
                    "title": video.title,
                    "grade": video.grade,
                    "hookStrength": video.hook_strength,
                    "pacingScore": video.pacing_score,
                    "structureScore": video.structure_score,
                    "ctaEffectiveness": video.cta_effectiveness,
                    "visualQuality": video.visual_quality,
                    "strengths": video.strengths,
                    "weaknesses": video.weaknesses,
                    "duration": video.duration,
                    "engagementMetrics": video.engagement_metrics,
                    "analyzedAt": datetime.utcnow().isoformat()
                })
            
            # Check if ProfileIntelData exists
            result = await db.execute(
                select(ProfileIntelData).where(
                    and_(
                        ProfileIntelData.org_id == org_id,
                        ProfileIntelData.profile_id == username,
                        ProfileIntelData.platform == platform
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing record
                existing.processed_videos = video_data
                existing.updated_at = datetime.utcnow()
            else:
                # Create new record
                profile_intel = ProfileIntelData(
                    org_id=org_id,
                    profile_id=username,
                    platform=platform,
                    oauth_data={},
                    scraped_data={},
                    processed_videos=video_data,
                    grades={},
                    recommendations={},
                    last_synced_at=datetime.utcnow()
                )
                db.add(profile_intel)
            
            await db.commit()
            logger.info(f"Stored video analysis for {len(analyzed_videos)} videos")
            
        except Exception as e:
            logger.error(f"Failed to store video analysis results: {e}")
            await db.rollback()
    
    def _calculate_video_grades(
        self, analyzed_videos: List[VideoGradeDetails]
    ) -> Tuple[int, int]:
        """Calculate Video Messaging and Storyboarding grades from analyzed videos."""
        
        if not analyzed_videos:
            return 0, 0
        
        # Filter successful analyses
        successful_videos = [v for v in analyzed_videos if v.grade != "F"]
        
        if not successful_videos:
            return 0, 0
        
        # Video Messaging Grade (hook + CTA)
        avg_hook = sum(v.hook_strength * 20 for v in successful_videos) / len(successful_videos)  # Convert to 0-100
        avg_cta = sum(v.cta_effectiveness for v in successful_videos) / len(successful_videos)
        video_messaging = int((avg_hook + avg_cta) / 2)
        
        # Storyboarding Grade (structure + pacing)
        avg_structure = sum(v.structure_score for v in successful_videos) / len(successful_videos)
        avg_pacing = sum(v.pacing_score for v in successful_videos) / len(successful_videos)
        storyboarding = int((avg_structure + avg_pacing) / 2)
        
        return video_messaging, storyboarding


# Service instance
user_video_analysis_service = UserVideoAnalysisService()