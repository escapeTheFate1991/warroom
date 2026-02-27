"""LeadGen API — Business discovery, enrichment, and website auditing."""

import csv
import io
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, case, update
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


async def _run_search(job_id: int, request: SearchRequest):
    """Background task: search Google Places, insert leads with pending enrichment."""
    async with leadgen_session() as db:
        try:
            places = await search_places(request.query, request.location, request.max_results)

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
                    enrichment_status="pending",  # Mark for background enrichment
                )
                db.add(lead)

            # Complete the search job immediately - leads are available
            job = (await db.execute(select(SearchJob).where(SearchJob.id == job_id))).scalar_one()
            job.total_found = len(places)
            job.status = "complete"  # Search complete, enrichment runs separately
            await db.commit()
            
            logger.info("Search complete for job %d (%d leads), starting background enrichment", job_id, len(places))

        except Exception as exc:
            logger.error("Search job %d failed: %s", job_id, exc, exc_info=True)
            job = (await db.execute(select(SearchJob).where(SearchJob.id == job_id))).scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                await db.commit()


async def _run_enrichment(job_id: int):
    """Background task: enrich pending leads for a search job."""
    async with leadgen_session() as db:
        try:
            logger.info("Starting enrichment for job %d", job_id)
            await enrich_job(job_id, db)
            logger.info("Enrichment complete for job %d", job_id)
        except Exception as exc:
            logger.error("Enrichment job %d failed: %s", job_id, exc, exc_info=True)


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


@router.get("/leads/stats", response_model=StatsResponse)
async def get_stats(search_job_id: int | None = None, db: AsyncSession = Depends(get_leadgen_db)):
    """Get lead statistics."""
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


@router.get("/leads/export")
async def export_leads(
    search_job_id: int | None = None,
    tier: str | None = None,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Export leads to CSV."""
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


@router.post("/search", response_model=SearchJobResponse)
async def create_search(request: SearchRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_leadgen_db)):
    """Start a new business search."""
    job = SearchJob(
        query=request.query,
        location=request.location,
        radius_km=request.radius_km,
        status="running",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Run search first (fast, returns leads immediately)
    background_tasks.add_task(_run_search, job.id, request)
    # Run enrichment separately (slow, updates leads in background)
    background_tasks.add_task(_run_enrichment, job.id)
    return job


@router.get("/search", response_model=list[SearchJobResponse])
async def list_searches(db: AsyncSession = Depends(get_leadgen_db)):
    """List all search jobs."""
    result = await db.execute(select(SearchJob).order_by(SearchJob.created_at.desc()))
    return result.scalars().all()


@router.get("/search/{job_id}", response_model=SearchJobResponse)
async def get_search(job_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Get search job details."""
    result = await db.execute(select(SearchJob).where(SearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Search job not found")
    return job


@router.post("/leads/{lead_id}/audit", response_model=WebsiteAuditResult)
async def trigger_website_audit(lead_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Trigger website audit for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.website:
        raise HTTPException(status_code=400, detail="Lead has no website")
    
    # Run audit
    audit = await audit_website(lead.website)
    
    # Update lead with audit results
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
        top_fixes=audit.top_fixes
    )


@router.get("/leads/{lead_id}/audit", response_model=WebsiteAuditResult)
async def get_audit_results(lead_id: int, db: AsyncSession = Depends(get_leadgen_db)):
    """Get audit results for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.website_audit_score:
        raise HTTPException(status_code=404, detail="No audit results found")
    
    return WebsiteAuditResult(
        score=lead.website_audit_score,
        grade=lead.website_audit_grade or "F",
        summary=lead.website_audit_summary or "",
        top_fixes=lead.website_audit_top_fixes or []
    )


# --- CRM / Contact Logging ---

@router.post("/leads/{lead_id}/contact")
async def log_contact(lead_id: int, body: ContactLogRequest, db: AsyncSession = Depends(get_leadgen_db)):
    """Log a contact attempt with a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = datetime.now()

    # Update current contact info
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

    # Append to contact history
    history = lead.contact_history or []
    history.append({
        "date": now.isoformat(),
        "by": body.contacted_by,
        "outcome": body.outcome,
        "notes": body.notes or "",
        "who_answered": body.who_answered or "",
    })
    lead.contact_history = history

    # Update outreach status
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


@router.post("/leads/rescore")
async def rescore_all_leads(db: AsyncSession = Depends(get_leadgen_db)):
    """Rescore all leads — fixes leads imported before scoring was wired up."""
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


@router.get("/contacts")
async def list_contacts(
    outcome: str | None = None,
    contacted_by: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """List all contacted leads (CRM history view)."""
    query = select(Lead).where(Lead.outreach_status != "none")
    
    if outcome:
        query = query.where(Lead.contact_outcome == outcome)
    if contacted_by:
        query = query.where(Lead.contacted_by.ilike(f"%{contacted_by}%"))
    
    query = query.order_by(Lead.contacted_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    leads = result.scalars().all()

    return [LeadResponse.model_validate(lead) for lead in leads]