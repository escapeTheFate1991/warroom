"""
Audience Intelligence API - New data model for extracting actionable insights.

Provides endpoints for:
- Per-video audience intelligence 
- Aggregated competitor audience intelligence
- On-demand extraction from stored comments
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id
from app.services.audience_intelligence import (
    extract_audience_intelligence_for_post,
    extract_audience_intelligence_for_competitor,
    analyze_audience_intelligence
)

logger = logging.getLogger(__name__)
router = APIRouter()


class AudienceIntelligenceResponse(BaseModel):
    """Response model for audience intelligence."""
    objections: List[Dict[str, Any]]
    desires: List[Dict[str, Any]]  
    questions: List[Dict[str, Any]]
    emotional_triggers: List[Dict[str, Any]]
    competitor_gaps: List[Dict[str, Any]]
    total_comments_analyzed: int
    analysis_timestamp: str


class CompetitorAudienceIntelligenceResponse(BaseModel):
    """Response model for competitor-wide audience intelligence."""
    objections: List[Dict[str, Any]]
    desires: List[Dict[str, Any]]
    questions: List[Dict[str, Any]]
    emotional_triggers: List[Dict[str, Any]]
    competitor_gaps: List[Dict[str, Any]]
    total_comments_analyzed: int
    total_posts_analyzed: int
    posts_analyzed: List[Dict[str, Any]]
    analysis_timestamp: str


class ExtractionRequest(BaseModel):
    """Request model for running extraction on specific posts."""
    post_ids: List[int] = Field(..., description="List of post IDs to extract intelligence from")
    force_refresh: bool = Field(default=False, description="Force re-extraction even if analysis exists")


class ExtractionResponse(BaseModel):
    """Response model for extraction operation."""
    success: bool
    posts_processed: int
    errors: List[str]
    results: Dict[int, Dict[str, Any]]  # post_id -> intelligence


@router.get(
    "/api/content-intel/audience-intelligence/{post_id}",
    response_model=AudienceIntelligenceResponse
)
async def get_audience_intelligence_for_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get audience intelligence for a specific video/post."""
    org_id = get_org_id(request)
    
    try:
        # Check if post exists
        post_query = text("""
            SELECT id, content_analysis, comments_data 
            FROM crm.competitor_posts 
            WHERE id = :post_id AND org_id = :org_id
        """)
        
        result = await db.execute(post_query, {"post_id": post_id, "org_id": org_id})
        post = result.first()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Check if we already have audience intelligence
        existing_intelligence = None
        if post.content_analysis and isinstance(post.content_analysis, dict):
            existing_intelligence = post.content_analysis.get("audience_intelligence")
        
        if existing_intelligence:
            logger.info(f"Returning cached audience intelligence for post {post_id}")
            return AudienceIntelligenceResponse(**existing_intelligence)
        
        # Extract new intelligence
        if not post.comments_data:
            raise HTTPException(
                status_code=400, 
                detail="Post has no comments data. Run comment scraping first."
            )
        
        logger.info(f"Extracting new audience intelligence for post {post_id}")
        intelligence = await extract_audience_intelligence_for_post(db, post_id, org_id)
        
        if not intelligence:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract audience intelligence"
            )
        
        return AudienceIntelligenceResponse(**intelligence)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get audience intelligence for post %s: %s", post_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audience intelligence: {str(e)}"
        )


