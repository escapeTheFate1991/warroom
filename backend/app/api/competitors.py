"""Competitor intelligence API endpoints."""
import logging
import json
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.competitor import Competitor
from app.models.crm.social import SocialAccount
from app.api.scraper import sync_instagram_competitor, sync_instagram_competitor_batch
from app.db.crm_db import crm_session

logger = logging.getLogger(__name__)


async def _background_sync_competitor(competitor_id: int, platform: str):
    """Background task to sync competitor after creation."""
    try:
        if platform.lower() != "instagram":
            return  # Only auto-sync Instagram for now
            
        async with crm_session() as db:
            # Get the competitor
            result = await db.execute(
                select(Competitor).where(Competitor.id == competitor_id)
            )
            competitor = result.scalar_one_or_none()
            
            if not competitor:
                logger.error(f"Competitor {competitor_id} not found for background sync")
                return
                
            # Sync the competitor
            sync_result = await sync_instagram_competitor(db, competitor)
            
            if sync_result["success"]:
                await db.commit()
                logger.info(f"Successfully synced competitor {competitor.handle} (ID: {competitor_id})")
            else:
                logger.error(f"Failed to sync competitor {competitor.handle} (ID: {competitor_id}): {sync_result['error']}")
                
    except Exception as e:
        logger.error(f"Background sync failed for competitor {competitor_id}: {e}")

router = APIRouter()


# Pydantic models
class CompetitorCreate(BaseModel):
    """Create competitor request - minimal required fields."""
    handle: str = Field(..., description="Social media handle without @")
    platform: str = Field(..., description="Social platform (instagram, x, youtube, tiktok, facebook, threads)")


class CompetitorUpdate(BaseModel):
    """Update competitor request."""
    handle: Optional[str] = None
    platform: Optional[str] = None
    top_angles: Optional[str] = None
    signature_formula: Optional[str] = None
    notes: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None


class CompetitorResponse(BaseModel):
    """Competitor response model."""
    id: int
    handle: str
    platform: str
    followers: int
    following: int
    post_count: int
    bio: Optional[str]
    profile_image_url: Optional[str]
    posting_frequency: Optional[str]
    avg_engagement_rate: float
    top_angles: Optional[str]
    signature_formula: Optional[str]
    notes: Optional[str]
    is_auto_populated: bool
    last_auto_sync: Optional[datetime]
    auto_sync_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SocialPlatformData(BaseModel):
    """Social platform data response."""
    followers: int = 0
    following: int = 0
    post_count: int = 0
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    posting_frequency: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


async def get_social_account_token(db: AsyncSession, platform: str) -> Optional[str]:
    """Get access token for connected social account."""
    try:
        result = await db.execute(
            select(SocialAccount.access_token)
            .where(SocialAccount.platform == platform)
            .where(SocialAccount.status == "connected")
            .limit(1)
        )
        token_row = result.first()
        return token_row[0] if token_row else None
    except Exception as e:
        logger.error("Failed to get token for %s: %s", platform, e)
        return None


