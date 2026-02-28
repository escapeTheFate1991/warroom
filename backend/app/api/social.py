"""Social media API endpoints."""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional
import random

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.social import SocialAccount, SocialAnalytics

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class SocialAccountCreate(BaseModel):
    """Create social account request."""
    platform: str
    username: str
    profile_url: Optional[str] = None
    follower_count: Optional[int] = 0
    following_count: Optional[int] = 0
    post_count: Optional[int] = 0


class SocialAccountResponse(BaseModel):
    """Social account response."""
    id: int
    platform: str
    username: Optional[str]
    profile_url: Optional[str]
    follower_count: int
    following_count: int
    post_count: int
    connected_at: datetime
    last_synced: Optional[datetime]
    status: str

    class Config:
        from_attributes = True


class SocialAnalyticsResponse(BaseModel):
    """Social analytics response."""
    platform: str
    metric_date: date
    impressions: int
    reach: int
    engagement: int
    engagement_rate: float
    followers_gained: int
    followers_lost: int
    profile_views: int
    link_clicks: int
    shares: int
    saves: int
    comments: int
    likes: int
    video_views: int


class SocialSummaryResponse(BaseModel):
    """Social summary response."""
    total_followers: int
    total_engagement: int
    total_impressions: int
    total_reach: int
    engagement_rate: float
    accounts_connected: int


@router.get("/accounts", response_model=List[SocialAccountResponse])
async def get_social_accounts(db: AsyncSession = Depends(get_crm_db)):
    """List all connected social media accounts."""
    try:
        result = await db.execute(select(SocialAccount))
        accounts = result.scalars().all()
        return [SocialAccountResponse.model_validate(account) for account in accounts]
    except Exception as e:
        logger.error(f"Failed to fetch social accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch social accounts")


@router.post("/accounts", response_model=SocialAccountResponse)
async def connect_social_account(
    account_data: SocialAccountCreate,
    db: AsyncSession = Depends(get_crm_db)
):
    """Connect a new social media account."""
    try:
        # For demo purposes, use user_id = 1
        new_account = SocialAccount(
            user_id=1,
            platform=account_data.platform,
            username=account_data.username,
            profile_url=account_data.profile_url,
            follower_count=account_data.follower_count,
            following_count=account_data.following_count,
            post_count=account_data.post_count,
            status="connected"
        )
        
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
        
        # Generate some mock analytics for the new account
        await _generate_mock_analytics(db, new_account.id)
        
        return SocialAccountResponse.model_validate(new_account)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create social account: {e}")
        raise HTTPException(status_code=500, detail="Failed to create social account")


@router.delete("/accounts/{account_id}")
async def disconnect_social_account(
    account_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Disconnect a social media account."""
    try:
        result = await db.execute(select(SocialAccount).where(SocialAccount.id == account_id))
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        await db.delete(account)
        await db.commit()
        
        return {"message": "Account disconnected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete social account: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect account")


@router.get("/analytics", response_model=SocialSummaryResponse)
async def get_social_analytics(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get aggregated social media analytics."""
    try:
        # Base query
        query = select(SocialAccount)
        if platform:
            query = query.where(SocialAccount.platform == platform)
        
        result = await db.execute(query)
        accounts = result.scalars().all()
        
        if not accounts:
            # Return mock data if no accounts exist
            return _generate_mock_summary(platform)
        
        # Get recent analytics (last 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        analytics_query = select(SocialAnalytics).join(SocialAccount).where(
            SocialAnalytics.metric_date >= start_date,
            SocialAnalytics.metric_date <= end_date
        )
        
        if platform:
            analytics_query = analytics_query.where(SocialAccount.platform == platform)
        
        analytics_result = await db.execute(analytics_query)
        analytics = analytics_result.scalars().all()
        
        # Aggregate data
        total_followers = sum(account.follower_count for account in accounts)
        total_engagement = sum(a.engagement for a in analytics)
        total_impressions = sum(a.impressions for a in analytics)
        total_reach = sum(a.reach for a in analytics)
        
        # Calculate engagement rate
        engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0
        
        return SocialSummaryResponse(
            total_followers=total_followers,
            total_engagement=total_engagement,
            total_impressions=total_impressions,
            total_reach=total_reach,
            engagement_rate=round(engagement_rate, 2),
            accounts_connected=len(accounts)
        )
    except Exception as e:
        logger.error(f"Failed to fetch social analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")


