"""Content intelligence API endpoints for competitive analysis and script generation."""
import logging
import json
import re
import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.competitor import Competitor
from app.models.crm.content_script import ContentScript
from app.models.crm.social import SocialAccount

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class CompetitorPost(BaseModel):
    """Individual competitor post data."""
    text: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    timestamp: datetime
    url: str
    engagement_score: float = 0.0


class CompetitorContentResponse(BaseModel):
    """Response for competitor content endpoint."""
    competitor_id: int
    platform: str
    handle: str
    posts: List[CompetitorPost]
    total_posts: int
    avg_engagement: float


class TrendingTopic(BaseModel):
    """Trending topic across competitors."""
    topic: str
    frequency: int
    avg_engagement: float
    sources: List[str]
    keywords: List[str]


class TrendingTopicsResponse(BaseModel):
    """Response for trending topics endpoint."""
    topics: List[TrendingTopic]
    total_analyzed_posts: int
    timeframe_days: int = 30


class ScriptGenerationRequest(BaseModel):
    """Request for script generation."""
    competitor_id: Optional[int] = None
    platform: str
    topic: Optional[str] = None
    hook_style: Optional[str] = None  # comparison, bold_claim, confession, etc.


class GeneratedScript(BaseModel):
    """Generated content script."""
    id: Optional[int] = None
    competitor_id: Optional[int] = None
    platform: str
    title: str
    hook: str
    body_outline: str
    cta: str
    topic: Optional[str] = None
    source_post_url: Optional[str] = None
    estimated_duration: Optional[str] = None


async def get_social_account_token(db: AsyncSession, platform: str) -> Optional[str]:
    """Get access token for connected social account."""
    try:
        result = await db.execute(
            select(SocialAccount.access_token)
            .where(SocialAccount.platform == platform)
            .where(SocialAccount.status == "connected")
            .limit(1)
        )
        token_row = result.first()
        return token_row[0] if token_row else None
    except Exception as e:
        logger.error(f"Failed to get token for {platform}: {e}")
        return None


async def fetch_instagram_content(handle: str, access_token: str) -> List[CompetitorPost]:
    """Fetch recent content from Instagram competitor."""
    try:
        posts = []
        async with httpx.AsyncClient() as client:
            # Get recent media
            url = "https://graph.instagram.com/me"
            params = {
                "fields": f"business_discovery.username({handle}){{media{{caption,like_count,comments_count,timestamp,permalink}}}}",
                "access_token": access_token
            }
            
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            business_data = data.get("business_discovery", {})
            media_data = business_data.get("media", {}).get("data", [])
            
            for post in media_data:
                posts.append(CompetitorPost(
                    text=post.get("caption", ""),
                    likes=post.get("like_count", 0),
                    comments=post.get("comments_count", 0),
                    shares=0,  # Instagram doesn't provide shares count
                    timestamp=datetime.fromisoformat(post.get("timestamp", "").replace("Z", "+00:00")),
                    url=post.get("permalink", ""),
                    engagement_score=post.get("like_count", 0) + post.get("comments_count", 0) * 2
                ))
            
            return posts
            
    except Exception as e:
        logger.error(f"Failed to fetch Instagram content for {handle}: {e}")
        return []


async def fetch_x_content(handle: str, access_token: str) -> List[CompetitorPost]:
    """Fetch recent content from X competitor."""
    try:
        posts = []
        async with httpx.AsyncClient() as client:
            # Get user ID first
            user_url = f"https://api.x.com/2/users/by/username/{handle}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            user_response = await client.get(user_url, headers=headers, timeout=30.0)
            user_response.raise_for_status()
            
            user_data = user_response.json()
            user_id = user_data.get("data", {}).get("id")
            
            if not user_id:
                return []
            
            # Get recent tweets
            tweets_url = f"https://api.x.com/2/users/{user_id}/tweets"
            params = {
                "tweet.fields": "created_at,public_metrics,text",
                "max_results": 20
            }
            
            tweets_response = await client.get(tweets_url, headers=headers, params=params, timeout=30.0)
            tweets_response.raise_for_status()
            
            tweets_data = tweets_response.json()
            tweets = tweets_data.get("data", [])
            
            for tweet in tweets:
                metrics = tweet.get("public_metrics", {})
                posts.append(CompetitorPost(
                    text=tweet.get("text", ""),
                    likes=metrics.get("like_count", 0),
                    comments=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                    timestamp=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")),
                    url=f"https://twitter.com/{handle}/status/{tweet.get('id')}",
                    engagement_score=metrics.get("like_count", 0) + metrics.get("reply_count", 0) * 2 + metrics.get("retweet_count", 0) * 3
                ))
            
            return posts
            
    except Exception as e:
        logger.error(f"Failed to fetch X content for {handle}: {e}")
        return []


