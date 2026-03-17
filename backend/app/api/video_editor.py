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
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import get_leadgen_db, leadgen_engine
from app.db.crm_db import get_tenant_db
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

TEMPLATES_DDL = """
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
)
"""

RENDER_JOBS_DDL = """
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
)
"""

VIDEO_PROJECTS_DDL = """
CREATE TABLE IF NOT EXISTS crm.video_projects (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    user_id INT NOT NULL,
    title TEXT NOT NULL,
    format_slug TEXT,
    status TEXT DEFAULT 'queued',
    scenes JSONB DEFAULT '[]',
    audio JSONB DEFAULT '{}',
    output_config JSONB DEFAULT '{}',
    output_url TEXT,
    total_duration_seconds FLOAT,
    estimated_cost JSONB DEFAULT '{}',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
)
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
    # Create public schema tables (templates, render jobs)
    async with leadgen_engine.begin() as conn:
        await conn.execute(text(TEMPLATES_DDL))
        await conn.execute(text(RENDER_JOBS_DDL))
    
    # Create CRM schema table (video projects)
    try:
        from app.db.crm_db import crm_engine
        async with crm_engine.begin() as conn:
            await conn.execute(text(VIDEO_PROJECTS_DDL))
        logger.info("Video editor tables initialized (public + crm schemas)")
    except Exception as e:
        logger.warning("Failed to create video_projects table in CRM schema: %s", e)


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
                            :duration_frames, :fps, :width, :height, CAST(:default_props AS jsonb))
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


# ── Video Compose Models ──────────────────────────────────────────────

class SceneInput(BaseModel):
    type: str  # "remotion" | "ai_generated" | "image" | "stock"
    template: Optional[str] = None  # remotion template name
    provider: Optional[str] = None  # "veo" | "nano_banana" | "seeddance"
    prompt: Optional[str] = None  # AI generation prompt
    url: Optional[str] = None  # image/stock URL
    duration_seconds: float = 3
    animation: Optional[str] = None
    props: Optional[Dict[str, Any]] = None

class AudioInput(BaseModel):
    voiceover_url: Optional[str] = None
    music_url: Optional[str] = None
    music_volume: float = 0.15

class OutputConfig(BaseModel):
    format: str = "mp4"
    resolution: str = "1080x1920"
    fps: int = 30

class ComposeRequest(BaseModel):
    project_title: str = "Untitled Video"
    format_slug: Optional[str] = None
    scenes: List[SceneInput]
    audio: Optional[AudioInput] = None
    output: Optional[OutputConfig] = None


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
        VALUES (:id, :org_id, :user_id, :template_id, :composition_id, CAST(:props AS jsonb), 'queued')
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


# ═══════════════════════════════════════════════════════════════════
# Video Copycat Endpoints (Stages 5-6)
# ═══════════════════════════════════════════════════════════════════

class LegacyComposeRequest(BaseModel):
    """Request to compose video from storyboard and assets (legacy)."""
    script: dict = Field(..., description="Script data with scenes and timing")
    assets: List[dict] = Field(..., description="List of generated assets")
    render_mode: str = Field(default="remotion", description="Render mode: 'remotion' or 'ffmpeg'")

class CaptionRequest(BaseModel):
    """Request to add captions to video."""
    video_path: str = Field(..., description="Path to input video")
    script: dict = Field(..., description="Script with text and timing")
    style: str = Field(default="hormozi", description="Caption style")


@router.post("/storyboards/{storyboard_id}/compose")
async def compose_video(
    storyboard_id: int,
    request_data: LegacyComposeRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """
    Build composition + render video from storyboard and assets (legacy).
    
    Creates a Remotion-compatible composition and renders the final video.
    """
    from app.services.video_composer import build_composition, generate_remotion_config, render_with_ffmpeg
    
    logger.info(f"Composing video for storyboard {storyboard_id}")
    org_id = get_org_id(request)
    
    try:
        # Get storyboard data (mock for now since storyboards table is being created)
        storyboard = {
            "id": storyboard_id,
            "scenes": [
                {"duration": 3.0, "show_product": True},
                {"duration": 4.0, "show_product": False},
                {"duration": 3.0, "show_product": True}
            ],
            "caption_style": "hormozi"
        }
        
        # Build composition from storyboard, script, and assets
        composition = build_composition(storyboard, request_data.script, request_data.assets)
        
        # Store composition in database
        composition_id = await _store_composition(db, storyboard_id, composition)
        
        # Generate output based on render mode
        if request_data.render_mode == "ffmpeg":
            # Render with ffmpeg fallback
            output_path = render_with_ffmpeg(composition)
            status = "completed"
            remotion_config = None
        else:
            # Generate Remotion config (actual render would be separate step)
            remotion_config = generate_remotion_config(composition)
            output_path = None
            status = "config_ready"
        
        # Update composition with results
        await _update_composition(db, composition_id, output_path, status, remotion_config)
        
        return {
            "success": True,
            "storyboard_id": storyboard_id,
            "composition_id": composition_id,
            "status": status,
            "output_path": output_path,
            "remotion_config": remotion_config,
            "layers_count": len(composition.layers),
            "duration": composition.duration
        }
        
    except Exception as e:
        logger.error(f"Video composition failed for storyboard {storyboard_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Video composition failed: {str(e)}")


@router.get("/storyboards/{storyboard_id}/composition")
async def get_composition(
    storyboard_id: int,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Get composition config for storyboard."""
    org_id = get_org_id(request)
    
    query = text("""
        SELECT 
            id, remotion_config, rendered_video_path, render_status,
            created_at, updated_at
        FROM public.video_compositions 
        WHERE storyboard_id = :storyboard_id
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    result = await db.execute(query, {"storyboard_id": storyboard_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Composition not found")
    
    return {
        "composition_id": row.id,
        "storyboard_id": storyboard_id,
        "remotion_config": row.remotion_config,
        "rendered_video_path": row.rendered_video_path,
        "render_status": row.render_status,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/storyboards/{storyboard_id}/add-captions")
async def add_captions_to_video(
    storyboard_id: int,
    caption_data: CaptionRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Add captions to rendered video."""
    from app.services.video_composer import add_captions
    
    logger.info(f"Adding captions to video for storyboard {storyboard_id}")
    org_id = get_org_id(request)
    
    try:
        # Add captions to video
        captioned_video_path = add_captions(
            caption_data.video_path,
            caption_data.script,
            caption_data.style
        )
        
        # Update composition with captioned video path
        update_query = text("""
            UPDATE public.video_compositions 
            SET rendered_video_path = :captioned_path,
                updated_at = NOW()
            WHERE storyboard_id = :storyboard_id
        """)
        
        await db.execute(update_query, {
            "captioned_path": captioned_video_path,
            "storyboard_id": storyboard_id
        })
        await db.commit()
        
        return {
            "success": True,
            "storyboard_id": storyboard_id,
            "original_path": caption_data.video_path,
            "captioned_path": captioned_video_path,
            "caption_style": caption_data.style
        }
        
    except Exception as e:
        logger.error(f"Caption addition failed for storyboard {storyboard_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Caption addition failed: {str(e)}")


async def _store_composition(db: AsyncSession, storyboard_id: int, composition) -> int:
    """Store composition in database."""
    query = text("""
        INSERT INTO public.video_compositions (
            storyboard_id, composition_name, remotion_config, render_status
        ) VALUES (
            :storyboard_id, :name, CAST(:config AS jsonb), 'pending'
        ) RETURNING id
    """)
    
    result = await db.execute(query, {
        "storyboard_id": storyboard_id,
        "name": f"composition_{storyboard_id}",
        "config": json.dumps(composition.to_dict())
    })
    
    composition_id = result.scalar()
    await db.commit()
    return composition_id


async def _update_composition(
    db: AsyncSession, 
    composition_id: int, 
    output_path: Optional[str], 
    status: str,
    remotion_config: Optional[dict] = None
) -> None:
    """Update composition with render results."""
    updates = ["render_status = :status", "updated_at = NOW()"]
    params = {"composition_id": composition_id, "status": status}
    
    if output_path:
        updates.append("rendered_video_path = :output_path")
        params["output_path"] = output_path
    
    if remotion_config:
        updates.append("remotion_config = CAST(:remotion_config AS jsonb)")
        params["remotion_config"] = json.dumps(remotion_config)
    
    query = text(f"""
        UPDATE public.video_compositions 
        SET {', '.join(updates)}
        WHERE id = :composition_id
    """)
    
    await db.execute(query, params)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  VIDEO COMPOSE FROM SCENES
# ═══════════════════════════════════════════════════════════════════════

@router.post("/compose-from-scenes")
async def compose_video_from_scenes(
    body: ComposeRequest,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Compose a video from mixed scene types (remotion, ai_generated, image, stock).
    
    Creates a video project and orchestrates the rendering pipeline by:
    1. Validating all scenes
    2. Calculating total duration and estimated cost
    3. Creating a video_projects record with status "queued"
    4. Returning project breakdown for tracking
    
    Phase 2b will handle actual rendering orchestration.
    """
    from app.services.tenant import get_org_id
    
    org_id = get_org_id(request)
    user_id = getattr(request.state, "user_id", user.id)
    
    # Validate scenes
    if not body.scenes or len(body.scenes) == 0:
        raise HTTPException(status_code=400, detail="At least one scene is required")
    
    # Calculate total duration
    total_duration = sum(scene.duration_seconds for scene in body.scenes)
    
    # Calculate scene breakdown
    scene_breakdown = {}
    for scene in body.scenes:
        scene_breakdown[scene.type] = scene_breakdown.get(scene.type, 0) + 1
    
    # Estimate costs
    ai_scene_count = scene_breakdown.get("ai_generated", 0)
    ai_cost = ai_scene_count * 0.05  # $0.05 per AI scene (placeholder)
    
    estimated_cost = {
        "ai_scenes": f"${ai_cost:.2f}" if ai_cost > 0 else None,
        "remotion_scenes": "free (local)" if scene_breakdown.get("remotion", 0) > 0 else None,
        "image_scenes": "free" if scene_breakdown.get("image", 0) > 0 else None,
        "stock_scenes": "free" if scene_breakdown.get("stock", 0) > 0 else None,
        "total": f"${ai_cost:.2f}"
    }
    
    # Filter out null values
    estimated_cost = {k: v for k, v in estimated_cost.items() if v is not None}
    
    # Prepare data for storage
    scenes_json = [scene.model_dump() for scene in body.scenes]
    audio_json = body.audio.model_dump() if body.audio else {}
    output_config_json = body.output.model_dump() if body.output else {}
    
    # Create video project
    insert_query = text("""
        INSERT INTO crm.video_projects 
        (org_id, user_id, title, format_slug, status, scenes, audio, output_config, 
         total_duration_seconds, estimated_cost)
        VALUES 
        (:org_id, :user_id, :title, :format_slug, 'queued', CAST(:scenes AS jsonb), 
         CAST(:audio AS jsonb), CAST(:output_config AS jsonb), :duration, CAST(:cost AS jsonb))
        RETURNING id
    """)
    
    result = await db.execute(insert_query, {
        "org_id": org_id,
        "user_id": user_id,
        "title": body.project_title,
        "format_slug": body.format_slug,
        "scenes": json.dumps(scenes_json),
        "audio": json.dumps(audio_json),
        "output_config": json.dumps(output_config_json),
        "duration": total_duration,
        "cost": json.dumps(estimated_cost)
    })
    
    project_id = result.scalar()
    await db.commit()
    
    # TODO: Phase 2b - Queue actual rendering jobs for each scene
    # For now, just create the project record and return the breakdown
    
    return {
        "project_id": project_id,
        "status": "queued",
        "total_scenes": len(body.scenes),
        "scene_breakdown": scene_breakdown,
        "estimated_duration_seconds": total_duration,
        "estimated_cost": estimated_cost
    }


@router.get("/projects/{project_id}")
async def get_video_project_status(
    project_id: int,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get the current status of a video project."""
    from app.services.tenant import get_org_id
    
    org_id = get_org_id(request)
    user_id = getattr(request.state, "user_id", user.id)
    
    query = text("""
        SELECT id, title, format_slug, status, scenes, audio, output_config,
               output_url, total_duration_seconds, estimated_cost, error,
               created_at, completed_at
        FROM crm.video_projects 
        WHERE id = :project_id AND org_id = :org_id AND user_id = :user_id
    """)
    
    result = await db.execute(query, {
        "project_id": project_id,
        "org_id": org_id,
        "user_id": user_id
    })
    
    project = result.mappings().first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")
    
    # Parse JSON fields
    project_dict = dict(project)
    if isinstance(project_dict.get("scenes"), str):
        project_dict["scenes"] = json.loads(project_dict["scenes"])
    if isinstance(project_dict.get("audio"), str):
        project_dict["audio"] = json.loads(project_dict["audio"])
    if isinstance(project_dict.get("output_config"), str):
        project_dict["output_config"] = json.loads(project_dict["output_config"])
    if isinstance(project_dict.get("estimated_cost"), str):
        project_dict["estimated_cost"] = json.loads(project_dict["estimated_cost"])
    
    # Convert timestamps to strings for JSON serialization
    project_dict["created_at"] = project_dict["created_at"].isoformat() if project_dict["created_at"] else None
    project_dict["completed_at"] = project_dict["completed_at"].isoformat() if project_dict["completed_at"] else None
    
    return project_dict
