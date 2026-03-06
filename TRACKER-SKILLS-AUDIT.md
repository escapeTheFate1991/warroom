# Content Tracker — Skills Audit

> Generated: 2026-03-05 | Auditor: Friday (subagent)  
> Scope: `ContentTracker.tsx` features mapped to OpenClaw skills + backend APIs

---

## 1. Current Feature Inventory

### Frontend (`ContentTracker.tsx`)
| Feature | What It Shows | Data Source |
|---------|--------------|-------------|
| **Pipeline Stats** | Total pieces, Published, In Production, Ideas | localStorage (`warroom_content_{platform}`, `warroom_content_pipeline`) |
| **Top Performing Content** | Bar chart of views, top 6 posts | Published content sorted by views |
| **Metrics Summary** | Videos count, Total Views, Avg Views, Total Likes | Aggregated from published posts |
| **Published Videos List** | Title, views, likes, comments, engagement %, platform badge, external link | All `stage: "posted"` content |
| **Platform Tracking** | Instagram + YouTube tags per post | `platform` field on each content card |
| **Content Stages** | `idea → scripted → filming → editing → scheduled → posted` | `stage` field on each content card |

### Backend (`content_intel.py`)
| Endpoint | Purpose | Status |
|----------|---------|--------|
| `GET /competitors/{id}/content` | Fetch/cache competitor posts (IG, X, YouTube) | ✅ Working (API-dependent) |
| `GET /competitors/trending-topics` | NLP topic extraction with TF-IDF + K-Means clustering | ✅ Working (requires NLTK + sklearn) |
| `GET /competitors/top-content` | Top posts by engagement across all competitors | ✅ Working |
| `GET /competitors/hooks` | Extract first-sentence hooks ranked by engagement | ✅ Working |
| `POST /competitors/refresh` | Re-fetch and cache competitor content | ✅ Working |
| `POST /competitors/{id}/generate-script` | Template-based script generation from hooks | ✅ Working (template, not AI) |
| `GET /competitors/scripts` | List saved generated scripts | ✅ Working |

### In-House Services
| Service | Purpose | Status |
|---------|---------|--------|
| `instagram_scraper.py` | Playwright-based public IG profile scraper (GraphQL intercept) | ✅ Working |

---

## 2. Feature → Skill Mapping

### Features That Have Matching Skills

| Tracker Feature | Existing Skill | Skill Location | How It Connects |
|----------------|---------------|----------------|-----------------|
| **Competitor content fetching** | `competitive-landscape` | workspace | Strategy/frameworks — doesn't provide scraping, but informs *what* to analyze |
| **Hook extraction & analysis** | `content-creator` | workspace | Brand voice + content frameworks; hooks are a subset of this |
| **Script generation** | `social-content` | workspace | Social media content strategy; could enhance the template-based generator with AI |
| **YouTube content fetching** | `youtube-summarizer` | workspace | Extracts YouTube transcripts via `youtube-transcript-api` — **directly usable** for script analysis |
| **Audio/video transcription** | `audio-transcriber` | workspace | Faster-Whisper transcription — **key for Instagram Reel hook analysis** |
| **Whisper API** | `openai-whisper` / `openai-whisper-api` | bundled | Alternative transcription via OpenAI API (costs money) |
| **Video frame extraction** | `video-frames` | bundled | ffmpeg-based frame extraction — useful for thumbnail analysis |
| **X/Twitter scraping** | `x-twitter-scraper` | workspace | Full X data platform (Xquik) — tweets, users, followers, engagement |
| **Content analytics patterns** | `analytics-tracking` | workspace | Analytics system design — informs metrics/tracking architecture |
| **Embedding/similarity** | `embedding-strategies` | workspace | Vector embeddings for content similarity/recommendations |
| **Trend analysis** | `apify-trend-analysis` | workspace | ⚠️ Uses Apify (paid) — **not usable**, but reference for approach |

### Features That Are Partially Covered

| Feature | Gap | What's Missing |
|---------|-----|---------------|
| **Instagram Reel video download** | Scraper gets metadata but not video files | Need video URL extraction + download pipeline in `instagram_scraper.py` |
| **Instagram Reel transcript extraction** | No audio-from-video pipeline | Need: download video → extract audio (ffmpeg) → transcribe (Whisper) → extract hook |
| **Content recommendations** | Backend has trending topics but no "what to post next" engine | Need similarity-based recommendation using embeddings |
| **Engagement prediction** | Frontend shows past metrics only | No ML model to predict which hooks/topics will perform |

### Features That Need New Skills

