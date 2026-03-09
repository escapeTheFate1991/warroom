"""Social media API endpoints."""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.agent_contract import AgentAssignmentSummary, load_agent_assignment_map
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
    agent_assignments: list[AgentAssignmentSummary] = Field(default_factory=list)

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
    total_link_clicks: int = 0
    total_shares: int = 0
    total_saves: int = 0
    total_video_views: int = 0
    total_views: int = 0
    total_interactions: int = 0
    avg_watch_time_ms: int = 0
    total_watch_time_ms: int = 0


class SocialAnalyticsSeriesPoint(BaseModel):
    """Aggregated analytics point for charting."""
    bucket: date
    label: str
    engagement: int
    impressions: int
    reach: int
    shares: int
    saves: int
    link_clicks: int
    video_views: int
    likes: int
    comments: int


def _shift_months(value: date, months: int) -> date:
    """Shift a month-start date backward or forward by a number of months."""
    month_index = (value.year * 12) + (value.month - 1) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _build_time_buckets(end_date: date, granularity: str) -> tuple[date, List[date]]:
    """Return the start date and ordered bucket boundaries for the requested granularity."""
    if granularity == "daily":
        start_date = end_date - timedelta(days=13)
        buckets = [start_date + timedelta(days=index) for index in range(14)]
        return start_date, buckets

    if granularity == "weekly":
        current_week_start = end_date - timedelta(days=end_date.weekday())
        start_date = current_week_start - timedelta(weeks=11)
        buckets = [start_date + timedelta(weeks=index) for index in range(12)]
        return start_date, buckets

    current_month_start = end_date.replace(day=1)
    start_date = _shift_months(current_month_start, -11)
    buckets = [_shift_months(start_date, index) for index in range(12)]
    return start_date, buckets


def _format_bucket_label(bucket: date, granularity: str) -> str:
    """Return a concise chart label for a bucket start date."""
    if granularity == "monthly":
        return bucket.strftime("%b %Y")

    return bucket.strftime("%b %d").replace(" 0", " ")


@router.get("/accounts", response_model=List[SocialAccountResponse])
async def get_social_accounts(db: AsyncSession = Depends(get_crm_db)):
    """List all connected social media accounts."""
    try:
        result = await db.execute(
            select(SocialAccount).where(SocialAccount.status == "connected")
        )
        accounts = result.scalars().all()
        assignment_map = await load_agent_assignment_map(
            db,
            entity_type="social_account",
            entity_ids=[str(account.id) for account in accounts],
        )
        return [
            SocialAccountResponse.model_validate(account).model_copy(
                update={"agent_assignments": assignment_map.get(str(account.id), [])}
            )
            for account in accounts
        ]
    except Exception as e:
        logger.error("Failed to fetch social accounts: %s", e)
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
        logger.error("Failed to create social account: %s", e)
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
        logger.error("Failed to delete social account: %s", e)
        raise HTTPException(status_code=500, detail="Failed to disconnect account")


