"""Mental Library — Video knowledge base stored in PostgreSQL.

Migrated from SQLite to the shared warroom PostgreSQL database.
Supports video processing, chunk storage, and search.
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import text

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# The running mental-library service handles download, transcription, deletion.
MENTAL_LIBRARY_API_URL = os.getenv("MENTAL_LIBRARY_API_URL", "http://10.0.0.1:8100")

# ── Table setup ──────────────────────────────────────────────────

CREATE_VIDEOS = """
CREATE TABLE IF NOT EXISTS crm.ml_videos (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT DEFAULT '',
    author TEXT DEFAULT '',
    description TEXT DEFAULT '',
    duration INTEGER DEFAULT 0,
    thumbnail_url TEXT DEFAULT '',
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    transcript_path TEXT DEFAULT '',
    audio_path TEXT DEFAULT '',
    topic_tags TEXT DEFAULT '',
    language TEXT DEFAULT 'en',
    chunk_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT DEFAULT '',
    document_text TEXT DEFAULT '',
    org_id INTEGER NOT NULL REFERENCES crm.organizations_tenant(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ml_service_id INTEGER DEFAULT NULL -- Foreign key to ML service's internal ID
);
"""

CREATE_CHUNKS = """
CREATE TABLE IF NOT EXISTS crm.ml_chunks (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES crm.ml_videos(id) ON DELETE CASCADE,
    chunk_index INTEGER DEFAULT 0,
    text TEXT DEFAULT '',
    start_time REAL DEFAULT 0,
    end_time REAL DEFAULT 0,
    embedding_vector_id TEXT DEFAULT '',
    token_count INTEGER DEFAULT 0,
    topic_tags TEXT DEFAULT '',
    confidence_score REAL DEFAULT 0,
    org_id INTEGER NOT NULL REFERENCES crm.organizations_tenant(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


async def ensure_tables(db):
    await db.execute(text(CREATE_VIDEOS))
    await db.execute(text(CREATE_CHUNKS))
    await db.commit()


def _parse_tags(tags_str: str) -> list[str]:
    return [t.strip() for t in (tags_str or "").split(",") if t.strip()]


async def _sync_video_from_ml_service(db, task_id: str, org_id: int):
    """After ML service processes a video, sync results to War Room DB."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Get status
            status_resp = await client.get(f"{MENTAL_LIBRARY_API_URL}/videos/status/{task_id}")
            if status_resp.status_code != 200:
                return None
                
            status_data = status_resp.json()
            if status_data["status"] != "completed":
                return None
                
            video_id = status_data["video_data"]["video_id"]
            
            # Get video details from ML service
            video_resp = await client.get(f"{MENTAL_LIBRARY_API_URL}/videos/{video_id}")
            if video_resp.status_code != 200:
                return None
                
            video_data = video_resp.json()
            
            # Get chunks from ML service
            chunks_resp = await client.get(f"{MENTAL_LIBRARY_API_URL}/videos/{video_id}/chunks")
            chunks_data = chunks_resp.json() if chunks_resp.status_code == 200 else []
            
            # Check if we already have this video (avoid duplicates)
            existing = await db.execute(text(
                "SELECT id FROM crm.ml_videos WHERE url = :url AND org_id = :org_id"
            ), {"url": video_data.get("url", ""), "org_id": org_id})
            
            if existing.first():
                logger.info(f"Video already synced: {video_data.get('title', 'Unknown')}")
                return existing.scalar()
            
            # Insert video into War Room PostgreSQL
            video_insert_result = await db.execute(text("""
                INSERT INTO crm.ml_videos (
                    url, title, author, description, duration, thumbnail_url,
                    topic_tags, chunk_count, status, document_text, org_id,
                    ml_service_id, processed_at
                ) VALUES (
                    :url, :title, :author, :description, :duration, :thumbnail_url,
                    :topic_tags, :chunk_count, 'completed', :document_text, :org_id,
                    :ml_service_id, :processed_at
                ) RETURNING id
            """), {
                "url": video_data.get("url", ""),
                "title": video_data.get("title", "")[:500],
                "author": video_data.get("author", "")[:200],
                "description": video_data.get("description", "")[:2000],
                "duration": int(video_data.get("duration", 0) or 0),
                "thumbnail_url": video_data.get("thumbnail_url", "")[:500],
                "topic_tags": ",".join(video_data.get("topic_tags", [])),
                "chunk_count": len(chunks_data),
                "document_text": video_data.get("document_text", ""),
                "org_id": org_id,
                "ml_service_id": video_id,
                "processed_at": video_data.get("processed_at")
            })
            
            war_room_video_id = video_insert_result.scalar()
            
            # Insert chunks
            for chunk in chunks_data:
                await db.execute(text("""
                    INSERT INTO crm.ml_chunks (
                        video_id, chunk_index, text, start_time, end_time,
                        token_count, topic_tags, org_id
                    ) VALUES (
                        :video_id, :chunk_index, :text, :start_time, :end_time,
                        :token_count, :topic_tags, :org_id
                    )
                """), {
                    "video_id": war_room_video_id,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "text": chunk.get("text", ""),
                    "start_time": float(chunk.get("start_time", 0) or 0),
                    "end_time": float(chunk.get("end_time", 0) or 0),
                    "token_count": int(chunk.get("token_count", 0) or 0),
                    "topic_tags": ",".join(chunk.get("topic_tags", [])),
                    "org_id": org_id
                })
            
            await db.commit()
            logger.info(f"Synced video: {video_data.get('title', 'Unknown')} with {len(chunks_data)} chunks")
            return war_room_video_id
            
    except Exception as e:
        logger.error(f"Failed to sync video from ML service: {e}")
        await db.rollback()
        return None


async def _background_sync_task(task_id: str, org_id: int):
    """Background task that polls ML service until video is complete, then syncs."""
    from app.db.crm_db import get_crm_db
    
    max_attempts = 60  # 10 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            attempt += 1
            
            # Get fresh DB connection for this background task
            async for db in get_crm_db():
                synced_video_id = await _sync_video_from_ml_service(db, task_id, org_id)
                if synced_video_id:
                    logger.info(f"Background sync completed for task {task_id}")
                    return synced_video_id
                
                # Wait 10 seconds before next attempt
                import asyncio
                await asyncio.sleep(10)
                break
            
        except Exception as e:
            logger.error(f"Background sync attempt {attempt} failed: {e}")
            import asyncio
            await asyncio.sleep(10)
    
    logger.warning(f"Background sync for task {task_id} timed out after {max_attempts} attempts")


def _video_row_to_dict(r: dict) -> dict:
    return {
        "id": r["id"],
        "url": r["url"],
        "title": r["title"],
        "author": r["author"],
        "duration": r["duration"] or 0,
        "thumbnail_url": r["thumbnail_url"],
        "processed_at": str(r["processed_at"]) if r["processed_at"] else None,
        "topic_tags": _parse_tags(r.get("topic_tags", "")),
        "chunk_count": r["chunk_count"] or 0,
        "status": r["status"],
    }


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/videos")
async def list_videos(request: Request, db=Depends(get_tenant_db)):
    org_id = get_org_id(request)
    await ensure_tables(db)
    result = await db.execute(text(
        "SELECT id, url, title, author, duration, thumbnail_url, processed_at, "
        "topic_tags, chunk_count, status FROM crm.ml_videos "
        "WHERE status='completed' AND org_id = :org_id ORDER BY id DESC"
    ), {"org_id": org_id})
    rows = result.mappings().all()
    return [_video_row_to_dict(dict(r)) for r in rows]


@router.post("/videos/process")
async def process_video(request: Request, db=Depends(get_tenant_db)):
    """Proxy to the mental-library service and start background sync."""
    org_id = get_org_id(request)
    await ensure_tables(db)
    
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{MENTAL_LIBRARY_API_URL}/videos/process",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            
            if resp.status_code == 200:
                # Start background sync process
                resp_data = resp.json()
                task_id = resp_data.get("task_id")
                if task_id:
                    import asyncio
                    asyncio.create_task(_background_sync_task(task_id, org_id))
            
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Mental library service is not reachable")


@router.get("/videos/status/{task_id}")
async def video_status(task_id: str):
    """Proxy to the mental-library service: poll processing status for a task."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{MENTAL_LIBRARY_API_URL}/videos/status/{task_id}")
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Mental library service is not reachable")


@router.delete("/videos/{video_id}")
async def delete_video(request: Request, video_id: int, db=Depends(get_tenant_db)):
    """Delete a video and its chunks. Also proxy to external service if running."""
    org_id = get_org_id(request)
    await ensure_tables(db)

    # Delete from our DB (with org_id filter)
    await db.execute(text("DELETE FROM crm.ml_chunks WHERE video_id = :vid AND org_id = :org_id"), {"vid": video_id, "org_id": org_id})
    result = await db.execute(text("DELETE FROM crm.ml_videos WHERE id = :vid AND org_id = :org_id RETURNING id"), {"vid": video_id, "org_id": org_id})
    await db.commit()

    if not result.first():
        raise HTTPException(status_code=404, detail="Video not found")

    # Also try to proxy delete to the external service (best effort)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(f"{MENTAL_LIBRARY_API_URL}/videos/{video_id}")
    except Exception:
        pass  # External service may not be running

    return {"deleted": True, "video_id": video_id}


@router.get("/videos/{video_id}")
async def get_video(request: Request, video_id: int, db=Depends(get_tenant_db)):
    org_id = get_org_id(request)
    await ensure_tables(db)
    result = await db.execute(text("SELECT * FROM crm.ml_videos WHERE id = :vid AND org_id = :org_id"), {"vid": video_id, "org_id": org_id})
    r = result.mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="Video not found")
    row = dict(r)
    return {
        **_video_row_to_dict(row),
        "description": row.get("description", ""),
        "document_text": row.get("document_text", ""),
    }


@router.get("/videos/{video_id}/chunks")
async def get_video_chunks(request: Request, video_id: int, db=Depends(get_tenant_db)):
    org_id = get_org_id(request)
    await ensure_tables(db)
    result = await db.execute(text(
        "SELECT c.id, c.chunk_index, c.text, c.start_time, c.end_time, c.token_count, c.topic_tags "
        "FROM crm.ml_chunks c JOIN crm.ml_videos v ON c.video_id = v.id "
        "WHERE c.video_id = :vid AND v.org_id = :org_id ORDER BY c.chunk_index"
    ), {"vid": video_id, "org_id": org_id})
    return [
        {
            "id": r["id"],
            "chunk_index": r["chunk_index"],
            "text": r["text"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "token_count": r["token_count"] or 0,
            "topic_tags": _parse_tags(r.get("topic_tags", "")),
        }
        for r in result.mappings().all()
    ]


@router.get("/stats")
async def stats(request: Request, db=Depends(get_tenant_db)):
    org_id = get_org_id(request)
    await ensure_tables(db)
    videos = await db.execute(text("SELECT count(*) as c FROM crm.ml_videos WHERE status='completed' AND org_id = :org_id"), {"org_id": org_id})
    chunks = await db.execute(text("SELECT count(*) as c FROM crm.ml_chunks c JOIN crm.ml_videos v ON c.video_id = v.id WHERE v.org_id = :org_id"), {"org_id": org_id})
    duration = await db.execute(text("SELECT coalesce(sum(duration),0) as d FROM crm.ml_videos WHERE status='completed' AND org_id = :org_id"), {"org_id": org_id})
    return {
        "total_videos": videos.scalar() or 0,
        "total_chunks": chunks.scalar() or 0,
        "total_duration": duration.scalar() or 0,
    }


@router.get("/search")
async def search_videos(request: Request, q: str = "", db=Depends(get_tenant_db)):
    """Full-text search across video titles, authors, tags, and chunk text."""
    org_id = get_org_id(request)
    await ensure_tables(db)

    if not q.strip():
        return await list_videos(request, db)

    pattern = f"%{q}%"
    result = await db.execute(text(
        "SELECT DISTINCT v.id, v.url, v.title, v.author, v.duration, v.thumbnail_url, "
        "v.processed_at, v.topic_tags, v.chunk_count, v.status "
        "FROM crm.ml_videos v "
        "LEFT JOIN crm.ml_chunks c ON c.video_id = v.id "
        "WHERE v.status = 'completed' AND v.org_id = :org_id AND ("
        "  v.title ILIKE :q OR v.author ILIKE :q OR v.topic_tags ILIKE :q "
        "  OR v.description ILIKE :q OR c.text ILIKE :q"
        ") ORDER BY v.id DESC LIMIT 50"
    ), {"q": pattern, "org_id": org_id})
    rows = result.mappings().all()
    return [_video_row_to_dict(dict(r)) for r in rows]


@router.get("/videos/{video_id}/document")
async def get_video_document(request: Request, video_id: int, db=Depends(get_tenant_db)):
    """Get the full processed document for a video."""
    org_id = get_org_id(request)
    await ensure_tables(db)
    result = await db.execute(text(
        "SELECT title, author, description, document_text, processed_at, url "
        "FROM crm.ml_videos WHERE id = :vid AND org_id = :org_id"
    ), {"vid": video_id, "org_id": org_id})
    r = result.mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="Video not found")
    
    row = dict(r)
    return {
        "title": row["title"],
        "author": row["author"], 
        "description": row["description"],
        "document_text": row["document_text"],
        "processed_at": str(row["processed_at"]) if row["processed_at"] else None,
        "source_url": row["url"]
    }


@router.post("/videos/{video_id}/convert-to-skill")
async def convert_video_to_skill(request: Request, video_id: int, db=Depends(get_tenant_db)):
    """Convert a processed video into an agent skill."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    await ensure_tables(db)
    
    # Check if video exists and belongs to this org
    result = await db.execute(text(
        "SELECT title, author, document_text, url FROM crm.ml_videos "
        "WHERE id = :vid AND org_id = :org_id AND status = 'completed'"
    ), {"vid": video_id, "org_id": org_id})
    video = result.mappings().first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found or not processed")
    
    # Get chunks for additional context
    chunks_result = await db.execute(text(
        "SELECT text, start_time, end_time FROM crm.ml_chunks "
        "WHERE video_id = :vid ORDER BY chunk_index"
    ), {"vid": video_id})
    chunks = chunks_result.mappings().all()
    
    # Generate skill content
    skill_name = _sanitize_skill_name(video["title"])
    skill_content = _generate_skill_content(
        title=video["title"], 
        author=video["author"],
        url=video["url"],
        document_text=video["document_text"],
        chunks=[dict(c) for c in chunks]
    )
    
    # Store in knowledge pool
    try:
        await db.execute(text("""
            INSERT INTO org_knowledge_pool (
                org_id, user_id, title, content, task_type, source_url, 
                created_at, status, content_type
            ) VALUES (
                :org_id, :user_id, :title, :content, 'skill', :source_url,
                NOW(), 'completed', 'agent_skill'
            )
        """), {
            "org_id": org_id,
            "user_id": user_id,
            "title": f"Skill: {skill_name}",
            "content": skill_content,
            "source_url": video["url"]
        })
        await db.commit()
        
        return {
            "message": "Skill successfully created and stored",
            "video_id": video_id,
            "skill_name": skill_name,
            "status": "completed",
            "skill_content_preview": skill_content[:500] + "..." if len(skill_content) > 500 else skill_content
        }
        
    except Exception as e:
        logger.error(f"Failed to store skill: {e}")
        raise HTTPException(status_code=500, detail="Failed to store skill in knowledge pool")


def _sanitize_skill_name(title: str) -> str:
    """Convert video title to a valid skill name."""
    import re
    # Remove special characters, convert to lowercase
    name = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())
    # Replace spaces with dashes, limit length
    name = re.sub(r'\s+', '-', name.strip())[:50]
    # Ensure it doesn't start/end with dash
    name = name.strip('-')
    return name or "video-skill"


def _generate_skill_content(title: str, author: str, url: str, document_text: str, chunks: list) -> str:
    """Generate AgentSkill SKILL.md content from video data."""
    # Create a summary from first few chunks if document_text is empty
    if not document_text and chunks:
        summary_chunks = chunks[:3]  # First 3 chunks
        document_text = "\n\n".join([chunk["text"] for chunk in summary_chunks])
    
    # Format timestamps for key segments
    key_segments = ""
    if chunks and len(chunks) > 1:
        key_segments = "\n\n### Key Segments\n\n"
        for i, chunk in enumerate(chunks[:5]):  # First 5 chunks
            timestamp = f"{int(chunk['start_time']//60)}:{int(chunk['start_time']%60):02d}"
            key_segments += f"**{timestamp}**: {chunk['text'][:100]}...\n\n"
    
    skill_content = f"""# {title}

**Source:** {author}  
**Video:** {url}

## Description

This skill captures insights and knowledge from "{title}" by {author}.

## Summary

{document_text[:1000]}{'...' if len(document_text) > 1000 else ''}

{key_segments}

## Usage

Use this skill when you need information about:
- {title.split(':')[0] if ':' in title else title}
- Insights from {author}
- Related concepts and strategies

## Implementation Notes

This skill was auto-generated from video transcription. Review and refine as needed for your specific use case.

**Generated from:** {url}  
**Timestamp:** {datetime.now(timezone.utc).isoformat()}
"""
    return skill_content
