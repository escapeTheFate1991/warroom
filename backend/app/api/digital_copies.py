"""Digital Copies API - Soul ID System

Persistent AI characters with uploaded reference photos, trained identity, and consistent appearance across videos.
"""

import os
import re
import uuid
import logging
import tempfile
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.api.auth import get_current_user
from app.models.crm.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

# S3 Configuration
def get_s3_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('GARAGE_ENDPOINT', 'http://10.0.0.11:3900'),
        aws_access_key_id=os.environ.get('GARAGE_ACCESS_KEY', 'GK6d3eb1c7bc06e00d77b8f89c'),
        aws_secret_access_key=os.environ.get('GARAGE_SECRET_KEY', '370b99ef00dbfee300e3d73b69b217a7f5633935b02b86ee37f5691aacdf602b'),
        region_name=os.environ.get('GARAGE_REGION', 'ai-local'),
        config=Config(signature_version='s3v4')
    )

S3_BUCKET = os.environ.get('GARAGE_BUCKET_DIGITAL_COPIES', 'digital-copies')
S3_PUBLIC_URL = os.environ.get('GARAGE_ENDPOINT', 'http://10.0.0.11:3900')

# Upload directory configuration (now used only for temp files)
UPLOAD_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Image quality thresholds
MIN_RESOLUTION_WIDTH = 512
MIN_RESOLUTION_HEIGHT = 512
TARGET_IMAGE_COUNT = 20


# ── Pydantic Models ────────────────────────────────────────────────────

class DigitalCopyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_model: str = "veo_3.1"


class DigitalCopyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_model: Optional[str] = None
    training_meta: Optional[Dict[str, Any]] = None
    prompt_anchor: Optional[str] = None
    status: Optional[str] = None


class ImageResponse(BaseModel):
    id: int
    image_type: str
    image_url: str
    angle: Optional[str]
    resolution_width: Optional[int]
    resolution_height: Optional[int]
    quality_score: Optional[float]
    uploaded_at: datetime


class DigitalCopyResponse(BaseModel):
    id: int
    org_id: int
    user_id: int
    name: str
    trigger_token: str
    status: str
    base_model: str
    training_meta: Dict[str, Any]
    prompt_anchor: Optional[str]
    created_at: datetime
    updated_at: datetime
    images: List[ImageResponse] = []


class QualityAuditResponse(BaseModel):
    total_images: int
    target_images: int
    angle_coverage: Dict[str, int]
    missing_angles: List[str]
    avg_resolution: Dict[str, int]
    quality_ok: bool
    ready_for_training: bool
    recommendation: str


class BuildPromptRequest(BaseModel):
    scene_description: str = Field(..., min_length=1)
    action_template_slug: str = Field(..., min_length=1)
    format_slug: Optional[str] = None


class BuildPromptResponse(BaseModel):
    prompt: str
    negative_prompt: str
    character_token: str
    anchor_weight: float


class ActionTemplateResponse(BaseModel):
    id: int
    org_id: int
    slug: str
    name: str
    description: Optional[str]
    remotion_config: Dict[str, Any]
    ai_params: Dict[str, Any]
    prompt_fragment: Optional[str]
    is_system: bool
    created_at: datetime


# ── Helper Functions ──────────────────────────────────────────────────

def generate_trigger_token(name: str) -> str:
    """Generate trigger token from name: sks_{name_lowercase_no_spaces}"""
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    return f"sks_{clean_name}"


async def ensure_upload_directory(copy_id: int) -> str:
    """Create and return temp directory for digital copy image processing"""
    temp_dir = tempfile.mkdtemp(prefix=f"digital_copy_{copy_id}_")
    return temp_dir


def validate_image_file(file: UploadFile) -> Dict[str, Any]:
    """Validate uploaded image file"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    if file.size and file.size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum size: {MAX_IMAGE_SIZE // (1024*1024)}MB"
        )
    
    # Sanitize filename
    filename = file.filename or "image.jpg"
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    if not safe_filename:
        safe_filename = f"image_{uuid.uuid4().hex[:8]}.jpg"
    
    return {"safe_filename": safe_filename}


def analyze_image_quality(image_path: str) -> Dict[str, Any]:
    """Analyze uploaded image for quality metrics"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Basic quality score based on resolution
            resolution_score = min(1.0, (width * height) / (1920 * 1080))
            
            # Check if image meets minimum requirements
            quality_ok = (
                width >= MIN_RESOLUTION_WIDTH and 
                height >= MIN_RESOLUTION_HEIGHT
            )
            
            return {
                "width": width,
                "height": height,
                "quality_score": round(resolution_score, 2),
                "quality_ok": quality_ok
            }
    except Exception as e:
        logger.error(f"Error analyzing image quality: {e}")
        return {
            "width": None,
            "height": None,
            "quality_score": 0.0,
            "quality_ok": False
        }


