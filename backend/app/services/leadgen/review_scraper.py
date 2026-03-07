"""Review scraping — Yelp frontend + Google Places reviews."""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}


@dataclass
class ReviewItem:
    text: str
    rating: float
    date: str = ""
    author: str = ""


@dataclass
class YelpScrapeResult:
    yelp_url: str = ""
    yelp_rating: float = 0.0
    yelp_reviews_count: int = 0
    reviews: list[ReviewItem] = field(default_factory=list)
    error: str = ""


@dataclass
class GoogleReviewResult:
    reviews: list[ReviewItem] = field(default_factory=list)
    error: str = ""


async def scrape_yelp_reviews(
    business_name: str, city: str, state: str
) -> YelpScrapeResult:
    """Search Yelp for a business and scrape its reviews.

    Gracefully returns empty results on 403, captcha, or any error.
    """
    result = YelpScrapeResult()

    try:
        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True, headers=BROWSER_HEADERS
        ) as client:
            # Step 1: Search Yelp for the business
            search_url = "https://www.yelp.com/search"
            location = f"{city}, {state}" if state else city
            params = {"find_desc": business_name, "find_loc": location}

            search_resp = await client.get(search_url, params=params)
            if search_resp.status_code != 200:
                result.error = f"Yelp search returned {search_resp.status_code}"
                logger.warning(result.error)
                return result

            html = search_resp.text

            # Find the business page URL from search results
            biz_url = _extract_business_url(html, business_name)
            if not biz_url:
                result.error = "Could not find business on Yelp"
                logger.debug("No Yelp match for '%s' in %s", business_name, location)
                return result

            result.yelp_url = biz_url

            # Delay between requests
            await asyncio.sleep(1.5)

            # Step 2: Fetch the business page
            biz_resp = await client.get(biz_url)
            if biz_resp.status_code != 200:
                result.error = f"Yelp biz page returned {biz_resp.status_code}"
                logger.warning(result.error)
                return result

            biz_html = biz_resp.text

            # Extract rating and review count from JSON-LD or HTML
            _parse_yelp_business_page(biz_html, result)

    except httpx.HTTPError as exc:
        result.error = f"HTTP error: {exc}"
        logger.warning("Yelp scrape HTTP error for '%s': %s", business_name, exc)
    except Exception as exc:
        result.error = f"Unexpected error: {exc}"
        logger.error("Yelp scrape failed for '%s': %s", business_name, exc)

    return result


def _extract_business_url(html: str, business_name: str) -> str:
    """Find the most relevant business URL from Yelp search results."""
    # Look for /biz/ links in the search results
    biz_links = re.findall(r'href="(/biz/[^"?]+)', html)
    if not biz_links:
        return ""

    # Deduplicate preserving order
    seen = set()
    unique_links = []
    for link in biz_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    # Try to find a link matching the business name
    name_slug = re.sub(r'[^a-z0-9]+', '-', business_name.lower()).strip('-')
    for link in unique_links:
        if name_slug[:15] in link.lower():
            return f"https://www.yelp.com{link}"

    # Fall back to first result
    if unique_links:
        return f"https://www.yelp.com{unique_links[0]}"

    return ""


def _parse_yelp_business_page(html: str, result: YelpScrapeResult) -> None:
    """Parse rating, review count, and reviews from a Yelp business page."""
    # Try JSON-LD first
    ld_matches = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    for ld_raw in ld_matches:
        try:
            ld_data = json.loads(ld_raw)
            if isinstance(ld_data, dict) and ld_data.get("@type") == "LocalBusiness":
                agg = ld_data.get("aggregateRating", {})
                if agg:
                    result.yelp_rating = float(agg.get("ratingValue", 0))
                    result.yelp_reviews_count = int(agg.get("reviewCount", 0))

                # Extract individual reviews from JSON-LD
                for rev in ld_data.get("review", [])[:20]:
                    text = rev.get("description", "") or rev.get("reviewBody", "")
                    rating_obj = rev.get("reviewRating", {})
                    rating = float(rating_obj.get("ratingValue", 0)) if rating_obj else 0.0
                    date = rev.get("datePublished", "")
                    author = rev.get("author", {}).get("name", "") if isinstance(rev.get("author"), dict) else ""
                    if text:
                        result.reviews.append(ReviewItem(
                            text=text[:1000],
                            rating=rating,
                            date=date,
                            author=author,
                        ))
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    # If no reviews from JSON-LD, try parsing from HTML comment JSON blobs
    if not result.reviews:
        _parse_reviews_from_html(html, result)

    # Fallback: extract rating from HTML if JSON-LD didn't have it
    if result.yelp_rating == 0:
        rating_match = re.search(r'aria-label="(\d(?:\.\d)?) star rating"', html)
        if rating_match:
            result.yelp_rating = float(rating_match.group(1))

    if result.yelp_reviews_count == 0:
        count_match = re.search(r'(\d+)\s+reviews?', html, re.IGNORECASE)
        if count_match:
            result.yelp_reviews_count = int(count_match.group(1))


