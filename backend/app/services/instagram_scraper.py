"""Instagram public profile scraper — Playwright headless browser.

No paid services. No third-party APIs. Our own scraper.

Uses Playwright to:
1. Load public Instagram profile pages in headless Chromium
2. Intercept the GraphQL API responses Instagram makes internally
3. Extract profile data + recent posts with full engagement metrics

Only works on PUBLIC accounts. That's all we need for competitor intel.
"""

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPost:
    """A single scraped post from a public Instagram profile."""
    shortcode: str
    post_url: str
    caption: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    media_type: str = "image"  # image, video, reel, carousel
    media_url: str = ""
    thumbnail_url: str = ""
    posted_at: Optional[datetime] = None
    is_reel: bool = False
    engagement_score: float = 0.0
    hook: str = ""


@dataclass
class ScrapedProfile:
    """Scraped public profile data."""
    handle: str
    full_name: str = ""
    bio: str = ""
    followers: int = 0
    following: int = 0
    post_count: int = 0
    profile_pic_url: str = ""
    is_private: bool = False
    is_verified: bool = False
    external_url: str = ""
    category: str = ""
    posts: List[ScrapedPost] = field(default_factory=list)
    scraped_at: Optional[datetime] = None
    error: Optional[str] = None


def _extract_hook(caption: str) -> str:
    """Extract the hook (first meaningful sentence) from a caption."""
    if not caption:
        return ""
    text = caption.strip()
    first_line = text.split("\n")[0].strip()
    for delim in [".", "!", "?"]:
        if delim in first_line:
            hook = first_line.split(delim)[0].strip() + delim
            if 10 <= len(hook) <= 200:
                return hook
    if len(first_line) > 150:
        return first_line[:147] + "..."
    return first_line


def _calc_engagement(likes: int, comments: int, views: int = 0) -> float:
    """Engagement score. Comments weighted 3x."""
    return likes * 1.0 + comments * 3.0


def _parse_user_data(user_data: Dict[str, Any], handle: str) -> ScrapedProfile:
    """Parse user data from any Instagram API response format into ScrapedProfile."""
    profile = ScrapedProfile(
        handle=handle,
        full_name=user_data.get("full_name", ""),
        bio=user_data.get("biography", ""),
        followers=(
            user_data.get("edge_followed_by", {}).get("count", 0)
            or user_data.get("follower_count", 0)
        ),
        following=(
            user_data.get("edge_follow", {}).get("count", 0)
            or user_data.get("following_count", 0)
        ),
        post_count=(
            user_data.get("edge_owner_to_timeline_media", {}).get("count", 0)
            or user_data.get("media_count", 0)
        ),
        profile_pic_url=(
            user_data.get("profile_pic_url_hd", "")
            or user_data.get("profile_pic_url", "")
            or user_data.get("hd_profile_pic_url_info", {}).get("url", "")
        ),
        is_private=user_data.get("is_private", False),
        is_verified=user_data.get("is_verified", False),
        external_url=user_data.get("external_url", "") or "",
        category=user_data.get("category_name", "") or "",
        scraped_at=datetime.now(),
    )

    if profile.is_private:
        profile.error = "Account is private"
        return profile

    # Parse posts from timeline media edges
    timeline = user_data.get("edge_owner_to_timeline_media", {})
    edges = timeline.get("edges", [])
    if edges:
        profile.posts = _parse_posts_from_edges(edges)

    return profile


