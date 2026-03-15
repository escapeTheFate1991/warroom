"""Lead Enrichment API — enrich contacts/leads with public web data.

Table: public.lead_enrichments (auto-created on startup).
No API keys needed — extracts domain info, social links from homepage.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from app.db.leadgen_db import leadgen_engine, leadgen_session
from app.services.tenant import get_org_id

logger = logging.getLogger(__name__)

# ── DB Setup — uses shared leadgen engine (same knowledge DB, public schema)
_engine = leadgen_engine
_session = leadgen_session

router = APIRouter()

# ── Table DDL ────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.lead_enrichments (
    id                      SERIAL PRIMARY KEY,
    contact_submission_id   INTEGER,
    lead_id                 INTEGER,
    email                   TEXT NOT NULL,
    domain                  TEXT,
    company_name            TEXT,
    company_description     TEXT,
    social_profiles         JSONB DEFAULT '{}',
    website_info            JSONB DEFAULT '{}',
    enriched_at             TIMESTAMP WITH TIME ZONE,
    status                  VARCHAR(20) DEFAULT 'pending',
    error                   TEXT
);
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_lead_enrichments_email ON public.lead_enrichments (email)",
    "CREATE INDEX IF NOT EXISTS idx_lead_enrichments_status ON public.lead_enrichments (status)",
    "CREATE INDEX IF NOT EXISTS idx_lead_enrichments_contact_id ON public.lead_enrichments (contact_submission_id)",
    "CREATE INDEX IF NOT EXISTS idx_lead_enrichments_lead_id ON public.lead_enrichments (lead_id)",
]


async def init_enrichments_table():
    """Auto-create the lead_enrichments table on startup."""
    try:
        async with _engine.begin() as conn:
            await conn.execute(text(CREATE_TABLE_SQL))
            for idx_sql in INDEX_SQLS:
                await conn.execute(text(idx_sql))
        logger.info("lead_enrichments table ready")
    except Exception as e:
        logger.error("Failed to init lead_enrichments table: %s", e)


# ── Schemas ──────────────────────────────────────────────────────────
class EnrichRequest(BaseModel):
    email: Optional[EmailStr] = None
    contact_submission_id: Optional[int] = None


class BatchEnrichRequest(BaseModel):
    emails: list[str]


# ── Social Link Extraction ───────────────────────────────────────────
SOCIAL_PATTERNS = {
    "linkedin": re.compile(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[^\s"\'<>]+', re.IGNORECASE),
    "twitter": re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s"\'<>]+', re.IGNORECASE),
    "facebook": re.compile(r'https?://(?:www\.)?facebook\.com/[^\s"\'<>]+', re.IGNORECASE),
    "instagram": re.compile(r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+', re.IGNORECASE),
}


def _extract_domain(email: str) -> Optional[str]:
    """Extract domain from email address, skip free providers."""
    free_domains = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "aol.com", "icloud.com", "mail.com", "protonmail.com",
        "live.com", "msn.com", "ymail.com",
    }
    try:
        domain = email.strip().lower().split("@")[1]
        return None if domain in free_domains else domain
    except (IndexError, AttributeError):
        return None


def _parse_title(html: str) -> Optional[str]:
    """Extract <title> from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # Clean up common suffixes
        for sep in [" | ", " - ", " — ", " · "]:
            if sep in title:
                title = title.split(sep)[0].strip()
        return title[:200] if title else None
    return None


def _parse_meta_description(html: str) -> Optional[str]:
    """Extract meta description from HTML."""
    match = re.search(
        r'<meta\s+(?:[^>]*?\s+)?(?:name|property)\s*=\s*["\'](?:description|og:description)["\'][^>]*?\s+content\s*=\s*["\']([^"\']*)["\']',
        html, re.IGNORECASE,
    )
    if not match:
        # Try reversed attribute order
        match = re.search(
            r'<meta\s+(?:[^>]*?\s+)?content\s*=\s*["\']([^"\']*)["\'][^>]*?\s+(?:name|property)\s*=\s*["\'](?:description|og:description)["\']',
            html, re.IGNORECASE,
        )
    if match:
        desc = match.group(1).strip()
        return desc[:500] if desc else None
    return None


