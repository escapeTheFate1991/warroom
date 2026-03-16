"""Mental Library — Universal Ingestion Engine.

Ingests URLs (articles, docs), PDFs, and enhances video processing.
All content ends up in ml_videos + ml_chunks for unified search.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Schema migrations ────────────────────────────────────────────

MIGRATIONS = [
    "ALTER TABLE crm.ml_videos ADD COLUMN IF NOT EXISTS media_type TEXT DEFAULT 'video'",
    "ALTER TABLE crm.ml_videos ADD COLUMN IF NOT EXISTS source_url TEXT",
    "ALTER TABLE crm.ml_videos ADD COLUMN IF NOT EXISTS ingestion_method TEXT DEFAULT 'manual'",
    "ALTER TABLE crm.ml_chunks ADD COLUMN IF NOT EXISTS source_url TEXT",
    "ALTER TABLE crm.ml_chunks ADD COLUMN IF NOT EXISTS chunk_type TEXT DEFAULT 'transcript'",
    "ALTER TABLE crm.ml_chunks ADD COLUMN IF NOT EXISTS frame_data JSONB DEFAULT '{}'",
]


async def _run_migrations(db):
    for sql in MIGRATIONS:
        try:
            await db.execute(text(sql))
        except Exception as exc:
            logger.debug("Migration skip: %s", exc)
    await db.commit()


# ── Helpers ──────────────────────────────────────────────────────

def _detect_url_type(url: str) -> str:
    """Classify URL as video, article, or docs."""
    parsed = urlparse(url)
    host = parsed.hostname or ""

    # YouTube
    if "youtube.com" in host or "youtu.be" in host:
        return "video"
    # Vimeo
    if "vimeo.com" in host:
        return "video"
    # Common video extensions
    if any(url.lower().endswith(ext) for ext in [".mp4", ".webm", ".mov"]):
        return "video"
    # PDF
    if url.lower().endswith(".pdf"):
        return "pdf"
    # Documentation sites
    if any(pattern in host for pattern in ["docs.", "wiki.", "readme.", "gitbook."]):
        return "documentation"
    # GitHub repos
    if "github.com" in host and "/blob/" not in url and "/tree/" not in url:
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 2:  # owner/repo
            return "repository"

    return "article"


def _smart_chunk(text_content: str, max_tokens: int = 500) -> list[dict]:
    """Split text into chunks respecting section boundaries.

    Preserves code blocks, headers, and paragraph breaks.
    Returns list of {text, chunk_type, token_count}.
    """
    if not text_content or not text_content.strip():
        return []

    chunks: list[dict] = []
    # Split by headers first (## or ### markdown headers)
    sections = re.split(r'\n(?=#{1,3}\s)', text_content)

    current_chunk = ""
    current_tokens = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Rough token estimate (words * 1.3)
        section_tokens = int(len(section.split()) * 1.3)

        if current_tokens + section_tokens > max_tokens and current_chunk:
            # Determine chunk type
            chunk_type = "code" if "```" in current_chunk else "text"
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_type": chunk_type,
                "token_count": current_tokens,
            })
            current_chunk = ""
            current_tokens = 0

        if section_tokens > max_tokens:
            # Section too big — split by paragraphs
            paragraphs = section.split("\n\n")
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                para_tokens = int(len(para.split()) * 1.3)

                if current_tokens + para_tokens > max_tokens and current_chunk:
                    chunk_type = "code" if "```" in current_chunk else "text"
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_type": chunk_type,
                        "token_count": current_tokens,
                    })
                    current_chunk = ""
                    current_tokens = 0

                current_chunk += para + "\n\n"
                current_tokens += para_tokens
        else:
            current_chunk += section + "\n\n"
            current_tokens += section_tokens

    # Flush remaining
    if current_chunk.strip():
        chunk_type = "code" if "```" in current_chunk else "text"
        chunks.append({
            "text": current_chunk.strip(),
            "chunk_type": chunk_type,
            "token_count": current_tokens,
        })

    return chunks


async def _fetch_article(url: str) -> dict:
    """Fetch and extract readable content from a URL."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; WarRoom/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        })
        resp.raise_for_status()
        html = resp.text

    # Basic content extraction — strip HTML tags, keep text
    # For production, use readability or trafilatura
    import re as _re

    # Remove script/style
    cleaned = _re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
    # Remove tags
    text_content = _re.sub(r'<[^>]+>', '\n', cleaned)
    # Clean whitespace
    text_content = _re.sub(r'\n{3,}', '\n\n', text_content)
    text_content = _re.sub(r'[ \t]+', ' ', text_content)
    text_content = text_content.strip()

    # Extract title from <title> tag
    title_match = _re.search(r'<title[^>]*>(.*?)</title>', html, _re.IGNORECASE | _re.DOTALL)
    title = title_match.group(1).strip() if title_match else url

    # Extract meta description
    desc_match = _re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, _re.IGNORECASE)
    description = desc_match.group(1).strip() if desc_match else ""

    return {
        "title": title[:500],
        "description": description[:1000],
        "text": text_content[:100000],  # Cap at 100k chars
        "url": url,
    }