def _parse_posts_from_edges(edges: List[Dict]) -> List[ScrapedPost]:
    """Parse post data from Instagram GraphQL edge nodes."""
    posts = []
    for edge in edges:
        node = edge.get("node", edge)
        shortcode = node.get("shortcode", "")
        if not shortcode:
            continue

        typename = node.get("__typename", "")
        is_video = node.get("is_video", False)
        product_type = node.get("product_type", "")

        if "Reel" in typename or product_type == "clips":
            media_type, is_reel = "reel", True
        elif is_video:
            media_type, is_reel = "video", False
        elif "Sidecar" in typename:
            media_type, is_reel = "carousel", False
        else:
            media_type, is_reel = "image", False

        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
        caption = caption_edges[0].get("node", {}).get("text", "") if caption_edges else ""

        likes = (
            node.get("edge_liked_by", {}).get("count", 0)
            or node.get("edge_media_preview_like", {}).get("count", 0)
        )
        comments = (
            node.get("edge_media_to_comment", {}).get("count", 0)
            or node.get("edge_media_preview_comment", {}).get("count", 0)
        )
        views = node.get("video_view_count", 0) or 0

        timestamp = node.get("taken_at_timestamp")
        posted_at = datetime.fromtimestamp(timestamp) if timestamp else None

        media_url = node.get("video_url", "") or node.get("display_url", "")
        thumbnail_url = node.get("thumbnail_src", "") or node.get("display_url", "")

        posts.append(ScrapedPost(
            shortcode=shortcode,
            post_url=f"https://www.instagram.com/p/{shortcode}/",
            caption=caption,
            likes=likes,
            comments=comments,
            views=views,
            media_type=media_type,
            media_url=media_url,
            thumbnail_url=thumbnail_url,
            posted_at=posted_at,
            is_reel=is_reel,
            engagement_score=_calc_engagement(likes, comments, views),
            hook=_extract_hook(caption),
        ))
    return posts


def _parse_media_items(items: List[Dict]) -> List[ScrapedPost]:
    """Parse posts from Instagram's v1 API format (items array)."""
    posts = []
    for item in items:
        code = item.get("code", "")
        if not code:
            continue

        media_type_int = item.get("media_type", 1)
        product_type = item.get("product_type", "")
        
        if product_type == "clips":
            media_type, is_reel = "reel", True
        elif media_type_int == 2:
            media_type, is_reel = "video", False
        elif media_type_int == 8:
            media_type, is_reel = "carousel", False
        else:
            media_type, is_reel = "image", False

        caption_obj = item.get("caption") or {}
        caption = caption_obj.get("text", "") if isinstance(caption_obj, dict) else ""

        likes = item.get("like_count", 0) or 0
        comments = item.get("comment_count", 0) or 0
        views = item.get("play_count", 0) or item.get("view_count", 0) or 0

        taken_at = item.get("taken_at")
        posted_at = datetime.fromtimestamp(taken_at) if taken_at else None

        # Get best image
        candidates = item.get("image_versions2", {}).get("candidates", [])
        thumbnail_url = candidates[0].get("url", "") if candidates else ""
        
        video_versions = item.get("video_versions", [])
        media_url = video_versions[0].get("url", "") if video_versions else thumbnail_url

        posts.append(ScrapedPost(
            shortcode=code,
            post_url=f"https://www.instagram.com/p/{code}/",
            caption=caption,
            likes=likes,
            comments=comments,
            views=views,
            media_type=media_type,
            media_url=media_url,
            thumbnail_url=thumbnail_url,
            posted_at=posted_at,
            is_reel=is_reel,
            engagement_score=_calc_engagement(likes, comments, views),
            hook=_extract_hook(caption),
        ))
    return posts


