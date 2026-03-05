"""Content intelligence API endpoints for competitive analysis and script generation."""
import logging
import json
import re
import httpx
import random
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
    platform: str
    topic: str = "AI automation for small business"
    hook_style: str = "bold_claim"  # bold_claim, question, confession, comparison, statistic
    include_scene_map: bool = True
    save: bool = False


class SceneMap(BaseModel):
    """Individual scene in a video script."""
    scene_num: int
    duration: str
    type: str  # hook, problem, solution, example, cta
    text: str
    visual_notes: str


class FullScript(BaseModel):
    """Complete script with scene-by-scene breakdown."""
    id: Optional[int] = None
    competitor_id: Optional[int] = None
    platform: str
    title: str
    hook: str
    scenes: List[SceneMap]
    cta: str
    topic: str
    source_hooks: List[str]  # hooks that inspired this script
    estimated_duration: str
    created_at: Optional[datetime] = None


class GeneratedScript(BaseModel):
    """Generated content script (legacy model for compatibility)."""
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


class PlatformContentCard(BaseModel):
    """Content card format for platform content tab."""
    id: str
    title: str
    description: str
    platform: str
    status: str = "draft"
    estimated_duration: str
    hook: str
    cta: str
    scenes: Optional[List[SceneMap]] = None
    created_at: datetime


# Hook style templates
HOOK_TEMPLATES = {
    "bold_claim": [
        "Most people don't realize {problem} is costing them {cost} every month",
        "{number}% of {audience} are making this expensive mistake",
        "The truth about {topic} that {industry} doesn't want you to know",
        "I've analyzed {number} {audience} accounts, and here's what separates the winners",
        "This {solution} completely changed how I think about {topic}"
    ],
    "question": [
        "What if I told you {solution} could {benefit} in half the time?",
        "What would you do if you had an extra {number} hours per {timeframe}?",
        "Why do some {audience} {succeed} while others struggle with {problem}?",
        "Have you ever wondered why {situation} happens to some people and not others?",
        "What's the real difference between {group_a} and {group_b}?"
    ],
    "confession": [
        "I used to {bad_habit} until I discovered {solution}",
        "For years, I believed {misconception}. Here's what changed my mind",
        "I'll admit it: I was completely wrong about {topic}",
        "My biggest mistake was thinking {wrong_assumption}",
        "Here's the embarrassing truth about my first {number} years doing {activity}"
    ],
    "comparison": [
        "{successful_person} does {topic} differently than everyone else. Here's why",
        "The difference between {level_a} and {level_b} {audience} isn't what you think",
        "While everyone else is focused on {wrong_focus}, smart {audience} are doing {right_focus}",
        "Here's how {industry_leader} approaches {topic} vs how most people do it",
        "The gap between those who {succeed} and those who {fail} comes down to this"
    ],
    "statistic": [
        "{number}% of {audience} are {missing_out} and don't even know it",
        "Only {small_number} out of {large_number} {audience} actually {achievement}",
        "Studies show that {statistic} about {topic}, but here's the real story",
        "The average {audience} spends {time/money} on {activity}. Here's a better way",
        "After tracking {number} {audience} for {timeframe}, I found this pattern"
    ]
}

# Platform-specific scene templates
SCENE_TEMPLATES = {
    "youtube": [
        {"type": "hook", "duration": "0-5s", "purpose": "Grab attention immediately"},
        {"type": "problem", "duration": "5-15s", "purpose": "Establish the pain point"},
        {"type": "solution", "duration": "15-45s", "purpose": "Present your approach"},
        {"type": "example", "duration": "45-75s", "purpose": "Show real-world application"},
        {"type": "cta", "duration": "75-90s", "purpose": "Drive engagement"}
    ],
    "instagram": [
        {"type": "hook", "duration": "0-3s", "purpose": "Stop the scroll"},
        {"type": "problem", "duration": "3-10s", "purpose": "Connect with audience pain"},
        {"type": "solution", "duration": "10-25s", "purpose": "Provide value"},
        {"type": "cta", "duration": "25-30s", "purpose": "Drive action"}
    ],
    "tiktok": [
        {"type": "hook", "duration": "0-3s", "purpose": "Instant engagement"},
        {"type": "reveal", "duration": "3-8s", "purpose": "Build curiosity"},
        {"type": "content", "duration": "8-25s", "purpose": "Deliver the payoff"},
        {"type": "cta", "duration": "25-30s", "purpose": "Encourage interaction"}
    ]
}


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


