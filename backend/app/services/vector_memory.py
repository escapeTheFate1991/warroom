"""Vector memory service for War Room organizations.

Provides per-org AI memory storage with semantic search capabilities.
Each organization gets its own collection for tenant isolation.

Infrastructure:
- War Room Qdrant: http://localhost:6334
- Embedding model: nomic-embed-text via http://10.0.0.11:11435 (FastEmbed on Brain 2)
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

QDRANT_URL = "http://localhost:6334"  # War Room's dedicated Qdrant instance
FASTEMBED_URL = "http://10.0.0.11:11435"  # FastEmbed service on Brain 2
EMBEDDING_DIM = 768  # nomic-embed-text dimension
EMBEDDING_TIMEOUT = 8.0  # 8-second timeout for embedding calls
MAX_RETRIES = 2  # Retry logic for embeddings


class VectorMemoryError(Exception):
    """Base exception for vector memory operations."""
    pass


class EmbeddingError(VectorMemoryError):
    """Embedding service errors."""
    pass


class QdrantError(VectorMemoryError):
    """Qdrant service errors."""
    pass


async def _get_embedding(text_input: str, retry_count: int = 0) -> List[float]:
    """Get embedding vector from FastEmbed service with retry logic."""
    if not text_input or not text_input.strip():
        raise EmbeddingError("Empty text input")
    
    try:
        async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
            response = await client.post(
                f"{FASTEMBED_URL}/api/embed",
                json={"text": text_input.strip()}
            )
            response.raise_for_status()
            
            result = response.json()
            if "embedding" not in result:
                raise EmbeddingError("Invalid embedding response format")
            
            embedding = result["embedding"]
            if not embedding or len(embedding) != EMBEDDING_DIM:
                raise EmbeddingError(f"Invalid embedding dimensions: {len(embedding)}")
            
            return embedding
            
    except httpx.TimeoutException as e:
        logger.warning("Embedding timeout (attempt %d/%d): %s", retry_count + 1, MAX_RETRIES + 1, e)
        if retry_count < MAX_RETRIES:
            # Exponential backoff: 1s, 2s delays
            delay = 2 ** retry_count
            await asyncio.sleep(delay)
            return await _get_embedding(text_input, retry_count + 1)
        raise EmbeddingError("Embedding timeout after retries")
        
    except httpx.HTTPStatusError as e:
        logger.error("Embedding HTTP error (attempt %d/%d): %s", retry_count + 1, MAX_RETRIES + 1, e)
        if retry_count < MAX_RETRIES and e.response.status_code >= 500:
            # Only retry on server errors
            delay = 2 ** retry_count
            await asyncio.sleep(delay)
            return await _get_embedding(text_input, retry_count + 1)
        raise EmbeddingError(f"Embedding service error: {e}")
        
    except Exception as e:
        logger.error("Embedding error (attempt %d/%d): %s", retry_count + 1, MAX_RETRIES + 1, e)
        if retry_count < MAX_RETRIES:
            delay = 2 ** retry_count
            await asyncio.sleep(delay)
            return await _get_embedding(text_input, retry_count + 1)
        raise EmbeddingError(f"Failed to get embedding: {e}")


async def _qdrant_request(method: str, path: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make a request to Qdrant with error handling."""
    try:
        async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=f"{QDRANT_URL}{path}",
                json=json_data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error("Qdrant HTTP error: %s - %s", e.response.status_code, e.response.text)
        raise QdrantError(f"Qdrant error: {e}")
    except Exception as e:
        logger.error("Qdrant request failed: %s", e)
        raise QdrantError(f"Qdrant request failed: {e}")


def _get_collection_name(org_id: str) -> str:
    """Get collection name for an organization."""
    return f"org_{org_id}_memory"


async def ensure_org_collection(org_id: str) -> bool:
    """Create organization's memory collection if it doesn't exist."""
    collection_name = _get_collection_name(org_id)
    
    # Check if collection exists
    try:
        await _qdrant_request("GET", f"/collections/{collection_name}")
        logger.debug("Collection %s already exists", collection_name)
        return True
    except QdrantError:
        # Collection doesn't exist, create it
        pass
    
    try:
        # Create collection with 768 dimensions and Cosine distance
        collection_config = {
            "vectors": {
                "size": EMBEDDING_DIM,
                "distance": "Cosine"
            }
        }
        
        await _qdrant_request("PUT", f"/collections/{collection_name}", collection_config)
        logger.info("Created memory collection for org %s", org_id)
        return True
        
    except QdrantError as e:
        logger.error("Failed to create collection for org %s: %s", org_id, e)
        return False


