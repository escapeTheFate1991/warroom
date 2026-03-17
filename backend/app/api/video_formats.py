"""Video Formats API - CRUD operations for viral video format templates."""
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id

logger = logging.getLogger(__name__)

router = APIRouter()


class VideoFormatCreate(BaseModel):
    """Request model for creating a custom video format."""
    slug: str = Field(..., description="Unique slug for the format")
    name: str = Field(..., description="Display name for the format")
    description: Optional[str] = None
    why_it_works: Optional[str] = None
    hook_patterns: List[str] = Field(default_factory=list, description="Example hook structures")
    scene_structure: List[Dict[str, str]] = Field(default_factory=list, description="Scene breakdown")


class VideoFormatResponse(BaseModel):
    """Response model for video format data."""
    id: int
    org_id: int
    slug: str
    name: str
    description: Optional[str] = None
    why_it_works: Optional[str] = None
    hook_patterns: List[Any] = Field(default_factory=list)
    scene_structure: List[Dict[str, Any]] = Field(default_factory=list)
    avg_engagement_score: Optional[float] = None
    post_count: int = 0
    is_system: bool = True
    created_at: datetime


class VideoFormatWithExamples(VideoFormatResponse):
    """Video format with example posts."""
    examples: List[Dict[str, Any]] = Field(default_factory=list)


def _parse_jsonb_field(value: Any) -> List:
    """Parse JSONB field from database, handling both string and list types."""
    import json
    
    if value is None:
        return []
    
    if isinstance(value, list):
        return value
    
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    return []


async def _get_format_or_404(db: AsyncSession, format_slug: str, org_id: int) -> Dict[str, Any]:
    """Get a video format by slug, checking both system and org-specific formats."""
    result = await db.execute(
        text("""
            SELECT id, org_id, slug, name, description, why_it_works, 
                   hook_patterns, scene_structure, avg_engagement_score, 
                   post_count, is_system, created_at
            FROM crm.video_formats 
            WHERE slug = :slug 
              AND (org_id = :org_id OR (org_id = 0 AND is_system = true))
            ORDER BY org_id DESC  -- Prefer org-specific over system
            LIMIT 1
        """),
        {"slug": format_slug, "org_id": org_id}
    )
    
    format_row = result.first()
    if not format_row:
        raise HTTPException(
            status_code=404, 
            detail=f"Video format '{format_slug}' not found"
        )
    
    return {
        "id": format_row[0],
        "org_id": format_row[1],
        "slug": format_row[2],
        "name": format_row[3],
        "description": format_row[4],
        "why_it_works": format_row[5],
        "hook_patterns": _parse_jsonb_field(format_row[6]),
        "scene_structure": _parse_jsonb_field(format_row[7]),
        "avg_engagement_score": format_row[8],
        "post_count": format_row[9] or 0,
        "is_system": format_row[10],
        "created_at": format_row[11],
    }


