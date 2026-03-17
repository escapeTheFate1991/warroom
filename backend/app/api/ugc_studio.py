"""UGC Video Studio — Digital Copy management & Video Generation via Veo 3.

Tables live in the public schema (same pattern as ai_planning, cold_email).
"""

import os
import uuid
import json
import logging
import base64
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id
from app.db.leadgen_db import leadgen_engine
from app.api.auth import get_current_user
from app.models.crm.user import User
from app.models.settings import Setting
from app.api.content_intel import load_cached_posts, _sorted_posts_for_analysis, extract_hook_from_text
from sqlalchemy import select
import httpx
from app.services.competitor_script_engine import get_top_scripts, generate_script_from_reference, extract_hook_body_cta
from app.services.editing_dna import extract_visual_layout, synthesize_editing_dna, process_competitor_for_dna, map_dna_to_remotion_config, seed_default_dna_templates

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Storage ────────────────────────────────────────────────────────────
ASSETS_DIR = os.getenv("UGC_ASSETS_DIR", "/data/ugc-assets")
VIDEOS_DIR = os.getenv("UGC_VIDEOS_DIR", "/data/ugc-videos")
MAX_ASSET_SIZE = 50 * 1024 * 1024  # 50 MB per file

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# ── DDL ────────────────────────────────────────────────────────────────

DIGITAL_COPIES_DDL = """
CREATE TABLE IF NOT EXISTS public.ugc_digital_copies (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    assets JSONB DEFAULT '[]'::jsonb,
    voice_samples JSONB DEFAULT '[]'::jsonb,
    preview_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
"""

VIDEO_TEMPLATES_DDL = """
CREATE TABLE IF NOT EXISTS public.ugc_video_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'ugc',
    duration_seconds INTEGER DEFAULT 15,
    scene_count INTEGER DEFAULT 3,
    storyboard JSONB DEFAULT '[]'::jsonb,
    prompt_template TEXT DEFAULT '',
    thumbnail_url TEXT,
    source_url TEXT,
    source_analysis JSONB DEFAULT '{}'::jsonb,
    user_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
"""

VIDEO_PROJECTS_DDL = """
CREATE TABLE IF NOT EXISTS public.ugc_video_projects (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    template_id TEXT,
    digital_copy_id TEXT,
    title TEXT NOT NULL DEFAULT 'Untitled Video',
    script TEXT DEFAULT '',
    content_mode TEXT DEFAULT 'product',
    product_images JSONB DEFAULT '[]'::jsonb,
    storyboard JSONB DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'draft',
    video_url TEXT,
    generation_id TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
"""

VOICE_SAMPLES_DIR = os.getenv("UGC_VOICE_DIR", "/data/ugc-voices")
TEMPLATIZER_TEMP = os.getenv("UGC_TEMP_DIR", "/tmp/ugc-templatizer")


ALTER_DDL = [
    "ALTER TABLE public.ugc_digital_copies ADD COLUMN IF NOT EXISTS voice_samples JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE public.ugc_video_templates ADD COLUMN IF NOT EXISTS source_url TEXT",
    "ALTER TABLE public.ugc_video_templates ADD COLUMN IF NOT EXISTS source_analysis JSONB DEFAULT '{}'::jsonb",
    "ALTER TABLE public.ugc_video_templates ADD COLUMN IF NOT EXISTS user_id INTEGER",
    "ALTER TABLE public.ugc_video_projects ADD COLUMN IF NOT EXISTS format_slug TEXT",
]


async def init_ugc_tables():
    """Create UGC tables if they don't exist."""
    async with leadgen_engine.begin() as conn:
        await conn.execute(text(DIGITAL_COPIES_DDL))
        await conn.execute(text(VIDEO_TEMPLATES_DDL))
        await conn.execute(text(VIDEO_PROJECTS_DDL))
        # Initialize Editing DNA table
        from app.services.editing_dna import EDITING_DNA_DDL
        await conn.execute(text(EDITING_DNA_DDL))
        for stmt in ALTER_DDL:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass
    logger.info("UGC Studio tables initialized")


# ── Seed templates ─────────────────────────────────────────────────────

SEED_TEMPLATES = [
    {
        "id": "tpl-product-demo",
        "name": "Product Demo (15s)",
        "description": "Quick product unboxing / demo — hook, show, CTA",
        "category": "product",
        "duration_seconds": 15,
        "scene_count": 3,
        "storyboard": json.dumps([
            {"scene": 1, "label": "Hook", "seconds": "0-3", "direction": "Close-up of product reveal. Shaky handheld, mid-sentence start. Excited energy.", "camera": "close-up", "mood": "excited discovery"},
            {"scene": 2, "label": "Demo", "seconds": "3-11", "direction": "Show the product in use. Natural speech, slight focus shifts, real lighting. Demonstrate the key benefit.", "camera": "medium", "mood": "genuine enthusiasm"},
            {"scene": 3, "label": "CTA", "seconds": "11-15", "direction": "Casual wrap-up with product visible. Direct call to action. No text overlays.", "camera": "medium-close", "mood": "confident recommendation"},
        ]),
        "prompt_template": "Create a {duration}-second raw iPhone-style UGC video:\n- 0–3s: {scene_1}\n- 3–11s: {scene_2}\n- 11–{duration}s: {scene_3}\nTone: {tone}\nEnergy: {energy}",
    },
    {
        "id": "tpl-talking-head",
        "name": "Talking Head (30s)",
        "description": "Creator speaks to camera — opinion, tip, or story",
        "category": "social",
        "duration_seconds": 30,
        "scene_count": 4,
        "storyboard": json.dumps([
            {"scene": 1, "label": "Hook", "seconds": "0-3", "direction": "Direct eye contact, bold statement or question. Raw selfie angle.", "camera": "selfie", "mood": "attention-grabbing"},
            {"scene": 2, "label": "Context", "seconds": "3-12", "direction": "Explain the situation or problem. Conversational tone, natural pauses.", "camera": "selfie", "mood": "relatable"},
            {"scene": 3, "label": "Value", "seconds": "12-24", "direction": "Deliver the tip, insight, or story payoff. Slight lean-in for emphasis.", "camera": "selfie", "mood": "knowledgeable"},
            {"scene": 4, "label": "CTA", "seconds": "24-30", "direction": "Ask for engagement — follow, comment, or save. Friendly sign-off.", "camera": "selfie", "mood": "warm"},
        ]),
        "prompt_template": "Create a {duration}-second talking head UGC video:\n{scenes}\nTone: {tone}\nEnergy: {energy}",
    },
    {
        "id": "tpl-before-after",
        "name": "Before / After (12s)",
        "description": "Transformation reveal — great for services & results",
        "category": "service",
        "duration_seconds": 12,
        "scene_count": 3,
        "storyboard": json.dumps([
            {"scene": 1, "label": "Before", "seconds": "0-4", "direction": "Show the problem state. Messy, dull, or broken. Real lighting, no filters.", "camera": "wide-to-close", "mood": "frustrated"},
            {"scene": 2, "label": "Transition", "seconds": "4-6", "direction": "Quick cut or wipe. Hands working, product being applied, or time skip.", "camera": "close-up", "mood": "anticipation"},
            {"scene": 3, "label": "After", "seconds": "6-12", "direction": "Reveal the transformation. Slow pan, satisfied reaction. Let it breathe.", "camera": "wide-to-close", "mood": "satisfaction"},
        ]),
        "prompt_template": "Create a {duration}-second before/after transformation UGC video:\n{scenes}\nTone: {tone}",
    },
    {
        "id": "tpl-testimonial",
        "name": "Testimonial (20s)",
        "description": "Customer review style — authentic social proof",
        "category": "product",
        "duration_seconds": 20,
        "scene_count": 3,
        "storyboard": json.dumps([
            {"scene": 1, "label": "Problem", "seconds": "0-5", "direction": "Creator describes the problem they had. Raw, relatable, slightly frustrated tone.", "camera": "selfie", "mood": "relatable frustration"},
            {"scene": 2, "label": "Discovery", "seconds": "5-14", "direction": "Show finding/using the product. B-roll of product with voiceover or on-camera narration.", "camera": "mixed", "mood": "pleasant surprise"},
            {"scene": 3, "label": "Result", "seconds": "14-20", "direction": "Show the outcome. Genuine smile, recommend to viewer. Product visible.", "camera": "selfie", "mood": "genuine satisfaction"},
        ]),
        "prompt_template": "Create a {duration}-second testimonial-style UGC video:\n{scenes}\nTone: {tone}\nEnergy: {energy}",
    },
]


async def seed_templates():
    """Insert default templates if none exist."""
    async with leadgen_engine.begin() as conn:
        row = await conn.execute(text("SELECT COUNT(*) FROM public.ugc_video_templates"))
        count = row.scalar()
        if count == 0:
            for t in SEED_TEMPLATES:
                await conn.execute(text("""
                    INSERT INTO public.ugc_video_templates (id, name, description, category, duration_seconds, scene_count, storyboard, prompt_template)
                    VALUES (:id, :name, :description, :category, :duration_seconds, :scene_count, CAST(:storyboard AS jsonb), :prompt_template)
                    ON CONFLICT (id) DO NOTHING
                """), t)
            logger.info("Seeded %d UGC video templates", len(SEED_TEMPLATES))


