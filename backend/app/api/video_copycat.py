"""Video Copycat API — Analyze competitor videos and generate new scripts."""

import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.crm_db import get_tenant_db
from app.db.leadgen_db import leadgen_engine
from app.models.crm.user import User
from app.services.tenant import get_org_id
from app.services.video_analyzer import analyze_video, VideoStoryboard, storyboard_to_json, json_to_storyboard
from app.services.video_script_generator import generate_script, VideoScript, script_to_json, json_to_script

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Schemas ────────────────────────────────────────────────────────────

class VideoAnalysisRequest(BaseModel):
    video_url: str
    source_competitor_id: Optional[int] = None
    title: Optional[str] = None

class BrandContextRequest(BaseModel):
    brand_name: str
    product_name: str
    target_audience: str = "potential customers"
    key_message: str = ""
    brand_voice: str = "conversational and authentic"
    product_url: Optional[str] = None

class ScriptGenerationRequest(BaseModel):
    brand_context: BrandContextRequest

class StoryboardResponse(BaseModel):
    id: int
    org_id: int
    user_id: int
    source_url: str
    source_competitor_id: Optional[int]
    title: Optional[str]
    status: str
    storyboard: dict
    generated_script: Optional[dict]
    created_at: datetime
    updated_at: datetime

class StoryboardListResponse(BaseModel):
    storyboards: List[StoryboardResponse]
    total: int

# ── Helper Functions ───────────────────────────────────────────────────

async def get_api_key_for_analysis(org_id: int) -> str:
    """Get Google AI API key from settings for video analysis."""
    async with leadgen_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT value FROM public.settings WHERE key = 'google_ai_api_key' AND org_id = :org_id"),
            {"org_id": org_id}
        )
        row = result.fetchone()
        
        if not row or not row[0]:
            # Try anthropic or openai as fallback
            result = await conn.execute(
                text("SELECT value FROM public.settings WHERE key IN ('anthropic_api_key', 'openai_api_key') AND org_id = :org_id ORDER BY key"),
                {"org_id": org_id}
            )
            row = result.fetchone()
            
            if not row or not row[0]:
                raise HTTPException(
                    status_code=400,
                    detail="No AI API key configured. Please add google_ai_api_key, anthropic_api_key, or openai_api_key in settings."
                )
        
        return row[0]

async def init_video_copycat_tables():
    """Initialize video copycat tables."""
    import os
    
    # Get the absolute path to the migration file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    migration_path = os.path.join(current_dir, "../db/video_copycat_migration.sql")
    
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    async with leadgen_engine.begin() as conn:
        await conn.execute(text(migration_sql))
    
    logger.info("Video copycat tables initialized")

# ── API Endpoints ──────────────────────────────────────────────────────

@router.post("/analyze", response_model=StoryboardResponse)
async def analyze_video_endpoint(
    request: VideoAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_org_id)
):
    """Submit video URL for analysis and storyboard extraction."""
    
    try:
        # Create initial record with analyzing status
        async with leadgen_engine.begin() as conn:
            result = await conn.execute(
                text("""
                    INSERT INTO public.video_storyboards 
                    (org_id, user_id, source_url, source_competitor_id, title, status, storyboard)
                    VALUES (:org_id, :user_id, :source_url, :source_competitor_id, :title, 'analyzing', '{}')
                    RETURNING id, created_at, updated_at
                """),
                {
                    "org_id": org_id,
                    "user_id": current_user.id,
                    "source_url": request.video_url,
                    "source_competitor_id": request.source_competitor_id,
                    "title": request.title or f"Video from {request.video_url}"
                }
            )
            
            row = result.fetchone()
            storyboard_id = row[0]
            created_at = row[1]
            updated_at = row[2]
        
        # Schedule background analysis
        background_tasks.add_task(
            analyze_video_background,
            storyboard_id=storyboard_id,
            video_url=request.video_url,
            org_id=org_id
        )
        
        # Return initial response
        return StoryboardResponse(
            id=storyboard_id,
            org_id=org_id,
            user_id=current_user.id,
            source_url=request.video_url,
            source_competitor_id=request.source_competitor_id,
            title=request.title,
            status="analyzing",
            storyboard={},
            generated_script=None,
            created_at=created_at,
            updated_at=updated_at
        )
        
    except Exception as e:
        logger.error(f"Video analysis request failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start video analysis")


async def analyze_video_background(storyboard_id: int, video_url: str, org_id: int):
    """Background task to analyze video and update storyboard."""
    
    try:
        # Get API key
        api_key = await get_api_key_for_analysis(org_id)
        
        # Analyze video
        storyboard = await analyze_video(video_url, api_key)
        
        # Update database with results
        async with leadgen_engine.begin() as conn:
            await conn.execute(
                text("""
                    UPDATE public.video_storyboards 
                    SET storyboard = CAST(:storyboard AS jsonb), status = 'analyzed'
                    WHERE id = :id
                """),
                {
                    "id": storyboard_id,
                    "storyboard": json.dumps(storyboard_to_json(storyboard))
                }
            )
        
        logger.info(f"Video analysis completed for storyboard {storyboard_id}")
        
    except Exception as e:
        logger.error(f"Video analysis background task failed: {e}")
        
        # Update status to show error
        async with leadgen_engine.begin() as conn:
            await conn.execute(
                text("""
                    UPDATE public.video_storyboards 
                    SET status = 'analyzed'
                    WHERE id = :id
                """),
                {"id": storyboard_id}
            )


