"""
Social media data sync — pulls real metrics from platform APIs into SocialAnalytics.
POST /api/social/sync       — sync all connected accounts
POST /api/social/sync/{platform} — sync specific platform

Auto-refreshes expired OAuth tokens on 401 and retries once.
"""
import logging
from datetime import datetime, date
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db

logger = logging.getLogger("social_sync")
router = APIRouter()

# ── Helpers ──────────────────────────────────────────────────────────

async def _get_accounts(db: AsyncSession, platform: Optional[str] = None):
    """Get connected accounts, optionally filtered by platform."""
    q = "SELECT id, platform, username, access_token, refresh_token FROM crm.social_accounts WHERE status = 'connected'"
    params = {}
    if platform:
        q += " AND platform = :p"
        params["p"] = platform
    r = await db.execute(text(q), params)
    return [{"id": row[0], "platform": row[1], "username": row[2], "token": row[3], "refresh": row[4]} for row in r.fetchall()]


async def _upsert_daily_analytics(
    db: AsyncSession, account_id: int, metric_date: date, **metrics
):
    """Insert or update daily analytics row (one per account per day)."""
    # Check if row exists
    r = await db.execute(text(
        "SELECT id FROM crm.social_analytics WHERE account_id = :aid AND metric_date = :d"
    ), {"aid": account_id, "d": metric_date})
    existing = r.fetchone()

    # Build SET clause from non-None metrics
    fields = {k: v for k, v in metrics.items() if v is not None}
    if not fields:
        return

    if existing:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        await db.execute(text(
            f"UPDATE crm.social_analytics SET {sets} WHERE id = :id"
        ), {**fields, "id": existing[0]})
    else:
        cols = ", ".join(["account_id", "metric_date"] + list(fields.keys()))
        vals = ", ".join([":aid", ":d"] + [f":{k}" for k in fields])
        await db.execute(text(
            f"INSERT INTO crm.social_analytics ({cols}) VALUES ({vals})"
        ), {"aid": account_id, "d": metric_date, **fields})


async def _update_account_stats(db: AsyncSession, account_id: int, **stats):
    """Update follower/following/post counts and last_synced."""
    fields = {k: v for k, v in stats.items() if v is not None}
    fields["last_synced"] = datetime.utcnow()
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    await db.execute(text(
        f"UPDATE crm.social_accounts SET {sets} WHERE id = :id"
    ), {**fields, "id": account_id})


# ── Token Refresh ────────────────────────────────────────────────────

async def _try_refresh_token(db: AsyncSession, acc: dict) -> Optional[str]:
    """Attempt to refresh an expired token using raw SQL + platform-specific refresh. Returns new token or None."""
    if not acc.get("refresh"):
        return None

    platform = acc["platform"]
    account_id = acc["id"]
    refresh_token = acc["refresh"]

    async def _get_setting(key: str) -> Optional[str]:
        r = await db.execute(text("SELECT value FROM public.settings WHERE key = :k"), {"k": key})
        row = r.fetchone()
        return row[0] if row else None

    try:
        new_token = None

        if platform == "youtube":
            client_id = await _get_setting("google_oauth_client_id")
            client_secret = await _get_setting("google_oauth_client_secret")
            if not client_id or not client_secret:
                return None
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://oauth2.googleapis.com/token", data={
                    "client_id": client_id, "client_secret": client_secret,
                    "grant_type": "refresh_token", "refresh_token": refresh_token,
                })
                resp.raise_for_status()
                new_token = resp.json()["access_token"]

        elif platform == "x":
            client_id = await _get_setting("x_client_id")
            client_secret = await _get_setting("x_client_secret")
            if not client_id or not client_secret:
                return None
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://api.x.com/2/oauth2/token", data={
                    "grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": client_id,
                }, auth=(client_id, client_secret))
                resp.raise_for_status()
                data = resp.json()
                new_token = data["access_token"]
                # X rotates refresh tokens
                if data.get("refresh_token"):
                    await db.execute(text("UPDATE crm.social_accounts SET refresh_token = :rt WHERE id = :id"),
                                     {"rt": data["refresh_token"], "id": account_id})

        elif platform in ("facebook", "instagram"):
            app_id = await _get_setting("meta_app_id")
            app_secret = await _get_setting("meta_app_secret")
            if not app_id or not app_secret:
                return None
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
                    "grant_type": "fb_exchange_token", "client_id": app_id,
                    "client_secret": app_secret, "fb_exchange_token": acc["token"],
                })
                resp.raise_for_status()
                new_token = resp.json()["access_token"]
        else:
            return None

        if new_token:
            await db.execute(text("UPDATE crm.social_accounts SET access_token = :t, status = 'connected' WHERE id = :id"),
                             {"t": new_token, "id": account_id})
            logger.info("Token refreshed for %s/@%s", platform, acc["username"])
            return new_token

    except Exception as e:
        logger.warning("Token refresh failed for %s/@%s: %s", platform, acc["username"], e)
        try:
            await db.rollback()
            await db.execute(text("SET search_path TO crm, public"))
            await db.execute(text("UPDATE social_accounts SET status = 'expired' WHERE id = :id"), {"id": account_id})
            await db.commit()
        except Exception:
            pass
        return None