async def fetch_youtube_content(handle: str, api_key: str) -> List[CompetitorPost]:
    """Fetch recent content from YouTube competitor."""
    try:
        posts = []
        async with httpx.AsyncClient() as client:
            # Search for channel
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "q": handle,
                "type": "channel",
                "part": "snippet",
                "maxResults": 1,
                "key": api_key
            }
            
            response = await client.get(search_url, params=search_params, timeout=30.0)
            response.raise_for_status()
            
            search_data = response.json()
            items = search_data.get("items", [])
            
            if not items:
                return []
            
            channel_id = items[0]["id"]["channelId"]
            
            # Get recent videos
            videos_url = "https://www.googleapis.com/youtube/v3/search"
            videos_params = {
                "channelId": channel_id,
                "part": "snippet",
                "order": "date",
                "maxResults": 20,
                "key": api_key
            }
            
            videos_response = await client.get(videos_url, params=videos_params, timeout=30.0)
            videos_response.raise_for_status()
            
            videos_data = videos_response.json()
            videos = videos_data.get("items", [])
            
            for video in videos:
                snippet = video.get("snippet", {})
                video_id = video.get("id", {}).get("videoId")
                
                if video_id:
                    # Get video statistics
                    stats_url = "https://www.googleapis.com/youtube/v3/videos"
                    stats_params = {
                        "id": video_id,
                        "part": "statistics",
                        "key": api_key
                    }
                    
                    stats_response = await client.get(stats_url, params=stats_params, timeout=30.0)
                    stats_response.raise_for_status()
                    
                    stats_data = stats_response.json()
                    stats_items = stats_data.get("items", [])
                    
                    if stats_items:
                        stats = stats_items[0].get("statistics", {})
                        
                        posts.append(CompetitorPost(
                            text=snippet.get("title", "") + " " + snippet.get("description", "")[:200],
                            likes=int(stats.get("likeCount", 0)),
                            comments=int(stats.get("commentCount", 0)),
                            shares=0,  # YouTube doesn't provide shares
                            timestamp=datetime.fromisoformat(snippet.get("publishedAt", "").replace("Z", "+00:00")),
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            engagement_score=int(stats.get("likeCount", 0)) + int(stats.get("commentCount", 0)) * 2
                        ))
            
            return posts
            
    except Exception as e:
        logger.error(f"Failed to fetch YouTube content for {handle}: {e}")
        return []


async def extract_hooks_from_posts(posts: List[CompetitorPost]) -> List[str]:
    """Extract hook patterns from competitor posts."""
    hooks = []
    
    for post in posts:
        text = post.text.strip()
        if not text:
            continue
        
        # Extract first sentence or up to first line break
        lines = text.split('\n')
        first_line = lines[0].strip()
        
        # Extract hook (first sentence or until punctuation)
        sentences = re.split(r'[.!?]', first_line)
        if sentences:
            hook = sentences[0].strip()
            if len(hook) > 10 and len(hook) < 200:  # Reasonable hook length
                hooks.append(hook)
    
    return hooks


async def analyze_trending_topics(posts: List[CompetitorPost]) -> List[TrendingTopic]:
    """Analyze posts to identify trending topics."""
    # Simple keyword extraction and frequency analysis
    word_freq = {}
    topic_posts = {}
    
    for post in posts:
        words = re.findall(r'\b\w+\b', post.text.lower())
        # Filter out common words and short words
        meaningful_words = [w for w in words if len(w) > 3 and w not in ['that', 'this', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 'which', 'their', 'time', 'more', 'like', 'just', 'only', 'over', 'also', 'back', 'after', 'first', 'well', 'many', 'some', 'could', 'would', 'should']]
        
        for word in meaningful_words:
            word_freq[word] = word_freq.get(word, 0) + 1
            if word not in topic_posts:
                topic_posts[word] = []
            topic_posts[word].append(post)
    
    # Create trending topics from most frequent meaningful words
    trending = []
    for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
        if freq >= 2:  # Appears in at least 2 posts
            related_posts = topic_posts[word]
            avg_engagement = sum(p.engagement_score for p in related_posts) / len(related_posts)
            
            trending.append(TrendingTopic(
                topic=word.title(),
                frequency=freq,
                avg_engagement=avg_engagement,
                sources=[f"Post {i+1}" for i in range(min(3, len(related_posts)))],
                keywords=[word]
            ))
    
    return trending


