"""Scraper API — our own data collection pipeline.

No paid services. No third-party APIs for competitor data.
Hits public endpoints directly and stores results in our DB.

Endpoints:
  POST /api/scraper/instagram/{handle}     — Scrape single competitor
  POST /api/scraper/instagram/bulk         — Scrape all tracked IG competitors
  POST /api/scraper/instagram/sync         — Scrape + update competitor records + cache posts
  GET  /api/scraper/status                 — Last scrape times, error counts
"""

import asyncio
import logging
import re
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db, crm_session
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.competitor import Competitor
# Removed direct scraper imports - now using HTTP calls to scraper service

logger = logging.getLogger(__name__)

router = APIRouter()

# Service URLs configuration
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:18797")

# Pydantic models for scraper service responses
class ScrapedPost(BaseModel):
    shortcode: str
    post_url: str
    caption: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    media_type: str = "image"
    posted_at: Optional[datetime] = None
    is_reel: bool = False
    engagement_score: float = 0.0
    hook: str = ""
    media_url: str = ""
    thumbnail_url: str = ""

class ScrapedProfile(BaseModel):
    handle: str
    full_name: str = ""
    bio: str = ""
    followers: int = 0
    following: int = 0
    post_count: int = 0
    profile_pic_url: str = ""
    is_private: bool = False
    is_verified: bool = False
    category: str = ""
    posts: List[ScrapedPost] = []
    scraped_at: Optional[datetime] = None
    error: Optional[str] = None
    bio_links: List[Dict[str, str]] = []
    threads_handle: str = ""
    external_url: str = ""