# ── Helper: get Gemini key ─────────────────────────────────────────────

async def _get_gemini_key(db: AsyncSession) -> str:
    result = await db.execute(select(Setting.value).where(Setting.key == "google_ai_studio_api_key"))
    row = result.scalar_one_or_none()
    key = row or os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Google AI Studio API key not configured")
    return key


# ═══════════════════════════════════════════════════════════════════════
#  DIGITAL COPIES
# ═══════════════════════════════════════════════════════════════════════

class DigitalCopyCreate(BaseModel):
    name: str
    description: str = ""


class DigitalCopyResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    assets: list
    preview_url: Optional[str]
    created_at: str


@router.post("/digital-copies")
async def create_digital_copy(
    request: Request,
    body: DigitalCopyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new digital copy entry (assets uploaded separately)."""
    org_id = get_org_id(request)
    copy_id = f"dc-{uuid.uuid4().hex[:12]}"
    await db.execute(text("""
        INSERT INTO public.ugc_digital_copies (id, user_id, name, description)
        VALUES (:id, :user_id, :name, :description)
    """), {"id": copy_id, "user_id": user.id, "name": body.name, "description": body.description})
    await db.commit()
    return {"id": copy_id, "name": body.name, "status": "draft"}


@router.get("/digital-copies")
async def list_digital_copies(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all digital copies for the current user."""
    org_id = get_org_id(request)
    rows = await db.execute(text("""
        SELECT id, name, description, status, assets, preview_url, created_at
        FROM public.ugc_digital_copies
        WHERE user_id = :uid
        ORDER BY created_at DESC
    """), {"uid": user.id})
    copies = []
    for r in rows.mappings():
        copies.append({
            "id": r["id"], "name": r["name"], "description": r["description"],
            "status": r["status"], "assets": r["assets"] or [],
            "preview_url": r["preview_url"],
            "created_at": str(r["created_at"]),
        })
    return {"copies": copies}


@router.get("/digital-copies/{copy_id}")
async def get_digital_copy(
    copy_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    row = await db.execute(text("""
        SELECT id, name, description, status, assets, preview_url, created_at
        FROM public.ugc_digital_copies WHERE id = :id AND user_id = :uid
    """), {"id": copy_id, "uid": user.id})
    r = row.mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    return dict(r)


@router.delete("/digital-copies/{copy_id}")
async def delete_digital_copy(
    copy_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    await db.execute(text(
        "DELETE FROM public.ugc_digital_copies WHERE id = :id AND user_id = :uid"
    ), {"id": copy_id, "uid": user.id})
    await db.commit()
    return {"ok": True}


@router.post("/digital-copies/{copy_id}/assets")
async def upload_asset(
    request: Request,
    copy_id: str,
    file: UploadFile = File(...),
    label: str = Form("angle"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Upload an image/video asset for a digital copy."""
    # Verify ownership
    row = await db.execute(text(
        "SELECT id, assets FROM public.ugc_digital_copies WHERE id = :id AND user_id = :uid"
    ), {"id": copy_id, "uid": user.id})
    dc = row.mappings().first()
    if not dc:
        raise HTTPException(status_code=404, detail="Digital copy not found")

    content = await file.read()
    if len(content) > MAX_ASSET_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    # Save file
    copy_dir = os.path.join(ASSETS_DIR, copy_id)
    os.makedirs(copy_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "file.jpg")[1].lower()
    safe_name = f"{label}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(copy_dir, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    # Update assets array
    existing = dc["assets"] or []
    asset_entry = {
        "filename": safe_name,
        "label": label,
        "path": filepath,
        "size_kb": len(content) // 1024,
        "content_type": file.content_type or "image/jpeg",
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    existing.append(asset_entry)
    await db.execute(text("""
        UPDATE public.ugc_digital_copies SET assets = :assets::jsonb, updated_at = NOW()
        WHERE id = :id
    """), {"id": copy_id, "assets": json.dumps(existing)})
    await db.commit()

    return {"ok": True, "asset": asset_entry, "total_assets": len(existing)}


# ═══════════════════════════════════════════════════════════════════════
#  VIDEO TEMPLATES
# ═══════════════════════════════════════════════════════════════════════

@router.get("/templates")
async def list_templates(
    request: Request,
    category: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List available video templates, optionally filtered by category."""
    org_id = get_org_id(request)
    if category:
        rows = await db.execute(text("""
            SELECT id, name, description, category, duration_seconds, scene_count, storyboard, prompt_template, thumbnail_url
            FROM public.ugc_video_templates WHERE category = :cat ORDER BY name
        """), {"cat": category})
    else:
        rows = await db.execute(text("""
            SELECT id, name, description, category, duration_seconds, scene_count, storyboard, prompt_template, thumbnail_url
            FROM public.ugc_video_templates ORDER BY name
        """))
    templates = []
    for r in rows.mappings():
        templates.append({
            "id": r["id"], "name": r["name"], "description": r["description"],
            "category": r["category"], "duration_seconds": r["duration_seconds"],
            "scene_count": r["scene_count"],
            "storyboard": r["storyboard"] if isinstance(r["storyboard"], list) else json.loads(r["storyboard"] or "[]"),
            "prompt_template": r["prompt_template"],
            "thumbnail_url": r["thumbnail_url"],
        })
    return {"templates": templates}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    row = await db.execute(text(
        "SELECT * FROM public.ugc_video_templates WHERE id = :id"
    ), {"id": template_id})
    r = row.mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="Template not found")
    result = dict(r)
    if isinstance(result.get("storyboard"), str):
        result["storyboard"] = json.loads(result["storyboard"])
    return result


# ═══════════════════════════════════════════════════════════════════════
#  VIDEO PROJECTS
# ═══════════════════════════════════════════════════════════════════════

class VideoProjectCreate(BaseModel):
    template_id: Optional[str] = None
    digital_copy_id: Optional[str] = None
    title: str = "Untitled Video"
    script: str = ""
    content_mode: str = "product"  # product | service
    format_slug: Optional[str] = None


@router.post("/projects")
async def create_project(
    body: VideoProjectCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new video project. Copies storyboard from template if provided."""
    org_id = get_org_id(request)
    project_id = f"vp-{uuid.uuid4().hex[:12]}"
    storyboard = []

    # Copy storyboard from template
    if body.template_id:
        tpl = await db.execute(text(
            "SELECT storyboard FROM public.ugc_video_templates WHERE id = :id"
        ), {"id": body.template_id})
        tpl_row = tpl.mappings().first()
        if tpl_row:
            sb = tpl_row["storyboard"]
            storyboard = sb if isinstance(sb, list) else json.loads(sb or "[]")

    await db.execute(text("""
        INSERT INTO public.ugc_video_projects
            (id, user_id, template_id, digital_copy_id, title, script, content_mode, storyboard, format_slug)
        VALUES (:id, :uid, :tpl, :dc, :title, :script, :mode, :sb::jsonb, :format)
    """), {
        "id": project_id, "uid": user.id, "tpl": body.template_id,
        "dc": body.digital_copy_id, "title": body.title,
        "script": body.script, "mode": body.content_mode,
        "sb": json.dumps(storyboard), "format": body.format_slug,
    })
    await db.commit()
    return {"id": project_id, "title": body.title, "storyboard": storyboard}


@router.get("/projects")
async def list_projects(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    rows = await db.execute(text("""
        SELECT id, title, template_id, digital_copy_id, content_mode, status, video_url, created_at, format_slug
        FROM public.ugc_video_projects WHERE user_id = :uid ORDER BY created_at DESC
    """), {"uid": user.id})
    projects = []
    for r in rows.mappings():
        projects.append(dict(r) | {"created_at": str(r["created_at"])})
    return {"projects": projects}


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    row = await db.execute(text("""
        SELECT * FROM public.ugc_video_projects WHERE id = :id AND user_id = :uid
    """), {"id": project_id, "uid": user.id})
    r = row.mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="Project not found")
    result = dict(r)
    for field in ("storyboard", "product_images"):
        if isinstance(result.get(field), str):
            result[field] = json.loads(result[field])
    result["created_at"] = str(result["created_at"])
    result["updated_at"] = str(result["updated_at"])
    return result


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    body: dict,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update project fields (title, script, storyboard, content_mode, digital_copy_id)."""
    org_id = get_org_id(request)
    allowed = {"title", "script", "storyboard", "content_mode", "digital_copy_id"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    set_clauses = []
    params = {"id": project_id, "uid": user.id}
    for k, v in updates.items():
        if k == "storyboard":
            set_clauses.append(f"{k} = :{k}::jsonb")
            params[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        else:
            set_clauses.append(f"{k} = :{k}")
            params[k] = v
    set_clauses.append("updated_at = NOW()")

    await db.execute(text(f"""
        UPDATE public.ugc_video_projects SET {', '.join(set_clauses)}
        WHERE id = :id AND user_id = :uid
    """), params)
    await db.commit()
    return {"ok": True}


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    await db.execute(text(
        "DELETE FROM public.ugc_video_projects WHERE id = :id AND user_id = :uid"
    ), {"id": project_id, "uid": user.id})
    await db.commit()
    return {"ok": True}



# ═══════════════════════════════════════════════════════════════════════
#  VIDEO GENERATION (Veo 3.1 via Gemini API)
# ═══════════════════════════════════════════════════════════════════════

def _build_scene_prompt(storyboard: list, script: str, content_mode: str) -> str:
    """Assemble a detailed Veo-ready prompt from storyboard scenes + script."""
    lines = []
    lines.append(f"Create a raw, authentic iPhone-style UGC video ad.")
    if content_mode == "service":
        lines.append("This is a service-based ad — no physical product. The creator talks directly to camera.")
    else:
        lines.append("This is a product ad — the product should be visible and demonstrated.")

    lines.append("")
    for scene in storyboard:
        label = scene.get("label", f"Scene {scene.get('scene', '?')}")
        seconds = scene.get("seconds", "")
        direction = scene.get("direction", "")
        camera = scene.get("camera", "")
        mood = scene.get("mood", "")
        lines.append(f"[{seconds}] {label}:")
        lines.append(f"  Direction: {direction}")
        if camera:
            lines.append(f"  Camera: {camera}")
        if mood:
            lines.append(f"  Mood/Energy: {mood}")
        lines.append("")

    if script:
        lines.append("Script / Voiceover:")
        lines.append(script)
        lines.append("")

    lines.append("Style: Handheld, natural lighting, no text overlays, no filters.")
    lines.append("Aspect ratio: 9:16 (vertical / portrait for social media).")
    return "\n".join(lines)


class GenerateVideoRequest(BaseModel):
    project_id: str
    tone: str = "excited discovery"
    energy: str = "caffeinated but genuine"


@router.post("/generate")
async def generate_video(
    body: GenerateVideoRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Kick off video generation via Google Veo 3.1 for a project."""
    org_id = get_org_id(request)
    api_key = await _get_gemini_key(db)

    # Load project
    row = await db.execute(text("""
        SELECT * FROM public.ugc_video_projects WHERE id = :id AND user_id = :uid
    """), {"id": body.project_id, "uid": user.id})
    project = row.mappings().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    storyboard = project["storyboard"]
    if isinstance(storyboard, str):
        storyboard = json.loads(storyboard or "[]")

    # Build the prompt
    prompt = _build_scene_prompt(storyboard, project["script"] or "", project["content_mode"] or "product")

    # If there's a digital copy, load its reference images for the prompt context
    reference_images = []
    if project["digital_copy_id"]:
        dc_row = await db.execute(text(
            "SELECT assets FROM public.ugc_digital_copies WHERE id = :id"
        ), {"id": project["digital_copy_id"]})
        dc = dc_row.mappings().first()
        if dc and dc["assets"]:
            assets = dc["assets"] if isinstance(dc["assets"], list) else json.loads(dc["assets"])
            for asset in assets[:5]:  # max 5 reference images
                fpath = asset.get("path", "")
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    mime = asset.get("content_type", "image/jpeg")
                    reference_images.append({"inline_data": {"mime_type": mime, "data": b64}})

    # Update status
    await db.execute(text("""
        UPDATE public.ugc_video_projects SET status = 'generating', updated_at = NOW()
        WHERE id = :id
    """), {"id": body.project_id})
    await db.commit()

    # Call Veo 3.1 via Gemini API
    veo_model = "veo-3.1-generate-preview"
    url = f"{GEMINI_API_BASE}/models/{veo_model}:predictLongRunning"

    # Build request parts
    parts = []
    for img in reference_images:
        parts.append(img)
    parts.append({"text": prompt})

    request_body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "aspectRatio": "9:16",
            "personGeneration": "allow_all",
            "numberOfVideos": 1,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, params={"key": api_key}, json=request_body)

            if resp.status_code == 200:
                data = resp.json()
                generation_id = data.get("name", "")
                await db.execute(text("""
                    UPDATE public.ugc_video_projects
                    SET generation_id = :gen_id, status = 'processing', updated_at = NOW()
                    WHERE id = :id
                """), {"gen_id": generation_id, "id": body.project_id})
                await db.commit()
                return {"ok": True, "generation_id": generation_id, "status": "processing", "prompt_used": prompt}
            else:
                error = resp.text[:500]
                logger.error("Veo API error %s: %s", resp.status_code, error)
                await db.execute(text("""
                    UPDATE public.ugc_video_projects
                    SET status = 'failed', error_message = :err, updated_at = NOW()
                    WHERE id = :id
                """), {"err": error, "id": body.project_id})
                await db.commit()
                raise HTTPException(status_code=502, detail=f"Veo API error: {error}")

    except httpx.TimeoutException:
        await db.execute(text("""
            UPDATE public.ugc_video_projects SET status = 'failed', error_message = 'Timeout', updated_at = NOW()
            WHERE id = :id
        """), {"id": body.project_id})
        await db.commit()
        raise HTTPException(status_code=504, detail="Veo API request timed out")


@router.get("/generate/{project_id}/status")
async def check_generation_status(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Poll generation status for a video project."""
    org_id = get_org_id(request)
    row = await db.execute(text("""
        SELECT id, status, generation_id, video_url, error_message
        FROM public.ugc_video_projects WHERE id = :id AND user_id = :uid
    """), {"id": project_id, "uid": user.id})
    project = row.mappings().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # If still processing and we have a generation_id, poll the API
    if project["status"] == "processing" and project["generation_id"]:
        api_key = await _get_gemini_key(db)
        poll_url = f"{GEMINI_API_BASE}/{project['generation_id']}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(poll_url, params={"key": api_key})
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("done"):
                        # Extract video URL from response
                        video_data = data.get("response", {})
                        videos = video_data.get("generatedSamples", [])
                        if videos:
                            video_b64 = videos[0].get("video", {}).get("bytesBase64Encoded", "")
                            if video_b64:
                                # Save video to disk
                                os.makedirs(VIDEOS_DIR, exist_ok=True)
                                video_path = os.path.join(VIDEOS_DIR, f"{project_id}.mp4")
                                with open(video_path, "wb") as f:
                                    f.write(base64.b64decode(video_b64))
                                video_url = f"/api/ai-studio/ugc/videos/{project_id}.mp4"
                                await db.execute(text("""
                                    UPDATE public.ugc_video_projects
                                    SET status = 'completed', video_url = :url, updated_at = NOW()
                                    WHERE id = :id
                                """), {"url": video_url, "id": project_id})
                                await db.commit()
                                return {"status": "completed", "video_url": video_url}
                        # Done but no video
                        await db.execute(text("""
                            UPDATE public.ugc_video_projects
                            SET status = 'failed', error_message = 'No video in response', updated_at = NOW()
                            WHERE id = :id
                        """), {"id": project_id})
                        await db.commit()
                        return {"status": "failed", "error": "No video generated"}
                    else:
                        return {"status": "processing", "generation_id": project["generation_id"]}
        except Exception as e:
            logger.warning("Poll error for %s: %s", project_id, e)
            return {"status": "processing", "generation_id": project["generation_id"]}

    return {
        "status": project["status"],
        "video_url": project["video_url"],
        "error": project["error_message"],
    }


@router.post("/generate/preview-prompt")
async def preview_prompt(
    body: dict,
    user: User = Depends(get_current_user),
):
    """Preview the assembled Veo prompt without generating. For debugging/review."""
    org_id = get_org_id(request)
    storyboard = body.get("storyboard", [])
    script = body.get("script", "")
    content_mode = body.get("content_mode", "product")
    prompt = _build_scene_prompt(storyboard, script, content_mode)
    return {"prompt": prompt}


# ═══════════════════════════════════════════════════════════════════════
#  TEMPLATIZER — Analyze any video URL and extract a reusable template
# ═══════════════════════════════════════════════════════════════════════

TEMPLATIZER_SYSTEM_PROMPT = """You are a UGC video ad analyst. You will receive a video file.
Analyze it in extreme detail and return a JSON object with this exact structure:

{
  "title": "Short descriptive template name (e.g. 'Skincare Testimonial 30s')",
  "description": "One-line summary of the video style and purpose",
  "category": "product | service | social | lifestyle",
  "duration_seconds": <estimated total duration in seconds>,
  "character_type": "on-camera | faceless | hands-only | voiceover-only",
  "character_description": "Describe the person: gender, approximate age, appearance, clothing style, energy",
  "product_visible": true | false,
  "product_description": "What product is shown, if any. Brand, type, how it appears.",
  "background_description": "Setting/location: indoor/outdoor, lighting, aesthetic",
  "script": "The exact spoken words / voiceover transcript, broken by scene markers like [HOOK] [DEMO] [CTA]",
  "scenes": [
    {
      "scene": 1,
      "label": "Hook",
      "seconds": "0-3",
      "direction": "Detailed direction: what happens visually, camera angle, movement, subject action",
      "camera": "selfie | close-up | medium | wide | b-roll | overhead | pov",
      "mood": "Emotional tone / energy level (e.g. 'excited discovery', 'calm authority')",
      "has_person": true,
      "has_product": false,
      "transition": "cut | fade | swipe | none"
    }
  ],
  "hooks_used": ["List the opening hook lines/techniques used"],
  "cta_type": "link-in-bio | shop-now | follow | comment | none",
  "music_style": "trending audio | background lo-fi | no music | voiceover only",
  "text_overlays": true | false,
  "editing_style": "raw iPhone | slightly polished | professional | jump-cuts",
  "posting_platform": "tiktok | instagram-reels | youtube-shorts | unknown"
}

Be extremely detailed in the scene directions — these will be used to recreate similar videos with different faces and products. Include every camera movement, angle change, and visual transition.
Return ONLY the JSON object, no markdown formatting."""


async def _download_video_for_templatizer(url: str) -> Optional[str]:
    """Download a video from any URL (Instagram, TikTok, YouTube, etc.) using yt-dlp."""
    import subprocess
    import asyncio

    os.makedirs(TEMPLATIZER_TEMP, exist_ok=True)
    output_id = uuid.uuid4().hex[:12]
    output_path = os.path.join(TEMPLATIZER_TEMP, f"tmpl_{output_id}.mp4")

    try:
        cmd = [
            "yt-dlp",
            "--no-warnings", "--quiet",
            "-o", output_path,
            "--max-filesize", "100M",
            "--format", "mp4/best[ext=mp4]/best",
            url,
        ]
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, timeout=90,
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            logger.info("Templatizer downloaded video (%d KB)", os.path.getsize(output_path) // 1024)
            return output_path
        logger.warning("yt-dlp failed: %s", result.stderr[:300] if result.stderr else "no output")
    except FileNotFoundError:
        logger.error("yt-dlp not installed")
    except Exception as e:
        logger.error("Download error: %s", e)

    return None


async def _upload_to_gemini_file_api(api_key: str, filepath: str, mime_type: str = "video/mp4") -> Optional[str]:
    """Upload a file to Gemini File API and return the file URI."""
    upload_url = f"{GEMINI_API_BASE}/upload/v1beta/files"

    file_size = os.path.getsize(filepath)
    display_name = os.path.basename(filepath)

    # Start resumable upload
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Initiate upload
        resp = await client.post(
            upload_url,
            params={"key": api_key},
            headers={
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(file_size),
                "X-Goog-Upload-Header-Content-Type": mime_type,
                "Content-Type": "application/json",
            },
            json={"file": {"display_name": display_name}},
        )
        if resp.status_code != 200:
            logger.error("File API init failed: %s %s", resp.status_code, resp.text[:300])
            return None

        upload_uri = resp.headers.get("X-Goog-Upload-URL") or resp.headers.get("x-goog-upload-url")
        if not upload_uri:
            logger.error("No upload URI in response headers")
            return None

        # Upload file bytes
        with open(filepath, "rb") as f:
            data = f.read()

        resp2 = await client.put(
            upload_uri,
            headers={
                "X-Goog-Upload-Command": "upload, finalize",
                "X-Goog-Upload-Offset": "0",
                "Content-Length": str(file_size),
            },
            content=data,
        )
        if resp2.status_code != 200:
            logger.error("File upload failed: %s %s", resp2.status_code, resp2.text[:300])
            return None

        file_info = resp2.json().get("file", {})
        file_uri = file_info.get("uri", "")
        file_name = file_info.get("name", "")
        state = file_info.get("state", "")
        logger.info("Uploaded to Gemini: %s (state=%s)", file_name, state)

        # Wait for file to be ACTIVE (processing can take a moment)
        if state != "ACTIVE":
            import asyncio as aio
            for _ in range(30):
                await aio.sleep(2)
                check = await client.get(
                    f"{GEMINI_API_BASE}/{file_name}",
                    params={"key": api_key},
                )
                if check.status_code == 200:
                    info = check.json()
                    if info.get("state") == "ACTIVE":
                        file_uri = info.get("uri", file_uri)
                        break
            else:
                logger.warning("File never became ACTIVE, proceeding anyway")

        return file_uri


class TemplatizeRequest(BaseModel):
    url: str
    save_as_template: bool = False


@router.post("/templatize")
async def templatize_video(
    body: TemplatizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Download a video from URL, send to Gemini 2.5 Pro, extract a reusable template."""
    org_id = get_org_id(request)
    api_key = await _get_gemini_key(db)

    # 1. Download the video
    filepath = await _download_video_for_templatizer(body.url)
    if not filepath:
        raise HTTPException(status_code=422, detail="Could not download video. Check the URL and try again.")

    try:
        # 2. Upload to Gemini File API
        file_uri = await _upload_to_gemini_file_api(api_key, filepath)
        if not file_uri:
            raise HTTPException(status_code=502, detail="Failed to upload video to Gemini for analysis.")

        # 3. Send to Gemini 2.5 Pro for analysis
        gen_url = f"{GEMINI_API_BASE}/models/gemini-2.5-pro:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": TEMPLATIZER_SYSTEM_PROMPT}]},
            "contents": [
                {
                    "parts": [
                        {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}},
                        {"text": "Analyze this video in full detail. Return the JSON template object."},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(gen_url, params={"key": api_key}, json=payload)

        if resp.status_code != 200:
            logger.error("Gemini analysis failed: %s %s", resp.status_code, resp.text[:500])
            raise HTTPException(status_code=502, detail="Gemini analysis failed")

        # Parse response
        data = resp.json()
        raw_text = ""
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                raw_text += part.get("text", "")

        # Strip markdown fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            analysis = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse Gemini response as JSON: %s", cleaned[:500])
            return {"analysis": None, "raw_response": raw_text, "error": "Could not parse structured response"}

        # 4. Optionally save as a new template
        template_id = None
        if body.save_as_template:
            template_id = f"tmpl-{uuid.uuid4().hex[:12]}"
            scenes = analysis.get("scenes", [])
            storyboard = []
            for s in scenes:
                storyboard.append({
                    "scene": s.get("scene", 1),
                    "label": s.get("label", ""),
                    "seconds": s.get("seconds", "0-5"),
                    "direction": s.get("direction", ""),
                    "camera": s.get("camera", "medium"),
                    "mood": s.get("mood", ""),
                    "has_person": s.get("has_person", True),
                    "has_product": s.get("has_product", False),
                    "transition": s.get("transition", "cut"),
                })
            await db.execute(text("""
                INSERT INTO public.ugc_video_templates
                (id, name, description, category, duration_seconds, scene_count, storyboard,
                 prompt_template, source_url, source_analysis, user_id)
                VALUES (:id, :name, :desc, :cat, :dur, :sc, :sb::jsonb,
                        :pt, :src, :sa::jsonb, :uid)
            """), {
                "id": template_id,
                "name": analysis.get("title", "Templatized Video"),
                "desc": analysis.get("description", ""),
                "cat": analysis.get("category", "ugc"),
                "dur": analysis.get("duration_seconds", 15),
                "sc": len(scenes),
                "sb": json.dumps(storyboard),
                "pt": analysis.get("script", ""),
                "src": body.url,
                "sa": json.dumps(analysis),
                "uid": user.id,
            })
            await db.commit()

        return {
            "analysis": analysis,
            "template_id": template_id,
            "source_url": body.url,
        }

    finally:
        # Cleanup temp file
        if os.path.exists(filepath):
            os.unlink(filepath)


# ═══════════════════════════════════════════════════════════════════════
#  TEMPLATIZE FROM COMPETITOR POSTS
# ═══════════════════════════════════════════════════════════════════════

class TemplatizeCompetitorRequest(BaseModel):
    competitor_post_id: int
    save_as_template: bool = True


@router.post("/templatize-competitor")
async def templatize_competitor_post(
    body: TemplatizeCompetitorRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Pull a top competitor video from CRM and templatize it."""
    org_id = get_org_id(request)
    # Look up the competitor post
    row = await db.execute(text("""
        SELECT cp.id, cp.post_url, cp.media_url, cp.media_type, cp.shortcode,
               cp.post_text, cp.engagement_score, c.handle, c.platform
        FROM crm.competitor_posts cp
        JOIN crm.competitors c ON c.id = cp.competitor_id
        WHERE cp.id = :pid
    """), {"pid": body.competitor_post_id})
    post = row.mappings().first()
    if not post:
        raise HTTPException(status_code=404, detail="Competitor post not found")

    if post["media_type"] not in ("video", "reel", "clip"):
        raise HTTPException(status_code=400, detail="Post is not a video/reel")

    # Build the best URL to download
    video_url = post["post_url"] or ""
    if post["shortcode"] and post["platform"] == "instagram":
        video_url = f"https://www.instagram.com/reel/{post['shortcode']}/"
    elif not video_url and post["media_url"]:
        video_url = post["media_url"]

    if not video_url:
        raise HTTPException(status_code=400, detail="No downloadable URL for this post")

    # Delegate to the main templatize logic
    result = await templatize_video(
        TemplatizeRequest(url=video_url, save_as_template=body.save_as_template),
        user=user,
        db=db,
    )
    # Attach competitor context
    result["competitor"] = {
        "handle": post["handle"],
        "platform": post["platform"],
        "engagement_score": float(post["engagement_score"] or 0),
        "original_caption": (post["post_text"] or "")[:500],
    }
    return result


@router.get("/competitor-videos")
async def list_competitor_videos(
    request: Request,
    limit: int = 20,
    min_engagement: float = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List top competitor video posts available for templatizing."""
    org_id = get_org_id(request)
    rows = await db.execute(text("""
        SELECT cp.id, cp.post_url, cp.media_url, cp.media_type, cp.shortcode,
               cp.post_text, cp.engagement_score, cp.likes, cp.comments,
               cp.thumbnail_url, cp.posted_at,
               c.handle, c.platform, c.profile_image_url
        FROM crm.competitor_posts cp
        JOIN crm.competitors c ON c.id = cp.competitor_id
        WHERE cp.media_type IN ('video', 'reel', 'clip')
          AND cp.engagement_score >= :min_eng
        ORDER BY cp.engagement_score DESC
        LIMIT :lim
    """), {"min_eng": min_engagement, "lim": limit})
    videos = []
    for r in rows.mappings():
        videos.append({
            "post_id": r["id"],
            "handle": r["handle"],
            "platform": r["platform"],
            "profile_image": r["profile_image_url"],
            "post_url": r["post_url"],
            "thumbnail_url": r["thumbnail_url"],
            "caption": (r["post_text"] or "")[:200],
            "likes": r["likes"],
            "comments": r["comments"],
            "engagement_score": float(r["engagement_score"] or 0),
            "posted_at": str(r["posted_at"]) if r["posted_at"] else None,
            "media_type": r["media_type"],
        })
    return {"videos": videos}


# ═══════════════════════════════════════════════════════════════════════
#  VOICE SAMPLES — Upload voice recordings for cloning
# ═══════════════════════════════════════════════════════════════════════

@router.post("/digital-copies/{copy_id}/voice-samples")
async def upload_voice_sample(
    request: Request,
    copy_id: str,
    file: UploadFile = File(...),
    label: str = Form("default"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Upload an audio sample for voice cloning to a digital copy."""
    # Verify ownership
    row = await db.execute(text(
        "SELECT id, voice_samples FROM public.ugc_digital_copies WHERE id = :id AND user_id = :uid"
    ), {"id": copy_id, "uid": user.id})
    dc = row.mappings().first()
    if not dc:
        raise HTTPException(status_code=404, detail="Digital copy not found")

    content = await file.read()
    if len(content) > MAX_ASSET_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    # Validate audio file type
    allowed = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".aac")
    ext = os.path.splitext(file.filename or "voice.mp3")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format. Allowed: {', '.join(allowed)}")

    # Save file
    voice_dir = os.path.join(VOICE_SAMPLES_DIR, copy_id)
    os.makedirs(voice_dir, exist_ok=True)
    safe_name = f"voice_{label}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(voice_dir, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    # Update voice_samples array
    existing = dc["voice_samples"] or []
    sample_entry = {
        "filename": safe_name,
        "label": label,
        "path": filepath,
        "size_kb": len(content) // 1024,
        "content_type": file.content_type or "audio/mpeg",
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    existing.append(sample_entry)
    await db.execute(text("""
        UPDATE public.ugc_digital_copies SET voice_samples = :vs::jsonb, updated_at = NOW()
        WHERE id = :id
    """), {"id": copy_id, "vs": json.dumps(existing)})
    await db.commit()

    return {"ok": True, "voice_sample": sample_entry, "total_samples": len(existing)}


@router.get("/digital-copies/{copy_id}/voice-samples")
async def list_voice_samples(
    copy_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List voice samples for a digital copy."""
    org_id = get_org_id(request)
    row = await db.execute(text(
        "SELECT voice_samples FROM public.ugc_digital_copies WHERE id = :id AND user_id = :uid"
    ), {"id": copy_id, "uid": user.id})
    dc = row.mappings().first()
    if not dc:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    return {"samples": dc["voice_samples"] or []}


@router.delete("/digital-copies/{copy_id}/voice-samples/{filename}")
async def delete_voice_sample(
    copy_id: str,
    filename: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Delete a voice sample from a digital copy."""
    org_id = get_org_id(request)
    row = await db.execute(text(
        "SELECT id, voice_samples FROM public.ugc_digital_copies WHERE id = :id AND user_id = :uid"
    ), {"id": copy_id, "uid": user.id})
    dc = row.mappings().first()
    if not dc:
        raise HTTPException(status_code=404, detail="Digital copy not found")

    samples = dc["voice_samples"] or []
    updated = [s for s in samples if s.get("filename") != filename]

    # Delete file from disk
    filepath = os.path.join(VOICE_SAMPLES_DIR, copy_id, filename)
    if os.path.exists(filepath):
        os.unlink(filepath)

    await db.execute(text("""
        UPDATE public.ugc_digital_copies SET voice_samples = :vs::jsonb, updated_at = NOW()
        WHERE id = :id
    """), {"id": copy_id, "vs": json.dumps(updated)})
    await db.commit()

    return {"ok": True, "remaining": len(updated)}


# ═══════════════════════════════════════════════════════════════════════
#  AI SCRIPT GENERATION (Viral Content Engine)
# ═══════════════════════════════════════════════════════════════════════

VIDEO_FORMATS = {
    "transformation": "Transformation (Before/After) — showing dramatic change over time. People buy outcomes, not products.",
    "myth_buster": "Myth Buster — take something everyone believes and flip it on its head. Creates instant engagement.",
    "pov": "POV — point of view format. Relatable scenarios that pull the viewer in.",
    "expose": "The Exposé — reveal industry secrets insiders don't want shared. Creates us-vs-them dynamic.",
    "speed_run": "Speed Run — condense a long process into a rapid-fire video.",
    "challenge": "Challenge Format — get people to try something for a specific timeframe. Creates community participation.",
    "show_dont_tell": "Show Don't Tell — demonstrate products/outcomes visually instead of explaining.",
    "direct_to_camera": "Direct-to-Camera (Gary Vee style) — raw, unfiltered takes straight to camera.",
    "listicle": "Listicle — '5 things you need to know' format. Easy to consume, high saves.",
    "day_in_the_life": "Day in the Life — authentic behind-the-scenes content.",
    "tutorial": "Tutorial — step-by-step how-to content that provides immediate value.",
    "reaction": "Reaction — respond to trending content or industry news.",
}


class GenerateScriptRequest(BaseModel):
    format: str
    hook: str
    topic: str
    target_audience: str = ""
    tone: str = "energetic and authentic"
    duration_seconds: int = 30
    use_competitor_intel: bool = False


async def extract_competitor_context(posts: List[Dict[str, Any]], format_slug: str = None) -> Dict[str, Any]:
    """Extract competitor intelligence context from posts."""
    # Filter by format if specified
    if format_slug:
        filtered_posts = [p for p in posts if p.get('detected_format') == format_slug]
        if filtered_posts:
            posts = filtered_posts
    
    # Extract top hooks
    hooks_with_engagement = []
    for post in posts[:30]:
        hook = post.get('hook') or extract_hook_from_text(post.get('post_text', ''))
        if hook and len(hook) >= 10:
            engagement = post.get('engagement_score', 0) or (
                (post.get('likes', 0) or 0) + 
                (post.get('comments', 0) or 0) + 
                (post.get('shares', 0) or 0)
            )
            hooks_with_engagement.append((hook, engagement, post.get('handle', '')))
    
    # Sort by engagement and take top 10
    top_hooks = sorted(hooks_with_engagement, key=lambda x: x[1], reverse=True)[:10]
    
    # Extract audience demand signals from comments
    audience_themes = []
    comment_texts = []
    
    for post in posts[:15]:  # Check comments from top 15 posts
        comments_data = post.get('comments_data')
        if comments_data:
            try:
                if isinstance(comments_data, str):
                    comments_json = json.loads(comments_data)
                else:
                    comments_json = comments_data
                
                if isinstance(comments_json, list):
                    for comment in comments_json:
                        if isinstance(comment, dict) and comment.get('text'):
                            comment_texts.append(comment['text'])
                elif isinstance(comments_json, dict):
                    if 'comments' in comments_json:
                        for comment in comments_json['comments']:
                            if isinstance(comment, dict) and comment.get('text'):
                                comment_texts.append(comment['text'])
            except (json.JSONDecodeError, TypeError):
                continue
    
    # Extract themes from comment texts
    question_patterns = []
    for text in comment_texts[:100]:  # Limit to avoid processing too many
        text_clean = text.lower().strip()
        if ('?' in text_clean or 
            text_clean.startswith(('how', 'what', 'why', 'where', 'when', 'does', 'can', 'will', 'is'))):
            # Clean and extract key question
            clean_question = re.sub(r'[^a-zA-Z0-9\s\?]', '', text_clean)
            if len(clean_question) > 10 and len(clean_question) < 100:
                question_patterns.append(clean_question)
    
    # Count recurring themes
    theme_counter = Counter()
    for question in question_patterns:
        # Extract key phrases (simple approach)
        words = question.split()
        if len(words) >= 3:
            for i in range(len(words) - 2):
                phrase = ' '.join(words[i:i+3])
                theme_counter[phrase] += 1
    
    audience_themes = [theme for theme, count in theme_counter.most_common(5) if count >= 2]
    
    # Extract format patterns (simplified)
    format_patterns = []
    if format_slug:
        format_patterns = [
            f"Strong visual hook in first 2 seconds",
            f"Direct address to camera",
            f"Clear value proposition early",
            f"Quick pace with short sentences",
            f"Strong call-to-action at end"
        ]
    
    # Get source handles
    source_handles = list(set(post.get('handle', '') for post in posts[:10] if post.get('handle')))
    
    return {
        'top_hooks': top_hooks,
        'audience_themes': audience_themes,
        'format_patterns': format_patterns,
        'source_handles': source_handles,
        'total_posts': len(posts)
    }


def parse_script_response(response_text: str) -> Dict[str, str]:
    """Parse AI response to extract script and 'why this works' section."""
    # Look for 'WHY THIS WORKS' section
    why_match = re.search(r'(?:WHY THIS WORKS|WHY IT WORKS)[:\n](.*?)(?:\n\n|\n(?=AUDIENCE DEMAND)|$)', 
                         response_text, re.DOTALL | re.IGNORECASE)
    why_section = why_match.group(1).strip() if why_match else ""
    
    # Extract main script (everything before WHY THIS WORKS)
    script_text = response_text
    if why_match:
        script_text = response_text[:why_match.start()].strip()
    
    return {
        'script': script_text,
        'why_this_works': why_section
    }


@router.post("/generate-script")
async def generate_script(
    body: GenerateScriptRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Generate a short-form video script using AI based on format + hook + topic."""
    org_id = get_org_id(request)
    api_key = await _get_gemini_key(db)

    format_desc = VIDEO_FORMATS.get(body.format, body.format)
    audience_line = f"\nTarget audience: {body.target_audience}" if body.target_audience else ""
    
    # Initialize competitor intelligence variables
    competitor_context = ""
    competitor_powered = False
    why_this_works = ""
    audience_demand_signals = []
    source_competitors = []
    
    # If competitor intel is requested, gather data
    if body.use_competitor_intel:
        try:
            # Load cached posts from last 45 days
            posts = await load_cached_posts(db, org_id, days=45)
            
            if posts:
                # Sort by engagement and take top 30
                ranked_posts = _sorted_posts_for_analysis(posts)[:30]
                
                # Extract competitor context
                context_data = await extract_competitor_context(ranked_posts, body.format)
                
                top_hooks = context_data['top_hooks']
                audience_themes = context_data['audience_themes']
                format_patterns = context_data['format_patterns']
                source_competitors = context_data['source_handles']
                audience_demand_signals = audience_themes
                
                # Build competitor context for prompt
                competitor_context = f"""
COMPETITOR INTELLIGENCE (from {context_data['total_posts']} top-performing posts):

TOP HOOKS THAT WENT VIRAL:
{chr(10).join(f'- "{h}" ({int(eng)} engagement)' for h, eng, handle in top_hooks[:8])}

AUDIENCE DEMAND SIGNALS (from comments analysis):
{chr(10).join(f'- {theme}' for theme in audience_themes[:5])}

PROVEN PATTERNS FOR {body.format.upper()} FORMAT:
{chr(10).join(f'- {pattern}' for pattern in format_patterns[:5])}
"""
                competitor_powered = True
                
        except Exception as e:
            logger.warning(f"Failed to load competitor intel: {e}")
            # Continue without competitor intel

    # Build the prompt
    if competitor_powered:
        prompt = f"""You are an expert short-form video scriptwriter using proven viral strategies.

{competitor_context}

Generate a {body.duration_seconds}-second video script.
FORMAT: {format_desc}
HOOK: "{body.hook}" (enhance this using the viral hook patterns above)
TOPIC: {body.topic}{audience_line}
TONE: {body.tone}

Write the script with clear sections:
[HOOK] — The first 2-3 seconds. Use the provided hook or improve it. This is the most important part.
[BODY] — The main content. Keep it punchy, one idea per sentence.
[CTA] — Call to action. 2-3 seconds max.

Rules:
- Write for speaking out loud, not reading
- Use short sentences (5-10 words each)
- Include [PAUSE] marks where dramatic pauses help
- Include (camera direction) notes in parentheses
- The hook MUST stop the scroll in the first 2 seconds
- Total script should be speakable in ~{body.duration_seconds} seconds
- No emojis in the script itself

IMPORTANT:
- Your hook MUST incorporate patterns from the top-performing hooks above
- Address at least one audience demand signal in the body
- After the script, include a "WHY THIS WORKS" section explaining which competitor patterns you used
- Include "AUDIENCE DEMAND" noting which comment themes you addressed

Return the script followed by analysis sections."""
    else:
        # Original prompt for backwards compatibility
        prompt = f"""You are an expert short-form video scriptwriter. Generate a {body.duration_seconds}-second video script.

FORMAT: {format_desc}
HOOK: "{body.hook}"
TOPIC: {body.topic}{audience_line}
TONE: {body.tone}

Write the script with clear sections:
[HOOK] — The first 2-3 seconds. Use the provided hook or improve it. This is the most important part.
[BODY] — The main content. Keep it punchy, one idea per sentence.
[CTA] — Call to action. 2-3 seconds max.

Rules:
- Write for speaking out loud, not reading
- Use short sentences (5-10 words each)
- Include [PAUSE] marks where dramatic pauses help
- Include (camera direction) notes in parentheses
- The hook MUST stop the scroll in the first 2 seconds
- Total script should be speakable in ~{body.duration_seconds} seconds
- No emojis in the script itself

Return ONLY the script text, no explanations or metadata."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024},
                },
            )
            if resp.status_code != 200:
                logger.error("Script generation failed: %s", resp.text[:500])
                raise HTTPException(500, "Script generation failed")

            data = resp.json()
            response_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

            if not response_text:
                raise HTTPException(500, "Empty script generated")

            # Parse the response
            if competitor_powered:
                parsed = parse_script_response(response_text)
                script_text = parsed['script']
                why_this_works = parsed['why_this_works']
            else:
                script_text = response_text.strip()

            # Build response
            response = {
                "script": script_text.strip(),
                "format": body.format,
                "format_description": format_desc,
                "hook_used": body.hook,
                "topic": body.topic,
            }
            
            # Add competitor intel fields if used
            if competitor_powered:
                response.update({
                    "competitor_powered": True,
                    "why_this_works": why_this_works,
                    "audience_demand_signals": audience_demand_signals,
                    "source_competitors": source_competitors,
                })

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Script generation error: %s", e)
        raise HTTPException(500, f"Script generation failed: {str(e)[:200]}")


@router.get("/competitor-hooks")
async def get_competitor_hooks(
    request: Request,
    format_slug: str = None,
    limit: int = 8,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get top-performing hooks from competitor data for the Hook Lab sidebar."""
    org_id = get_org_id(request)
    
    try:
        # Load cached posts from last 45 days
        posts = await load_cached_posts(db, org_id, days=45)
        
        if not posts:
            return {"hooks": [], "audience_demands": []}
        
        # Sort by engagement and take top 30
        ranked_posts = _sorted_posts_for_analysis(posts)[:30]
        
        # Filter by format if specified
        if format_slug:
            filtered_posts = [p for p in ranked_posts if p.get('detected_format') == format_slug]
            if filtered_posts:
                ranked_posts = filtered_posts
        
        # Extract hooks with metadata
        hooks_data = []
        for post in ranked_posts[:limit]:
            hook = post.get('hook') or extract_hook_from_text(post.get('post_text', ''))
            if hook and len(hook) >= 10:
                engagement_score = post.get('engagement_score', 0) or (
                    (post.get('likes', 0) or 0) + 
                    (post.get('comments', 0) or 0) + 
                    (post.get('shares', 0) or 0)
                )
                
                hooks_data.append({
                    "hook_text": hook,
                    "handle": post.get('handle', ''),
                    "likes": post.get('likes', 0) or 0,
                    "engagement_score": int(engagement_score),
                    "format": post.get('detected_format', ''),
                    "post_url": post.get('post_url', '')
                })
        
        # Sort by engagement and take the requested limit
        hooks_data.sort(key=lambda x: x['engagement_score'], reverse=True)
        top_hooks = hooks_data[:limit]
        
        # Extract audience demand signals from comments
        audience_demands = []
        comment_texts = []
        competitor_themes = defaultdict(list)
        
        for post in ranked_posts[:15]:  # Check comments from top 15 posts
            comments_data = post.get('comments_data')
            handle = post.get('handle', '')
            
            if comments_data:
                try:
                    if isinstance(comments_data, str):
                        comments_json = json.loads(comments_data)
                    else:
                        comments_json = comments_data
                    
                    post_questions = []
                    
                    if isinstance(comments_json, list):
                        for comment in comments_json:
                            if isinstance(comment, dict) and comment.get('text'):
                                text = comment['text'].lower().strip()
                                if ('?' in text or 
                                    text.startswith(('how', 'what', 'why', 'where', 'when', 'does', 'can', 'will', 'is'))):
                                    clean_question = re.sub(r'[^a-zA-Z0-9\s\?]', '', text)
                                    if 10 <= len(clean_question) <= 100:
                                        post_questions.append(clean_question)
                    elif isinstance(comments_json, dict):
                        if 'comments' in comments_json:
                            for comment in comments_json['comments']:
                                if isinstance(comment, dict) and comment.get('text'):
                                    text = comment['text'].lower().strip()
                                    if ('?' in text or 
                                        text.startswith(('how', 'what', 'why', 'where', 'when', 'does', 'can', 'will', 'is'))):
                                        clean_question = re.sub(r'[^a-zA-Z0-9\s\?]', '', text)
                                        if 10 <= len(clean_question) <= 100:
                                            post_questions.append(clean_question)
                    
                    # Group questions by competitor
                    for question in post_questions:
                        competitor_themes[handle].append(question)
                        
                except (json.JSONDecodeError, TypeError):
                    continue
        
        # Count recurring themes across all competitors
        theme_counter = Counter()
        theme_sources = defaultdict(set)
        
        for handle, questions in competitor_themes.items():
            for question in questions:
                # Extract key phrases (simple approach)
                words = question.split()
                if len(words) >= 3:
                    for i in range(len(words) - 2):
                        phrase = ' '.join(words[i:i+3])
                        theme_counter[phrase] += 1
                        theme_sources[phrase].add(handle)
        
        # Build audience demands response
        for theme, frequency in theme_counter.most_common(5):
            if frequency >= 2:  # Only themes that appear multiple times
                audience_demands.append({
                    "theme": theme,
                    "frequency": frequency,
                    "source_competitors": list(theme_sources[theme])
                })
        
        return {
            "hooks": top_hooks,
            "audience_demands": audience_demands
        }
        
    except Exception as e:
        logger.error(f"Failed to load competitor hooks: {e}")
        return {"hooks": [], "audience_demands": []}


# ═══════════════════════════════════════════════════════════════════════
#  TTS / VOICEOVER GENERATION
# ═══════════════════════════════════════════════════════════════════════

@router.post("/generate-voiceover")
async def generate_voiceover_endpoint(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form(None),
    voice_reference: UploadFile = File(None),
    pace: float = Form(1.0),
    exaggeration: float = Form(0.5),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Generate voiceover for video script using Chatterbox TTS.
    
    Args:
        text: Text to convert to speech
        voice_id: Previously saved voice ID
        voice_reference: Audio file for voice cloning
        pace: Speech pace (0.5-2.0)
        exaggeration: Voice exaggeration level (0.0-1.0)
    
    Returns:
        Information about the generated voiceover file
    """
    from app.services.tts_service import tts_service
    
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Text too long (max 2000 characters)")
    
    # Validate pace and exaggeration values
    if not (0.5 <= pace <= 2.0):
        raise HTTPException(status_code=400, detail="Pace must be between 0.5 and 2.0")
    
    if not (0.0 <= exaggeration <= 1.0):
        raise HTTPException(status_code=400, detail="Exaggeration must be between 0.0 and 1.0")
    
    try:
        # Handle voice reference upload if provided
        voice_reference_path = None
        if voice_reference:
            # Save uploaded file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                content = await voice_reference.read()
                tmp_file.write(content)
                voice_reference_path = tmp_file.name
        
        # Generate voiceover
        voiceover_path = await tts_service.generate_voiceover(
            text=text,
            voice_id=voice_id,
            voice_reference_path=voice_reference_path,
            pace=pace,
            exaggeration=exaggeration
        )
        
        # Clean up temporary file if created
        if voice_reference_path and os.path.exists(voice_reference_path):
            os.unlink(voice_reference_path)
        
        # Return relative path for frontend use
        relative_path = voiceover_path.replace("/app/uploads/", "/uploads/")
        
        return {
            "success": True,
            "voiceover_url": relative_path,
            "text_length": len(text),
            "estimated_duration": len(text) / 150,  # Rough estimate: 150 chars per minute
            "voice_id": voice_id,
            "settings": {
                "pace": pace,
                "exaggeration": exaggeration
            }
        }
        
    except Exception as e:
        logger.error(f"Voiceover generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voiceover generation failed: {str(e)}")


@router.post("/clone-voice")
async def clone_voice_endpoint(
    request: Request,
    name: str = Form(...),
    audio_reference: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Clone a voice for reuse in voiceover generation.
    
    Args:
        name: Friendly name for the voice
        audio_reference: Audio file containing the voice to clone
    
    Returns:
        Speaker ID for future use
    """
    from app.services.tts_service import tts_service
    
    if not name or len(name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Voice name cannot be empty")
    
    if not audio_reference:
        raise HTTPException(status_code=400, detail="Audio reference file is required")
    
    try:
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            content = await audio_reference.read()
            tmp_file.write(content)
            temp_path = tmp_file.name
        
        # Clone the voice
        speaker_id = await tts_service.clone_voice(name, temp_path)
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        return {
            "success": True,
            "speaker_id": speaker_id,
            "name": name,
            "message": f"Voice '{name}' cloned successfully"
        }
        
    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {str(e)}")


@router.get("/voices")
async def list_voices_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List available cloned voices."""
    from app.services.tts_service import tts_service
    
    try:
        voices_data = await tts_service.list_voices()
        return voices_data
        
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {str(e)}")


@router.delete("/voices/{speaker_id}")
async def delete_voice_endpoint(
    speaker_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Delete a cloned voice."""
    from app.services.tts_service import tts_service
    
    try:
        success = await tts_service.delete_voice(speaker_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Voice not found")
        
        return {
            "success": True,
            "speaker_id": speaker_id,
            "message": "Voice deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete voice {speaker_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete voice: {str(e)}")


# ── Editing DNA Endpoints ──────────────────────────────────────
# Visual Format Extraction for Remotion Templates

from app.services.editing_dna import (
    init_editing_dna_table,
    extract_visual_layout,
    synthesize_editing_dna,
    process_competitor_for_dna,
    map_dna_to_remotion_config,
    seed_default_dna_templates,
    get_dna_by_id,
    list_dna_templates,
    validate_dna_structure
)

class EditingDnaExtractRequest(BaseModel):
    post_id: Optional[int] = None
    video_url: Optional[str] = None

class EditingDnaCreateRequest(BaseModel):
    name: str
    description: str = ""
    layout_type: str
    layers: list
    audio_logic: dict = {}
    timing_dna: dict = {}


@router.post("/editing-dna/extract")
async def extract_editing_dna(
    body: EditingDnaExtractRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Extract visual layout from competitor post or video URL and create Editing DNA."""
    org_id = get_org_id(request)
    api_key = await _get_gemini_key(db)
    
    # Initialize table if needed
    await init_editing_dna_table(db)
    
    # Seed default templates if needed
    await seed_default_dna_templates(db, org_id)
    
    if body.post_id:
        # Extract from competitor post
        try:
            result = await process_competitor_for_dna(db, body.post_id, org_id, api_key)
            return {
                "success": True,
                "dna_id": result["id"],
                "name": result["name"],
                "layout_type": result["layout_type"],
                "source": "competitor_post",
                "source_id": body.post_id
            }
        except Exception as e:
            logger.error(f"Failed to extract DNA from post {body.post_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
    elif body.video_url:
        # Extract from direct URL
        try:
            # Extract visual layout
            raw_layout = await extract_visual_layout(body.video_url, api_key)
            
            # Synthesize to DNA
            dna = await synthesize_editing_dna(raw_layout)
            
            # Save to database
            layout_type = raw_layout.get("layout_type", "fullscreen")
            name = f"Manual Extract - {layout_type}"
            description = f"Extracted from {body.video_url}"
            
            from app.services.editing_dna import LAYOUT_TO_REMOTION_COMPOSITION
            remotion_composition = LAYOUT_TO_REMOTION_COMPOSITION.get(layout_type, "UniversalTemplate")
            
            result = await db.execute(text("""
                INSERT INTO crm.editing_dna (
                    org_id, name, description, layout_type, aspect_ratio,
                    layers, audio_logic, timing_dna, remotion_composition
                ) VALUES (
                    :org_id, :name, :description, :layout_type, :aspect_ratio,
                    :layers::jsonb, :audio_logic::jsonb, :timing_dna::jsonb, :remotion_composition
                ) RETURNING id
            """), {
                "org_id": org_id,
                "name": name,
                "description": description,
                "layout_type": layout_type,
                "aspect_ratio": dna["meta"]["aspect_ratio"],
                "layers": json.dumps(dna["layers"]),
                "audio_logic": json.dumps(dna["audio_logic"]),
                "timing_dna": json.dumps(dna["timing_dna"]),
                "remotion_composition": remotion_composition
            })
            
            dna_id = result.scalar()
            await db.commit()
            
            return {
                "success": True,
                "dna_id": dna_id,
                "name": name,
                "layout_type": layout_type,
                "source": "video_url",
                "raw_analysis": raw_layout
            }
            
        except Exception as e:
            logger.error(f"Failed to extract DNA from URL {body.video_url}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="Must provide either post_id or video_url")


@router.get("/editing-dna")
async def list_editing_dna(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all saved Editing DNA templates for the organization."""
    org_id = get_org_id(request)
    
    # Initialize table if needed
    await init_editing_dna_table(db)
    
    # Seed default templates if needed
    await seed_default_dna_templates(db, org_id)
    
    try:
        templates = await list_dna_templates(db, org_id)
        return {"dna_templates": templates}
    except Exception as e:
        logger.error(f"Failed to list DNA templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/editing-dna/{dna_id}")
async def get_editing_dna_detail(
    dna_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get full detail of one DNA template including all layers and timing."""
    org_id = get_org_id(request)
    
    try:
        dna = await get_dna_by_id(db, dna_id, org_id)
        if not dna:
            raise HTTPException(status_code=404, detail="DNA template not found")
        return dna
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get DNA template {dna_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/editing-dna/{dna_id}/to-remotion")
async def convert_dna_to_remotion(
    dna_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Convert DNA to Remotion props that can be used directly by the frontend renderer."""
    org_id = get_org_id(request)
    
    try:
        # Get the DNA template
        dna = await get_dna_by_id(db, dna_id, org_id)
        if not dna:
            raise HTTPException(status_code=404, detail="DNA template not found")
        
        # Convert to Remotion config
        remotion_config = map_dna_to_remotion_config(dna["dna"])
        
        return {
            "success": True,
            "dna_id": dna_id,
            "remotion_config": remotion_config,
            "composition": dna.get("remotion_composition", "UniversalTemplate")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to convert DNA {dna_id} to Remotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/editing-dna/create")
async def create_custom_dna(
    body: EditingDnaCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a custom DNA template manually."""
    org_id = get_org_id(request)
    
    # Initialize table if needed
    await init_editing_dna_table(db)
    
    try:
        # Build the DNA structure
        dna = {
            "layout_id": f"custom_{uuid.uuid4().hex[:8]}",
            "meta": {
                "composition_type": "custom",
                "aspect_ratio": "9:16",
                "source_reference_id": "manual_creation"
            },
            "layers": body.layers,
            "audio_logic": body.audio_logic,
            "timing_dna": body.timing_dna
        }
        
        # Validate structure
        issues = validate_dna_structure(dna)
        if issues:
            return {
                "success": False,
                "errors": issues
            }
        
        from app.services.editing_dna import LAYOUT_TO_REMOTION_COMPOSITION
        remotion_composition = LAYOUT_TO_REMOTION_COMPOSITION.get(body.layout_type, "UniversalTemplate")
        
        # Save to database
        result = await db.execute(text("""
            INSERT INTO crm.editing_dna (
                org_id, name, description, layout_type, aspect_ratio,
                layers, audio_logic, timing_dna, remotion_composition
            ) VALUES (
                :org_id, :name, :description, :layout_type, :aspect_ratio,
                :layers::jsonb, :audio_logic::jsonb, :timing_dna::jsonb, :remotion_composition
            ) RETURNING id
        """), {
            "org_id": org_id,
            "name": body.name,
            "description": body.description,
            "layout_type": body.layout_type,
            "aspect_ratio": dna["meta"]["aspect_ratio"],
            "layers": json.dumps(body.layers),
            "audio_logic": json.dumps(body.audio_logic),
            "timing_dna": json.dumps(body.timing_dna),
            "remotion_composition": remotion_composition
        })
        
        dna_id = result.scalar()
        await db.commit()
        
        return {
            "success": True,
            "dna_id": dna_id,
            "name": body.name,
            "layout_type": body.layout_type
        }
        
    except Exception as e:
        logger.error(f"Failed to create custom DNA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
#  COMPETITOR SCRIPT ENGINE — Generate scripts from competitor intel
# ═══════════════════════════════════════════════════════════════════════

class GenerateScriptFromCompetitorRequest(BaseModel):
    reference_post_id: int
    brand_name: str = "Stuff N Things"
    product_name: str = "AI Website Management"
    target_audience: str = "local businesses"  
    key_message: str = "We handle your entire web presence"


@router.get("/competitor-scripts")
async def get_competitor_scripts(
    request: Request,
    format: Optional[str] = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Returns top competitor scripts ranked by engagement.
    
    Each entry: post_id, hook, body_preview, cta, format, likes, engagement, thumbnail_url, media_url
    This powers the "side drawer" in the frontend.
    """
    from app.services.competitor_script_engine import get_top_scripts
    
    org_id = get_org_id(request)
    
    try:
        scripts = await get_top_scripts(db, org_id, format_filter=format, limit=limit)
        
        # Convert to response format for the side drawer
        script_list = []
        for script in scripts:
            # Get additional post data for thumbnails, etc.
            post_query = """
                SELECT cp.post_url, cp.likes, cp.comments, cp.thumbnail_url, 
                       cp.media_url, c.handle, c.platform
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE cp.id = :post_id
            """
            result = await db.execute(text(post_query), {"post_id": script.source_post_id})
            post_data = result.mappings().first()
            
            script_entry = {
                "post_id": script.source_post_id,
                "hook": script.hook,
                "body_preview": " ".join(script.body[:2]) + "..." if len(script.body) > 2 else " ".join(script.body),
                "cta": script.cta,
                "format": script.format_type,
                "likes": post_data["likes"] if post_data else 0,
                "engagement_score": int(script.engagement_score),
                "thumbnail_url": post_data["thumbnail_url"] if post_data else "",
                "media_url": post_data["media_url"] if post_data else "",
                "handle": post_data["handle"] if post_data else "",
                "platform": post_data["platform"] if post_data else "",
                "total_duration": script.total_duration
            }
            script_list.append(script_entry)
            
        return {"scripts": script_list}
        
    except Exception as e:
        logger.error(f"Failed to get competitor scripts: {e}")
        raise HTTPException(status_code=500, detail="Failed to load competitor scripts")


@router.post("/generate-script")
async def generate_script_from_competitor(
    body: GenerateScriptFromCompetitorRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Uses the reference post's structure to generate a new script.
    
    Returns: {hook, body, cta, visual_directions, total_duration, source_reference}
    """
    from app.services.competitor_script_engine import generate_script_from_reference, _get_google_api_key
    
    org_id = get_org_id(request)
    
    try:
        # Get API key
        api_key = await _get_google_api_key(db)
        if not api_key:
            raise HTTPException(status_code=503, detail="Google AI Studio API key not configured")
            
        # Build brand context
        brand_context = {
            "brand_name": body.brand_name,
            "product_name": body.product_name,
            "target_audience": body.target_audience,
            "key_message": body.key_message
        }
        
        # Generate script
        generated_script = await generate_script_from_reference(
            db, body.reference_post_id, brand_context, api_key
        )
        
        if not generated_script:
            raise HTTPException(status_code=400, detail="Failed to generate script from reference")
            
        return {
            "hook": generated_script.hook,
            "body": generated_script.body,
            "cta": generated_script.cta,
            "visual_directions": generated_script.visual_directions,
            "total_duration": generated_script.total_duration,
            "source_reference": body.reference_post_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate script: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@router.get("/competitor-scripts/{post_id}/detail")
async def get_competitor_script_detail(
    post_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Returns full detail for a single competitor post.
    
    Used when the side drawer item is clicked for preview.
    Returns: hook, full transcript, content_analysis, format, engagement metrics
    """
    org_id = get_org_id(request)
    
    try:
        # Get full post details
        query = """
            SELECT cp.*, c.handle, c.platform, c.followers
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE cp.id = :post_id AND c.org_id = :org_id
        """
        result = await db.execute(text(query), {"post_id": post_id, "org_id": org_id})
        post_data = result.mappings().first()
        
        if not post_data:
            raise HTTPException(status_code=404, detail="Competitor post not found")
            
        # Parse JSON fields
        content_analysis = post_data["content_analysis"]
        if isinstance(content_analysis, str):
            try:
                content_analysis = json.loads(content_analysis)
            except json.JSONDecodeError:
                content_analysis = {}
        elif not isinstance(content_analysis, dict):
            content_analysis = {}
            
        transcript_data = post_data["transcript"]
        if isinstance(transcript_data, str):
            try:
                transcript_data = json.loads(transcript_data)
            except json.JSONDecodeError:
                transcript_data = {}
        elif not isinstance(transcript_data, dict):
            transcript_data = {}
            
        return {
            "post_id": post_id,
            "hook": post_data["hook"],
            "full_transcript": transcript_data.get("text", ""),
            "content_analysis": content_analysis,
            "format": post_data["detected_format"],
            "engagement_metrics": {
                "likes": post_data["likes"],
                "comments": post_data["comments"], 
                "shares": post_data["shares"],
                "engagement_score": float(post_data["engagement_score"] or 0)
            },
            "competitor_info": {
                "handle": post_data["handle"],
                "platform": post_data["platform"],
                "followers": post_data["followers"]
            },
            "post_url": post_data["post_url"],
            "media_url": post_data["media_url"],
            "thumbnail_url": post_data["thumbnail_url"],
            "posted_at": str(post_data["posted_at"]) if post_data["posted_at"] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get competitor script detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to load script detail")