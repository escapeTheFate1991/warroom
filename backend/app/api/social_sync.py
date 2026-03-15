"""
Social media data sync — pulls real metrics from platform APIs into SocialAnalytics.
POST /api/social/sync       — sync all connected accounts
POST /api/social/sync/{platform} — sync specific platform

Auto-refreshes expired OAuth tokens on 401 and retries once.
"""
import logging
from datetime import datetime, date, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger("social_sync")
router = APIRouter()

# ── Helpers ──────────────────────────────────────────────────────────

async def _get_accounts(db: AsyncSession, org_id: int, platform: Optional[str] = None):
    """Get connected accounts, optionally filtered by platform."""
    q = "SELECT id, platform, username, access_token, refresh_token FROM crm.social_accounts WHERE status = 'connected' AND org_id = :org_id"
    params = {"org_id": org_id}
    if platform:
        q += " AND platform = :p"
        params["p"] = platform
    r = await db.execute(text(q), params)
    return [{"id": row[0], "platform": row[1], "username": row[2], "token": row[3], "refresh": row[4]} for row in r.fetchall()]


async def _upsert_daily_analytics(
    db: AsyncSession, account_id: int, metric_date: date, org_id: int, **metrics
):
    """Insert or update daily analytics row (one per account per day)."""
    # Check if row exists
    r = await db.execute(text(
        "SELECT id FROM crm.social_analytics WHERE account_id = :aid AND metric_date = :d AND org_id = :org_id"
    ), {"aid": account_id, "d": metric_date, "org_id": org_id})
    existing = r.fetchone()

    # Build SET clause from non-None metrics
    fields = {k: v for k, v in metrics.items() if v is not None}
    if not fields:
        return

    if existing:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        await db.execute(text(
            f"UPDATE crm.social_analytics SET {sets} WHERE id = :id AND org_id = :org_id"
        ), {**fields, "id": existing[0], "org_id": org_id})
    else:
        cols = ", ".join(["account_id", "metric_date", "org_id"] + list(fields.keys()))
        vals = ", ".join([":aid", ":d", ":org_id"] + [f":{k}" for k in fields])
        await db.execute(text(
            f"INSERT INTO crm.social_analytics ({cols}) VALUES ({vals})"
        ), {"aid": account_id, "d": metric_date, "org_id": org_id, **fields})


async def _update_account_stats(db: AsyncSession, account_id: int, org_id: int, **stats):
    """Update follower/following/post counts and last_synced."""
    fields = {k: v for k, v in stats.items() if v is not None}
    fields["last_synced"] = datetime.now(timezone.utc)
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    await db.execute(text(
        f"UPDATE crm.social_accounts SET {sets} WHERE id = :id AND org_id = :org_id"
    ), {**fields, "id": account_id, "org_id": org_id})


# ── Token Refresh ────────────────────────────────────────────────────

async def _try_refresh_token(db: AsyncSession, acc: dict, org_id: int) -> Optional[str]:
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
                    await db.execute(text("UPDATE crm.social_accounts SET refresh_token = :rt WHERE id = :id AND org_id = :org_id"),
                                     {"rt": data["refresh_token"], "id": account_id, "org_id": org_id})

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
            await db.execute(text("UPDATE crm.social_accounts SET access_token = :t, status = 'connected' WHERE id = :id AND org_id = :org_id"),
                             {"t": new_token, "id": account_id, "org_id": org_id})
            logger.info("Token refreshed for %s/@%s", platform, acc["username"])
            return new_token

    except Exception as e:
        logger.warning("Token refresh failed for %s/@%s: %s", platform, acc["username"], e)
        try:
            await db.rollback()
            await db.execute(text("SET search_path TO crm, public"))
            await db.execute(text("UPDATE social_accounts SET status = 'expired' WHERE id = :id AND org_id = :org_id"), {"id": account_id, "org_id": org_id})
            await db.commit()
        except Exception:
            pass
        return None


# ── Platform Sync Functions ──────────────────────────────────────────