@router.get("/video-formats", response_model=List[VideoFormatResponse])
async def list_video_formats(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """List all video formats available to this org (system + custom)."""
    org_id = get_org_id(request)
    
    try:
        result = await db.execute(
            text("""
                SELECT vf.id, vf.org_id, vf.slug, vf.name, vf.description, vf.why_it_works,
                       vf.hook_patterns, vf.scene_structure, vf.avg_engagement_score,
                       vf.post_count, vf.is_system, vf.created_at,
                       COALESCE(post_stats.count, 0) as actual_post_count
                FROM crm.video_formats vf
                LEFT JOIN (
                    SELECT detected_format, COUNT(*) as count
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE c.org_id = :org_id AND cp.detected_format IS NOT NULL
                    GROUP BY detected_format
                ) post_stats ON vf.slug = post_stats.detected_format
                WHERE vf.org_id = :org_id OR (vf.org_id = 0 AND vf.is_system = true)
                ORDER BY vf.is_system DESC, actual_post_count DESC, vf.created_at DESC
            """),
            {"org_id": org_id}
        )
        
        formats = []
        for row in result.fetchall():
            formats.append(VideoFormatResponse(
                id=row[0],
                org_id=row[1],
                slug=row[2],
                name=row[3],
                description=row[4],
                why_it_works=row[5],
                hook_patterns=_parse_jsonb_field(row[6]),
                scene_structure=_parse_jsonb_field(row[7]),
                avg_engagement_score=row[8],
                post_count=row[12],  # Use actual_post_count from the query
                is_system=row[10],
                created_at=row[11]
            ))
        
        return formats
        
    except Exception as e:
        logger.error("Failed to list video formats: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list video formats")


@router.get("/video-formats/{format_slug}", response_model=VideoFormatResponse)
async def get_video_format(
    request: Request,
    format_slug: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get a single video format with its competitor post count."""
    org_id = get_org_id(request)
    
    try:
        # Get the format
        format_data = await _get_format_or_404(db, format_slug, org_id)
        
        # Get actual post count for this format in this org
        count_result = await db.execute(
            text("""
                SELECT COUNT(*)
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE c.org_id = :org_id AND cp.detected_format = :format_slug
            """),
            {"org_id": org_id, "format_slug": format_slug}
        )
        actual_count = count_result.scalar() or 0
        
        # Update the post count with actual data
        format_data["post_count"] = actual_count
        
        return VideoFormatResponse(**format_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video format %s: %s", format_slug, e)
        raise HTTPException(status_code=500, detail="Failed to get video format")


@router.get("/video-formats/{format_slug}/examples")
async def get_format_examples(
    request: Request,
    format_slug: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get top competitor posts that match this format."""
    org_id = get_org_id(request)
    
    try:
        # Verify format exists
        await _get_format_or_404(db, format_slug, org_id)
        
        # Get top posts for this format
        result = await db.execute(
            text("""
                SELECT cp.id, cp.post_text, cp.hook, cp.likes, cp.comments, cp.shares,
                       cp.engagement_score, cp.post_url, cp.posted_at, cp.media_type,
                       c.handle, c.platform
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE c.org_id = :org_id 
                  AND cp.detected_format = :format_slug
                  AND cp.post_text IS NOT NULL
                ORDER BY cp.engagement_score DESC, cp.posted_at DESC
                LIMIT :limit
            """),
            {"org_id": org_id, "format_slug": format_slug, "limit": limit}
        )
        
        examples = []
        for row in result.fetchall():
            examples.append({
                "id": row[0],
                "post_text": row[1],
                "hook": row[2],
                "likes": row[3] or 0,
                "comments": row[4] or 0,
                "shares": row[5] or 0,
                "engagement_score": row[6] or 0,
                "post_url": row[7],
                "posted_at": row[8],
                "media_type": row[9],
                "competitor_handle": row[10],
                "platform": row[11]
            })
        
        return {
            "format_slug": format_slug,
            "examples": examples,
            "total_examples": len(examples)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get format examples for %s: %s", format_slug, e)
        raise HTTPException(status_code=500, detail="Failed to get format examples")


@router.post("/video-formats", response_model=VideoFormatResponse)
async def create_video_format(
    request: Request,
    format_data: VideoFormatCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Create a custom video format for this organization."""
    org_id = get_org_id(request)
    
    try:
        # Check if slug already exists for this org
        existing_result = await db.execute(
            text("""
                SELECT id FROM crm.video_formats 
                WHERE slug = :slug AND org_id = :org_id
            """),
            {"slug": format_data.slug, "org_id": org_id}
        )
        
        if existing_result.first():
            raise HTTPException(
                status_code=409, 
                detail=f"Format with slug '{format_data.slug}' already exists"
            )
        
        # Insert new format
        insert_result = await db.execute(
            text("""
                INSERT INTO crm.video_formats 
                (org_id, slug, name, description, why_it_works, hook_patterns, scene_structure, is_system)
                VALUES (:org_id, :slug, :name, :description, :why_it_works, 
                        CAST(:hook_patterns AS jsonb), CAST(:scene_structure AS jsonb), false)
                RETURNING id, created_at
            """),
            {
                "org_id": org_id,
                "slug": format_data.slug,
                "name": format_data.name,
                "description": format_data.description,
                "why_it_works": format_data.why_it_works,
                "hook_patterns": json.dumps(format_data.hook_patterns),
                "scene_structure": json.dumps(format_data.scene_structure)
            }
        )
        
        new_row = insert_result.first()
        if not new_row:
            raise HTTPException(status_code=500, detail="Failed to create format")
        
        new_id = new_row[0]
        created_at = new_row[1]
        
        await db.commit()
        
        return VideoFormatResponse(
            id=new_id,
            org_id=org_id,
            slug=format_data.slug,
            name=format_data.name,
            description=format_data.description,
            why_it_works=format_data.why_it_works,
            hook_patterns=format_data.hook_patterns,
            scene_structure=format_data.scene_structure,
            avg_engagement_score=None,
            post_count=0,
            is_system=False,
            created_at=created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create video format: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create video format")


@router.put("/video-formats/{format_slug}", response_model=VideoFormatResponse)
async def update_video_format(
    request: Request,
    format_slug: str,
    format_data: VideoFormatCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Update a custom video format (system formats cannot be modified)."""
    org_id = get_org_id(request)
    
    try:
        # Get existing format
        existing_format = await _get_format_or_404(db, format_slug, org_id)
        
        # Check if it's a system format
        if existing_format["is_system"] and existing_format["org_id"] == 0:
            raise HTTPException(
                status_code=403, 
                detail="Cannot modify system formats"
            )
        
        # Check if it belongs to this org
        if existing_format["org_id"] != org_id:
            raise HTTPException(
                status_code=403, 
                detail="Cannot modify formats from other organizations"
            )
        
        # Update the format
        await db.execute(
            text("""
                UPDATE crm.video_formats
                SET name = :name, description = :description, why_it_works = :why_it_works,
                    hook_patterns = CAST(:hook_patterns AS jsonb), 
                    scene_structure = CAST(:scene_structure AS jsonb)
                WHERE id = :format_id
            """),
            {
                "format_id": existing_format["id"],
                "name": format_data.name,
                "description": format_data.description,
                "why_it_works": format_data.why_it_works,
                "hook_patterns": json.dumps(format_data.hook_patterns),
                "scene_structure": json.dumps(format_data.scene_structure)
            }
        )
        
        await db.commit()
        
        # Return updated format
        updated_format = await _get_format_or_404(db, format_slug, org_id)
        return VideoFormatResponse(**updated_format)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update video format %s: %s", format_slug, e)
        raise HTTPException(status_code=500, detail="Failed to update video format")


@router.delete("/video-formats/{format_slug}")
async def delete_video_format(
    request: Request,
    format_slug: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Delete a custom video format (system formats cannot be deleted)."""
    org_id = get_org_id(request)
    
    try:
        # Get existing format
        existing_format = await _get_format_or_404(db, format_slug, org_id)
        
        # Check if it's a system format
        if existing_format["is_system"] and existing_format["org_id"] == 0:
            raise HTTPException(
                status_code=403, 
                detail="Cannot delete system formats"
            )
        
        # Check if it belongs to this org
        if existing_format["org_id"] != org_id:
            raise HTTPException(
                status_code=403, 
                detail="Cannot delete formats from other organizations"
            )
        
        # Delete the format
        await db.execute(
            text("DELETE FROM crm.video_formats WHERE id = :format_id"),
            {"format_id": existing_format["id"]}
        )
        
        await db.commit()
        
        return {"message": f"Video format '{format_slug}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete video format %s: %s", format_slug, e)
        raise HTTPException(status_code=500, detail="Failed to delete video format")


