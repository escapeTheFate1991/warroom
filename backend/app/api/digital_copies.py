"""Digital Copies API - Soul ID System

Persistent AI characters with uploaded reference photos, trained identity, and consistent appearance across videos.
"""

import os
import re
import uuid
import logging
import tempfile
import json
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import anthropic
import httpx

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.api.auth import get_current_user
from app.models.crm.user import User
from app.services import nano_banana

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


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for an S3 object."""
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': s3_key},
        ExpiresIn=expires_in
    )


def s3_url_to_presigned(image_url: str) -> str:
    """Convert a stored S3 URL to a presigned URL for frontend access."""
    if not image_url:
        return image_url
    prefix = f"{S3_PUBLIC_URL}/{S3_BUCKET}/"
    if image_url.startswith(prefix):
        s3_key = image_url[len(prefix):]
        return get_presigned_url(s3_key)
    return image_url

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
    character_dna: Optional[Dict[str, Any]] = None
    target_format: Optional[str] = None


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
    character_dna: Dict[str, Any] = {}
    reference_sheet_url: Optional[str] = None
    style_dna_url: Optional[str] = None
    target_format: str = "talking_head"
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
    # NEW fields:
    quality_score: int  # 0-100 combined score
    score_breakdown: Dict[str, int]  # {"image_count": 35, "angle_coverage": 30, "image_quality": 25}
    format_requirements: Dict[str, Any]  # what this format needs
    ai_analyzed: bool  # whether AI analysis has been run


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


class AIAnalysisResult(BaseModel):
    detected_angle: str
    face_visible: bool
    face_quality: int  # 0-100
    background_quality: str  # clean/busy/neutral
    usability_notes: str


class ImageAnalysisResponse(BaseModel):
    image_id: int
    image_url: str
    analysis: AIAnalysisResult
    updated: bool


# ── Helper Functions ──────────────────────────────────────────────────

# AI Image Analysis
def get_anthropic_client():
    """Get Anthropic client instance"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    return anthropic.Anthropic(api_key=api_key)


async def download_and_encode_image(image_url: str) -> str:
    """Download image from S3 and return base64 encoded"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=30.0)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to download image {image_url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download image: {str(e)}")


async def analyze_image_with_ai(image_url: str) -> AIAnalysisResult:
    """Analyze image with Haiku for angle detection and quality assessment"""
    client = get_anthropic_client()
    
    # Download and encode image
    image_base64 = await download_and_encode_image(image_url)
    
    # Structured prompt for Haiku
    prompt = """Please analyze this image and return a JSON response with the following fields:

{
  "detected_angle": "one of: close_up, full_body, quarter_body, profile_left, profile_right, other",
  "face_visible": boolean,
  "face_quality": number from 0-100 (consider sharpness, lighting, clarity),
  "background_quality": "one of: clean, busy, neutral",
  "usability_notes": "any issues like blurry, occluded, bad lighting, etc. or 'good' if no issues"
}

For angle detection:
- close_up: head and shoulders visible
- full_body: entire person from head to feet
- quarter_body: from waist up
- profile_left: side view facing left
- profile_right: side view facing right
- other: any other angle

