"""Video Editor API — Remotion-based programmatic video creation.

Extends the UGC Studio with template-driven video composition
using Remotion for in-browser preview and server-side rendering.
"""

import os
import uuid
import json
import logging
import asyncio
import subprocess
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import get_leadgen_db, leadgen_engine
from app.api.auth import get_current_user
from app.models.crm.user import User
from app.models.settings import Setting
from app.services.tenant import get_org_id
from sqlalchemy import select
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

VIDEOS_DIR = os.getenv("UGC_VIDEOS_DIR", "/data/ugc-videos")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# ── DDL ────────────────────────────────────────────────────────────────

TABLES_DDL = """
CREATE TABLE IF NOT EXISTS public.remotion_templates (
    id TEXT PRIMARY KEY,
    org_id INTEGER,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    composition_id TEXT NOT NULL,
    duration_frames INTEGER DEFAULT 450,
    fps INTEGER DEFAULT 30,
    width INTEGER DEFAULT 1920,
    height INTEGER DEFAULT 1080,
    default_props JSONB DEFAULT '{}'::jsonb,
    thumbnail_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.remotion_render_jobs (
    id TEXT PRIMARY KEY,
    org_id INTEGER,
    user_id INTEGER NOT NULL,
    template_id TEXT NOT NULL,
    composition_id TEXT NOT NULL,
    props JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'queued',
    progress FLOAT DEFAULT 0,
    output_url TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
"""

SEED_TEMPLATES = [
    {
        "id": "remotion-product-showcase",
        "name": "Product Showcase",
        "description": "Image slideshow with text overlays — perfect for product launches and features",
        "category": "product",
        "composition_id": "ProductShowcase",
        "duration_frames": 450,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "default_props": json.dumps({
            "images": [],
            "headline": "Introducing Our Product",
            "features": ["Feature One", "Feature Two", "Feature Three"],
            "ctaText": "Learn More",
            "brandColor": "#6366f1",
            "backgroundColor": "#0f172a",
        }),
    },
    {
        "id": "remotion-social-ad",
        "name": "Social Media Ad",
        "description": "Hook → Body → CTA format for social media ads (9:16 vertical)",
        "category": "social",
        "composition_id": "SocialMediaAd",
        "duration_frames": 360,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "default_props": json.dumps({
            "hookText": "Stop scrolling!",
            "bodyText": "This changes everything about how you work.",
            "ctaText": "Try it free →",
            "backgroundImage": "",
            "brandColor": "#6366f1",
            "backgroundColor": "#0f172a",
        }),
    },
    {
        "id": "remotion-testimonial",
        "name": "Testimonial",
        "description": "Quote + avatar + branding — great for social proof and customer stories",
        "category": "social",
        "composition_id": "Testimonial",
        "duration_frames": 600,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "default_props": json.dumps({
            "quote": "This product completely transformed our workflow. We saved 10 hours per week.",
            "authorName": "Jane Smith",
            "authorTitle": "CEO at TechCo",
            "avatarUrl": "",
            "brandLogo": "",
            "brandColor": "#6366f1",
            "backgroundColor": "#0f172a",
            "tagline": "Trusted by 1000+ teams",
        }),
    },
]


async def init_video_editor_tables():
    """Create video editor tables if they don't exist."""
    async with leadgen_engine.begin() as conn:
        await conn.execute(text(TABLES_DDL))
    logger.info("Video editor tables initialized")


async def seed_remotion_templates():
    """Insert default Remotion templates if none exist."""
    async with leadgen_engine.begin() as conn:
        row = await conn.execute(text("SELECT COUNT(*) FROM public.remotion_templates"))
        count = row.scalar()
        if count == 0:
            for t in SEED_TEMPLATES:
                await conn.execute(text("""
                    INSERT INTO public.remotion_templates
                    (id, name, description, category, composition_id,
                     duration_frames, fps, width, height, default_props)
                    VALUES (:id, :name, :description, :category, :composition_id,
                            :duration_frames, :fps, :width, :height, :default_props::jsonb)
                    ON CONFLICT (id) DO NOTHING
                """), t)
            logger.info("Seeded %d Remotion templates", len(SEED_TEMPLATES))


