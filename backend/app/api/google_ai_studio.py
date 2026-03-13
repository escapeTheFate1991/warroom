"""Google AI Studio — Gemini-powered AI generation endpoints.

Provides chat, content generation, and prompt experimentation
via Google's Gemini API (generativelanguage.googleapis.com).
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import httpx
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.leadgen_db import get_leadgen_db
from app.models.settings import Setting
from app.api.auth import get_current_user
from app.models.crm.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiMessage(BaseModel):
    role: str = "user"  # "user" or "model"
    text: str


class GeminiChatRequest(BaseModel):
    messages: List[GeminiMessage]
    model: str = "gemini-2.0-flash"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    system_instruction: Optional[str] = None


class GeminiGenerateRequest(BaseModel):
    prompt: str
    model: str = "gemini-2.0-flash"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    system_instruction: Optional[str] = None


class GeminiModelInfo(BaseModel):
    id: str
    name: str
    description: str


AVAILABLE_MODELS = [
    GeminiModelInfo(id="gemini-2.0-flash", name="Gemini 2.0 Flash", description="Fast, versatile model for most tasks"),
    GeminiModelInfo(id="gemini-2.5-pro-preview-05-06", name="Gemini 2.5 Pro", description="Most capable model for complex reasoning"),
    GeminiModelInfo(id="gemini-2.5-flash-preview-05-20", name="Gemini 2.5 Flash", description="Best balance of speed and intelligence"),
]


async def _get_gemini_key(db: AsyncSession) -> str:
    """Retrieve the Google AI Studio API key from settings or env."""
    result = await db.execute(
        select(Setting.value).where(Setting.key == "google_ai_studio_api_key")
    )
    row = result.scalar_one_or_none()
    key = row or os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Google AI Studio API key not configured. Add it in Settings → API Keys.")
    return key


async def _call_gemini(api_key: str, model: str, contents: list, system_instruction: Optional[str], temperature: float, max_tokens: int) -> str:
    """Call the Gemini generateContent API."""
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    body: dict = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, params={"key": api_key}, json=body)
        if resp.status_code != 200:
            detail = resp.text[:300]
            logger.error("Gemini API error %s: %s", resp.status_code, detail)
            raise HTTPException(status_code=502, detail=f"Gemini API error: {detail}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts)

        raise HTTPException(status_code=502, detail="Gemini returned no candidates")


@router.get("/models")
async def list_models():
    """Return available Gemini models."""
    return {"models": [m.model_dump() for m in AVAILABLE_MODELS]}


@router.post("/chat")
async def gemini_chat(req: GeminiChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_leadgen_db)):
    """Multi-turn chat with Gemini."""
    api_key = await _get_gemini_key(db)
    contents = [{"role": m.role, "parts": [{"text": m.text}]} for m in req.messages]
    result = await _call_gemini(api_key, req.model, contents, req.system_instruction, req.temperature, req.max_tokens)
    return {"response": result, "model": req.model}


@router.post("/generate")
async def gemini_generate(req: GeminiGenerateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_leadgen_db)):
    """Single-prompt generation with Gemini."""
    api_key = await _get_gemini_key(db)
    contents = [{"role": "user", "parts": [{"text": req.prompt}]}]
    result = await _call_gemini(api_key, req.model, contents, req.system_instruction, req.temperature, req.max_tokens)
    return {"response": result, "model": req.model}


@router.get("/status")
async def gemini_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_leadgen_db)):
    """Check if Google AI Studio API key is configured."""
    try:
        await _get_gemini_key(db)
        return {"configured": True}
    except HTTPException:
        return {"configured": False}