| Feature | Skill Needed | Priority |
|---------|-------------|----------|
| **Video-to-Transcript Pipeline** | `video-transcript-pipeline` | 🔴 P0 — Core to hook analysis |
| **Content Recommendation Engine** | `content-recommender` | 🟡 P1 — High value but works without it |
| **Follower Demographic Inference** | `audience-demographics` | 🟡 P1 — Valuable for targeting |
| **Engagement Predictor** | `engagement-predictor` | 🟢 P2 — Nice to have |

---

## 3. Gap Analysis & Recommended Approaches

### 🔴 P0: Video-to-Transcript Pipeline

**What:** Download Instagram Reels/YouTube Shorts → extract audio → transcribe → extract hooks/scripts

**Approach (all in-house, no paid services):**

1. **Video Download**
   - Instagram: Extend `instagram_scraper.py` — the GraphQL intercept already captures `video_url` from media nodes. Download with `httpx` or `aiohttp` to temp storage.
   - YouTube: Use `yt-dlp` (open source, no API key) — `yt-dlp -x --audio-format wav <url>`
   
2. **Audio Extraction**
   - `ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav`
   - Already have ffmpeg on the system (used by `video-frames` skill)

3. **Transcription**
   - **Primary:** `faster-whisper` (local, free, GPU-accelerated) — the `audio-transcriber` skill already uses this
   - **Fallback:** `openai-whisper-api` (bundled skill) if local GPU can't handle load
   - The GTX 970 (4GB VRAM) can run `faster-whisper` small/base models fine

4. **Hook Extraction**
   - First 3-5 seconds of transcript = the hook
   - Use timestamp data from Whisper to isolate opening lines
   - Feed to existing `extract_hook_from_text()` in `content_intel.py`

**Backend integration:**
```
POST /content-intel/competitors/{id}/transcribe-reels
→ Downloads recent reels → Extracts audio → Transcribes → Saves hooks to competitor_posts table
```

**Skill structure:**
```
skills/video-transcript-pipeline/
├── SKILL.md
├── scripts/
│   ├── download_video.py      # Platform-agnostic video downloader
│   ├── extract_audio.py       # ffmpeg wrapper
│   ├── transcribe.py          # faster-whisper wrapper
│   └── extract_hooks.py       # First-N-seconds hook extraction
└── references/
    └── pipeline-architecture.md
```

---

### 🟡 P1: Content Recommendation Engine

**What:** Given competitor content + trending topics + past performance, suggest what to post next

**Approach (all local, no paid services):**

1. **Embedding-based similarity**
   - Use `sentence-transformers` (local, free) — `all-MiniLM-L6-v2` (80MB, runs on CPU)
   - Embed all competitor hooks + post texts
   - Store in a local vector DB (Qdrant is already in the stack via OpenClaw memory)

