"""News & web mention scanner — uses free sources (Reddit JSON API, Google News RSS, DuckDuckGo).

No API keys required. All direct scraping.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


@dataclass
class NewsMention:
    title: str
    url: str
    source: str
    snippet: str
    date: str = ""


@dataclass
class NewsResult:
    mentions: list[NewsMention] = field(default_factory=list)
    error: str = ""


@dataclass
class GlassdoorResult:
    url: str = ""
    rating: Optional[float] = None
    review_count: int = 0
    summary: str = ""
    error: str = ""


# ── Reddit (free JSON API via old.reddit.com) ─────────────────────

async def search_reddit(business_name: str) -> list[NewsMention]:
    """Search Reddit for mentions using the free JSON API."""
    mentions = []
    query = quote_plus(f'"{business_name}"')

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # old.reddit.com/search.json is public, no auth needed
            resp = await client.get(
                f"https://old.reddit.com/search.json?q={query}&sort=relevance&limit=10",
                headers={**HEADERS, "Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                for child in children[:5]:
                    post = child.get("data", {})
                    title = post.get("title", "")
                    subreddit = post.get("subreddit", "")
                    permalink = post.get("permalink", "")
                    selftext = post.get("selftext", "")[:200]
                    created = post.get("created_utc", 0)

                    # Skip if business name not in title or text
                    combined = f"{title} {selftext}".lower()
                    if business_name.lower().split()[0] not in combined:
                        continue

                    from datetime import datetime
                    date_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d") if created else ""

                    mentions.append(NewsMention(
                        title=title,
                        url=f"https://reddit.com{permalink}",
                        source=f"r/{subreddit}",
                        snippet=selftext[:200] if selftext else title,
                        date=date_str,
                    ))
            elif resp.status_code == 429:
                logger.warning("Reddit rate limited")
            else:
                logger.debug("Reddit search returned %d", resp.status_code)
    except Exception as exc:
        logger.warning("Reddit search failed: %s", exc)

    return mentions


# ── Google News RSS (free, no API key) ────────────────────────────

async def search_news(business_name: str, website_url: str = "") -> NewsResult:
    """Search Google News RSS for recent coverage. Free, no auth."""
    result = NewsResult()
    query = quote_plus(f'"{business_name}"')

    # Parse business domain to filter out their own site
    own_domain = ""
    if website_url:
        try:
            from urllib.parse import urlparse
            own_domain = urlparse(website_url).hostname or ""
            own_domain = own_domain.replace("www.", "")
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # Google News RSS feed
            resp = await client.get(
                f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
                headers=HEADERS,
            )
            if resp.status_code == 200:
                text = resp.text
                # Parse RSS XML items
                items = re.findall(
                    r'<item>\s*<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>.*?'
                    r'<link>(.*?)</link>.*?'
                    r'(?:<source[^>]*>(.*?)</source>)?.*?'
                    r'(?:<pubDate>(.*?)</pubDate>)?.*?'
                    r'</item>',
                    text, re.DOTALL
                )

                for title, url, source, pub_date in items[:10]:
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    url = url.strip()
                    source = re.sub(r'<[^>]+>', '', source).strip() if source else ""

                    # Skip own website and social profiles
                    if own_domain and own_domain in url:
                        continue
                    if any(s in url for s in ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "yelp.com"]):
                        continue

                    # Parse date
                    date_str = ""
                    if pub_date:
                        try:
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(pub_date.strip())
                            date_str = dt.strftime("%Y-%m-%d")
                        except Exception:
                            date_str = pub_date.strip()[:10]

                    result.mentions.append(NewsMention(
                        title=title,
                        url=url,
                        source=source or "Google News",
                        snippet=title,  # RSS doesn't include description usually
                        date=date_str,
                    ))
            else:
                logger.debug("Google News RSS returned %d", resp.status_code)
    except Exception as exc:
        logger.warning("News search failed: %s", exc)
        result.error = str(exc)[:200]

    return result


# ── DuckDuckGo HTML scrape (fallback for general web mentions) ────

async def search_web_mentions(business_name: str, website_url: str = "") -> list[NewsMention]:
    """Search DuckDuckGo HTML for web mentions. No API key."""
    mentions = []
    query = quote_plus(f'"{business_name}" reviews OR news OR article')

    own_domain = ""
    if website_url:
        try:
            from urllib.parse import urlparse
            own_domain = urlparse(website_url).hostname or ""
            own_domain = own_domain.replace("www.", "")
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                f"https://html.duckduckgo.com/html/?q={query}",
                headers=HEADERS,
            )
            if resp.status_code == 200:
                # Parse result blocks
                results = re.findall(
                    r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
                    r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                    resp.text, re.DOTALL
                )
                for url, title, snippet in results[:5]:
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    url = url.strip()

                    # Decode DDG redirect URL
                    if "uddg=" in url:
                        from urllib.parse import unquote, parse_qs, urlparse as _up
                        parsed = _up(url)
                        qs = parse_qs(parsed.query)
                        url = unquote(qs.get("uddg", [url])[0])

                    if own_domain and own_domain in url:
                        continue
                    if any(s in url for s in ["facebook.com", "twitter.com", "instagram.com"]):
                        continue

                    mentions.append(NewsMention(
                        title=title,
                        url=url,
                        source="DuckDuckGo",
                        snippet=snippet[:200],
                    ))
    except Exception as exc:
        logger.warning("DDG search failed: %s", exc)

    return mentions


# ── Glassdoor (direct scrape attempt) ─────────────────────────────

async def search_glassdoor(business_name: str) -> GlassdoorResult:
    """Try to get Glassdoor info via direct scrape. Glassdoor blocks aggressively."""
    result = GlassdoorResult()
    query = quote_plus(business_name)

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # Try Glassdoor search page
            resp = await client.get(
                f"https://www.glassdoor.com/Search/results.htm?keyword={query}",
                headers=HEADERS,
            )
            if resp.status_code == 200:
                text = resp.text
                # Try to extract rating from search results
                rating_match = re.search(r'(\d\.\d)\s*(?:★|star)', text)
                reviews_match = re.search(r'([\d,]+)\s*(?:reviews?|Reviews?)', text)
                url_match = re.search(r'href="(/Overview/[^"]+)"', text)

                if rating_match:
                    result.rating = float(rating_match.group(1))
                if reviews_match:
                    result.review_count = int(reviews_match.group(1).replace(",", ""))
                if url_match:
                    result.url = f"https://www.glassdoor.com{url_match.group(1)}"
                    result.summary = f"Glassdoor profile found for {business_name}"
            elif resp.status_code == 403:
                result.error = "Glassdoor blocked request (anti-bot)"
            else:
                result.error = f"Glassdoor returned {resp.status_code}"
    except Exception as exc:
        result.error = f"Glassdoor scrape failed: {str(exc)[:100]}"
        logger.debug("Glassdoor scrape failed: %s", exc)

    return result