# ── Platform Sync Functions ──────────────────────────────────────────

async def _sync_instagram(db: AsyncSession, acc: dict) -> dict:
    """Sync Instagram: profile stats + post-level metrics + account insights."""
    results = {"platform": "instagram", "username": acc["username"], "status": "ok", "posts_synced": 0}

    async with httpx.AsyncClient(timeout=15) as client:
        # Profile stats
        profile = await client.get("https://graph.instagram.com/me", params={
            "fields": "id,username,account_type,media_count,followers_count,follows_count",
            "access_token": acc["token"],
        })
        if profile.status_code == 200:
            p = profile.json()
            await _update_account_stats(db, acc["id"],
                follower_count=p.get("followers_count", 0),
                following_count=p.get("follows_count", 0),
                post_count=p.get("media_count", 0),
                username=p.get("username", acc["username"]),
            )
            results["followers"] = p.get("followers_count", 0)
        else:
            logger.warning("Instagram profile fetch failed: %s %s", profile.status_code, profile.text[:200])
            results["status"] = "partial"

        # Recent media with engagement
        media_resp = await client.get("https://graph.instagram.com/me/media", params={
            "fields": "id,timestamp,like_count,comments_count,media_type",
            "limit": 25,
            "access_token": acc["token"],
        })
        if media_resp.status_code == 200:
            posts = media_resp.json().get("data", [])
            total_likes = 0
            total_comments = 0
            for post in posts:
                total_likes += post.get("like_count", 0)
                total_comments += post.get("comments_count", 0)
            results["posts_synced"] = len(posts)

            # Store today's aggregated engagement
            await _upsert_daily_analytics(db, acc["id"], date.today(),
                likes=total_likes,
                comments=total_comments,
                engagement=total_likes + total_comments,
                engagement_rate=round((total_likes + total_comments) / max(len(posts), 1), 2) if posts else 0,
            )

        # Account insights (requires Business/Creator account)
        try:
            insights_resp = await client.get("https://graph.instagram.com/me/insights", params={
                "metric": "impressions,reach,profile_views",
                "period": "day",
                "access_token": acc["token"],
            })
            if insights_resp.status_code == 200:
                for metric in insights_resp.json().get("data", []):
                    name = metric.get("name")
                    values = metric.get("values", [])
                    if values:
                        val = values[-1].get("value", 0)
                        if name == "impressions":
                            await _upsert_daily_analytics(db, acc["id"], date.today(), impressions=val)
                        elif name == "reach":
                            await _upsert_daily_analytics(db, acc["id"], date.today(), reach=val)
                        elif name == "profile_views":
                            await _upsert_daily_analytics(db, acc["id"], date.today(), profile_views=val)
        except Exception as e:
            logger.warning("Instagram insights error: %s", e)

    return results