async def scrape_profile(handle: str) -> ScrapedProfile:
    """Call scraper service to scrape a single profile."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{SCRAPER_SERVICE_URL}/scrape-profile",
                json={"handle": handle}
            )
            if response.status_code == 200:
                return ScrapedProfile(**response.json())
            else:
                logger.error(f"Scraper service error for {handle}: {response.status_code} - {response.text}")
                return ScrapedProfile(handle=handle, error=f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to call scraper service for {handle}: {e}")
        return ScrapedProfile(handle=handle, error=f"Service unavailable: {str(e)}")

async def scrape_multiple(handles: List[str], delay_range: tuple = (3, 7)) -> List[ScrapedProfile]:
    """Call scraper service to scrape multiple profiles."""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{SCRAPER_SERVICE_URL}/scrape-multiple",
                json={"handles": handles, "delay_range": delay_range}
            )
            if response.status_code == 200:
                data = response.json()
                return [ScrapedProfile(**profile_data) for profile_data in data.get("profiles", [])]
            else:
                logger.error(f"Scraper service error for multiple profiles: {response.status_code} - {response.text}")
                return [ScrapedProfile(handle=handle, error=f"HTTP {response.status_code}") for handle in handles]
    except Exception as e:
        logger.error(f"Failed to call scraper service for multiple profiles: {e}")
        return [ScrapedProfile(handle=handle, error=f"Service unavailable: {str(e)}") for handle in handles]

_instagram_sync_task: Optional[asyncio.Task] = None
_instagram_sync_result: Optional[Dict[str, Any]] = None


# ── Response Models ──────────────────────────────────────────────

class ScrapedPostResponse(BaseModel):
    shortcode: str
    post_url: str
    caption: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    media_type: str = "image"
    posted_at: Optional[datetime] = None
    is_reel: bool = False
    engagement_score: float = 0.0
    hook: str = ""


class ScrapedProfileResponse(BaseModel):
    handle: str
    full_name: str = ""
    bio: str = ""
    followers: int = 0
    following: int = 0
    post_count: int = 0
    profile_pic_url: str = ""
    is_private: bool = False
    is_verified: bool = False
    category: str = ""
    posts: List[ScrapedPostResponse] = []
    scraped_at: Optional[datetime] = None
    error: Optional[str] = None


class BulkScrapeRequest(BaseModel):
    handles: Optional[List[str]] = None  # If None, scrapes all tracked competitors
    delay_min: float = Field(default=3.0, ge=1.0, le=30.0)
    delay_max: float = Field(default=7.0, ge=2.0, le=60.0)


class BulkScrapeResponse(BaseModel):
    total: int
    success: int
    failed: int
    profiles: List[ScrapedProfileResponse]
    posts_saved: int = 0
    accepted: bool = False
    message: Optional[str] = None


class ScrapeStatusResponse(BaseModel):
    total_competitors: int
    total_cached_posts: int
    last_scrape: Optional[datetime] = None
    competitors: List[Dict[str, Any]] = []
    sync_running: bool = False
    sync_result: Optional[Dict[str, Any]] = None


# ── Helpers ──────────────────────────────────────────────────────

def calculate_competitor_engagement_score(
    likes: int,
    comments: int,
    shares: int = 0,
    platform: Optional[str] = None,
) -> float:
    """Calculate competitor engagement from stored interaction counts."""
    total = (likes or 0) + (comments or 0)
    if platform and platform.lower() != "instagram":
        total += shares or 0
    return float(total)

def _profile_to_response(profile: ScrapedProfile) -> ScrapedProfileResponse:
    """Convert internal ScrapedProfile to API response."""
    return ScrapedProfileResponse(
        handle=profile.handle,
        full_name=profile.full_name,
        bio=profile.bio,
        followers=profile.followers,
        following=profile.following,
        post_count=profile.post_count,
        profile_pic_url=profile.profile_pic_url,
        is_private=profile.is_private,
        is_verified=profile.is_verified,
        category=profile.category,
        posts=[
            ScrapedPostResponse(
                shortcode=p.shortcode,
                post_url=p.post_url,
                caption=p.caption,
                likes=p.likes,
                comments=p.comments,
                views=p.views,
                media_type=p.media_type,
                posted_at=p.posted_at,
                is_reel=p.is_reel,
                engagement_score=calculate_competitor_engagement_score(
                    p.likes,
                    p.comments,
                    p.views,
                    platform="instagram",
                ),
                hook=p.hook,
            )
            for p in profile.posts
        ],
        scraped_at=profile.scraped_at,
        error=profile.error,
    )


def _normalize_handle(handle: str) -> str:
    """Normalize a social handle for matching competitor records."""
    return handle.strip().lstrip("@").lower()


def _extract_business_intel(bio: str, full_name: str) -> dict:
    """Extract structured business intelligence from bio text.
    
    Parses job titles, companies, expertise areas, and business signals
    from Instagram bio descriptions.
    """
    intel = {}
    if not bio:
        return intel
    
    # Job titles / roles
    role_patterns = [
        r"(?:^|\W)(CEO|CTO|COO|CFO|CMO|VP|Director|Manager|Founder|Co-Founder|"
        r"Engineer|Developer|Designer|Consultant|Coach|Mentor|Creator|Strategist|"
        r"Entrepreneur|Author|Speaker|Advisor|Partner|Freelancer|Artist|Photographer|"
        r"Producer|Editor|Analyst|Architect|Instructor|Teacher|Professor|Doctor|"
        r"Therapist|Attorney|Lawyer|Realtor|Agent|Broker|Trainer|Chef|Stylist)(?:\W|$)",
    ]
    roles = set()
    for pattern in role_patterns:
        matches = re.findall(pattern, bio, re.IGNORECASE)
        roles.update(m.strip() for m in matches)
    
    # "Ex [Role] at [Company]" or "[Role] at [Company]" patterns
    title_at_company = re.findall(
        r"(?:ex |former )?([\w\s]+?)\s+(?:at|@)\s+([\w\s&.]+?)(?:[,.|•\n]|$)",
        bio, re.IGNORECASE
    )
    
    positions = []
    for title, company in title_at_company:
        title = title.strip()
        company = company.strip()
        if len(title) < 50 and len(company) < 50:
            positions.append({"title": title, "company": company})
    
    # "Ex [Something]" pattern (like "Ex Founding Engineer, Ex Startup CTO")
    ex_roles = re.findall(r"[Ee]x\s+([\w\s]+?)(?:[,.|•\n]|$)", bio)
    for role in ex_roles:
        role = role.strip()
        if len(role) < 50 and role not in [p.get("title") for p in positions]:
            positions.append({"title": f"Ex {role}", "company": ""})
    
    if positions:
        intel["positions"] = positions
    if roles:
        intel["roles"] = sorted(roles)
    
    # Years of experience
    exp_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(\w+)", bio, re.IGNORECASE)
    if exp_match:
        intel["experience"] = f"{exp_match.group(1)}+ years of {exp_match.group(2)}"
    
    # What they do / offer (helping, teaching, building patterns)
    offering_match = re.search(
        r"(?:helping|teaching|coaching|building|creating|making|growing|scaling)\s+(.+?)(?:[.|•\n]|$)",
        bio, re.IGNORECASE
    )
    if offering_match:
        intel["offering"] = offering_match.group(1).strip()[:200]
    
    # DM/booking signals
    if re.search(r"(?:DM|book|schedule|consult|hire me|work with me|inquir)", bio, re.IGNORECASE):
        intel["accepts_inquiries"] = True
    
    if full_name:
        intel["full_name"] = full_name
    
    return intel


async def _save_profile_to_competitor(
    db: AsyncSession, competitor: Competitor, profile: ScrapedProfile
) -> None:
    """Update a Competitor record with scraped profile data."""
    if profile.error or profile.is_private:
        return
    
    # Only update fields if we got real data (Instagram login wall returns
    # profile stats via GraphQL but zero posts — don't regress stored values)
    if profile.followers:
        competitor.followers = profile.followers
    if profile.following:
        competitor.following = profile.following
    if profile.post_count:
        competitor.post_count = profile.post_count
    if profile.bio:
        competitor.bio = profile.bio
    if profile.profile_pic_url:
        competitor.profile_image_url = profile.profile_pic_url
    
    # Dossier enrichment — only on every 5th sync or first sync (dossier rarely changes)
    sync_count = (competitor.dossier_data or {}).get("_sync_count", 0) + 1
    dossier = competitor.dossier_data or {}
    dossier["_sync_count"] = sync_count
    
    if sync_count == 1 or sync_count % 5 == 0:
        if profile.bio_links:
            dossier["bio_links"] = profile.bio_links
        if profile.threads_handle:
            dossier["threads_handle"] = profile.threads_handle
        if profile.external_url:
            dossier["external_url"] = profile.external_url
        if profile.full_name:
            dossier["full_name"] = profile.full_name
        if profile.is_verified:
            dossier["is_verified"] = True
        if profile.category:
            dossier["category"] = profile.category
        bio_intel = _extract_business_intel(profile.bio or "", profile.full_name or "")
        if bio_intel:
            dossier["business_intel"] = bio_intel
    
    competitor.dossier_data = dossier
    
    competitor.is_auto_populated = True
    competitor.last_auto_sync = datetime.now()
    competitor.updated_at = datetime.now()
    
    # Calculate posting frequency from post timestamps
    if profile.posts:
        timestamps = [p.posted_at for p in profile.posts if p.posted_at]
        if len(timestamps) >= 2:
            timestamps.sort(reverse=True)
            days_span = (timestamps[0] - timestamps[-1]).days or 1
            freq = len(timestamps) / (days_span / 7)
            competitor.posting_frequency = f"{freq:.1f} posts/week"
        
        # Calculate avg engagement rate
        total_eng = sum(
            calculate_competitor_engagement_score(
                p.likes,
                p.comments,
                p.views,
                platform="instagram",
            )
            for p in profile.posts
        )
        avg_eng = total_eng / len(profile.posts)
        if profile.followers > 0:
            competitor.avg_engagement_rate = round(
                (avg_eng / profile.followers) * 100, 2
            )
        else:
            competitor.avg_engagement_rate = 0.0
    else:
        # Don't zero out engagement rate if we simply couldn't scrape posts
        # (e.g. Instagram login wall). Keep the previously stored value.
        pass


async def _save_posts_to_cache(
    db: AsyncSession, competitor_id: int, platform: str, posts: List[ScrapedPost], org_id: int
) -> int:
    """Save scraped posts to competitor_posts cache table using UPSERT.
    
    Preserves transcript and comments_data on existing posts.
    Only inserts new posts or updates engagement metrics on existing ones.
    """
    if not posts:
        return 0

    try:
        saved = 0
        for post in posts:
            score = calculate_competitor_engagement_score(
                post.likes, post.comments, post.views, platform=platform,
            )
            # UPSERT: insert if new shortcode, update metrics if exists
            # Never touch transcript or comments_data — those are enriched separately
            if post.shortcode:
                upsert_key = "shortcode"
                upsert_val = post.shortcode
            else:
                upsert_key = "post_url"
                upsert_val = post.post_url

            # Check if post exists
            existing = await db.execute(
                text(f"SELECT id FROM crm.competitor_posts WHERE competitor_id = :cid AND {upsert_key} = :key AND org_id = :org_id LIMIT 1"),
                {"cid": competitor_id, "key": upsert_val, "org_id": org_id},
            )
            row = existing.fetchone()

            if row:
                # Get existing post details to check for expired URLs
                existing_post = await db.execute(
                    text("SELECT media_url, thumbnail_url, posted_at FROM crm.competitor_posts WHERE id = :id"),
                    {"id": row[0]}
                )
                existing_data = existing_post.fetchone()
                
                # Determine if we should force refresh URLs
                force_refresh_urls = False
                if existing_data:
                    existing_media_url = existing_data[0] or ""
                    existing_posted_at = existing_data[2]
                    
                    # Check if this is an Instagram CDN URL that's older than 24 hours
                    if ("scontent" in existing_media_url and 
                        existing_posted_at and 
                        (datetime.now() - existing_posted_at.replace(tzinfo=None)).days >= 1):
                        force_refresh_urls = True
                
                # Choose URL update strategy
                if force_refresh_urls and post.media_url:
                    # Force refresh: use new URLs even if they're different
                    media_url_update = post.media_url
                    thumbnail_url_update = post.thumbnail_url
                else:
                    # Normal update: only update if new URL is not empty
                    media_url_update = post.media_url if post.media_url else existing_data[0] if existing_data else ""
                    thumbnail_url_update = post.thumbnail_url if post.thumbnail_url else existing_data[1] if existing_data else ""
                
                # Update engagement metrics and URLs
                await db.execute(
                    text("""
                        UPDATE crm.competitor_posts SET
                            likes = :likes, comments = :comments, shares = :shares,
                            engagement_score = :score, post_text = :text, hook = :hook,
                            media_type = :media_type, media_url = :media_url,
                            thumbnail_url = :thumbnail_url,
                            shortcode = COALESCE(NULLIF(:shortcode, ''), shortcode),
                            fetched_at = NOW()
                        WHERE id = :id AND org_id = :org_id
                    """),
                    {
                        "id": row[0],
                        "likes": post.likes,
                        "comments": post.comments,
                        "shares": post.views,
                        "score": score,
                        "text": post.caption,
                        "hook": post.hook,
                        "media_type": post.media_type,
                        "media_url": media_url_update,
                        "thumbnail_url": thumbnail_url_update,
                        "shortcode": post.shortcode,
                        "org_id": org_id,
                    },
                )
            else:
                # New post — insert
                await db.execute(
                    text("""
                        INSERT INTO crm.competitor_posts 
                        (competitor_id, platform, post_text, likes, comments, shares,
                         engagement_score, hook, post_url, posted_at, fetched_at,
                         media_type, media_url, thumbnail_url, shortcode, org_id)
                        VALUES (:cid, :platform, :text, :likes, :comments, :shares,
                                :score, :hook, :url, :posted_at, NOW(),
                                :media_type, :media_url, :thumbnail_url, :shortcode, :org_id)
                    """),
                    {
                        "cid": competitor_id,
                        "platform": platform,
                        "text": post.caption,
                        "likes": post.likes,
                        "comments": post.comments,
                        "shares": post.views,
                        "media_type": post.media_type,
                        "media_url": post.media_url,
                        "thumbnail_url": post.thumbnail_url,
                        "shortcode": post.shortcode,
                        "score": score,
                        "hook": post.hook,
                        "url": post.post_url,
                        "posted_at": post.posted_at,
                        "org_id": org_id,
                    },
                )
                saved += 1

        return saved
    except SQLAlchemyError as exc:
        logger.warning(
            "Failed to cache posts for competitor %s on %s: %s",
            competitor_id, platform, exc,
        )
        return 0


async def _competitor_posts_cache_available(db: AsyncSession) -> bool:
    """Return whether the competitor post cache table is available."""
    try:
        result = await db.execute(text("SELECT to_regclass('crm.competitor_posts')"))
        return bool(result.scalar())
    except SQLAlchemyError as exc:
        logger.warning("Failed to check competitor_posts cache table: %s", exc)
        return False


def _instagram_sync_running() -> bool:
    """Return whether an Instagram sync background task is active."""
    return _instagram_sync_task is not None and not _instagram_sync_task.done()


async def _load_instagram_competitors(db: AsyncSession, org_id: int) -> List[Competitor]:
    """Load Instagram competitors that are enabled for auto sync."""
    result = await db.execute(
        select(Competitor)
        .where(Competitor.platform == "instagram")
        .where(Competitor.auto_sync_enabled == True)
        .where(Competitor.org_id == org_id)
    )
    return result.scalars().all()


async def sync_instagram_competitor(
    db: AsyncSession,
    competitor: Competitor,
    org_id: int,
    cache_available: Optional[bool] = None,
) -> Dict[str, Any]:
    """Scrape and persist a single Instagram competitor without committing."""
    handle = competitor.handle.strip().lstrip("@")
    profile = await scrape_profile(handle)

    if profile.error:
        return {
            "success": False,
            "error": profile.error,
            "posts_saved": 0,
            "profile": profile,
        }

    if cache_available is None:
        cache_available = await _competitor_posts_cache_available(db)
        if not cache_available:
            logger.warning(
                "crm.competitor_posts table is unavailable; scraper sync will skip post caching"
            )

    await _save_profile_to_competitor(db, competitor, profile)

    posts_saved = 0
    if cache_available:
        posts_saved = await _save_posts_to_cache(
            db, competitor.id, "instagram", profile.posts, org_id
        )

    return {
        "success": True,
        "error": None,
        "posts_saved": posts_saved,
        "profile": profile,
    }


async def sync_instagram_competitor_batch(
    db: AsyncSession,
    competitors: List[Competitor],
    org_id: int,
) -> BulkScrapeResponse:
    """Scrape and persist a batch of Instagram competitors without committing."""
    if not competitors:
        raise HTTPException(status_code=404, detail="No Instagram competitors to sync")

    cache_available = await _competitor_posts_cache_available(db)
    if not cache_available:
        logger.warning(
            "crm.competitor_posts table is unavailable; scraper sync will skip post caching"
        )

    handles = [c.handle.strip().lstrip("@") for c in competitors]
    handle_to_competitor = {_normalize_handle(c.handle): c for c in competitors}

    profiles = await scrape_multiple(handles, delay_range=(3, 7))

    success = 0
    failed = 0
    total_posts_saved = 0
    responses = []

    for profile in profiles:
        if profile.error:
            failed += 1
        else:
            success += 1

            competitor = handle_to_competitor.get(_normalize_handle(profile.handle))
            if competitor:
                await _save_profile_to_competitor(db, competitor, profile)
                if cache_available:
                    posts_saved = await _save_posts_to_cache(
                        db, competitor.id, "instagram", profile.posts, org_id
                    )
                    total_posts_saved += posts_saved

        responses.append(_profile_to_response(profile))

    return BulkScrapeResponse(
        total=len(profiles),
        success=success,
        failed=failed,
        profiles=responses,
        posts_saved=total_posts_saved,
    )


async def _execute_instagram_sync(db: AsyncSession, org_id: int) -> BulkScrapeResponse:
    """Run the full Instagram sync and return the API response payload."""
    competitors = await _load_instagram_competitors(db, org_id)
    return await sync_instagram_competitor_batch(db, competitors, org_id)


async def _run_instagram_sync_in_background() -> None:
    """Run the Instagram sync in a detached task so long scrapes survive proxy limits."""
    global _instagram_sync_result
    _instagram_sync_result = {"status": "running", "started_at": datetime.now().isoformat()}
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            result = await _execute_instagram_sync(db, org_id=1)
            await db.commit()
            _instagram_sync_result = {
                "status": "complete",
                "success": result.success,
                "failed": result.failed,
                "total": result.total,
                "posts_saved": result.posts_saved,
                "completed_at": datetime.now().isoformat(),
            }
            logger.info(
                "Background Instagram sync finished: %s/%s succeeded, %s posts cached",
                result.success,
                result.total,
                result.posts_saved,
            )
    except HTTPException as exc:
        _instagram_sync_result = {"status": "error", "error": exc.detail, "completed_at": datetime.now().isoformat()}
        logger.warning("Background Instagram sync skipped: %s", exc.detail)
    except Exception as exc:
        _instagram_sync_result = {"status": "error", "error": str(exc), "completed_at": datetime.now().isoformat()}
        logger.exception("Background Instagram sync failed: %s", exc)


def _empty_competitor_status(competitor: Competitor) -> Dict[str, Any]:
    """Build a scraper status row when cache data is unavailable."""
    return {
        "id": competitor.id,
        "handle": competitor.handle,
        "followers": competitor.followers,
        "post_count": competitor.post_count,
        "cached_posts": 0,
        "last_scrape": None,
        "is_populated": competitor.is_auto_populated,
        "avg_engagement_rate": float(competitor.avg_engagement_rate or 0),
    }


# ── Endpoints ────────────────────────────────────────────────────
# IMPORTANT: Static routes MUST come before parameterized /{handle} route
# or FastAPI will match "sync" as a handle.

@router.post("/scraper/instagram/sync", response_model=BulkScrapeResponse)
async def sync_all_instagram_competitors(
    request: Request,
    background: bool = False,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Scrape ALL tracked Instagram competitors, update their records, and cache posts.
    
    This is the main data collection endpoint for the Reports feature.
    """
    org_id = get_org_id(request)
    global _instagram_sync_task

    try:
        competitors = await _load_instagram_competitors(db, org_id)
        if not competitors:
            raise HTTPException(status_code=404, detail="No Instagram competitors to sync")

        if background:
            if _instagram_sync_running():
                return BulkScrapeResponse(
                    total=len(competitors),
                    success=0,
                    failed=0,
                    profiles=[],
                    posts_saved=0,
                    accepted=True,
                    message="Instagram scrape is already running in the background.",
                )

            _instagram_sync_task = asyncio.create_task(_run_instagram_sync_in_background())
            return BulkScrapeResponse(
                total=len(competitors),
                success=0,
                failed=0,
                profiles=[],
                posts_saved=0,
                accepted=True,
                message=(
                    f"Instagram scrape started in the background for {len(competitors)} competitors. "
                    "Refresh again shortly to load the updated content cache."
                ),
            )

        result = await _execute_instagram_sync(db, org_id)
        await db.commit()
        return result
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Instagram competitor sync failed: %s", exc)
        raise HTTPException(status_code=500, detail="Instagram competitor sync failed")


