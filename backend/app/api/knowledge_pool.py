"""Knowledge Pool API — Shared org knowledge management endpoints.

Endpoints for contributing to and searching the organization-wide knowledge pool
where completed agent task results are stored and shared.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id, is_superadmin
from app.services.knowledge_pool import KnowledgePoolService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Models ─────────────────────────────────────────────────────

class KnowledgeContribution(BaseModel):
    agent_id: int = Field(..., gt=0)
    task_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=2000)
    result_data: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class KnowledgeSearch(BaseModel):
    query: str = Field(..., min_length=1)
    task_type: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = Field(None)
    limit: int = Field(default=10, ge=1, le=50)


# ── Contribution Endpoints ───────────────────────────────────────

@router.post("/contribute", response_model=Dict[str, Any])
async def contribute_knowledge(
    contribution: KnowledgeContribution,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Add completed task result to knowledge pool."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    # Verify the agent belongs to the user
    await db.execute(text("SET search_path TO crm, public"))
    agent_result = await db.execute(
        text("""
            SELECT id FROM agent_instances
            WHERE id = :agent_id AND org_id = :org_id AND user_id = :user_id
        """),
        {"agent_id": contribution.agent_id, "org_id": org_id, "user_id": user_id}
    )
    
    if not agent_result.fetchone():
        raise HTTPException(status_code=403, detail="Agent not found or not owned by user")
    
    try:
        knowledge_id = await KnowledgePoolService.contribute_knowledge(
            db=db,
            org_id=org_id,
            agent_id=contribution.agent_id,
            user_id=user_id,
            task_type=contribution.task_type,
            title=contribution.title,
            summary=contribution.summary,
            result_data=contribution.result_data,
            tags=contribution.tags
        )
        
        return {
            "id": knowledge_id,
            "contributed": True,
            "message": "Knowledge added to org pool"
        }
        
    except Exception as e:
        logger.error("Failed to contribute knowledge: %s", e)
        raise HTTPException(status_code=500, detail="Failed to add knowledge")


# ── Search Endpoints ──────────────────────────────────────────────

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_knowledge(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    q: str = Query(..., min_length=1, description="Search query"),
    type: Optional[str] = Query(None, description="Filter by task type"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(10, ge=1, le=50)
):
    """Search knowledge pool (any user in org can read)."""
    org_id = get_org_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
    
    # Parse tags if provided
    tag_list = None
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    try:
        results = await KnowledgePoolService.search_knowledge(
            db=db,
            org_id=org_id,
            query=q,
            task_type=type,
            tags=tag_list,
            limit=limit
        )
        
        return results
        
    except Exception as e:
        logger.error("Failed to search knowledge: %s", e)
        raise HTTPException(status_code=500, detail="Search failed")


# ── Pool Statistics ───────────────────────────────────────────────

@router.get("/stats", response_model=Dict[str, Any])
async def get_knowledge_stats(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get knowledge pool statistics."""
    org_id = get_org_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
    
    try:
        stats = await KnowledgePoolService.get_pool_stats(db, org_id)
        return stats
        
    except Exception as e:
        logger.error("Failed to get knowledge stats: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/recent", response_model=List[Dict[str, Any]])
async def get_recent_knowledge(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    limit: int = Query(10, ge=1, le=50)
):
    """Get recent knowledge contributions."""
    org_id = get_org_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
    
    try:
        from sqlalchemy import text
        
        result = await db.execute(
            text("""
                SELECT id, task_type, title, summary, tags, quality_score,
                       usage_count, contributed_by_user_id, created_at
                FROM public.org_knowledge_pool
                WHERE org_id = :org_id AND status = 'active'
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"org_id": org_id, "limit": limit}
        )
        
        recent = []
        for row in result:
            recent.append({
                "id": row[0],
                "task_type": row[1],
                "title": row[2],
                "summary": row[3],
                "tags": row[4],
                "quality_score": float(row[5]) if row[5] else 0.0,
                "usage_count": row[6],
                "contributed_by_user_id": row[7],
                "created_at": row[8]
            })
        
        return recent
        
    except Exception as e:
        logger.error("Failed to get recent knowledge: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get recent entries")


# ── Usage Tracking ────────────────────────────────────────────────

@router.post("/{knowledge_id}/reference", response_model=Dict[str, bool])
async def record_knowledge_usage(
    knowledge_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Record that an agent used this knowledge."""
    org_id = get_org_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
    
    # Verify knowledge exists in this org
    await db.execute(text("SET search_path TO crm, public"))
    knowledge_result = await db.execute(
        text("""
            SELECT id FROM public.org_knowledge_pool
            WHERE id = :knowledge_id AND org_id = :org_id AND status = 'active'
        """),
        {"knowledge_id": knowledge_id, "org_id": org_id}
    )
    
    if not knowledge_result.fetchone():
        raise HTTPException(status_code=404, detail="Knowledge not found")
    
    try:
        success = await KnowledgePoolService.record_usage(db, knowledge_id)
        return {"recorded": success}
        
    except Exception as e:
        logger.error("Failed to record knowledge usage: %s", e)
        raise HTTPException(status_code=500, detail="Failed to record usage")


# ── Archive Management ────────────────────────────────────────────

@router.put("/{knowledge_id}/archive")
async def archive_knowledge(
    knowledge_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Archive knowledge (admin or contributor only)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    # Check if user is admin or the contributor
    await db.execute(text("SET search_path TO crm, public"))
    
    # Check if admin
    is_admin = is_superadmin(request)
    if not is_admin:
        # Check admin role
        role_result = await db.execute(
            text("""
                SELECT r.permission_type, r.permissions
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = :user_id AND u.org_id = :org_id
            """),
            {"user_id": user_id, "org_id": org_id}
        )
        role = role_result.fetchone()
        is_admin = role and (role[0] == 'all' or 'knowledge.archive' in (role[1] or []))
    
    # Check if contributor
    if not is_admin:
        contributor_result = await db.execute(
            text("""
                SELECT contributed_by_user_id FROM public.org_knowledge_pool
                WHERE id = :knowledge_id AND org_id = :org_id
            """),
            {"knowledge_id": knowledge_id, "org_id": org_id}
        )
        
        contributor = contributor_result.fetchone()
        if not contributor or contributor[0] != user_id:
            raise HTTPException(
                status_code=403, 
                detail="Only admin or contributor can archive knowledge"
            )
    
    try:
        success = await KnowledgePoolService.archive_knowledge(db, org_id, knowledge_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        
        return {"archived": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to archive knowledge: %s", e)
        raise HTTPException(status_code=500, detail="Failed to archive knowledge")