async def _sync_youtube(db: AsyncSession, acc: dict) -> dict:
    """Sync YouTube: channel stats + video metrics."""
    results = {"platform": "youtube", "username": acc["username"], "status": "ok", "videos_synced": 0}
    headers = {"Authorization": f"Bearer {acc['token']}"}

    async with httpx.AsyncClient(timeout=15) as client:
        # Channel stats
        ch_resp = await client.get("https://www.googleapis.com/youtube/v3/channels", params={
            "part": "statistics,snippet,contentDetails",
            "mine": "true",
        }, headers=headers)

        if ch_resp.status_code != 200:
            logger.warning("YouTube channel fetch failed: %s", ch_resp.status_code)
            results["status"] = "error"
            return results

        channels = ch_resp.json().get("items", [])
        if not channels:
            results["status"] = "no_channel"
            return results

        ch = channels[0]
        stats = ch.get("statistics", {})
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        vids = int(stats.get("videoCount", 0))

        await _update_account_stats(db, acc["id"],
            follower_count=subs,
            post_count=vids,
            username=ch["snippet"]["title"],
        )
        results["subscribers"] = subs

        # Recent videos
        uploads_id = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if uploads_id:
            pl_resp = await client.get("https://www.googleapis.com/youtube/v3/playlistItems", params={
                "part": "snippet",
                "playlistId": uploads_id,
                "maxResults": 10,
            }, headers=headers)

            if pl_resp.status_code == 200:
                items = pl_resp.json().get("items", [])
                video_ids = [i["snippet"]["resourceId"]["videoId"] for i in items
                             if i["snippet"]["resourceId"]["kind"] == "youtube#video"]

                if video_ids:
                    v_resp = await client.get("https://www.googleapis.com/youtube/v3/videos", params={
                        "part": "statistics",
                        "id": ",".join(video_ids[:10]),
                    }, headers=headers)

                    if v_resp.status_code == 200:
                        total_views = 0
                        total_likes = 0
                        total_comments = 0
                        for v in v_resp.json().get("items", []):
                            s = v.get("statistics", {})
                            total_views += int(s.get("viewCount", 0))
                            total_likes += int(s.get("likeCount", 0))
                            total_comments += int(s.get("commentCount", 0))

                        results["videos_synced"] = len(video_ids)
                        await _upsert_daily_analytics(db, acc["id"], date.today(),
                            video_views=total_views,
                            likes=total_likes,
                            comments=total_comments,
                            engagement=total_likes + total_comments,
                            impressions=total_views,
                        )

        # Store total channel views as reach
        await _upsert_daily_analytics(db, acc["id"], date.today(), reach=views)

    return results


async def _sync_facebook(db: AsyncSession, acc: dict) -> dict:
    """Sync Facebook: post engagement metrics."""
    results = {"platform": "facebook", "username": acc["username"], "status": "ok", "posts_synced": 0}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://graph.facebook.com/v21.0/me/posts", params={
            "fields": "id,created_time,shares,likes.summary(true),comments.summary(true)",
            "limit": 25,
            "access_token": acc["token"],
        })

        if resp.status_code != 200:
            logger.warning("Facebook posts fetch failed: %s", resp.status_code)
            results["status"] = "error"
            return results

        posts = resp.json().get("data", [])
        total_likes = 0
        total_comments = 0
        total_shares = 0
        for p in posts:
            total_likes += p.get("likes", {}).get("summary", {}).get("total_count", 0)
            total_comments += p.get("comments", {}).get("summary", {}).get("total_count", 0)
            total_shares += p.get("shares", {}).get("count", 0)

        results["posts_synced"] = len(posts)
        await _update_account_stats(db, acc["id"], post_count=len(posts))

        await _upsert_daily_analytics(db, acc["id"], date.today(),
            likes=total_likes,
            comments=total_comments,
            shares=total_shares,
            engagement=total_likes + total_comments + total_shares,
        )

    return results


