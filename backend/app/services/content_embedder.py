"""Content embedding pipeline for the recommendation engine.

Embeds top competitor content (captions + transcripts + audience intel)
into Qdrant for semantic search and content-based recommendations.

Infrastructure:
- Qdrant: http://10.0.0.11:6333
- Embedding model: nomic-embed-text via http://10.0.0.11:11435
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://10.0.0.11:6333")
FASTEMBED_URL = os.getenv("FASTEMBED_URL", "http://10.0.0.11:11435")
COLLECTION_NAME = "content_recommendations"
EMBEDDING_DIM = 768  # nomic-embed-text dimension


async def _get_embedding(text_input: str) -> Optional[List[float]]:
    """Get embedding vector from the embedding service."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{FASTEMBED_URL}/v1/embeddings",
                json={"input": text_input[:8000], "model": "nomic-embed-text-v1.5"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["data"][0]["embedding"]
            else:
                logger.warning("Embedding service returned %d: %s", resp.status_code, resp.text[:200])
                return None
    except Exception as e:
        logger.error("Embedding service error: %s", e)
        return None


async def _ensure_collection():
    """Create Qdrant collection if it doesn't exist."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Check if exists
            resp = await client.get(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
            if resp.status_code == 200:
                return True
            
            # Create
            resp = await client.put(
                f"{QDRANT_URL}/collections/{COLLECTION_NAME}",
                json={
                    "vectors": {
                        "size": EMBEDDING_DIM,
                        "distance": "Cosine",
                    },
                },
            )
            if resp.status_code in (200, 201):
                logger.info("Created Qdrant collection: %s", COLLECTION_NAME)
                return True
            else:
                logger.error("Failed to create collection: %s", resp.text[:200])
                return False
    except Exception as e:
        logger.error("Qdrant connection error: %s", e)
        return False


def _build_document_text(post: Dict[str, Any]) -> str:
    """Build a rich text document from a post for embedding.
    
    Combines caption, transcript, and audience intel into one
    searchable text block.
    """
    parts = []
    
    # Caption / post text
    caption = post.get("post_text", "") or ""
    if caption:
        parts.append(caption.strip())
    
    # Hook (proven opening)
    hook = post.get("hook", "") or ""
    if hook and hook not in caption:
        parts.append(f"Hook: {hook}")
    
    # Transcript (what's said in the video)
    transcript = post.get("transcript")
    if transcript:
        if isinstance(transcript, str):
            try:
                transcript = json.loads(transcript)
            except json.JSONDecodeError:
                transcript = None
        if isinstance(transcript, list):
            transcript_text = " ".join(seg.get("text", "") for seg in transcript if seg.get("text"))
            if transcript_text:
                parts.append(f"Video transcript: {transcript_text[:3000]}")
    
    # Audience intelligence (themes, questions, pain points)
    comments_data = post.get("comments_data")
    if comments_data:
        if isinstance(comments_data, str):
            try:
                comments_data = json.loads(comments_data)
            except json.JSONDecodeError:
                comments_data = None
        if isinstance(comments_data, dict):
            questions = comments_data.get("questions", [])
            if questions:
                q_text = "; ".join(q.get("question", "") for q in questions[:5])
                parts.append(f"Audience questions: {q_text}")
            
            pain_points = comments_data.get("pain_points", [])
            if pain_points:
                p_text = "; ".join(p.get("pain", "") for p in pain_points[:5])
                parts.append(f"Pain points: {p_text}")
            
            themes = comments_data.get("themes", [])
            if themes:
                t_text = ", ".join(t.get("theme", "") for t in themes[:10])
                parts.append(f"Themes: {t_text}")
    
    return "\n\n".join(parts)


def _build_metadata(post: Dict[str, Any]) -> Dict[str, Any]:
    """Build metadata payload for Qdrant point."""
    # Extract hashtags from caption
    import re
    caption = post.get("post_text", "") or ""
    hashtags = re.findall(r"#(\w+)", caption)
    
    # Sentiment from audience intel
    sentiment = "unknown"
    comments_data = post.get("comments_data")
    if comments_data:
        if isinstance(comments_data, str):
            try:
                comments_data = json.loads(comments_data)
            except Exception:
                comments_data = None
        if isinstance(comments_data, dict):
            sentiment = comments_data.get("sentiment", "unknown")
    
    posted_at = post.get("posted_at")
    if isinstance(posted_at, datetime):
        posted_at = posted_at.isoformat()
    elif posted_at is None:
        posted_at = ""
    
    return {
        "competitor_id": post.get("competitor_id", 0),
        "competitor_handle": post.get("handle", ""),
        "platform": post.get("platform", "instagram"),
        "media_type": post.get("media_type", "image"),
        "shortcode": post.get("shortcode", ""),
        "post_url": post.get("post_url", ""),
        "hook": (post.get("hook", "") or "")[:200],
        "likes": post.get("likes", 0) or 0,
        "comments_count": post.get("comments", 0) or 0,
        "views": post.get("shares", 0) or 0,
        "engagement_score": float(post.get("engagement_score", 0) or 0),
        "hashtags": hashtags[:20],
        "sentiment": sentiment,
        "has_transcript": bool(post.get("transcript")),
        "has_audience_intel": bool(post.get("comments_data")),
        "posted_at": str(posted_at),
        "indexed_at": datetime.now().isoformat(),
    }


async def index_top_content(
    db: AsyncSession,
    min_engagement_percentile: float = 0.8,
    days: int = 90,
    limit: int = 200,
) -> Dict:
    """Index top competitor content into Qdrant for recommendations.
    
    Only indexes the top tier (default top 20%) by engagement score.
    Prefer posts with transcripts and audience intel for richer embeddings.
    
    Returns: {indexed: int, skipped: int, errors: [str]}
    """
    if not await _ensure_collection():
        return {"indexed": 0, "skipped": 0, "errors": ["Failed to connect to Qdrant"]}
    
    # Load all posts with engagement stats
    cutoff = datetime.now() - timedelta(days=days)
    result = await db.execute(
        text("""
            SELECT cp.*, c.handle,
                   PERCENT_RANK() OVER (
                       PARTITION BY cp.competitor_id 
                       ORDER BY cp.engagement_score
                   ) as engagement_percentile
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON c.id = cp.competitor_id
            WHERE cp.posted_at >= :cutoff OR cp.posted_at IS NULL
            ORDER BY cp.engagement_score DESC
        """),
        {"cutoff": cutoff},
    )
    all_posts = [dict(row._mapping) for row in result.fetchall()]
    
    # Filter to top percentile
    top_posts = [
        p for p in all_posts
        if p.get("engagement_percentile", 0) >= min_engagement_percentile
    ][:limit]
    
    if not top_posts:
        return {"indexed": 0, "skipped": 0, "errors": ["No top content found to index"]}
    
    stats = {"indexed": 0, "skipped": 0, "errors": []}
    points = []
    
    for post in top_posts:
        post_id = post.get("id")
        if not post_id:
            stats["skipped"] += 1
            continue
        
        doc_text = _build_document_text(post)
        if len(doc_text.strip()) < 20:
            stats["skipped"] += 1
            continue
        
        embedding = await _get_embedding(doc_text)
        if not embedding:
            stats["errors"].append(f"post {post_id}: embedding failed")
            continue
        
        metadata = _build_metadata(post)
        
        points.append({
            "id": post_id,
            "vector": embedding,
            "payload": metadata,
        })
        
        # Batch upsert every 20 points
        if len(points) >= 20:
            success = await _upsert_points(points)
            if success:
                stats["indexed"] += len(points)
            else:
                stats["errors"].append(f"batch upsert failed ({len(points)} points)")
            points = []
    
    # Flush remaining
    if points:
        success = await _upsert_points(points)
        if success:
            stats["indexed"] += len(points)
        else:
            stats["errors"].append(f"final upsert failed ({len(points)} points)")
    
    logger.info(
        "Content indexing complete: %d indexed, %d skipped, %d errors",
        stats["indexed"], stats["skipped"], len(stats["errors"])
    )
    return stats


async def _upsert_points(points: List[Dict]) -> bool:
    """Upsert a batch of points into Qdrant."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
                json={"points": points},
            )
            return resp.status_code == 200
    except Exception as e:
        logger.error("Qdrant upsert error: %s", e)
        return False


