"""Carousel API — Text-to-Instagram Carousel Pipeline

Provides endpoints for:
- Generating carousel slides from text
- Creating branded images for slides
- Previewing carousel content
- Publishing to Instagram via Graph API
"""

import logging
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.api.auth import get_current_user
from app.models.crm.user import User
from app.services.tenant import get_org_id
from app.services.carousel_generator import CarouselGenerator
from app.services.instagram_publisher import InstagramPublisher

router = APIRouter()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════

class GenerateCarouselRequest(BaseModel):
    """Request to generate carousel slides from text."""
    text: str = Field(..., description="Long-form text content to convert to slides")
    format: str = Field(default="portrait", description="Carousel format: portrait|square|story")

class GenerateImagesRequest(BaseModel):
    """Request to generate branded images for carousel slides."""
    slides: List[Dict[str, Any]] = Field(..., description="Slides with text content")
    brand_colors: Optional[Dict[str, str]] = Field(default=None, description="Brand color scheme")

class PublishCarouselRequest(BaseModel):
    """Request to publish carousel to Instagram."""
    carousel_id: int = Field(..., description="Carousel post ID to publish")
    caption: str = Field(..., description="Instagram post caption")
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags for the post")

class UpdateCarouselRequest(BaseModel):
    """Request to update carousel content."""
    slides: Optional[List[Dict[str, Any]]] = Field(default=None, description="Updated slides")
    caption: Optional[str] = Field(default=None, description="Updated caption") 
    hashtags: Optional[List[str]] = Field(default=None, description="Updated hashtags")

