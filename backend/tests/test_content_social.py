"""Tests for Content AI, Content Tracker, and Social Content endpoints."""

import os, sys, json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import jwt, pytest, pytest_asyncio, httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://x:x@localhost/fake")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://x:x@localhost/fake")
os.environ.setdefault("OPENCLAW_AUTH_TOKEN", "test-token")
sys.modules.setdefault("app.services.notify", MagicMock(send_notification=AsyncMock()))

from sqlalchemy.ext.asyncio import AsyncSession

JWT_SECRET = "test-secret-key-for-tests"


class FakeResult:
    def __init__(self, items=None):
        self._items = items or []
    def scalars(self): return self
    def all(self): return self._items
    def first(self): return self._items[0] if self._items else None
    def fetchall(self): return self._items
    def fetchone(self): return self._items[0] if self._items else None
    def mappings(self): return self


def auth_hdr():
    p = {"user_id": 1, "email": "t@t.io", "is_superadmin": True,
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return {"Authorization": f"Bearer {jwt.encode(p, JWT_SECRET, algorithm='HS256')}"}


def _mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=FakeResult())
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _resp(status_code=200, json_data=None, text_body=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text_body
    return r


def _mock_social_client(*responses):
    """Mock httpx.AsyncClient so `async with httpx.AsyncClient() as c:` yields a mock."""
    mock_inst = AsyncMock()
    if len(responses) == 1:
        mock_inst.get = AsyncMock(return_value=responses[0])
    else:
        mock_inst.get = AsyncMock(side_effect=list(responses))
    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_inst)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_cls


def _fake_account():
    return FakeResult([(1, "fake-token", "refresh-tok", "testuser")])


@pytest_asyncio.fixture
async def client():
    from app.main import app
    from app.db.crm_db import get_crm_db
    db = _mock_db()
    app.dependency_overrides[get_crm_db] = lambda: db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        c._test_db = db
        yield c
    app.dependency_overrides.clear()


PATCH_OC = "app.api.content_ai.call_openclaw"
PATCH_SOCIAL_HTTPX = "app.api.social_content.httpx.AsyncClient"


# ═══════════════════════════════════════════════════════════
# Content AI Tests
# ═══════════════════════════════════════════════════════════

class TestContentAIIdeas:
    @pytest.mark.asyncio
    async def test_success(self, client):
        with patch(PATCH_OC, new_callable=AsyncMock, return_value='[{"title":"idea1"}]'):
            r = await client.post("/api/content/ai/ideas",
                json={"niche": "roofing", "platform": "instagram", "count": 3}, headers=auth_hdr())
        assert r.status_code == 200
        assert r.json()["platform"] == "instagram"

    @pytest.mark.asyncio
    async def test_missing_niche(self, client):
        r = await client.post("/api/content/ai/ideas", json={"platform": "instagram"}, headers=auth_hdr())
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_no_auth_token(self, client):
        with patch.dict(os.environ, {"OPENCLAW_AUTH_TOKEN": ""}):
            r = await client.post("/api/content/ai/ideas",
                json={"niche": "roofing", "platform": "instagram"}, headers=auth_hdr())
        assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_api_error(self, client):
        from fastapi import HTTPException
        with patch(PATCH_OC, new_callable=AsyncMock, side_effect=HTTPException(502, "fail")):
            r = await client.post("/api/content/ai/ideas",
                json={"niche": "roofing", "platform": "instagram"}, headers=auth_hdr())
        assert r.status_code == 502


class TestContentAIScript:
    @pytest.mark.asyncio
    async def test_success(self, client):
        with patch(PATCH_OC, new_callable=AsyncMock, return_value="Hook: Hey!"):
            r = await client.post("/api/content/ai/script",
                json={"topic": "roofing tips", "platform": "youtube"}, headers=auth_hdr())
        assert r.status_code == 200
        d = r.json()
        assert "script" in d and d["platform"] == "youtube" and d["topic"] == "roofing tips"

    @pytest.mark.asyncio
    async def test_with_options(self, client):
        with patch(PATCH_OC, new_callable=AsyncMock, return_value="Script"):
            r = await client.post("/api/content/ai/script",
                json={"topic": "t", "platform": "instagram", "style": "entertaining", "duration": "30s"},
                headers=auth_hdr())
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_topic(self, client):
        r = await client.post("/api/content/ai/script", json={"platform": "youtube"}, headers=auth_hdr())
        assert r.status_code == 422



class TestContentAICaptions:
    @pytest.mark.asyncio
    async def test_success(self, client):
        with patch(PATCH_OC, new_callable=AsyncMock, return_value="Great caption!"):
            r = await client.post("/api/content/ai/captions",
                json={"topic": "roof repair", "platform": "instagram"}, headers=auth_hdr())
        assert r.status_code == 200 and "caption" in r.json()

    @pytest.mark.asyncio
    async def test_no_hashtags(self, client):
        with patch(PATCH_OC, new_callable=AsyncMock, return_value="No tags"):
            r = await client.post("/api/content/ai/captions",
                json={"topic": "roof", "platform": "facebook", "include_hashtags": False, "include_cta": False},
                headers=auth_hdr())
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_topic(self, client):
        r = await client.post("/api/content/ai/captions", json={"platform": "ig"}, headers=auth_hdr())
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════
# Content Tracker Tests
# ═══════════════════════════════════════════════════════════

class TestContentTracker:
    @pytest.mark.asyncio
    async def test_get_tracked_content(self, client):
        db = client._test_db
        db.execute.return_value = FakeResult([
            {"account_id": 1, "platform": "instagram", "username": "testuser",
             "follower_count": 5000, "post_count": 120, "status": "connected"},
        ])
        r = await client.get("/api/content/tracker", headers=auth_hdr())
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["platform"] == "instagram"

    @pytest.mark.asyncio
    async def test_with_platform_filter(self, client):
        db = client._test_db
        db.execute.return_value = FakeResult([
            {"account_id": 2, "platform": "youtube", "username": "ytchan",
             "follower_count": 10000, "post_count": 50, "status": "connected"},
        ])
        r = await client.get("/api/content/tracker?platform=youtube", headers=auth_hdr())
        assert r.status_code == 200
        assert r.json()["items"][0]["platform"] == "youtube"

    @pytest.mark.asyncio
    async def test_empty(self, client):
        client._test_db.execute.return_value = FakeResult([])
        r = await client.get("/api/content/tracker", headers=auth_hdr())
        assert r.status_code == 200 and r.json()["total"] == 0