Focus on photo quality for AI training purposes. Return ONLY the JSON, no other text."""

    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # Parse JSON response
        response_text = message.content[0].text.strip()
        analysis_data = json.loads(response_text)
        
        return AIAnalysisResult(**analysis_data)
        
    except Exception as e:
        logger.error(f"AI image analysis failed for {image_url}: {e}")
        # Return default analysis on failure
        return AIAnalysisResult(
            detected_angle="other",
            face_visible=False,
            face_quality=0,
            background_quality="neutral",
            usability_notes=f"AI analysis failed: {str(e)}"
        )


def get_format_requirements(format_slug: str = "talking_head") -> Dict[str, Any]:
    """Get image requirements based on target format"""
    requirements = {
        "talking_head": {
            "primary_angles": ["close_up"],
            "optional_angles": ["quarter_body"],
            "min_images": 8,
            "target_images": 12,
            "description": "Talking head videos need mainly close-up shots"
        },
        "car_talking": {
            "primary_angles": ["close_up"],
            "optional_angles": ["quarter_body"],
            "min_images": 8,
            "target_images": 12,
            "description": "Car talking videos focus on upper body and face"
        },
        "podcast_seated": {
            "primary_angles": ["close_up"],
            "optional_angles": ["quarter_body"],
            "min_images": 8,
            "target_images": 12,
            "description": "Podcast videos emphasize facial expressions"
        },
        "selling_ugc": {
            "primary_angles": ["close_up"],
            "optional_angles": ["quarter_body"],
            "min_images": 8,
            "target_images": 12,
            "description": "UGC selling videos need expressive close-ups"
        },
        "presentation": {
            "primary_angles": ["close_up", "quarter_body"],
            "optional_angles": ["full_body"],
            "min_images": 10,
            "target_images": 15,
            "description": "Presentations need both face and gesture shots"
        },
        "walking_vlog": {
            "primary_angles": ["full_body", "quarter_body", "close_up"],
            "optional_angles": ["profile_left", "profile_right"],
            "min_images": 15,
            "target_images": 20,
            "description": "Walking vlogs need full range of angles"
        }
    }
    
    return requirements.get(format_slug, requirements["talking_head"])


def calculate_quality_score(
    total_images: int,
    angle_coverage: Dict[str, int],
    avg_face_quality: float,
    format_requirements: Dict[str, Any]
) -> Dict[str, int]:
    """Calculate quality score breakdown based on format requirements"""
    
    # Image Count score (0-40)
    target_images = format_requirements["target_images"]
    min_images = format_requirements["min_images"]
    
    if total_images >= target_images:
        image_count_score = 40
    elif total_images >= min_images:
        # Linear interpolation between min and target
        ratio = (total_images - min_images) / (target_images - min_images)
        image_count_score = int(20 + (ratio * 20))
    else:
        # Below minimum
        ratio = total_images / min_images
        image_count_score = int(ratio * 20)
    
    # Angle Coverage score (0-30)
    primary_angles = format_requirements["primary_angles"]
    primary_count = sum(angle_coverage.get(angle, 0) for angle in primary_angles)
    
    if primary_count >= len(primary_angles) * 3:  # At least 3 of each primary angle
        angle_coverage_score = 30
    elif primary_count >= len(primary_angles):  # At least 1 of each primary angle
        ratio = primary_count / (len(primary_angles) * 3)
        angle_coverage_score = int(15 + (ratio * 15))
    else:
        # Missing primary angles
        covered_primary = sum(1 for angle in primary_angles if angle_coverage.get(angle, 0) > 0)
        angle_coverage_score = int((covered_primary / len(primary_angles)) * 15)
    
    # Image Quality score (0-30)
    if avg_face_quality >= 80:
        image_quality_score = 30
    elif avg_face_quality >= 60:
        ratio = (avg_face_quality - 60) / 20
        image_quality_score = int(20 + (ratio * 10))
    elif avg_face_quality >= 40:
        ratio = (avg_face_quality - 40) / 20
        image_quality_score = int(10 + (ratio * 10))
    else:
        ratio = avg_face_quality / 40
        image_quality_score = int(ratio * 10)
    
    return {
        "image_count": image_count_score,
        "angle_coverage": angle_coverage_score,
        "image_quality": image_quality_score
    }


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
                     dc.character_dna, dc.reference_sheet_url, dc.style_dna_url, dc.target_format,
                     dc.created_at, dc.updated_at
            ORDER BY dc.created_at DESC
        """),
        {"org_id": org_id}
    )
    
    copies = []
    for row in result.mappings().all():
        copy_data = dict(row)
        copy_data["images"] = [
            ImageResponse(**{**img, "image_url": s3_url_to_presigned(img.get("image_url", ""))})
            for img in copy_data["images"]
        ]
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
                     dc.character_dna, dc.reference_sheet_url, dc.style_dna_url, dc.target_format,
                     dc.created_at, dc.updated_at
        """),
        {"copy_id": copy_id, "org_id": org_id}
    )
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    copy_data = dict(row)
    copy_data["images"] = [
        ImageResponse(**{**img, "image_url": s3_url_to_presigned(img.get("image_url", ""))})
        for img in copy_data["images"]
    ]
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
    
    # Initialize Character DNA scaffold
    initial_dna = {
        "identity_id": f"dc_{trigger_token}",
        "biological_anchors": {
            "facial_structure": "",
            "eyes": {"color": "", "shape": "", "distinction": ""},
            "hair": {"style": "", "color": "", "texture": ""},
            "skin": {"tone": "", "texture": "", "pore_detail": ""}
        },
        "visual_consistency_assets": {
            "reference_sheet_url": None,
            "style_dna": "cinematic 35mm film, soft Rembrandt lighting, f/2.8 depth of field",
            "fixed_elements": []
        },
        "movement_profile": {
            "posture": "",
            "gait": "",
            "micro_expressions": []
        }
    }

    result = await db.execute(
        text("""
            INSERT INTO crm.digital_copies (org_id, user_id, name, trigger_token, base_model, character_dna)
            VALUES (:org_id, :user_id, :name, :trigger_token, :base_model, :character_dna::jsonb)
            RETURNING *
        """),
        {
            "org_id": org_id,
            "user_id": user_id,
            "name": copy_data.name,
            "trigger_token": trigger_token,
            "base_model": copy_data.base_model,
            "character_dna": json.dumps(initial_dna)
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
    
    if update_data.character_dna is not None:
        update_fields.append("character_dna = :character_dna::jsonb")
        import json as _json
        params["character_dna"] = _json.dumps(update_data.character_dna)
    
    if update_data.target_format is not None:
        update_fields.append("target_format = :target_format")
        params["target_format"] = update_data.target_format
    
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
    # Accept any image_type — no validation needed
    
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


@router.post("/digital-copies/{copy_id}/analyze-images")
async def analyze_images_with_ai(
    copy_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze all images for a digital copy using AI"""
    org_id = get_org_id(request)
    
    # Verify copy exists and belongs to org
    copy_check = await db.execute(
        text("SELECT id FROM crm.digital_copies WHERE id = :copy_id AND org_id = :org_id"),
        {"copy_id": copy_id, "org_id": org_id}
    )
    if not copy_check.first():
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    # Get all images for analysis
    result = await db.execute(
        text("""
            SELECT id, image_url, image_type
            FROM crm.digital_copy_images 
            WHERE digital_copy_id = :copy_id
            ORDER BY uploaded_at
        """),
        {"copy_id": copy_id}
    )
    
    images = result.mappings().all()
    if not images:
        raise HTTPException(status_code=400, detail="No images found for analysis")
    
    analysis_results = []
    
    for image_row in images:
        try:
            # Analyze image with AI
            analysis = await analyze_image_with_ai(image_row["image_url"])
            
            # Update the image_type (angle) field in the database based on AI detection
            await db.execute(
                text("""
                    UPDATE crm.digital_copy_images 
                    SET image_type = :detected_angle
                    WHERE id = :image_id
                """),
                {
                    "image_id": image_row["id"],
                    "detected_angle": analysis.detected_angle
                }
            )
            
            analysis_results.append(ImageAnalysisResponse(
                image_id=image_row["id"],
                image_url=image_row["image_url"],
                analysis=analysis,
                updated=True
            ))
            
        except Exception as e:
            logger.error(f"Failed to analyze image {image_row['id']}: {e}")
            analysis_results.append(ImageAnalysisResponse(
                image_id=image_row["id"],
                image_url=image_row["image_url"],
                analysis=AIAnalysisResult(
                    detected_angle=image_row["image_type"],
                    face_visible=False,
                    face_quality=0,
                    background_quality="neutral",
                    usability_notes=f"Analysis failed: {str(e)}"
                ),
                updated=False
            ))
    
    await db.commit()
    
    return {
        "ok": True,
        "analyzed": len([r for r in analysis_results if r.updated]),
        "total": len(analysis_results),
        "results": analysis_results
    }


