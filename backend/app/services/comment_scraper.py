"""Instagram comment scraper — authenticated Playwright sessions.

Scrapes comments from competitor posts using our authenticated browser session.
Stores top comments per post for audience intelligence analysis.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

COOKIE_PATH = Path(os.getenv("INSTAGRAM_COOKIE_PATH", "/data/instagram_cookies.json"))


async def scrape_post_comments(
    shortcode: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Scrape comments from a single Instagram post using authenticated Playwright.
    
    Returns list of comments: [{username, text, likes, timestamp, is_reply}]
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright not installed")
        return []
    
    comments: List[Dict] = []
    captured_comments: List[Dict] = []
    
    async def intercept_response(response):
        """Capture comment data from Instagram API responses."""
        url = response.url
        try:
            if response.status != 200:
                return
            
            # GraphQL comment responses
            if "graphql" in url and ("comment" in url.lower() or "edge_media_to" in url.lower()):
                data = await response.json()
                _extract_comments_from_graphql(data, captured_comments)
            
            # v1 API comments
            elif "/api/v1/media/" in url and "/comments" in url:
                data = await response.json()
                _extract_comments_from_v1(data, captured_comments)
                
        except Exception:
            pass
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
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
            
            # Load cookies
            if COOKIE_PATH.exists():
                try:
                    cookies = json.loads(COOKIE_PATH.read_text())
                    if cookies:
                        await context.add_cookies(cookies)
                except Exception as e:
                    logger.warning("Failed to load cookies: %s", e)
            
            page = await context.new_page()
            page.on("response", intercept_response)
            
            post_url = f"https://www.instagram.com/p/{shortcode}/"
            logger.info("Scraping comments from %s", post_url)
            
            await page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
            
            # Wait for comments to load
            try:
                await page.wait_for_selector(
                    'ul[class*="comment"], div[class*="comment"], span[class*="comment"]',
                    timeout=10000,
                )
            except Exception:
                logger.debug("No comment selector found, trying scroll...")
            
            # Scroll to load more comments (Instagram lazy-loads them)
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)
                
                # Click "View more comments" if present
                try:
                    more_btn = await page.query_selector(
                        'button:has-text("View all"), button:has-text("more comments"), '
                        'span:has-text("View all"), a:has-text("View all")'
                    )
                    if more_btn:
                        await more_btn.click()
                        await asyncio.sleep(2)
                except Exception:
                    pass
            
            # Give time for API responses
            await asyncio.sleep(2)
            
            # If no comments captured via API interception, try DOM extraction
            if not captured_comments:
                captured_comments.extend(await _extract_comments_from_dom(page))
            
            await browser.close()
    
    except Exception as e:
        logger.error("Comment scraping error for %s: %s", shortcode, e)
        return []
    
    # Deduplicate and sort by likes
    seen = set()
    for c in captured_comments:
        key = f"{c.get('username', '')}:{c.get('text', '')[:50]}"
        if key not in seen:
            seen.add(key)
            comments.append(c)
    
    comments.sort(key=lambda x: x.get("likes", 0), reverse=True)
    return comments[:limit]


def _extract_comments_from_graphql(data: dict, out: list):
    """Extract comments from GraphQL response data."""
    # Navigate nested structure to find comment edges
    def _find_comments(obj, depth=0):
        if depth > 10 or not isinstance(obj, dict):
            return
        
        # Look for comment edge arrays
        for key in ["edge_media_to_parent_comment", "edge_media_to_comment",
                     "edge_media_preview_comment", "comments"]:
            if key in obj:
                edges = obj[key]
                if isinstance(edges, dict):
                    edges = edges.get("edges", [])
                if isinstance(edges, list):
                    for edge in edges:
                        node = edge.get("node", edge) if isinstance(edge, dict) else {}
                        if isinstance(node, dict) and node.get("text"):
                            owner = node.get("owner", {})
                            out.append({
                                "username": owner.get("username", "") or node.get("username", ""),
                                "text": node["text"],
                                "likes": node.get("edge_liked_by", {}).get("count", 0) or node.get("like_count", 0),
                                "timestamp": _format_timestamp(node.get("created_at")),
                                "is_reply": bool(node.get("edge_threaded_comments")),
                            })
        
        # Recurse into data/user/etc
        for key in ["data", "user", "media", "xdt_shortcode_media"]:
            if key in obj and isinstance(obj[key], dict):
                _find_comments(obj[key], depth + 1)
    
    _find_comments(data)


def _extract_comments_from_v1(data: dict, out: list):
    """Extract comments from v1 API response."""
    comments = data.get("comments", [])
    for c in comments:
        if not isinstance(c, dict):
            continue
        user = c.get("user", {})
        out.append({
            "username": user.get("username", ""),
            "text": c.get("text", ""),
            "likes": c.get("comment_like_count", 0),
            "timestamp": _format_timestamp(c.get("created_at")),
            "is_reply": bool(c.get("parent_comment_id")),
        })


async def _extract_comments_from_dom(page) -> list:
    """Fallback: extract visible comments from DOM."""
    try:
        return await page.evaluate("""() => {
            const comments = [];
            
            // Find comment containers
            const commentEls = document.querySelectorAll(
                'ul li[role="menuitem"], div[class*="comment"] > div, ul > div > li'
            );
            
            for (const el of commentEls) {
                const usernameEl = el.querySelector('a[href*="/"] span, h3 a, a[role="link"]');
                const textEl = el.querySelector('span:not(:first-child), div > span');
                const likeEl = el.querySelector('button[class*="like"] span, span[class*="like"]');
                
                if (usernameEl && textEl) {
                    const username = usernameEl.textContent?.trim() || '';
                    const text = textEl.textContent?.trim() || '';
                    
                    // Skip if it looks like a username repeat or empty
                    if (text && text !== username && text.length > 1) {
                        comments.push({
                            username: username.replace('@', ''),
                            text: text,
                            likes: parseInt(likeEl?.textContent?.replace(/[^0-9]/g, '') || '0') || 0,
                            timestamp: null,
                            is_reply: false
                        });
                    }
                }
            }
            
            return comments;
        }""")
    except Exception as e:
        logger.debug("DOM comment extraction failed: %s", e)
        return []


def _format_timestamp(ts) -> Optional[str]:
    """Format Unix timestamp to ISO string."""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts)).isoformat()
    except (ValueError, TypeError):
        return None


async def scrape_competitor_comments(
    db: AsyncSession,
    competitor_id: int,
    top_n: int = 10,
    comments_per_post: int = 50,
) -> Dict:
    """Scrape comments for top N posts by engagement that don't have comments yet.
    
    Returns: {processed: int, scraped: int, total_comments: int, errors: [str]}
    """
    result = await db.execute(
        text("""
            SELECT id, shortcode
            FROM crm.competitor_posts
            WHERE competitor_id = :cid
              AND comments_data IS NULL
              AND shortcode IS NOT NULL
              AND comments > 5
            ORDER BY engagement_score DESC
            LIMIT :lim
        """),
        {"cid": competitor_id, "lim": top_n},
    )
    posts = result.fetchall()
    
    if not posts:
        return {"processed": 0, "scraped": 0, "total_comments": 0, "errors": []}
    
    stats = {"processed": 0, "scraped": 0, "total_comments": 0, "errors": []}
    
    for post_id, shortcode in posts:
        stats["processed"] += 1
        logger.info("Scraping comments for %s...", shortcode)
        
        try:
            comments = await scrape_post_comments(shortcode, limit=comments_per_post)
            
            if comments:
                await db.execute(
                    text("UPDATE crm.competitor_posts SET comments_data = :c WHERE id = :id"),
                    {"c": json.dumps(comments), "id": post_id},
                )
                await db.commit()
                stats["scraped"] += 1
                stats["total_comments"] += len(comments)
                logger.info("✅ %s: %d comments stored", shortcode, len(comments))
            else:
                # Store empty array to mark as attempted
                await db.execute(
                    text("UPDATE crm.competitor_posts SET comments_data = '[]' WHERE id = :id"),
                    {"id": post_id},
                )
                await db.commit()
                stats["errors"].append(f"{shortcode}: no comments found")
        
        except Exception as e:
            stats["errors"].append(f"{shortcode}: {str(e)[:100]}")
            logger.error("Comment scraping failed for %s: %s", shortcode, e)
        
        # Random delay between posts to avoid rate limiting
        import random
        await asyncio.sleep(random.uniform(2, 5))
    
    return stats
