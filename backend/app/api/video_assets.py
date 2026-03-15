"""Video Copycat Assets API

Asset generation and avatar services for Video Copycat pipeline.
Stages 3-4: Asset Generation + Avatar Swap
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import get_leadgen_db, leadgen_engine
from app.db.crm_db import crm_session
from app.api.auth import get_current_user
from app.models.crm.user import User
from app.services.tenant import get_org_id
from app.services import asset_generator, avatar_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Asset storage directory
ASSET_DIR = Path("/home/eddy/Development/warroom/backend/generated_assets")


# ── Pydantic Models ────────────────────────────────────────────────────────

class AssetGenerationRequest(BaseModel):
    """Request to generate assets for a storyboard."""
    storyboard_id: int
    scenes: List[Dict[str, Any]]
    brand_colors: Optional[List[str]] = None
    style: str = "modern"
    force_regenerate: bool = False


class AssetResponse(BaseModel):
    """Response model for asset information."""
    id: int
    storyboard_id: int
    scene_index: int
    asset_type: str
    file_path: Optional[str] = None
    cloud_url: Optional[str] = None
    prompt_used: Optional[str] = None
    dimensions: Optional[str] = None
    format: Optional[str] = None
    status: str
    created_at: datetime


class DigitalCopySetupRequest(BaseModel):
    """Request to set up digital copy configuration."""
    voice_provider: str = "edge-tts"
    voice_clone_id: Optional[str] = None
    default_style: str = "professional"


class DigitalCopyResponse(BaseModel):
    """Response model for digital copy information."""
    id: int
    org_id: int
    user_id: int
    avatar_images: List[str]
    voice_clone_id: Optional[str]
    voice_provider: str
    default_style: str
    created_at: datetime
    updated_at: datetime


class VoiceGenerationRequest(BaseModel):
    """Request to generate voice audio."""
    text: str = Field(..., max_length=5000)
    emotion: str = "neutral"
    voice_clone_id: Optional[str] = None


# ── Database Initialization ────────────────────────────────────────────────

async def init_video_copycat_tables():
    """Initialize video assets and digital copies tables."""
    try:
        # Execute the migration SQL
        migration_sql = (Path(__file__).parent.parent / "db" / "video_assets_migration.sql").read_text()
        
        # Split and execute individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        async with leadgen_engine.begin() as conn:
            for statement in statements:
                if statement:
                    await conn.execute(text(statement))
        
        logger.info("Video assets tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize video assets tables: {e}")
        return False


# ── Asset Generation Endpoints ─────────────────────────────────────────────

@router.post("/storyboards/{storyboard_id}/generate-assets")
async def generate_assets(
    storyboard_id: int,
    request: AssetGenerationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db)
):
    """Kick off asset generation for a storyboard."""
    try:
        org_id = await get_org_id(db, user.id)
        if not org_id:
            raise HTTPException(status_code=400, detail="No organization found for user")
        
        # Plan assets based on script scenes
        script = {"scenes": request.scenes}
        storyboard = {"id": storyboard_id}
        
        asset_plans = asset_generator.plan_assets(script, storyboard)
        
        # Store asset generation tasks in database
        generated_assets = []
        
        for scene_plan in asset_plans:
            scene_index = scene_plan["scene_index"]
            
            for asset_info in scene_plan["assets"]:
                # Insert pending asset record
                insert_query = text("""
                    INSERT INTO public.video_assets 
                    (org_id, storyboard_id, scene_index, asset_type, prompt_used, 
                     dimensions, format, status)
                    VALUES (:org_id, :storyboard_id, :scene_index, :asset_type, 
                            :prompt_used, :dimensions, :format, 'pending')
                    RETURNING id, created_at
                """)
                
                result = await db.execute(insert_query, {
                    "org_id": org_id,
                    "storyboard_id": storyboard_id,
                    "scene_index": scene_index,
                    "asset_type": asset_info["asset_type"],
                    "prompt_used": asset_info["prompt"],
                    "dimensions": f"{asset_info['dimensions'][0]}x{asset_info['dimensions'][1]}",
                    "format": asset_info["format"]
                })
                
                row = result.fetchone()
                
                generated_assets.append({
                    "id": row.id,
                    "scene_index": scene_index,
                    "asset_type": asset_info["asset_type"],
                    "status": "pending",
                    "created_at": row.created_at
                })
        
        await db.commit()
        
        # Start background asset generation
        asyncio.create_task(_generate_assets_background(
            org_id, storyboard_id, asset_plans, request.brand_colors, request.style
        ))
        
        return {
            "storyboard_id": storyboard_id,
            "total_assets": len(generated_assets),
            "assets": generated_assets,
            "status": "generation_started"
        }
        
    except Exception as e:
        logger.error(f"Error starting asset generation: {e}")
        raise HTTPException(status_code=500, detail="Asset generation failed")


@router.get("/storyboards/{storyboard_id}/assets")
async def list_storyboard_assets(
    storyboard_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db)
):
    """List all assets for a storyboard."""
    try:
        org_id = await get_org_id(db, user.id)
        if not org_id:
            raise HTTPException(status_code=400, detail="No organization found for user")
        
        query = text("""
            SELECT id, org_id, storyboard_id, scene_index, asset_type, 
                   file_path, cloud_url, prompt_used, dimensions, format,
                   status, created_at, updated_at
            FROM public.video_assets 
            WHERE org_id = :org_id AND storyboard_id = :storyboard_id
            ORDER BY scene_index, asset_type
        """)
        
        result = await db.execute(query, {
            "org_id": org_id,
            "storyboard_id": storyboard_id
        })
        
        assets = []
        for row in result.fetchall():
            assets.append({
                "id": row.id,
                "storyboard_id": row.storyboard_id,
                "scene_index": row.scene_index,
                "asset_type": row.asset_type,
                "file_path": row.file_path,
                "cloud_url": row.cloud_url,
                "prompt_used": row.prompt_used,
                "dimensions": row.dimensions,
                "format": row.format,
                "status": row.status,
                "created_at": row.created_at,
                "updated_at": row.updated_at
            })
        
        return {
            "storyboard_id": storyboard_id,
            "assets": assets,
            "total_count": len(assets)
        }
        
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        raise HTTPException(status_code=500, detail="Failed to list assets")


@router.get("/assets/{asset_id}")
async def get_asset_detail(
    asset_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db)
):
    """Get detailed information about a specific asset."""
    try:
        org_id = await get_org_id(db, user.id)
        if not org_id:
            raise HTTPException(status_code=400, detail="No organization found for user")
        
        query = text("""
            SELECT id, org_id, storyboard_id, scene_index, asset_type,
                   file_path, cloud_url, prompt_used, dimensions, format,
                   status, created_at, updated_at
            FROM public.video_assets 
            WHERE id = :asset_id AND org_id = :org_id
        """)
        
        result = await db.execute(query, {
            "asset_id": asset_id,
            "org_id": org_id
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset_data = {
            "id": row.id,
            "storyboard_id": row.storyboard_id,
            "scene_index": row.scene_index,
            "asset_type": row.asset_type,
            "file_path": row.file_path,
            "cloud_url": row.cloud_url,
            "prompt_used": row.prompt_used,
            "dimensions": row.dimensions,
            "format": row.format,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at
        }
        
        # Add file info if asset exists
        if row.file_path and Path(row.file_path).exists():
            file_info = await asset_generator.get_asset_info(row.file_path)
            asset_data["file_info"] = file_info
        
        return asset_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to get asset")


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db)
):
    """Download an asset file."""
    try:
        org_id = await get_org_id(db, user.id)
        if not org_id:
            raise HTTPException(status_code=400, detail="No organization found for user")
        
        query = text("""
            SELECT file_path, asset_type, format
            FROM public.video_assets 
            WHERE id = :asset_id AND org_id = :org_id AND status = 'complete'
        """)
        
        result = await db.execute(query, {
            "asset_id": asset_id,
            "org_id": org_id
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found or not ready")
        
        file_path = Path(row.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Asset file not found")
        
        return FileResponse(
            path=str(file_path),
            filename=f"{row.asset_type}_{asset_id}.{row.format}",
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading asset: {e}")
        raise HTTPException(status_code=500, detail="Download failed")


# ── Digital Copy Endpoints ─────────────────────────────────────────────────

@router.post("/digital-copies/setup")
async def setup_digital_copy(
    request: DigitalCopySetupRequest,
    avatar_files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user)
):
    """Upload avatar images and configure digital copy settings."""
    try:
        async with crm_session() as db:
            org_id = await get_org_id(db, user.id)
            if not org_id:
                raise HTTPException(status_code=400, detail="No organization found for user")
            
            # Save uploaded avatar images
            avatar_paths = []
            avatar_dir = ASSET_DIR / "avatars" / f"org_{org_id}" / f"user_{user.id}"
            avatar_dir.mkdir(parents=True, exist_ok=True)
            
            for i, file in enumerate(avatar_files):
                if not file.content_type.startswith('image/'):
                    continue
                
                file_extension = Path(file.filename).suffix.lower()
                if file_extension not in ['.jpg', '.jpeg', '.png']:
                    continue
                
                filename = f"avatar_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
                file_path = avatar_dir / filename
                
                content = await file.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                avatar_paths.append(str(file_path))
            
            if not avatar_paths:
                raise HTTPException(status_code=400, detail="No valid avatar images provided")
            
            # Validate avatar images
            validation_result = await avatar_service.validate_avatar_images(avatar_paths)
            if not validation_result["valid_images"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"No valid avatar images: {validation_result['issues']}"
                )
            
            # Upsert digital copy record
            upsert_query = text("""
                INSERT INTO crm.digital_copies 
                (org_id, user_id, avatar_images, voice_clone_id, voice_provider, default_style)
                VALUES (:org_id, :user_id, CAST(:avatar_images AS jsonb), :voice_clone_id, :voice_provider, :default_style)
                ON CONFLICT (org_id, user_id) 
                DO UPDATE SET 
                    avatar_images = EXCLUDED.avatar_images,
                    voice_clone_id = EXCLUDED.voice_clone_id,
                    voice_provider = EXCLUDED.voice_provider,
                    default_style = EXCLUDED.default_style,
                    updated_at = NOW()
                RETURNING id, created_at, updated_at
            """)
            
            result = await db.execute(upsert_query, {
                "org_id": org_id,
                "user_id": user.id,
                "avatar_images": json.dumps(validation_result["valid_images"]),
                "voice_clone_id": request.voice_clone_id,
                "voice_provider": request.voice_provider,
                "default_style": request.default_style
            })
            
            row = result.fetchone()
            await db.commit()
            
            return {
                "id": row.id,
                "org_id": org_id,
                "user_id": user.id,
                "avatar_images": validation_result["valid_images"],
                "voice_clone_id": request.voice_clone_id,
                "voice_provider": request.voice_provider,
                "default_style": request.default_style,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "validation": validation_result
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up digital copy: {e}")
        raise HTTPException(status_code=500, detail="Digital copy setup failed")


@router.get("/digital-copies/me")
async def get_my_digital_copy(
    user: User = Depends(get_current_user)
):
    """Get current user's digital copy configuration."""
    try:
        async with crm_session() as db:
            org_id = await get_org_id(db, user.id)
            if not org_id:
                raise HTTPException(status_code=400, detail="No organization found for user")
            
            digital_copy = await avatar_service.get_digital_copy(db, org_id, user.id)
            
            if not digital_copy:
                return {"message": "No digital copy configured"}
            
            return digital_copy
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting digital copy: {e}")
        raise HTTPException(status_code=500, detail="Failed to get digital copy")


