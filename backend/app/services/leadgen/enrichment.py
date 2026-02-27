"""Enrichment pipeline — crawl websites, score leads, update DB."""

import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, SearchJob
from app.services.leadgen.website_crawler import crawl_website
from app.services.leadgen.lead_scorer import score_lead

logger = logging.getLogger(__name__)


async def enrich_lead(lead_id: int, db: AsyncSession) -> None:
    """Enrich a single lead with website data and scoring."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        return

    lead.enrichment_status = "crawling"
    await db.commit()

    if not lead.website:
        lead.has_website = False
        lead.enrichment_status = "enriched"
        lead.audit_status = "no_website"
        score, tier = score_lead(lead)
        lead.lead_score = score
        lead.lead_tier = tier
        await db.commit()
        return

    lead.has_website = True
    crawl = await crawl_website(lead.website)

    lead.website_status = crawl.status_code
    lead.website_platform = crawl.platform
    lead.emails = crawl.emails
    lead.facebook_url = crawl.facebook
    lead.instagram_url = crawl.instagram
    lead.linkedin_url = crawl.linkedin
    lead.twitter_url = crawl.twitter
    lead.tiktok_url = crawl.tiktok
    lead.youtube_url = crawl.youtube
    lead.yelp_url = crawl.yelp
    lead.enrichment_status = "failed" if crawl.error else "enriched"

    score, tier = score_lead(lead)
    lead.lead_score = score
    lead.lead_tier = tier

    await db.commit()


async def enrich_job(job_id: int, db: AsyncSession) -> None:
    """Enrich all pending leads in a search job."""
    result = await db.execute(
        select(Lead)
        .where(Lead.search_job_id == job_id, Lead.enrichment_status == "pending")
        .order_by(Lead.id)
    )
    leads = result.scalars().all()

    await db.execute(
        update(SearchJob).where(SearchJob.id == job_id).values(status="running")
    )
    await db.commit()

    enriched = 0
    semaphore = asyncio.Semaphore(3)  # Limit concurrency

    async def _enrich_one(lead_id: int):
        nonlocal enriched
        async with semaphore:
            await enrich_lead(lead_id, db)
            enriched += 1
            if enriched % 5 == 0:
                await db.execute(
                    update(SearchJob)
                    .where(SearchJob.id == job_id)
                    .values(enriched_count=enriched)
                )
                await db.commit()

    tasks = [_enrich_one(lead.id) for lead in leads]
    await asyncio.gather(*tasks, return_exceptions=True)

    await db.execute(
        update(SearchJob)
        .where(SearchJob.id == job_id)
        .values(status="complete", enriched_count=enriched)
    )
    await db.commit()
    logger.info("Enrichment complete for job %d: %d leads", job_id, enriched)