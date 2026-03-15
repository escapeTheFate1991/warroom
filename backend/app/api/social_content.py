"""
Social Content API — fetch real posts, videos, and metrics from connected platforms.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger("social_content")
router = APIRouter()

# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

async def _get_account(db: AsyncSession, platform: str, org_id: int):
    r = await db.execute(
        text("SELECT id, access_token, refresh_token, username FROM crm.social_accounts WHERE platform = :p AND status = 'connected' AND org_id = :org_id LIMIT 1"),
        {"p": platform, "org_id": org_id},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(404, f"No connected {platform} account")
    return {"id": row[0], "token": row[1], "refresh": row[2], "username": row[3]}


# ═══════════════════════════════════════════════════════════
# Instagram — Media + Insights
# ═══════════════════════════════════════════════════════════

INSTAGRAM_GRAPH = "https://graph.instagram.com"

@router.get("/instagram/media")
async def instagram_media(request: Request, limit: int = 25, db: AsyncSession = Depends(get_tenant_db)):
    """Fetch recent Instagram posts with engagement metrics."""
    org_id = get_org_id(request)
    acc = await _get_account(db, "instagram", org_id)

    async with httpx.AsyncClient(timeout=15) as client:
        # Get user's media
        resp = await client.get(f"{INSTAGRAM_GRAPH}/me/media", params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
            "limit": limit,
            "access_token": acc["token"],
        })

        if resp.status_code == 400:
            data = resp.json()
            logger.error("Instagram API error: %s", data)
            raise HTTPException(400, data.get("error", {}).get("message", "Instagram API error"))

        if resp.status_code != 200:
            raise HTTPException(502, f"Instagram API returned {resp.status_code}")

        data = resp.json()
        posts = data.get("data", [])

        # Get profile info
        profile_resp = await client.get(f"{INSTAGRAM_GRAPH}/me", params={
            "fields": "id,username,account_type,media_count,followers_count,follows_count",
            "access_token": acc["token"],
        })
        profile = profile_resp.json() if profile_resp.status_code == 200 else {}

        return {
            "profile": {
                "username": profile.get("username", acc["username"]),
                "followers": profile.get("followers_count", 0),
                "following": profile.get("follows_count", 0),
                "posts": profile.get("media_count", 0),
                "account_type": profile.get("account_type", ""),
            },
            "media": [
                {
                    "id": p["id"],
                    "caption": p.get("caption", ""),
                    "type": p.get("media_type", ""),
                    "url": p.get("media_url", ""),
                    "thumbnail": p.get("thumbnail_url", p.get("media_url", "")),
                    "permalink": p.get("permalink", ""),
                    "timestamp": p.get("timestamp", ""),
                    "likes": p.get("like_count", 0),
                    "comments": p.get("comments_count", 0),
                }
                for p in posts
            ],
            "paging": data.get("paging", {}),
        }


@router.get("/instagram/insights")
async def instagram_insights(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    """Fetch Instagram account-level insights (requires Business/Creator account)."""
    org_id = get_org_id(request)
    acc = await _get_account(db, "instagram", org_id)

    async with httpx.AsyncClient(timeout=15) as client:
        # Account insights — last 30 days
        now = datetime.now(timezone.utc)
        resp = await client.get(f"{INSTAGRAM_GRAPH}/me/insights", params={
            "metric": "impressions,reach,profile_views",
            "period": "day",
            "since": int(now.timestamp() - 30 * 86400),
            "until": int(now.timestamp()),
            "access_token": acc["token"],
        })

        if resp.status_code != 200:
            logger.warning("Instagram insights error %s: %s", resp.status_code, resp.text[:200])
            return {"insights": [], "error": "Insights may require a Business or Creator account"}

        return {"insights": resp.json().get("data", [])}


# ═══════════════════════════════════════════════════════════
# YouTube — Videos + Analytics
# ═══════════════════════════════════════════════════════════

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

@router.get("/youtube/videos")
async def youtube_videos(request: Request, limit: int = 25, db: AsyncSession = Depends(get_tenant_db)):
    """Fetch recent YouTube videos with view/like/comment counts."""
    org_id = get_org_id(request)
    acc = await _get_account(db, "youtube", org_id)

    async with httpx.AsyncClient(timeout=15) as client:
        # Get channel info
        ch_resp = await client.get(f"{YOUTUBE_API}/channels", params={
            "part": "snippet,statistics,contentDetails",
            "mine": "true",
        }, headers={"Authorization": f"Bearer {acc['token']}"})

        if ch_resp.status_code != 200:
            logger.error("YouTube channels error: %s", ch_resp.text[:200])
            raise HTTPException(502, "Failed to fetch YouTube channel")

        channels = ch_resp.json().get("items", [])
        if not channels:
            return {"channel": {}, "videos": []}

        channel = channels[0]
        stats = channel.get("statistics", {})
        uploads_id = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")

        channel_info = {
            "id": channel["id"],
            "title": channel["snippet"]["title"],
            "thumbnail": channel["snippet"].get("thumbnails", {}).get("default", {}).get("url", ""),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0)),
        }

        # Update DB with real subscriber count
        await db.execute(
            text("UPDATE crm.social_accounts SET follower_count = :f, post_count = :p, username = :u WHERE id = :id AND org_id = :org_id"),
            {"f": channel_info["subscribers"], "p": channel_info["videos"], "u": channel_info["title"], "id": acc["id"], "org_id": org_id},
        )
        await db.commit()

        videos = []
        if uploads_id:
            # Get video IDs from uploads playlist
            pl_resp = await client.get(f"{YOUTUBE_API}/playlistItems", params={
                "part": "snippet",
                "playlistId": uploads_id,
                "maxResults": limit,
            }, headers={"Authorization": f"Bearer {acc['token']}"})

            if pl_resp.status_code == 200:
                items = pl_resp.json().get("items", [])
                video_ids = [item["snippet"]["resourceId"]["videoId"] for item in items if item["snippet"]["resourceId"]["kind"] == "youtube#video"]

                if video_ids:
                    # Get video stats
                    v_resp = await client.get(f"{YOUTUBE_API}/videos", params={
                        "part": "snippet,statistics,contentDetails",
                        "id": ",".join(video_ids[:25]),
                    }, headers={"Authorization": f"Bearer {acc['token']}"})

                    if v_resp.status_code == 200:
                        for v in v_resp.json().get("items", []):
                            s = v.get("statistics", {})
                            snip = v["snippet"]
                            videos.append({
                                "id": v["id"],
                                "title": snip.get("title", ""),
                                "description": snip.get("description", "")[:200],
                                "thumbnail": snip.get("thumbnails", {}).get("medium", {}).get("url", ""),
                                "published": snip.get("publishedAt", ""),
                                "views": int(s.get("viewCount", 0)),
                                "likes": int(s.get("likeCount", 0)),
                                "comments": int(s.get("commentCount", 0)),
                                "duration": v.get("contentDetails", {}).get("duration", ""),
                                "url": f"https://youtube.com/watch?v={v['id']}",
                            })

        return {"channel": channel_info, "videos": videos}


# ═══════════════════════════════════════════════════════════
# Facebook — Posts + Insights
# ═══════════════════════════════════════════════════════════

FB_GRAPH = "https://graph.facebook.com/v21.0"

@router.get("/facebook/posts")
async def facebook_posts(request: Request, limit: int = 25, db: AsyncSession = Depends(get_tenant_db)):
    """Fetch recent Facebook page/profile posts."""
    org_id = get_org_id(request)
    acc = await _get_account(db, "facebook", org_id)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{FB_GRAPH}/me/posts", params={
            "fields": "id,message,created_time,permalink_url,full_picture,shares,likes.summary(true),comments.summary(true)",
            "limit": limit,
            "access_token": acc["token"],
        })

        if resp.status_code != 200:
            logger.error("Facebook posts error: %s", resp.text[:200])
            return {"posts": [], "error": "Failed to fetch posts"}

        posts = resp.json().get("data", [])
        return {
            "posts": [
                {
                    "id": p["id"],
                    "message": p.get("message", ""),
                    "created": p.get("created_time", ""),
                    "permalink": p.get("permalink_url", ""),
                    "image": p.get("full_picture", ""),
                    "likes": p.get("likes", {}).get("summary", {}).get("total_count", 0),
                    "comments": p.get("comments", {}).get("summary", {}).get("total_count", 0),
                    "shares": p.get("shares", {}).get("count", 0),
                }
                for p in posts
            ]
        }


# ═══════════════════════════════════════════════════════════
# X (Twitter) — Tweets + Metrics
# ═══════════════════════════════════════════════════════════

X_API = "https://api.x.com/2"

@router.get("/x/tweets")
async def x_tweets(request: Request, limit: int = 25, db: AsyncSession = Depends(get_tenant_db)):
    """Fetch recent tweets with engagement metrics."""
    org_id = get_org_id(request)
    acc = await _get_account(db, "x", org_id)
    headers = {"Authorization": f"Bearer {acc['token']}"}

    async with httpx.AsyncClient(timeout=15) as client:
        # Get user ID
        me_resp = await client.get(f"{X_API}/users/me", params={
            "user.fields": "public_metrics,profile_image_url,username,name",
        }, headers=headers)

        if me_resp.status_code != 200:
            logger.error("X /users/me error: %s", me_resp.text[:200])
            raise HTTPException(502, f"X API returned {me_resp.status_code}")

        me = me_resp.json().get("data", {})
        user_id = me.get("id")
        metrics = me.get("public_metrics", {})

        # Update DB with real counts
        await db.execute(
            text("UPDATE crm.social_accounts SET follower_count = :f, following_count = :fw, post_count = :p, username = :u WHERE id = :id AND org_id = :org_id"),
            {"f": metrics.get("followers_count", 0), "fw": metrics.get("following_count", 0),
             "p": metrics.get("tweet_count", 0), "u": me.get("username", acc["username"]), "id": acc["id"], "org_id": org_id},
        )
        await db.commit()

        profile = {
            "username": me.get("username", ""),
            "name": me.get("name", ""),
            "followers": metrics.get("followers_count", 0),
            "following": metrics.get("following_count", 0),
            "tweets": metrics.get("tweet_count", 0),
            "profile_image": me.get("profile_image_url", ""),
        }

        # Get recent tweets
        tweets = []
        if user_id:
            t_resp = await client.get(f"{X_API}/users/{user_id}/tweets", params={
                "max_results": min(limit, 100),
                "tweet.fields": "created_at,public_metrics,text",
            }, headers=headers)

            if t_resp.status_code == 200:
                for t in t_resp.json().get("data", []):
                    pm = t.get("public_metrics", {})
                    tweets.append({
                        "id": t["id"],
                        "text": t.get("text", ""),
                        "created_at": t.get("created_at", ""),
                        "likes": pm.get("like_count", 0),
                        "retweets": pm.get("retweet_count", 0),
                        "replies": pm.get("reply_count", 0),
                        "quotes": pm.get("quote_count", 0),
                        "impressions": pm.get("impression_count", 0),
                        "url": f"https://x.com/{me.get('username', '')}/status/{t['id']}",
                    })
            else:
                logger.warning("X tweets fetch failed: %s %s", t_resp.status_code, t_resp.text[:200])

        return {"profile": profile, "tweets": tweets}


# ═══════════════════════════════════════════════════════════
# Cross-platform summary
# ═══════════════════════════════════════════════════════════

@router.get("/summary")
async def content_summary(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    """Quick summary of all connected platforms — content counts and top posts."""
    org_id = get_org_id(request)
    r = await db.execute(
        text("SELECT platform, username, follower_count, post_count, following_count FROM crm.social_accounts WHERE status = 'connected' AND org_id = :org_id"),
        {"org_id": org_id}
    )
    accounts = r.fetchall()

    return {
        "platforms": [
            {
                "platform": a[0],
                "username": a[1],
                "followers": a[2],
                "posts": a[3],
                "following": a[4],
            }
            for a in accounts
        ],
        "total_followers": sum(a[2] or 0 for a in accounts),
        "total_posts": sum(a[3] or 0 for a in accounts),
        "connected_count": len(accounts),
    }
