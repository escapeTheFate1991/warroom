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
            
            # Wait for page to render comments
            await asyncio.sleep(4)
            
            # Scroll to load more comments
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1.5)
            
            # Try clicking "View all X comments" to expand
            try:
                view_all = await page.query_selector('text=/View all.*comment/i')
                if view_all:
                    await view_all.click()
                    await asyncio.sleep(3)
                    # Scroll more in expanded view
                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, 600)")
                        await asyncio.sleep(1.5)
            except Exception:
                pass
            
            # Primary extraction: DOM (Instagram 2026 format)
            # Comments are rendered in div containers with Reply text nodes
            captured_comments.extend(await _extract_comments_from_dom(page))
            logger.info("DOM extraction: %d comments from %s", len(captured_comments), shortcode)
            
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
                            username = owner.get("username", "") or node.get("username", "")
                            out.append({
                                "username": username,
                                "profile_url": f"https://www.instagram.com/{username}/" if username else None,
                                "text": node["text"],
                                "likes": node.get("edge_liked_by", {}).get("count", 0) or node.get("like_count", 0),
                                "timestamp": _format_timestamp(node.get("created_at")),
                                "is_reply": bool(node.get("edge_threaded_comments")),
                                "is_verified": owner.get("is_verified", False),
                                "profile_pic_url": owner.get("profile_pic_url"),
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
        username = user.get("username", "")
        out.append({
            "username": username,
            "profile_url": f"https://www.instagram.com/{username}/" if username else None,
            "text": c.get("text", ""),
            "likes": c.get("comment_like_count", 0),
            "timestamp": _format_timestamp(c.get("created_at")),
            "is_reply": bool(c.get("parent_comment_id")),
            "is_verified": user.get("is_verified", False),
            "profile_pic_url": user.get("profile_pic_url"),
        })


async def _extract_comments_from_dom(page) -> list:
    """Extract comments from Instagram DOM (2026 format).
    
    Instagram renders comments in div containers with 'Reply' text nodes.
    Each comment container has: username, timestamp, comment text, like count.
    """
    try:
        return await page.evaluate("""() => {
            const comments = [];
            const seen = new Set();
            
            // Find all 'Reply' text nodes — each marks a comment
            const walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_TEXT, null
            );
            const replyParents = [];
            while (walker.nextNode()) {
                if (walker.currentNode.textContent.trim() === 'Reply') {
                    // Walk up 3-6 levels to find the comment container div
                    let el = walker.currentNode.parentElement;
                    for (let i = 0; i < 5; i++) {
                        if (!el) break;
                        el = el.parentElement;
                    }
                    if (el) replyParents.push(el);
                }
            }
            
            for (const container of replyParents) {
                const text = container.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                if (lines.length < 3) continue;
                
                // Parse structure: username, timestamp, comment text, [likes], Reply
                let username = '';
                let commentText = '';
                let likes = 0;
                let timestamp = '';
                let isReply = false;
                
                // First non-empty line is usually the username
                username = lines[0].replace(/Verified$/, '').trim();
                
                // Skip if username looks wrong
                if (!username || username.length > 40 || username.includes(' ')) continue;
                
                // Second line is usually timestamp (e.g., "39w", "5d", "3h")
                const timePattern = /^\\d+[wdhms]$/;
                let textStartIdx = 1;
                if (lines.length > 1 && timePattern.test(lines[1])) {
                    timestamp = lines[1];
                    textStartIdx = 2;
                }
                
                // Collect text until we hit 'Reply', 'Like', or a like count
                const textParts = [];
                for (let i = textStartIdx; i < lines.length; i++) {
                    const line = lines[i];
                    if (line === 'Reply' || line === 'Like') break;
                    if (/^\\d[\\d,]* likes?$/i.test(line)) {
                        likes = parseInt(line.replace(/[^0-9]/g, '')) || 0;
                        break;
                    }
                    if (/^View all \\d+ replies?$/i.test(line)) {
                        isReply = false;
                        break;
                    }
                    textParts.push(line);
                }
                
                commentText = textParts.join(' ').trim();
                
                // Skip empty, too short, or duplicate
                if (!commentText || commentText.length < 2) continue;
                const key = username + ':' + commentText.substring(0, 40);
                if (seen.has(key)) continue;
                seen.add(key);
                
                comments.push({
                    username: username,
                    profile_url: username ? `https://www.instagram.com/${username}/` : null,
                    text: commentText,
                    likes: likes,
                    timestamp: timestamp || null,
                    is_reply: isReply,
                    is_verified: false,  // Can't easily detect from DOM
                    profile_pic_url: null  // Not available in DOM
                });
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


def _analyze_comments(comments: List[Dict], post_caption: str = "") -> Dict:
    """Analyze raw comments into audience intelligence — no raw text stored.
    
    Extracts: sentiment, themes, questions, pain points, product mentions,
    engagement patterns. Raw comment text is discarded after analysis.
    """
    if not comments:
        return {"analyzed": 0, "sentiment": "neutral", "themes": [], "questions": [], "pain_points": []}
    
    import re
    from collections import Counter
    
    total = len(comments)
    total_likes = sum(c.get("likes", 0) for c in comments)
    
    # Sentiment: simple keyword-based (fast, no API needed)
    positive_words = {"love", "amazing", "great", "awesome", "perfect", "best", "beautiful", 
                      "incredible", "excellent", "fantastic", "fire", "insane", "goat", "🔥", "❤️", "💯", "🙌"}
    negative_words = {"hate", "terrible", "worst", "awful", "bad", "disappointed", "scam",
                      "waste", "boring", "fake", "cringe", "mid", "👎"}
    question_words = {"how", "what", "where", "when", "why", "which", "can", "do", "does", "is", "are"}
    
    pos_count = 0
    neg_count = 0
    questions = []
    pain_points = []
    product_mentions = []
    themes = Counter()
    top_commenters = Counter()
    reply_rate = sum(1 for c in comments if c.get("is_reply")) / max(total, 1)
    
    for c in comments:
        text = (c.get("text") or "").lower()
        username = c.get("username", "")
        likes = c.get("likes", 0)
        
        # Sentiment
        words = set(re.findall(r'\w+', text)) | set(re.findall(r'[🔥❤️💯🙌👎😂💀🤔💡👀✅]', text))
        if words & positive_words:
            pos_count += 1
        if words & negative_words:
            neg_count += 1
        
        # Questions (audience wants to know)
        first_word = text.split()[0] if text.split() else ""
        if "?" in text or first_word in question_words:
            # Extract the question (first sentence with ?)
            q_match = re.search(r'([^.!]*\?)', text)
            if q_match and len(q_match.group(1)) > 10:
                questions.append({"question": q_match.group(1).strip()[:150], "likes": likes})
        
        # Pain points ("I struggle with", "I wish", "I need", "how do I")
        pain_patterns = [
            r"i (?:struggle|can't|cant|don't know|wish|need help|have trouble)\b.{5,80}",
            r"how do (?:i|you|we)\b.{5,80}",
            r"(?:frustrat|confus|stuck|lost|overwhelm)\w*.{5,60}",
        ]
        for pattern in pain_patterns:
            match = re.search(pattern, text)
            if match:
                pain_points.append({"pain": match.group(0).strip()[:150], "likes": likes})
                break
        
        # Product/tool mentions — look for capitalized names or @mentions
        # Only match words that look like proper nouns (capitalized) after trigger verbs
        original_text = (c.get("text") or "")
        product_trigger = re.search(
            r"(?:use|using|try|tried|recommend|check out|switched to|built with|powered by|running|works with)\s+"
            r"([A-Z][\w]*(?:\s+[A-Z][\w]*){0,3})",
            original_text,
        )
        if product_trigger:
            product_name = product_trigger.group(1).strip()
            if len(product_name) > 2 and product_name.lower() not in {"the", "this", "that", "it", "they", "you", "my"}:
                product_mentions.append(product_name[:50])
        # Also catch @mentions as products/tools
        at_mentions = re.findall(r"@(\w{2,30})", text)
        for mention in at_mentions:
            if mention not in top_commenters and len(mention) > 2:
                product_mentions.append(mention)

        # Theme extraction — extract meaningful 2-4 word phrases, not single words
        # Use noun-phrase-like patterns from the comment text
        theme_stop = {"the", "and", "for", "this", "that", "you", "your", "with", "from", "have", "are",
                      "but", "not", "was", "were", "been", "being", "its", "just", "really", "very",
                      "would", "could", "should", "will", "can", "more", "about", "like", "what",
                      "how", "all", "they", "them", "their", "there", "here", "also", "than", "then",
                      "too", "out", "get", "got", "has", "had", "did", "does", "don", "one", "who",
                      "want", "know", "think", "make", "need", "some", "look", "going", "thing"}
        # Extract 2-3 word phrases (bigrams/trigrams) as topic candidates
        clean_words = re.findall(r'\b[a-z]{3,}\b', text)
        clean_words = [w for w in clean_words if w not in theme_stop]
        for i in range(len(clean_words) - 1):
            bigram = f"{clean_words[i]} {clean_words[i+1]}"
            themes[bigram] += 1
            if i + 2 < len(clean_words):
                trigram = f"{clean_words[i]} {clean_words[i+1]} {clean_words[i+2]}"
                themes[trigram] += 1
        
        if username:
            top_commenters[username] += 1
    
    # Determine overall sentiment
    if pos_count > neg_count * 2:
        sentiment = "very_positive"
    elif pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count * 2:
        sentiment = "very_negative"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Sort questions and pain points by likes (most-liked = most resonant)
    questions.sort(key=lambda x: x.get("likes", 0), reverse=True)
    pain_points.sort(key=lambda x: x.get("likes", 0), reverse=True)
    
    # Deduplicate product mentions
    product_counter = Counter(product_mentions)
    
    return {
        "analyzed": total,
        "sentiment": sentiment,
        "sentiment_breakdown": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": total - pos_count - neg_count,
        },
        "avg_comment_likes": round(total_likes / max(total, 1), 1),
        "reply_rate": round(reply_rate * 100, 1),
        "questions": questions[:10],  # Top 10 questions by likes
        "pain_points": pain_points[:10],
        "product_mentions": [{"product": p, "count": c} for p, c in product_counter.most_common(10)],
        "themes": [{"theme": t, "count": c} for t, c in themes.most_common(15)],
        "top_commenters": [{"username": u, "count": c} for u, c in top_commenters.most_common(10)],
        "engagement_quality": "high" if total_likes / max(total, 1) > 5 else "moderate" if total_likes / max(total, 1) > 1 else "low",
    }


async def scrape_competitor_comments(
    db: AsyncSession,
    competitor_id: int,
    top_n: int = 10,
    comments_per_post: int = 50,
) -> Dict:
    """Scrape comments for top N posts, analyze them, store ONLY the analysis.
    
    Raw comment text is never persisted — only audience intelligence and sentiment.
    Returns: {processed: int, analyzed: int, errors: [str]}
    """
    result = await db.execute(
        text("""
            SELECT id, shortcode, post_text
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
        return {"processed": 0, "analyzed": 0, "errors": []}
    
    stats = {"processed": 0, "analyzed": 0, "errors": []}
    
    for post_id, shortcode, post_caption in posts:
        stats["processed"] += 1
        logger.info("Scraping + analyzing comments for %s...", shortcode)
        
        try:
            # Scrape raw comments (held in memory only)
            raw_comments = await scrape_post_comments(shortcode, limit=comments_per_post)
            
            # Analyze using ML pipeline (FastEmbed + clustering), fallback to regex
            try:
                from app.services.comment_analyzer import analyze_comments_ml
                analysis = await analyze_comments_ml(raw_comments, post_caption or "")
            except Exception as e:
                logger.warning("ML analysis failed, falling back to regex: %s", e)
                analysis = _analyze_comments(raw_comments, post_caption or "")
            
            # Store ONLY the analysis, not raw comments
            await db.execute(
                text("UPDATE crm.competitor_posts SET comments_data = :c WHERE id = :id"),
                {"c": json.dumps(analysis), "id": post_id},
            )
            await db.commit()
            stats["analyzed"] += 1
            logger.info("✅ %s: analyzed %d comments → %s sentiment, %d questions, %d pain points",
                        shortcode, analysis["analyzed"], analysis["sentiment"],
                        len(analysis["questions"]), len(analysis["pain_points"]))
            
        except Exception as e:
            stats["errors"].append(f"{shortcode}: {str(e)[:100]}")
            logger.error("Comment analysis failed for %s: %s", shortcode, e)
        
        # Random delay between posts to avoid rate limiting
        import random
        await asyncio.sleep(random.uniform(2, 5))
    
    return stats


async def analyze_competitor_comments_batch(
    db: AsyncSession,
    competitor_ids: List[int],
    top_n_per_competitor: int = 5,
) -> Dict:
    """Batch comment analysis across multiple competitors.
    
    Returns: {analyzed: int, processed: int}
    """
    totals = {"analyzed": 0, "processed": 0}
    
    for cid in competitor_ids:
        try:
            result = await scrape_competitor_comments(db, cid, top_n=top_n_per_competitor)
            totals["analyzed"] += result.get("analyzed", 0)
            totals["processed"] += result.get("processed", 0)
        except Exception as e:
            logger.warning("Comment analysis batch failed for competitor %s: %s", cid, e)
    
    return totals
