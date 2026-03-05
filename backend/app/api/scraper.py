"""Scraper API — our own data collection pipeline.

No paid services. No third-party APIs for competitor data.
Hits public endpoints directly and stores results in our DB.

Endpoints:
  POST /api/scraper/instagram/{handle}     — Scrape single competitor
  POST /api/scraper/instagram/bulk         — Scrape all tracked IG competitors
  POST /api/scraper/instagram/sync         — Scrape + update competitor records + cache posts
  GET  /api/scraper/status                 — Last scrape times, error counts
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.competitor import Competitor
from app.services.instagram_scraper import (
    scrape_profile,
    scrape_multiple,
    ScrapedProfile,
    ScrapedPost,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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


class ScrapeStatusResponse(BaseModel):
    total_competitors: int
    total_cached_posts: int
    last_scrape: Optional[datetime] = None
    competitors: List[Dict[str, Any]] = []


# ── Helpers ──────────────────────────────────────────────────────

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
                engagement_score=p.engagement_score,
                hook=p.hook,
            )
            for p in profile.posts
        ],
        scraped_at=profile.scraped_at,
        error=profile.error,
    )


async def _save_profile_to_competitor(
    db: AsyncSession, competitor: Competitor, profile: ScrapedProfile
) -> None:
    """Update a Competitor record with scraped profile data."""
    if profile.error or profile.is_private:
        return
    
    competitor.followers = profile.followers
    competitor.following = profile.following
    competitor.post_count = profile.post_count
    competitor.bio = profile.bio
    competitor.profile_image_url = profile.profile_pic_url
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
        total_eng = sum(p.engagement_score for p in profile.posts)
        avg_eng = total_eng / len(profile.posts)
        if profile.followers > 0:
            competitor.avg_engagement_rate = round(
                (avg_eng / profile.followers) * 100, 2
            )


async def _save_posts_to_cache(
    db: AsyncSession, competitor_id: int, platform: str, posts: List[ScrapedPost]
) -> int:
    """Save scraped posts to competitor_posts cache table. Returns count saved."""
    if not posts:
        return 0
    
    # Delete old cached posts for this competitor
    await db.execute(
        text(
            "DELETE FROM crm.competitor_posts "
            "WHERE competitor_id = :cid AND platform = :platform"
        ),
        {"cid": competitor_id, "platform": platform},
    )
    
    saved = 0
    for post in posts:
        try:
            await db.execute(
                text("""
                    INSERT INTO crm.competitor_posts 
                    (competitor_id, platform, post_text, likes, comments, shares,
                     engagement_score, hook, post_url, posted_at, fetched_at)
                    VALUES (:cid, :platform, :text, :likes, :comments, :shares,
                            :score, :hook, :url, :posted_at, NOW())
                """),
                {
                    "cid": competitor_id,
                    "platform": platform,
                    "text": post.caption,
                    "likes": post.likes,
                    "comments": post.comments,
                    "shares": post.views,  # Use views as "shares" for video reach
                    "score": post.engagement_score,
                    "hook": post.hook,
                    "url": post.post_url,
                    "posted_at": post.posted_at,
                },
            )
            saved += 1
        except Exception as e:
            logger.warning(f"Failed to save post {post.shortcode}: {e}")
    
    return saved


# ── Endpoints ────────────────────────────────────────────────────
# IMPORTANT: Static routes MUST come before parameterized /{handle} route
# or FastAPI will match "sync" as a handle.

@router.post("/scraper/instagram/sync", response_model=BulkScrapeResponse)
async def sync_all_instagram_competitors(
    db: AsyncSession = Depends(get_crm_db),
):
    """Scrape ALL tracked Instagram competitors, update their records, and cache posts.
    
    This is the main data collection endpoint for the Reports feature.
    """
    # Get all Instagram competitors
    result = await db.execute(
        select(Competitor)
        .where(Competitor.platform == "instagram")
        .where(Competitor.auto_sync_enabled == True)
    )
    competitors = result.scalars().all()
    
    if not competitors:
        raise HTTPException(status_code=404, detail="No Instagram competitors to sync")
    
    handles = [c.handle for c in competitors]
    handle_to_competitor = {c.handle: c for c in competitors}
    
    # Scrape all profiles
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
            
            # Update competitor record
            competitor = handle_to_competitor.get(profile.handle)
            if competitor:
                await _save_profile_to_competitor(db, competitor, profile)
                
                # Cache posts
                posts_saved = await _save_posts_to_cache(
                    db, competitor.id, "instagram", profile.posts
                )
                total_posts_saved += posts_saved
        
        responses.append(_profile_to_response(profile))
    
    await db.commit()
    
    return BulkScrapeResponse(
        total=len(profiles),
        success=success,
        failed=failed,
        profiles=responses,
        posts_saved=total_posts_saved,
    )


@router.post("/scraper/instagram/bulk", response_model=BulkScrapeResponse)
async def bulk_scrape_instagram(
    request: BulkScrapeRequest,
    db: AsyncSession = Depends(get_crm_db),
):
    """Scrape specific handles or all tracked competitors."""
    
    if request.handles:
        handles = [h.strip().lstrip("@") for h in request.handles]
    else:
        # Scrape all tracked Instagram competitors
        result = await db.execute(
            select(Competitor.handle).where(Competitor.platform == "instagram")
        )
        handles = [row[0] for row in result.fetchall()]
    
    if not handles:
        raise HTTPException(status_code=404, detail="No handles to scrape")
    
    profiles = await scrape_multiple(
        handles, delay_range=(request.delay_min, request.delay_max)
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
async def get_scrape_status(db: AsyncSession = Depends(get_crm_db)):
    """Get scraper status — last sync times, post counts, errors."""
    
    # Total competitors
    comp_result = await db.execute(
        select(Competitor).where(Competitor.platform == "instagram")
    )
    competitors = comp_result.scalars().all()
    
    # Total cached posts
    post_count = await db.execute(
        text("SELECT COUNT(*) FROM crm.competitor_posts")
    )
    total_posts = post_count.scalar() or 0
    
    # Last scrape time
    last_scrape_result = await db.execute(
        text("SELECT MAX(fetched_at) FROM crm.competitor_posts")
    )
    last_scrape = last_scrape_result.scalar()
    
    # Per-competitor status
    comp_status = []
    for c in competitors:
        # Count posts for this competitor
        cp_result = await db.execute(
            text(
                "SELECT COUNT(*), MAX(fetched_at) FROM crm.competitor_posts "
                "WHERE competitor_id = :cid"
            ),
            {"cid": c.id},
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
    
    return ScrapeStatusResponse(
        total_competitors=len(competitors),
        total_cached_posts=total_posts,
        last_scrape=last_scrape,
        competitors=comp_status,
    )


# /{handle} MUST be last — otherwise "sync", "bulk", "status" match as handles
@router.post("/scraper/instagram/{handle}", response_model=ScrapedProfileResponse)
async def scrape_instagram_profile(handle: str):
    """Scrape a single public Instagram profile. No auth needed."""
    profile = await scrape_profile(handle)
    return _profile_to_response(profile)