async def _sync_instagram(db: AsyncSession, acc: dict, org_id: int) -> dict:
    """Sync Instagram: profile stats + per-media insights + account insights.

    Per-media metrics (Reels): views, reach, likes, comments, shares, saves,
    total_interactions, avg_watch_time, total_watch_time, replays.
    Account metrics: reach, profile_views, follows_and_unfollows.
    """
    results = {"platform": "instagram", "username": acc["username"], "status": "ok", "posts_synced": 0}
    import json as _json

    async with httpx.AsyncClient(timeout=20) as client:
        # 1. Profile stats
        profile = await client.get("https://graph.instagram.com/me", params={
            "fields": "id,username,account_type,media_count,followers_count,follows_count",
            "access_token": acc["token"],
        })
        if profile.status_code == 200:
            p = profile.json()
            await _update_account_stats(db, acc["id"], org_id,
                follower_count=p.get("followers_count", 0),
                following_count=p.get("follows_count", 0),
                post_count=p.get("media_count", 0),
                username=p.get("username", acc["username"]),
            )
            results["followers"] = p.get("followers_count", 0)
        else:
            logger.warning("Instagram profile fetch failed: %s %s", profile.status_code, profile.text[:200])
            results["status"] = "partial"

        # 2. Recent media + per-post insights
        media_resp = await client.get("https://graph.instagram.com/me/media", params={
            "fields": "id,timestamp,like_count,comments_count,media_type,permalink",
            "limit": 25,
            "access_token": acc["token"],
        })

        totals = {"likes": 0, "comments": 0, "shares": 0, "saves": 0, "views": 0,
                  "reach": 0, "total_interactions": 0, "avg_watch_time_ms": 0,
                  "total_watch_time_ms": 0, "video_views": 0}
        post_insights_list = []

        if media_resp.status_code == 200:
            posts = media_resp.json().get("data", [])
            results["posts_synced"] = len(posts)

            for post in posts:
                mid = post["id"]
                mtype = post.get("media_type", "")

                # Determine which metrics to request based on media type
                if mtype == "VIDEO":  # Reels
                    metrics = "reach,saved,shares,likes,comments,total_interactions,ig_reels_avg_watch_time,ig_reels_video_view_total_time,views"
                elif mtype == "CAROUSEL_ALBUM":
                    metrics = "reach,saved,shares,likes,comments,total_interactions"
                else:  # IMAGE
                    metrics = "reach,saved,shares,likes,comments,total_interactions"

                try:
                    ins_resp = await client.get(f"https://graph.instagram.com/{mid}/insights", params={
                        "metric": metrics,
                        "access_token": acc["token"],
                    })
                    post_data = {"id": mid, "type": mtype, "permalink": post.get("permalink", "")}

                    if ins_resp.status_code == 200:
                        for m in ins_resp.json().get("data", []):
                            name = m["name"]
                            val = m["values"][0]["value"] if m.get("values") else 0
                            post_data[name] = val

                            if name == "likes":
                                totals["likes"] += val
                            elif name == "comments":
                                totals["comments"] += val
                            elif name == "shares":
                                totals["shares"] += val
                            elif name == "saved":
                                totals["saves"] += val
                            elif name == "views":
                                totals["views"] += val
                                totals["video_views"] += val
                            elif name == "reach":
                                totals["reach"] += val
                            elif name == "total_interactions":
                                totals["total_interactions"] += val
                            elif name == "ig_reels_avg_watch_time":
                                totals["avg_watch_time_ms"] += val
                            elif name == "ig_reels_video_view_total_time":
                                totals["total_watch_time_ms"] += val

                    post_insights_list.append(post_data)

                    # Snapshot for engagement velocity tracking
                    await db.execute(text(
                        "INSERT INTO social_snapshots (account_id, media_ig_id, views, likes, comments, shares, saves, reach, total_interactions, avg_watch_time_ms, org_id) "
                        "VALUES (:aid, :mid, :views, :likes, :comments, :shares, :saves, :reach, :interactions, :awt, :org_id)"
                    ), {
                        "aid": acc["id"], "mid": mid,
                        "views": post_data.get("views", 0),
                        "likes": post_data.get("likes", 0),
                        "comments": post_data.get("comments", 0),
                        "shares": post_data.get("shares", 0),
                        "saves": post_data.get("saved", 0),
                        "reach": post_data.get("reach", 0),
                        "interactions": post_data.get("total_interactions", 0),
                        "awt": post_data.get("ig_reels_avg_watch_time", 0),
                        "org_id": org_id,
                    })
                except Exception as e:
                    logger.debug("Insights failed for %s: %s", mid, e)

            # Average the avg_watch_time across posts
            video_count = sum(1 for p in posts if p.get("media_type") == "VIDEO")
            if video_count > 0:
                totals["avg_watch_time_ms"] = totals["avg_watch_time_ms"] // video_count

            # Engagement = likes + comments + shares + saves
            total_engagement = totals["likes"] + totals["comments"] + totals["shares"] + totals["saves"]

            await _upsert_daily_analytics(db, acc["id"], date.today(), org_id,
                likes=totals["likes"],
                comments=totals["comments"],
                shares=totals["shares"],
                saves=totals["saves"],
                views=totals["views"],
                video_views=totals["video_views"],
                reach=totals["reach"],
                total_interactions=totals["total_interactions"],
                avg_watch_time_ms=totals["avg_watch_time_ms"],
                total_watch_time_ms=totals["total_watch_time_ms"],
                engagement=total_engagement,
                engagement_rate=round(total_engagement / max(len(posts), 1), 2),
                media_insights=_json.dumps(post_insights_list) if post_insights_list else None,
            )

        # 3. Account-level insights (daily)
        try:
            acct_resp = await client.get("https://graph.instagram.com/me/insights", params={
                "metric": "reach",
                "period": "day",
                "access_token": acc["token"],
            })
            if acct_resp.status_code == 200:
                for m in acct_resp.json().get("data", []):
                    vals = m.get("values", [])
                    if vals:
                        val = vals[-1].get("value", 0)
                        if m["name"] == "reach" and val > totals["reach"]:
                            await _upsert_daily_analytics(db, acc["id"], date.today(), org_id, reach=val)
        except Exception as e:
            logger.debug("Account insights error: %s", e)

    return results