class TestContentTrackerSummary:
    @pytest.mark.asyncio
    async def test_get_summary(self, client):
        db = client._test_db
        summary_result = FakeResult([
            {"total_accounts": 3, "total_followers": 15000, "total_posts": 300}
        ])
        platform_result = FakeResult([
            {"platform": "instagram", "accounts": 1, "followers": 8000, "posts": 200},
            {"platform": "youtube", "accounts": 1, "followers": 5000, "posts": 50},
        ])
        db.execute.side_effect = [summary_result, platform_result]
        r = await client.get("/api/content/tracker/summary", headers=auth_hdr())
        assert r.status_code == 200
        d = r.json()
        assert d["total_accounts"] == 3 and d["total_followers"] == 15000
        assert len(d["platforms"]) == 2


class TestContentTrackerTopPerforming:
    @pytest.mark.asyncio
    async def test_get_top(self, client):
        client._test_db.execute.return_value = FakeResult([
            {"platform": "instagram", "username": "top1", "follower_count": 50000, "post_count": 500},
        ])
        r = await client.get("/api/content/tracker/top-performing", headers=auth_hdr())
        assert r.status_code == 200 and len(r.json()["items"]) == 1

    @pytest.mark.asyncio
    async def test_empty(self, client):
        client._test_db.execute.return_value = FakeResult([])
        r = await client.get("/api/content/tracker/top-performing", headers=auth_hdr())
        assert r.status_code == 200 and r.json()["items"] == []


# ═══════════════════════════════════════════════════════════
# Instagram Tests
# ═══════════════════════════════════════════════════════════

class TestInstagramMedia:
    @pytest.mark.asyncio
    async def test_success(self, client):
        client._test_db.execute.return_value = _fake_account()
        media_resp = _resp(200, {
            "data": [{"id": "1", "caption": "test", "media_type": "IMAGE",
                      "media_url": "https://x.com/1.jpg", "permalink": "https://ig.com/p/1",
                      "timestamp": "2024-01-01T00:00:00Z", "like_count": 100, "comments_count": 10}],
            "paging": {}
        })
        profile_resp = _resp(200, {
            "username": "testuser", "followers_count": 5000,
            "follows_count": 200, "media_count": 120, "account_type": "BUSINESS"
        })
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(media_resp, profile_resp)):
            r = await client.get("/api/social/content/instagram/media", headers=auth_hdr())
        assert r.status_code == 200
        d = r.json()
        assert d["profile"]["username"] == "testuser"
        assert len(d["media"]) == 1 and d["media"][0]["likes"] == 100

    @pytest.mark.asyncio
    async def test_no_account(self, client):
        client._test_db.execute.return_value = FakeResult([])
        r = await client.get("/api/social/content/instagram/media", headers=auth_hdr())
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_api_error(self, client):
        client._test_db.execute.return_value = _fake_account()
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(_resp(502, text_body="Bad Gateway"))):
            r = await client.get("/api/social/content/instagram/media", headers=auth_hdr())
        assert r.status_code == 502


class TestInstagramInsights:
    @pytest.mark.asyncio
    async def test_success(self, client):
        client._test_db.execute.return_value = _fake_account()
        resp = _resp(200, {"data": [{"name": "impressions", "values": [{"value": 1000}]}]})
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(resp)):
            r = await client.get("/api/social/content/instagram/insights", headers=auth_hdr())
        assert r.status_code == 200 and len(r.json()["insights"]) == 1

    @pytest.mark.asyncio
    async def test_not_business(self, client):
        client._test_db.execute.return_value = _fake_account()
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(_resp(400, text_body="Not eligible"))):
            r = await client.get("/api/social/content/instagram/insights", headers=auth_hdr())
        assert r.status_code == 200 and "error" in r.json()


# ═══════════════════════════════════════════════════════════
# YouTube Tests
# ═══════════════════════════════════════════════════════════

class TestYouTubeVideos:
    @pytest.mark.asyncio
    async def test_success(self, client):
        client._test_db.execute.return_value = _fake_account()
        ch = _resp(200, {"items": [{
            "id": "UC123",
            "snippet": {"title": "Ch", "thumbnails": {"default": {"url": "https://yt.com/t.jpg"}}},
            "statistics": {"subscriberCount": "10000", "viewCount": "500000", "videoCount": "100"},
            "contentDetails": {"relatedPlaylists": {"uploads": "UU123"}}
        }]})
        pl = _resp(200, {"items": [
            {"snippet": {"resourceId": {"kind": "youtube#video", "videoId": "vid1"}}}
        ]})
        vid = _resp(200, {"items": [{
            "id": "vid1",
            "snippet": {"title": "Test", "description": "d",
                "thumbnails": {"medium": {"url": "https://yt.com/v.jpg"}},
                "publishedAt": "2024-01-01T00:00:00Z"},
            "statistics": {"viewCount": "5000", "likeCount": "200", "commentCount": "30"},
            "contentDetails": {"duration": "PT5M30S"}
        }]})
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(ch, pl, vid)):
            r = await client.get("/api/social/content/youtube/videos", headers=auth_hdr())
        assert r.status_code == 200
        d = r.json()
        assert d["channel"]["subscribers"] == 10000
        assert len(d["videos"]) == 1 and d["videos"][0]["views"] == 5000

    @pytest.mark.asyncio
    async def test_no_account(self, client):
        client._test_db.execute.return_value = FakeResult([])
        r = await client.get("/api/social/content/youtube/videos", headers=auth_hdr())
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_api_error(self, client):
        client._test_db.execute.return_value = _fake_account()
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(_resp(403, text_body="Forbidden"))):
            r = await client.get("/api/social/content/youtube/videos", headers=auth_hdr())
        assert r.status_code == 502

    @pytest.mark.asyncio
    async def test_no_channels(self, client):
        client._test_db.execute.return_value = _fake_account()
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(_resp(200, {"items": []}))):
            r = await client.get("/api/social/content/youtube/videos", headers=auth_hdr())
        assert r.status_code == 200 and r.json()["videos"] == []


