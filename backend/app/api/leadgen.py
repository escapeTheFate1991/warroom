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

from app.db.leadgen_db import get_leadgen_db
from app.models.lead import Lead, SearchJob
from app.services.leadgen.google_places import search_places
from app.services.leadgen.enrichment import enrich_job
from app.services.leadgen.website_auditor import audit_website
from app.api.leadgen_schemas import (
    LeadResponse, LeadUpdate, StatsResponse, SearchRequest, 
    SearchJobResponse, WebsiteAuditResult
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_search(job_id: int, request: SearchRequest, db: AsyncSession):
    """Background task: search Google Places and insert leads."""
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
            )
            db.add(lead)

        await db.execute(
            select(SearchJob).where(SearchJob.id == job_id)
        )
        job = (await db.execute(select(SearchJob).where(SearchJob.id == job_id))).scalar_one()
        job.total_found = len(places)
        job.status = "complete"
        await db.commit()

        # Auto-start enrichment
        await enrich_job(job_id, db)

    except Exception as exc:
        logger.error("Search job %d failed: %s", job_id, exc)
        job = (await db.execute(select(SearchJob).where(SearchJob.id == job_id))).scalar_one_or_none()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            await db.commit()


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
    limit: int = Query(default=100, le=500),
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

    background_tasks.add_task(_run_search, job.id, request, db)
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