@router.get(
    "/api/content-intel/audience-intelligence/competitor/{competitor_id}",
    response_model=CompetitorAudienceIntelligenceResponse
)
async def get_audience_intelligence_for_competitor(
    competitor_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get aggregated audience intelligence across a competitor's videos."""
    org_id = get_org_id(request)
    
    try:
        # Check if competitor exists
        competitor_query = text("""
            SELECT id, handle, platform 
            FROM crm.competitors 
            WHERE id = :competitor_id AND org_id = :org_id
        """)
        
        result = await db.execute(competitor_query, {"competitor_id": competitor_id, "org_id": org_id})
        competitor = result.first()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        logger.info(f"Extracting audience intelligence for competitor {competitor.handle}")
        
        # Extract aggregated intelligence
        intelligence = await extract_audience_intelligence_for_competitor(
            db, competitor_id, org_id
        )
        
        if "error" in intelligence:
            raise HTTPException(status_code=400, detail=intelligence["error"])
        
        return CompetitorAudienceIntelligenceResponse(**intelligence)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get audience intelligence for competitor %s: %s", competitor_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get competitor audience intelligence: {str(e)}"
        )


@router.post(
    "/api/content-intel/audience-intelligence/extract",
    response_model=ExtractionResponse
)
async def extract_audience_intelligence(
    extraction_request: ExtractionRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Run audience intelligence extraction on specified posts."""
    org_id = get_org_id(request)
    
    if not extraction_request.post_ids:
        raise HTTPException(status_code=400, detail="No post IDs provided")
    
    if len(extraction_request.post_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 posts per extraction request")
    
    try:
        results = {}
        errors = []
        posts_processed = 0
        
        for post_id in extraction_request.post_ids:
            try:
                # Get post data
                post_query = text("""
                    SELECT id, content_analysis, comments_data, post_url
                    FROM crm.competitor_posts 
                    WHERE id = :post_id AND org_id = :org_id
                """)
                
                result = await db.execute(post_query, {"post_id": post_id, "org_id": org_id})
                post = result.first()
                
                if not post:
                    errors.append(f"Post {post_id} not found")
                    continue
                
                if not post.comments_data:
                    errors.append(f"Post {post_id} has no comments data")
                    continue
                
                # Check if extraction needed
                if not extraction_request.force_refresh and post.content_analysis:
                    existing = post.content_analysis.get("audience_intelligence")
                    if existing:
                        results[post_id] = existing
                        posts_processed += 1
                        continue
                
                # Extract intelligence
                logger.info(f"Extracting audience intelligence for post {post_id}")
                intelligence = await extract_audience_intelligence_for_post(db, post_id, org_id)
                
                if intelligence:
                    results[post_id] = intelligence
                    posts_processed += 1
                    logger.info(f"Successfully extracted intelligence for post {post_id}")
                else:
                    errors.append(f"Failed to extract intelligence for post {post_id}")
                    
            except Exception as e:
                logger.error("Error processing post %s: %s", post_id, e)
                errors.append(f"Post {post_id}: {str(e)}")
        
        return ExtractionResponse(
            success=len(errors) == 0,
            posts_processed=posts_processed,
            errors=errors,
            results=results
        )
        
    except Exception as e:
        logger.error("Failed extraction request: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process extraction request: {str(e)}"
        )


@router.get("/api/content-intel/audience-intelligence/test/{post_id}")
async def test_audience_intelligence(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Test endpoint for debugging audience intelligence extraction."""
    org_id = get_org_id(request)
    
    try:
        # Get post data
        post_query = text("""
            SELECT id, comments_data, post_url, competitor_id
            FROM crm.competitor_posts 
            WHERE id = :post_id AND org_id = :org_id
        """)
        
        result = await db.execute(post_query, {"post_id": post_id, "org_id": org_id})
        post = result.first()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if not post.comments_data:
            raise HTTPException(status_code=400, detail="Post has no comments data")
        
        # Run analysis directly (without storing)
        intelligence = await analyze_audience_intelligence(post.comments_data)
        
        # Add debug info
        debug_info = {
            "post_id": post.id,
            "post_url": post.post_url,
            "competitor_id": post.competitor_id,
            "total_comments": len(post.comments_data),
            "sample_comments": post.comments_data[:3],  # First 3 comments for inspection
            "extraction_results": intelligence
        }
        
        return debug_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Test extraction failed for post %s: %s", post_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Test extraction failed: {str(e)}"
        )