def generate_hook_from_template(hook_style: str, topic: str, competitor_hooks: List[str]) -> str:
    """Generate a hook based on style template and competitor analysis."""
    templates = HOOK_TEMPLATES.get(hook_style, HOOK_TEMPLATES["bold_claim"])
    template = random.choice(templates)
    
    # Extract common themes from competitor hooks for context
    context_words = []
    for hook in competitor_hooks:
        words = re.findall(r'\b\w+\b', hook.lower())
        context_words.extend([w for w in words if len(w) > 4])
    
    # Basic template filling with topic-specific content
    replacements = {
        "problem": f"{topic} inefficiency",
        "cost": "$500-2000",
        "number": str(random.choice([75, 80, 85, 90, 95])),
        "audience": "business owners",
        "industry": "tech",
        "solution": topic,
        "benefit": "increase productivity",
        "timeframe": "week",
        "succeed": "scale successfully",
        "activity": topic.lower(),
        "topic": topic,
        "wrong_focus": "quick fixes",
        "right_focus": "systematic solutions",
        "achievement": "achieve consistent results",
        "time/money": "5+ hours per week"
    }
    
    # Fill template
    filled_template = template
    for key, value in replacements.items():
        filled_template = filled_template.replace(f"{{{key}}}", value)
    
    return filled_template


def generate_scene_content(scene_template: Dict, topic: str, hook: str, platform: str) -> SceneMap:
    """Generate content for a specific scene based on template."""
    scene_type = scene_template["type"]
    duration = scene_template["duration"]
    
    if scene_type == "hook":
        text = hook
        visual_notes = "Strong eye contact, confident posture, clear text overlay with hook"
    elif scene_type == "problem":
        text = f"Here's the challenge most people face with {topic}..."
        visual_notes = "Show problem visually - split screen, before/after, frustrated expressions"
    elif scene_type == "solution":
        text = f"But here's what actually works for {topic}..."
        visual_notes = "Smooth transition to solution, step-by-step visuals, positive energy"
    elif scene_type == "example":
        text = f"Let me show you exactly how this applies to {topic}..."
        visual_notes = "Real examples, screenshots, case study format, specific numbers"
    elif scene_type == "reveal":
        text = f"The surprising truth about {topic} is..."
        visual_notes = "Build suspense, reveal animation, emphasis on key points"
    elif scene_type == "content":
        text = f"Here's the step-by-step breakdown of {topic}..."
        visual_notes = "Clear bullet points, numbered steps, easy to follow visuals"
    elif scene_type == "cta":
        if platform == "youtube":
            text = "If this helped you understand {topic}, smash that like button and subscribe for more insights!"
        elif platform == "instagram":
            text = "Save this post about {topic} and share it with someone who needs to see this!"
        elif platform == "tiktok":
            text = "Follow for more {topic} tips that actually work!"
        else:
            text = f"What's your biggest challenge with {topic}? Drop a comment!"
        
        visual_notes = "Clear call-to-action text, engaging gesture, subscribe/follow buttons highlighted"
    
    # Replace topic placeholder in text
    text = text.replace("{topic}", topic)
    
    return SceneMap(
        scene_num=0,  # Will be set by caller
        duration=duration,
        type=scene_type,
        text=text,
        visual_notes=visual_notes
    )


async def generate_intelligent_script(
    topic: str, 
    platform: str, 
    hook_style: str, 
    competitor_hooks: List[str],
    competitor_id: Optional[int] = None
) -> FullScript:
    """Generate intelligent script with scene-by-scene breakdown."""
    
    # Generate hook using template and competitor analysis
    hook = generate_hook_from_template(hook_style, topic, competitor_hooks)
    
    # Platform-specific title generation
    if platform == "youtube":
        title = f"The Truth About {topic} (What Nobody Tells You)"
    elif platform == "instagram":
        title = f"{topic}: The Reality Check You Need"
    elif platform == "tiktok":
        title = f"POV: You finally understand {topic}"
    else:
        title = f"{topic}: What Actually Works"
    
    # Generate scenes based on platform
    scene_templates = SCENE_TEMPLATES.get(platform, SCENE_TEMPLATES["youtube"])
    scenes = []
    
    for i, scene_template in enumerate(scene_templates):
        scene = generate_scene_content(scene_template, topic, hook, platform)
        scene.scene_num = i + 1
        scenes.append(scene)
    
    # Platform-specific CTA
    if platform == "youtube":
        cta = f"Ready to master {topic}? Subscribe and hit the bell for weekly insights that actually move the needle!"
    elif platform == "instagram":
        cta = f"Save this {topic} breakdown and follow @youraccount for more game-changing insights!"
    elif platform == "tiktok":
        cta = f"Follow for daily {topic} tips that your competitors don't know! 🔥"
    elif platform == "x":
        cta = f"Retweet if this {topic} insight was valuable! What's your experience? 👇"
    else:
        cta = f"What's your biggest {topic} challenge? Let's solve it together!"
    
    # Calculate estimated duration
    if platform == "youtube":
        estimated_duration = "8-12 minutes"
    elif platform == "instagram":
        estimated_duration = "30-60 seconds"
    elif platform == "tiktok":
        estimated_duration = "15-30 seconds"
    else:
        estimated_duration = "2-3 minutes"
    
    return FullScript(
        competitor_id=competitor_id,
        platform=platform,
        title=title,
        hook=hook,
        scenes=scenes,
        cta=cta,
        topic=topic,
        source_hooks=competitor_hooks[:3],  # Top 3 hooks that inspired this
        estimated_duration=estimated_duration,
        created_at=datetime.now()
    )


