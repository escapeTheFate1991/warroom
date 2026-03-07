"""Content Tracker API — Real social media data from connected accounts."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from app.db.crm_db import get_crm_db

router = APIRouter()


@router.get("/content/tracker")
async def get_tracked_content(
    platform: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get content from connected social accounts with real metrics."""
    query = """
        SELECT 
            sa.id as account_id,
            sa.platform,
            sa.username,
            sa.follower_count,
            sa.post_count,
            sa.status
        FROM social_accounts sa
        WHERE sa.status = 'connected'
    """
    params: dict = {}
    if platform:
        query += " AND sa.platform = :platform"
        params["platform"] = platform

    query += " ORDER BY sa.follower_count DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    accounts = result.mappings().all()

    content_items = []
    for acc in accounts:
        content_items.append({
            "id": f"{acc['platform']}_{acc['account_id']}",
            "platform": acc["platform"],
            "username": acc["username"],
            "follower_count": acc["follower_count"] or 0,
            "post_count": acc["post_count"] or 0,
            "status": acc["status"],
        })

    return {"items": content_items, "total": len(content_items)}


@router.get("/content/tracker/summary")
async def get_content_summary(db: AsyncSession = Depends(get_crm_db)):
    """Get aggregated content metrics across all platforms."""
    result = await db.execute(text("""
        SELECT 
            COUNT(*) as total_accounts,
            COALESCE(SUM(follower_count), 0) as total_followers,
            COALESCE(SUM(post_count), 0) as total_posts
        FROM social_accounts
        WHERE status = 'connected'
    """))
    row = result.mappings().first()

    platform_result = await db.execute(text("""
        SELECT 
            platform,
            COUNT(*) as accounts,
            COALESCE(SUM(follower_count), 0) as followers,
            COALESCE(SUM(post_count), 0) as posts
        FROM social_accounts
        WHERE status = 'connected'
        GROUP BY platform
        ORDER BY followers DESC
    """))
    platforms = [dict(r) for r in platform_result.mappings().all()]

    return {
        "total_accounts": row["total_accounts"],
        "total_followers": row["total_followers"],
        "total_posts": row["total_posts"],
        "platforms": platforms,
    }


@router.get("/content/tracker/top-performing")
async def get_top_performing(limit: int = 10, db: AsyncSession = Depends(get_crm_db)):
    """Get top performing content by engagement metrics."""
    try:
        result = await db.execute(text("""
            SELECT 
                sa.platform,
                sa.username,
                sa.follower_count,
                sa.post_count
            FROM social_accounts sa
            WHERE sa.status = 'connected'
            ORDER BY sa.follower_count DESC
            LIMIT :limit
        """), {"limit": limit})
        accounts = [dict(r) for r in result.mappings().all()]
        return {"items": accounts}
    except Exception:
        return {"items": []}