2. **Recommendation logic**
   - Find top-performing competitor posts (high engagement)
   - Find posts in YOUR content gap (topics competitors cover that you don't)
   - Score by: `engagement_potential × topic_freshness × content_gap_score`
   - Filter out topics you've already covered recently

3. **Output format**
   - "Based on competitor analysis, here are 5 content ideas ranked by potential"
   - Each idea includes: topic, suggested hook style, reference posts, estimated engagement

**Backend integration:**
```
GET /content-intel/recommendations?platform=instagram&limit=5
→ Returns ranked content suggestions with source data
```

**Leverages existing:**
- `embedding-strategies` skill (workspace) for model selection
- `content_intel.py` trending topics endpoint for topic data
- `content-creator` skill for content frameworks

---

### 🟡 P1: Follower Demographic Inference

**What:** Understand competitor audience demographics without API access to their follower lists

**Approach (realistic for public data only):**

Since Instagram/YouTube don't expose follower demographics publicly, we use **inference from engagement signals:**

1. **Commenter Analysis**
   - Scrape comments on competitor posts (extend `instagram_scraper.py`)
   - Analyze commenter profiles: bio keywords, handle patterns, profile pics
   - Use NLP to classify: age bracket (gen-z slang vs professional language), interests, likely occupation

2. **Engagement Pattern Analysis**
   - When do posts get most engagement? → Timezone/region inference
   - What topics get most comments? → Interest mapping
   - Language distribution in comments → Geographic inference

3. **Bio/Handle Pattern Mining**
   - Scrape bios of top commenters (public data)
   - Extract: job titles, locations, interests, emoji patterns
   - Aggregate into demographic clusters

4. **Proxy metrics**
   - Follower/following ratio of commenters → Bot detection
   - Account age patterns → Audience maturity
   - Cross-reference with known demographic data for similar niches

**Backend integration:**
```
GET /content-intel/competitors/{id}/audience-profile
→ Returns inferred demographics: location distribution, interest clusters, engagement windows
```

**Note:** This is inherently approximate. No tool can give you exact demographics from public data. Frame it as "Audience Signals" not "Demographics."

---

### 🟢 P2: Engagement Predictor

**What:** Predict how well a piece of content will perform before posting

**Approach:**

1. **Feature extraction from historical data**
   - Hook type (question, bold claim, confession, comparison)
   - Post length, hashtag count, posting time
   - Topic category, platform
   - Historical engagement for similar content

2. **Simple ML model**
   - Train on competitor post data in `competitor_posts` table
   - Random Forest or XGBoost (sklearn, runs locally)
   - Target: engagement_score bucket (low/medium/high/viral)

3. **Integration**
   - Score content ideas before posting
   - Show prediction confidence in the Content Tracker UI

**Backend integration:**
```
POST /content-intel/predict-engagement
Body: { hook, platform, topic, posting_time }
→ Returns { predicted_engagement: "high", confidence: 0.72, similar_posts: [...] }
```

---

## 4. Existing Skills — Usability Summary

### Directly Usable (No Modification Needed)
| Skill | How to Use |
|-------|-----------|
| `audio-transcriber` | Feed extracted audio → get transcript with timestamps |
| `youtube-summarizer` | Feed YouTube URLs → get full transcript + summary |
| `video-frames` | Extract thumbnail frames from competitor videos |
| `x-twitter-scraper` | Scrape X/Twitter competitor data (if Xquik API available) |

### Usable with Integration Work
| Skill | What's Needed |
|-------|--------------|
| `content-creator` | Wire brand voice analysis into script generator (replace templates with AI) |
| `social-content` | Use its frameworks to structure generated scripts |
| `embedding-strategies` | Apply its guidance when building the recommendation engine |
| `competitive-landscape` | Use Porter's Five Forces etc. to structure competitive analysis views |

### NOT Usable (Paid/Third-Party Dependencies)
| Skill | Why Not |
|-------|---------|
| `apify-*` (all 10+) | Requires paid Apify subscription — against project constraints |
| `instagram-automation` | Requires Composio/Rube MCP — paid service |
| `openai-whisper-api` | Costs money per transcription — use local Whisper instead |

---

## 5. Priority Build Order

| # | What to Build | Effort | Impact | Dependencies |
|---|--------------|--------|--------|-------------|
| **1** | Extend `instagram_scraper.py` to download video URLs | 2-3 hrs | High | None — scraper already intercepts GraphQL with `video_url` |
| **2** | Build video-to-transcript pipeline | 4-6 hrs | Very High | #1 + ffmpeg + faster-whisper (already available) |
| **3** | Wire transcripts into `content_intel.py` hooks endpoint | 2-3 hrs | High | #2 |
| **4** | Build content recommendation endpoint | 6-8 hrs | High | sentence-transformers + existing trending topics |
| **5** | Upgrade script generator from templates to AI-powered | 3-4 hrs | Medium | LLM API (already have via OpenClaw) |
| **6** | Add commenter analysis for audience inference | 8-10 hrs | Medium | Extend scraper + NLP pipeline |
| **7** | Build engagement predictor | 6-8 hrs | Low-Medium | Enough historical data in competitor_posts |

### Quick Wins (< 1 hour each)
- Wire `youtube-summarizer` skill to auto-transcribe YouTube competitor videos
- Add `video-frames` thumbnail extraction to competitor content display
- Connect `content-creator` brand voice analysis to the script generator

---

## 6. Frontend Gaps (ContentTracker.tsx)

The current frontend is **read-only with localStorage**. To leverage the backend properly:

| Current State | Needed |
|--------------|--------|
| Data from localStorage | API calls to `content_intel.py` endpoints |
| Hardcoded fallback data | Real competitor data from backend |
| No transcript display | Hook/script viewer for transcribed reels |
| No recommendations | "Suggested content" panel from recommendation engine |
| No trend visualization | Trending topics chart from `/competitors/trending-topics` |
| No engagement prediction | Score badge on content ideas |

---

## 7. Architecture Note

All new capabilities should follow the existing pattern:
- **Backend:** New endpoints in `content_intel.py` or new router file
- **Services:** New service files in `backend/app/services/` (like `instagram_scraper.py`)
- **Frontend:** New components or extend `ContentTracker.tsx`
- **Skills:** New OpenClaw skills for reusable agent capabilities
- **No paid services.** Everything runs locally or uses free/open-source tools.

### Key Dependencies (All Free/Open Source)
| Tool | Purpose | Install |
|------|---------|---------|
| `faster-whisper` | Local speech-to-text | `pip install faster-whisper` |
| `yt-dlp` | YouTube video/audio download | `pip install yt-dlp` |
| `ffmpeg` | Audio extraction from video | System package (likely already installed) |
| `sentence-transformers` | Text embeddings for recommendations | `pip install sentence-transformers` |
| `scikit-learn` | ML models, TF-IDF (already in use) | Already installed |
