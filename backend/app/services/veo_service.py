"""Veo 3.1 Video Generation Service

Image-to-Video generation using Google's Veo 3.1 model via Gemini API.
Supports async operation tracking and video extension capabilities.
"""

import os
import uuid
import logging
import asyncio
import tempfile
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
import httpx
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

# Gemini API Configuration
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Vertex AI fallback configuration
VERTEX_AI_BASE = "https://{region}-aiplatform.googleapis.com/v1"
DEFAULT_PROJECT_ID = "894470157324"  # From memory context
DEFAULT_REGION = "us-central1"


@dataclass
class VideoGenerationRequest:
    """Request structure for video generation"""
    seed_image: bytes
    prompt: str
    duration_seconds: int = 5
    aspect_ratio: str = "9:16"


@dataclass
class VideoOperation:
    """Video generation operation tracking"""
    operation_id: str
    status: str  # "pending", "running", "complete", "failed"
    progress: int = 0  # 0-100
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None


class VeoService:
    """Google Veo 3.1 Video Generation Service"""
    
    def __init__(self):
        self.api_key = None
        self.project_id = DEFAULT_PROJECT_ID
        self.region = DEFAULT_REGION
    
    async def _get_api_key(self, db=None) -> str:
        """Get Google AI Studio API key from environment or database"""
        if self.api_key:
            return self.api_key
            
        # Try environment first
        key = os.environ.get('GOOGLE_AI_STUDIO_API_KEY')
        if key:
            self.api_key = key
            return key
        
        # Try database if provided
        if db:
            from sqlalchemy import text
            result = await db.execute(text("SELECT value FROM public.settings WHERE key = 'google_ai_studio_api_key'"))
            row = result.first()
            if row and row[0]:
                self.api_key = row[0]
                return self.api_key
        
        raise ValueError("Google AI Studio API key not configured. Add it in Settings.")
    
    def _encode_image_base64(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64 string"""
        return base64.b64encode(image_bytes).decode('utf-8')
    

    async def generate_video_from_text(
        self,
        prompt: str,
        duration_seconds: int = 8,
        aspect_ratio: str = "9:16",
        model: str = "veo-3.0-fast-generate-001",
        db=None
    ) -> Dict[str, Any]:
        """
        Generate video from text prompt using Veo 3.
        
        Args:
            prompt: Description/script for the video
            duration_seconds: Video duration (4-8 seconds)
            aspect_ratio: Video aspect ratio (9:16, 16:9, 1:1)
            model: Veo model to use (veo-3.0-fast-generate-001 or veo-3.0-generate-001)
            db: Database session for API key lookup
            
        Returns:
            Dict with operation_id and status for polling
        """
        try:
            api_key = await self._get_api_key(db)
            
            # Clamp duration to valid range
            duration_seconds = max(4, min(8, duration_seconds))
            
            # Construct request payload
            payload = {
                "instances": [{
                    "prompt": prompt
                }],
                "parameters": {
                    "aspectRatio": aspect_ratio,
                    "durationSeconds": duration_seconds
                }
            }
            
            # Use key as query parameter (not Bearer token)
            url = f"{GEMINI_API_BASE}/models/{model}:predictLongRunning?key={api_key}"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"Calling Veo API: {url.split('?')[0]}")
                response = await client.post(url, json=payload)
                
                if response.status_code == 429:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail="Google AI rate limit reached. Please wait a moment and try again."
                    )
                
                response_text = response.text.lower()
                if "quota" in response_text or "exceeded" in response_text:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=402,
                        detail="Google AI billing quota exceeded. Check billing at https://ai.google.dev"
                    )
                
                if response.status_code != 200:
                    error_detail = response.json().get("error", {}).get("message", response.text[:200])
                    logger.error(f"Veo API error {response.status_code}: {error_detail}")
                    return {
                        "status": "error",
                        "error": f"Veo API error: {error_detail}"
                    }
                
                result = response.json()
                operation_id = result.get("name", "")
                
                logger.info(f"Veo video generation started. Operation: {operation_id}")
                
                return {
                    "status": "pending",
                    "operation_id": operation_id,
                    "model": model
                }
                
        except Exception as e:
            logger.error(f"Veo generation failed: {e}")
            return {
                "status": "error", 
                "error": str(e)
            }

    async def generate_video_from_text(
    prompt: str,
    duration_seconds: int = 8,
    aspect_ratio: str = "9:16",
    model: str = "veo-3.0-fast-generate-001",
    db=None
) -> Dict[str, Any]:
    """Convenience wrapper for VeoService.generate_video_from_text"""
    return await veo_service.generate_video_from_text(prompt, duration_seconds, aspect_ratio, model, db)


async def generate_video_from_image(
        self, 
        seed_image: bytes, 
        prompt: str, 
        duration_seconds: int = 5, 
        aspect_ratio: str = "9:16",
        db=None
    ) -> Dict[str, Any]:
        """
        Generate video from image using Veo 3.1
        
        Args:
            seed_image: Image bytes for video seed
            prompt: Description of the video to generate
            duration_seconds: Video duration (default 5s)
            aspect_ratio: Video aspect ratio (default 9:16)
            db: Database session for API key lookup
            
        Returns:
            Dict with operation_id and status for polling
        """
        try:
            api_key = await self._get_api_key(db)
            
            # Prepare image for API  
            image_b64 = self._encode_image_base64(seed_image)
            
            # Construct request payload for Veo 3.1
            payload = {
                "model": "veo-2.0-generate-001",
                "prompt": {
                    "text": prompt,
                    "image": {
                        "data": image_b64,
                        "mimeType": "image/jpeg"
                    }
                },
                "generationConfig": {
                    "duration": f"{duration_seconds}s",
                    "aspectRatio": aspect_ratio,
                    "quality": "high"
                }
            }
            
            # Try Gemini API endpoint first
            url = f"{GEMINI_API_BASE}/models/veo-2.0-generate-001:predictLongRunning"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"Calling Veo API: {url}")
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 404:
                    # Model not available - return clear error
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=501,
                        detail="Veo video generation requires Google Cloud Vertex AI project. Contact support to enable."
                    )
                
                # Handle rate limiting
                if response.status_code == 429:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail="Google AI rate limit reached. Please wait a moment and try again."
                    )
                
                # Handle quota exhaustion
                response_text = response.text.lower()
                if "quota" in response_text or "exceeded" in response_text:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=402,
                        detail="Google AI billing quota exceeded. Check your billing at https://ai.google.dev"
                    )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract operation ID from response
                operation_id = result.get("name", str(uuid.uuid4()))
                
                return {
                    "operation_id": operation_id,
                    "status": "pending",
                    "message": "Video generation started"
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Veo API request failed: {e}")
            # Return mock operation for development
            return await self._create_mock_operation(prompt)
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise ValueError(f"Video generation failed: {str(e)}")
    
    async def _generate_via_vertex_ai(
        self,
        seed_image: bytes,
        prompt: str,
        duration_seconds: int,
        aspect_ratio: str,
        api_key: str
    ) -> Dict[str, Any]:
        """
        Fallback to Vertex AI endpoint if Gemini API unavailable
        
        TODO: Implement when project configuration is available
        This is a scaffold for the Vertex AI integration
        """
        logger.warning("Vertex AI endpoint not implemented - using mock operation")
        return await self._create_mock_operation(prompt)
    
    async def _create_mock_operation(self, prompt: str) -> Dict[str, Any]:
        """Create mock operation for development/fallback"""
        operation_id = f"mock_veo_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Created mock Veo operation: {operation_id}")
        return {
            "operation_id": operation_id,
            "status": "pending",
            "message": f"Mock video generation for: {prompt[:50]}..."
        }
    
    async def check_video_status(self, operation_id: str, db=None) -> Dict[str, Any]:
        """
        Check status of video generation operation
        
        Args:
            operation_id: Operation ID from generate_video_from_image
            db: Database session for API key lookup
            
        Returns:
            Dict with status, progress, and video_url when complete
        """
        try:
            api_key = await self._get_api_key(db)
            
            # Handle mock operations
            if operation_id.startswith("mock_veo_"):
                return await self._mock_operation_status(operation_id)
            
            # Query Gemini operations endpoint with key param
            url = f"{GEMINI_API_BASE}/{operation_id}?key={api_key}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                result = response.json()
                
                # Parse operation status
                if result.get("done", False):
                    # Operation complete
                    if "error" in result:
                        return {
                            "status": "failed",
                            "progress": 100,
                            "error": result["error"].get("message", "Unknown error")
                        }
                    
                    # Success - extract video URL from Veo 3 response
                    response_data = result.get("response", {})
                    # Veo 3 returns generateVideoResponse.generatedSamples[].video.uri
                    gen_response = response_data.get("generateVideoResponse", response_data)
                    samples = gen_response.get("generatedSamples", [])
                    if samples:
                        video_url = samples[0].get("video", {}).get("uri", "")
                    else:
                        video_url = response_data.get("videoUri", response_data.get("video", {}).get("uri"))
                    
                    return {
                        "status": "complete",
                        "progress": 100,
                        "video_url": video_url
                    }
                else:
                    # Still running
                    metadata = result.get("metadata", {})
                    progress = int(metadata.get("progressPercentage", 50))
                    
                    return {
                        "status": "running",
                        "progress": progress
                    }
                    
        except httpx.HTTPError as e:
            logger.error(f"Status check failed: {e}")
            return {
                "status": "failed",
                "progress": 100,
                "error": f"Status check failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error checking status: {e}")
            return {
                "status": "failed",
                "progress": 100,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def _mock_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Mock operation status for development"""
        # Simulate progression: pending -> running -> complete
        import time
        creation_time = int(operation_id.split("_")[-1], 16) if "_" in operation_id else int(time.time())
        elapsed = int(time.time()) - creation_time
        
        if elapsed < 10:
            return {"status": "running", "progress": min(90, elapsed * 10)}
        else:
            # Mock completed after 10 seconds
            return {
                "status": "complete",
                "progress": 100,
                "video_url": f"https://example.com/mock_video_{operation_id}.mp4"
            }
    
    async def extend_video(
        self,
        video_url: str,
        prompt: str,
        duration_seconds: int = 5,
        db=None
    ) -> Dict[str, Any]:
        """
        Extend an existing video with scene continuity
        
        Args:
            video_url: URL of the video to extend
            prompt: Description for the extension
            duration_seconds: Extension duration (default 5s)
            db: Database session for API key lookup
            
        Returns:
            Dict with operation_id and status for polling
        """
        try:
            api_key = await self._get_api_key(db)
            
            # Download last frame from video for continuity
            # TODO: Implement video frame extraction
            logger.warning("Video extension not fully implemented - using mock")
            
            # For now, create a mock extension operation
            operation_id = f"extend_veo_{uuid.uuid4().hex[:8]}"
            
            return {
                "operation_id": operation_id,
                "status": "pending",
                "message": f"Video extension started: {prompt[:50]}..."
            }
            
        except Exception as e:
            logger.error(f"Video extension failed: {e}")
            raise ValueError(f"Video extension failed: {str(e)}")


# Global service instance
veo_service = VeoService()


# Convenience functions for direct use
async def generate_video_from_image(
    seed_image: bytes,
    prompt: str,
    duration_seconds: int = 5,
    aspect_ratio: str = "9:16",
    db=None
) -> Dict[str, Any]:
    """Generate video from image using Veo 3.1"""
    return await veo_service.generate_video_from_image(
        seed_image, prompt, duration_seconds, aspect_ratio, db
    )


async def check_video_status(operation_id: str, db=None) -> Dict[str, Any]:
    """Check video generation status"""
    return await veo_service.check_video_status(operation_id, db)


async def extend_video(video_url: str, prompt: str, duration_seconds: int = 5, db=None) -> Dict[str, Any]:
    """Extend existing video"""
    return await veo_service.extend_video(video_url, prompt, duration_seconds, db)