@router.post("/scraper/instagram/bulk", response_model=BulkScrapeResponse)
async def bulk_scrape_instagram(
    request: Request,
    body: BulkScrapeRequest,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Scrape specific handles or all tracked competitors."""
    org_id = get_org_id(request)
    
    if body.handles:
        handles = [h.strip().lstrip("@") for h in body.handles]
    else:
        # Scrape all tracked Instagram competitors
        result = await db.execute(
            select(Competitor.handle).where(Competitor.platform == "instagram").where(Competitor.org_id == org_id)
        )
        handles = [row[0] for row in result.fetchall()]
    
    if not handles:
        raise HTTPException(status_code=404, detail="No handles to scrape")
    
    profiles = await scrape_multiple(
        handles, delay_range=(body.delay_min, body.delay_max)
    )
    
    success = sum(1 for p in profiles if not p.error)
    failed = sum(1 for p in profiles if p.error)
    
    return BulkScrapeResponse(
        total=len(profiles),
        success=success,
        failed=failed,
        profiles=[_profile_to_response(p) for p in profiles],
    )


@router.get("/scraper/status", response_model=ScrapeStatusResponse)
async def get_scrape_status(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    """Get scraper status — last sync times, post counts, errors."""
    org_id = get_org_id(request)
    
    # Total competitors
    comp_result = await db.execute(
        select(Competitor).where(Competitor.platform == "instagram").where(Competitor.org_id == org_id)
    )
    competitors = comp_result.scalars().all()
    
    if not await _competitor_posts_cache_available(db):
        return ScrapeStatusResponse(
            total_competitors=len(competitors),
            total_cached_posts=0,
            last_scrape=None,
            competitors=[_empty_competitor_status(c) for c in competitors],
            sync_running=_instagram_sync_running(),
            sync_result=_instagram_sync_result,
        )

    total_posts = 0
    last_scrape = None
    comp_status = []

    try:
        post_count = await db.execute(
            text("SELECT COUNT(*) FROM crm.competitor_posts WHERE org_id = :org_id"),
            {"org_id": org_id}
        )
        total_posts = post_count.scalar() or 0

        last_scrape_result = await db.execute(
            text("SELECT MAX(fetched_at) FROM crm.competitor_posts WHERE org_id = :org_id"),
            {"org_id": org_id}
        )
        last_scrape = last_scrape_result.scalar()

        for c in competitors:
            cp_result = await db.execute(
                text(
                    "SELECT COUNT(*), MAX(fetched_at) FROM crm.competitor_posts "
                    "WHERE competitor_id = :cid AND org_id = :org_id"
                ),
                {"cid": c.id, "org_id": org_id},
            )
            row = cp_result.fetchone()

            comp_status.append({
                "id": c.id,
                "handle": c.handle,
                "followers": c.followers,
                "post_count": c.post_count,
                "cached_posts": row[0] if row else 0,
                "last_scrape": row[1].isoformat() if row and row[1] else None,
                "is_populated": c.is_auto_populated,
                "avg_engagement_rate": float(c.avg_engagement_rate or 0),
            })
    except SQLAlchemyError as exc:
        logger.warning("Failed to load scraper cache status: %s", exc)
        comp_status = [_empty_competitor_status(c) for c in competitors]
    
    return ScrapeStatusResponse(
        total_competitors=len(competitors),
        total_cached_posts=total_posts,
        last_scrape=last_scrape,
        competitors=comp_status,
        sync_running=_instagram_sync_running(),
        sync_result=_instagram_sync_result,
    )


# /{handle} MUST be last — otherwise "sync", "bulk", "status" match as handles
@router.post("/scraper/instagram/{handle}", response_model=ScrapedProfileResponse)
async def scrape_instagram_profile(handle: str):
    """Scrape a single public Instagram profile. No auth needed."""
    profile = await scrape_profile(handle)
    return _profile_to_response(profile)


# ── Deep Intelligence Endpoints ──────────────────────────────────

@router.post("/scraper/transcribe/{competitor_id}")
async def transcribe_competitor_videos_endpoint(
    request: Request,
    competitor_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Download, transcribe, and delete video/reel posts for a competitor.
    
    Only processes posts with media_type in (video, reel) that don't have transcripts yet.
    Videos are deleted immediately after transcription.
    """
    org_id = get_org_id(request)
    from app.services.video_transcriber import transcribe_competitor_videos
    
    # Verify competitor exists
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id).where(Competitor.org_id == org_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    stats = await transcribe_competitor_videos(db, competitor_id, limit=limit)
    return {
        "competitor_id": competitor_id,
        "handle": competitor.handle,
        **stats,
    }


@router.post("/scraper/comments/{competitor_id}")
async def scrape_competitor_comments_endpoint(
    request: Request,
    competitor_id: int,
    top_n: int = 10,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Scrape comments from a competitor's top posts.
    
    Uses authenticated Playwright to access post pages and extract comments.
    Only processes posts that don't have comments scraped yet.
    """
    org_id = get_org_id(request)
    from app.services.comment_scraper import scrape_competitor_comments
    
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id).where(Competitor.org_id == org_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    stats = await scrape_competitor_comments(db, competitor_id, top_n=top_n)
    return {
        "competitor_id": competitor_id,
        "handle": competitor.handle,
        **stats,
    }


@router.get("/scraper/posts/{post_id}")
async def get_post_detail(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get full post detail including transcript and comments."""
    org_id = get_org_id(request)
    result = await db.execute(
        text("""
            SELECT cp.*, c.handle
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON c.id = cp.competitor_id
            WHERE cp.id = :pid AND cp.org_id = :org_id AND c.org_id = :org_id
        """),
        {"pid": post_id, "org_id": org_id},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return _build_post_detail(row)


@router.get("/scraper/posts/by-shortcode/{shortcode}")
async def get_post_by_shortcode(
    request: Request,
    shortcode: str,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get post detail by Instagram shortcode."""
    org_id = get_org_id(request)
    result = await db.execute(
        text("""
            SELECT cp.*, c.handle
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON c.id = cp.competitor_id
            WHERE cp.shortcode = :sc AND cp.org_id = :org_id AND c.org_id = :org_id
            LIMIT 1
        """),
        {"sc": shortcode, "org_id": org_id},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return _build_post_detail(row)


def _build_post_detail(row) -> dict:
    """Build post detail response from DB row."""
    row_dict = dict(row._mapping)
    
    def _parse_jsonb(val):
        if isinstance(val, str):
            return json.loads(val)
        return val
    
    transcript = _parse_jsonb(row_dict.get("transcript"))
    comments_data = _parse_jsonb(row_dict.get("comments_data"))
    content_analysis = _parse_jsonb(row_dict.get("content_analysis"))
    
    return {
        "id": row_dict["id"],
        "competitor_id": row_dict["competitor_id"],
        "handle": row_dict["handle"],
        "shortcode": row_dict.get("shortcode"),
        "platform": row_dict.get("platform"),
        "post_text": row_dict.get("post_text", ""),
        "hook": row_dict.get("hook", ""),
        "likes": row_dict.get("likes", 0),
        "comments": row_dict.get("comments", 0),
        "shares": row_dict.get("shares", 0),
        "engagement_score": float(row_dict.get("engagement_score", 0)),
        "media_type": row_dict.get("media_type", "image"),
        "media_url": row_dict.get("media_url"),
        "thumbnail_url": row_dict.get("thumbnail_url"),
        "post_url": row_dict.get("post_url"),
        "posted_at": row_dict.get("posted_at"),
        "transcript": transcript,
        "comments_data": comments_data,
        "content_analysis": content_analysis,
    }
