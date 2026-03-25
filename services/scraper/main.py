"""Scraper Microservice — FastAPI wrapper for Instagram scraping functionality.

Extracted from the monolith backend, this service handles:
- Instagram profile scraping with authenticated sessions
- Comment scraping from posts
- Follow/batch follow actions
- Cookie session management

Environment Variables:
- INSTAGRAM_USERNAME: Instagram username for authenticated scraping
- INSTAGRAM_PASSWORD: Instagram password  
- INSTAGRAM_TOTP_SECRET: TOTP secret for 2FA (optional)
- INSTAGRAM_COOKIE_PATH: Path to store session cookies (default: /data/instagram_cookies.json)
"""

import logging
import os
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local imports (copied from backend)
from instagram_scraper import (
    ScrapedPost,
    ScrapedProfile, 
    scrape_profile,
    scrape_multiple,
    follow_instagram_user,
    follow_multiple_users,
    force_relogin,
    COOKIE_PATH,
)
from comment_scraper import scrape_post_comments

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="War Room Scraper Service",
    description="Instagram scraping microservice with authenticated sessions",
    version="1.0.0",
)

# Request/Response Models
class ScrapeProfileRequest(BaseModel):
    handle: str

class ScrapeCommentsRequest(BaseModel):
    shortcode: str
    limit: int = 50

class FollowRequest(BaseModel):
    handle: str

class BatchFollowRequest(BaseModel):
    handles: List[str]
    delay: float = 5.0

class ScrapeProfileResponse(BaseModel):
    handle: str
    full_name: str
    bio: str
    followers: int
    following: int
    post_count: int
    profile_pic_url: str
    is_private: bool
    is_verified: bool
    external_url: str
    bio_links: List[Dict[str, str]]
    threads_handle: str
    category: str
    posts: List[Dict]  # ScrapedPost as dict
    scraped_at: Optional[str]
    error: Optional[str]

class CommentResponse(BaseModel):
    username: str
    text: str
    likes: int
    timestamp: Optional[str]
    is_reply: bool
    is_verified: bool
    profile_url: Optional[str]

class FollowResponse(BaseModel):
    success: bool
    message: str
    already_following: Optional[bool] = None

# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "war-room-scraper",
        "cookie_path_exists": COOKIE_PATH.exists(),
        "instagram_username_configured": bool(os.getenv("INSTAGRAM_USERNAME")),
    }

# Cookie Status
@app.get("/cookie-status")
async def cookie_status():
    """Check if authenticated Instagram session exists."""
    cookie_exists = COOKIE_PATH.exists()
    cookie_size = COOKIE_PATH.stat().st_size if cookie_exists else 0
    
    return {
        "cookie_file_exists": cookie_exists,
        "cookie_file_size": cookie_size,
        "cookie_file_path": str(COOKIE_PATH),
        "last_modified": COOKIE_PATH.stat().st_mtime if cookie_exists else None,
    }

# Force Re-login
@app.post("/force-relogin")
async def force_relogin_endpoint():
    """Force a fresh Instagram login - use when scrapes start failing."""
    try:
        success = await force_relogin()
        return {
            "success": success,
            "message": "Fresh login successful" if success else "Login failed - check credentials"
        }
    except Exception as e:
        logger.error("Force relogin failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Relogin failed: {str(e)}")

# Profile Scraping
@app.post("/scrape-profile", response_model=ScrapeProfileResponse)
async def scrape_profile_endpoint(request: ScrapeProfileRequest):
    """Scrape an Instagram profile with posts."""
    try:
        profile = await scrape_profile(request.handle)
        
        # Convert ScrapedPost objects to dicts
        posts_dict = []
        for post in profile.posts:
            post_dict = {
                "shortcode": post.shortcode,
                "post_url": post.post_url,
                "caption": post.caption,
                "likes": post.likes,
                "comments": post.comments,
                "views": post.views,
                "media_type": post.media_type,
                "media_url": post.media_url,
                "thumbnail_url": post.thumbnail_url,
                "posted_at": post.posted_at.isoformat() if post.posted_at else None,
                "is_reel": post.is_reel,
                "engagement_score": post.engagement_score,
                "hook": post.hook,
                "music_info": post.music_info,
            }
            posts_dict.append(post_dict)
        
        return ScrapeProfileResponse(
            handle=profile.handle,
            full_name=profile.full_name,
            bio=profile.bio,
            followers=profile.followers,
            following=profile.following,
            post_count=profile.post_count,
            profile_pic_url=profile.profile_pic_url,
            is_private=profile.is_private,
            is_verified=profile.is_verified,
            external_url=profile.external_url,
            bio_links=profile.bio_links,
            threads_handle=profile.threads_handle,
            category=profile.category,
            posts=posts_dict,
            scraped_at=profile.scraped_at.isoformat() if profile.scraped_at else None,
            error=profile.error,
        )
    except Exception as e:
        logger.error("Profile scraping failed for @%s: %s", request.handle, e)
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

# Comment Scraping
@app.post("/scrape-comments")
async def scrape_comments_endpoint(request: ScrapeCommentsRequest):
    """Scrape comments from an Instagram post."""
    try:
        comments = await scrape_post_comments(request.shortcode, request.limit)
        
        return {
            "shortcode": request.shortcode,
            "comments_count": len(comments),
            "comments": comments,
        }
    except Exception as e:
        logger.error("Comment scraping failed for %s: %s", request.shortcode, e)
        raise HTTPException(status_code=500, detail=f"Comment scraping failed: {str(e)}")

# Follow User
@app.post("/follow", response_model=FollowResponse)
async def follow_user_endpoint(request: FollowRequest):
    """Follow an Instagram user."""
    try:
        result = await follow_instagram_user(request.handle)
        return FollowResponse(**result)
    except Exception as e:
        logger.error("Follow failed for @%s: %s", request.handle, e)
        raise HTTPException(status_code=500, detail=f"Follow failed: {str(e)}")

# Batch Follow
@app.post("/follow-batch")
async def batch_follow_endpoint(request: BatchFollowRequest):
    """Follow multiple Instagram users with delays."""
    try:
        results = await follow_multiple_users(request.handles, request.delay)
        
        return {
            "total_handles": len(request.handles),
            "delay_between": request.delay,
            "results": results,
        }
    except Exception as e:
        logger.error("Batch follow failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Batch follow failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18797)