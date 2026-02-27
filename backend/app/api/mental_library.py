"""Mental Library — proxy mutations to the running mental-library service;
read-only endpoints query the shared SQLite DB directly (mounted read-only).
"""
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
import sqlite3
import httpx
import os

router = APIRouter()

# Path to the SQLite DB mounted from the mental-library service volume.
DB_PATH = os.getenv(
    "MENTAL_LIBRARY_DB",
    "/data/mental-library/mental_library.db"
)

# The running mental-library service handles download, transcription, deletion.
# Currently on Brain 1 (10.0.0.1). Set via MENTAL_LIBRARY_API_URL env var.
MENTAL_LIBRARY_API_URL = os.getenv("MENTAL_LIBRARY_API_URL", "http://10.0.0.1:8100")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/videos")
async def list_videos():
    db = get_db()
    rows = db.execute(
        "SELECT id, url, title, author, duration, thumbnail_url, processed_at, "
        "topic_tags, chunk_count, status FROM videos WHERE status='completed' ORDER BY id DESC"
    ).fetchall()
    db.close()
    return [
        {
            "id": r["id"],
            "url": r["url"],
            "title": r["title"],
            "author": r["author"],
            "duration": r["duration"] or 0,
            "thumbnail_url": r["thumbnail_url"],
            "processed_at": r["processed_at"],
            "topic_tags": [t.strip() for t in (r["topic_tags"] or "").split(",") if t.strip()],
            "chunk_count": r["chunk_count"] or 0,
            "status": r["status"],
        }
        for r in rows
    ]


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
async def delete_video(video_id: int):
    """Proxy to the mental-library service: delete a video and its embeddings."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(f"{MENTAL_LIBRARY_API_URL}/videos/{video_id}")
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Mental library service is not reachable")


@router.get("/videos/{video_id}")
async def get_video(video_id: int):
    db = get_db()
    r = db.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
    db.close()
    if not r:
        raise HTTPException(status_code=404, detail="Video not found")
    return {
        "id": r["id"],
        "url": r["url"],
        "title": r["title"],
        "author": r["author"],
        "description": r["description"],
        "duration": r["duration"] or 0,
        "thumbnail_url": r["thumbnail_url"],
        "processed_at": r["processed_at"],
        "topic_tags": [t.strip() for t in (r["topic_tags"] or "").split(",") if t.strip()],
        "chunk_count": r["chunk_count"] or 0,
        "status": r["status"],
        "document_text": r["document_text"],
    }


@router.get("/videos/{video_id}/chunks")
async def get_video_chunks(video_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT id, chunk_index, text, start_time, end_time, token_count, topic_tags "
        "FROM chunks WHERE video_id=? ORDER BY id", (video_id,)
    ).fetchall()
    db.close()
    return [
        {
            "id": r["id"],
            "chunk_index": r["chunk_index"],
            "text": r["text"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "token_count": r["token_count"] or 0,
            "topic_tags": [t.strip() for t in (r["topic_tags"] or "").split(",") if t.strip()],
        }
        for r in rows
    ]


@router.get("/stats")
async def stats():
    db = get_db()
    videos = db.execute("SELECT count(*) as c FROM videos WHERE status='completed'").fetchone()
    chunks = db.execute("SELECT count(*) as c FROM chunks").fetchone()
    duration = db.execute("SELECT coalesce(sum(duration),0) as d FROM videos WHERE status='completed'").fetchone()
    db.close()
    return {
        "total_videos": videos["c"],
        "total_chunks": chunks["c"],
        "total_duration": duration["d"],
    }
