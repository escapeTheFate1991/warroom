"""News & web mention scanner — uses Brave Search API for recent coverage."""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


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


async def _get_brave_api_key() -> str:
    """Get Brave Search API key from settings DB, falling back to env."""
    try:
        from app.db.leadgen_db import leadgen_session
        from sqlalchemy import text
        async with leadgen_session() as db:
            r = await db.execute(
                text("SELECT value FROM public.settings WHERE key = 'brave_api_key'")
            )
            row = r.fetchone()
            if row and row[0]:
                return row[0]
    except Exception:
        pass
    return os.environ.get("BRAVE_API_KEY", "")


async def search_news(
    business_name: str,
    city: str = "",
    state: str = "",
    owner_name: str = "",
    max_results: int = 5,
) -> NewsResult:
    """Search for recent news/mentions about a business and optionally its owner."""
    result = NewsResult()

    api_key = await _get_brave_api_key()
    if not api_key:
        result.error = "No Brave Search API key configured"
        return result

    queries = []
    # Business name + location
    location = f"{city} {state}".strip()
    queries.append(f'"{business_name}" {location}')
    # Owner name if available
    if owner_name:
        queries.append(f'"{owner_name}" {business_name}')

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            seen_urls = set()

            for query in queries:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={
                        "q": query,
                        "count": max_results,
                        "freshness": "py",  # Past year
                    },
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": api_key,
                    },
                )

                if resp.status_code != 200:
                    logger.warning("Brave Search returned %d for '%s'", resp.status_code, query)
                    continue

                data = resp.json()
                web_results = data.get("web", {}).get("results", [])

                for item in web_results:
                    url = item.get("url", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Skip the business's own website
                    if _is_own_website(url, business_name):
                        continue

                    # Skip social media profiles (we get those separately)
                    if any(d in url for d in [
                        "facebook.com", "instagram.com", "twitter.com", "x.com",
                        "linkedin.com", "tiktok.com", "youtube.com", "yelp.com",
                        "bbb.org", "glassdoor.com",
                    ]):
                        continue

                    result.mentions.append(NewsMention(
                        title=item.get("title", ""),
                        url=url,
                        source=item.get("meta_url", {}).get("hostname", _extract_domain(url)),
                        snippet=item.get("description", "")[:300],
                        date=item.get("page_age", ""),
                    ))

                if len(result.mentions) >= max_results:
                    break

    except httpx.HTTPError as exc:
        result.error = f"HTTP error: {exc}"
        logger.warning("News search failed for '%s': %s", business_name, exc)
    except Exception as exc:
        result.error = f"Error: {exc}"
        logger.warning("News search error for '%s': %s", business_name, exc)

    return result


async def search_reddit(
    business_name: str,
    city: str = "",
    state: str = "",
    max_results: int = 5,
) -> list[dict]:
    """Search Reddit for mentions of a business via Brave Search."""
    api_key = await _get_brave_api_key()
    if not api_key:
        return []

    location = f"{city} {state}".strip()
    query = f'site:reddit.com "{business_name}" {location}'

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
            )

            if resp.status_code != 200:
                return []

            data = resp.json()
            results = []

            for item in data.get("web", {}).get("results", []):
                url = item.get("url", "")
                if "reddit.com" not in url:
                    continue

                # Extract subreddit
                sub_match = re.search(r'reddit\.com/r/([^/]+)', url)
                subreddit = sub_match.group(1) if sub_match else ""

                results.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "subreddit": subreddit,
                    "snippet": item.get("description", "")[:300],
                    "date": item.get("page_age", ""),
                })

            return results

    except Exception as exc:
        logger.warning("Reddit search failed for '%s': %s", business_name, exc)
        return []


async def search_glassdoor(
    business_name: str,
    city: str = "",
    state: str = "",
) -> dict:
    """Search for Glassdoor listing via Brave Search (direct scraping blocked)."""
    api_key = await _get_brave_api_key()
    if not api_key:
        return {}

    query = f'site:glassdoor.com "{business_name}" reviews'

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 3},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
            )

            if resp.status_code != 200:
                return {}

            data = resp.json()
            for item in data.get("web", {}).get("results", []):
                url = item.get("url", "")
                if "glassdoor.com" not in url:
                    continue

                # Try to extract rating from snippet
                snippet = item.get("description", "")
                rating_match = re.search(r'(\d\.\d)\s*/?\s*5', snippet)
                review_match = re.search(r'(\d[\d,]*)\s*reviews?', snippet, re.IGNORECASE)

                return {
                    "url": url,
                    "rating": float(rating_match.group(1)) if rating_match else None,
                    "review_count": int(review_match.group(1).replace(",", "")) if review_match else 0,
                    "summary": snippet[:200],
                }

    except Exception as exc:
        logger.warning("Glassdoor search failed for '%s': %s", business_name, exc)

    return {}


def _is_own_website(url: str, business_name: str) -> bool:
    """Check if a URL is likely the business's own website."""
    slug = re.sub(r'[^a-z0-9]+', '', business_name.lower())
    domain = _extract_domain(url).lower().replace(".", "").replace("-", "")
    return slug[:10] in domain


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    match = re.search(r'://(?:www\.)?([^/]+)', url)
    return match.group(1) if match else url
