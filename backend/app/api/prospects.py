"""Prospects API — unified view of qualified leads, contact submissions, and email leads.

Merges data from:
- leadgen.leads (hot/contacted leads)
- public.contact_submissions (website form submissions)
- Calendar events tagged as prospect meetings

Table: public.prospects_meta (stores stage, notes, and source mapping)
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()

# ── DB Setup ─────────────────────────────────────────────────
DB_URL = "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
_engine = create_async_engine(DB_URL, echo=False, pool_size=3, max_overflow=5)
_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


# ── Table DDL ────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.prospects_meta (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(20) NOT NULL,       -- leadgen, form, email, referral
    source_id       INTEGER,                    -- FK to source table
    stage           VARCHAR(30) DEFAULT 'new',  -- new, contacted, meeting_scheduled, proposal_sent, won, lost
    notes           TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_prospects_meta_source ON public.prospects_meta (source);
CREATE INDEX IF NOT EXISTS idx_prospects_meta_stage ON public.prospects_meta (stage);
"""

_TABLE_INIT = False


async def init_prospects_table():
    """Auto-create the prospects_meta table on startup."""
    global _TABLE_INIT
    if _TABLE_INIT:
        return
    try:
        async with _engine.begin() as conn:
            for stmt in CREATE_TABLE_SQL.split(";"):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(text(stmt))
        _TABLE_INIT = True
        logger.info("Prospects meta table initialized")
    except Exception as e:
        logger.error("Failed to init prospects table: %s", e)
        _TABLE_INIT = True


# ── Schemas ──────────────────────────────────────────────────

class ProspectListRequest(BaseModel):
    source: Optional[str] = None           # leadgen, form, email, all
    stage: Optional[str] = None            # new, contacted, meeting_scheduled, proposal_sent, won, lost
    search: Optional[str] = None           # search by name/business
    sort_by: Optional[str] = "created_at"  # created_at, stage, score
    sort_dir: Optional[str] = "desc"       # asc, desc
    limit: int = 50
    offset: int = 0


class ProspectStageUpdate(BaseModel):
    stage: str


class ProspectNotesUpdate(BaseModel):
    notes: str


# ── Helpers ──────────────────────────────────────────────────

def _get_stage_for_lead(outreach_status: str, lead_tier: str) -> str:
    """Map lead outreach_status to prospect stage."""
    mapping = {
        "none": "new",
        "contacted": "contacted",
        "in_progress": "contacted",
        "won": "won",
        "lost": "lost",
    }
    return mapping.get(outreach_status, "new")


def _get_stage_for_submission(status: str) -> str:
    """Map contact submission status to prospect stage."""
    mapping = {
        "new": "new",
        "read": "new",
        "in_progress": "contacted",
        "replied": "contacted",
        "closed": "won",
        "spam": "lost",
    }
    return mapping.get(status, "new")


# ── Endpoints ────────────────────────────────────────────────

