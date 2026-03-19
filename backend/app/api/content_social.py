"""Content to Social API - Extract content and generate social media posts.

Endpoints:
- POST /api/content-social/extract - Extract content from URL
- POST /api/content-social/generate-posts - Generate platform-specific posts
- POST /api/content-social/schedule - Schedule posts with approval
- GET /api/content-social/drafts - List draft posts
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.services.content_extractor import ContentExtractor
from app.services.social_post_generator import SocialPostGenerator, PLATFORM_CONFIGS
from app.api.approvals import ApprovalCreate

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Schemas ──────────────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    url: HttpUrl
    include_social_summary: bool = True

class GeneratePostsRequest(BaseModel):
    content: dict  # Extracted content from extract endpoint
    platforms: List[str]
    tone: str = "professional"  # professional, casual, funny, inspiring

class SchedulePostsRequest(BaseModel):
    posts: dict  # Generated posts from generate-posts endpoint
    selected_platforms: List[str]
    scheduled_for: datetime
    require_approval: bool = True
    approval_note: Optional[str] = None

class ContentDraftResponse(BaseModel):
    id: int
    source_url: str
    extracted_content: dict
    generated_posts: dict
    selected_platforms: List[str]
    status: str
    approval_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/extract")
async def extract_content(
    request: Request,
    body: ExtractRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Extract structured content from any URL.
    
    Supports articles, blog posts, YouTube videos, GitHub repos, and more.
    """
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    logger.info(f"Extracting content from URL: {body.url}")
    
    try:
        extractor = ContentExtractor(db)
        content = await extractor.extract_from_url(str(body.url))
        
        # Add social summary if requested
        if body.include_social_summary and content.get('content_type') != 'error':
            social_summary = await extractor.summarize_for_social(content)
            content['social_summary'] = social_summary
        
        logger.info(f"Successfully extracted content: {content.get('title', 'Unknown')} "
                   f"({content.get('word_count', 0)} words)")
        
        return {
            "status": "success",
            "data": {
                "content": content,
                "extraction_info": {
                    "url": str(body.url),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "content_type": content.get('content_type'),
                    "word_count": content.get('word_count', 0),
                    "has_images": len(content.get('images', [])) > 0,
                    "has_social_summary": 'social_summary' in content
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Content extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content extraction failed: {str(e)}")


@router.post("/generate-posts")
async def generate_posts(
    request: Request,
    body: GeneratePostsRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Generate platform-optimized social media posts from extracted content."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    logger.info(f"Generating posts for platforms: {body.platforms}")
    
    # Validate platforms
    invalid_platforms = [p for p in body.platforms if p not in PLATFORM_CONFIGS]
    if invalid_platforms:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid platforms: {invalid_platforms}. "
                  f"Valid platforms: {list(PLATFORM_CONFIGS.keys())}"
        )
    
    if not body.content:
        raise HTTPException(status_code=400, detail="Content is required")
    
    try:
        generator = SocialPostGenerator(db)
        posts = await generator.generate_posts(
            content=body.content,
            platforms=body.platforms,
            tone=body.tone
        )
        
        if not posts:
            raise HTTPException(status_code=500, detail="Failed to generate any posts")
        
        # Calculate total character count and suggest post types
        total_chars = sum(post.get('character_count', 0) for post in posts.values())
        suggested_media_count = len(set().union(*[post.get('suggested_media', []) for post in posts.values()]))
        
        logger.info(f"Generated {len(posts)} posts across {len(body.platforms)} platforms")
        
        return {
            "status": "success",
            "data": {
                "posts": posts,
                "generation_info": {
                    "platforms_generated": list(posts.keys()),
                    "total_character_count": total_chars,
                    "suggested_media_count": suggested_media_count,
                    "tone_used": body.tone,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Post generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Post generation failed: {str(e)}")


@router.post("/generate-variations")
async def generate_variations(
    request: Request,
    platform: str,
    post_data: dict,
    count: int = 3,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Generate A/B test variations of a specific post."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if platform not in PLATFORM_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform: {platform}. Valid platforms: {list(PLATFORM_CONFIGS.keys())}"
        )
    
    if count < 1 or count > 10:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 10")
    
    try:
        generator = SocialPostGenerator(db)
        variations = await generator.generate_variations(post_data, count)
        
        logger.info(f"Generated {len(variations)} variations for {platform}")
        
        return {
            "status": "success",
            "data": {
                "variations": variations,
                "platform": platform,
                "variation_count": len(variations),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Variation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Variation generation failed: {str(e)}")


@router.post("/schedule")
async def schedule_posts(
    request: Request,
    body: SchedulePostsRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Schedule generated posts for publication, optionally requiring approval."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    logger.info(f"Scheduling posts for platforms: {body.selected_platforms}")
    
    # Validate that all selected platforms have generated posts
    missing_platforms = [p for p in body.selected_platforms if p not in body.posts]
    if missing_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Posts not generated for platforms: {missing_platforms}"
        )
    
    # Validate schedule time (must be in future)
    if body.scheduled_for <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Scheduled time must be in the future"
        )
    
    try:
        # Create draft entry first
        content_data = {
            "source_url": body.posts.get(body.selected_platforms[0], {}).get('source_url', ''),
            "title": body.posts.get(body.selected_platforms[0], {}).get('title', 'Social Media Post'),
            "extraction_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        draft_result = await db.execute(text("""
            INSERT INTO crm.content_drafts (
                org_id, source_url, extracted_content, generated_posts, 
                selected_platforms, status, created_at, updated_at
            ) VALUES (
                :org_id, :source_url, :extracted_content::jsonb, 
                :generated_posts::jsonb, :selected_platforms, 
                'draft', NOW(), NOW()
            ) RETURNING id
        """), {
            "org_id": org_id,
            "source_url": content_data["source_url"],
            "extracted_content": f'{{"placeholder": "content data"}}',  # Simplified for now
            "generated_posts": f'{body.posts}',
            "selected_platforms": body.selected_platforms
        })
        
        draft_id = draft_result.scalar()
        await db.commit()
        
        approval_id = None
        status = "draft"
        
        # Create approval request if required
        if body.require_approval:
            approval_payload = {
                "draft_id": draft_id,
                "platforms": body.selected_platforms,
                "scheduled_for": body.scheduled_for.isoformat(),
                "posts_preview": {platform: posts.get('text', '')[:200] + '...' 
                               for platform, posts in body.posts.items() 
                               if platform in body.selected_platforms},
                "approval_note": body.approval_note
            }
            
            # Use the approvals system
            from app.api.approvals import create_approval
            approval_request = ApprovalCreate(
                type="social_dm",  # Reusing existing approval type
                payload=approval_payload,
                requested_by_user_id=user_id,
                entity_id=draft_id
            )
            
            approval_response = await create_approval(request, approval_request, db)
            approval_id = approval_response["data"]["id"]
            status = "pending_approval"
            
            # Update draft with approval ID
            await db.execute(text("""
                UPDATE crm.content_drafts 
                SET approval_id = :approval_id, status = :status, updated_at = NOW()
                WHERE id = :draft_id AND org_id = :org_id
            """), {
                "approval_id": approval_id,
                "status": status,
                "draft_id": draft_id,
                "org_id": org_id
            })
            await db.commit()
            
            logger.info(f"Created approval request {approval_id} for draft {draft_id}")
        
        else:
            # Schedule directly without approval
            from app.services.content_scheduler import schedule_post
            
            scheduled_post_ids = []
            for platform in body.selected_platforms:
                post_data = body.posts[platform]
                
                post_id = await schedule_post(
                    db=db,
                    org_id=org_id,
                    user_id=user_id,
                    platform=platform,
                    media_path="",  # No media path for now
                    caption=post_data.get('text', ''),
                    scheduled_for=body.scheduled_for,
                    hashtags=post_data.get('hashtags', []),
                    content_type=post_data.get('post_type', 'text')
                )
                scheduled_post_ids.append(post_id)
            
            status = "scheduled"
            
            # Update draft status
            await db.execute(text("""
                UPDATE crm.content_drafts 
                SET status = :status, updated_at = NOW()
                WHERE id = :draft_id AND org_id = :org_id
            """), {
                "status": status,
                "draft_id": draft_id,
                "org_id": org_id
            })
            await db.commit()
            
            logger.info(f"Scheduled {len(scheduled_post_ids)} posts for draft {draft_id}")
        
        return {
            "status": "success",
            "data": {
                "draft_id": draft_id,
                "approval_id": approval_id,
                "status": status,
                "platforms": body.selected_platforms,
                "scheduled_for": body.scheduled_for.isoformat(),
                "requires_approval": body.require_approval,
                "message": f"Posts {'submitted for approval' if body.require_approval else 'scheduled'} successfully"
            }
        }
        
    except Exception as e:
        logger.error(f"Post scheduling failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Post scheduling failed: {str(e)}")


@router.get("/drafts")
async def list_content_drafts(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_db)
):
    """List content drafts with optional status filtering."""
    org_id = get_org_id(request)
    
    # Build query conditions
    conditions = ["org_id = :org_id"]
    params = {"org_id": org_id, "limit": limit, "offset": offset}
    
    if status:
        conditions.append("status = :status")
        params["status"] = status
    
    where_clause = " AND ".join(conditions)
    
    try:
        # Get total count
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM crm.content_drafts WHERE {where_clause}"),
            params
        )
        total = count_result.scalar()
        
        # Get drafts
        result = await db.execute(text(f"""
            SELECT 
                id, source_url, extracted_content, generated_posts,
                selected_platforms, approval_id, status,
                created_at, updated_at
            FROM crm.content_drafts 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """), params)
        
        rows = result.fetchall()
        drafts = []
        
        for row in rows:
            draft = {
                "id": row.id,
                "source_url": row.source_url,
                "extracted_content": row.extracted_content,
                "generated_posts": row.generated_posts,
                "selected_platforms": row.selected_platforms,
                "approval_id": row.approval_id,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            }
            drafts.append(draft)
        
        return {
            "status": "success",
            "data": drafts,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list drafts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list drafts: {str(e)}")


@router.get("/platforms")
async def get_platform_configs():
    """Get available platforms and their configurations."""
    return {
        "status": "success",
        "data": {
            "platforms": PLATFORM_CONFIGS,
            "platform_list": list(PLATFORM_CONFIGS.keys())
        }
    }


@router.delete("/drafts/{draft_id}")
async def delete_draft(
    request: Request,
    draft_id: int,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Delete a content draft."""
    org_id = get_org_id(request)
    
    try:
        result = await db.execute(text("""
            DELETE FROM crm.content_drafts 
            WHERE id = :draft_id AND org_id = :org_id
            RETURNING id
        """), {"draft_id": draft_id, "org_id": org_id})
        
        deleted_row = result.fetchone()
        await db.commit()
        
        if not deleted_row:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        logger.info(f"Deleted draft {draft_id}")
        
        return {
            "status": "success",
            "message": "Draft deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete draft: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete draft: {str(e)}")