@router.get("/analytics/{platform}", response_model=List[SocialAnalyticsResponse])
async def get_platform_analytics(
    platform: str,
    days: int = 30,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get analytics for a specific platform."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        query = (
            select(SocialAnalytics)
            .join(SocialAccount)
            .where(
                SocialAccount.platform == platform,
                SocialAnalytics.metric_date >= start_date,
                SocialAnalytics.metric_date <= end_date
            )
            .order_by(SocialAnalytics.metric_date.desc())
        )
        
        result = await db.execute(query)
        analytics = result.scalars().all()
        
        if not analytics:
            # Generate mock data for the platform
            return _generate_mock_platform_analytics(platform, days)
        
        return [
            SocialAnalyticsResponse(
                platform=platform,
                metric_date=a.metric_date,
                impressions=a.impressions,
                reach=a.reach,
                engagement=a.engagement,
                engagement_rate=float(a.engagement_rate),
                followers_gained=a.followers_gained,
                followers_lost=a.followers_lost,
                profile_views=a.profile_views,
                link_clicks=a.link_clicks,
                shares=a.shares,
                saves=a.saves,
                comments=a.comments,
                likes=a.likes,
                video_views=a.video_views
            )
            for a in analytics
        ]
    except Exception as e:
        logger.error(f"Failed to fetch platform analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch platform analytics")


async def _generate_mock_analytics(db: AsyncSession, account_id: int):
    """Generate mock analytics data for a new account."""
    end_date = date.today()
    
    for i in range(30):  # Last 30 days
        metric_date = end_date - timedelta(days=i)
        
        analytics = SocialAnalytics(
            account_id=account_id,
            metric_date=metric_date,
            impressions=random.randint(500, 2000),
            reach=random.randint(400, 1800),
            engagement=random.randint(50, 200),
            engagement_rate=random.uniform(2.5, 8.5),
            followers_gained=random.randint(0, 15),
            followers_lost=random.randint(0, 8),
            profile_views=random.randint(20, 100),
            link_clicks=random.randint(5, 30),
            shares=random.randint(2, 15),
            saves=random.randint(3, 20),
            comments=random.randint(5, 25),
            likes=random.randint(30, 150),
            video_views=random.randint(100, 800)
        )
        
        db.add(analytics)
    
    await db.commit()


def _generate_mock_summary(platform: Optional[str] = None) -> SocialSummaryResponse:
    """Generate mock summary data when no accounts exist."""
    if platform:
        # Single platform mock data
        return SocialSummaryResponse(
            total_followers=random.randint(1000, 5000),
            total_engagement=random.randint(500, 2000),
            total_impressions=random.randint(10000, 50000),
            total_reach=random.randint(8000, 40000),
            engagement_rate=random.uniform(3.0, 7.5),
            accounts_connected=1
        )
    else:
        # Overall mock data
        return SocialSummaryResponse(
            total_followers=random.randint(5000, 20000),
            total_engagement=random.randint(2000, 8000),
            total_impressions=random.randint(50000, 200000),
            total_reach=random.randint(40000, 160000),
            engagement_rate=random.uniform(4.0, 6.5),
            accounts_connected=3
        )


def _generate_mock_platform_analytics(platform: str, days: int) -> List[SocialAnalyticsResponse]:
    """Generate mock analytics for a platform."""
    analytics = []
    end_date = date.today()
    
    for i in range(days):
        metric_date = end_date - timedelta(days=i)
        
        analytics.append(SocialAnalyticsResponse(
            platform=platform,
            metric_date=metric_date,
            impressions=random.randint(500, 2000),
            reach=random.randint(400, 1800),
            engagement=random.randint(50, 200),
            engagement_rate=random.uniform(2.5, 8.5),
            followers_gained=random.randint(0, 15),
            followers_lost=random.randint(0, 8),
            profile_views=random.randint(20, 100),
            link_clicks=random.randint(5, 30),
            shares=random.randint(2, 15),
            saves=random.randint(3, 20),
            comments=random.randint(5, 25),
            likes=random.randint(30, 150),
            video_views=random.randint(100, 800)
        ))
    
    return analytics