# ── Helper: get Gemini key ─────────────────────────────────────────────

async def _get_gemini_key(db: AsyncSession) -> str:
    result = await db.execute(select(Setting.value).where(Setting.key == "google_ai_studio_api_key"))
    row = result.scalar_one_or_none()
    key = row or os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Google AI Studio API key not configured")
    return key


# ═══════════════════════════════════════════════════════════════════════
#  TEMPLATES
# ═══════════════════════════════════════════════════════════════════════

@router.get("/templates")
async def list_remotion_templates(
    category: Optional[str] = None,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """List available Remotion video templates."""
    org_id = get_org_id(request)
    params = {}
    where_clauses = ["(org_id IS NULL OR org_id = :org_id)"]
    params["org_id"] = org_id

    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    where_sql = " AND ".join(where_clauses)
    rows = await db.execute(text(f"""
        SELECT id, name, description, category, composition_id,
               duration_frames, fps, width, height, default_props, thumbnail_url
        FROM public.remotion_templates
        WHERE {where_sql}
        ORDER BY name
    """), params)

    templates = []
    for r in rows.mappings():
        props = r["default_props"]
        if isinstance(props, str):
            props = json.loads(props)
        templates.append({
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "category": r["category"],
            "compositionId": r["composition_id"],
            "durationFrames": r["duration_frames"],
            "fps": r["fps"],
            "width": r["width"],
            "height": r["height"],
            "defaultProps": props,
            "thumbnailUrl": r["thumbnail_url"],
        })
    return {"templates": templates}


@router.get("/templates/{template_id}")
async def get_remotion_template(
    template_id: str,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Get a single Remotion template with its composition config."""
    org_id = get_org_id(request)
    row = await db.execute(text("""
        SELECT * FROM public.remotion_templates
        WHERE id = :id AND (org_id IS NULL OR org_id = :org_id)
    """), {"id": template_id, "org_id": org_id})
    r = row.mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="Template not found")
    result = dict(r)
    if isinstance(result.get("default_props"), str):
        result["default_props"] = json.loads(result["default_props"])
    return result


# ═══════════════════════════════════════════════════════════════════════
#  AI STORYBOARD GENERATION
# ═══════════════════════════════════════════════════════════════════════

class StoryboardRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000)
    template_id: Optional[str] = None
    duration_seconds: int = Field(default=15, ge=5, le=60)


STORYBOARD_SYSTEM_PROMPT = """You are a video storyboard generator for a Remotion-based video editor.
Given a user prompt, generate a JSON object describing a video composition.

Return ONLY valid JSON with this structure:
{
  "templateId": "remotion-product-showcase" | "remotion-social-ad" | "remotion-testimonial",
  "title": "Short title for the video",
  "props": {
    // Template-specific props based on the chosen template:
    // For ProductShowcase: images[], headline, features[], ctaText, brandColor, backgroundColor
    // For SocialMediaAd: hookText, bodyText, ctaText, backgroundImage, brandColor, backgroundColor
    // For Testimonial: quote, authorName, authorTitle, avatarUrl, brandLogo, brandColor, backgroundColor, tagline
  },
  "scenes": [
    {
      "scene": 1,
      "label": "Hook",
      "seconds": "0-3",
      "description": "What happens in this scene"
    }
  ]
}

Choose the most appropriate template based on the user's prompt.
Fill in compelling, specific copy — not generic placeholder text.
Return ONLY the JSON, no markdown fences or explanation."""


@router.post("/storyboard")
async def generate_storyboard(
    body: StoryboardRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """AI-generate a video storyboard from a text prompt using Gemini."""
    org_id = get_org_id(request)
    api_key = await _get_gemini_key(db)

    gen_url = f"{GEMINI_API_BASE}/models/gemini-2.5-flash:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": STORYBOARD_SYSTEM_PROMPT}]},
        "contents": [
            {
                "parts": [
                    {"text": f"Create a {body.duration_seconds}-second video storyboard for: {body.prompt}"}
                ]
            }
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(gen_url, params={"key": api_key}, json=payload)

        if resp.status_code != 200:
            logger.error("Gemini storyboard error: %s %s", resp.status_code, resp.text[:300])
            raise HTTPException(status_code=502, detail="AI storyboard generation failed")

        data = resp.json()
        raw_text = ""
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                raw_text += part.get("text", "")

        # Strip markdown fences
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            storyboard = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse storyboard JSON: %s", cleaned[:500])
            return {"storyboard": None, "raw": raw_text, "error": "Could not parse AI response"}

        return {"storyboard": storyboard, "prompt": body.prompt}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI storyboard generation timed out")


# ═══════════════════════════════════════════════════════════════════════
#  RENDER (Server-side Remotion rendering)
# ═══════════════════════════════════════════════════════════════════════

class RenderRequest(BaseModel):
    template_id: str
    props: dict = Field(default_factory=dict)
    title: str = "Untitled Video"
    output_format: str = "mp4"


@router.post("/render")
async def start_render(
    body: RenderRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Queue a server-side Remotion render job.
    
    Note: In MVP, this creates the job record and returns immediately.
    Actual Remotion CLI rendering requires the Remotion project to be
    set up on the server. For now, this is a placeholder that validates
    the request and stores the render intent.
    """
    org_id = get_org_id(request)

    # Validate template exists
    tpl_row = await db.execute(text("""
        SELECT id, composition_id, duration_frames, fps, width, height, default_props
        FROM public.remotion_templates
        WHERE id = :id AND (org_id IS NULL OR org_id = :org_id)
    """), {"id": body.template_id, "org_id": org_id})
    template = tpl_row.mappings().first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Merge default props with user props
    default_props = template["default_props"]
    if isinstance(default_props, str):
        default_props = json.loads(default_props)
    merged_props = {**default_props, **body.props}

    # Create render job
    job_id = f"rj-{uuid.uuid4().hex[:12]}"
    await db.execute(text("""
        INSERT INTO public.remotion_render_jobs
        (id, org_id, user_id, template_id, composition_id, props, status)
        VALUES (:id, :org_id, :user_id, :template_id, :composition_id, :props::jsonb, 'queued')
    """), {
        "id": job_id,
        "org_id": org_id,
        "user_id": user.id,
        "template_id": body.template_id,
        "composition_id": template["composition_id"],
        "props": json.dumps(merged_props),
    })
    await db.commit()

    # Also create a UGC project entry so it shows up in "My Projects"
    project_id = f"vp-{uuid.uuid4().hex[:12]}"
    await db.execute(text("""
        INSERT INTO public.ugc_video_projects
        (id, user_id, title, status, storyboard)
        VALUES (:id, :uid, :title, 'queued', '[]'::jsonb)
    """), {
        "id": project_id,
        "uid": user.id,
        "title": body.title,
    })
    await db.commit()

    # TODO: Phase 2 — actually invoke `npx remotion render` via subprocess
    # For now, mark as "queued" and let the user know server-side rendering
    # is pending infrastructure setup.

    return {
        "ok": True,
        "job_id": job_id,
        "project_id": project_id,
        "status": "queued",
        "composition_id": template["composition_id"],
        "props": merged_props,
        "message": "Render job queued. Server-side Remotion rendering will be available in Phase 2. Use the in-browser player for preview.",
    }


@router.get("/render/{job_id}/status")
async def get_render_status(
    job_id: str,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Check the status of a render job."""
    org_id = get_org_id(request)
    row = await db.execute(text("""
        SELECT id, status, progress, output_url, error_message, created_at, completed_at
        FROM public.remotion_render_jobs
        WHERE id = :id AND org_id = :org_id AND user_id = :uid
    """), {"id": job_id, "org_id": org_id, "uid": user.id})
    job = row.mappings().first()
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    return dict(job) | {
        "created_at": str(job["created_at"]),
        "completed_at": str(job["completed_at"]) if job["completed_at"] else None,
    }