async def fetch_instagram_data(handle: str, access_token: str) -> SocialPlatformData:
    """Fetch data from Instagram API."""
    try:
        async with httpx.AsyncClient() as client:
            # Use Instagram Business Discovery API
            url = "https://graph.instagram.com/me"
            params = {
                "fields": f"business_discovery.username({handle}){{username,media_count,followers_count,follows_count,biography,profile_picture_url}}",
                "access_token": access_token
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            business_data = data.get("business_discovery", {})
            
            return SocialPlatformData(
                followers=business_data.get("followers_count", 0),
                following=business_data.get("follows_count", 0), 
                post_count=business_data.get("media_count", 0),
                bio=business_data.get("biography"),
                profile_image_url=business_data.get("profile_picture_url"),
                success=True
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("Instagram API error for %s: %s - %s", handle, e.response.status_code, e.response.text)
        return SocialPlatformData(success=False, error=f"API error: {e.response.status_code}")
    except Exception as e:
        logger.error("Instagram fetch error for %s: %s", handle, e)
        return SocialPlatformData(success=False, error=str(e))


async def fetch_x_data(handle: str, access_token: str) -> SocialPlatformData:
    """Fetch data from X/Twitter API."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://api.x.com/2/users/by/username/{handle}"
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                "user.fields": "public_metrics,description,profile_image_url"
            }
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            user_data = data.get("data", {})
            public_metrics = user_data.get("public_metrics", {})
            
            return SocialPlatformData(
                followers=public_metrics.get("followers_count", 0),
                following=public_metrics.get("following_count", 0),
                post_count=public_metrics.get("tweet_count", 0),
                bio=user_data.get("description"),
                profile_image_url=user_data.get("profile_image_url"),
                success=True
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("X API error for %s: %s - %s", handle, e.response.status_code, e.response.text)
        return SocialPlatformData(success=False, error=f"API error: {e.response.status_code}")
    except Exception as e:
        logger.error("X fetch error for %s: %s", handle, e)
        return SocialPlatformData(success=False, error=str(e))


async def fetch_youtube_data(handle: str, api_key: str) -> SocialPlatformData:
    """Fetch data from YouTube API."""
    try:
        async with httpx.AsyncClient() as client:
            # Try searching by handle first
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "q": handle,
                "type": "channel",
                "part": "snippet",
                "maxResults": 1,
                "key": api_key
            }
            
            response = await client.get(search_url, params=search_params)
            response.raise_for_status()
            
            search_data = response.json()
            items = search_data.get("items", [])
            
            if not items:
                return SocialPlatformData(success=False, error="Channel not found")
            
            channel_id = items[0]["id"]["channelId"]
            
            # Get channel statistics
            stats_url = "https://www.googleapis.com/youtube/v3/channels"
            stats_params = {
                "id": channel_id,
                "part": "statistics,snippet",
                "key": api_key
            }
            
            stats_response = await client.get(stats_url, params=stats_params)
            stats_response.raise_for_status()
            
            stats_data = stats_response.json()
            if not stats_data.get("items"):
                return SocialPlatformData(success=False, error="Channel stats not available")
            
            channel_info = stats_data["items"][0]
            stats = channel_info.get("statistics", {})
            snippet = channel_info.get("snippet", {})
            
            return SocialPlatformData(
                followers=int(stats.get("subscriberCount", 0)),
                following=0,  # YouTube doesn't have "following" concept
                post_count=int(stats.get("videoCount", 0)),
                bio=snippet.get("description"),
                profile_image_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
                success=True
            )
            
    except httpx.HTTPStatusError as e:
        logger.error("YouTube API error for %s: %s - %s", handle, e.response.status_code, e.response.text)
        return SocialPlatformData(success=False, error=f"API error: {e.response.status_code}")
    except Exception as e:
        logger.error("YouTube fetch error for %s: %s", handle, e)
        return SocialPlatformData(success=False, error=str(e))


async def auto_populate_competitor_data(handle: str, platform: str, db: AsyncSession) -> SocialPlatformData:
    """Auto-populate competitor data from social platform APIs."""
    platform = platform.lower()
    
    if platform == "instagram":
        token = await get_social_account_token(db, "instagram")
        if not token:
            return SocialPlatformData(success=False, error="Instagram account not connected")
        return await fetch_instagram_data(handle, token)
    
    elif platform == "x":
        token = await get_social_account_token(db, "x")
        if not token:
            return SocialPlatformData(success=False, error="X account not connected")
        return await fetch_x_data(handle, token)
    
    elif platform == "youtube":
        # For YouTube, we would need a separate API key configuration
        # For now, return mock data
        return SocialPlatformData(success=False, error="YouTube auto-population not configured")
    
    elif platform in ["tiktok", "facebook", "threads"]:
        # These platforms have restrictive APIs or need special setup
        return SocialPlatformData(success=False, error=f"{platform.title()} auto-population not supported yet")
    
    else:
        return SocialPlatformData(success=False, error=f"Unknown platform: {platform}")


def _apply_social_platform_data(
    competitor: Competitor,
    auto_data: SocialPlatformData,
) -> None:
    """Apply fetched platform data to a competitor row."""
    competitor.followers = auto_data.followers
    competitor.following = auto_data.following
    competitor.post_count = auto_data.post_count
    competitor.bio = auto_data.bio
    competitor.profile_image_url = auto_data.profile_image_url
    competitor.posting_frequency = auto_data.posting_frequency
    competitor.is_auto_populated = True
    competitor.last_auto_sync = datetime.now()
    competitor.updated_at = datetime.now()


async def _sync_competitor_record(
    db: AsyncSession,
    competitor: Competitor,
) -> tuple[bool, Optional[str]]:
    """Refresh a competitor through the correct platform-specific data path."""
    platform = competitor.platform.lower()

    if platform == "instagram":
        sync_result = await sync_instagram_competitor(db, competitor)
        return sync_result["success"], sync_result["error"]

    auto_data = await auto_populate_competitor_data(
        competitor.handle,
        competitor.platform,
        db,
    )

    if not auto_data.success:
        return False, auto_data.error

    _apply_social_platform_data(competitor, auto_data)
    return True, None


@router.post("/competitors", response_model=CompetitorResponse)
async def create_competitor(
    competitor_data: CompetitorCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_crm_db)
):
    """Create a new competitor with auto-populated data."""
    try:
        handle = competitor_data.handle.strip().lstrip('@')
        platform = competitor_data.platform.lower()
        
        # Check if competitor already exists
        existing_result = await db.execute(
            select(Competitor).where(
                Competitor.handle == handle,
                Competitor.platform == platform
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Competitor already exists")
        
        if platform == "instagram":
            new_competitor = Competitor(
                handle=handle,
                platform=platform,
                is_auto_populated=False,
                last_auto_sync=None,
            )
        else:
            auto_data = await auto_populate_competitor_data(handle, platform, db)

            new_competitor = Competitor(
                handle=handle,
                platform=platform,
                followers=auto_data.followers,
                following=auto_data.following,
                post_count=auto_data.post_count,
                bio=auto_data.bio,
                profile_image_url=auto_data.profile_image_url,
                posting_frequency=auto_data.posting_frequency,
                is_auto_populated=auto_data.success,
                last_auto_sync=datetime.now() if auto_data.success else None,
            )
        
        db.add(new_competitor)
        await db.commit()
        await db.refresh(new_competitor)
        
        # Trigger background sync for the new competitor
        background_tasks.add_task(
            _background_sync_competitor, 
            new_competitor.id, 
            new_competitor.platform
        )
        
        return CompetitorResponse.model_validate(new_competitor)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create competitor: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create competitor")


@router.get("/competitors", response_model=List[CompetitorResponse])
async def list_competitors(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """List all competitors."""
    try:
        query = select(Competitor).order_by(Competitor.created_at.desc())
        
        if platform:
            query = query.where(Competitor.platform == platform.lower())
        
        result = await db.execute(query)
        competitors = result.scalars().all()
        
        return [CompetitorResponse.model_validate(comp) for comp in competitors]
        
    except Exception as e:
        logger.error("Failed to fetch competitors: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch competitors")


@router.get("/competitors/{competitor_id}", response_model=CompetitorResponse)
async def get_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get a specific competitor."""
    try:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        return CompetitorResponse.model_validate(competitor)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch competitor: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch competitor")


@router.put("/competitors/{competitor_id}", response_model=CompetitorResponse)
async def update_competitor(
    competitor_id: int,
    update_data: CompetitorUpdate,
    db: AsyncSession = Depends(get_crm_db)
):
    """Update a competitor."""
    try:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(competitor, field, value)
        
        competitor.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(competitor)
        
        return CompetitorResponse.model_validate(competitor)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update competitor: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update competitor")


@router.delete("/competitors/{competitor_id}")
async def delete_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Delete a competitor."""
    try:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        await db.delete(competitor)
        await db.commit()
        
        return {"message": "Competitor deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete competitor: %s", e)
        raise HTTPException(status_code=500, detail="Failed to delete competitor")


@router.post("/competitors/{competitor_id}/auto-populate", response_model=CompetitorResponse)
async def auto_populate_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Populate an existing competitor through the real platform-specific write path."""
    try:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        success, error = await _sync_competitor_record(db, competitor)
        if not success:
            raise HTTPException(
                status_code=422,
                detail=f"Failed to auto-populate competitor: {error}",
            )

        await db.commit()
        await db.refresh(competitor)

        return CompetitorResponse.model_validate(competitor)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to auto-populate competitor: %s", e)
        raise HTTPException(status_code=500, detail="Failed to auto-populate competitor")


@router.post("/competitors/sync")
async def sync_competitors(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Refresh all tracked competitors' stats from their respective APIs."""
    try:
        # Get competitors to sync
        query = select(Competitor).where(Competitor.auto_sync_enabled == True)
        
        if platform:
            query = query.where(Competitor.platform == platform.lower())
        
        result = await db.execute(query)
        competitors = result.scalars().all()
        
        sync_results = {
            "success": 0,
            "failed": 0,
            "details": []
        }

        instagram_competitors = [
            competitor
            for competitor in competitors
            if competitor.platform.lower() == "instagram"
        ]

        if instagram_competitors:
            batch_result = await sync_instagram_competitor_batch(db, instagram_competitors)
            instagram_lookup = {
                competitor.handle.strip().lstrip("@").lower(): competitor
                for competitor in instagram_competitors
            }

            sync_results["success"] += batch_result.success
            sync_results["failed"] += batch_result.failed

            for profile in batch_result.profiles:
                competitor = instagram_lookup.get(profile.handle.strip().lstrip("@").lower())
                if not competitor:
                    continue

                detail = {
                    "id": competitor.id,
                    "handle": competitor.handle,
                    "platform": competitor.platform,
                    "status": "failed" if profile.error else "success",
                }
                if profile.error:
                    detail["error"] = profile.error
                sync_results["details"].append(detail)
        
        for competitor in competitors:
            if competitor.platform.lower() == "instagram":
                continue

            try:
                success, error = await _sync_competitor_record(db, competitor)

                if success:
                    sync_results["success"] += 1
                    sync_results["details"].append({
                        "id": competitor.id,
                        "handle": competitor.handle,
                        "platform": competitor.platform,
                        "status": "success"
                    })
                else:
                    sync_results["failed"] += 1
                    sync_results["details"].append({
                        "id": competitor.id,
                        "handle": competitor.handle,
                        "platform": competitor.platform,
                        "status": "failed",
                        "error": error
                    })
                    
            except Exception as e:
                sync_results["failed"] += 1
                sync_results["details"].append({
                    "id": competitor.id,
                    "handle": competitor.handle,
                    "platform": competitor.platform,
                    "status": "error",
                    "error": str(e)
                })
        
        await db.commit()
        
        return {
            "message": f"Sync completed: {sync_results['success']} succeeded, {sync_results['failed']} failed",
            "results": sync_results
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to sync competitors: %s", e)
        raise HTTPException(status_code=500, detail="Failed to sync competitors")


@router.post("/competitors/{competitor_id}/sync", response_model=CompetitorResponse)
async def sync_single_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Refresh a single competitor's data from their platform API."""
    try:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        success, error = await _sync_competitor_record(db, competitor)

        if not success:
            raise HTTPException(
                status_code=422, 
                detail=f"Failed to sync data: {error}"
            )
        
        await db.commit()
        await db.refresh(competitor)
        
        return CompetitorResponse.model_validate(competitor)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to sync competitor: %s", e)
        raise HTTPException(status_code=500, detail="Failed to sync competitor")