def _parse_reviews_from_html(html: str, result: YelpScrapeResult) -> None:
    """Try to extract reviews from Yelp HTML comment JSON blobs or visible text."""
    # Yelp sometimes embeds data in HTML comments: <!--{...}-->
    comment_blobs = re.findall(r'<!--(\{.+?\})-->', html, re.DOTALL)
    for blob in comment_blobs:
        try:
            data = json.loads(blob)
            # Walk the blob looking for review-like structures
            reviews = _find_reviews_in_json(data)
            for rev in reviews[:20]:
                if rev.text and rev.text not in [r.text for r in result.reviews]:
                    result.reviews.append(rev)
        except (json.JSONDecodeError, ValueError):
            continue

    # Try regex-based extraction for review text blocks
    if not result.reviews:
        # Match review paragraphs near star rating indicators
        review_blocks = re.findall(
            r'aria-label="(\d) star rating"[^>]*>.*?<p[^>]*>(.*?)</p>',
            html, re.DOTALL
        )
        for rating_str, text in review_blocks[:20]:
            clean = re.sub(r'<[^>]+>', '', text).strip()
            if clean and len(clean) > 20:
                result.reviews.append(ReviewItem(
                    text=clean[:1000],
                    rating=float(rating_str),
                ))


def _find_reviews_in_json(data, depth: int = 0) -> list[ReviewItem]:
    """Recursively search a JSON blob for review-like objects."""
    if depth > 8:
        return []
    reviews = []

    if isinstance(data, dict):
        # Check if this looks like a review
        text = data.get("text", {})
        if isinstance(text, dict):
            text = text.get("full", "") or text.get("raw", "")
        elif not isinstance(text, str):
            text = ""
        comment = data.get("comment", {})
        if isinstance(comment, dict):
            comment_text = comment.get("text", "")
        elif isinstance(comment, str):
            comment_text = comment
        else:
            comment_text = ""

        review_text = text or comment_text or data.get("reviewText", "") or data.get("body", "")
        rating = data.get("rating", 0)

        if review_text and isinstance(review_text, str) and len(review_text) > 20:
            reviews.append(ReviewItem(
                text=review_text[:1000],
                rating=float(rating) if rating else 0.0,
                date=str(data.get("date", "") or data.get("localizedDate", "")),
                author=str(data.get("userName", "") or data.get("authorName", "")),
            ))

        # Recurse into values
        for val in data.values():
            reviews.extend(_find_reviews_in_json(val, depth + 1))

    elif isinstance(data, list):
        for item in data:
            reviews.extend(_find_reviews_in_json(item, depth + 1))

    return reviews


async def fetch_google_reviews(place_id: str) -> GoogleReviewResult:
    """Fetch reviews from Google Places Details API.

    Uses the same API key retrieval as google_places.py.
    Falls back gracefully if key missing or quota exceeded.
    """
    result = GoogleReviewResult()

    try:
        from app.services.leadgen.google_places import _get_google_maps_key

        api_key = await _get_google_maps_key()
        if not api_key:
            result.error = "No Google Maps API key available"
            logger.debug(result.error)
            return result

        # Check daily rate limit before calling Google API
        from app.services.leadgen.google_places import _check_places_rate_limit, _increment_places_count
        if not _check_places_rate_limit():
            result.error = "Google Places daily limit reached"
            logger.warning(result.error)
            return result

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "reviews",
            "key": api_key,
        }

        _increment_places_count()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)

        if resp.status_code != 200:
            result.error = f"Google Places API returned {resp.status_code}"
            logger.warning(result.error)
            return result

        data = resp.json()
        status = data.get("status", "")
        if status not in ("OK", "ZERO_RESULTS"):
            result.error = f"Google Places API status: {status}"
            logger.warning(result.error)
            return result

        place_result = data.get("result", {})
        for rev in place_result.get("reviews", []):
            result.reviews.append(ReviewItem(
                text=rev.get("text", "")[:1000],
                rating=float(rev.get("rating", 0)),
                author=rev.get("author_name", ""),
                date=str(rev.get("relative_time_description", "")),
            ))

    except ImportError:
        result.error = "google_places module not available"
        logger.warning(result.error)
    except httpx.HTTPError as exc:
        result.error = f"HTTP error: {exc}"
        logger.warning("Google reviews HTTP error: %s", exc)
    except Exception as exc:
        result.error = f"Unexpected error: {exc}"
        logger.error("Google reviews failed for '%s': %s", place_id, exc)

    return result
