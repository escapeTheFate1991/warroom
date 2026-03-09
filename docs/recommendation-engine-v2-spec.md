# Recommendation Engine v2 — Embedding-Based Content Intelligence

## Problem
Current engine is template-based string matching. It doesn't learn, doesn't understand WHY content works, and generates generic scripts.

## Goal
A content-based recommendation engine that learns from competitors' top-performing content (captions + transcripts + audience intel) and recommends hooks, hashtags, and scripts tailored to Stuff N Things.

## Architecture

### Data Pipeline
```
Competitor Posts (captions, hooks, hashtags)
    + Video Transcripts (what's SAID, how it's delivered)
    + Audience Intel (sentiment, questions, pain points)
    ↓
Embedding Pipeline (nomic-embed-text on Brain 2)
    ↓
Qdrant Vector Store (content_recommendations collection)
    ↓
Recommendation Engine
    ↓
Hooks, Hashtags, Scripts → aligned to OUR business
```

### Embedding Strategy
Each competitor post becomes a document with combined features:
```json
{
  "id": "post_{competitor_id}_{shortcode}",
  "text": "{caption}\n\nTranscript: {transcript_text}\n\nAudience: {audience_themes}",
  "metadata": {
    "competitor_handle": "richkuo7",
    "platform": "instagram",
    "media_type": "reel",
    "engagement_score": 1250.0,
    "virality_score": 85.2,
    "likes": 500,
    "comments": 120,
    "views": 15000,
    "hook": "Here's why vibe coding fails...",
    "hashtags": ["vibecoders", "coding", "ai"],
    "sentiment": "positive",
    "audience_questions": ["how do I start?", "what tools?"],
    "pain_points": ["I struggle with deployment"],
    "posted_at": "2026-03-01"
  }
}
```

### Recommendation Flow
1. **Index**: On sync/transcribe, embed top posts into Qdrant
2. **Query**: When generating content ideas, query by:
   - Business context (what WE do: web dev, AI automation, etc.)
   - Requested topic (if specified)
   - Platform (Instagram, TikTok, etc.)
3. **Filter**: Only top-tier content (engagement_score > threshold)
4. **Rank**: Semantic similarity × engagement_score × recency
5. **Generate**: Use similar top content as few-shot examples for script generation

### What Makes This Better Than v1
| Feature | v1 (Current) | v2 (Embedding-Based) |
|---------|-------------|---------------------|
| Pattern matching | Keyword regex | Semantic embeddings |
| Content source | Captions only | Captions + transcripts + audience intel |
| Business alignment | Keyword overlap score | Semantic similarity to business context |
| Learning | None (static rules) | Improves as more content is indexed |
| Hook recommendations | Copy top hook | Semantic neighbors of proven hooks |
| Topic discovery | Hashtag frequency | Cluster analysis on embeddings |

### Infrastructure (Already Available)
- **Qdrant**: `http://10.0.0.11:6333` — vector store
- **FastEmbed/nomic-embed-text**: `http://10.0.0.11:11435` — embedding model
- **PostgreSQL**: competitor_posts with transcript + comments_data
- **Business settings**: stored in DB, defines what WE do

### New Files
1. `backend/app/services/content_embedder.py` — embed competitor posts into Qdrant
2. `backend/app/services/recommendation_engine.py` — query Qdrant, rank, generate recommendations
3. Update `content_intel.py` `/recommend` endpoint to use v2 engine

### Endpoints
- `POST /api/content-intel/index-content` — trigger indexing of top posts into Qdrant
- `POST /api/content-intel/recommend` (updated) — v2 embedding-based recommendations
- `GET /api/content-intel/recommendation-status` — how many posts indexed, last index time

### Only Top Content
We only embed and learn from posts above an engagement threshold:
- Top 20% by engagement_score per competitor
- Must have caption (not empty)
- Prefer posts with transcripts (richer signal)
- Weight recent content higher (last 60 days)

### Hashtag Recommendations
Analyze hashtag co-occurrence in top content:
- Which hashtags appear together on high-engagement posts?
- Which hashtags are trending (increasing frequency)?
- Map to our business: "These hashtags work for competitors in our space"

### Script Generation (Enhanced)
Instead of templated bodies, use top similar content as context:
```
"Here are 3 top-performing competitor posts on this topic:
1. [hook] [key points from transcript] [engagement: X]
2. [hook] [key points from transcript] [engagement: X]  
3. [hook] [key points from transcript] [engagement: X]

Audience is asking: [top questions from comments]
Pain points: [from comment analysis]

Generate a script for [OUR business: Stuff N Things] that:
- Uses a proven hook pattern from above
- Addresses the audience's questions
- Positions our solution naturally
- Matches the delivery style that works"
```

This can go to Claude/GPT for actual script writing, or stay rule-based for speed.