@router.get("/storyboards", response_model=StoryboardListResponse)
async def list_storyboards(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_org_id)
):
    """List user's video storyboards."""
    
    where_clause = "WHERE org_id = :org_id"
    params = {"org_id": org_id}
    
    if status:
        where_clause += " AND status = :status"
        params["status"] = status
    
    async with leadgen_engine.begin() as conn:
        # Get total count
        count_result = await conn.execute(
            text(f"SELECT COUNT(*) FROM public.video_storyboards {where_clause}"),
            params
        )
        total = count_result.fetchone()[0]
        
        # Get paginated results
        result = await conn.execute(
            text(f"""
                SELECT id, org_id, user_id, source_url, source_competitor_id, title, status, 
                       storyboard, generated_script, created_at, updated_at
                FROM public.video_storyboards 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """),
            {**params, "limit": limit, "skip": skip}
        )
        
        storyboards = []
        for row in result:
            storyboard = StoryboardResponse(
                id=row[0],
                org_id=row[1],
                user_id=row[2],
                source_url=row[3],
                source_competitor_id=row[4],
                title=row[5],
                status=row[6],
                storyboard=row[7] or {},
                generated_script=row[8],
                created_at=row[9],
                updated_at=row[10]
            )
            storyboards.append(storyboard)
    
    return StoryboardListResponse(storyboards=storyboards, total=total)


@router.get("/storyboards/{storyboard_id}", response_model=StoryboardResponse)
async def get_storyboard(
    storyboard_id: int,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_org_id)
):
    """Get specific storyboard details."""
    
    async with leadgen_engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT id, org_id, user_id, source_url, source_competitor_id, title, status,
                       storyboard, generated_script, created_at, updated_at
                FROM public.video_storyboards 
                WHERE id = :id AND org_id = :org_id
            """),
            {"id": storyboard_id, "org_id": org_id}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Storyboard not found")
        
        return StoryboardResponse(
            id=row[0],
            org_id=row[1],
            user_id=row[2],
            source_url=row[3],
            source_competitor_id=row[4],
            title=row[5],
            status=row[6],
            storyboard=row[7] or {},
            generated_script=row[8],
            created_at=row[9],
            updated_at=row[10]
        )


@router.post("/storyboards/{storyboard_id}/generate-script", response_model=StoryboardResponse)
async def generate_script_endpoint(
    storyboard_id: int,
    request: ScriptGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_org_id)
):
    """Generate script from storyboard."""
    
    # Get existing storyboard
    async with leadgen_engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT storyboard, status FROM public.video_storyboards 
                WHERE id = :id AND org_id = :org_id
            """),
            {"id": storyboard_id, "org_id": org_id}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Storyboard not found")
        
        if row[1] != 'analyzed':
            raise HTTPException(status_code=400, detail="Storyboard not ready for script generation")
        
        storyboard_json = row[0]
    
    try:
        # Update status to generating
        async with leadgen_engine.begin() as conn:
            await conn.execute(
                text("UPDATE public.video_storyboards SET status = 'generating' WHERE id = :id"),
                {"id": storyboard_id}
            )
        
        # Schedule background script generation
        background_tasks.add_task(
            generate_script_background,
            storyboard_id=storyboard_id,
            storyboard_json=storyboard_json,
            brand_context=request.brand_context.dict(),
            org_id=org_id
        )
        
        # Return updated response
        return await get_storyboard(storyboard_id, current_user, org_id)
        
    except Exception as e:
        logger.error(f"Script generation request failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start script generation")


async def generate_script_background(storyboard_id: int, storyboard_json: dict, brand_context: dict, org_id: int):
    """Background task to generate script from storyboard."""
    
    try:
        # Get API key
        api_key = await get_api_key_for_analysis(org_id)
        
        # Convert JSON back to storyboard object
        storyboard = json_to_storyboard(storyboard_json)
        
        # Generate script
        script = await generate_script(
            storyboard=storyboard,
            brand_context=brand_context,
            product_url=brand_context.get('product_url'),
            api_key=api_key
        )
        
        # Update database with generated script
        async with leadgen_engine.begin() as conn:
            await conn.execute(
                text("""
                    UPDATE public.video_storyboards 
                    SET generated_script = CAST(:script AS jsonb), status = 'scripted'
                    WHERE id = :id
                """),
                {
                    "id": storyboard_id,
                    "script": json.dumps(script_to_json(script))
                }
            )
        
        logger.info(f"Script generation completed for storyboard {storyboard_id}")
        
    except Exception as e:
        logger.error(f"Script generation background task failed: {e}")
        
        # Revert status on error
        async with leadgen_engine.begin() as conn:
            await conn.execute(
                text("UPDATE public.video_storyboards SET status = 'analyzed' WHERE id = :id"),
                {"id": storyboard_id}
            )


@router.put("/storyboards/{storyboard_id}/script")
async def update_script(
    storyboard_id: int,
    script_data: dict,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_org_id)
):
    """Manually edit script for a storyboard."""
    
    try:
        # Validate script structure (basic check)
        if 'scenes' not in script_data or 'title' not in script_data:
            raise HTTPException(status_code=400, detail="Invalid script format")
        
        async with leadgen_engine.begin() as conn:
            # Verify storyboard exists and belongs to org
            check_result = await conn.execute(
                text("SELECT id FROM public.video_storyboards WHERE id = :id AND org_id = :org_id"),
                {"id": storyboard_id, "org_id": org_id}
            )
            
            if not check_result.fetchone():
                raise HTTPException(status_code=404, detail="Storyboard not found")
            
            # Update script
            await conn.execute(
                text("""
                    UPDATE public.video_storyboards 
                    SET generated_script = CAST(:script AS jsonb), status = 'scripted'
                    WHERE id = :id
                """),
                {
                    "id": storyboard_id,
                    "script": json.dumps(script_data)
                }
            )
        
        return {"message": "Script updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Script update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update script")