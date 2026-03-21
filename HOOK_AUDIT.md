# WAR ROOM Hook Detection Audit

## Problem
Hook/value/CTA detection is wrong. Currently pulling from video descriptions, captions, or metadata — NOT from the actual audio transcript. The hook MUST come from what the person SAYS in the video, not what's written in the post description.

## Current Data Flow

### 1. Data Storage (`save_competitor_posts`)
- **Line 1153**: `"hook": extract_hook_from_text(post.text)`
- **Problem**: `post.text` is the post description/caption, not transcript
- **Location**: `backend/app/api/content_intel.py:1153`

### 2. Hook Retrieval (`_post_hook`)
- **Line 378**: Uses stored `post.get("hook")` first
- **Line 382**: Falls back to `extract_hook_from_text(post.get("post_text", ""))`
- **Problem**: Both use post description, not transcript
- **Location**: `backend/app/api/content_intel.py:378-382`

### 3. Transcript Data
- **Exists**: `transcript` column in `crm.competitor_posts` 
- **Format**: JSON array of segments `[{start: float, end: float, text: str}, ...]`
- **Populated by**: `video_transcriber.py` service
- **Currently unused**: Hook detection ignores this field completely

## Database Schema

```sql
-- competitor_posts table has:
post_text TEXT,  -- Post description/caption (Instagram caption, etc.)
transcript JSONB, -- Video transcript segments [{"start": 0.0, "end": 3.0, "text": "Hey guys..."}, ...]
hook TEXT,       -- Currently extracted from post_text, should come from transcript
```

## Fix Required

### Core Logic Changes:
1. **Hook extraction**: Use transcript first 3-5 seconds, NOT post description
2. **Value extraction**: Use transcript middle content
3. **CTA extraction**: Use transcript final 5-10 seconds  
4. **Fallback**: If transcript empty/null, mark as "no_verbal_hook" with flag
5. **Music metadata**: Add music info from Instagram API if available

### Files to Modify:
1. `backend/app/api/content_intel.py`:
   - Fix `_post_hook()` function to use transcript
   - Add `extract_hook_from_transcript()` function
   - Add `has_verbal_hook` field to content_analysis JSON
   - Handle non-verbal hooks (text overlays)

2. `backend/app/services/content_analyzer.py`:
   - Already uses transcript correctly for Hook/Value/CTA analysis
   - Should be the source of truth for this logic

## Current Status
- ✅ Transcript data exists and is populated
- ❌ Hook detection uses wrong data source
- ❌ Content analysis JSON missing has_verbal_hook field
- ❌ Music metadata not extracted