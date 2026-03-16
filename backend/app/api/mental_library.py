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
from sqlalchemy import text

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# The running mental-library service handles download, transcription, deletion.
MENTAL_LIBRARY_API_URL = os.getenv("MENTAL_LIBRARY_API_URL", "http://10.0.0.1:8100")

# ── Table setup ──────────────────────────────────────────────────

CREATE_VIDEOS = """
CREATE TABLE IF NOT EXISTS ml_videos (
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
    document_text TEXT DEFAULT ''
);
"""

CREATE_CHUNKS = """
CREATE TABLE IF NOT EXISTS ml_chunks (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES ml_videos(id) ON DELETE CASCADE,
    chunk_index INTEGER DEFAULT 0,
    text TEXT DEFAULT '',
    start_time REAL DEFAULT 0,
    end_time REAL DEFAULT 0,
    embedding_vector_id TEXT DEFAULT '',
    token_count INTEGER DEFAULT 0,
    topic_tags TEXT DEFAULT '',
    confidence_score REAL DEFAULT 0
);
"""


async def ensure_tables(db):
    await db.execute(text(CREATE_VIDEOS))
    await db.execute(text(CREATE_CHUNKS))
    await db.commit()


def _parse_tags(tags_str: str) -> list[str]:
    return [t.strip() for t in (tags_str or "").split(",") if t.strip()]


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
        "topic_tags, chunk_count, status FROM ml_videos "
        "WHERE status='completed' AND org_id = :org_id ORDER BY id DESC"
    ), {"org_id": org_id})
    rows = result.mappings().all()
    return [_video_row_to_dict(dict(r)) for r in rows]


@router.post("/videos/process")
async def process_video(request: Request):
    """Proxy to the mental-library service: submit a URL for processing."""
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{MENTAL_LIBRARY_API_URL}/videos/process",
                content=body,
                headers={"Content-Type": "application/json"},
            )
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
    await db.execute(text("DELETE FROM ml_chunks WHERE video_id = :vid AND org_id = :org_id"), {"vid": video_id, "org_id": org_id})
    result = await db.execute(text("DELETE FROM ml_videos WHERE id = :vid AND org_id = :org_id RETURNING id"), {"vid": video_id, "org_id": org_id})
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
    result = await db.execute(text("SELECT * FROM ml_videos WHERE id = :vid AND org_id = :org_id"), {"vid": video_id, "org_id": org_id})
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
        "FROM ml_chunks c JOIN ml_videos v ON c.video_id = v.id "
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
    videos = await db.execute(text("SELECT count(*) as c FROM ml_videos WHERE status='completed' AND org_id = :org_id"), {"org_id": org_id})
    chunks = await db.execute(text("SELECT count(*) as c FROM ml_chunks c JOIN ml_videos v ON c.video_id = v.id WHERE v.org_id = :org_id"), {"org_id": org_id})
    duration = await db.execute(text("SELECT coalesce(sum(duration),0) as d FROM ml_videos WHERE status='completed' AND org_id = :org_id"), {"org_id": org_id})
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
        "FROM ml_videos v "
        "LEFT JOIN ml_chunks c ON c.video_id = v.id "
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
        "FROM ml_videos WHERE id = :vid AND org_id = :org_id"
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
    """Convert a processed video into an agent skill (placeholder for now)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    await ensure_tables(db)
    
    # Check if video exists and belongs to this org
    result = await db.execute(text(
        "SELECT title, author, document_text FROM ml_videos "
        "WHERE id = :vid AND org_id = :org_id AND status = 'completed'"
    ), {"vid": video_id, "org_id": org_id})
    video = result.mappings().first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found or not processed")
    
    # TODO: Implement actual skill generation logic
    # For now, return a placeholder response
    return {
        "message": "Skill conversion initiated",
        "video_id": video_id,
        "skill_name": f"skill-{video['title'][:50].lower().replace(' ', '-')}",
        "status": "placeholder",
        "note": "This feature is not yet implemented - placeholder for skill conversion pipeline"
    }