def _extract_social_links(html: str) -> dict:
    """Find social media URLs in page HTML."""
    socials = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        match = pattern.search(html)
        if match:
            url = match.group(0).rstrip('",;)')
            socials[platform] = url
    return socials


# ── Core Enrichment Logic ────────────────────────────────────────────
async def _enrich_email(email: str) -> dict:
    """Enrich a single email — fetch domain homepage, extract metadata."""
    domain = _extract_domain(email)
    result = {
        "domain": domain,
        "company_name": None,
        "company_description": None,
        "social_profiles": {},
        "website_info": {},
    }

    if not domain:
        result["website_info"] = {"note": "Free email provider — no domain to enrich"}
        return result

    url = f"https://{domain}"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; WarRoom/1.0)"},
        ) as client:
            resp = await client.get(url)
            html = resp.text

        title = _parse_title(html)
        description = _parse_meta_description(html)
        socials = _extract_social_links(html)

        result["company_name"] = title
        result["company_description"] = description
        result["social_profiles"] = socials
        result["website_info"] = {
            "url": str(resp.url),
            "status_code": resp.status_code,
            "title": title,
            "description": description,
            "domain": domain,
        }

    except httpx.HTTPError as e:
        result["website_info"] = {"url": url, "error": str(e), "domain": domain}
    except Exception as e:
        result["website_info"] = {"url": url, "error": f"Unexpected: {e}", "domain": domain}

    return result


async def _run_enrichment(enrichment_id: int, email: str, contact_submission_id: Optional[int] = None):
    """Background task: enrich and store results."""
    try:
        data = await _enrich_email(email)

        async with _session() as db:
            await db.execute(
                text("""
                    UPDATE public.lead_enrichments
                    SET domain = :domain,
                        company_name = :company_name,
                        company_description = :company_description,
                        social_profiles = CAST(:social_profiles AS jsonb),
                        website_info = CAST(:website_info AS jsonb),
                        enriched_at = now(),
                        status = 'enriched'
                    WHERE id = :id
                """),
                {
                    "id": enrichment_id,
                    "domain": data["domain"],
                    "company_name": data["company_name"],
                    "company_description": data["company_description"],
                    "social_profiles": __import__("json").dumps(data["social_profiles"]),
                    "website_info": __import__("json").dumps(data["website_info"]),
                },
            )
            await db.commit()

        # Update contact_submissions with enriched company info if linked
        if contact_submission_id and data["company_name"]:
            try:
                async with _session() as db:
                    await db.execute(
                        text("""
                            UPDATE public.contact_submissions
                            SET notes = COALESCE(notes, '') || E'\n[Enriched] ' || :company_info
                            WHERE id = :id
                        """),
                        {
                            "id": contact_submission_id,
                            "company_info": f"{data['company_name']} — {data.get('company_description') or 'No description'}",
                        },
                    )
                    await db.commit()
            except Exception as e:
                logger.warning("Failed to update contact_submission %d: %s", contact_submission_id, e)

        logger.info("Enriched email %s (id=%d)", email, enrichment_id)

    except Exception as e:
        logger.error("Enrichment failed for %s (id=%d): %s", email, enrichment_id, e)
        async with _session() as db:
            await db.execute(
                text("""
                    UPDATE public.lead_enrichments
                    SET status = 'failed', error = :error
                    WHERE id = :id
                """),
                {"id": enrichment_id, "error": str(e)[:500]},
            )
            await db.commit()


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/enrichment/enrich", status_code=202)
async def enrich(body: EnrichRequest, background_tasks: BackgroundTasks):
    """Enrich a lead by email or contact_submission_id. Runs in background."""
    org_id = get_org_id(request)
    email = body.email

    # Resolve email from contact_submission if needed
    if not email and body.contact_submission_id:
        async with _session() as db:
            result = await db.execute(
                text("SELECT email FROM public.contact_submissions WHERE id = :id"),
                {"id": body.contact_submission_id},
            )
            row = result.fetchone()
            if not row:
                return JSONResponse(status_code=404, content={"error": "Contact submission not found"})
            email = row[0]

    if not email:
        return JSONResponse(status_code=400, content={"error": "email or contact_submission_id required"})

    email = email.lower().strip()

    # Check for existing recent enrichment (avoid duplicates)
    async with _session() as db:
        existing = await db.execute(
            text("""
                SELECT id, status, enriched_at, company_name, domain, social_profiles, website_info
                FROM public.lead_enrichments
                WHERE email = :email AND status = 'enriched'
                  AND enriched_at > now() - INTERVAL '7 days'
                ORDER BY enriched_at DESC LIMIT 1
            """),
            {"email": email},
        )
        cached = existing.fetchone()
        if cached:
            return {"id": cached[0], "status": "cached", "message": "Recent enrichment exists"}

    # Create enrichment record
    async with _session() as db:
        result = await db.execute(
            text("""
                INSERT INTO public.lead_enrichments (email, contact_submission_id, lead_id)
                VALUES (:email, :csid, :lid)
                RETURNING id
            """),
            {
                "email": email,
                "csid": body.contact_submission_id,
                "lid": None,
            },
        )
        enrichment_id = result.fetchone()[0]
        await db.commit()

    background_tasks.add_task(_run_enrichment, enrichment_id, email, body.contact_submission_id)

    return {"id": enrichment_id, "status": "pending", "message": "Enrichment started"}


