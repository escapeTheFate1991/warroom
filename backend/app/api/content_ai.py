"""Content AI — OpenAI-powered content generation endpoints.

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


async def call_openai(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI chat completions API following the same pattern as chat.py."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,
            },
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        logger.error("OpenAI API error: %s %s", resp.status_code, resp.text[:200])
        raise HTTPException(
            status_code=502, detail=f"OpenAI error: {resp.status_code}"
        )


@router.post("/ai/ideas")
async def generate_ideas(req: IdeaRequest):
    """Generate viral content ideas for a niche and platform."""
    system = "You are a social media content strategist. Generate viral content ideas."
    user = (
        f"Generate {req.count} content ideas for a {req.niche} brand on {req.platform}. "
        f"For each idea, provide: 1) Title/hook, 2) Brief description, 3) Why it would perform well. "
        f"Format as JSON array with keys: title, description, reasoning."
    )
    result = await call_openai(system, user)
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
    result = await call_openai(system, user)
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
    result = await call_openai(system, user)
    return {"caption": result, "platform": req.platform}