async def search_similar_content(
    query: str,
    platform: str = None,
    min_engagement: float = 0,
    limit: int = 10,
) -> List[Dict]:
    """Search for content similar to a query string.
    
    Returns ranked list of similar competitor content with metadata.
    """
    embedding = await _get_embedding(query)
    if not embedding:
        return []
    
    # Build filter
    must_conditions = []
    if platform:
        must_conditions.append({
            "key": "platform",
            "match": {"value": platform},
        })
    if min_engagement > 0:
        must_conditions.append({
            "key": "engagement_score",
            "range": {"gte": min_engagement},
        })
    
    search_body = {
        "vector": embedding,
        "limit": limit,
        "with_payload": True,
    }
    if must_conditions:
        search_body["filter"] = {"must": must_conditions}
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search",
                json=search_body,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for hit in data.get("result", []):
                    payload = hit.get("payload", {})
                    payload["similarity_score"] = round(hit.get("score", 0), 4)
                    payload["post_db_id"] = hit.get("id")
                    results.append(payload)
                return results
            else:
                logger.warning("Qdrant search failed: %s", resp.text[:200])
                return []
    except Exception as e:
        logger.error("Qdrant search error: %s", e)
        return []


async def get_index_status() -> Dict:
    """Get current state of the content recommendation index."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
            if resp.status_code == 200:
                data = resp.json().get("result", {})
                return {
                    "collection": COLLECTION_NAME,
                    "points_count": data.get("points_count", 0),
                    "indexed_vectors": data.get("indexed_vectors_count", 0),
                    "status": data.get("status", "unknown"),
                }
            return {"collection": COLLECTION_NAME, "points_count": 0, "status": "not_found"}
    except Exception as e:
        return {"collection": COLLECTION_NAME, "points_count": 0, "status": f"error: {e}"}
