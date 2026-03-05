"""Social media API endpoints."""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, text
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
            # Return empty data if no accounts exist
            return SocialSummaryResponse(
                total_followers=0,
                total_engagement=0,
                total_impressions=0,
                total_reach=0,
                engagement_rate=0.0,
                accounts_connected=0
            )
        
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
            # Return empty data if no analytics exist
            return []
        
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


@router.get("/analytics/sparkline")
async def get_analytics_sparkline(
    days: int = 7,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get sparkline data for each platform (engagement arrays for charts)."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get all accounts
        accounts_query = select(SocialAccount)
        accounts_result = await db.execute(accounts_query)
        accounts = accounts_result.scalars().all()
        
        sparkline_data = {}
        
        for account in accounts:
            platform = account.platform
            
            # Get daily engagement data for this platform
            analytics_query = text("""
                SELECT metric_date, SUM(engagement) as total_engagement
                FROM crm.social_analytics 
                WHERE account_id = :account_id 
                    AND metric_date >= :start_date 
                    AND metric_date <= :end_date
                GROUP BY metric_date
                ORDER BY metric_date ASC
            """)
            
            result = await db.execute(analytics_query, {
                "account_id": account.id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            daily_data = result.fetchall()
            
            # Convert to engagement array (fill missing days with 0)
            engagement_array = []
            data_dict = {row.metric_date: row.total_engagement for row in daily_data}
            
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                engagement_array.append(data_dict.get(current_date, 0))
            
            if platform not in sparkline_data:
                sparkline_data[platform] = engagement_array
            else:
                # Add to existing platform data if multiple accounts
                sparkline_data[platform] = [
                    existing + new for existing, new in zip(sparkline_data[platform], engagement_array)
                ]
        
        return sparkline_data
    except Exception as e:
        logger.error(f"Failed to fetch sparkline data: {e}")
        return {}


@router.get("/analytics/trends")
async def get_analytics_trends(db: AsyncSession = Depends(get_crm_db)):
    """Get percentage change trends (this week vs last week)."""
    try:
        today = date.today()
        
        # Calculate week boundaries
        this_week_start = today - timedelta(days=7)
        last_week_start = today - timedelta(days=14)
        last_week_end = this_week_start - timedelta(days=1)
        
        # Query this week's data
        this_week_query = text("""
            SELECT 
                SUM(sa.engagement) as total_engagement,
                SUM(sa.impressions) as total_impressions,
                SUM(sa.followers_gained - sa.followers_lost) as net_followers
            FROM crm.social_analytics sa
            JOIN crm.social_accounts acc ON sa.account_id = acc.id
            WHERE sa.metric_date >= :start_date AND sa.metric_date <= :end_date
        """)
        
        # Query last week's data  
        last_week_query = text("""
            SELECT 
                SUM(sa.engagement) as total_engagement,
                SUM(sa.impressions) as total_impressions,
                SUM(sa.followers_gained - sa.followers_lost) as net_followers
            FROM crm.social_analytics sa
            JOIN crm.social_accounts acc ON sa.account_id = acc.id
            WHERE sa.metric_date >= :start_date AND sa.metric_date <= :end_date
        """)
        
        this_week_result = await db.execute(this_week_query, {
            "start_date": this_week_start,
            "end_date": today
        })
        this_week = this_week_result.fetchone()
        
        last_week_result = await db.execute(last_week_query, {
            "start_date": last_week_start,
            "end_date": last_week_end
        })
        last_week = last_week_result.fetchone()
        
        def calculate_percentage_change(current, previous):
            if not previous or previous == 0:
                return "+0.0%" if current == 0 else "+100.0%"
            change = ((current - previous) / previous) * 100
            sign = "+" if change >= 0 else ""
            return f"{sign}{change:.1f}%"
        
        trends = {
            "followers": calculate_percentage_change(
                this_week.net_followers or 0,
                last_week.net_followers or 0
            ),
            "engagement": calculate_percentage_change(
                this_week.total_engagement or 0,
                last_week.total_engagement or 0
            ),
            "impressions": calculate_percentage_change(
                this_week.total_impressions or 0,
                last_week.total_impressions or 0
            )
        }
        
        return trends
    except Exception as e:
        logger.error(f"Failed to fetch trends data: {e}")
        return {
            "followers": "+0.0%",
            "engagement": "+0.0%", 
            "impressions": "+0.0%"
        }


@router.post("/sync")
async def sync_social_data(db: AsyncSession = Depends(get_crm_db)):
    """Trigger sync of all connected social media accounts."""
    try:
        # Get all connected accounts
        result = await db.execute(select(SocialAccount).where(SocialAccount.status == "connected"))
        accounts = result.scalars().all()
        
        if not accounts:
            return {"message": "No connected accounts to sync", "synced_accounts": 0}
        
        # Update last_synced timestamp for all accounts
        for account in accounts:
            account.last_synced = datetime.utcnow()
        
        await db.commit()
        
        return {
            "message": f"Successfully triggered sync for {len(accounts)} accounts",
            "synced_accounts": len(accounts)
        }
    except Exception as e:
        logger.error(f"Failed to sync social data: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync social data")








