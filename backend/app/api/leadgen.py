"""LeadGen API — Business discovery, enrichment, and website auditing."""

import csv
import io
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, case, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import get_leadgen_db, leadgen_session
from app.models.lead import Lead, SearchJob
from app.services.leadgen.google_places import search_places
from app.services.leadgen.enrichment import enrich_job
from app.services.leadgen.website_auditor import audit_website
from app.services.leadgen.lead_scorer import score_lead
from app.api.leadgen_schemas import (
    LeadResponse, LeadUpdate, StatsResponse, SearchRequest,
    SearchJobResponse, WebsiteAuditResult, ContactLogRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Ensure enrichment_error column exists (idempotent ALTER TABLE)
# ---------------------------------------------------------------------------
_ENRICHMENT_ERROR_COL_ADDED = False


async def _ensure_enrichment_error_column(db: AsyncSession):
    """Add enrichment_error column to leads table if it doesn't exist."""
    global _ENRICHMENT_ERROR_COL_ADDED
    if _ENRICHMENT_ERROR_COL_ADDED:
        return
    try:
        await db.execute(text(
            "ALTER TABLE leadgen.leads ADD COLUMN IF NOT EXISTS enrichment_error TEXT"
        ))
        await db.commit()
        _ENRICHMENT_ERROR_COL_ADDED = True
    except Exception:
        await db.rollback()
        _ENRICHMENT_ERROR_COL_ADDED = True  # Don't retry on every request


# ---------------------------------------------------------------------------
# Ensure lead_source column exists (idempotent ALTER TABLE)
# ---------------------------------------------------------------------------
_SOURCE_COL_ADDED = False


async def _ensure_source_column(db: AsyncSession):
    """Add lead_source column to leads table if it doesn't exist."""
    global _SOURCE_COL_ADDED
    if _SOURCE_COL_ADDED:
        return
    try:
        await db.execute(text(
            "ALTER TABLE leadgen.leads ADD COLUMN IF NOT EXISTS lead_source TEXT DEFAULT 'google_places'"
        ))
        await db.commit()
        _SOURCE_COL_ADDED = True
    except Exception:
        await db.rollback()
        _SOURCE_COL_ADDED = True


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def _run_search(job_id: int, request: SearchRequest):
    """Background task: search for businesses, insert leads with pending enrichment."""
    async with leadgen_session() as db:
        try:
            await _ensure_enrichment_error_column(db)
            await _ensure_source_column(db)

            places = await search_places(request.query, request.location, request.max_results, request.radius_km)

            inserted = 0
            for place in places:
                existing = await db.execute(
                    select(Lead).where(Lead.google_place_id == place.place_id)
                )
                if existing.scalar_one_or_none():
                    continue

                lead = Lead(
                    search_job_id=job_id,
                    google_place_id=place.place_id,
                    business_name=place.name,
                    address=place.address,
                    city=place.city,
                    state=place.state,
                    zip=place.zip_code,
                    phone=place.phone,
                    website=place.website or None,
                    google_maps_url=place.maps_url,
                    google_rating=place.rating or None,
                    google_reviews_count=place.review_count,
                    business_category=place.category,
                    business_types=place.types,
                    latitude=place.latitude or None,
                    longitude=place.longitude or None,
                    opening_hours=place.opening_hours,
                    has_website=bool(place.website),
                    enrichment_status="pending",
                )
                db.add(lead)
                inserted += 1

            # Complete the search job — leads available
            job = (await db.execute(select(SearchJob).where(SearchJob.id == job_id))).scalar_one()
            job.total_found = len(places)
            job.status = "complete"
            await db.commit()

            # Try to set lead_source for newly inserted leads
            try:
                for place in places:
                    await db.execute(
                        text("UPDATE leadgen.leads SET lead_source = :src WHERE google_place_id = :pid"),
                        {"src": place.source, "pid": place.place_id},
                    )
                await db.commit()
            except Exception:
                await db.rollback()

            logger.info(
                "Search complete for job %d (%d found, %d new), starting enrichment",
                job_id, len(places), inserted,
            )

            # Run enrichment inline
            await _run_enrichment_safe(job_id, db)
            logger.info("Enrichment complete for job %d", job_id)

        except Exception as exc:
            logger.error("Search job %d failed: %s", job_id, exc, exc_info=True)
            try:
                job = (await db.execute(select(SearchJob).where(SearchJob.id == job_id))).scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)[:500]
                    await db.commit()
            except Exception:
                pass