async def store_memory(
    org_id: str,
    user_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Store a memory in the organization's collection."""
    if not text or not text.strip():
        raise VectorMemoryError("Memory text cannot be empty")
    
    # Ensure collection exists
    if not await ensure_org_collection(org_id):
        raise VectorMemoryError(f"Failed to ensure collection for org {org_id}")
    
    # Get embedding for the text
    try:
        embedding = await _get_embedding(text.strip())
    except EmbeddingError as e:
        logger.error("Failed to embed memory text: %s", e)
        raise VectorMemoryError(f"Failed to embed memory: {e}")
    
    # Generate memory ID
    memory_id = str(uuid.uuid4())
    
    # Prepare payload
    payload = {
        "org_id": org_id,
        "user_id": user_id,
        "text": text.strip(),
        "created_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }
    
    # Store in Qdrant
    collection_name = _get_collection_name(org_id)
    point_data = {
        "points": [{
            "id": memory_id,
            "vector": embedding,
            "payload": payload
        }]
    }
    
    try:
        await _qdrant_request("PUT", f"/collections/{collection_name}/points", point_data)
        logger.debug("Stored memory %s for org %s", memory_id, org_id)
        return memory_id
        
    except QdrantError as e:
        logger.error("Failed to store memory in Qdrant: %s", e)
        raise VectorMemoryError(f"Failed to store memory: {e}")


async def search_memory(
    org_id: str,
    query: str,
    limit: int = 5,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Search memories in the organization's collection."""
    if not query or not query.strip():
        return []
    
    # Ensure collection exists
    if not await ensure_org_collection(org_id):
        logger.warning("Collection not found for org %s", org_id)
        return []
    
    # Get embedding for the query
    try:
        query_embedding = await _get_embedding(query.strip())
    except EmbeddingError as e:
        logger.error("Failed to embed search query: %s", e)
        raise VectorMemoryError(f"Failed to embed query: {e}")
    
    # Search in Qdrant
    collection_name = _get_collection_name(org_id)
    search_data = {
        "vector": query_embedding,
        "limit": limit,
        "score_threshold": score_threshold,
        "with_payload": True
    }
    
    try:
        response = await _qdrant_request("POST", f"/collections/{collection_name}/points/search", search_data)
        
        results = []
        for hit in response.get("result", []):
            result = {
                "id": hit["id"],
                "score": hit["score"],
                "payload": hit.get("payload", {})
            }
            results.append(result)
        
        logger.debug("Found %d memories for query in org %s", len(results), org_id)
        return results
        
    except QdrantError as e:
        logger.error("Failed to search memories: %s", e)
        raise VectorMemoryError(f"Failed to search memories: {e}")


async def delete_memory(org_id: str, memory_id: str) -> bool:
    """Delete a memory from the organization's collection."""
    collection_name = _get_collection_name(org_id)
    
    try:
        delete_data = {
            "points": [memory_id]
        }
        
        await _qdrant_request("POST", f"/collections/{collection_name}/points/delete", delete_data)
        logger.debug("Deleted memory %s from org %s", memory_id, org_id)
        return True
        
    except QdrantError as e:
        logger.error("Failed to delete memory %s: %s", memory_id, e)
        return False


async def get_memory_stats(org_id: str) -> Dict[str, Any]:
    """Get memory statistics for an organization."""
    collection_name = _get_collection_name(org_id)
    
    try:
        # Get collection info which includes point count
        response = await _qdrant_request("GET", f"/collections/{collection_name}")
        
        collection_info = response.get("result", {})
        points_count = collection_info.get("points_count", 0)
        status = collection_info.get("status", "unknown")
        
        return {
            "org_id": org_id,
            "collection_name": collection_name,
            "memory_count": points_count,
            "status": status,
            "embedding_dim": EMBEDDING_DIM
        }
        
    except QdrantError as e:
        logger.error("Failed to get stats for org %s: %s", org_id, e)
        return {
            "org_id": org_id,
            "collection_name": collection_name,
            "memory_count": 0,
            "status": "error",
            "error": str(e)
        }


async def health_check() -> Dict[str, Any]:
    """Check if Qdrant service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{QDRANT_URL}/healthz")
            response.raise_for_status()
            return {"status": "healthy", "url": QDRANT_URL}
    except Exception as e:
        return {"status": "unhealthy", "url": QDRANT_URL, "error": str(e)}