async def _sync_x(db: AsyncSession, acc: dict) -> dict:
    """Sync X/Twitter: profile metrics + tweet engagement."""
    results = {"platform": "x", "username": acc["username"], "status": "ok", "tweets_synced": 0}
    headers = {"Authorization": f"Bearer {acc['token']}"}

    async with httpx.AsyncClient(timeout=15) as client:
        # Profile stats
        me_resp = await client.get("https://api.x.com/2/users/me", params={
            "user.fields": "public_metrics,profile_image_url",
        }, headers=headers)

        if me_resp.status_code == 200:
            me = me_resp.json().get("data", {})
            metrics = me.get("public_metrics", {})
            await _update_account_stats(db, acc["id"],
                follower_count=metrics.get("followers_count", 0),
                following_count=metrics.get("following_count", 0),
                post_count=metrics.get("tweet_count", 0),
                username=me.get("username", acc["username"]),
            )
            results["followers"] = metrics.get("followers_count", 0)

            # Get user ID for tweet lookup
            user_id = me.get("id")
            if user_id:
                # Recent tweets with metrics
                tweets_resp = await client.get(f"https://api.x.com/2/users/{user_id}/tweets", params={
                    "max_results": 10,
                    "tweet.fields": "created_at,public_metrics",
                }, headers=headers)

                if tweets_resp.status_code == 200:
                    tweets = tweets_resp.json().get("data", [])
                    total_likes = 0
                    total_retweets = 0
                    total_replies = 0
                    total_impressions = 0
                    for t in tweets:
                        pm = t.get("public_metrics", {})
                        total_likes += pm.get("like_count", 0)
                        total_retweets += pm.get("retweet_count", 0)
                        total_replies += pm.get("reply_count", 0)
                        total_impressions += pm.get("impression_count", 0)

                    results["tweets_synced"] = len(tweets)
                    await _upsert_daily_analytics(db, acc["id"], date.today(),
                        likes=total_likes,
                        shares=total_retweets,
                        comments=total_replies,
                        impressions=total_impressions,
                        engagement=total_likes + total_retweets + total_replies,
                    )
                else:
                    logger.warning("X tweets fetch failed: %s %s", tweets_resp.status_code, tweets_resp.text[:200])
        else:
            logger.warning("X profile fetch failed: %s %s", me_resp.status_code, me_resp.text[:200])
            results["status"] = "error"

    return results


SYNC_MAP = {
    "instagram": _sync_instagram,
    "youtube": _sync_youtube,
    "facebook": _sync_facebook,
    "x": _sync_x,
}


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/sync")
async def sync_all(db: AsyncSession = Depends(get_crm_db)):
    """Sync all connected social accounts."""
    accounts = await _get_accounts(db)
    if not accounts:
        return {"status": "no_accounts", "results": []}

    results = []
    for acc in accounts:
        syncer = SYNC_MAP.get(acc["platform"])
        if syncer:
            try:
                r = await syncer(db, acc)
                # If sync got errors (likely 401), try refreshing token and retry
                if r.get("status") == "error":
                    new_token = await _try_refresh_token(db, acc)
                    if new_token:
                        acc["token"] = new_token
                        r = await syncer(db, acc)
                        if r.get("status") != "error":
                            r["token_refreshed"] = True
                results.append(r)
            except Exception as e:
                logger.error("Sync failed for %s/@%s: %s", acc['platform'], acc['username'], e)
                results.append({"platform": acc["platform"], "username": acc["username"], "status": "error", "error": str(e)[:200]})

    await db.commit()
    return {"status": "ok", "synced_at": datetime.utcnow().isoformat(), "results": results}


@router.post("/sync/{platform}")
async def sync_platform(platform: str, db: AsyncSession = Depends(get_crm_db)):
    """Sync a specific platform."""
    syncer = SYNC_MAP.get(platform)
    if not syncer:
        raise HTTPException(400, f"Unknown platform: {platform}")

    accounts = await _get_accounts(db, platform)
    if not accounts:
        raise HTTPException(404, f"No connected {platform} account")

    results = []
    for acc in accounts:
        try:
            r = await syncer(db, acc)
            if r.get("status") == "error":
                new_token = await _try_refresh_token(db, acc)
                if new_token:
                    acc["token"] = new_token
                    r = await syncer(db, acc)
                    if r.get("status") != "error":
                        r["token_refreshed"] = True
            results.append(r)
        except Exception as e:
            logger.error("Sync failed for %s/@%s: %s", platform, acc['username'], e)
            results.append({"platform": platform, "username": acc["username"], "status": "error", "error": str(e)[:200]})

    await db.commit()
    return {"status": "ok", "synced_at": datetime.utcnow().isoformat(), "results": results}
