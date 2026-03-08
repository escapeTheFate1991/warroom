# Competitor Intelligence Overhaul Spec

## Context
The competitor intel feature was recently fixed (see competitor-intelligence-fix-guide.md) but still has gaps. This spec covers the remaining work.

## Current State
- Backend: `backend/app/api/content_intel.py` (~1845 lines)
- Frontend: `frontend/src/components/intelligence/CompetitorIntel.tsx` (~1646 lines)
- Scraper: `backend/app/api/scraper.py` (~575 lines)
- Instagram scraping works via Apify actors
- Engagement rate calculation recently fixed to use real data
- Script generation produces multi-script output

## Required Changes

### 1. Auto-Sync on Competitor Add
When a new competitor is added, trigger an immediate scrape. Don't wait for the user to manually refresh.
- In the `POST /api/competitors` endpoint (or wherever competitors are created), call `sync_instagram_competitor()` right after insert

### 2. Cron Job — Twice Daily at Random Times
- Create two cron jobs that sync ALL competitors
- Random time within a window (e.g., 6am-10am and 4pm-8pm EST)
- Each run should call `sync_instagram_competitor_batch()` for all active competitors
- Endpoint: `POST /api/content-intel/sync-all`

### 3. Top Content Freshness
- Top Content and Hooks should weight recency heavily
- Current virality scoring already blends recency, but the frontend may be showing stale cached data
- Ensure the top-content endpoint always re-fetches from cache, not from stale DB summaries
- Add a "last synced" timestamp to each competitor card

### 4. Deeper Video Analysis
- **Timestamps on chunks**: The video chunk cards need start_time/end_time displayed
- **Post time**: Record when the competitor posted (not just when we scraped)
- **Video length**: Show duration if available
- **Description**: Full post description/caption
- **Thumbnails**: Store and display thumbnail URLs
- **First comment**: Detect if competitor posts their own first comment
- **Affiliate links**: Extract links from bio/captions, flag affiliate/UTM links

### 5. Linked Accounts / Competitor Dossier
New feature: detect and auto-add linked accounts.
- **New tab in competitor drill-down**: "Content Overview" | "Dossier"
- **Dossier tab shows**:
  - Business/products they're selling (extracted from bio, links, captions)
  - Linked accounts (other social profiles mentioned in bio or tagged)
  - Auto-add linked accounts as new competitors
  - Affiliate links and products promoted
  - Network map of related accounts pushing same products

### 6. Recommendation Engine
- One-button script generation based on competitor analysis
- Analyze top-performing content: what format, hook style, length, topic
- Cross-reference with business settings to generate ideas that match OUR brand
- Output: 3-6 script ideas ranked by predicted performance
- Each script should include: hook, body outline, CTA, predicted engagement, source competitors

### 7. Audience Intelligence
- Should evolve over time as more competitor data is scraped
- Track: follower growth, engagement trends, content type preferences
- Re-run audience analysis after each sync, not just on initial add
- Store historical snapshots for trend detection

### 8. Frontend Fixes
- Add timestamps to video chunk cards
- Add "last synced" indicator per competitor
- Add sync-in-progress indicator
- Add dossier tab to competitor drill-down

## Files to Modify
- `backend/app/api/content_intel.py` — sync-all endpoint, auto-sync on add, recommendation engine
- `backend/app/api/scraper.py` — deeper data extraction (first comment, affiliate links, linked accounts)
- `frontend/src/components/intelligence/CompetitorIntel.tsx` — dossier tab, timestamps, sync indicators
- New: cron job configuration

## Convention Reminders
- Use `authFetch` not raw `fetch` in frontend
- No hardcoded credentials
- Centralized config
- Commit after each logical change