# ── API Endpoints ──────────────────────────────────────────────────────

@router.get("/digital-copies", response_model=List[DigitalCopyResponse])
async def list_digital_copies(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """List all digital copies for organization"""
    org_id = get_org_id(request)
    
    result = await db.execute(
        text("""
            SELECT dc.*, 
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', dci.id,
                               'image_type', dci.image_type,
                               'image_url', dci.image_url,
                               'angle', dci.angle,
                               'resolution_width', dci.resolution_width,
                               'resolution_height', dci.resolution_height,
                               'quality_score', dci.quality_score,
                               'uploaded_at', dci.uploaded_at
                           ) ORDER BY dci.uploaded_at
                       ) FILTER (WHERE dci.id IS NOT NULL), 
                       '[]'::json
                   ) as images
            FROM crm.digital_copies dc
            LEFT JOIN crm.digital_copy_images dci ON dc.id = dci.digital_copy_id
            WHERE dc.org_id = :org_id
            GROUP BY dc.id, dc.org_id, dc.user_id, dc.name, dc.trigger_token, 
                     dc.status, dc.base_model, dc.training_meta, dc.prompt_anchor,
                     dc.created_at, dc.updated_at
            ORDER BY dc.created_at DESC
        """),
        {"org_id": org_id}
    )
    
    copies = []
    for row in result.mappings().all():
        copy_data = dict(row)
        copy_data["images"] = [ImageResponse(**img) for img in copy_data["images"]]
        copies.append(DigitalCopyResponse(**copy_data))
    
    return copies


@router.get("/digital-copies/{copy_id}", response_model=DigitalCopyResponse)
async def get_digital_copy(
    copy_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Get single digital copy with images"""
    org_id = get_org_id(request)
    
    result = await db.execute(
        text("""
            SELECT dc.*, 
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', dci.id,
                               'image_type', dci.image_type,
                               'image_url', dci.image_url,
                               'angle', dci.angle,
                               'resolution_width', dci.resolution_width,
                               'resolution_height', dci.resolution_height,
                               'quality_score', dci.quality_score,
                               'uploaded_at', dci.uploaded_at
                           ) ORDER BY dci.uploaded_at
                       ) FILTER (WHERE dci.id IS NOT NULL), 
                       '[]'::json
                   ) as images
            FROM crm.digital_copies dc
            LEFT JOIN crm.digital_copy_images dci ON dc.id = dci.digital_copy_id
            WHERE dc.id = :copy_id AND dc.org_id = :org_id
            GROUP BY dc.id, dc.org_id, dc.user_id, dc.name, dc.trigger_token, 
                     dc.status, dc.base_model, dc.training_meta, dc.prompt_anchor,
                     dc.created_at, dc.updated_at
        """),
        {"copy_id": copy_id, "org_id": org_id}
    )
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    copy_data = dict(row)
    copy_data["images"] = [ImageResponse(**img) for img in copy_data["images"]]
    return DigitalCopyResponse(**copy_data)


@router.post("/digital-copies", response_model=DigitalCopyResponse)
async def create_digital_copy(
    copy_data: DigitalCopyCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Create new digital copy"""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    trigger_token = generate_trigger_token(copy_data.name)
    
    # Check for duplicate trigger token
    existing = await db.execute(
        text("SELECT id FROM crm.digital_copies WHERE trigger_token = :token"),
        {"token": trigger_token}
    )
    if existing.first():
        raise HTTPException(
            status_code=400,
            detail=f"Trigger token '{trigger_token}' already exists. Please use a different name."
        )
    
    result = await db.execute(
        text("""
            INSERT INTO crm.digital_copies (org_id, user_id, name, trigger_token, base_model)
            VALUES (:org_id, :user_id, :name, :trigger_token, :base_model)
            RETURNING *
        """),
        {
            "org_id": org_id,
            "user_id": user_id,
            "name": copy_data.name,
            "trigger_token": trigger_token,
            "base_model": copy_data.base_model
        }
    )
    await db.commit()
    
    row = result.mappings().first()
    copy_data = dict(row)
    copy_data["images"] = []
    return DigitalCopyResponse(**copy_data)


