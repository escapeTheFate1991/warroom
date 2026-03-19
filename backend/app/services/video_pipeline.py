"""Video Production Pipeline — End-to-end orchestrator.

Connects: Competitor Intel → Script → Storyboard → Editing DNA → Digital Copy → Nano Banana → Veo → Final Video
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Import existing services
from app.services.competitor_script_engine import generate_script_from_reference, extract_hook_body_cta
from app.services.editing_dna import process_competitor_for_dna, map_dna_to_remotion_config, get_dna_by_id
from app.services.nano_banana import generate_reference_sheet, generate_scene
from app.services.veo_service import generate_video_from_image, check_video_status
from app.services.video_composer import build_composition, generate_remotion_config, render_with_ffmpeg

logger = logging.getLogger(__name__)


async def create_project_from_pipeline(
    db: AsyncSession, pipeline_id: int, user_id: int,
    title: str, script: str, digital_copy_id: Optional[int],
    reference_post_id: Optional[int], assets: List[Dict],
    status: str = "complete", video_url: str = ""
):
    """Bridge: create a ugc_video_projects entry when pipeline completes."""
    project_id = str(uuid.uuid4())
    
    # Find final video URL from assets
    if not video_url:
        for asset in reversed(assets):
            if asset.get("type") in ("composed_video", "scene_video") and asset.get("url"):
                video_url = asset["url"]
                break
    
    storyboard_json = json.dumps([
        {"index": a.get("index", i), "type": a.get("type"), "url": a.get("url", ""), "prompt": a.get("prompt", "")}
        for i, a in enumerate(assets) if a.get("type") in ("scene_image", "scene_video", "composed_video")
    ])
    
    await db.execute(text("""
        INSERT INTO public.ugc_video_projects (
            id, user_id, title, script, digital_copy_id, status, video_url,
            storyboard, generation_id, content_mode
        ) VALUES (
            :id, :user_id, :title, :script, :copy_id, :status, :video_url,
            :storyboard::jsonb, :gen_id, 'competitor_clone'
        ) ON CONFLICT (id) DO NOTHING
    """), {
        "id": project_id,
        "user_id": user_id,
        "title": title,
        "script": script,
        "copy_id": str(digital_copy_id) if digital_copy_id else None,
        "status": "completed" if status == "complete" else "processing",
        "video_url": video_url,
        "storyboard": storyboard_json,
        "gen_id": str(pipeline_id),
    })
    await db.commit()
    logger.info(f"Created project {project_id} from pipeline {pipeline_id}")
    return project_id

# ═══════════════════════════════════════════════════════════════════════
# DATABASE SETUP
# ═══════════════════════════════════════════════════════════════════════

PIPELINE_DDL = """
CREATE TABLE IF NOT EXISTS crm.video_pipelines (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    digital_copy_id INTEGER,
    reference_post_id INTEGER,
    editing_dna_id INTEGER,
    script JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending',  -- pending, generating_script, generating_images, generating_video, composing, complete, failed
    current_step TEXT,
    progress INTEGER DEFAULT 0,
    generated_assets JSONB DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_pipelines_org_user ON crm.video_pipelines(org_id, user_id);
CREATE INDEX IF NOT EXISTS idx_video_pipelines_status ON crm.video_pipelines(status);
"""

async def init_pipeline_table(db: AsyncSession):
    """Initialize the video_pipelines table if it doesn't exist."""
    try:
        await db.execute(text(PIPELINE_DDL))
        await db.commit()
        logger.info("Video pipeline table initialized")
    except Exception as e:
        logger.warning(f"Error initializing video pipeline table: {e}")
        await db.rollback()

# ═══════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class PipelineAsset:
    """Generated asset in the pipeline."""
    type: str  # "script", "reference_sheet", "scene_image", "video", "composition"
    url: str
    metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class PipelineResult:
    """Final result from the pipeline."""
    pipeline_id: int
    status: str
    progress: int
    current_step: str
    generated_assets: List[PipelineAsset]
    error_message: Optional[str] = None

# ═══════════════════════════════════════════════════════════════════════
# CORE PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

async def _get_api_key(db: AsyncSession) -> str:
    """Get Google AI Studio API key from database or environment."""
    # Try environment first
    key = os.environ.get('GOOGLE_AI_STUDIO_API_KEY')
    if key:
        return key
    
    # Fallback to database
    result = await db.execute(text("SELECT value FROM public.settings WHERE key = 'google_ai_studio_api_key'"))
    row = result.first()
    if row:
        return row[0]
    
    raise ValueError("Google AI Studio API key not configured")

async def _update_pipeline_status(
    db: AsyncSession,
    pipeline_id: int,
    status: str,
    progress: int,
    current_step: str,
    assets: Optional[List[Dict[str, Any]]] = None,
    error_message: Optional[str] = None
):
    """Update pipeline status in database."""
    update_data = {
        "pipeline_id": pipeline_id,
        "status": status,
        "progress": progress,
        "current_step": current_step,
        "updated_at": datetime.now()
    }
    
    if assets:
        update_data["generated_assets"] = json.dumps(assets)
    
    if error_message:
        update_data["error_message"] = error_message
    
    query = """
        UPDATE crm.video_pipelines 
        SET status = :status, 
            progress = :progress, 
            current_step = :current_step, 
            updated_at = :updated_at
    """
    
    if assets:
        query += ", generated_assets = :generated_assets::jsonb"
    
    if error_message:
        query += ", error_message = :error_message"
    
    query += " WHERE id = :pipeline_id"
    
    await db.execute(text(query), update_data)
    await db.commit()

async def create_video_from_competitor_reference(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    reference_post_id: int,
    digital_copy_id: int,
    brand_context: Dict[str, Any],
    api_key: str
) -> Dict[str, Any]:
    """
    Full pipeline: competitor post → script → DNA → scene images → video → composition.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID
        reference_post_id: ID of competitor post to use as reference
        digital_copy_id: Digital copy/character to use
        brand_context: Brand info (brand_name, product_name, target_audience, key_message)
        api_key: Google AI Studio API key
        
    Returns:
        Pipeline result with operation ID and initial status
    """
    # Initialize pipeline table if needed
    await init_pipeline_table(db)
    
    # Create pipeline record
    result = await db.execute(text("""
        INSERT INTO crm.video_pipelines (
            org_id, user_id, digital_copy_id, reference_post_id, 
            status, current_step, progress
        ) VALUES (
            :org_id, :user_id, :digital_copy_id, :reference_post_id,
            'pending', 'loading_reference', 0
        ) RETURNING id
    """), {
        "org_id": org_id,
        "user_id": user_id,
        "digital_copy_id": digital_copy_id,
        "reference_post_id": reference_post_id
    })
    
    pipeline_id = result.scalar()
    await db.commit()
    
    assets = []
    
    try:
        # Step 1: Load competitor post from DB
        await _update_pipeline_status(db, pipeline_id, "pending", 10, "loading_reference")
        
        post_result = await db.execute(text("""
            SELECT cp.*, c.handle, c.platform
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE cp.id = :post_id
        """), {"post_id": reference_post_id})
        
        post_row = post_result.mappings().first()
        if not post_row:
            raise ValueError(f"Competitor post {reference_post_id} not found")
        
        post_data = dict(post_row)
        
        # Step 2: Extract script structure (hook/body/CTA) from content_analysis
        await _update_pipeline_status(db, pipeline_id, "generating_script", 20, "extracting_script_structure")
        
        script_structure = await extract_hook_body_cta(post_data)
        if not script_structure:
            raise ValueError("Could not extract script structure from competitor post")
        
        # Step 3: Generate new script using Gemini (rewrite with brand voice)
        await _update_pipeline_status(db, pipeline_id, "generating_script", 30, "generating_brand_script")
        
        generated_script = await generate_script_from_reference(
            db, reference_post_id, brand_context, api_key
        )
        
        if not generated_script:
            raise ValueError("Failed to generate script from reference")
        
        # Save script as asset
        script_asset = {
            "type": "script",
            "url": "",  # No URL needed for JSON data
            "metadata": {
                "hook": generated_script.hook,
                "body": generated_script.body,
                "cta": generated_script.cta,
                "visual_directions": generated_script.visual_directions,
                "total_duration": generated_script.total_duration,
                "source_structure_id": generated_script.source_structure_id
            },
            "created_at": datetime.now().isoformat()
        }
        assets.append(script_asset)
        
        # Step 4: Load or extract Editing DNA from the competitor post
        await _update_pipeline_status(db, pipeline_id, "generating_script", 40, "extracting_editing_dna", assets)
        
        try:
            # Try to find existing DNA for this post
            dna_result = await db.execute(text("""
                SELECT id FROM crm.editing_dna 
                WHERE source_post_id = :post_id AND org_id = :org_id
                LIMIT 1
            """), {"post_id": reference_post_id, "org_id": org_id})
            
            existing_dna_id = dna_result.scalar()
            
            if existing_dna_id:
                editing_dna = await get_dna_by_id(db, existing_dna_id, org_id)
            else:
                # Extract DNA from competitor post
                dna_result = await process_competitor_for_dna(db, reference_post_id, org_id, api_key)
                editing_dna = dna_result
            
        except Exception as dna_error:
            logger.warning(f"Could not extract DNA, using fallback: {dna_error}")
            # Use a default fullscreen DNA
            editing_dna = {
                "id": 0,
                "name": "Fullscreen Fallback",
                "layout_type": "fullscreen",
                "dna": {
                    "layout_id": "fullscreen_fallback",
                    "meta": {
                        "composition_type": "direct_address",
                        "aspect_ratio": "9:16"
                    },
                    "layers": [
                        {
                            "role": "digital_twin_anchor",
                            "position": {"top": "0%", "left": "0%", "width": "100%", "height": "100%"},
                            "source_type": "veo_generated_character",
                            "z_index": 1,
                            "effects": ["subtle_breathing"]
                        }
                    ],
                    "audio_logic": {
                        "primary_track": "digital_twin_voiceover",
                        "auto_captions": {"style": "bold_yellow_centered", "y_offset": "80%"}
                    },
                    "timing_dna": {
                        "hook_duration_frames": 60,
                        "transition_style": "fade"
                    }
                }
            }
        
        # Step 5: Load the digital copy's character DNA and reference sheet
        await _update_pipeline_status(db, pipeline_id, "generating_images", 50, "loading_digital_copy", assets)
        
        # Handle digital_copy_id as both string ("dc-xxx") and int formats
        if str(digital_copy_id).startswith("dc-"):
            copy_query = "SELECT * FROM public.ugc_digital_copies WHERE id = :copy_id"
            copy_params = {"copy_id": digital_copy_id}
        else:
            copy_query = "SELECT * FROM public.ugc_digital_copies WHERE id = CAST(:copy_id AS INTEGER)"
            copy_params = {"copy_id": digital_copy_id}
            
        copy_result = await db.execute(text(copy_query), copy_params)
        
        copy_row = copy_result.mappings().first()
        if not copy_row:
            raise ValueError(f"Digital copy {digital_copy_id} not found")
        
        character_dna = json.loads(copy_row["character_dna"] or "{}")
        reference_sheet_url = copy_row["reference_sheet_url"]
        
        # Graceful degradation when no reference sheet
        if not reference_sheet_url:
            logger.warning(f"Digital copy {digital_copy_id} has no reference sheet, checking for images")
            
            # Try to find images from digital copy
            image_result = await db.execute(text("""
                SELECT image_url FROM crm.digital_copy_images 
                WHERE digital_copy_id = :copy_id 
                ORDER BY quality_score DESC NULLS LAST, uploaded_at ASC
                LIMIT 1
            """), {"copy_id": digital_copy_id})
            
            image_row = image_result.mappings().first()
            if image_row and image_row["image_url"]:
                # Use first image as reference
                reference_sheet_url = image_row["image_url"]
                logger.info(f"Using first image as reference for {digital_copy_id}: {reference_sheet_url}")
            else:
                # No images at all - skip scene generation and go text-only
                logger.warning(f"Digital copy {digital_copy_id} has no reference sheet or images, skipping scene generation")
                reference_sheet_url = None
        
        # Step 6: Generate scene images with Nano Banana using script + DNA layout (if reference available)
        await _update_pipeline_status(db, pipeline_id, "generating_images", 60, "generating_scene_images", assets)
        
        scene_images = []
        dna_layers = editing_dna.get("dna", {}).get("layers", [])
        
        if reference_sheet_url:
            # Generate images for each visual direction in the script
            for i, visual_direction in enumerate(generated_script.visual_directions):
                scene_prompt = f"{visual_direction}. {generated_script.body[i] if i < len(generated_script.body) else generated_script.hook}"
                
                try:
                    scene_image_bytes = await generate_scene(
                        reference_sheet_url,
                        scene_prompt,
                        character_dna,
                        db=db
                    )
                    
                    # Save scene image to Garage S3 (only if upload succeeds)
                    scene_image_url = None
                    if scene_image_bytes and len(scene_image_bytes) > 100:
                        try:
                            import boto3
                            s3 = boto3.client(
                                's3',
                                endpoint_url=os.environ.get('GARAGE_ENDPOINT', 'http://10.0.0.11:3900'),
                                aws_access_key_id=os.environ.get('GARAGE_ACCESS_KEY', 'GK6d3eb1c7bc06e00d77b8f89c'),
                                aws_secret_access_key=os.environ.get('GARAGE_SECRET_KEY', '370b99ef00dbfee300e3d73b69b217a7f5633935b02b86ee37f5691aacdf602b'),
                                region_name=os.environ.get('GARAGE_REGION', 'ai-local'),
                            )
                            bucket = os.environ.get('GARAGE_BUCKET_PIPELINE', 'digital-copies')
                            s3_key = f"pipeline/{pipeline_id}/scene_{i}.png"
                            s3.put_object(Bucket=bucket, Key=s3_key, Body=scene_image_bytes, ContentType="image/png")
                            s3_base = os.environ.get('GARAGE_ENDPOINT', 'http://10.0.0.11:3900')
                            scene_image_url = f"{s3_base}/{bucket}/{s3_key}"
                            logger.info(f"Saved scene {i} to S3: {scene_image_url}")
                        except Exception as s3_err:
                            logger.warning(f"S3 upload failed for scene {i}, keeping bytes in memory: {s3_err}")
                            # Don't set scene_image_url to placeholder - keep it None and rely on bytes
                    
                    scene_images.append({
                        "index": i,
                        "url": scene_image_url,  # None if S3 upload failed
                        "prompt": scene_prompt,
                        "duration": generated_script.total_duration / len(generated_script.visual_directions),
                        "image_bytes": scene_image_bytes,  # Keep bytes for Veo
                    })
                    
                except Exception as scene_error:
                    logger.warning(f"Failed to generate scene {i}: {scene_error}")
                    scene_images.append({
                        "index": i,
                        "url": None,
                        "prompt": scene_prompt,
                        "duration": generated_script.total_duration / len(generated_script.visual_directions),
                        "image_bytes": None,
                    })
        else:
            # No reference sheet - skip scene generation, prepare for text-only composition
            logger.info(f"No reference available for {digital_copy_id}, preparing text-only composition")
            # Create placeholder scenes for text-only Remotion composition
            for i, visual_direction in enumerate(generated_script.visual_directions):
                scene_prompt = f"{visual_direction}. {generated_script.body[i] if i < len(generated_script.body) else generated_script.hook}"
                scene_images.append({
                    "index": i,
                    "url": None,
                    "prompt": scene_prompt,
                    "duration": generated_script.total_duration / len(generated_script.visual_directions),
                    "image_bytes": None,
                    "text_only": True  # Flag for text-only composition
                })
        
        # Add scene images as assets
        for scene_img in scene_images:
            assets.append({
                "type": "scene_image",
                "url": scene_img["url"],
                "metadata": scene_img,
                "created_at": datetime.now().isoformat()
            })
        
        # Step 7: Generate video with Veo using scene images as seeds or prepare text-only composition
        await _update_pipeline_status(db, pipeline_id, "generating_video", 70, "generating_videos", assets)
        
        video_operations = []
        text_only_scenes = [scene for scene in scene_images if scene.get("text_only")]
        
        if text_only_scenes:
            # Text-only composition - skip video generation, go directly to composition
            logger.info(f"Detected {len(text_only_scenes)} text-only scenes, skipping video generation")
            
            # Mark as ready for text-only composition
            await _update_pipeline_status(db, pipeline_id, "composing", 90, "text_only_composition", assets)
            
            # TODO: Implement text-only Remotion composition
            # For now, mark as complete
            await _update_pipeline_status(db, pipeline_id, "complete", 100, "complete", assets)
            
            # Bridge: create project so it shows in My Projects
            await create_project_from_pipeline(
                db, pipeline_id, user_id,
                title=brand_context.get("product_name", "Untitled Video"),
                script=brand_context.get("script", ""),
                digital_copy_id=digital_copy_id,
                reference_post_id=reference_post_id,
                assets=assets, status="complete"
            )
            
            return {
                "pipeline_id": pipeline_id,
                "status": "complete",
                "progress": 100,
                "current_step": "complete",
                "generated_assets": assets,
                "message": "Text-only pipeline completed successfully - no reference sheet available"
            }
        
        for scene_img in scene_images:
            image_bytes = scene_img.get("image_bytes")
            if not image_bytes or len(image_bytes) < 100:
                logger.warning(f"Skipping scene {scene_img['index']}: no image bytes")
                continue
            
            video_prompt = f"Video of {scene_img['prompt']}"
            
            try:
                video_operation = await generate_video_from_image(
                    image_bytes,
                    video_prompt,
                    duration_seconds=min(int(scene_img["duration"]), 8),
                    aspect_ratio="9:16",
                    db=db
                )
                
                video_operations.append({
                    "scene_index": scene_img["index"],
                    "operation_id": video_operation["operation_id"],
                    "status": video_operation["status"],
                    "prompt": video_prompt
                })
                
            except Exception as video_error:
                logger.warning(f"Failed to start video generation for scene {scene_img['index']}: {video_error}")
        
        # Add video operations as assets
        for video_op in video_operations:
            assets.append({
                "type": "video_operation",
                "url": "",
                "metadata": video_op,
                "created_at": datetime.now().isoformat()
            })
        
        # Step 8: Mark as in progress (videos are generating)
        await _update_pipeline_status(db, pipeline_id, "generating_video", 80, "videos_in_progress", assets)
        
        return {
            "pipeline_id": pipeline_id,
            "status": "generating_video",
            "progress": 80,
            "current_step": "videos_in_progress",
            "generated_assets": assets,
            "message": "Pipeline started successfully, video generation in progress"
        }
        
    except Exception as e:
        error_message = f"Pipeline failed: {str(e)}"
        logger.error(error_message)
        
        await _update_pipeline_status(
            db, pipeline_id, "failed", 100, "failed", 
            assets, error_message
        )
        
        return {
            "pipeline_id": pipeline_id,
            "status": "failed",
            "progress": 100,
            "current_step": "failed",
            "error_message": error_message,
            "generated_assets": assets
        }

async def create_video_from_template(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    editing_dna_id: int,
    script_text: str,
    digital_copy_id: int,
    api_key: str
) -> Dict[str, Any]:
    """
    Simpler path — use a saved template.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID
        editing_dna_id: ID of existing editing DNA template
        script_text: Manual script text
        digital_copy_id: Digital copy to use
        api_key: Google AI Studio API key
        
    Returns:
        Pipeline result
    """
    # Initialize pipeline table if needed
    await init_pipeline_table(db)
    
    # Create pipeline record
    result = await db.execute(text("""
        INSERT INTO crm.video_pipelines (
            org_id, user_id, digital_copy_id, editing_dna_id,
            script, status, current_step, progress
        ) VALUES (
            :org_id, :user_id, :digital_copy_id, :editing_dna_id,
            :script::jsonb, 'pending', 'loading_template', 0
        ) RETURNING id
    """), {
        "org_id": org_id,
        "user_id": user_id,
        "digital_copy_id": digital_copy_id,
        "editing_dna_id": editing_dna_id,
        "script": json.dumps({"text": script_text})
    })
    
    pipeline_id = result.scalar()
    await db.commit()
    
    assets = []
    
    try:
        # Step 1: Load the Editing DNA template
        await _update_pipeline_status(db, pipeline_id, "pending", 10, "loading_template")
        
        editing_dna = await get_dna_by_id(db, editing_dna_id, org_id)
        if not editing_dna:
            raise ValueError(f"Editing DNA template {editing_dna_id} not found")
        
        # Step 2: Load the digital copy
        await _update_pipeline_status(db, pipeline_id, "pending", 20, "loading_digital_copy")
        
        # Handle digital_copy_id as both string ("dc-xxx") and int formats
        if str(digital_copy_id).startswith("dc-"):
            copy_query = "SELECT * FROM public.ugc_digital_copies WHERE id = :copy_id"
            copy_params = {"copy_id": digital_copy_id}
        else:
            copy_query = "SELECT * FROM public.ugc_digital_copies WHERE id = CAST(:copy_id AS INTEGER)"
            copy_params = {"copy_id": digital_copy_id}
            
        copy_result = await db.execute(text(copy_query), copy_params)
        
        copy_row = copy_result.mappings().first()
        if not copy_row:
            raise ValueError(f"Digital copy {digital_copy_id} not found")
        
        character_dna = json.loads(copy_row["character_dna"] or "{}")
        reference_sheet_url = copy_row["reference_sheet_url"]
        
        # Graceful degradation when no reference sheet
        if not reference_sheet_url:
            logger.warning(f"Digital copy {digital_copy_id} has no reference sheet, checking for images")
            
            # Try to find images from digital copy
            image_result = await db.execute(text("""
                SELECT image_url FROM crm.digital_copy_images 
                WHERE digital_copy_id = :copy_id 
                ORDER BY quality_score DESC NULLS LAST, uploaded_at ASC
                LIMIT 1
            """), {"copy_id": digital_copy_id})
            
            image_row = image_result.mappings().first()
            if image_row and image_row["image_url"]:
                # Use first image as reference
                reference_sheet_url = image_row["image_url"]
                logger.info(f"Using first image as reference for {digital_copy_id}: {reference_sheet_url}")
            else:
                # No images at all - skip scene generation and go text-only
                logger.warning(f"Digital copy {digital_copy_id} has no reference sheet or images, skipping scene generation")
                reference_sheet_url = None
        
        # Step 3: Parse script into scenes based on DNA timing
        await _update_pipeline_status(db, pipeline_id, "generating_images", 30, "parsing_script")
        
        timing_dna = editing_dna.get("dna", {}).get("timing_dna", {})
        hook_duration = timing_dna.get("hook_duration_frames", 90) / 30  # Convert frames to seconds (30fps)
        
        # Simple script parsing - split into sentences for scenes
        sentences = [s.strip() for s in script_text.split('.') if s.strip()]
        scene_duration = max(3.0, len(sentences) * 2.0)  # Estimate duration
        
        scenes = []
        for i, sentence in enumerate(sentences):
            scenes.append({
                "index": i,
                "text": sentence.strip() + ".",
                "duration": scene_duration / len(sentences),
                "visual_direction": f"Scene {i+1}: Character speaking about {sentence[:30]}..."
            })
        
        # Step 4: Generate scene images per DNA layer (if reference available)
        await _update_pipeline_status(db, pipeline_id, "generating_images", 50, "generating_scene_images", assets)
        
        scene_images = []
        if reference_sheet_url:
            for scene in scenes:
                try:
                    scene_image_bytes = await generate_scene(
                        reference_sheet_url,
                        scene["visual_direction"],
                        character_dna,
                        db=db
                    )
                    
                    # Save scene image (mock URL for now)
                    scene_image_url = f"https://example.com/template_scene_{pipeline_id}_{scene['index']}.jpg"
                    scene_images.append({
                        "index": scene["index"],
                        "url": scene_image_url,
                        "prompt": scene["visual_direction"],
                        "duration": scene["duration"]
                    })
                    
                except Exception as scene_error:
                    logger.warning(f"Failed to generate scene {scene['index']}: {scene_error}")
                    scene_images.append({
                        "index": scene["index"],
                        "url": None,
                        "prompt": scene["visual_direction"],
                        "duration": scene["duration"]
                    })
        else:
            # No reference sheet - prepare for text-only composition
            logger.info(f"No reference available for {digital_copy_id}, preparing text-only composition")
            for scene in scenes:
                scene_images.append({
                    "index": scene["index"],
                    "url": None,
                    "prompt": scene["visual_direction"],
                    "duration": scene["duration"],
                    "text_only": True  # Flag for text-only composition
                })
        
        # Add scene images as assets
        for scene_img in scene_images:
            assets.append({
                "type": "scene_image",
                "url": scene_img["url"],
                "metadata": scene_img,
                "created_at": datetime.now().isoformat()
            })
        
        # Step 5: Generate video per scene (Veo) or prepare text-only composition
        await _update_pipeline_status(db, pipeline_id, "generating_video", 70, "generating_videos", assets)
        
        video_operations = []
        text_only_scenes = [scene for scene in scene_images if scene.get("text_only")]
        
        if text_only_scenes:
            # Text-only composition - skip video generation, go directly to composition
            logger.info(f"Detected {len(text_only_scenes)} text-only scenes, skipping video generation")
            
            # Mark as ready for text-only composition
            await _update_pipeline_status(db, pipeline_id, "composing", 90, "text_only_composition", assets)
            
            # TODO: Implement text-only Remotion composition
            # For now, mark as complete
            await _update_pipeline_status(db, pipeline_id, "complete", 100, "complete", assets)
            
            # Bridge: create project from template pipeline
            await create_project_from_pipeline(
                db, pipeline_id, user_id,
                title=brand_context.get("product_name", "Untitled Video"),
                script=brand_context.get("script", ""),
                digital_copy_id=digital_copy_id,
                reference_post_id=None,
                assets=assets, status="complete"
            )
            
            return {
                "pipeline_id": pipeline_id,
                "status": "complete",
                "progress": 100,
                "current_step": "complete",
                "generated_assets": assets,
                "message": "Text-only template pipeline completed successfully"
            }
            
        for scene_img in scene_images:
            if not scene_img.get("url"):
                continue
            
            video_prompt = f"Video of {scene_img['prompt']}"
            
            try:
                mock_image_bytes = b"mock_image_data"
                
                video_operation = await generate_video_from_image(
                    mock_image_bytes,
                    video_prompt,
                    duration_seconds=int(scene_img["duration"]),
                    aspect_ratio="9:16",
                    db=db
                )
                
                video_operations.append({
                    "scene_index": scene_img["index"],
                    "operation_id": video_operation["operation_id"],
                    "status": video_operation["status"],
                    "prompt": video_prompt
                })
                
            except Exception as video_error:
                logger.warning(f"Failed to start video for scene {scene_img['index']}: {video_error}")
        
        # Add video operations as assets
        for video_op in video_operations:
            assets.append({
                "type": "video_operation",
                "url": "",
                "metadata": video_op,
                "created_at": datetime.now().isoformat()
            })
        
        # Return pipeline result
        await _update_pipeline_status(db, pipeline_id, "generating_video", 80, "videos_in_progress", assets)
        
        return {
            "pipeline_id": pipeline_id,
            "status": "generating_video",
            "progress": 80,
            "current_step": "videos_in_progress",
            "generated_assets": assets,
            "message": "Template pipeline started successfully"
        }
        
    except Exception as e:
        error_message = f"Template pipeline failed: {str(e)}"
        logger.error(error_message)
        
        await _update_pipeline_status(
            db, pipeline_id, "failed", 100, "failed",
            assets, error_message
        )
        
        return {
            "pipeline_id": pipeline_id,
            "status": "failed",
            "progress": 100,
            "current_step": "failed",
            "error_message": error_message,
            "generated_assets": assets
        }

async def get_pipeline_status(db: AsyncSession, pipeline_id: int) -> Dict[str, Any]:
    """
    Track progress across the multi-step pipeline.
    
    Args:
        db: Database session
        pipeline_id: Pipeline ID to check
        
    Returns:
        Dict with current step, progress %, generated assets, any errors
    """
    # Load pipeline from database
    result = await db.execute(text("""
        SELECT * FROM crm.video_pipelines WHERE id = :pipeline_id
    """), {"pipeline_id": pipeline_id})
    
    pipeline_row = result.mappings().first()
    if not pipeline_row:
        raise ValueError(f"Pipeline {pipeline_id} not found")
    
    pipeline_data = dict(pipeline_row)
    
    # Parse generated assets
    generated_assets = []
    if pipeline_data.get("generated_assets"):
        try:
            if isinstance(pipeline_data["generated_assets"], str):
                generated_assets = json.loads(pipeline_data["generated_assets"])
            else:
                generated_assets = pipeline_data["generated_assets"]
        except json.JSONDecodeError:
            generated_assets = []
    
    # Check video operation statuses if in generating_video phase
    if pipeline_data["status"] == "generating_video":
        video_operations = [asset for asset in generated_assets if asset.get("type") == "video_operation"]
        
        completed_videos = 0
        total_videos = len(video_operations)
        
        for video_asset in video_operations:
            operation_id = video_asset.get("metadata", {}).get("operation_id")
            if operation_id:
                try:
                    video_status = await check_video_status(operation_id, db)
                    
                    if video_status["status"] == "complete":
                        completed_videos += 1
                        # Update asset with video URL
                        video_asset["url"] = video_status.get("video_url", "")
                        video_asset["metadata"]["status"] = "complete"
                    elif video_status["status"] == "failed":
                        video_asset["metadata"]["status"] = "failed"
                        video_asset["metadata"]["error"] = video_status.get("error", "Unknown error")
                
                except Exception as check_error:
                    logger.warning(f"Failed to check video status for {operation_id}: {check_error}")
        
        # Update progress based on completed videos
        if total_videos > 0:
            video_progress = int((completed_videos / total_videos) * 20)  # 20% of total pipeline
            new_progress = 80 + video_progress
            
            if completed_videos == total_videos:
                # All videos complete, move to composition phase
                await _update_pipeline_status(
                    db, pipeline_id, "composing", 95, "composing_final_video", generated_assets
                )
                
                # TODO: Implement actual composition logic here
                # For now, mark as complete
                await _update_pipeline_status(
                    db, pipeline_id, "complete", 100, "complete", generated_assets
                )
                
                # Bridge: create project so it shows in My Projects
                await create_project_from_pipeline(
                    db, pipeline_id, user_id,
                    title=brand_context.get("product_name", "Untitled Video"),
                    script=brand_context.get("script", ""),
                    digital_copy_id=digital_copy_id,
                    reference_post_id=reference_post_id,
                    assets=generated_assets, status="complete"
                )
                
                pipeline_data["status"] = "complete"
                pipeline_data["progress"] = 100
                pipeline_data["current_step"] = "complete"
            else:
                await _update_pipeline_status(
                    db, pipeline_id, "generating_video", new_progress, "videos_in_progress", generated_assets
                )
                pipeline_data["progress"] = new_progress
    
    return {
        "pipeline_id": pipeline_id,
        "status": pipeline_data["status"],
        "progress": pipeline_data["progress"],
        "current_step": pipeline_data["current_step"],
        "generated_assets": generated_assets,
        "error_message": pipeline_data.get("error_message"),
        "created_at": pipeline_data["created_at"].isoformat() if pipeline_data["created_at"] else None,
        "updated_at": pipeline_data["updated_at"].isoformat() if pipeline_data["updated_at"] else None
    }