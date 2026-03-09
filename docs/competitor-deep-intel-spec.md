# Competitor Deep Intelligence — Feature Spec

## Overview
Enhance competitor intelligence with video transcription, comment scraping, and post drill-down UI. The scraper now has authenticated Instagram access via Playwright cookies.

## Database State (Already Migrated)
`crm.competitor_posts` now has these columns:
- `media_type` VARCHAR(20) — image/video/reel/carousel
- `media_url` TEXT — direct URL to media
- `thumbnail_url` TEXT — thumbnail for video/reel
- `transcript` JSONB — `[{start: 0.0, end: 2.5, text: "..."}, ...]`
- `comments_data` JSONB — `[{username, text, likes, timestamp}, ...]`
- `shortcode` VARCHAR(50) — Instagram shortcode for post lookup (indexed)

The save function in `backend/app/api/scraper.py` already persists `media_type`, `media_url`, `thumbnail_url`, `shortcode`.

## Track 2: Video Transcription Pipeline

### Flow
1. After scraping posts, identify video/reel posts (`media_type in ('video', 'reel')`)
2. Download video via `yt-dlp` or direct `media_url` fetch to `/tmp/`
3. Transcribe with Whisper at `http://10.0.0.1:18796` (already running)
4. Store transcript JSON in `competitor_posts.transcript`
5. Delete the video file immediately after transcription

### New file: `backend/app/services/video_transcriber.py`
```python
async def transcribe_competitor_videos(db, competitor_id: int, limit: int = 10):
    """Find video/reel posts without transcripts, download, transcribe, delete."""
    # 1. SELECT from competitor_posts WHERE media_type IN ('video','reel') AND transcript IS NULL
    # 2. For each: download media_url to /tmp/{shortcode}.mp4
    # 3. POST to Whisper: http://10.0.0.1:18796/v1/audio/transcriptions
    # 4. Parse response into [{start, end, text}] chunks
    # 5. UPDATE competitor_posts SET transcript = :chunks WHERE id = :id
    # 6. Delete /tmp/{shortcode}.mp4
```

### Download strategy
- Try `yt-dlp -o /tmp/{shortcode}.mp4 https://www.instagram.com/reel/{shortcode}/` first
- Fallback: direct HTTP download of `media_url` (may be CDN-expiring URL)
- yt-dlp should use cookies from `/data/instagram_cookies.json` via `--cookies` flag

### Whisper API
```bash
curl -X POST http://10.0.0.1:18796/v1/audio/transcriptions \
  -F file=@/tmp/video.mp4 \
  -F model=whisper-1 \
  -F response_format=verbose_json \
  -F timestamp_granularities[]=segment
```
Response: `{"segments": [{"start": 0.0, "end": 2.5, "text": "..."}]}`

### New endpoint
- `POST /api/scraper/transcribe/{competitor_id}` — trigger transcription for a competitor's videos

## Track 3: Comment Scraping

### Flow
1. For each cached post (especially high-engagement ones), scrape comments
2. Use authenticated Playwright to navigate to `https://www.instagram.com/p/{shortcode}/`
3. Intercept GraphQL responses containing comment data
4. Store top 50 comments per post in `competitor_posts.comments_data`

### New file: `backend/app/services/comment_scraper.py`
```python
async def scrape_post_comments(shortcode: str, limit: int = 50) -> list[dict]:
    """Scrape comments from a single Instagram post using authenticated Playwright."""
    # 1. Load cookies from /data/instagram_cookies.json
    # 2. Navigate to https://www.instagram.com/p/{shortcode}/
    # 3. Intercept responses containing edge_media_to_parent_comment or comments
    # 4. Parse: [{username, text, likes, timestamp, is_reply}]
    # 5. Return top comments sorted by likes

async def scrape_competitor_comments(db, competitor_id: int, top_n: int = 10):
    """Scrape comments for top N posts by engagement."""
    # 1. SELECT top N posts by engagement_score WHERE comments_data IS NULL
    # 2. For each: scrape_post_comments(shortcode)
    # 3. UPDATE competitor_posts SET comments_data = :data WHERE shortcode = :sc
```

### Comment data structure
```json
[
  {"username": "user1", "text": "Great content!", "likes": 45, "timestamp": "2026-03-01T12:00:00Z", "is_reply": false},
  {"username": "user2", "text": "@user1 agreed!", "likes": 12, "timestamp": "2026-03-01T12:05:00Z", "is_reply": true}
]
```

### New endpoint
- `POST /api/scraper/comments/{competitor_id}` — scrape comments for a competitor's posts

## Track 4: Frontend Post Detail Drill-Down

### Current behavior
- Content cards show caption, engagement, hook, timestamp
- Clicking → opens post URL in new tab (external link)

### New behavior
- Clicking a content card → opens a **detail modal/slide-out panel**
- Panel shows:
  - Post caption (full)
  - Engagement stats (likes, comments, views)
  - **Transcript** with timestamps (clickable timestamps link to video at that point)
  - **Comments** section showing top comments with usernames and likes
  - "View on Instagram" external link
  - Media type badge (🎬 Reel, 📷 Image, 🎠 Carousel)

### New endpoint needed
- `GET /api/content-intel/posts/{post_id}` or `GET /api/content-intel/posts/by-shortcode/{shortcode}`
  - Returns full post data including transcript and comments_data

### Frontend component: `PostDetailModal.tsx`
- Receives post data (or fetches by shortcode)
- Tabs or sections: Overview | Transcript | Comments
- Transcript: formatted with MM:SS timestamps, each segment is a row
- Comments: username, text, likes, time ago — sorted by likes desc

## Track 5: Audience Intelligence (after Track 3)

### Enhancement
Once we have comments scraped, the audience analysis can extract:
- **Pain points** — questions asked in comments
- **Product interest** — mentions of products/tools/services
- **Sentiment** — positive/negative/neutral per post
- **Top commenters** — who engages most (potential leads or collaborators)
- **Common asks** — "how do I...", "where can I...", "do you offer..."

This enriches the Dossier's Audience Intelligence section with real data instead of inferred themes.

## Integration Points
- `POST /api/scraper/instagram/sync` already calls `_save_posts_to_cache` → now persists media_type/url/shortcode
- After sync, can trigger transcription and comment scraping as background tasks
- Dossier endpoint already reads from competitor_posts → will automatically benefit from richer data