@router.put("/digital-copies/{copy_id}", response_model=DigitalCopyResponse)
async def update_digital_copy(
    copy_id: int,
    update_data: DigitalCopyUpdate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Update digital copy"""
    org_id = get_org_id(request)
    
    # Build dynamic update query
    update_fields = []
    params = {"copy_id": copy_id, "org_id": org_id}
    
    if update_data.name is not None:
        # Generate new trigger token if name changes
        new_token = generate_trigger_token(update_data.name)
        update_fields.extend(["name = :name", "trigger_token = :trigger_token"])
        params.update({"name": update_data.name, "trigger_token": new_token})
    
    if update_data.base_model is not None:
        update_fields.append("base_model = :base_model")
        params["base_model"] = update_data.base_model
    
    if update_data.training_meta is not None:
        update_fields.append("training_meta = :training_meta::jsonb")
        params["training_meta"] = update_data.training_meta
    
    if update_data.prompt_anchor is not None:
        update_fields.append("prompt_anchor = :prompt_anchor")
        params["prompt_anchor"] = update_data.prompt_anchor
    
    if update_data.status is not None:
        update_fields.append("status = :status")
        params["status"] = update_data.status
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields.append("updated_at = NOW()")
    
    result = await db.execute(
        text(f"""
            UPDATE crm.digital_copies 
            SET {', '.join(update_fields)}
            WHERE id = :copy_id AND org_id = :org_id
            RETURNING *
        """),
        params
    )
    await db.commit()
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    # Get updated copy with images
    return await get_digital_copy(copy_id, request, db, current_user)


@router.delete("/digital-copies/{copy_id}")
async def delete_digital_copy(
    copy_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Delete digital copy and cascade images"""
    org_id = get_org_id(request)
    
    result = await db.execute(
        text("""
            DELETE FROM crm.digital_copies 
            WHERE id = :copy_id AND org_id = :org_id
            RETURNING id
        """),
        {"copy_id": copy_id, "org_id": org_id}
    )
    await db.commit()
    
    if not result.first():
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    # Clean up S3 objects for this copy
    try:
        s3_client = get_s3_client()
        # List all objects with the copy_id prefix
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{copy_id}/"
        )
        
        if 'Contents' in response:
            # Delete all objects for this copy
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            if objects_to_delete:
                s3_client.delete_objects(
                    Bucket=S3_BUCKET,
                    Delete={'Objects': objects_to_delete}
                )
                logger.info(f"Deleted {len(objects_to_delete)} S3 objects for copy {copy_id}")
    except Exception as e:
        logger.warning(f"Failed to clean up S3 objects for copy {copy_id}: {e}")
    
    return {"ok": True, "message": "Digital copy deleted successfully"}


