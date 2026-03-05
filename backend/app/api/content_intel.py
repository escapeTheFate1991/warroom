"""Enhanced Content intelligence API endpoints for competitive analysis and script generation."""
import logging
import json
import re
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter, defaultdict
import string

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db.crm_db import get_crm_db
from app.models.crm.competitor import Competitor
from app.models.crm.content_script import ContentScript
from app.models.crm.social import SocialAccount

# Import NLP libraries for better text processing
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.util import ngrams
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    NLTK_AVAILABLE = True
    
    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# Enhanced Pydantic models
class CompetitorPost(BaseModel):
    """Individual competitor post data."""
    text: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    timestamp: datetime
    url: str
    engagement_score: float = 0.0
    hook: Optional[str] = None


class CompetitorContentResponse(BaseModel):
    """Response for competitor content endpoint."""
    competitor_id: int
    platform: str
    handle: str
    posts: List[CompetitorPost]
    total_posts: int
    avg_engagement: float


class TrendingTopic(BaseModel):
    """Enhanced trending topic with clustering and engagement weighting."""
    topic: str
    frequency: int
    avg_engagement: float
    recency_weight: float
    final_score: float
    sources: List[str]
    keywords: List[str]
    related_topics: List[str] = []


class TrendingTopicsResponse(BaseModel):
    """Response for trending topics endpoint."""
    topics: List[TrendingTopic]
    total_analyzed_posts: int
    timeframe_days: int = 30


class TopContentItem(BaseModel):
    """Top performing content item."""
    text: str
    hook: str
    likes: int
    comments: int
    shares: int
    engagement_score: float
    platform: str
    competitor_handle: str
    url: str
    timestamp: datetime


class TopContentResponse(BaseModel):
    """Response for top content endpoint."""
    posts: List[TopContentItem]
    total_posts: int


class HookItem(BaseModel):
    """Extracted hook with engagement data."""
    hook: str
    engagement_score: float
    platform: str
    competitor_handle: str
    source_url: str


class HooksResponse(BaseModel):
    """Response for hooks endpoint."""
    hooks: List[HookItem]
    total_hooks: int


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


def calculate_engagement_score(likes: int, comments: int, shares: int) -> float:
    """Calculate engagement score with weighted values."""
    return likes * 1.0 + comments * 3.0 + shares * 5.0


def calculate_recency_weight(posted_at: datetime) -> float:
    """Calculate recency boost factor."""
    days_ago = (datetime.now() - posted_at).days
    
    if days_ago <= 7:
        return 2.0  # 2x boost for last 7 days
    elif days_ago <= 14:
        return 1.5  # 1.5x boost for last 14 days
    else:
        return 1.0  # No boost for older content


def extract_hook_from_text(text: str) -> str:
    """Extract hook (first sentence) from post text."""
    if not text:
        return ""
    
    # Clean text
    text = text.strip()
    lines = text.split('\n')
    first_line = lines[0].strip()
    
    if NLTK_AVAILABLE:
        try:
            sentences = sent_tokenize(first_line)
            if sentences:
                hook = sentences[0].strip()
                # Return hook if it's reasonable length
                if 10 <= len(hook) <= 200:
                    return hook
        except Exception:
            pass
    
    # Fallback: extract until first punctuation
    for delimiter in ['.', '!', '?']:
        if delimiter in first_line:
            hook = first_line.split(delimiter)[0].strip()
            if 10 <= len(hook) <= 200:
                return hook
    
    # Return first 150 chars if no good hook found
    return first_line[:150] + "..." if len(first_line) > 150 else first_line


def extract_ngrams(text: str, n: int = 2) -> List[str]:
    """Extract n-grams from text using NLTK if available."""
    if not text or not NLTK_AVAILABLE:
        return []
    
    try:
        # Clean and tokenize
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        tokens = word_tokenize(text)
        
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
        
        # Generate n-grams
        n_grams = list(ngrams(tokens, n))
        return [' '.join(gram) for gram in n_grams if len(' '.join(gram)) > 5]
    except Exception as e:
        logger.warning(f"Error extracting n-grams: {e}")
        return []