def generate_script_content(competitor_handle: str, platform: str, topic: str, hooks: List[str]) -> GeneratedScript:
    """Generate a content script based on competitor analysis."""
    # Select best performing hook if available
    best_hook = hooks[0] if hooks else f"Here's what I learned from studying {competitor_handle}"
    
    # Platform-specific script generation
    if platform == "instagram":
        title = f"Instagram Post: {topic} Breakdown"
        body = f"""
**Opening Hook:** {best_hook}

**Main Content Points:**
• Point 1: Share the main insight about {topic}
• Point 2: Provide a specific example or case study  
• Point 3: Give actionable advice

**Engagement Elements:**
• Ask a question to boost comments
• Use relevant hashtags for reach
• Include a carousel or visual element

**Timing:** Best posted during 6-9 PM EST for max engagement
"""
        cta = "Double-tap if you agree and save this for later! What's your experience with this? 👇"
        duration = "60-90 seconds read time"
    
    elif platform == "youtube":
        title = f"YouTube Video: The Truth About {topic}"
        body = f"""
**Hook (0-15s):** {best_hook}

**Introduction (15-30s):**
• Set expectations for what viewers will learn
• Tease the biggest insight coming up

**Main Content (30s-8min):**
• Section 1: The problem/current situation
• Section 2: Your unique perspective/solution
• Section 3: Step-by-step breakdown
• Section 4: Real examples/case studies

**Conclusion (8-10min):**
• Recap the key takeaways
• Strong call to action
"""
        cta = "If this helped you, smash that like button and subscribe for more insights like this. What questions do you have? Drop them below!"
        duration = "8-12 minutes"
    
    elif platform == "x":
        title = f"X Thread: {topic} Deep Dive"
        body = f"""
**Thread Structure:**

1/8 🧵 {best_hook}

2/8 Here's what most people get wrong about {topic}...

3/8 The real issue is [specific problem]

4/8 I've seen this pattern across [number] different cases:

5/8 Here's the exact framework that actually works:

6/8 Step 1: [First step]
    Step 2: [Second step]  
    Step 3: [Third step]

7/8 This approach led to [specific result] in just [timeframe]

8/8 If you found this valuable:
    • Like this tweet
    • Retweet the thread
    • Follow me for more insights like this
"""
        cta = "Retweet if this helped you. What's your biggest challenge with this topic?"
        duration = "2-3 minutes read time"
    
    else:  # Default/other platforms
        title = f"{platform.title()} Post: {topic} Insights"
        body = f"""
**Hook:** {best_hook}

**Key Points:**
• Main insight about {topic}
• Supporting example or data
• Actionable takeaway

**Engagement:**
• Ask engaging question
• Encourage sharing/comments
"""
        cta = "Let me know your thoughts in the comments!"
        duration = "1-2 minutes"
    
    return GeneratedScript(
        platform=platform,
        title=title,
        hook=best_hook,
        body_outline=body,
        cta=cta,
        topic=topic,
        estimated_duration=duration
    )