# ═══════════════════════════════════════════════════════════
# Facebook Tests
# ═══════════════════════════════════════════════════════════

class TestFacebookPosts:
    @pytest.mark.asyncio
    async def test_success(self, client):
        client._test_db.execute.return_value = _fake_account()
        resp = _resp(200, {"data": [{
            "id": "fb_1", "message": "Hello Facebook!",
            "created_time": "2024-01-01T00:00:00Z",
            "permalink_url": "https://fb.com/post/1",
            "full_picture": "https://fb.com/pic1.jpg",
            "likes": {"summary": {"total_count": 50}},
            "comments": {"summary": {"total_count": 5}},
            "shares": {"count": 3}
        }]})
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(resp)):
            r = await client.get("/api/social/content/facebook/posts", headers=auth_hdr())
        assert r.status_code == 200
        d = r.json()
        assert len(d["posts"]) == 1 and d["posts"][0]["likes"] == 50 and d["posts"][0]["shares"] == 3

    @pytest.mark.asyncio
    async def test_no_account(self, client):
        client._test_db.execute.return_value = FakeResult([])
        r = await client.get("/api/social/content/facebook/posts", headers=auth_hdr())
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_api_error(self, client):
        client._test_db.execute.return_value = _fake_account()
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(_resp(500, text_body="Error"))):
            r = await client.get("/api/social/content/facebook/posts", headers=auth_hdr())
        assert r.status_code == 200 and "error" in r.json()


# ═══════════════════════════════════════════════════════════
# X (Twitter) Tests
# ═══════════════════════════════════════════════════════════

class TestXTweets:
    @pytest.mark.asyncio
    async def test_success(self, client):
        client._test_db.execute.return_value = _fake_account()
        me = _resp(200, {"data": {
            "id": "user123", "username": "testx", "name": "Test X",
            "profile_image_url": "https://x.com/pic.jpg",
            "public_metrics": {"followers_count": 2000, "following_count": 500, "tweet_count": 800}
        }})
        tweets = _resp(200, {"data": [{
            "id": "t1", "text": "Hello X!", "created_at": "2024-01-01T00:00:00Z",
            "public_metrics": {"like_count": 25, "retweet_count": 5,
                "reply_count": 3, "quote_count": 1, "impression_count": 1000}
        }]})
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(me, tweets)):
            r = await client.get("/api/social/content/x/tweets", headers=auth_hdr())
        assert r.status_code == 200
        d = r.json()
        assert d["profile"]["username"] == "testx" and d["profile"]["followers"] == 2000
        assert len(d["tweets"]) == 1 and d["tweets"][0]["likes"] == 25

    @pytest.mark.asyncio
    async def test_no_account(self, client):
        client._test_db.execute.return_value = FakeResult([])
        r = await client.get("/api/social/content/x/tweets", headers=auth_hdr())
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_api_error(self, client):
        client._test_db.execute.return_value = _fake_account()
        with patch(PATCH_SOCIAL_HTTPX, _mock_social_client(_resp(401, text_body="Unauthorized"))):
            r = await client.get("/api/social/content/x/tweets", headers=auth_hdr())
        assert r.status_code == 502


# ═══════════════════════════════════════════════════════════
# Cross-platform Summary Tests
# ═══════════════════════════════════════════════════════════

class TestContentSummary:
    @pytest.mark.asyncio
    async def test_success(self, client):
        client._test_db.execute.return_value = FakeResult([
            ("instagram", "iguser", 5000, 120, 200),
            ("youtube", "ytchan", 10000, 50, 0),
        ])
        r = await client.get("/api/social/content/summary", headers=auth_hdr())
        assert r.status_code == 200
        d = r.json()
        assert d["connected_count"] == 2 and d["total_followers"] == 15000
        assert d["total_posts"] == 170 and len(d["platforms"]) == 2

    @pytest.mark.asyncio
    async def test_empty(self, client):
        client._test_db.execute.return_value = FakeResult([])
        r = await client.get("/api/social/content/summary", headers=auth_hdr())
        assert r.status_code == 200
        assert r.json()["connected_count"] == 0 and r.json()["total_followers"] == 0


# ═══════════════════════════════════════════════════════════
# Social Sync / Analytics / Scheduler Tests
# ═══════════════════════════════════════════════════════════