def cluster_topics(topics: List[str], max_clusters: int = 5) -> Dict[str, List[str]]:
    """Cluster similar topics together using TF-IDF and K-means."""
    if not topics or not NLTK_AVAILABLE or len(topics) < 2:
        return {topic: [topic] for topic in topics}
    
    try:
        # Use TF-IDF to vectorize topics
        vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2),
            stop_words='english'
        )
        
        # Fit and transform topics
        topic_vectors = vectorizer.fit_transform(topics)
        
        # Determine optimal number of clusters (min of topics/2 and max_clusters)
        n_clusters = min(max(len(topics) // 2, 1), max_clusters)
        
        # Cluster topics
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(topic_vectors)
        
        # Group topics by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[f"cluster_{label}"].append(topics[i])
        
        # Convert to regular dict with representative topic names
        result = {}
        for cluster_id, cluster_topics in clusters.items():
            # Use most frequent topic as cluster name
            cluster_name = Counter(cluster_topics).most_common(1)[0][0]
            result[cluster_name] = cluster_topics
        
        return result
        
    except Exception as e:
        logger.warning(f"Error clustering topics: {e}")
        # Fallback: group by first word
        clusters = defaultdict(list)
        for topic in topics:
            first_word = topic.split()[0] if topic else "other"
            clusters[first_word].append(topic)
        return dict(clusters)


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


async def save_competitor_posts(db: AsyncSession, competitor_id: int, platform: str, 
                               posts: List[CompetitorPost]) -> bool:
    """Save competitor posts to cache table."""
    try:
        # Delete old posts for this competitor/platform
        await db.execute(
            text("""
                DELETE FROM crm.competitor_posts 
                WHERE competitor_id = :competitor_id AND platform = :platform
            """),
            {"competitor_id": competitor_id, "platform": platform}
        )
        
        # Insert new posts
        for post in posts:
            await db.execute(
                text("""
                    INSERT INTO crm.competitor_posts 
                    (competitor_id, platform, post_text, likes, comments, shares, 
                     engagement_score, hook, post_url, posted_at, fetched_at)
                    VALUES (:competitor_id, :platform, :post_text, :likes, :comments, :shares,
                            :engagement_score, :hook, :post_url, :posted_at, NOW())
                """),
                {
                    "competitor_id": competitor_id,
                    "platform": platform,
                    "post_text": post.text,
                    "likes": post.likes,
                    "comments": post.comments,
                    "shares": post.shares,
                    "engagement_score": post.engagement_score,
                    "hook": extract_hook_from_text(post.text),
                    "post_url": post.url,
                    "posted_at": post.timestamp
                }
            )
        
        await db.commit()
        return True
        
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to save competitor posts: {e}")
        return False


async def load_cached_posts(db: AsyncSession, competitor_id: int = None, 
                           platform: str = None, days: int = 30) -> List[Dict]:
    """Load cached competitor posts from database."""
    try:
        query = """
            SELECT cp.*, c.handle 
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE cp.posted_at >= :cutoff_date
        """
        params = {"cutoff_date": datetime.now() - timedelta(days=days)}
        
        if competitor_id:
            query += " AND cp.competitor_id = :competitor_id"
            params["competitor_id"] = competitor_id
            
        if platform:
            query += " AND cp.platform = :platform"
            params["platform"] = platform
            
        query += " ORDER BY cp.engagement_score DESC"
        
        result = await db.execute(text(query), params)
        return [dict(row._mapping) for row in result.fetchall()]
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to load cached posts: {e}")
        return []


# Social media fetching functions (keep existing implementations but enhance error handling)
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
                engagement_score = calculate_engagement_score(
                    post.get("like_count", 0),
                    post.get("comments_count", 0),
                    0  # Instagram doesn't provide shares
                )
                
                posts.append(CompetitorPost(
                    text=post.get("caption", ""),
                    likes=post.get("like_count", 0),
                    comments=post.get("comments_count", 0),
                    shares=0,
                    timestamp=datetime.fromisoformat(post.get("timestamp", "").replace("Z", "+00:00")),
                    url=post.get("permalink", ""),
                    engagement_score=engagement_score,
                    hook=extract_hook_from_text(post.get("caption", ""))
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
                engagement_score = calculate_engagement_score(
                    metrics.get("like_count", 0),
                    metrics.get("reply_count", 0),
                    metrics.get("retweet_count", 0)
                )
                
                posts.append(CompetitorPost(
                    text=tweet.get("text", ""),
                    likes=metrics.get("like_count", 0),
                    comments=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                    timestamp=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")),
                    url=f"https://twitter.com/{handle}/status/{tweet.get('id')}",
                    engagement_score=engagement_score,
                    hook=extract_hook_from_text(tweet.get("text", ""))
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
                        
                        engagement_score = calculate_engagement_score(
                            int(stats.get("likeCount", 0)),
                            int(stats.get("commentCount", 0)),
                            0  # YouTube doesn't provide shares
                        )
                        
                        title_desc = snippet.get("title", "") + " " + snippet.get("description", "")[:200]
                        
                        posts.append(CompetitorPost(
                            text=title_desc,
                            likes=int(stats.get("likeCount", 0)),
                            comments=int(stats.get("commentCount", 0)),
                            shares=0,
                            timestamp=datetime.fromisoformat(snippet.get("publishedAt", "").replace("Z", "+00:00")),
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            engagement_score=engagement_score,
                            hook=extract_hook_from_text(title_desc)
                        ))
            
            return posts
            
    except Exception as e:
        logger.error(f"Failed to fetch YouTube content for {handle}: {e}")
        return []


async def analyze_trending_topics(posts: List[Dict], cluster_topics: bool = True) -> List[TrendingTopic]:
    """Enhanced topic analysis with n-grams, engagement weighting, and recency boost."""
    if not posts:
        return []
    
    # Extract meaningful phrases (bigrams and trigrams)
    phrase_data = defaultdict(lambda: {
        'posts': [],
        'engagement_scores': [],
        'recency_weights': []
    })
    
    for post in posts:
        text = post.get('post_text', '')
        if not text:
            continue
            
        posted_at = post.get('posted_at', datetime.now())
        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
            except:
                posted_at = datetime.now()
        
        engagement_score = post.get('engagement_score', 0)
        recency_weight = calculate_recency_weight(posted_at)
        
        # Extract bigrams and trigrams
        bigrams = extract_ngrams(text, 2)
        trigrams = extract_ngrams(text, 3)
        
        # Combine all phrases
        phrases = bigrams + trigrams
        
        for phrase in phrases:
            # Filter out generic phrases
            if len(phrase.split()) >= 2 and not any(word in phrase.lower() for word in 
                ['the', 'and', 'for', 'with', 'this', 'that', 'you', 'your', 'how']):
                phrase_data[phrase]['posts'].append(post)
                phrase_data[phrase]['engagement_scores'].append(engagement_score)
                phrase_data[phrase]['recency_weights'].append(recency_weight)
    
    # Calculate trending topics
    trending = []
    
    for phrase, data in phrase_data.items():
        frequency = len(data['posts'])
        
        # Only consider phrases that appear in at least 2 posts
        if frequency >= 2:
            avg_engagement = sum(data['engagement_scores']) / len(data['engagement_scores'])
            avg_recency = sum(data['recency_weights']) / len(data['recency_weights'])
            
            # Calculate final score: frequency * avg_engagement * recency_boost
            final_score = frequency * avg_engagement * avg_recency
            
            # Get source handles
            sources = list(set([post.get('handle', 'Unknown') for post in data['posts']]))
            
            trending.append(TrendingTopic(
                topic=phrase.title(),
                frequency=frequency,
                avg_engagement=avg_engagement,
                recency_weight=avg_recency,
                final_score=final_score,
                sources=sources[:5],  # Limit to 5 sources
                keywords=phrase.split()
            ))
    
    # Sort by final score
    trending.sort(key=lambda x: x.final_score, reverse=True)
    
    # Cluster related topics if requested
    if cluster_topics and trending:
        topic_names = [t.topic for t in trending[:20]]  # Top 20 topics
        clusters = cluster_topics(topic_names)
        
        # Add related topics to each trending topic
        for topic in trending[:20]:
            for cluster_name, cluster_topics in clusters.items():
                if topic.topic in cluster_topics:
                    related = [t for t in cluster_topics if t != topic.topic]
                    topic.related_topics = related[:3]  # Max 3 related topics
                    break
    
    return trending[:15]  # Return top 15 topics


# API Endpoints

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
        
        # First try to load from cache
        cached_posts = await load_cached_posts(db, competitor_id, platform)
        
        if cached_posts:
            # Convert cached posts to CompetitorPost objects
            for cached_post in cached_posts:
                posts.append(CompetitorPost(
                    text=cached_post.get('post_text', ''),
                    likes=cached_post.get('likes', 0),
                    comments=cached_post.get('comments', 0),
                    shares=cached_post.get('shares', 0),
                    timestamp=cached_post.get('posted_at', datetime.now()),
                    url=cached_post.get('post_url', ''),
                    engagement_score=cached_post.get('engagement_score', 0),
                    hook=cached_post.get('hook', '')
                ))
        else:
            # Fetch fresh content from APIs
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
            
            # Cache the posts if we fetched fresh data
            if posts:
                await save_competitor_posts(db, competitor_id, platform, posts)
        
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
        # Load cached posts from all competitors
        cached_posts = await load_cached_posts(db, platform=platform, days=days)
        
        if not cached_posts:
            # If no cached posts, we need to refresh data
            return TrendingTopicsResponse(
                topics=[],
                total_analyzed_posts=0,
                timeframe_days=days
            )
        
        # Analyze trending topics
        trending_topics = await analyze_trending_topics(cached_posts)
        
        return TrendingTopicsResponse(
            topics=trending_topics,
            total_analyzed_posts=len(cached_posts),
            timeframe_days=days
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze trending topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze trending topics")


@router.get("/competitors/top-content", response_model=TopContentResponse)
async def get_top_content(
    limit: int = 20,
    days: int = 30,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get top performing content across all competitors."""
    try:
        # Load cached posts sorted by engagement
        cached_posts = await load_cached_posts(db, platform=platform, days=days)
        
        if not cached_posts:
            return TopContentResponse(posts=[], total_posts=0)
        
        # Sort by engagement score and take top posts
        top_posts = sorted(cached_posts, key=lambda x: x.get('engagement_score', 0), reverse=True)[:limit]
        
        # Convert to response format
        top_content = []
        for post in top_posts:
            top_content.append(TopContentItem(
                text=post.get('post_text', ''),
                hook=post.get('hook', ''),
                likes=post.get('likes', 0),
                comments=post.get('comments', 0),
                shares=post.get('shares', 0),
                engagement_score=post.get('engagement_score', 0),
                platform=post.get('platform', ''),
                competitor_handle=post.get('handle', ''),
                url=post.get('post_url', ''),
                timestamp=post.get('posted_at', datetime.now())
            ))
        
        return TopContentResponse(
            posts=top_content,
            total_posts=len(cached_posts)
        )
        
    except Exception as e:
        logger.error(f"Failed to get top content: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top content")


@router.get("/competitors/hooks", response_model=HooksResponse)
async def get_hooks(
    limit: int = 50,
    days: int = 30,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get extracted hooks ranked by engagement score."""
    try:
        # Load cached posts
        cached_posts = await load_cached_posts(db, platform=platform, days=days)
        
        if not cached_posts:
            return HooksResponse(hooks=[], total_hooks=0)
        
        # Extract hooks and sort by engagement
        hooks = []
        for post in cached_posts:
            hook = post.get('hook', '')
            if hook and len(hook.strip()) > 10:  # Filter out short/empty hooks
                hooks.append(HookItem(
                    hook=hook,
                    engagement_score=post.get('engagement_score', 0),
                    platform=post.get('platform', ''),
                    competitor_handle=post.get('handle', ''),
                    source_url=post.get('post_url', '')
                ))
        
        # Sort by engagement and take top hooks
        hooks.sort(key=lambda x: x.engagement_score, reverse=True)
        top_hooks = hooks[:limit]
        
        return HooksResponse(
            hooks=top_hooks,
            total_hooks=len(hooks)
        )
        
    except Exception as e:
        logger.error(f"Failed to get hooks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get hooks")


@router.post("/competitors/refresh")
async def refresh_competitor_content(
    competitor_id: Optional[int] = None,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Re-fetch content for competitors and update cache."""
    try:
        # Get competitors to refresh
        query = select(Competitor)
        
        if competitor_id:
            query = query.where(Competitor.id == competitor_id)
        if platform:
            query = query.where(Competitor.platform == platform.lower())
            
        result = await db.execute(query)
        competitors = result.scalars().all()
        
        refreshed = 0
        errors = []
        
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
                elif platform_name == "youtube":
                    # Add YouTube implementation when API key is available
                    pass
                
                if posts:
                    success = await save_competitor_posts(db, competitor.id, platform_name, posts)
                    if success:
                        refreshed += 1
                    else:
                        errors.append(f"Failed to save posts for {handle}")
                else:
                    errors.append(f"No posts fetched for {handle}")
                    
            except Exception as e:
                logger.warning(f"Failed to refresh competitor {competitor.handle}: {e}")
                errors.append(f"Error refreshing {competitor.handle}: {str(e)}")
        
        return {
            "message": f"Refreshed content for {refreshed} competitors",
            "refreshed_competitors": refreshed,
            "total_competitors": len(competitors),
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh competitor content: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh competitor content")


# Keep existing script generation endpoints
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
        
        # Use cached posts for hook extraction
        cached_posts = await load_cached_posts(db, competitor_id)
        
        # Extract hooks from top-performing posts
        hooks = []
        if cached_posts:
            sorted_posts = sorted(cached_posts, key=lambda x: x.get('engagement_score', 0), reverse=True)
            for post in sorted_posts[:5]:  # Top 5 posts
                hook = post.get('hook', '')
                if hook:
                    hooks.append(hook)
        
        # Use provided topic or derive from trending analysis
        topic = request.topic or "content creation"
        
        # Generate script (reuse existing function)
        script = generate_script_content(
            competitor_handle=competitor.handle,
            platform=request.platform,
            topic=topic,
            hooks=hooks
        )
        
        script.competitor_id = competitor_id
        script.source_post_url = cached_posts[0].get('post_url', '') if cached_posts else None
        
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