@router.put("/digital-copies/me")
async def update_my_digital_copy(
    request: DigitalCopySetupRequest,
    user: User = Depends(get_current_user)
):
    """Update current user's digital copy settings."""
    try:
        async with crm_session() as db:
            org_id = await get_org_id(db, user.id)
            if not org_id:
                raise HTTPException(status_code=400, detail="No organization found for user")
            
            # Check if digital copy exists
            existing = await avatar_service.get_digital_copy(db, org_id, user.id)
            if not existing:
                raise HTTPException(status_code=404, detail="Digital copy not found - set up first")
            
            # Update settings
            update_query = text("""
                UPDATE crm.digital_copies 
                SET voice_clone_id = :voice_clone_id,
                    voice_provider = :voice_provider,
                    default_style = :default_style,
                    updated_at = NOW()
                WHERE org_id = :org_id AND user_id = :user_id
                RETURNING id, created_at, updated_at
            """)
            
            result = await db.execute(update_query, {
                "org_id": org_id,
                "user_id": user.id,
                "voice_clone_id": request.voice_clone_id,
                "voice_provider": request.voice_provider,
                "default_style": request.default_style
            })
            
            row = result.fetchone()
            await db.commit()
            
            # Return updated digital copy
            return await avatar_service.get_digital_copy(db, org_id, user.id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating digital copy: {e}")
        raise HTTPException(status_code=500, detail="Update failed")


@router.post("/digital-copies/generate-voice")
async def generate_voice_sample(
    request: VoiceGenerationRequest,
    user: User = Depends(get_current_user)
):
    """Generate a voice audio sample."""
    try:
        async with crm_session() as db:
            org_id = await get_org_id(db, user.id)
            if not org_id:
                raise HTTPException(status_code=400, detail="No organization found for user")
            
            # Get user's voice settings if available
            digital_copy = await avatar_service.get_digital_copy(db, org_id, user.id)
            
            voice_clone_id = request.voice_clone_id
            if not voice_clone_id and digital_copy:
                voice_clone_id = digital_copy.get("voice_clone_id")
            
            # Generate voice audio
            audio_path = await avatar_service.generate_voice_audio(
                text=request.text,
                voice_clone_id=voice_clone_id or "en-US-AvaNeural",
                emotion=request.emotion
            )
            
            return {
                "audio_path": audio_path,
                "text": request.text,
                "voice_clone_id": voice_clone_id,
                "emotion": request.emotion,
                "file_exists": Path(audio_path).exists()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating voice: {e}")
        raise HTTPException(status_code=500, detail="Voice generation failed")


@router.get("/digital-copies/voices")
async def list_available_voices():
    """Get list of available voices for voice cloning."""
    try:
        voices = await avatar_service.get_available_voices("edge-tts")
        return {
            "voices": voices,
            "total_count": len(voices),
            "provider": "edge-tts"
        }
        
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        raise HTTPException(status_code=500, detail="Failed to list voices")


# ── Background Tasks ───────────────────────────────────────────────────────

async def _generate_assets_background(
    org_id: int,
    storyboard_id: int, 
    asset_plans: List[Dict[str, Any]],
    brand_colors: Optional[List[str]],
    style: str
):
    """Background task to generate assets."""
    try:
        async with leadgen_engine.begin() as conn:
            for scene_plan in asset_plans:
                for asset_info in scene_plan["assets"]:
                    try:
                        # Generate the asset based on type
                        if asset_info["asset_type"] == "product-shot":
                            file_path = await asset_generator.generate_product_shot(
                                product_description=asset_info["prompt"],
                                style=style
                            )
                        elif asset_info["asset_type"] == "background":
                            file_path = await asset_generator.generate_background(
                                description=asset_info["prompt"],
                                brand_colors=brand_colors
                            )
                        elif asset_info["asset_type"] == "infographic":
                            # Extract data from prompt for infographic
                            data = {"text": asset_info["prompt"]}
                            file_path = await asset_generator.generate_infographic(
                                data=data,
                                style=style
                            )
                        else:
                            # Generic asset generation
                            file_path = await asset_generator.generate_background(
                                description=asset_info["prompt"]
                            )
                        
                        # Update database with generated file
                        update_query = text("""
                            UPDATE public.video_assets 
                            SET file_path = :file_path, 
                                status = 'complete',
                                updated_at = NOW()
                            WHERE org_id = :org_id 
                              AND storyboard_id = :storyboard_id 
                              AND scene_index = :scene_index
                              AND asset_type = :asset_type
                              AND status = 'pending'
                        """)
                        
                        await conn.execute(update_query, {
                            "file_path": file_path,
                            "org_id": org_id,
                            "storyboard_id": storyboard_id,
                            "scene_index": scene_plan["scene_index"],
                            "asset_type": asset_info["asset_type"]
                        })
                        
                        logger.info(f"Generated asset: {asset_info['asset_type']} for scene {scene_plan['scene_index']}")
                        
                    except Exception as e:
                        logger.error(f"Failed to generate asset {asset_info['asset_type']}: {e}")
                        
                        # Mark as failed
                        fail_query = text("""
                            UPDATE public.video_assets 
                            SET status = 'failed',
                                updated_at = NOW()
                            WHERE org_id = :org_id 
                              AND storyboard_id = :storyboard_id 
                              AND scene_index = :scene_index
                              AND asset_type = :asset_type
                              AND status = 'pending'
                        """)
                        
                        await conn.execute(fail_query, {
                            "org_id": org_id,
                            "storyboard_id": storyboard_id,
                            "scene_index": scene_plan["scene_index"],
                            "asset_type": asset_info["asset_type"]
                        })
        
        logger.info(f"Background asset generation completed for storyboard {storyboard_id}")
        
    except Exception as e:
        logger.error(f"Background asset generation failed: {e}")


# ── Static File Serving ────────────────────────────────────────────────────

@router.get("/serve/{asset_type}/{filename}")
async def serve_asset_file(asset_type: str, filename: str):
    """Serve generated asset files."""
    try:
        file_path = ASSET_DIR / asset_type / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Asset file not found")
        
        # Basic security check - ensure file is within assets directory
        if not str(file_path.resolve()).startswith(str(ASSET_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(path=str(file_path))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving asset file: {e}")
        raise HTTPException(status_code=500, detail="File serving failed")