class TestSocialSync:
    @pytest.mark.asyncio
    async def test_sync_all_uses_canonical_response_shape(self, client):
        account = [{"id": 1, "platform": "instagram", "username": "iguser", "token": "tok", "refresh": "ref"}]
        syncer = AsyncMock(return_value={"platform": "instagram", "username": "iguser", "status": "ok", "posts_synced": 3})

        with patch("app.api.social_sync._get_accounts", new=AsyncMock(return_value=account)), \
             patch("app.api.social_sync._try_refresh_token", new=AsyncMock(return_value=None)), \
             patch.dict("app.api.social_sync.SYNC_MAP", {"instagram": syncer}, clear=True):
            r = await client.post("/api/social/sync", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert "synced_at" in d
        assert d["results"][0]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_sync_all_does_not_mark_token_refreshed_when_retry_still_fails(self, client):
        account = [{"id": 1, "platform": "instagram", "username": "iguser", "token": "tok", "refresh": "ref"}]
        syncer = AsyncMock(side_effect=[
            {"platform": "instagram", "username": "iguser", "status": "error"},
            {"platform": "instagram", "username": "iguser", "status": "error"},
        ])

        with patch("app.api.social_sync._get_accounts", new=AsyncMock(return_value=account)), \
             patch("app.api.social_sync._try_refresh_token", new=AsyncMock(return_value="new-token")), \
             patch.dict("app.api.social_sync.SYNC_MAP", {"instagram": syncer}, clear=True):
            r = await client.post("/api/social/sync", headers=auth_hdr())

        assert r.status_code == 200
        result = r.json()["results"][0]
        assert result["status"] == "error"
        assert "token_refreshed" not in result


class TestSocialSyncPlatform:
    @pytest.mark.asyncio
    async def test_sync_platform_success(self, client):
        account = [{"id": 1, "platform": "instagram", "username": "iguser", "token": "tok", "refresh": "ref"}]
        syncer = AsyncMock(return_value={"platform": "instagram", "username": "iguser", "status": "ok"})

        with patch("app.api.social_sync._get_accounts", new=AsyncMock(return_value=account)), \
             patch("app.api.social_sync._try_refresh_token", new=AsyncMock(return_value=None)), \
             patch.dict("app.api.social_sync.SYNC_MAP", {"instagram": syncer}, clear=True):
            r = await client.post("/api/social/sync/instagram", headers=auth_hdr())

        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["results"][0]["platform"] == "instagram"


class TestSocialSyncHelpers:
    @pytest.mark.asyncio
    async def test_upsert_daily_analytics_inserts_new_row(self):
        from app.api.social_sync import _upsert_daily_analytics

        db = _mock_db()
        db.execute = AsyncMock(side_effect=[FakeResult([]), FakeResult([])])

        await _upsert_daily_analytics(db, 7, date(2024, 1, 5), likes=12, comments=3, reach=50)

        insert_call = db.execute.await_args_list[1]
        assert "INSERT INTO crm.social_analytics" in str(insert_call.args[0])
        assert insert_call.args[1]["aid"] == 7
        assert insert_call.args[1]["d"] == date(2024, 1, 5)
        assert insert_call.args[1]["likes"] == 12

    @pytest.mark.asyncio
    async def test_upsert_daily_analytics_updates_existing_row(self):
        from app.api.social_sync import _upsert_daily_analytics

        db = _mock_db()
        db.execute = AsyncMock(side_effect=[FakeResult([(99,)]), FakeResult([])])

        await _upsert_daily_analytics(db, 7, date(2024, 1, 5), likes=15, comments=4)

        update_call = db.execute.await_args_list[1]
        assert "UPDATE crm.social_analytics SET" in str(update_call.args[0])
        assert update_call.args[1]["id"] == 99
        assert update_call.args[1]["likes"] == 15
        assert update_call.args[1]["comments"] == 4

    @pytest.mark.asyncio
    async def test_update_account_stats_sets_last_synced(self):
        from app.api.social_sync import _update_account_stats

        db = _mock_db()

        await _update_account_stats(db, 5, follower_count=100, post_count=9)

        execute_call = db.execute.await_args
        assert "UPDATE crm.social_accounts SET" in str(execute_call.args[0])
        assert execute_call.args[1]["id"] == 5
        assert execute_call.args[1]["follower_count"] == 100
        assert isinstance(execute_call.args[1]["last_synced"], datetime)

    @pytest.mark.asyncio
    async def test_sync_instagram_writes_snapshots_and_daily_rollups(self):
        from app.api.social_sync import _sync_instagram

        db = _mock_db()
        db.execute = AsyncMock(return_value=FakeResult([]))
        acc = {"id": 1, "platform": "instagram", "username": "iguser", "token": "tok"}

        profile_resp = _resp(200, {
            "username": "iguser",
            "followers_count": 1200,
            "follows_count": 80,
            "media_count": 25,
        })
        media_resp = _resp(200, {"data": [
            {"id": "m1", "media_type": "VIDEO", "permalink": "https://ig/p/1"},
            {"id": "m2", "media_type": "IMAGE", "permalink": "https://ig/p/2"},
        ]})
        video_insights = _resp(200, {"data": [
            {"name": "likes", "values": [{"value": 10}]},
            {"name": "comments", "values": [{"value": 2}]},
            {"name": "shares", "values": [{"value": 1}]},
            {"name": "saved", "values": [{"value": 3}]},
            {"name": "views", "values": [{"value": 200}]},
            {"name": "reach", "values": [{"value": 100}]},
            {"name": "total_interactions", "values": [{"value": 16}]},
            {"name": "ig_reels_avg_watch_time", "values": [{"value": 500}]},
            {"name": "ig_reels_video_view_total_time", "values": [{"value": 5000}]},
        ]})
        image_insights = _resp(200, {"data": [
            {"name": "likes", "values": [{"value": 4}]},
            {"name": "comments", "values": [{"value": 1}]},
            {"name": "shares", "values": [{"value": 0}]},
            {"name": "saved", "values": [{"value": 1}]},
            {"name": "reach", "values": [{"value": 80}]},
            {"name": "total_interactions", "values": [{"value": 6}]},
        ]})
        account_insights = _resp(200, {"data": [{"name": "reach", "values": [{"value": 400}]}]})

        with patch("app.api.social_sync.httpx.AsyncClient", _mock_social_client(
            profile_resp,
            media_resp,
            video_insights,
            image_insights,
            account_insights,
        )), patch("app.api.social_sync._update_account_stats", new=AsyncMock()) as update_stats, \
             patch("app.api.social_sync._upsert_daily_analytics", new=AsyncMock()) as upsert_daily:
            result = await _sync_instagram(db, acc)

        assert result["status"] == "ok"
        assert result["posts_synced"] == 2
        update_stats.assert_awaited_once()

        snapshot_calls = [
            call for call in db.execute.await_args_list
            if "INSERT INTO social_snapshots" in str(call.args[0])
        ]
        assert len(snapshot_calls) == 2

        first_upsert = upsert_daily.await_args_list[0]
        assert first_upsert.args[1] == 1
        assert first_upsert.kwargs["likes"] == 14
        assert first_upsert.kwargs["comments"] == 3
        assert first_upsert.kwargs["shares"] == 1
        assert first_upsert.kwargs["saves"] == 4
        assert first_upsert.kwargs["views"] == 200
        assert first_upsert.kwargs["video_views"] == 200
        assert first_upsert.kwargs["reach"] == 180
        assert first_upsert.kwargs["engagement"] == 22
        assert first_upsert.kwargs["avg_watch_time_ms"] == 500
        assert first_upsert.kwargs["total_watch_time_ms"] == 5000
        assert json.loads(first_upsert.kwargs["media_insights"])[0]["id"] == "m1"

        second_upsert = upsert_daily.await_args_list[1]
        assert second_upsert.kwargs == {"reach": 400}


class TestSocialAnalytics:
    @pytest.mark.asyncio
    async def test_summary_uses_views_when_impressions_are_zero(self, client):
        client._test_db.execute.side_effect = [
            FakeResult([(1, 5000)]),
            FakeResult([(250, 0, 100, 30, 4, 3, 200, 150, 25, 900, 275, 1200, 36000)]),
        ]

        r = await client.get("/api/social/analytics", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d["accounts_connected"] == 1
        assert d["total_impressions"] == 900
        assert d["total_views"] == 900
        assert d["total_interactions"] == 275
        assert d["engagement_rate"] == pytest.approx(27.78, abs=0.01)

    @pytest.mark.asyncio
    async def test_summary_exposes_instagram_rollups_from_recent_sync_data(self, client):
        client._test_db.execute.side_effect = [
            FakeResult([(1, 1200)]),
            FakeResult([(22, 200, 400, 15, 1, 4, 200, 14, 3, 200, 22, 500, 5000)]),
        ]

        r = await client.get("/api/social/analytics?platform=instagram", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d["total_followers"] == 1200
        assert d["total_engagement"] == 22
        assert d["total_impressions"] == 200
        assert d["total_reach"] == 400
        assert d["total_link_clicks"] == 15
        assert d["total_shares"] == 1
        assert d["total_saves"] == 4
        assert d["total_video_views"] == 200
        assert d["total_views"] == 200
        assert d["avg_watch_time_ms"] == 500
        assert d["total_watch_time_ms"] == 5000

    @pytest.mark.asyncio
    async def test_trends_compares_this_week_to_last_week(self, client):
        client._test_db.execute.side_effect = [
            FakeResult([SimpleNamespace(total_engagement=120, total_impressions=2000, net_followers=30)]),
            FakeResult([SimpleNamespace(total_engagement=60, total_impressions=1000, net_followers=10)]),
        ]

        r = await client.get("/api/social/analytics/trends", headers=auth_hdr())

        assert r.status_code == 200
        assert r.json() == {
            "followers": "+200.0%",
            "engagement": "+100.0%",
            "impressions": "+100.0%",
        }

    @pytest.mark.asyncio
    async def test_timeseries_fills_missing_daily_buckets(self, client):
        target_bucket = date.today() - timedelta(days=11)
        client._test_db.execute.return_value = FakeResult([
            {
                "bucket_date": target_bucket,
                "engagement": 12,
                "impressions": 100,
                "reach": 80,
                "shares": 2,
                "saves": 1,
                "link_clicks": 5,
                "video_views": 40,
                "likes": 9,
                "comments": 3,
            }
        ])

        r = await client.get("/api/social/analytics/timeseries?granularity=daily", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert len(d) == 14
        assert d[0]["engagement"] == 0
        matching_bucket = next(item for item in d if item["bucket"] == target_bucket.isoformat())
        assert matching_bucket["engagement"] == 12
        assert matching_bucket["impressions"] == 100

    @pytest.mark.asyncio
    async def test_engagement_velocity_route_is_not_shadowed_by_platform_route(self, client):
        client._test_db.execute.return_value = FakeResult([
            (datetime(2024, 1, 1, tzinfo=timezone.utc), 100, 10, 1, 0, 0, 80, 11),
            (datetime(2024, 1, 2, tzinfo=timezone.utc), 160, 18, 2, 1, 0, 120, 21),
        ])

        r = await client.get("/api/social/analytics/engagement-velocity", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d["total_snapshots"] == 2
        assert d["points"][0]["delta_views"] == 100
        assert d["points"][1]["delta_views"] == 60


class TestCompetitorIntel:
    def test_recommendation_engine_normalizes_comments_from_cached_post_shape(self):
        from app.services import recommendation_engine as engine

        recs = engine._generate_recommendations(
            similar_content=[{
                "hook": "Stop posting random reels if you want inbound leads",
                "comments": 27,
                "likes": 1200,
                "engagement_score": 540,
                "competitor_handle": "compalpha",
                "post_url": "https://example.com/posts/11",
                "media_type": "reel",
                "similarity_score": 0.81,
            }],
            patterns={
                "top_hooks": ["Stop posting random reels if you want inbound leads"],
                "hook_patterns": [{"pattern": "controversy", "count": 3, "example": "Stop posting random reels"}],
                "best_media_type": "reel",
            },
            business_context="B2B marketing studio",
            topic="lead generation",
            count=1,
        )

        assert recs[0]["source_inspiration"]["comments"] == 27
        assert "27 comments" in recs[0]["reasoning"]

    @pytest.mark.asyncio
    async def test_top_content_includes_id_and_forwards_days_and_platform(self, client):
        now = datetime.now(timezone.utc)
        cached_posts = [{
            "id": 321,
            "post_text": "How we turned one reel into qualified leads.",
            "hook": "How we turned one reel into qualified leads in 7 days",
            "likes": 120,
            "comments": 18,
            "shares": 9,
            "platform": "instagram",
            "handle": "compalpha",
            "post_url": "https://example.com/posts/321",
            "posted_at": now,
            "followers": 2000,
        }]

        with patch("app.api.content_intel.load_cached_posts", new=AsyncMock(return_value=cached_posts)) as load_cached_posts:
            r = await client.get(
                "/api/content-intel/competitors/top-content?days=7&platform=instagram",
                headers=auth_hdr(),
            )

        assert r.status_code == 200
        d = r.json()
        assert d["total_posts"] == 1
        assert d["posts"][0]["id"] == 321
        assert d["posts"][0]["competitor_handle"] == "compalpha"
        assert load_cached_posts.await_args.kwargs["days"] == 7
        assert load_cached_posts.await_args.kwargs["platform"] == "instagram"

    @pytest.mark.asyncio
    async def test_hooks_forwards_days_and_returns_deduplicated_ranked_hooks(self, client):
        now = datetime.now(timezone.utc)
        cached_posts = [
            {
                "id": 1,
                "post_text": "",
                "hook": "Stop posting random reels if you want inbound leads",
                "likes": 100,
                "comments": 20,
                "shares": 8,
                "platform": "instagram",
                "handle": "compalpha",
                "post_url": "https://example.com/posts/1",
                "posted_at": now,
                "followers": 2500,
            },
            {
                "id": 2,
                "post_text": "",
                "hook": "Stop posting random reels if you want inbound leads",
                "likes": 50,
                "comments": 5,
                "shares": 1,
                "platform": "instagram",
                "handle": "compbeta",
                "post_url": "https://example.com/posts/2",
                "posted_at": now - timedelta(hours=2),
                "followers": 4000,
            },
            {
                "id": 3,
                "post_text": "",
                "hook": "The easiest way to fix your conversion bottleneck today",
                "likes": 80,
                "comments": 12,
                "shares": 6,
                "platform": "instagram",
                "handle": "compgamma",
                "post_url": "https://example.com/posts/3",
                "posted_at": now - timedelta(hours=1),
                "followers": 2200,
            },
        ]

        with patch("app.api.content_intel.load_cached_posts", new=AsyncMock(return_value=cached_posts)) as load_cached_posts:
            r = await client.get("/api/content-intel/competitors/hooks?days=1", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d["total_hooks"] == 2
        assert d["hooks"][0]["hook"] == "Stop posting random reels if you want inbound leads"
        assert d["hooks"][1]["hook"] == "The easiest way to fix your conversion bottleneck today"
        assert load_cached_posts.await_args.kwargs["days"] == 1

    @pytest.mark.asyncio
    async def test_global_audience_intel_returns_rich_aggregate_shape(self, client):
        client._test_db.execute.return_value = FakeResult([
            (
                json.dumps({
                    "analyzed": 5,
                    "sentiment_breakdown": {"positive": 4, "negative": 0, "neutral": 1},
                    "questions": [{"question": "What camera do you use?", "likes": 3}],
                    "pain_points": [{"pain": "Audio quality is inconsistent", "likes": 2}],
                    "themes": [{"theme": "Editing", "count": 3}],
                    "product_mentions": [{"product": "CapCut", "count": 2}],
                    "top_commenters": [{"username": "alice", "count": 2}],
                    "engagement_quality": "high",
                }),
                json.dumps({"content_format": "reel"}),
                120.0,
            ),
            (
                json.dumps({
                    "analyzed": 3,
                    "sentiment_breakdown": {"positive": 1, "negative": 1, "neutral": 1},
                    "questions": [{"question": "What camera do you use?", "likes": 1}],
                    "pain_points": [{"pain": "Audio quality is inconsistent", "likes": 1}],
                    "themes": [{"theme": "Strategy", "count": 2}],
                    "product_mentions": [{"product": "Notion", "count": 1}],
                    "top_commenters": [{"username": "bob", "count": 1}],
                    "engagement_quality": "moderate",
                }),
                {"content_format": "carousel"},
                20.0,
            ),
        ])

        r = await client.get("/api/content-intel/competitors/audience-intel", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d["posts_analyzed"] == 2
        assert d["comments_analyzed"] == 8
        assert d["sentiment"] == "very_positive"
        assert d["questions"][0]["question"] == "What camera do you use?"
        assert d["pain_points"][0]["pain"] == "Audio quality is inconsistent"
        assert d["themes"][0]["theme"] == "Editing"
        assert d["product_mentions"][0]["product"] == "CapCut"
        assert d["content_formats"] == {"reel": 1, "carousel": 1}

    @pytest.mark.asyncio
    async def test_competitor_audience_intel_supports_dict_rows_and_very_negative_sentiment(self, client):
        client._test_db.execute.return_value = FakeResult([
            {
                "comments_data": {
                    "analyzed": 9,
                    "sentiment_breakdown": {"positive": 1, "negative": 7, "neutral": 1},
                    "questions": [{"question": "Why does this keep dropping off?", "likes": 4}],
                    "pain_points": [{"pain": "Results are inconsistent", "likes": 3}],
                    "themes": [{"theme": "Retention", "count": 4}],
                    "product_mentions": [{"product": "Premiere", "count": 2}],
                    "top_commenters": [{"username": "critic1", "count": 3}],
                    "engagement_quality": "low",
                },
                "content_analysis": {"content_format": "video"},
                "engagement_score": 44.0,
            }
        ])

        r = await client.get("/api/content-intel/competitors/42/audience-intel", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d["posts_analyzed"] == 1
        assert d["comments_analyzed"] == 9
        assert d["sentiment"] == "very_negative"
        assert d["themes"][0] == {"theme": "Retention", "count": 4}
        assert d["content_formats"] == {"video": 1}
        assert client._test_db.execute.await_args.args[1] == {"cid": 42}

    @pytest.mark.asyncio
    async def test_instagram_account_advice_returns_connect_prompt_when_no_account(self, client):
        from app.api.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=77)
        client._test_db.execute.return_value = FakeResult([])

        try:
            r = await client.get("/api/content-intel/instagram/account-advice", headers=auth_hdr())
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert r.status_code == 200
        d = r.json()
        assert d["connected"] is False
        assert d["status"] == "not_connected"
        assert "Connect your Instagram account" in d["recommendations"][0]["title"]
        assert client._test_db.execute.await_args.args[1] == {"user_id": 77}

    @pytest.mark.asyncio
    async def test_instagram_account_advice_returns_needs_sync_when_analytics_missing(self, client):
        from app.api.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=77)
        client._test_db.execute.side_effect = [
            FakeResult([{
                "id": 9,
                "username": "warroomhq",
                "follower_count": 4200,
                "following_count": 210,
                "post_count": 98,
                "last_synced": datetime.now(timezone.utc),
                "status": "connected",
            }]),
            FakeResult([]),
        ]

        try:
            r = await client.get("/api/content-intel/instagram/account-advice", headers=auth_hdr())
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert r.status_code == 200
        d = r.json()
        assert d["connected"] is True
        assert d["status"] == "needs_sync"
        assert d["username"] == "warroomhq"
        assert d["recommendations"][0]["title"] == "Sync your Instagram analytics"

    @pytest.mark.asyncio
    async def test_instagram_account_advice_only_reviews_authenticated_users_account(self, client):
        from app.api.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=77)
        now = datetime.now(timezone.utc)
        client._test_db.execute.side_effect = [
            FakeResult([{
                "id": 9,
                "username": "warroomhq",
                "follower_count": 4200,
                "following_count": 210,
                "post_count": 98,
                "last_synced": now,
                "status": "connected",
            }]),
            FakeResult([
                {
                    "metric_date": date.today(),
                    "impressions": 4000,
                    "reach": 2500,
                    "engagement_rate": 1.8,
                    "followers_gained": 8,
                    "followers_lost": 3,
                    "profile_views": 120,
                    "link_clicks": 5,
                    "shares": 9,
                    "saves": 10,
                    "comments": 18,
                    "likes": 190,
                    "video_views": 3100,
                },
                {
                    "metric_date": date.today() - timedelta(days=1),
                    "impressions": 3600,
                    "reach": 2200,
                    "engagement_rate": 2.1,
                    "followers_gained": 6,
                    "followers_lost": 2,
                    "profile_views": 100,
                    "link_clicks": 4,
                    "shares": 7,
                    "saves": 8,
                    "comments": 14,
                    "likes": 160,
                    "video_views": 2800,
                },
            ]),
        ]

        try:
            r = await client.get("/api/content-intel/instagram/account-advice", headers=auth_hdr())
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert r.status_code == 200
        d = r.json()
        assert d["connected"] is True
        assert d["status"] == "ready"
        assert d["username"] == "warroomhq"
        assert d["days_analyzed"] == 2
        assert d["avg_video_views"] == 2950
        assert d["net_followers"] == 9
        assert "Reviewing only @warroomhq" in d["summary"]
        assert client._test_db.execute.await_args_list[0].args[1] == {"user_id": 77}
        assert client._test_db.execute.await_args_list[1].args[1] == {"account_id": 9}

    @pytest.mark.asyncio
    async def test_top_competitor_videos_returns_one_ranked_video_per_competitor(self, client):
        now = datetime.now(timezone.utc)
        rich_analysis = {
            "content_format": "short_form",
            "hook": {
                "text": "Stop making reels that never convert",
                "start": 0.0,
                "end": 2.8,
                "type": "command",
                "strength": 0.91,
            },
            "value": {
                "text": "Show the bottleneck, prove the fix, and explain why it matters.",
                "start": 2.8,
                "end": 24.0,
                "key_points": [
                    "Show the bottleneck with one concrete example",
                    "Walk through the fix in plain language",
                    "Tie the fix back to revenue or leads",
                ],
            },
            "cta": {
                "text": "Comment AUDIT and I'll send the checklist.",
                "start": 24.0,
                "end": 29.5,
                "type": "engagement",
                "phrase": "Comment AUDIT",
            },
            "total_duration": 29.5,
            "structure_score": 0.93,
            "full_script": "Stop making reels that never convert...",
        }
        competitors = [
            SimpleNamespace(id=1, handle="compalpha", platform="instagram", followers=5000, avg_engagement_rate=3.2),
            SimpleNamespace(id=2, handle="compbeta", platform="instagram", followers=4200, avg_engagement_rate=4.5),
            SimpleNamespace(id=3, handle="compgamma", platform="instagram", followers=3100, avg_engagement_rate=2.7),
        ]
        client._test_db.execute.return_value = FakeResult(competitors)

        ensure_cached = AsyncMock(side_effect=[
            ([{
                "id": 101,
                "competitor_id": 1,
                "handle": "compalpha",
                "platform": "instagram",
                "media_type": "reel",
                "post_text": "Alpha reel",
                "likes": 350,
                "comments": 41,
                "shares": 18,
                "video_views": 8000,
                "followers": 5000,
                "posted_at": now,
                "post_url": "https://example.com/alpha",
                "content_analysis": rich_analysis,
                "transcript": [{"start": 0.0, "end": 2.8, "text": "Stop making reels that never convert"}],
            }], False),
            ([{
                "id": 202,
                "competitor_id": 2,
                "handle": "compbeta",
                "platform": "instagram",
                "media_type": "video",
                "post_text": "Beta breakdown",
                "likes": 290,
                "comments": 55,
                "shares": 23,
                "video_views": 12000,
                "followers": 4200,
                "posted_at": now - timedelta(hours=4),
                "post_url": "https://example.com/beta",
            }], False),
            ([{
                "id": 303,
                "competitor_id": 3,
                "handle": "compgamma",
                "platform": "instagram",
                "media_type": "carousel",
                "post_text": "Gamma carousel",
                "likes": 410,
                "comments": 30,
                "shares": 14,
                "video_views": 0,
                "followers": 3100,
                "posted_at": now - timedelta(hours=8),
                "post_url": "https://example.com/gamma",
            }], False),
        ])

        with patch("app.api.content_intel._ensure_competitor_cached_posts", new=ensure_cached):
            r = await client.get("/api/content-intel/competitors/top-videos?days=7&limit=5", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert {item["competitor_handle"] for item in d} == {"compalpha", "compbeta"}
        assert d[0]["virality_score"] >= d[1]["virality_score"]
        assert d[0]["analysis"]["hook_type"] == "command"
        assert d[0]["analysis"]["cta_phrase"] == "Comment AUDIT"
        assert d[0]["analysis"]["pacing_label"] in {"fast", "balanced"}
        assert "3-beat value stack" in d[0]["analysis"]["scene_pattern"]
        assert d[0]["analysis"]["storyboard"][-1]["scene"] == "CTA"
        assert d[0]["analysis"]["production_spec"]["cta_strategy"].startswith("Close with a engagement CTA")
        assert ensure_cached.await_args_list[0].kwargs["days"] == 7
        assert ensure_cached.await_args_list[1].kwargs["days"] == 7

    @pytest.mark.asyncio
    async def test_competitor_top_videos_includes_storyboard_fallback_when_analysis_is_sparse(self, client):
        competitor = SimpleNamespace(id=42, handle="compdelta", platform="instagram")
        cached_posts = [{
            "id": 909,
            "competitor_id": 42,
            "handle": "compdelta",
            "platform": "instagram",
            "media_type": "reel",
            "post_text": "3 mistakes killing your demo rate. First, your CTA is vague. Second, there is no proof. Third, the offer feels generic.",
            "hook": "3 mistakes killing your demo rate",
            "likes": 220,
            "comments": 17,
            "shares": 9,
            "video_views": 4200,
            "followers": 3300,
            "posted_at": datetime.now(timezone.utc),
            "post_url": "https://example.com/delta",
        }]

        with patch("app.api.content_intel._get_competitor_or_404", new=AsyncMock(return_value=competitor)), \
             patch("app.api.content_intel._ensure_competitor_cached_posts", new=AsyncMock(return_value=(cached_posts, False))):
            r = await client.get("/api/content-intel/competitors/42/top-videos?limit=1", headers=auth_hdr())

        assert r.status_code == 200
        d = r.json()
        assert d[0]["analysis"]["content_format"] == "short_form"
        assert d[0]["analysis"]["pacing_label"] != "unknown"
        assert len(d[0]["analysis"]["key_points"]) >= 1
        assert d[0]["analysis"]["storyboard"][0]["scene"] == "Hook"
        assert d[0]["analysis"]["production_spec"]["production_notes"]

    @pytest.mark.asyncio
    async def test_recommend_content_uses_v2_engine_when_index_is_ready(self, client):
        response_payload = {"recommendations": [{"suggested_hook": "Hook"}], "engine": "v2"}

        with patch("app.services.content_embedder.get_index_status", new=AsyncMock(return_value={"points_count": 12})), \
             patch("app.services.recommendation_engine.recommend_content_v2", new=AsyncMock(return_value=response_payload)) as recommend_v2:
            r = await client.post(
                "/api/content-intel/recommend",
                json={"topic": "lead generation", "platform": "instagram", "count": 3},
                headers=auth_hdr(),
            )

        assert r.status_code == 200
        assert r.json() == response_payload
        assert recommend_v2.await_args.kwargs["platform"] == "instagram"
        assert recommend_v2.await_args.kwargs["topic"] == "lead generation"
        assert recommend_v2.await_args.kwargs["count"] == 3

    @pytest.mark.asyncio
    async def test_recommend_content_fallback_builds_scripts_from_cached_competitor_posts(self, client):
        from app.api.content_intel import GeneratedScript

        client._test_db.execute.return_value = FakeResult([
            SimpleNamespace(id=1, handle="compalpha", platform="instagram"),
            SimpleNamespace(id=2, handle="compbeta", platform="instagram"),
        ])

        cached_posts = [
            {
                "id": 11,
                "handle": "compalpha",
                "platform": "instagram",
                "post_text": "How we doubled qualified demos in 14 days",
                "hook": "How we doubled qualified demos in 14 days",
                "likes": 250,
                "comments": 36,
                "shares": 12,
                "video_views": 7000,
                "followers": 4000,
            },
            {
                "id": 12,
                "handle": "compbeta",
                "platform": "instagram",
                "post_text": "3 fixes for your demo funnel",
                "hook": "3 fixes for your demo funnel",
                "likes": 210,
                "comments": 28,
                "shares": 10,
                "video_views": 6200,
                "followers": 3700,
            },
        ]
        fallback_script = GeneratedScript(
            id=91,
            platform="instagram",
            title="Demo funnel teardown",
            hook="Start with the leak that is costing you demos",
            body_outline="Break down the bottleneck, then show the fix.",
            cta="Comment DEMO for the checklist",
            predicted_views=4200,
            predicted_engagement=260,
            predicted_engagement_rate=6.2,
            virality_score=78.0,
            business_alignment_score=89.0,
            business_alignment_label="High",
            business_alignment_reason="Matches our funnel offer",
            source_competitors=["compalpha, compbeta"],
            similar_videos=[],
            scene_map=[],
        )

        with patch("app.services.content_embedder.get_index_status", new=AsyncMock(return_value={"points_count": 0})), \
             patch("app.api.content_intel.load_cached_posts", new=AsyncMock(return_value=cached_posts)) as load_cached_posts, \
             patch("app.api.content_intel.analyze_trending_topics", new=AsyncMock(return_value=[SimpleNamespace(topic="lead generation"), SimpleNamespace(topic="conversion")])) as analyze_topics, \
             patch("app.api.content_intel._get_business_settings", new=AsyncMock(return_value={"offer": "Growth advisory"})) as get_business_settings, \
             patch("app.api.content_intel.build_competitor_script_ideas", return_value=[fallback_script]) as build_scripts:
            r = await client.post(
                "/api/content-intel/recommend",
                json={"topic": "lead generation", "platform": "instagram", "count": 2},
                headers=auth_hdr(),
            )

        assert r.status_code == 200
        d = r.json()
        assert d["engine"] == "v1_fallback"
        assert d["posts_analyzed"] == 2
        assert d["top_topics"] == ["lead generation", "conversion"]
        assert d["recommendations"][0]["title"] == "Demo funnel teardown"
        assert d["recommendations"][0]["source_competitors"] == ["compalpha", "compbeta"]
        assert load_cached_posts.await_args.kwargs["platform"] == "instagram"
        assert load_cached_posts.await_args.kwargs["days"] == 45
        assert analyze_topics.await_args.args[0]
        assert analyze_topics.await_args.kwargs["enable_clustering"] is False
        assert get_business_settings.await_count == 1
        assert build_scripts.call_args.kwargs["requested_topic"] == "lead generation"
        assert build_scripts.call_args.kwargs["trending_topics"] == ["lead generation", "conversion"]


class TestScheduler:
    @pytest.mark.asyncio
    async def test_start_scheduler_registers_social_sync_jobs(self):
        from app.services import scheduler

        fake_tasks = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        def fake_create_task(coro):
            coro.close()
            return fake_tasks.pop(0)

        scheduler._running_tasks.clear()

        with patch.object(scheduler, "_daily_loop", new_callable=AsyncMock) as daily_loop, \
             patch("app.services.scheduler.asyncio.create_task", side_effect=fake_create_task):
            await scheduler.start_scheduler()

        job_names = [call.args[0] for call in daily_loop.call_args_list]
        assert "competitor-sync-am" in job_names
        assert "competitor-sync-pm" in job_names
        assert "social-sync-am" in job_names
        assert "social-sync-pm" in job_names
        assert len(scheduler._running_tasks) == 4

        await scheduler.stop_scheduler()
        assert scheduler._running_tasks == []