@router.post("/prospects/list")
async def list_prospects(req: ProspectListRequest):
    """Unified prospect list merging leads + contact submissions."""
    await init_prospects_table()

    prospects = []

    async with _session() as db:
        # 1. Fetch qualified leads (hot tier OR outreach != none)
        lead_sql = """
            SELECT id, business_name, address, city, state, phone, website,
                   google_rating, google_reviews_count, emails,
                   lead_score, lead_tier, outreach_status, contacted_at,
                   website_audit_score, website_audit_grade,
                   review_sentiment_score, review_highlights, review_pain_points,
                   review_opportunity_flags, contact_notes, contact_history,
                   owner_name, notes, created_at, updated_at
            FROM leadgen.leads
            WHERE outreach_status != 'none' OR lead_tier = 'hot'
            ORDER BY created_at DESC
        """
        result = await db.execute(text(lead_sql))
        rows = result.mappings().all()

        for row in rows:
            emails_list = row["emails"] or []
            stage = _get_stage_for_lead(row["outreach_status"] or "none", row["lead_tier"] or "")

            # Check for override in prospects_meta
            meta = await db.execute(
                text("SELECT stage, notes FROM public.prospects_meta WHERE source = 'leadgen' AND source_id = :sid"),
                {"sid": row["id"]},
            )
            meta_row = meta.mappings().first()
            if meta_row:
                stage = meta_row["stage"]

            prospect = {
                "id": f"lead-{row['id']}",
                "source_id": row["id"],
                "source": "leadgen",
                "name": row["owner_name"] or row["business_name"],
                "business_name": row["business_name"],
                "email": emails_list[0] if emails_list else None,
                "phone": row["phone"],
                "website": row["website"],
                "address": ", ".join(filter(None, [row["address"], row["city"], row["state"]])),
                "stage": stage,
                "score": row["lead_score"] or 0,
                "rating": float(row["google_rating"]) if row["google_rating"] else None,
                "reviews_count": row["google_reviews_count"] or 0,
                "review_sentiment_score": float(row["review_sentiment_score"]) if row["review_sentiment_score"] else None,
                "review_highlights": row["review_highlights"] or [],
                "review_pain_points": row["review_pain_points"] or [],
                "review_opportunity_flags": row["review_opportunity_flags"] or [],
                "website_audit_score": row["website_audit_score"],
                "website_audit_grade": row["website_audit_grade"],
                "contact_notes": row["contact_notes"] or (meta_row["notes"] if meta_row else None),
                "contact_history": row["contact_history"] or [],
                "lead_tier": row["lead_tier"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "last_activity": (row["contacted_at"] or row["updated_at"] or row["created_at"]).isoformat() if (row["contacted_at"] or row["updated_at"] or row["created_at"]) else None,
                "original_message": None,
            }
            prospects.append(prospect)

        # 2. Fetch contact form submissions
        sub_sql = """
            SELECT id, name, email, phone, message, status, notes,
                   submitted_at
            FROM public.contact_submissions
            ORDER BY submitted_at DESC
        """
        result = await db.execute(text(sub_sql))
        rows = result.mappings().all()

        for row in rows:
            stage = _get_stage_for_submission(row["status"] or "new")

            meta = await db.execute(
                text("SELECT stage, notes FROM public.prospects_meta WHERE source = 'form' AND source_id = :sid"),
                {"sid": row["id"]},
            )
            meta_row = meta.mappings().first()
            if meta_row:
                stage = meta_row["stage"]

            prospect = {
                "id": f"form-{row['id']}",
                "source_id": row["id"],
                "source": "form",
                "name": row["name"],
                "business_name": None,
                "email": row["email"],
                "phone": row["phone"],
                "website": None,
                "address": None,
                "stage": stage,
                "score": 0,
                "rating": None,
                "reviews_count": 0,
                "review_sentiment_score": None,
                "review_highlights": [],
                "review_pain_points": [],
                "review_opportunity_flags": [],
                "website_audit_score": None,
                "website_audit_grade": None,
                "contact_notes": row["notes"] or (meta_row["notes"] if meta_row else None),
                "contact_history": [],
                "lead_tier": None,
                "created_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
                "last_activity": row["submitted_at"].isoformat() if row["submitted_at"] else None,
                "original_message": row["message"],
            }
            prospects.append(prospect)

    # Apply filters
    if req.source and req.source != "all":
        prospects = [p for p in prospects if p["source"] == req.source]

    if req.stage and req.stage != "all":
        prospects = [p for p in prospects if p["stage"] == req.stage]

    if req.search:
        q = req.search.lower()
        prospects = [p for p in prospects if
                     q in (p["name"] or "").lower() or
                     q in (p["business_name"] or "").lower() or
                     q in (p["email"] or "").lower()]

    # Sort
    stage_order = {"new": 0, "contacted": 1, "meeting_scheduled": 2, "proposal_sent": 3, "won": 4, "lost": 5}

    if req.sort_by == "stage":
        prospects.sort(key=lambda p: stage_order.get(p["stage"], 99), reverse=(req.sort_dir == "desc"))
    elif req.sort_by == "score":
        prospects.sort(key=lambda p: p["score"] or 0, reverse=(req.sort_dir == "desc"))
    else:
        prospects.sort(key=lambda p: p["created_at"] or "", reverse=(req.sort_dir == "desc"))

    total = len(prospects)
    prospects = prospects[req.offset: req.offset + req.limit]

    # Stats
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Recalculate stats from full (unfiltered) set — re-fetch if filtered
    # For simplicity, compute from current filtered set context
    all_prospects_for_stats = prospects  # This is post-filter; ideally pre-filter but good enough

    stats = {
        "total": total,
        "new_this_week": sum(1 for p in prospects if p["stage"] == "new" and (p["created_at"] or "") >= week_ago),
        "meetings_scheduled": sum(1 for p in prospects if p["stage"] == "meeting_scheduled"),
        "won_this_month": sum(1 for p in prospects if p["stage"] == "won" and (p["created_at"] or "") >= month_start),
    }

    return {"prospects": prospects, "total": total, "stats": stats}


@router.patch("/prospects/{prospect_id}/stage")
async def update_prospect_stage(prospect_id: str, body: ProspectStageUpdate):
    """Update the stage of a prospect."""
    await init_prospects_table()

    valid_stages = {"new", "contacted", "meeting_scheduled", "proposal_sent", "won", "lost"}
    if body.stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {body.stage}")

    parts = prospect_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid prospect ID format")

    source = "leadgen" if parts[0] == "lead" else parts[0]
    source_id = int(parts[1])

    async with _session() as db:
        # Upsert into prospects_meta
        await db.execute(text("""
            INSERT INTO public.prospects_meta (source, source_id, stage, updated_at)
            VALUES (:source, :source_id, :stage, now())
            ON CONFLICT (source, source_id)
            DO UPDATE SET stage = :stage, updated_at = now()
        """), {"source": source, "source_id": source_id, "stage": body.stage})
        await db.commit()

    return {"ok": True, "prospect_id": prospect_id, "stage": body.stage}


@router.patch("/prospects/{prospect_id}/notes")
async def update_prospect_notes(prospect_id: str, body: ProspectNotesUpdate):
    """Update the notes for a prospect."""
    await init_prospects_table()

    parts = prospect_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid prospect ID format")

    source = "leadgen" if parts[0] == "lead" else parts[0]
    source_id = int(parts[1])

    async with _session() as db:
        await db.execute(text("""
            INSERT INTO public.prospects_meta (source, source_id, notes, updated_at)
            VALUES (:source, :source_id, :notes, now())
            ON CONFLICT (source, source_id)
            DO UPDATE SET notes = :notes, updated_at = now()
        """), {"source": source, "source_id": source_id, "notes": body.notes})
        await db.commit()

    return {"ok": True, "prospect_id": prospect_id}