@router.get("/enrichment/{enrichment_id}")
async def get_enrichment(enrichment_id: int):
    """Get enrichment result by ID."""
    org_id = get_org_id(request)
    async with _session() as db:
        result = await db.execute(
            text("""
                SELECT id, contact_submission_id, lead_id, email, domain,
                       company_name, company_description, social_profiles,
                       website_info, enriched_at, status, error
                FROM public.lead_enrichments
                WHERE id = :id
            """),
            {"id": enrichment_id},
        )
        row = result.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Enrichment not found"})
        return dict(row._mapping)


@router.get("/enrichment/by-email/{email}")
async def get_by_email(email: str):
    """Lookup enrichment results by email."""
    org_id = get_org_id(request)
    async with _session() as db:
        result = await db.execute(
            text("""
                SELECT id, contact_submission_id, lead_id, email, domain,
                       company_name, company_description, social_profiles,
                       website_info, enriched_at, status, error
                FROM public.lead_enrichments
                WHERE email = :email
                ORDER BY enriched_at DESC NULLS LAST
                LIMIT 10
            """),
            {"email": email.lower().strip()},
        )
        rows = result.fetchall()
        if not rows:
            return JSONResponse(status_code=404, content={"error": "No enrichments found for this email"})
        return {"items": [dict(r._mapping) for r in rows]}


@router.post("/enrichment/batch", status_code=202)
async def batch_enrich(body: BatchEnrichRequest, background_tasks: BackgroundTasks):
    """Batch enrich multiple emails. Each runs in background."""
    org_id = get_org_id(request)
    if not body.emails:
        return JSONResponse(status_code=400, content={"error": "emails list is empty"})

    if len(body.emails) > 50:
        return JSONResponse(status_code=400, content={"error": "Max 50 emails per batch"})

    results = []
    async with _session() as db:
        for email in body.emails:
            email = email.lower().strip()

            # Check cache
            existing = await db.execute(
                text("""
                    SELECT id FROM public.lead_enrichments
                    WHERE email = :email AND status = 'enriched'
                      AND enriched_at > now() - INTERVAL '7 days'
                    LIMIT 1
                """),
                {"email": email},
            )
            cached = existing.fetchone()
            if cached:
                results.append({"email": email, "id": cached[0], "status": "cached"})
                continue

            # Insert new
            result = await db.execute(
                text("""
                    INSERT INTO public.lead_enrichments (email)
                    VALUES (:email)
                    RETURNING id
                """),
                {"email": email},
            )
            enrichment_id = result.fetchone()[0]
            results.append({"email": email, "id": enrichment_id, "status": "pending"})

            background_tasks.add_task(_run_enrichment, enrichment_id, email)

        await db.commit()

    return {
        "total": len(results),
        "queued": sum(1 for r in results if r["status"] == "pending"),
        "cached": sum(1 for r in results if r["status"] == "cached"),
        "items": results,
    }
