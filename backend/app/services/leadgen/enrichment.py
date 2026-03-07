"""Enrichment pipeline — crawl websites, score leads, update DB."""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, SearchJob
from app.services.leadgen.website_crawler import crawl_website
from app.services.leadgen.lead_scorer import score_lead
from app.services.leadgen.review_scraper import scrape_yelp_reviews, fetch_google_reviews
from app.services.leadgen.review_analyzer import analyze_reviews
from app.services.notify import send_notification

logger = logging.getLogger(__name__)


async def enrich_lead(lead_id: int, db: AsyncSession) -> None:
    """Enrich a single lead with website data and scoring."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        return

    # Skip if already enriched
    if lead.enrichment_status == "enriched":
        logger.debug("Lead %d already enriched, skipping", lead_id)
        return

    # Check if we already have enriched data for this google_place_id
    if lead.google_place_id:
        existing = await db.execute(
            select(Lead).where(
                Lead.google_place_id == lead.google_place_id,
                Lead.enrichment_status == "enriched",
                Lead.id != lead_id
            ).limit(1)
        )
        existing_lead = existing.scalar_one_or_none()
        if existing_lead:
            logger.debug("Found existing enriched lead for place %s, copying data", lead.google_place_id)
            # Copy enrichment data from existing lead
            lead.enrichment_status = "enriched"
            lead.has_website = existing_lead.has_website
            lead.website_status = existing_lead.website_status
            lead.website_platform = existing_lead.website_platform
            lead.emails = existing_lead.emails
            lead.website_phones = existing_lead.website_phones
            lead.facebook_url = existing_lead.facebook_url
            lead.instagram_url = existing_lead.instagram_url
            lead.linkedin_url = existing_lead.linkedin_url
            lead.twitter_url = existing_lead.twitter_url
            lead.tiktok_url = existing_lead.tiktok_url
            lead.youtube_url = existing_lead.youtube_url
            lead.yelp_url = existing_lead.yelp_url
            lead.audit_lite_flags = existing_lead.audit_lite_flags
            lead.yelp_rating = existing_lead.yelp_rating
            lead.yelp_reviews_count = existing_lead.yelp_reviews_count
            lead.review_highlights = existing_lead.review_highlights
            lead.review_sentiment_score = existing_lead.review_sentiment_score
            lead.review_pain_points = existing_lead.review_pain_points
            lead.review_opportunity_flags = existing_lead.review_opportunity_flags
            lead.reviews_scraped_at = existing_lead.reviews_scraped_at
            lead.website_audit_score = existing_lead.website_audit_score
            lead.website_audit_grade = existing_lead.website_audit_grade
            lead.website_audit_summary = existing_lead.website_audit_summary
            lead.website_audit_top_fixes = existing_lead.website_audit_top_fixes
            lead.website_audit_date = existing_lead.website_audit_date
            lead.audit_status = existing_lead.audit_status
            score, tier = score_lead(lead)
            lead.lead_score = score
            lead.lead_tier = tier
            await db.commit()
            return

    # Check if audit is recent enough (within 30 days)
    if (lead.website_audit_date and 
        datetime.now() - lead.website_audit_date < timedelta(days=30)):
        logger.debug("Lead %d has recent audit, skipping crawl", lead_id)
        lead.enrichment_status = "enriched"
        score, tier = score_lead(lead)
        lead.lead_score = score
        lead.lead_tier = tier
        await db.commit()
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
    # Store scraped phones — merge with Google phone if different
    if crawl.phones:
        lead.website_phones = crawl.phones
    lead.facebook_url = crawl.facebook
    lead.instagram_url = crawl.instagram
    lead.linkedin_url = crawl.linkedin
    lead.twitter_url = crawl.twitter
    lead.tiktok_url = crawl.tiktok
    lead.youtube_url = crawl.youtube
    lead.yelp_url = crawl.yelp
    lead.enrichment_status = "failed" if crawl.error else "enriched"

    # Quick audit lite — surface level signals from the crawl
    audit_flags = []
    if crawl.platform and crawl.platform != "custom":
        audit_flags.append(f"Built on {crawl.platform.title()}")
    if not crawl.emails:
        audit_flags.append("No email found on website")
    if not crawl.phones:
        audit_flags.append("No phone found on website")
    has_ssl = lead.website.startswith("https://") if lead.website else False
    if not has_ssl:
        audit_flags.append("No SSL (HTTP only)")
    social_count = sum(1 for x in [crawl.facebook, crawl.instagram, crawl.linkedin, crawl.twitter] if x)
    if social_count == 0:
        audit_flags.append("No social media links")
    elif social_count < 2:
        audit_flags.append("Minimal social presence")
    lead.audit_lite_flags = audit_flags

    # --- Review scraping & analysis ---
    try:
        await _enrich_reviews(lead)
    except Exception as exc:
        logger.warning("Review enrichment failed for lead %d: %s", lead_id, exc)

    score, tier = score_lead(lead)
    lead.lead_score = score
    lead.lead_tier = tier
    lead.website_audit_date = datetime.now()  # Track when we performed enrichment

    await db.commit()

    # Notification: hot lead found (score >= 60)
    if score >= 60:
        await send_notification(
            type="alert",
            title="🔥 Hot Lead Found",
            message=f"{lead.business_name} — Score {score}, {tier}",
            data={"lead_id": lead.id, "score": score, "link": "/leadgen"},
        )


async def enrich_job(job_id: int, db: AsyncSession) -> None:
    """Enrich all pending leads in a search job.
    
    Each lead gets its own session to avoid SQLAlchemy concurrent-access issues.
    Only leads WITH websites get crawled; no-website leads are scored immediately.
    """
    from app.db.leadgen_db import leadgen_session

    result = await db.execute(
        select(Lead.id, Lead.has_website)
        .where(Lead.search_job_id == job_id, Lead.enrichment_status == "pending")
        .order_by(Lead.id)
    )
    lead_rows = result.all()

    await db.execute(
        update(SearchJob).where(SearchJob.id == job_id).values(status="running")
    )
    await db.commit()

    enriched = 0
    semaphore = asyncio.Semaphore(3)  # Limit concurrency for website crawls

    async def _enrich_one(lead_id: int):
        nonlocal enriched
        async with semaphore:
            # Each task gets its own DB session — prevents shared-session hangs
            async with leadgen_session() as task_db:
                try:
                    await enrich_lead(lead_id, task_db)
                except Exception as exc:
                    logger.error("Failed to enrich lead %d: %s", lead_id, exc)
            enriched += 1

    tasks = [_enrich_one(row[0]) for row in lead_rows]
    await asyncio.gather(*tasks, return_exceptions=True)

    await db.execute(
        update(SearchJob)
        .where(SearchJob.id == job_id)
        .values(status="complete", enriched_count=enriched)
    )
    await db.commit()
    logger.info("Enrichment complete for job %d: %d leads", job_id, enriched)


async def _enrich_reviews(lead: Lead) -> None:
    """Scrape Yelp + Google reviews, analyze, and populate review columns."""
    all_review_texts: list[str] = []

    # Yelp reviews
    if lead.business_name and lead.city:
        yelp_result = await scrape_yelp_reviews(
            lead.business_name,
            lead.city,
            lead.state or "",
        )
        if yelp_result.yelp_url:
            lead.yelp_url = lead.yelp_url or yelp_result.yelp_url
        if yelp_result.yelp_rating:
            lead.yelp_rating = yelp_result.yelp_rating
        if yelp_result.yelp_reviews_count:
            lead.yelp_reviews_count = yelp_result.yelp_reviews_count
        all_review_texts.extend(r.text for r in yelp_result.reviews if r.text)

    # Google reviews (if we have a place_id)
    if lead.google_place_id:
        google_result = await fetch_google_reviews(lead.google_place_id)
        all_review_texts.extend(r.text for r in google_result.reviews if r.text)

    # Analyze combined reviews
    if all_review_texts:
        analysis = analyze_reviews(all_review_texts)
        lead.review_sentiment_score = analysis.sentiment_score
        lead.review_pain_points = analysis.pain_points
        lead.review_opportunity_flags = analysis.opportunity_flags
        lead.review_highlights = analysis.highlight_quotes
        lead.reviews_scraped_at = datetime.now()
        logger.info(
            "Lead %d: %d reviews analyzed, sentiment=%.2f, flags=%s",
            lead.id, len(all_review_texts),
            analysis.sentiment_score, analysis.opportunity_flags,
        )