# ═══════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/generate")
async def generate_carousel(
    request: GenerateCarouselRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Generate carousel slides from text content.
    
    Returns: {"slides": [...], "total_slides": int, "format": str}
    """
    try:
        org_id = get_org_id(http_request)
        
        # Validate format
        if request.format not in ["portrait", "square", "story"]:
            raise HTTPException(status_code=400, detail="Invalid format. Must be: portrait, square, or story")
        
        # Generate slides
        generator = CarouselGenerator()
        slides = await generator.split_text_to_slides(request.text, request.format)
        
        # Create carousel record in database
        query = text("""
            INSERT INTO crm.carousel_posts (org_id, source_text, format, slides, status)
            VALUES (:org_id, :source_text, :format, :slides, 'draft')
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "org_id": org_id,
            "source_text": request.text,
            "format": request.format,
            "slides": json.dumps(slides)
        })
        
        carousel_id = result.scalar()
        await db.commit()
        
        return {
            "carousel_id": carousel_id,
            "slides": slides,
            "total_slides": len(slides),
            "format": request.format,
            "status": "draft"
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to generate carousel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate carousel: {str(e)}")

@router.post("/generate-images")
async def generate_carousel_images(
    request: GenerateImagesRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Generate branded images for carousel slides.
    
    Returns: {"image_urls": [...], "slides_updated": int}
    """
    try:
        org_id = get_org_id(http_request)
        
        # Default brand colors
        brand_colors = request.brand_colors or {
            "primary": "#007bff",
            "secondary": "#6c757d",
            "background": "#ffffff", 
            "text": "#212529"
        }
        
        # Generate images
        generator = CarouselGenerator()
        image_urls = await generator.generate_carousel_images(
            request.slides, brand_colors, org_id, db
        )
        
        # Update slides with image URLs
        updated_slides = []
        for i, slide in enumerate(request.slides):
            updated_slide = slide.copy()
            if i < len(image_urls):
                updated_slide["image_url"] = image_urls[i]
            updated_slides.append(updated_slide)
        
        return {
            "slides": updated_slides,
            "image_urls": image_urls,
            "slides_updated": len([url for url in image_urls if url is not None])
        }
        
    except Exception as e:
        logger.error(f"Failed to generate carousel images: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate images: {str(e)}")

@router.get("/preview/{carousel_id}")
async def preview_carousel(
    carousel_id: int,
    http_request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get full carousel data for frontend preview.
    
    Returns: Complete carousel data with slides, metadata, status
    """
    try:
        org_id = get_org_id(http_request)
        
        # Get carousel data
        query = text("""
            SELECT id, source_text, format, slides, caption, hashtags, status, 
                   instagram_post_id, published_url, published_at, created_at, updated_at
            FROM crm.carousel_posts
            WHERE id = :carousel_id AND org_id = :org_id
        """)
        
        result = await db.execute(query, {"carousel_id": carousel_id, "org_id": org_id})
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Carousel not found")
        
        slides_data = json.loads(row.slides) if row.slides else []
        
        return {
            "id": row.id,
            "source_text": row.source_text,
            "format": row.format,
            "slides": slides_data,
            "caption": row.caption,
            "hashtags": row.hashtags or [],
            "status": row.status,
            "instagram_post_id": row.instagram_post_id,
            "published_url": row.published_url,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "total_slides": len(slides_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get carousel preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get carousel: {str(e)}")

@router.put("/{carousel_id}")
async def update_carousel(
    carousel_id: int,
    request: UpdateCarouselRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Update carousel content.
    
    Returns: Updated carousel data
    """
    try:
        org_id = get_org_id(http_request)
        
        # Build update query dynamically
        updates = []
        params = {"carousel_id": carousel_id, "org_id": org_id}
        
        if request.slides is not None:
            updates.append("slides = :slides")
            params["slides"] = json.dumps(request.slides)
        
        if request.caption is not None:
            updates.append("caption = :caption")
            params["caption"] = request.caption
        
        if request.hashtags is not None:
            updates.append("hashtags = :hashtags")
            params["hashtags"] = request.hashtags
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        updates.append("updated_at = NOW()")
        
        query = text(f"""
            UPDATE crm.carousel_posts 
            SET {', '.join(updates)}
            WHERE id = :carousel_id AND org_id = :org_id
            RETURNING id
        """)
        
        result = await db.execute(query, params)
        updated_id = result.scalar()
        
        if not updated_id:
            raise HTTPException(status_code=404, detail="Carousel not found")
        
        await db.commit()
        
        # Return updated carousel data
        return await preview_carousel(carousel_id, user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update carousel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update carousel: {str(e)}")

@router.post("/publish")
async def publish_carousel(
    request: PublishCarouselRequest,
    req: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Publish carousel to Instagram via Graph API.
    
    Returns: {"media_id": str, "permalink": str, "published_at": str}
    """
    try:
        org_id = get_org_id(req)
        
        # Get carousel data
        query = text("""
            SELECT slides, status FROM crm.carousel_posts
            WHERE id = :carousel_id AND org_id = :org_id
        """)
        
        result = await db.execute(query, {"carousel_id": request.carousel_id, "org_id": org_id})
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Carousel not found")
        
        if row.status == "published":
            raise HTTPException(status_code=400, detail="Carousel already published")
        
        slides = json.loads(row.slides) if row.slides else []
        if not slides:
            raise HTTPException(status_code=400, detail="No slides found in carousel")
        
        # Validate slides have images
        slides_with_images = [s for s in slides if s.get("image_url")]
        if len(slides_with_images) < 2:
            raise HTTPException(status_code=400, detail="At least 2 slides with images required")
        
        # Update status to publishing
        await db.execute(
            text("UPDATE crm.carousel_posts SET status = 'publishing' WHERE id = :id"),
            {"id": request.carousel_id}
        )
        await db.commit()
        
        try:
            # Prepare caption with hashtags
            caption_text = request.caption
            if request.hashtags:
                hashtag_text = " ".join([f"#{tag.strip('#')}" for tag in request.hashtags])
                caption_text = f"{caption_text}\n\n{hashtag_text}"
            
            # Get base URL from request
            base_url = f"{req.url.scheme}://{req.headers.get('host', 'localhost')}"
            
            # Publish to Instagram
            publisher = InstagramPublisher()
            result = await publisher.post_carousel(
                org_id=org_id,
                slides=slides_with_images,
                caption=caption_text,
                db=db,
                base_url=base_url
            )
            
            published_at = datetime.now(timezone.utc)
            
            # Update carousel record with publish data
            update_query = text("""
                UPDATE crm.carousel_posts 
                SET status = 'published',
                    instagram_post_id = :media_id,
                    published_url = :permalink,
                    published_at = :published_at,
                    caption = :caption,
                    hashtags = :hashtags
                WHERE id = :carousel_id
            """)
            
            await db.execute(update_query, {
                "carousel_id": request.carousel_id,
                "media_id": result["media_id"],
                "permalink": result["permalink"],
                "published_at": published_at,
                "caption": request.caption,
                "hashtags": request.hashtags
            })
            await db.commit()
            
            return {
                "media_id": result["media_id"],
                "permalink": result["permalink"],
                "published_at": published_at.isoformat(),
                "slides_count": result["slides_count"],
                "status": "published"
            }
            
        except Exception as e:
            # Update status to failed on error
            await db.execute(
                text("UPDATE crm.carousel_posts SET status = 'failed' WHERE id = :id"),
                {"id": request.carousel_id}
            )
            await db.commit()
            raise e
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish carousel {request.carousel_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish carousel: {str(e)}")

@router.get("/")
async def list_carousels(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    http_request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """List carousels for the organization.
    
    Returns: {"carousels": [...], "total": int}
    """
    try:
        org_id = get_org_id(http_request)
        
        # Build query with optional status filter
        where_clause = "WHERE org_id = :org_id"
        params = {"org_id": org_id, "limit": limit, "offset": offset}
        
        if status:
            where_clause += " AND status = :status"
            params["status"] = status
        
        # Get total count
        count_query = text(f"SELECT COUNT(*) FROM crm.carousel_posts {where_clause}")
        count_result = await db.execute(count_query, params)
        total = count_result.scalar()
        
        # Get carousels
        query = text(f"""
            SELECT id, source_text, format, caption, hashtags, status,
                   instagram_post_id, published_url, published_at, created_at,
                   (slides::jsonb -> '$')::jsonb as slide_count
            FROM crm.carousel_posts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        carousels = []
        for row in rows:
            # Calculate slide count from JSON
            slides_data = json.loads(row.source_text) if row.source_text else "[]"
            try:
                slide_count = len(json.loads(slides_data)) if isinstance(slides_data, str) else 0
            except:
                slide_count = 0
            
            carousels.append({
                "id": row.id,
                "source_text_preview": row.source_text[:100] + "..." if len(row.source_text or "") > 100 else row.source_text,
                "format": row.format,
                "caption": row.caption,
                "hashtags": row.hashtags or [],
                "status": row.status,
                "slide_count": slide_count,
                "instagram_post_id": row.instagram_post_id,
                "published_url": row.published_url,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {
            "carousels": carousels,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to list carousels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list carousels: {str(e)}")

@router.delete("/{carousel_id}")
async def delete_carousel(
    carousel_id: int,
    http_request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Delete a carousel.
    
    Returns: {"deleted": True}
    """
    try:
        org_id = get_org_id(http_request)
        
        query = text("DELETE FROM crm.carousel_posts WHERE id = :carousel_id AND org_id = :org_id RETURNING id")
        result = await db.execute(query, {"carousel_id": carousel_id, "org_id": org_id})
        deleted_id = result.scalar()
        
        if not deleted_id:
            raise HTTPException(status_code=404, detail="Carousel not found")
        
        await db.commit()
        
        return {"deleted": True, "id": deleted_id}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete carousel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete carousel: {str(e)}")