async def _run_enrichment_safe(job_id: int, db: AsyncSession):
    """Enrich leads for a job, catching per-lead failures gracefully."""
    try:
        await enrich_job(job_id, db)
    except Exception as exc:
        logger.error("Enrichment for job %d failed globally: %s", job_id, exc, exc_info=True)
        # Mark remaining pending leads as failed
        try:
            await db.execute(
                text("""
                    UPDATE leadgen.leads
                    SET enrichment_status = 'failed',
                        enrichment_error = :err
                    WHERE search_job_id = :jid AND enrichment_status = 'pending'
                """),
                {"err": f"Batch enrichment error: {str(exc)[:200]}", "jid": job_id},
            )
            await db.commit()
        except Exception:
            await db.rollback()


async def _run_enrichment(job_id: int):
    """Background task: enrich pending leads for a search job."""
    async with leadgen_session() as db:
        try:
            logger.info("Starting enrichment for job %d", job_id)
            await _run_enrichment_safe(job_id, db)
            logger.info("Enrichment complete for job %d", job_id)
        except Exception as exc:
            logger.error("Enrichment job %d failed: %s", job_id, exc, exc_info=True)


# ---------------------------------------------------------------------------
# Lead endpoints
# ---------------------------------------------------------------------------

@router.get("/leads", response_model=list[LeadResponse])
async def list_leads(
    search_job_id: int | None = None,
    tier: str | None = None,
    enrichment_status: str | None = None,
    has_website: bool | None = None,
    category: str | None = None,
    city: str | None = None,
    state: str | None = None,
    min_score: int | None = None,
    sort_by: str = "lead_score",
    sort_dir: str = "desc",
    limit: int = Query(default=10, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """List leads with filtering and sorting."""
    try:
        query = select(Lead)

        if search_job_id:
            query = query.where(Lead.search_job_id == search_job_id)
        if tier:
            query = query.where(Lead.lead_tier == tier)
        if enrichment_status:
            query = query.where(Lead.enrichment_status == enrichment_status)
        if has_website is not None:
            query = query.where(Lead.has_website == has_website)
        if category:
            query = query.where(Lead.business_category.ilike(f"%{category}%"))
        if city:
            query = query.where(Lead.city.ilike(f"%{city}%"))
        if state:
            query = query.where(Lead.state == state.upper())
        if min_score is not None:
            query = query.where(Lead.lead_score >= min_score)

        sort_column = getattr(Lead, sort_by, Lead.lead_score)
        query = query.order_by(sort_column.desc() if sort_dir == "desc" else sort_column.asc())
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()
    except Exception as exc:
        logger.error("Failed to list leads: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load leads: {str(exc)[:200]}")


@router.get("/leads/stats", response_model=StatsResponse)
async def get_stats(search_job_id: int | None = None, db: AsyncSession = Depends(get_leadgen_db)):
    """Get lead statistics."""
    try:
        base = select(Lead)
        if search_job_id:
            base = base.where(Lead.search_job_id == search_job_id)

        total = (await db.execute(select(func.count(Lead.id)).select_from(base.subquery()))).scalar() or 0
        enriched = (await db.execute(
            select(func.count(Lead.id)).where(Lead.enrichment_status == "enriched")
        )).scalar() or 0
        with_site = (await db.execute(
            select(func.count(Lead.id)).where(Lead.has_website == True)
        )).scalar() or 0
        without_site = (await db.execute(
            select(func.count(Lead.id)).where(Lead.has_website == False, Lead.enrichment_status == "enriched")
        )).scalar() or 0

        hot = (await db.execute(select(func.count(Lead.id)).where(Lead.lead_tier == "hot"))).scalar() or 0
        warm = (await db.execute(select(func.count(Lead.id)).where(Lead.lead_tier == "warm"))).scalar() or 0
        cold = (await db.execute(select(func.count(Lead.id)).where(Lead.lead_tier == "cold"))).scalar() or 0
        avg_score = (await db.execute(select(func.avg(Lead.lead_score)))).scalar() or 0.0

        cats = await db.execute(
            select(Lead.business_category, func.count(Lead.id).label("count"))
            .where(Lead.business_category.isnot(None))
            .group_by(Lead.business_category)
            .order_by(func.count(Lead.id).desc())
            .limit(10)
        )
        top_categories = [{"category": row[0], "count": row[1]} for row in cats.all()]

        contacted = (await db.execute(select(func.count(Lead.id)).where(Lead.outreach_status != "none"))).scalar() or 0
        won = (await db.execute(select(func.count(Lead.id)).where(Lead.contact_outcome == "won"))).scalar() or 0
        lost = (await db.execute(select(func.count(Lead.id)).where(Lead.contact_outcome == "lost"))).scalar() or 0

        return StatsResponse(
            total_leads=total,
            enriched=enriched,
            with_website=with_site,
            without_website=without_site,
            hot_leads=hot,
            warm_leads=warm,
            cold_leads=cold,
            avg_lead_score=round(float(avg_score), 1),
            top_categories=top_categories,
            contacted=contacted,
            won=won,
            lost=lost,
        )
    except Exception as exc:
        logger.error("Failed to get stats: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load stats: {str(exc)[:200]}")


@router.get("/leads/export")
async def export_leads(
    search_job_id: int | None = None,
    tier: str | None = None,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Export leads to CSV."""
    try:
        query = select(Lead)
        if search_job_id:
            query = query.where(Lead.search_job_id == search_job_id)
        if tier:
            query = query.where(Lead.lead_tier == tier)
        query = query.order_by(Lead.lead_score.desc())

        result = await db.execute(query)
        leads = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Business Name", "Address", "City", "State", "Zip", "Phone",
            "Website", "Emails", "Google Rating", "Reviews",
            "Category", "Platform", "Lead Score", "Tier",
            "Facebook", "Instagram", "LinkedIn", "Twitter",
            "Audit Score", "Audit Grade", "Notes",
        ])
        for lead in leads:
            writer.writerow([
                lead.business_name, lead.address, lead.city, lead.state,
                lead.zip, lead.phone, lead.website,
                "; ".join(lead.emails or []),
                lead.google_rating, lead.google_reviews_count,
                lead.business_category, lead.website_platform,
                lead.lead_score, lead.lead_tier,
                lead.facebook_url, lead.instagram_url,
                lead.linkedin_url, lead.twitter_url,
                lead.website_audit_score, lead.website_audit_grade,
                lead.notes,
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
        )
    except Exception as exc:
        logger.error("Failed to export leads: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(exc)[:200]}")


# ---------------------------------------------------------------------------
# Freshness & stale data management
# ---------------------------------------------------------------------------

@router.get("/leads/freshness")
async def get_freshness(db: AsyncSession = Depends(get_leadgen_db)):
    """Return freshness info for each search job — how old the data is."""
    try:
        result = await db.execute(
            select(SearchJob).order_by(SearchJob.created_at.desc())
        )
        jobs = result.scalars().all()
        now = datetime.utcnow()

        freshness = []
        for job in jobs:
            created = job.created_at.replace(tzinfo=None) if job.created_at.tzinfo else job.created_at
            age = now - created
            age_days = age.days
            freshness.append({
                "job_id": job.id,
                "query": job.query,
                "location": job.location,
                "status": job.status,
                "total_found": job.total_found,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "age_days": age_days,
                "age_label": (
                    "Today" if age_days == 0
                    else f"{age_days} day{'s' if age_days != 1 else ''} old"
                ),
                "is_stale": age_days > 30,
            })
        return freshness
    except Exception as exc:
        logger.error("Failed to get freshness: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Freshness check failed: {str(exc)[:200]}")


@router.delete("/leads/stale")
async def delete_stale_leads(
    max_age_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Delete leads (and search jobs) older than max_age_days."""
    try:
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        # Find stale job IDs
        stale_jobs = await db.execute(
            select(SearchJob.id).where(SearchJob.created_at < cutoff)
        )
        stale_job_ids = [row[0] for row in stale_jobs.all()]

        if not stale_job_ids:
            return {"deleted_leads": 0, "deleted_jobs": 0, "cutoff_days": max_age_days}

        # Delete leads attached to stale jobs
        lead_result = await db.execute(
            delete(Lead).where(Lead.search_job_id.in_(stale_job_ids))
        )
        leads_deleted = lead_result.rowcount

        # Delete stale jobs
        job_result = await db.execute(
            delete(SearchJob).where(SearchJob.id.in_(stale_job_ids))
        )
        jobs_deleted = job_result.rowcount

        await db.commit()
        logger.info("Deleted %d stale leads and %d jobs (older than %d days)", leads_deleted, jobs_deleted, max_age_days)
        return {"deleted_leads": leads_deleted, "deleted_jobs": jobs_deleted, "cutoff_days": max_age_days}
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to delete stale leads: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Stale cleanup failed: {str(exc)[:200]}")


# ---------------------------------------------------------------------------
# Search endpoints
# ---------------------------------------------------------------------------

@router.post("/search", response_model=SearchJobResponse)
async def create_search(request: SearchRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_leadgen_db)):
    """Start a new business search."""
    try:
        await _ensure_enrichment_error_column(db)
        await _ensure_source_column(db)

        job = SearchJob(
            query=request.query,
            location=request.location,
            radius_km=request.radius_km,
            status="running",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        background_tasks.add_task(_run_search, job.id, request)
        return job
    except Exception as exc:
        logger.error("Failed to create search: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start search: {str(exc)[:200]}")


@router.get("/search", response_model=list[SearchJobResponse])
async def list_searches(db: AsyncSession = Depends(get_leadgen_db)):
    """List all search jobs."""
    try:
        result = await db.execute(select(SearchJob).order_by(SearchJob.created_at.desc()))
        return result.scalars().all()
    except Exception as exc:
        logger.error("Failed to list searches: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list searches: {str(exc)[:200]}")


@router.get("/search/{job_id}", response_model=SearchJobResponse)
async def get_search(job_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Get search job details."""
    try:
        result = await db.execute(select(SearchJob).where(SearchJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Search job not found")
        return job
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get search %d: %s", job_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get search status: {str(exc)[:200]}")


@router.get("/search/{job_id}/status")
async def get_search_status(job_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Get detailed search job progress with status messages."""
    try:
        result = await db.execute(select(SearchJob).where(SearchJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Search job not found")

        # Count lead statuses for this job
        total_leads = (await db.execute(
            select(func.count(Lead.id)).where(Lead.search_job_id == job_id)
        )).scalar() or 0

        enriched = (await db.execute(
            select(func.count(Lead.id)).where(
                Lead.search_job_id == job_id,
                Lead.enrichment_status == "enriched",
            )
        )).scalar() or 0

        pending = (await db.execute(
            select(func.count(Lead.id)).where(
                Lead.search_job_id == job_id,
                Lead.enrichment_status == "pending",
            )
        )).scalar() or 0

        failed = (await db.execute(
            select(func.count(Lead.id)).where(
                Lead.search_job_id == job_id,
                Lead.enrichment_status == "failed",
            )
        )).scalar() or 0

        # Build human-readable status message
        if job.status == "running":
            if total_leads == 0:
                message = f"Searching for {job.query} in {job.location}..."
            else:
                message = f"Found {total_leads} businesses, enriching... ({enriched}/{total_leads} done)"
        elif job.status == "complete":
            parts = [f"Found {job.total_found} businesses"]
            if enriched > 0:
                parts.append(f"{enriched} enriched")
            if pending > 0:
                parts.append(f"{pending} enriching")
            if failed > 0:
                parts.append(f"{failed} failed")
            message = " · ".join(parts)
        elif job.status == "failed":
            message = f"Search failed: {job.error_message or 'Unknown error'}"
        else:
            message = f"Status: {job.status}"

        # Age info
        now = datetime.utcnow()
        created = job.created_at.replace(tzinfo=None) if job.created_at and job.created_at.tzinfo else job.created_at
        age_days = (now - created).days if created else 0

        return {
            "job_id": job.id,
            "status": job.status,
            "query": job.query,
            "location": job.location,
            "total_found": job.total_found,
            "total_leads": total_leads,
            "enriched": enriched,
            "pending": pending,
            "failed": failed,
            "error_message": job.error_message,
            "message": message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "age_days": age_days,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get search status %d: %s", job_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get search status: {str(exc)[:200]}")


# ---------------------------------------------------------------------------
# Lead detail endpoints
# ---------------------------------------------------------------------------

@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Get a single lead by ID."""
    try:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get lead %d: %s", lead_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load lead: {str(exc)[:200]}")


@router.post("/leads/{lead_id}/audit", response_model=WebsiteAuditResult)
async def trigger_website_audit(lead_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Trigger website audit for a lead."""
    try:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        if not lead.website:
            raise HTTPException(status_code=400, detail="Lead has no website to audit")

        audit = await audit_website(lead.website)

        lead.website_audit_score = audit.score
        lead.website_audit_grade = audit.grade
        lead.website_audit_summary = audit.summary
        lead.website_audit_top_fixes = audit.top_fixes
        lead.website_audit_date = datetime.now()
        lead.audit_status = "complete"

        await db.commit()

        return WebsiteAuditResult(
            score=audit.score,
            grade=audit.grade,
            summary=audit.summary,
            top_fixes=audit.top_fixes,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Audit failed for lead %d: %s", lead_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Website audit failed: {str(exc)[:200]}")


@router.get("/leads/{lead_id}/audit", response_model=WebsiteAuditResult)
async def get_audit_results(lead_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Get audit results for a lead."""
    try:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        if not lead.website_audit_score:
            raise HTTPException(status_code=404, detail="No audit results found for this lead")

        return WebsiteAuditResult(
            score=lead.website_audit_score,
            grade=lead.website_audit_grade or "F",
            summary=lead.website_audit_summary or "",
            top_fixes=lead.website_audit_top_fixes or [],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get audit for lead %d: %s", lead_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load audit: {str(exc)[:200]}")


# ---------------------------------------------------------------------------
# CRM / Contact Logging
# ---------------------------------------------------------------------------

@router.post("/leads/{lead_id}/contact")
async def log_contact(lead_id: int, body: ContactLogRequest, db: AsyncSession = Depends(get_leadgen_db)):
    """Log a contact attempt with a lead."""
    try:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        now = datetime.now()

        lead.contacted_by = body.contacted_by
        lead.contacted_at = now
        lead.contact_outcome = body.outcome
        lead.contact_notes = body.notes
        if body.who_answered:
            lead.contact_who_answered = body.who_answered
        if body.owner_name:
            lead.contact_owner_name = body.owner_name
        if body.economic_buyer:
            lead.contact_economic_buyer = body.economic_buyer
        if body.champion:
            lead.contact_champion = body.champion

        history = lead.contact_history or []
        history.append({
            "date": now.isoformat(),
            "by": body.contacted_by,
            "outcome": body.outcome,
            "notes": body.notes or "",
            "who_answered": body.who_answered or "",
        })
        lead.contact_history = history

        if body.outcome == "won":
            lead.outreach_status = "won"
        elif body.outcome == "lost":
            lead.outreach_status = "lost"
        elif body.outcome in ("follow_up", "callback"):
            lead.outreach_status = "in_progress"
        else:
            lead.outreach_status = "contacted"

        await db.commit()
        return {"status": "logged", "lead_id": lead_id, "outcome": body.outcome}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to log contact for lead %d: %s", lead_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to log contact: {str(exc)[:200]}")


@router.post("/leads/enrich-pending")
async def enrich_pending_leads(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_leadgen_db)):
    """Trigger enrichment for all pending leads across all jobs."""
    try:
        result = await db.execute(
            select(func.count(Lead.id)).where(Lead.enrichment_status == "pending")
        )
        pending_count = result.scalar() or 0

        if pending_count == 0:
            return {"status": "nothing_to_enrich", "pending": 0}

        jobs = await db.execute(
            select(Lead.search_job_id).where(Lead.enrichment_status == "pending").distinct()
        )
        job_ids = [row[0] for row in jobs.all() if row[0] is not None]

        for job_id in job_ids:
            background_tasks.add_task(_run_enrichment, job_id)

        return {"status": "started", "pending": pending_count, "jobs": len(job_ids)}
    except Exception as exc:
        logger.error("Failed to trigger enrichment: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment trigger failed: {str(exc)[:200]}")


@router.post("/leads/rescore")
async def rescore_all_leads(db: AsyncSession = Depends(get_leadgen_db)):
    """Rescore all leads — fixes leads imported before scoring was wired up."""
    try:
        result = await db.execute(select(Lead))
        leads = result.scalars().all()
        updated = 0
        for lead in leads:
            score, tier = score_lead(lead)
            if lead.lead_score != score or lead.lead_tier != tier:
                lead.lead_score = score
                lead.lead_tier = tier
                updated += 1
        await db.commit()
        return {"status": "rescored", "total": len(leads), "updated": updated}
    except Exception as exc:
        logger.error("Failed to rescore leads: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rescore failed: {str(exc)[:200]}")


@router.get("/contacts")
async def list_contacts(
    outcome: str | None = None,
    contacted_by: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """List all contacted leads (CRM history view)."""
    try:
        query = select(Lead).where(Lead.outreach_status != "none")

        if outcome:
            query = query.where(Lead.contact_outcome == outcome)
        if contacted_by:
            query = query.where(Lead.contacted_by.ilike(f"%{contacted_by}%"))

        query = query.order_by(Lead.contacted_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        leads = result.scalars().all()

        return [LeadResponse.model_validate(lead) for lead in leads]
    except Exception as exc:
        logger.error("Failed to list contacts: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list contacts: {str(exc)[:200]}")