@router.post("/digital-copies/{copy_id}/images")
async def upload_images(
    copy_id: int,
    request: Request,
    image_type: str = Form(...),
    file: UploadFile = File(None),
    files: List[UploadFile] = File(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Upload image(s) to digital copy"""
    org_id = get_org_id(request)
    
    # Verify copy exists and belongs to org
    copy_check = await db.execute(
        text("SELECT id FROM crm.digital_copies WHERE id = :copy_id AND org_id = :org_id"),
        {"copy_id": copy_id, "org_id": org_id}
    )
    if not copy_check.first():
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    # Validate image_type
    valid_types = ["close_up", "full_body", "quarter_body", "profile_left", "profile_right", "other"]
    if image_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Accept both single 'file' and multiple 'files'
    all_files = []
    if file:
        all_files.append(file)
    if files:
        all_files.extend(files)
    if not all_files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    temp_dir = await ensure_upload_directory(copy_id)
    uploaded_images = []
    s3_client = get_s3_client()
    
    for file in all_files:
        try:
            # Validate file
            validation = validate_image_file(file)
            safe_filename = validation["safe_filename"]
            
            # Save file to temp location for analysis
            temp_file_path = os.path.join(temp_dir, safe_filename)
            with open(temp_file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Analyze image quality from temp file
            quality_data = analyze_image_quality(temp_file_path)
            
            # Upload to S3
            s3_key = f"{copy_id}/{safe_filename}"
            try:
                with open(temp_file_path, "rb") as f:
                    s3_client.upload_fileobj(
                        f,
                        S3_BUCKET,
                        s3_key,
                        ExtraArgs={'ContentType': file.content_type or 'image/jpeg'}
                    )
                logger.info(f"Uploaded {s3_key} to S3 bucket {S3_BUCKET}")
            except Exception as s3_error:
                logger.error(f"S3 upload failed for {s3_key}: {s3_error}")
                raise HTTPException(status_code=500, detail=f"Failed to upload {safe_filename} to storage")
            
            # Clean up temp file
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
            
            # Generate S3 URL for database storage
            image_url = f"{S3_PUBLIC_URL}/{S3_BUCKET}/{s3_key}"
            
            # Store in database
            result = await db.execute(
                text("""
                    INSERT INTO crm.digital_copy_images 
                    (digital_copy_id, image_type, image_url, resolution_width, 
                     resolution_height, quality_score)
                    VALUES (:copy_id, :image_type, :image_url, :width, :height, :quality_score)
                    RETURNING *
                """),
                {
                    "copy_id": copy_id,
                    "image_type": image_type,
                    "image_url": image_url,
                    "width": quality_data["width"],
                    "height": quality_data["height"],
                    "quality_score": quality_data["quality_score"]
                }
            )
            
            row = result.mappings().first()
            uploaded_images.append(ImageResponse(**dict(row)))
            
        except Exception as e:
            logger.error(f"Error uploading image {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error uploading {file.filename}: {str(e)}")
    
    # Clean up temp directory
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
    
    await db.commit()
    return {"ok": True, "uploaded": len(uploaded_images), "images": uploaded_images}


@router.delete("/digital-copies/{copy_id}/images/{image_id}")
async def delete_image(
    copy_id: int,
    image_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Remove image from digital copy"""
    org_id = get_org_id(request)
    
    # Get image info and verify ownership
    result = await db.execute(
        text("""
            SELECT dci.image_url 
            FROM crm.digital_copy_images dci
            JOIN crm.digital_copies dc ON dci.digital_copy_id = dc.id
            WHERE dci.id = :image_id AND dc.id = :copy_id AND dc.org_id = :org_id
        """),
        {"image_id": image_id, "copy_id": copy_id, "org_id": org_id}
    )
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_path = row["image_url"]
    
    # Delete from database
    await db.execute(
        text("DELETE FROM crm.digital_copy_images WHERE id = :image_id"),
        {"image_id": image_id}
    )
    await db.commit()
    
    # Delete from S3
    try:
        # Extract S3 key from URL (format: http://10.0.0.11:3900/digital-copies/copy_id/filename)
        if image_path.startswith(S3_PUBLIC_URL):
            s3_key = image_path.replace(f"{S3_PUBLIC_URL}/{S3_BUCKET}/", "")
            s3_client = get_s3_client()
            s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
            logger.info(f"Deleted S3 object: {s3_key}")
        else:
            # Fallback for old local file paths
            if os.path.exists(image_path):
                os.remove(image_path)
    except Exception as e:
        logger.warning(f"Failed to delete image {image_path}: {e}")
    
    return {"ok": True, "message": "Image deleted successfully"}


@router.get("/digital-copies/{copy_id}/quality-audit", response_model=QualityAuditResponse)
async def quality_audit(
    copy_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Check angle coverage and image quality for digital copy"""
    org_id = get_org_id(request)
    
    # Verify copy exists
    copy_check = await db.execute(
        text("SELECT id FROM crm.digital_copies WHERE id = :copy_id AND org_id = :org_id"),
        {"copy_id": copy_id, "org_id": org_id}
    )
    if not copy_check.first():
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    # Get all images with quality data
    result = await db.execute(
        text("""
            SELECT image_type, resolution_width, resolution_height, quality_score
            FROM crm.digital_copy_images 
            WHERE digital_copy_id = :copy_id
            ORDER BY uploaded_at
        """),
        {"copy_id": copy_id}
    )
    
    images = result.mappings().all()
    total_images = len(images)
    
    # Analyze angle coverage
    angle_coverage = {}
    for image_type in ["close_up", "full_body", "quarter_body", "profile_left", "profile_right", "other"]:
        angle_coverage[image_type] = sum(1 for img in images if img["image_type"] == image_type)
    
    # Find missing critical angles
    missing_angles = []
    critical_angles = ["close_up", "full_body", "profile_left", "profile_right"]
    for angle in critical_angles:
        if angle_coverage.get(angle, 0) == 0:
            missing_angles.append(angle)
    
    # Calculate average resolution
    if images:
        avg_width = sum(img["resolution_width"] or 0 for img in images) / total_images
        avg_height = sum(img["resolution_height"] or 0 for img in images) / total_images
    else:
        avg_width = avg_height = 0
    
    # Determine quality status
    quality_ok = (
        total_images >= 10 and
        len(missing_angles) == 0 and
        avg_width >= MIN_RESOLUTION_WIDTH and
        avg_height >= MIN_RESOLUTION_HEIGHT
    )
    
    ready_for_training = total_images >= TARGET_IMAGE_COUNT and quality_ok
    
    # Generate recommendation
    if ready_for_training:
        recommendation = "Ready for training! You have sufficient high-quality images across all angles."
    elif total_images < TARGET_IMAGE_COUNT:
        needed = TARGET_IMAGE_COUNT - total_images
        if missing_angles:
            recommendation = f"Add {needed} more photos, especially {', '.join(missing_angles)} shots."
        else:
            recommendation = f"Add {needed} more photos to reach the target of {TARGET_IMAGE_COUNT}."
    else:
        recommendation = f"Add photos for missing angles: {', '.join(missing_angles)}."
    
    return QualityAuditResponse(
        total_images=total_images,
        target_images=TARGET_IMAGE_COUNT,
        angle_coverage=angle_coverage,
        missing_angles=missing_angles,
        avg_resolution={"width": int(avg_width), "height": int(avg_height)},
        quality_ok=quality_ok,
        ready_for_training=ready_for_training,
        recommendation=recommendation
    )


@router.get("/action-templates", response_model=List[ActionTemplateResponse])
async def list_action_templates(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """List action templates for organization"""
    org_id = get_org_id(request)
    
    result = await db.execute(
        text("""
            SELECT * FROM crm.action_templates
            WHERE org_id = :org_id OR is_system = true
            ORDER BY is_system DESC, name ASC
        """),
        {"org_id": org_id}
    )
    
    return [ActionTemplateResponse(**dict(row)) for row in result.mappings().all()]


@router.get("/action-templates/{slug}", response_model=ActionTemplateResponse)
async def get_action_template(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Get single action template"""
    org_id = get_org_id(request)
    
    result = await db.execute(
        text("""
            SELECT * FROM crm.action_templates
            WHERE slug = :slug AND (org_id = :org_id OR is_system = true)
            ORDER BY is_system DESC
            LIMIT 1
        """),
        {"slug": slug, "org_id": org_id}
    )
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Action template not found")
    
    return ActionTemplateResponse(**dict(row))


@router.post("/digital-copies/{copy_id}/build-prompt", response_model=BuildPromptResponse)
async def build_prompt(
    copy_id: int,
    prompt_request: BuildPromptRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Build AI prompt for Veo/Nano Banana scene generation"""
    org_id = get_org_id(request)
    
    # Get digital copy
    copy_result = await db.execute(
        text("""
            SELECT trigger_token, prompt_anchor 
            FROM crm.digital_copies 
            WHERE id = :copy_id AND org_id = :org_id
        """),
        {"copy_id": copy_id, "org_id": org_id}
    )
    
    copy_row = copy_result.mappings().first()
    if not copy_row:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    # Get action template
    template_result = await db.execute(
        text("""
            SELECT prompt_fragment, ai_params 
            FROM crm.action_templates
            WHERE slug = :slug AND (org_id = :org_id OR is_system = true)
            ORDER BY is_system DESC
            LIMIT 1
        """),
        {"slug": prompt_request.action_template_slug, "org_id": org_id}
    )
    
    template_row = template_result.mappings().first()
    if not template_row:
        raise HTTPException(status_code=404, detail="Action template not found")
    
    # Build the prompt
    trigger_token = copy_row["trigger_token"]
    character_token = trigger_token
    anchor_weight = 1.5
    
    # Construct main prompt
    prompt_parts = [
        f"({character_token}:{anchor_weight}) man",
        "highly detailed facial features",
        "consistent character identity",
        "direct eye contact",
        "speaking to camera"
    ]
    
    # Add action template fragment
    if template_row["prompt_fragment"]:
        prompt_parts.append(template_row["prompt_fragment"])
    
    # Add scene description
    if prompt_request.scene_description:
        prompt_parts.append(prompt_request.scene_description)
    
    # Add style suffix
    prompt_parts.extend([
        "cinematic depth of field",
        "8k",
        "photorealistic UGC style"
    ])
    
    prompt = ", ".join(prompt_parts)
    
    # Negative prompt for consistency
    negative_prompt = "distorted features, morphing, blurry face, inconsistent identity"
    
    return BuildPromptResponse(
        prompt=prompt,
        negative_prompt=negative_prompt,
        character_token=character_token,
        anchor_weight=anchor_weight
    )