"""Vector Memory API — AI memory storage and semantic search for organizations."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.requests import Request

from app.api.auth import get_current_user
from app.models.crm.user import User
from app.services.tenant import get_org_id
from app.services.vector_memory import (
    VectorMemoryError,
    store_memory,
    search_memory,
    delete_memory,
    get_memory_stats,
    health_check
)

logger = logging.getLogger(__name__)
router = APIRouter()


class StoreMemoryRequest(BaseModel):
    """Request model for storing a memory."""
    text: str = Field(..., description="Memory text to store", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class StoreMemoryResponse(BaseModel):
    """Response model for storing a memory."""
    memory_id: str = Field(..., description="Unique memory ID")
    org_id: int = Field(..., description="Organization ID")
    success: bool = Field(..., description="Whether storage was successful")


class SearchMemoryRequest(BaseModel):
    """Request model for searching memories."""
    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(default=5, description="Maximum number of results", ge=1, le=50)
    score_threshold: float = Field(default=0.7, description="Minimum similarity score", ge=0.0, le=1.0)


class SearchMemoryResponse(BaseModel):
    """Response model for search results."""
    memories: List[Dict[str, Any]] = Field(..., description="Search results")
    org_id: int = Field(..., description="Organization ID")
    query: str = Field(..., description="Original query")
    count: int = Field(..., description="Number of results")


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics."""
    org_id: int = Field(..., description="Organization ID")
    collection_name: str = Field(..., description="Qdrant collection name")
    memory_count: int = Field(..., description="Number of stored memories")
    status: str = Field(..., description="Collection status")
    embedding_dim: int = Field(..., description="Embedding vector dimension")


class DeleteMemoryResponse(BaseModel):
    """Response model for memory deletion."""
    success: bool = Field(..., description="Whether deletion was successful")
    memory_id: str = Field(..., description="Memory ID")
    org_id: int = Field(..., description="Organization ID")


@router.post("/store", response_model=StoreMemoryResponse)
async def store_memory_endpoint(
    request: Request,
    data: StoreMemoryRequest,
    current_user: User = Depends(get_current_user)
) -> StoreMemoryResponse:
    """Store a memory in the organization's vector collection."""
    org_id = get_org_id(request)
    
    try:
        memory_id = await store_memory(
            org_id=org_id,
            user_id=str(current_user.id),
            text=data.text,
            metadata=data.metadata
        )
        
        logger.info("Stored memory %s for user %s in org %s", memory_id, current_user.id, org_id)
        
        return StoreMemoryResponse(
            memory_id=memory_id,
            org_id=org_id,
            success=True
        )
        
    except VectorMemoryError as e:
        logger.error("Failed to store memory for org %s: %s", org_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error storing memory for org %s: %s", org_id, e)
        raise HTTPException(status_code=500, detail="Failed to store memory")


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory_endpoint(
    request: Request,
    data: SearchMemoryRequest,
    current_user: User = Depends(get_current_user)
) -> SearchMemoryResponse:
    """Search memories in the organization's vector collection."""
    org_id = get_org_id(request)
    
    try:
        results = await search_memory(
            org_id=org_id,
            query=data.query,
            limit=data.limit,
            score_threshold=data.score_threshold
        )
        
        logger.debug("Found %d memories for query '%s' in org %s", len(results), data.query, org_id)
        
        return SearchMemoryResponse(
            memories=results,
            org_id=org_id,
            query=data.query,
            count=len(results)
        )
        
    except VectorMemoryError as e:
        logger.error("Failed to search memories for org %s: %s", org_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error searching memories for org %s: %s", org_id, e)
        raise HTTPException(status_code=500, detail="Failed to search memories")


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> MemoryStatsResponse:
    """Get memory statistics for the organization."""
    org_id = get_org_id(request)
    
    try:
        stats = await get_memory_stats(org_id)
        
        return MemoryStatsResponse(
            org_id=stats["org_id"],
            collection_name=stats["collection_name"],
            memory_count=stats["memory_count"],
            status=stats["status"],
            embedding_dim=stats.get("embedding_dim", 768)
        )
        
    except Exception as e:
        logger.error("Failed to get memory stats for org %s: %s", org_id, e)
        raise HTTPException(status_code=500, detail="Failed to get memory statistics")


@router.delete("/{memory_id}", response_model=DeleteMemoryResponse)
async def delete_memory_endpoint(
    request: Request,
    memory_id: str,
    current_user: User = Depends(get_current_user)
) -> DeleteMemoryResponse:
    """Delete a memory from the organization's collection."""
    org_id = get_org_id(request)
    
    try:
        success = await delete_memory(org_id, memory_id)
        
        if success:
            logger.info("Deleted memory %s for user %s in org %s", memory_id, current_user.id, org_id)
        else:
            logger.warning("Failed to delete memory %s for org %s", memory_id, org_id)
        
        return DeleteMemoryResponse(
            success=success,
            memory_id=memory_id,
            org_id=org_id
        )
        
    except Exception as e:
        logger.error("Unexpected error deleting memory %s for org %s: %s", memory_id, org_id, e)
        raise HTTPException(status_code=500, detail="Failed to delete memory")