def convert_to_legacy_format(full_script: FullScript) -> GeneratedScript:
    """Convert FullScript to legacy GeneratedScript format for compatibility."""
    
    # Convert scenes to body outline
    body_sections = []
    for scene in full_script.scenes:
        body_sections.append(f"**{scene.type.title()} ({scene.duration}):**\n{scene.text}\n*Visual: {scene.visual_notes}*")
    
    body_outline = "\n\n".join(body_sections)
    
    return GeneratedScript(
        id=full_script.id,
        competitor_id=full_script.competitor_id,
        platform=full_script.platform,
        title=full_script.title,
        hook=full_script.hook,
        body_outline=body_outline,
        cta=full_script.cta,
        topic=full_script.topic,
        estimated_duration=full_script.estimated_duration
    )


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
    """Generate a content script based on competitor analysis (legacy function)."""
    # This is the old hardcoded function, kept for backward compatibility
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


@router.post("/competitors/{competitor_id}/generate-script", response_model=FullScript)
async def generate_content_script_new(
    competitor_id: int,
    request: ScriptGenerationRequest,
    db: AsyncSession = Depends(get_crm_db)
):
    """Generate an intelligent script with scene-by-scene breakdown based on competitor analysis."""
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
        
        # Generate intelligent script
        script = await generate_intelligent_script(
            topic=request.topic,
            platform=request.platform,
            hook_style=request.hook_style,
            competitor_hooks=hooks,
            competitor_id=competitor_id
        )
        
        # Save to database if requested
        if request.save:
            # Convert scenes to JSON string
            scenes_json = json.dumps([scene.dict() for scene in script.scenes])
            
            content_script = ContentScript(
                competitor_id=competitor_id,
                platform=request.platform,
                title=script.title,
                hook=script.hook,
                body="\n".join([f"{scene.type}: {scene.text}" for scene in script.scenes]),
                cta=script.cta,
                topic=request.topic,
                scene_map=scenes_json,  # New field for scene data
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


@router.post("/competitors/{competitor_id}/generate-script-legacy", response_model=GeneratedScript)
async def generate_content_script_legacy(
    competitor_id: int,
    request: ScriptGenerationRequest,
    save_to_db: bool = False,
    db: AsyncSession = Depends(get_crm_db)
):
    """Generate a script document based on competitor analysis (legacy endpoint for backward compatibility)."""
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
        
        # Generate script using legacy function
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


@router.post("/content-intel/scripts/{script_id}/save-to-pipeline", response_model=PlatformContentCard)
async def save_script_to_pipeline(
    script_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Save a script to the platform content pipeline."""
    try:
        # Get the script
        result = await db.execute(
            select(ContentScript).where(ContentScript.id == script_id)
        )
        script = result.scalar_one_or_none()
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        # Parse scenes from JSON if available
        scenes = []
        if script.scene_map:
            try:
                scenes_data = json.loads(script.scene_map)
                scenes = [SceneMap(**scene_data) for scene_data in scenes_data]
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse scene_map for script {script_id}")
        
        # Create content card format expected by frontend
        content_card = PlatformContentCard(
            id=f"script_{script.id}",
            title=script.title or "Generated Script",
            description=script.body[:200] + "..." if script.body else "Script generated from competitor analysis",
            platform=script.platform,
            status="draft",
            estimated_duration=script.topic or "5-10 minutes",  # Using topic field as duration for now
            hook=script.hook or "",
            cta=script.cta or "",
            scenes=scenes if scenes else None,
            created_at=script.created_at or datetime.now()
        )
        
        # Update script status to indicate it's been saved to pipeline
        script.status = 'saved'
        await db.commit()
        
        return content_card
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save script to pipeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to save script to pipeline")


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