async def _extract_pdf_text(content: bytes) -> dict:
    """Extract text from PDF bytes using PyMuPDF if available, else basic fallback."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=content, filetype="pdf")
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text())
        full_text = "\n\n".join(pages_text)

        title = doc.metadata.get("title", "") or f"PDF ({len(doc)} pages)"
        author = doc.metadata.get("author", "")
        doc.close()

        return {
            "title": title,
            "author": author,
            "text": full_text[:200000],
            "page_count": len(pages_text),
        }
    except ImportError:
        logger.warning("PyMuPDF not installed — PDF ingestion limited")
        return {
            "title": "PDF Document",
            "author": "",
            "text": "(PDF text extraction requires PyMuPDF: pip install PyMuPDF)",
            "page_count": 0,
        }


# ── Schemas ──────────────────────────────────────────────────────

class IngestURLRequest(BaseModel):
    url: str
    tags: Optional[str] = ""
    source: str = "chat_link"  # chat_link, manual, competitor_scan


class IngestResponse(BaseModel):
    video_id: int
    title: str
    media_type: str
    chunk_count: int
    status: str


class VideoAnalysisRequest(BaseModel):
    url: str
    competitor_name: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def universal_ingest(request: Request, req: IngestURLRequest, db=Depends(get_tenant_db)):
    """Universal ingester — auto-detects URL type and processes accordingly.

    Supports: articles, documentation sites, YouTube videos (proxied to ML service), PDFs.
    """
    org_id = get_org_id(request)
    await _run_migrations(db)

    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    media_type = _detect_url_type(url)

    # Check for duplicate
    existing = await db.execute(
        text("SELECT id FROM crm.ml_videos WHERE source_url = :url OR url = :url LIMIT 1"),
        {"url": url},
    )
    if existing.first():
        raise HTTPException(status_code=409, detail="This URL has already been ingested")

    if media_type == "video":
        # Proxy to existing mental library video processing service
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                from app.api.mental_library import MENTAL_LIBRARY_API_URL
                resp = await client.post(
                    f"{MENTAL_LIBRARY_API_URL}/videos/process",
                    json={"url": url},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return IngestResponse(
                        video_id=data.get("video_id", 0),
                        title=data.get("title", url),
                        media_type="video",
                        chunk_count=0,
                        status="processing",
                    )
        except Exception as exc:
            logger.warning("Video processing service unavailable: %s", exc)
            raise HTTPException(status_code=503, detail="Video processing service not available")

    elif media_type == "pdf":
        # Fetch PDF from URL
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                pdf_data = await _extract_pdf_text(resp.content)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch PDF: {exc}")

        return await _store_and_chunk(
            db, org_id, pdf_data["title"], pdf_data.get("author", ""), pdf_data["text"],
            url, media_type="pdf", tags=req.tags, source=req.source,
            description=f"{pdf_data.get('page_count', 0)} pages",
        )

    else:
        # Article / documentation
        try:
            article = await _fetch_article(url)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}")

        if len(article["text"]) < 50:
            raise HTTPException(status_code=422, detail="Could not extract meaningful content from this URL")

        return await _store_and_chunk(
            db, org_id, article["title"], "", article["text"],
            url, media_type=media_type, tags=req.tags, source=req.source,
            description=article.get("description", ""),
        )


@router.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf_upload(
    request: Request,
    file: UploadFile = File(...),
    tags: str = Form(""),
    db=Depends(get_tenant_db),
):
    """Upload and ingest a PDF file."""
    org_id = get_org_id(request)
    await _run_migrations(db)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="PDF too large (max 50MB)")

    pdf_data = await _extract_pdf_text(content)

    # Use file hash as dedup key
    file_hash = hashlib.md5(content).hexdigest()
    source_url = f"upload://{file.filename}#{file_hash}"

    return await _store_and_chunk(
        db, org_id, pdf_data["title"] or file.filename, pdf_data.get("author", ""),
        pdf_data["text"], source_url,
        media_type="pdf", tags=tags, source="manual",
        description=f"{pdf_data.get('page_count', 0)} pages",
    )


@router.post("/analyze-video")
async def analyze_competitor_video(request: Request, req: VideoAnalysisRequest, db=Depends(get_tenant_db)):
    """Analyze a competitor video for hooks, transitions, CTAs, and layout patterns.

    Returns structured analysis that feeds into competitor intel.
    """
    org_id = get_org_id(request)
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # For now, extract what we can from the video metadata
    # Full frame analysis requires the video processing service + Gemini vision
    analysis = {
        "url": url,
        "competitor": req.competitor_name,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "hook": {"text": None, "duration_seconds": None, "style": None},
        "transitions": [],
        "cta": {"text": None, "position": None},
        "layout": {"type": None, "orientation": None},
        "metrics": {},
        "recommendations": [],
        "status": "pending_deep_analysis",
    }

    # Try to get video metadata via yt-dlp style extraction
    if "youtube.com" in url or "youtu.be" in url:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Use noembed for basic metadata
                oembed_url = f"https://noembed.com/embed?url={url}"
                resp = await client.get(oembed_url)
                if resp.status_code == 200:
                    meta = resp.json()
                    analysis["title"] = meta.get("title", "")
                    analysis["author"] = meta.get("author_name", "")
                    analysis["thumbnail"] = meta.get("thumbnail_url", "")
        except Exception:
            pass

    # Store in competitor's video_analysis if competitor specified
    if req.competitor_name:
        try:
            await db.execute(text("""
                UPDATE leadgen.leads
                SET video_analysis = COALESCE(video_analysis, '[]'::jsonb) || :analysis::jsonb
                WHERE company_name ILIKE :name
            """), {
                "analysis": f'[{__import__("json").dumps(analysis)}]',
                "name": f"%{req.competitor_name}%",
            })
            await db.commit()
        except Exception as exc:
            logger.warning("Failed to store video analysis: %s", exc)

    return analysis


@router.get("/sources")
async def list_sources(request: Request, db=Depends(get_tenant_db)):
    """List all ingested sources with type and status."""
    org_id = get_org_id(request)
    await _run_migrations(db)

    result = await db.execute(text("""
        SELECT id, url, title, media_type, source_url, ingestion_method,
               status, chunk_count, processed_at
        FROM crm.ml_videos
        WHERE org_id = :org_id
        ORDER BY id DESC
        LIMIT 100
    """), {"org_id": org_id})
    rows = result.mappings().all()
    return [
        {
            "id": r["id"],
            "url": r["url"],
            "title": r["title"],
            "media_type": r.get("media_type", "video"),
            "source_url": r.get("source_url"),
            "ingestion_method": r.get("ingestion_method", "manual"),
            "status": r["status"],
            "chunk_count": r["chunk_count"] or 0,
            "processed_at": str(r["processed_at"]) if r["processed_at"] else None,
        }
        for r in rows
    ]


# ── Internal ─────────────────────────────────────────────────────

async def _store_and_chunk(
    db, org_id: int, title: str, author: str, text_content: str,
    url: str, media_type: str, tags: str, source: str,
    description: str = "",
) -> IngestResponse:
    """Store content as ml_video + chunked ml_chunks."""
    chunks = _smart_chunk(text_content)

    # Insert video record
    result = await db.execute(text("""
        INSERT INTO crm.ml_videos (url, title, author, description, media_type, source_url,
                               ingestion_method, topic_tags, status, chunk_count, processed_at, org_id)
        VALUES (:url, :title, :author, :desc, :media_type, :source_url,
                :method, :tags, 'completed', :count, NOW(), :org_id)
        RETURNING id
    """), {
        "url": url,
        "title": title[:500],
        "author": author[:200],
        "desc": description[:2000],
        "media_type": media_type,
        "source_url": url,
        "method": source,
        "tags": tags,
        "count": len(chunks),
        "org_id": org_id,
    })
    video_id = result.scalar_one()

    # Insert chunks
    for i, chunk in enumerate(chunks):
        await db.execute(text("""
            INSERT INTO crm.ml_chunks (video_id, chunk_index, text, token_count, chunk_type, source_url, org_id)
            VALUES (:vid, :idx, :text, :tokens, :ctype, :url, :org_id)
        """), {
            "vid": video_id,
            "idx": i,
            "text": chunk["text"],
            "tokens": chunk["token_count"],
            "ctype": chunk["chunk_type"],
            "url": url,
            "org_id": org_id,
        })

    await db.commit()

    logger.info("Ingested %s: '%s' → %d chunks", media_type, title[:60], len(chunks))

    return IngestResponse(
        video_id=video_id,
        title=title[:500],
        media_type=media_type,
        chunk_count=len(chunks),
        status="completed",
    )