async def scrape_profile(handle: str) -> ScrapedProfile:
    """Scrape a public Instagram profile using Playwright.
    
    Launches headless Chromium, navigates to the profile page, and intercepts
    the GraphQL/API responses that Instagram makes internally to load profile data.
    """
    handle = handle.strip().lstrip("@").lower()
    profile = ScrapedProfile(handle=handle, scraped_at=datetime.now())

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        profile.error = "Playwright not installed. Run: pip install playwright && playwright install chromium"
        return profile

    captured_data: Dict[str, Any] = {}

    async def intercept_response(response):
        """Capture Instagram API responses."""
        url = response.url
        try:
            if response.status != 200:
                return

            # Capture web_profile_info responses
            if "web_profile_info" in url and "username" in url:
                data = await response.json()
                user = data.get("data", {}).get("user")
                if user:
                    captured_data["user"] = user
                    logger.info(f"Captured web_profile_info for @{handle}")

            # Capture graphql user responses
            elif "/graphql" in url or "graphql/query" in url:
                data = await response.json()
                user = (
                    data.get("data", {}).get("user")
                    or data.get("data", {}).get("xdt_api__v1__feed__user_timeline_graphql_connection", {})
                )
                if user and isinstance(user, dict):
                    if "edge_followed_by" in user or "follower_count" in user or "edge_owner_to_timeline_media" in user:
                        captured_data["user"] = user
                        logger.info(f"Captured GraphQL user data for @{handle}")
                    # Also capture timeline media separately
                    edges = user.get("edges", [])
                    if edges and any("node" in e for e in edges):
                        captured_data["timeline_edges"] = edges

            # Capture v1 API user info
            elif "/api/v1/users/" in url and "/info" in url:
                data = await response.json()
                user = data.get("user")
                if user:
                    captured_data["user_v1"] = user
                    logger.info(f"Captured v1 user info for @{handle}")

            # Capture v1 feed
            elif "/api/v1/feed/user/" in url:
                data = await response.json()
                items = data.get("items", [])
                if items:
                    captured_data.setdefault("feed_items", []).extend(items)
                    logger.info(f"Captured {len(items)} feed items for @{handle}")

        except Exception:
            # Not JSON or other error — ignore
            pass

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                timezone_id="America/New_York",
            )

            page = await context.new_page()
            page.on("response", intercept_response)

            # Navigate to profile
            url = f"https://www.instagram.com/{handle}/"
            logger.info(f"Navigating to {url}")

            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if resp and resp.status == 404:
                profile.error = "Profile not found (404)"
                await browser.close()
                return profile

            # Wait for profile content to render
            # Try waiting for specific selectors that indicate data has loaded
            try:
                await page.wait_for_selector(
                    'header section, [data-testid="user-avatar"], meta[property="og:title"]',
                    timeout=15000,
                )
            except Exception:
                logger.debug("Timeout waiting for header section, continuing...")

            # Give extra time for API calls to complete
            await asyncio.sleep(3)

            # If network interception didn't capture data, try extracting from DOM
            if "user" not in captured_data and "user_v1" not in captured_data:
                logger.info("No API data intercepted, trying DOM extraction...")
                dom_data = await _extract_from_dom(page, handle)
                if dom_data:
                    captured_data["dom"] = dom_data

            await browser.close()

    except Exception as e:
        profile.error = f"Browser error: {str(e)}"
        logger.error(f"Playwright error for @{handle}: {e}")
        return profile

    # Parse captured data into profile
    return _build_profile_from_captured(handle, captured_data)


async def _extract_from_dom(page, handle: str) -> Optional[Dict]:
    """Extract profile data directly from the rendered DOM as fallback."""
    try:
        data = await page.evaluate("""(handle) => {
            const result = {};
            
            // Try to get follower/following counts from the page
            const headerLinks = document.querySelectorAll('header a, header span, header li');
            for (const el of headerLinks) {
                const text = el.textContent || el.title || '';
                const titleAttr = el.getAttribute('title') || '';
                
                // Match patterns like "5,606 followers" or "123 posts"
                const followerMatch = text.match(/([\d,.]+[KMkm]?)\s*followers?/i) || 
                                     titleAttr.match(/([\d,.]+)/);
                const followingMatch = text.match(/([\d,.]+[KMkm]?)\s*following/i);
                const postsMatch = text.match(/([\d,.]+[KMkm]?)\s*posts?/i);
                
                if (followerMatch && text.toLowerCase().includes('follower')) {
                    result.followers_text = followerMatch[1];
                }
                if (followingMatch) {
                    result.following_text = followingMatch[1];
                }
                if (postsMatch) {
                    result.posts_text = postsMatch[1];
                }
            }
            
            // Get bio
            const bioSection = document.querySelector('header section > div > span, [data-testid="user-bio"]');
            if (bioSection) {
                result.bio = bioSection.textContent;
            }
            
            // Get full name
            const nameEl = document.querySelector('header h2, header span[dir]');
            if (nameEl) {
                result.full_name = nameEl.textContent;
            }
            
            // Get profile pic
            const avatar = document.querySelector('header img[alt*="profile"], header img[data-testid="user-avatar"]');
            if (avatar) {
                result.profile_pic_url = avatar.src;
            }
            
            // Check if private
            const privateText = document.body.textContent;
            result.is_private = privateText.includes('This account is private') || 
                               privateText.includes('This Account is Private');
            
            // Get post links from the grid
            const postLinks = document.querySelectorAll('article a[href*="/p/"], main a[href*="/p/"], a[href*="/reel/"]');
            result.post_urls = [];
            for (const link of postLinks) {
                const href = link.getAttribute('href');
                if (href) result.post_urls.push(href);
            }
            
            return result;
        }""", handle)
        
        return data if data and (data.get("followers_text") or data.get("post_urls")) else None
        
    except Exception as e:
        logger.debug(f"DOM extraction failed: {e}")
        return None