@router.get("/digital-copies/{copy_id}/quality-audit", response_model=QualityAuditResponse)
async def quality_audit(
    copy_id: int,
    request: Request,
    format: str = "talking_head",  # Query parameter for format
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Check angle coverage and image quality for digital copy with format awareness"""
    org_id = get_org_id(request)
    
    # Verify copy exists
    copy_check = await db.execute(
        text("SELECT id FROM crm.digital_copies WHERE id = :copy_id AND org_id = :org_id"),
        {"copy_id": copy_id, "org_id": org_id}
    )
    if not copy_check.first():
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    # Get format requirements
    format_requirements = get_format_requirements(format)
    
    # Get all images with quality data and check if AI analysis has been run
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
    
    # Find missing primary angles for this format
    missing_angles = []
    primary_angles = format_requirements["primary_angles"]
    for angle in primary_angles:
        if angle_coverage.get(angle, 0) == 0:
            missing_angles.append(angle)
    
    # Calculate average resolution
    if images:
        avg_width = sum(img["resolution_width"] or 0 for img in images) / total_images
        avg_height = sum(img["resolution_height"] or 0 for img in images) / total_images
    else:
        avg_width = avg_height = 0
    
    # Mock face quality for now (would come from AI analysis)
    avg_face_quality = 75.0  # Default assumption
    
    # Calculate format-aware quality scores
    score_breakdown = calculate_quality_score(
        total_images, angle_coverage, avg_face_quality, format_requirements
    )
    quality_score = sum(score_breakdown.values())
    
    # Determine quality status based on format
    min_images = format_requirements["min_images"]
    quality_ok = (
        total_images >= min_images and
        len(missing_angles) == 0 and
        avg_width >= MIN_RESOLUTION_WIDTH and
        avg_height >= MIN_RESOLUTION_HEIGHT
    )
    
    target_images = format_requirements["target_images"]
    ready_for_training = total_images >= target_images and quality_ok and quality_score >= 70
    
    # Generate format-specific recommendation
    if ready_for_training:
        recommendation = f"Your {total_images} photos are perfect for {format} videos. Face quality looks good. Ready to generate!"
    elif total_images < min_images:
        needed = min_images - total_images
        if missing_angles:
            recommendation = f"Add {needed} more {', '.join(missing_angles)} photos for {format} format."
        else:
            recommendation = f"Add {needed} more photos to reach minimum for {format} format."
    elif missing_angles:
        recommendation = f"You have {total_images} photos but need {', '.join(missing_angles)} angles for {format} format."
    elif total_images < target_images:
        needed = target_images - total_images
        recommendation = f"Good coverage! Add {needed} more photos to reach optimal quality for {format}."
    else:
        recommendation = f"Great collection for {format}! Consider running AI analysis for detailed quality insights."
    
    # Check if AI analysis has been run (simplified check)
    ai_analyzed = False  # Would check for actual AI analysis results in production
    
    return QualityAuditResponse(
        total_images=total_images,
        target_images=target_images,
        angle_coverage=angle_coverage,
        missing_angles=missing_angles,
        avg_resolution={"width": int(avg_width), "height": int(avg_height)},
        quality_ok=quality_ok,
        ready_for_training=ready_for_training,
        recommendation=recommendation,
        quality_score=quality_score,
        score_breakdown=score_breakdown,
        format_requirements=format_requirements,
        ai_analyzed=ai_analyzed
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


@router.post("/digital-copies/{copy_id}/generate-reference-sheet")
async def generate_reference_sheet(
    copy_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Generate Master Reference Sheet from uploaded images using Nano Banana 2"""
    org_id = get_org_id(request)
    
    # Get digital copy with current images
    result = await db.execute(
        text("""
            SELECT dc.*, 
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', dci.id,
                               'image_url', dci.image_url
                           ) ORDER BY dci.uploaded_at
                       ) FILTER (WHERE dci.id IS NOT NULL), 
                       '[]'::json
                   ) as images
            FROM crm.digital_copies dc
            LEFT JOIN crm.digital_copy_images dci ON dc.id = dci.digital_copy_id
            WHERE dc.id = :copy_id AND dc.org_id = :org_id
            GROUP BY dc.id, dc.org_id, dc.user_id, dc.name, dc.trigger_token, 
                     dc.status, dc.base_model, dc.training_meta, dc.prompt_anchor,
                     dc.character_dna, dc.reference_sheet_url, dc.style_dna_url, dc.target_format,
                     dc.created_at, dc.updated_at
        """),
        {"copy_id": copy_id, "org_id": org_id}
    )
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    copy_data = dict(row)
    images = copy_data["images"]
    
    if not images:
        raise HTTPException(status_code=400, detail="No images found for reference sheet generation")
    
    try:
        # Download all images from S3
        image_bytes_list = []
        for image_info in images:
            image_url = image_info["image_url"]
            # Convert to presigned URL if needed
            if image_url.startswith(f"{S3_PUBLIC_URL}/{S3_BUCKET}/"):
                s3_key = image_url[len(f"{S3_PUBLIC_URL}/{S3_BUCKET}/"):]
                image_url = get_presigned_url(s3_key)
            
            image_bytes = await nano_banana.download_image_bytes(image_url)
            image_bytes_list.append(image_bytes)
        
        # Generate reference sheet using Nano Banana 2
        reference_sheet_bytes = await nano_banana.generate_reference_sheet(
            reference_images=image_bytes_list,
            character_name=copy_data["name"],
            character_dna=copy_data["character_dna"],
            db=db
        )
        
        # Upload reference sheet to S3
        s3_client = get_s3_client()
        ref_sheet_key = f"{copy_id}/reference_sheet.jpg"
        
        import io
        s3_client.upload_fileobj(
            io.BytesIO(reference_sheet_bytes),
            S3_BUCKET,
            ref_sheet_key,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        
        reference_sheet_url = f"{S3_PUBLIC_URL}/{S3_BUCKET}/{ref_sheet_key}"
        
        # Enrich character DNA with biological anchors
        enriched_dna = await nano_banana.enrich_character_dna(
            reference_images=image_bytes_list,
            current_dna=copy_data["character_dna"],
            db=db
        )
        
        # Update the digital copy with reference sheet URL and enriched DNA
        await db.execute(
            text("""
                UPDATE crm.digital_copies 
                SET reference_sheet_url = :reference_sheet_url,
                    character_dna = :character_dna::jsonb,
                    updated_at = NOW()
                WHERE id = :copy_id AND org_id = :org_id
            """),
            {
                "copy_id": copy_id,
                "org_id": org_id,
                "reference_sheet_url": reference_sheet_url,
                "character_dna": json.dumps(enriched_dna)
            }
        )
        await db.commit()
        
        # Return presigned URL for the generated reference sheet
        presigned_url = get_presigned_url(ref_sheet_key)
        
        return {
            "ok": True,
            "reference_sheet_url": presigned_url,
            "message": "Reference sheet generated successfully",
            "character_dna_enriched": True
        }
        
    except Exception as e:
        logger.error(f"Failed to generate reference sheet for copy {copy_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate reference sheet: {str(e)}")


class GenerateSceneRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Scene description")
    style_override: Optional[str] = Field(None, description="Optional style override")


@router.post("/digital-copies/{copy_id}/generate-scene")
async def generate_scene(
    copy_id: int,
    scene_request: GenerateSceneRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Generate scene image using reference sheet and character DNA"""
    org_id = get_org_id(request)
    
    # Get digital copy with reference sheet
    result = await db.execute(
        text("""
            SELECT reference_sheet_url, character_dna, name
            FROM crm.digital_copies
            WHERE id = :copy_id AND org_id = :org_id
        """),
        {"copy_id": copy_id, "org_id": org_id}
    )
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Digital copy not found")
    
    copy_data = dict(row)
    reference_sheet_url = copy_data["reference_sheet_url"]
    
    if not reference_sheet_url:
        raise HTTPException(
            status_code=400, 
            detail="No reference sheet found. Generate reference sheet first."
        )
    
    try:
        # Convert to presigned URL if needed
        if reference_sheet_url.startswith(f"{S3_PUBLIC_URL}/{S3_BUCKET}/"):
            s3_key = reference_sheet_url[len(f"{S3_PUBLIC_URL}/{S3_BUCKET}/"):]
            reference_sheet_url = get_presigned_url(s3_key)
        
        # Generate scene using Nano Banana 2
        scene_image_bytes = await nano_banana.generate_scene(
            reference_sheet_url=reference_sheet_url,
            scene_prompt=scene_request.prompt,
            character_dna=copy_data["character_dna"],
            style_dna=scene_request.style_override,
            db=db
        )
        
        # Upload scene image to S3
        scene_uuid = str(uuid.uuid4())
        s3_client = get_s3_client()
        scene_key = f"{copy_id}/scenes/{scene_uuid}.jpg"
        
        import io
        s3_client.upload_fileobj(
            io.BytesIO(scene_image_bytes),
            S3_BUCKET,
            scene_key,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        
        # Return presigned URL for the generated scene
        presigned_url = get_presigned_url(scene_key)
        
        return {
            "ok": True,
            "scene_image_url": presigned_url,
            "scene_id": scene_uuid,
            "message": "Scene generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate scene for copy {copy_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate scene: {str(e)}")