@router.get("/analytics", response_model=SocialSummaryResponse)
async def get_social_analytics(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get aggregated social media analytics (raw SQL — includes all Reel metrics)."""
    try:
        # Count connected accounts + total followers
        acct_q = "SELECT count(*), coalesce(sum(follower_count), 0) FROM social_accounts WHERE status = 'connected'"
        acct_params: dict = {}
        if platform:
            acct_q += " AND platform = :p"
            acct_params["p"] = platform
        r = await db.execute(text(acct_q), acct_params)
        acct_row = r.fetchone()
        accounts_connected = acct_row[0] if acct_row else 0
        total_followers = acct_row[1] if acct_row else 0

        if accounts_connected == 0:
            return SocialSummaryResponse(
                total_followers=0, total_engagement=0, total_impressions=0,
                total_reach=0, engagement_rate=0.0, accounts_connected=0,
            )

        # Aggregate analytics (last 30 days)
        analytics_q = """
            SELECT
                coalesce(sum(a.engagement), 0),
                coalesce(sum(a.impressions), 0),
                coalesce(sum(a.reach), 0),
                coalesce(sum(a.link_clicks), 0),
                coalesce(sum(a.shares), 0),
                coalesce(sum(a.saves), 0),
                coalesce(sum(a.video_views), 0),
                coalesce(sum(a.likes), 0),
                coalesce(sum(a.comments), 0),
                coalesce(sum(a.views), 0),
                coalesce(sum(a.total_interactions), 0),
                coalesce(avg(nullif(a.avg_watch_time_ms, 0)), 0)::int,
                coalesce(sum(a.total_watch_time_ms), 0)
            FROM social_analytics a
            JOIN social_accounts s ON s.id = a.account_id
            WHERE s.status = 'connected'
              AND a.metric_date >= current_date - 30
        """
        params: dict = {}
        if platform:
            analytics_q += " AND s.platform = :p"
            params["p"] = platform

        r = await db.execute(text(analytics_q), params)
        row = r.fetchone()

        total_engagement = row[0]
        total_impressions = row[1]
        total_reach = row[2]
        total_link_clicks = row[3]
        total_shares = row[4]
        total_saves = row[5]
        total_video_views = row[6]
        total_views = row[9]
        total_interactions = row[10]
        avg_watch_time_ms = row[11]
        total_watch_time_ms = row[12]

        # Use views as impressions if impressions are 0 (IG Reels don't have impressions)
        if total_impressions == 0 and total_views > 0:
            total_impressions = total_views

        engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0

        return SocialSummaryResponse(
            total_followers=total_followers,
            total_engagement=total_engagement,
            total_impressions=total_impressions,
            total_reach=total_reach,
            engagement_rate=round(engagement_rate, 2),
            accounts_connected=accounts_connected,
            total_link_clicks=total_link_clicks,
            total_shares=total_shares,
            total_saves=total_saves,
            total_video_views=total_video_views,
            total_views=total_views,
            total_interactions=total_interactions,
            avg_watch_time_ms=avg_watch_time_ms,
            total_watch_time_ms=total_watch_time_ms,
        )
    except Exception as e:
        logger.error("Failed to fetch social analytics: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")


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
        accounts_query = select(SocialAccount).where(SocialAccount.status == "connected")
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
        logger.error("Failed to fetch sparkline data: %s", e)
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
            WHERE acc.status = 'connected'
              AND sa.metric_date >= :start_date AND sa.metric_date <= :end_date
        """)
        
        # Query last week's data  
        last_week_query = text("""
            SELECT 
                SUM(sa.engagement) as total_engagement,
                SUM(sa.impressions) as total_impressions,
                SUM(sa.followers_gained - sa.followers_lost) as net_followers
            FROM crm.social_analytics sa
            JOIN crm.social_accounts acc ON sa.account_id = acc.id
            WHERE acc.status = 'connected'
              AND sa.metric_date >= :start_date AND sa.metric_date <= :end_date
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
        logger.error("Failed to fetch trends data: %s", e)
        return {
            "followers": "+0.0%",
            "engagement": "+0.0%", 
            "impressions": "+0.0%"
        }


@router.get("/analytics/timeseries", response_model=List[SocialAnalyticsSeriesPoint])
async def get_analytics_timeseries(
    platform: Optional[str] = None,
    granularity: str = "daily",
    db: AsyncSession = Depends(get_crm_db)
):
    """Get aggregated analytics bars for the dashboard."""
    allowed_granularities = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
    }

    if granularity not in allowed_granularities:
        raise HTTPException(status_code=422, detail="granularity must be one of daily, weekly, monthly")

    try:
        end_date = date.today()
        start_date, buckets = _build_time_buckets(end_date, granularity)
        truncate_unit = allowed_granularities[granularity]
        platform_filter = "AND acc.platform = :platform" if platform else ""

        query = text(f"""
            SELECT
                date_trunc('{truncate_unit}', sa.metric_date::timestamp)::date AS bucket_date,
                COALESCE(SUM(sa.engagement), 0) AS engagement,
                COALESCE(SUM(sa.impressions), 0) AS impressions,
                COALESCE(SUM(sa.reach), 0) AS reach,
                COALESCE(SUM(sa.shares), 0) AS shares,
                COALESCE(SUM(sa.saves), 0) AS saves,
                COALESCE(SUM(sa.link_clicks), 0) AS link_clicks,
                COALESCE(SUM(sa.video_views), 0) AS video_views,
                COALESCE(SUM(sa.likes), 0) AS likes,
                COALESCE(SUM(sa.comments), 0) AS comments
            FROM crm.social_analytics sa
            JOIN crm.social_accounts acc ON sa.account_id = acc.id
            WHERE acc.status = 'connected'
              AND sa.metric_date >= :start_date
              AND sa.metric_date <= :end_date
              {platform_filter}
            GROUP BY bucket_date
            ORDER BY bucket_date ASC
        """)

        params = {
            "start_date": start_date,
            "end_date": end_date,
        }
        if platform:
            params["platform"] = platform

        result = await db.execute(query, params)
        rows = result.mappings().all()
        rows_by_bucket: Dict[date, Dict] = {
            row["bucket_date"]: row for row in rows
        }

        series = []
        for bucket in buckets:
            row = rows_by_bucket.get(bucket, {})
            series.append(
                SocialAnalyticsSeriesPoint(
                    bucket=bucket,
                    label=_format_bucket_label(bucket, granularity),
                    engagement=int(row.get("engagement", 0) or 0),
                    impressions=int(row.get("impressions", 0) or 0),
                    reach=int(row.get("reach", 0) or 0),
                    shares=int(row.get("shares", 0) or 0),
                    saves=int(row.get("saves", 0) or 0),
                    link_clicks=int(row.get("link_clicks", 0) or 0),
                    video_views=int(row.get("video_views", 0) or 0),
                    likes=int(row.get("likes", 0) or 0),
                    comments=int(row.get("comments", 0) or 0),
                )
            )

        return series
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch analytics timeseries: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch analytics timeseries")


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
                SocialAccount.status == "connected",
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
        logger.error("Failed to fetch platform analytics: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch platform analytics")


@router.get("/analytics/engagement-velocity")
async def get_engagement_velocity(
    media_id: Optional[str] = None,
    platform: str = "instagram",
    db: AsyncSession = Depends(get_crm_db)
):
    """Get engagement velocity over time — snapshots of metrics at each sync.
    Shows how likes/views/reach grow over time for a post or aggregate.
    Used for 'When people engage' line chart."""
    try:
        if media_id:
            # Per-post velocity
            r = await db.execute(text("""
                SELECT captured_at, views, likes, comments, shares, saves, reach, total_interactions
                FROM social_snapshots
                WHERE media_ig_id = :mid
                ORDER BY captured_at ASC
            """), {"mid": media_id})
        else:
            # Aggregate velocity — sum across all media per snapshot time
            r = await db.execute(text("""
                SELECT captured_at,
                    sum(views) as views, sum(likes) as likes, sum(comments) as comments,
                    sum(shares) as shares, sum(saves) as saves, sum(reach) as reach,
                    sum(total_interactions) as total_interactions
                FROM social_snapshots s
                JOIN social_accounts a ON a.id = s.account_id
                WHERE a.platform = :p AND a.status = 'connected'
                GROUP BY captured_at
                ORDER BY captured_at ASC
            """), {"p": platform})

        rows = r.fetchall()
        points = []
        prev = None
        for row in rows:
            point = {
                "time": row[0].isoformat(),
                "views": row[1],
                "likes": row[2],
                "comments": row[3],
                "shares": row[4],
                "saves": row[5],
                "reach": row[6],
                "interactions": row[7],
            }
            # Calculate deltas (velocity = change since last snapshot)
            if prev:
                point["delta_views"] = max(0, row[1] - prev[1])
                point["delta_likes"] = max(0, row[2] - prev[2])
                point["delta_reach"] = max(0, row[6] - prev[6])
            else:
                point["delta_views"] = row[1]
                point["delta_likes"] = row[2]
                point["delta_reach"] = row[6]
            prev = row
            points.append(point)

        return {"points": points, "total_snapshots": len(points)}
    except Exception as e:
        logger.error("Failed to fetch engagement velocity: %s", e)
        raise HTTPException(500, "Failed to fetch engagement velocity")


@router.post("/sync")
async def sync_social_data(db: AsyncSession = Depends(get_crm_db)):
    """Trigger real sync of all connected social media accounts (calls platform APIs)."""
    try:
        from app.api.social_sync import _get_accounts, SYNC_MAP, _try_refresh_token

        accounts = await _get_accounts(db)
        if not accounts:
            return {"message": "No connected accounts to sync", "synced_accounts": 0}

        results = []
        for acc in accounts:
            syncer = SYNC_MAP.get(acc["platform"])
            if syncer:
                try:
                    r = await syncer(db, acc)
                    if r.get("status") == "error":
                        new_token = await _try_refresh_token(db, acc)
                        if new_token:
                            acc["token"] = new_token
                            r = await syncer(db, acc)
                            r["token_refreshed"] = True
                    results.append(r)
                except Exception as e:
                    results.append({"platform": acc["platform"], "status": "error", "error": str(e)[:200]})

        await db.commit()
        return {
            "message": f"Synced {len(results)} accounts",
            "synced_accounts": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error("Failed to sync social data: %s", e)
        raise HTTPException(status_code=500, detail="Failed to sync social data")