def _parse_count(text: str) -> int:
    """Parse count strings like '5,606', '12.3K', '1.2M'."""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    multipliers = {"k": 1000, "m": 1000000, "b": 1000000000}
    for suffix, mult in multipliers.items():
        if text.lower().endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _build_profile_from_captured(handle: str, captured: Dict) -> ScrapedProfile:
    """Build ScrapedProfile from all captured data sources."""
    
    # Priority: user (GraphQL/web_profile_info) > user_v1 > dom
    if "user" in captured:
        profile = _parse_user_data(captured["user"], handle)
    elif "user_v1" in captured:
        user = captured["user_v1"]
        profile = ScrapedProfile(
            handle=handle,
            full_name=user.get("full_name", ""),
            bio=user.get("biography", ""),
            followers=user.get("follower_count", 0),
            following=user.get("following_count", 0),
            post_count=user.get("media_count", 0),
            profile_pic_url=user.get("hd_profile_pic_url_info", {}).get("url", "")
                           or user.get("profile_pic_url", ""),
            is_private=user.get("is_private", False),
            is_verified=user.get("is_verified", False),
            external_url=user.get("external_url", "") or "",
            category=user.get("category_name", "") or "",
            scraped_at=datetime.now(),
        )
    elif "dom" in captured:
        dom = captured["dom"]
        profile = ScrapedProfile(
            handle=handle,
            full_name=dom.get("full_name", ""),
            bio=dom.get("bio", ""),
            followers=_parse_count(dom.get("followers_text", "")),
            following=_parse_count(dom.get("following_text", "")),
            post_count=_parse_count(dom.get("posts_text", "")),
            profile_pic_url=dom.get("profile_pic_url", ""),
            is_private=dom.get("is_private", False),
            scraped_at=datetime.now(),
        )
    else:
        return ScrapedProfile(
            handle=handle,
            scraped_at=datetime.now(),
            error="No data captured — profile may require login to view",
        )

    # Add feed items if captured separately
    if "feed_items" in captured and not profile.posts:
        profile.posts = _parse_media_items(captured["feed_items"])

    # Add timeline edges if captured separately
    if "timeline_edges" in captured and not profile.posts:
        profile.posts = _parse_posts_from_edges(captured["timeline_edges"])

    return profile


async def scrape_multiple(
    handles: List[str], delay_range: tuple = (3, 7)
) -> List[ScrapedProfile]:
    """Scrape multiple profiles with random delays between requests."""
    results = []
    for i, handle in enumerate(handles):
        logger.info(f"Scraping @{handle} ({i + 1}/{len(handles)})")
        profile = await scrape_profile(handle)
        results.append(profile)

        if profile.error:
            logger.warning(f"@{handle}: {profile.error}")
        else:
            logger.info(
                f"@{handle}: {profile.followers} followers, "
                f"{len(profile.posts)} posts scraped"
            )

        if i < len(handles) - 1:
            delay = random.uniform(*delay_range)
            logger.debug(f"Waiting {delay:.1f}s before next request...")
            await asyncio.sleep(delay)

    return results