@router.get("/competitors/{competitor_id}/content", response_model=CompetitorContentResponse)
async def get_competitor_content(
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Fetch recent posts from a tracked competitor using the appropriate social API."""
    try:
        # Get competitor info
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        posts = []
        platform = competitor.platform.lower()
        handle = competitor.handle
        
        # Fetch content based on platform
        if platform == "instagram":
            token = await get_social_account_token(db, "instagram")
            if not token:
                raise HTTPException(status_code=422, detail="Instagram account not connected")
            posts = await fetch_instagram_content(handle, token)
        
        elif platform == "x":
            token = await get_social_account_token(db, "x")
            if not token:
                raise HTTPException(status_code=422, detail="X account not connected")
            posts = await fetch_x_content(handle, token)
        
        elif platform == "youtube":
            # For YouTube, we'd need API key configuration
            # For now, return mock data or implement with available API key
            raise HTTPException(status_code=422, detail="YouTube content fetching not configured")
        
        else:
            raise HTTPException(status_code=422, detail=f"Content fetching not supported for {platform}")
        
        # Calculate average engagement
        avg_engagement = sum(p.engagement_score for p in posts) / len(posts) if posts else 0
        
        return CompetitorContentResponse(
            competitor_id=competitor_id,
            platform=platform,
            handle=handle,
            posts=posts,
            total_posts=len(posts),
            avg_engagement=avg_engagement
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch competitor content: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch competitor content")


@router.get("/competitors/trending-topics", response_model=TrendingTopicsResponse)
async def get_trending_topics(
    platform: Optional[str] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_crm_db)
):
    """Analyze all competitor content to extract common themes/topics ranked by engagement."""
    try:
        # Get competitors
        query = select(Competitor)
        if platform:
            query = query.where(Competitor.platform == platform.lower())
        
        result = await db.execute(query)
        competitors = result.scalars().all()
        
        all_posts = []
        total_analyzed = 0
        
        # Fetch content for each competitor
        for competitor in competitors:
            try:
                platform_name = competitor.platform.lower()
                handle = competitor.handle
                
                posts = []
                if platform_name == "instagram":
                    token = await get_social_account_token(db, "instagram")
                    if token:
                        posts = await fetch_instagram_content(handle, token)
                elif platform_name == "x":
                    token = await get_social_account_token(db, "x")
                    if token:
                        posts = await fetch_x_content(handle, token)
                
                # Filter posts to specified timeframe
                cutoff_date = datetime.now() - timedelta(days=days)
                recent_posts = [p for p in posts if p.timestamp >= cutoff_date]
                
                all_posts.extend(recent_posts)
                total_analyzed += len(recent_posts)
                
            except Exception as e:
                logger.warning(f"Failed to fetch content for competitor {competitor.handle}: {e}")
                continue
        
        # Analyze trending topics
        trending_topics = await analyze_trending_topics(all_posts)
        
        return TrendingTopicsResponse(
            topics=trending_topics,
            total_analyzed_posts=total_analyzed,
            timeframe_days=days
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze trending topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze trending topics")


@router.post("/competitors/{competitor_id}/generate-script", response_model=GeneratedScript)
async def generate_content_script(
    competitor_id: int,
    request: ScriptGenerationRequest,
    save_to_db: bool = False,
    db: AsyncSession = Depends(get_crm_db)
):
    """Generate a script document based on competitor analysis."""
    try:
        # Get competitor info
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        # Fetch competitor's content to extract hooks
        posts = []
        platform_name = competitor.platform.lower()
        handle = competitor.handle
        
        if platform_name == "instagram":
            token = await get_social_account_token(db, "instagram")
            if token:
                posts = await fetch_instagram_content(handle, token)
        elif platform_name == "x":
            token = await get_social_account_token(db, "x")
            if token:
                posts = await fetch_x_content(handle, token)
        
        # Extract hooks from top-performing posts
        sorted_posts = sorted(posts, key=lambda x: x.engagement_score, reverse=True)
        top_posts = sorted_posts[:5]  # Top 5 posts
        hooks = await extract_hooks_from_posts(top_posts)
        
        # Use provided topic or derive from trending analysis
        topic = request.topic or "content creation"
        
        # Generate script
        script = generate_script_content(
            competitor_handle=handle,
            platform=request.platform,
            topic=topic,
            hooks=hooks
        )
        
        script.competitor_id = competitor_id
        script.source_post_url = top_posts[0].url if top_posts else None
        
        # Optionally save to database
        if save_to_db:
            content_script = ContentScript(
                competitor_id=competitor_id,
                platform=request.platform,
                title=script.title,
                hook=script.hook,
                body=script.body_outline,
                cta=script.cta,
                topic=topic,
                source_post_url=script.source_post_url,
                status='generated'
            )
            
            db.add(content_script)
            await db.commit()
            await db.refresh(content_script)
            
            script.id = content_script.id
        
        return script
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate script: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate script")


@router.get("/competitors/scripts", response_model=List[GeneratedScript])
async def list_generated_scripts(
    platform: Optional[str] = None,
    competitor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """List all generated content scripts."""
    try:
        query = select(ContentScript).order_by(ContentScript.created_at.desc())
        
        if platform:
            query = query.where(ContentScript.platform == platform.lower())
        if competitor_id:
            query = query.where(ContentScript.competitor_id == competitor_id)
        
        result = await db.execute(query)
        scripts = result.scalars().all()
        
        return [
            GeneratedScript(
                id=script.id,
                competitor_id=script.competitor_id,
                platform=script.platform,
                title=script.title or "",
                hook=script.hook or "",
                body_outline=script.body or "",
                cta=script.cta or "",
                topic=script.topic,
                source_post_url=script.source_post_url
            )
            for script in scripts
        ]
        
    except Exception as e:
        logger.error(f"Failed to list scripts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list scripts")


@router.delete("/competitors/scripts/{script_id}")
async def delete_script(
    script_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Delete a generated script."""
    try:
        result = await db.execute(
            select(ContentScript).where(ContentScript.id == script_id)
        )
        script = result.scalar_one_or_none()
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        await db.delete(script)
        await db.commit()
        
        return {"message": "Script deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete script: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete script")