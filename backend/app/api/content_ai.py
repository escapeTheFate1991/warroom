"""Content AI — OpenClaw-powered content generation endpoints.

Provides idea generation, script writing, and caption creation
for social media content pipelines.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
OPENCLAW_API = os.getenv("OPENCLAW_API_URL", "http://10.0.0.1:18789")


class IdeaRequest(BaseModel):
    niche: str  # e.g., "digital marketing agency"
    platform: str  # e.g., "instagram", "youtube"
    count: int = 5


class ScriptRequest(BaseModel):
    topic: str
    platform: str
    style: Optional[str] = "educational"  # educational, entertaining, storytelling
    duration: Optional[str] = "60s"  # 15s, 30s, 60s, 3min


class CaptionRequest(BaseModel):
    topic: str
    platform: str
    tone: Optional[str] = "professional"  # professional, casual, humorous
    include_hashtags: bool = True
    include_cta: bool = True


async def call_openclaw(system_prompt: str, user_prompt: str) -> str:
    """Call the OpenClaw chat completions API."""
    auth_token = os.getenv("OPENCLAW_AUTH_TOKEN", "")
    if not auth_token:
        raise HTTPException(status_code=503, detail="OpenClaw auth token not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{os.getenv('OPENCLAW_API_URL', OPENCLAW_API)}/v1/chat/completions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "temperature": 0.8,
            },
        )
        if resp.status_code != 200:
            logger.error("OpenClaw API error %s: %s", resp.status_code, resp.text[:200])
            raise HTTPException(status_code=502, detail="AI service unavailable")

        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

        logger.error("OpenClaw response missing choices payload")
        raise HTTPException(status_code=502, detail="AI service unavailable")


@router.post("/ai/ideas")
async def generate_ideas(req: IdeaRequest):
    """Generate viral content ideas for a niche and platform."""
    system = "You are a social media content strategist. Generate viral content ideas."
    user = (
        f"Generate {req.count} content ideas for a {req.niche} brand on {req.platform}. "
        f"For each idea, provide: 1) Title/hook, 2) Brief description, 3) Why it would perform well. "
        f"Format as JSON array with keys: title, description, reasoning."
    )
    result = await call_openclaw(system, user)
    return {"ideas": result, "platform": req.platform}


@router.post("/ai/script")
async def generate_script(req: ScriptRequest):
    """Generate a platform-optimized content script."""
    system = (
        f"You are a {req.platform} content scriptwriter. "
        f"Write engaging scripts optimized for {req.platform}."
    )
    user = (
        f"Write a {req.duration} {req.style} script about: {req.topic}\n\n"
        f"Include: Hook (first 3 seconds), body, call-to-action. "
        f"Format with clear sections."
    )
    result = await call_openclaw(system, user)
    return {"script": result, "platform": req.platform, "topic": req.topic}


@router.post("/ai/captions")
async def generate_captions(req: CaptionRequest):
    """Generate a social media caption with optional hashtags and CTA."""
    extras = []
    if req.include_hashtags:
        extras.append("Include 10-15 relevant hashtags")
    if req.include_cta:
        extras.append("Include a call-to-action")
    system = (
        f"You are a {req.platform} copywriter. "
        f"Write engaging captions in a {req.tone} tone."
    )
    user = (
        f"Write a caption for {req.platform} about: {req.topic}\n\n"
        f"{'. '.join(extras)}."
    )
    result = await call_openclaw(system, user)
    return {"caption": result, "platform": req.platform}

