"""Video Analysis Service for Competitor Intel Enhancement
Integrates @dymoo/media-understanding for frame-by-frame video analysis.
"""

import logging
import json
import tempfile
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update
import httpx

logger = logging.getLogger(__name__)

@dataclass
class FrameChunk:
    """8-second video chunk with analysis data"""
    start_time: float
    end_time: float
    duration: float
    frame_url: str
    description: str
    veo_prompt: str
    visual_elements: List[str]
    action_type: str
    pacing: str

class VideoAnalysisService:
    """Service for analyzing competitor videos frame-by-frame"""
    
    def __init__(self):
        self.media_api_url = os.getenv("MEDIA_UNDERSTANDING_URL", "http://localhost:18796")
        self.chunk_duration = 8.0  # VEO optimal duration
    
    async def analyze_competitor_video(
        self,
        db: AsyncSession,
        post_id: int,
        video_url: str,
        force_reanalysis: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze a competitor video and store frame chunks for video generation
        
        Args:
            db: Database session
            post_id: Competitor post ID
            video_url: URL to video file
            force_reanalysis: Re-analyze even if already done
            
        Returns:
            Analysis results with success status
        """
        try:
            # Check if already analyzed (unless forced)
            if not force_reanalysis:
                existing = await db.execute(
                    text("SELECT analysis_status FROM crm.competitor_posts WHERE id = :id"),
                    {"id": post_id}
                )
                status = existing.scalar()
                if status == "completed":
                    logger.info(f"Video post {post_id} already analyzed, skipping")
                    return {"success": True, "status": "already_analyzed"}
            
            # Update status to processing
            await db.execute(
                text("UPDATE crm.competitor_posts SET analysis_status = 'processing' WHERE id = :id"),
                {"id": post_id}
            )
            await db.commit()
            
            # Download video to temp file
            video_path = await self._download_video(video_url)
            
            try:
                # Run full media understanding analysis
                analysis_result = await self._analyze_with_media_understanding(video_path)
                
                # Break into 8-second chunks with VEO prompts
                frame_chunks = await self._create_frame_chunks(video_path, analysis_result)
                
                # Store results in database
                await self._store_analysis_results(db, post_id, analysis_result, frame_chunks)
                
                logger.info(f"Successfully analyzed video post {post_id}, created {len(frame_chunks)} chunks")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "chunks_created": len(frame_chunks),
                    "analysis": analysis_result
                }
                
            finally:
                # Cleanup temp file
                if os.path.exists(video_path):
                    os.unlink(video_path)
                    
        except Exception as e:
            logger.error(f"Video analysis failed for post {post_id}: {e}")
            
            # Update status to failed
            await db.execute(
                text("UPDATE crm.competitor_posts SET analysis_status = 'failed' WHERE id = :id"),
                {"id": post_id}
            )
            await db.commit()
            
            return {
                "success": False,
                "error": str(e),
                "post_id": post_id
            }
    
    async def _download_video(self, video_url: str) -> str:
        """Download video to temporary file using yt-dlp (handles Instagram auth)."""
        import subprocess as sp
        
        temp_path = tempfile.mktemp(suffix='.mp4')
        try:
            result = await asyncio.to_thread(
                sp.run,
                ["yt-dlp", "--no-warnings", "--quiet", "-o", temp_path,
                 "--max-filesize", "100M", "--format", "mp4/best[ext=mp4]/best",
                 video_url],
                capture_output=True, text=True, timeout=90,
            )
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
                logger.info("Downloaded video (%d KB)", os.path.getsize(temp_path) // 1024)
                return temp_path
            logger.warning("yt-dlp failed: %s", result.stderr[:200] if result.stderr else "empty file")
        except Exception as e:
            logger.error("Video download error: %s", e)
        
        # Fallback to direct HTTP (for S3/Garage URLs)
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(video_url)
                response.raise_for_status()
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                if os.path.getsize(temp_path) > 1000:
                    return temp_path
        except Exception as e:
            logger.error("HTTP download fallback failed: %s", e)
        
        raise Exception(f"Could not download video from {video_url[:80]}")
    
    async def _analyze_with_media_understanding(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze video using media-understanding HTTP API service.
        The service runs as a separate Docker container on port 18796.
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.media_api_url}/analyze",
                    json={"file_path": video_path}
                )
                resp.raise_for_status()
                result = resp.json()
            
            if result.get("isError"):
                error_text = ""
                for item in result.get("content", []):
                    if item.get("type") == "text":
                        error_text += item.get("text", "")
                raise Exception(f"Analysis failed: {error_text[:200]}")
            
            # Extract content from the MCP-style response
            content = result.get("content", [])
            analysis_data = {}
            for item in content:
                if item.get("type") == "text":
                    # Try to parse as JSON if it's structured data
                    text_content = item.get("text", "")
                    try:
                        parsed = json.loads(text_content)
                        analysis_data.update(parsed)
                    except json.JSONDecodeError:
                        # If not JSON, store as description
                        analysis_data["description"] = text_content
                elif item.get("type") == "image":
                    # Handle image content (keyframes, etc.)
                    if "keyframes" not in analysis_data:
                        analysis_data["keyframes"] = []
                    analysis_data["keyframes"].append({
                        "url": item.get("data", ""),
                        "timestamp": item.get("timestamp", 0),
                        "description": item.get("text", "")
                    })
            
            return analysis_data
            
        except Exception as e:
            raise Exception(f"Media analysis failed: {str(e)}")
    
    async def _create_frame_chunks(
        self, 
        video_path: str, 
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Break video into 8-second chunks with VEO prompts
        """
        chunks = []
        video_duration = analysis_result.get("duration", 0)
        keyframes = analysis_result.get("keyframes", [])
        transcript = analysis_result.get("transcript", [])
        
        # Create chunks every 8 seconds
        for start_time in range(0, int(video_duration), int(self.chunk_duration)):
            end_time = min(start_time + self.chunk_duration, video_duration)
            
            # Find relevant keyframes for this chunk
            chunk_keyframes = [
                kf for kf in keyframes 
                if start_time <= kf.get("timestamp", 0) <= end_time
            ]
            
            # Find relevant transcript for this chunk
            chunk_text = self._extract_chunk_transcript(transcript, start_time, end_time)
            
            # Generate VEO prompt for this chunk
            veo_prompt = await self._generate_veo_prompt(
                chunk_keyframes, 
                chunk_text, 
                start_time, 
                end_time
            )
            
            # Analyze visual elements and pacing
            visual_analysis = self._analyze_chunk_visuals(chunk_keyframes)
            
            chunk = {
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "frame_urls": [kf.get("url", "") for kf in chunk_keyframes],
                "transcript_text": chunk_text,
                "veo_prompt": veo_prompt,
                "visual_elements": visual_analysis["elements"],
                "action_type": visual_analysis["action_type"],
                "pacing": visual_analysis["pacing"],
                "keyframe_count": len(chunk_keyframes)
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _extract_chunk_transcript(
        self, 
        transcript: List[Dict], 
        start_time: float, 
        end_time: float
    ) -> str:
        """Extract transcript text for a specific time chunk"""
        chunk_text = []
        
        for entry in transcript:
            entry_start = entry.get("start", 0)
            entry_end = entry.get("end", entry_start)
            
            # Include if overlaps with chunk timeframe
            if (start_time <= entry_start <= end_time or 
                start_time <= entry_end <= end_time or
                (entry_start <= start_time and entry_end >= end_time)):
                chunk_text.append(entry.get("text", ""))
        
        return " ".join(chunk_text).strip()
    
    async def _generate_veo_prompt(
        self,
        keyframes: List[Dict],
        transcript_text: str,
        start_time: float,
        end_time: float
    ) -> str:
        """
        Generate a VEO-optimized prompt for this video chunk
        """
        if not keyframes:
            return f"Video segment from {start_time}s to {end_time}s. {transcript_text}"
        
        # Analyze visual changes across keyframes
        visual_descriptions = []
        for kf in keyframes:
            if kf.get("description"):
                visual_descriptions.append(kf["description"])
        
        # Create prompt based on visual progression and audio
        prompt_parts = []
        
        if visual_descriptions:
            if len(visual_descriptions) == 1:
                prompt_parts.append(visual_descriptions[0])
            else:
                # Multiple frames - describe progression
                prompt_parts.append(f"Scene starts with {visual_descriptions[0]}")
                if len(visual_descriptions) > 1:
                    prompt_parts.append(f"transitioning to {visual_descriptions[-1]}")
        
        if transcript_text:
            prompt_parts.append(f"Audio: {transcript_text}")
        
        # Add duration constraint
        duration = end_time - start_time
        prompt_parts.append(f"Duration: {duration:.1f} seconds")
        
        return ". ".join(prompt_parts)
    
    def _analyze_chunk_visuals(self, keyframes: List[Dict]) -> Dict[str, Any]:
        """Analyze visual elements and pacing for a chunk"""
        if not keyframes:
            return {
                "elements": [],
                "action_type": "static",
                "pacing": "unknown"
            }
        
        # Extract visual elements from descriptions
        elements = set()
        action_indicators = []
        
        for kf in keyframes:
            description = kf.get("description", "").lower()
            
            # Detect common visual elements
            if "person" in description or "people" in description:
                elements.add("person")
            if "product" in description:
                elements.add("product")
            if "text" in description or "overlay" in description:
                elements.add("text_overlay")
            if "background" in description:
                elements.add("background")
            
            # Detect action type
            if any(word in description for word in ["moving", "motion", "action", "walking", "running"]):
                action_indicators.append("dynamic")
            elif any(word in description for word in ["static", "still", "portrait"]):
                action_indicators.append("static")
        
        # Determine overall action type
        if len(action_indicators) > 1:
            action_type = "dynamic" if "dynamic" in action_indicators else "mixed"
        elif action_indicators:
            action_type = action_indicators[0]
        else:
            action_type = "unknown"
        
        # Determine pacing based on keyframe density
        pacing = "fast" if len(keyframes) > 6 else "medium" if len(keyframes) > 3 else "slow"
        
        return {
            "elements": list(elements),
            "action_type": action_type,
            "pacing": pacing
        }
    
    async def _store_analysis_results(
        self,
        db: AsyncSession,
        post_id: int,
        analysis_result: Dict[str, Any],
        frame_chunks: List[Dict[str, Any]]
    ) -> None:
        """Store analysis results in database"""
        await db.execute(
            text("""
                UPDATE crm.competitor_posts 
                SET video_analysis = :analysis,
                    frame_chunks = :chunks,
                    analysis_status = 'completed',
                    analyzed_at = NOW()
                WHERE id = :id
            """),
            {
                "id": post_id,
                "analysis": json.dumps(analysis_result),
                "chunks": json.dumps(frame_chunks)
            }
        )
        await db.commit()
    
    async def get_analyzed_videos(
        self,
        db: AsyncSession,
        org_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of analyzed videos for video creation"""
        result = await db.execute(
            text("""
                SELECT cp.id, cp.media_url, cp.frame_chunks, cp.analyzed_at,
                       c.handle, c.platform
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE cp.analysis_status = 'completed'
                  AND cp.org_id = :org_id
                  AND cp.media_type = 'video'
                ORDER BY cp.analyzed_at DESC
                LIMIT :limit
            """),
            {"org_id": org_id, "limit": limit}
        )
        
        videos = []
        for row in result.fetchall():
            videos.append({
                "post_id": row[0],
                "media_url": row[1],
                "frame_chunks": json.loads(row[2]) if row[2] else [],
                "analyzed_at": row[3],
                "competitor_handle": row[4],
                "platform": row[5]
            })
        
        return videos


# Service instance
video_analysis_service = VideoAnalysisService()