async def _sync_youtube(db: AsyncSession, acc: dict, org_id: int) -> dict:
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

        await _update_account_stats(db, acc["id"], org_id,
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
                        await _upsert_daily_analytics(db, acc["id"], date.today(), org_id,
                            video_views=total_views,
                            likes=total_likes,
                            comments=total_comments,
                            engagement=total_likes + total_comments,
                            impressions=total_views,
                        )

        # Store total channel views as reach
        await _upsert_daily_analytics(db, acc["id"], date.today(), org_id, reach=views)

    return results


async def _sync_facebook(db: AsyncSession, acc: dict, org_id: int) -> dict:
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
        await _update_account_stats(db, acc["id"], org_id, post_count=len(posts))

        await _upsert_daily_analytics(db, acc["id"], date.today(), org_id,
            likes=total_likes,
            comments=total_comments,
            shares=total_shares,
            engagement=total_likes + total_comments + total_shares,
        )

    return results


async def _sync_x(db: AsyncSession, acc: dict, org_id: int) -> dict:
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
            await _update_account_stats(db, acc["id"], org_id,
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
                    await _upsert_daily_analytics(db, acc["id"], date.today(), org_id,
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
async def sync_all(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    """Sync all connected social accounts."""
    org_id = get_org_id(request)
    accounts = await _get_accounts(db, org_id)
    if not accounts:
        return {"status": "no_accounts", "results": []}

    results = []
    for acc in accounts:
        syncer = SYNC_MAP.get(acc["platform"])
        if syncer:
            try:
                r = await syncer(db, acc, org_id)
                # If sync got errors (likely 401), try refreshing token and retry
                if r.get("status") == "error":
                    new_token = await _try_refresh_token(db, acc, org_id)
                    if new_token:
                        acc["token"] = new_token
                        r = await syncer(db, acc, org_id)
                        if r.get("status") != "error":
                            r["token_refreshed"] = True
                results.append(r)
            except Exception as e:
                logger.error("Sync failed for %s/@%s: %s", acc['platform'], acc['username'], e)
                results.append({"platform": acc["platform"], "username": acc["username"], "status": "error", "error": str(e)[:200]})

    await db.commit()
    return {"status": "ok", "synced_at": datetime.now(timezone.utc).isoformat(), "results": results}


@router.post("/sync/{platform}")
async def sync_platform(request: Request, platform: str, db: AsyncSession = Depends(get_tenant_db)):
    """Sync a specific platform."""
    org_id = get_org_id(request)
    syncer = SYNC_MAP.get(platform)
    if not syncer:
        raise HTTPException(400, f"Unknown platform: {platform}")

    accounts = await _get_accounts(db, org_id, platform)
    if not accounts:
        raise HTTPException(404, f"No connected {platform} account")

    results = []
    for acc in accounts:
        try:
            r = await syncer(db, acc, org_id)
            if r.get("status") == "error":
                new_token = await _try_refresh_token(db, acc, org_id)
                if new_token:
                    acc["token"] = new_token
                    r = await syncer(db, acc, org_id)
                    if r.get("status") != "error":
                        r["token_refreshed"] = True
            results.append(r)
        except Exception as e:
            logger.error("Sync failed for %s/@%s: %s", platform, acc['username'], e)
            results.append({"platform": platform, "username": acc["username"], "status": "error", "error": str(e)[:200]})

    await db.commit()
    return {"status": "ok", "synced_at": datetime.now(timezone.utc).isoformat(), "results": results}
