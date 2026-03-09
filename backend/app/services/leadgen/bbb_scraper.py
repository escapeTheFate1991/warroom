"""BBB (Better Business Bureau) scraper — rating, accreditation, complaints.

BBB.org is a client-rendered SPA, so we use two strategies:
1. Try the BBB JSON search API (works intermittently)
2. Fall back to web search to find the BBB profile page and extract meta info
"""

import logging
import re
from dataclasses import dataclass
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
}


@dataclass
class BBBResult:
    url: str = ""
    rating: str = ""  # A+ to F
    accredited: bool = False
    complaints: int = 0
    summary: str = ""
    error: str = ""


async def scrape_bbb(business_name: str, city: str, state: str) -> BBBResult:
    """Search for BBB profile and extract rating/accreditation info.

    Strategy:
      1. Try BBB's internal JSON search API
      2. Fall back to fetching a BBB profile page directly if URL is known
    """
    result = BBBResult()

    try:
        async with httpx.AsyncClient(
            timeout=20.0, follow_redirects=True, headers=BROWSER_HEADERS
        ) as client:
            # Strategy 1: BBB API search
            api_result = await _search_bbb_api(client, business_name, city, state)
            if api_result:
                return api_result

            # Strategy 2: Try constructing the BBB URL directly
            direct_result = await _try_direct_bbb(client, business_name, city, state)
            if direct_result:
                return direct_result

            result.error = "No BBB profile found"

    except httpx.HTTPError as exc:
        result.error = f"HTTP error: {exc}"
        logger.warning("BBB scrape failed for '%s': %s", business_name, exc)
    except Exception as exc:
        result.error = f"Error: {exc}"
        logger.warning("BBB scrape error for '%s': %s", business_name, exc)

    return result


async def _search_bbb_api(
    client: httpx.AsyncClient,
    business_name: str,
    city: str,
    state: str,
) -> BBBResult | None:
    """Try BBB's internal search API."""
    try:
        location = f"{city}, {state}" if state else city
        resp = await client.get(
            "https://www.bbb.org/api/search",
            params={
                "find_text": business_name,
                "find_loc": location,
                "find_country": "US",
                "find_type": "Category",
                "page": "1",
                "count": "5",
            },
            headers={**BROWSER_HEADERS, "Accept": "application/json"},
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        # Find best match
        name_lower = business_name.lower()
        best = results[0]
        for item in results:
            if name_lower in (item.get("businessName", "")).lower():
                best = item
                break

        bbb = BBBResult()
        bbb.url = best.get("reportUrl", "")
        if bbb.url and not bbb.url.startswith("http"):
            bbb.url = f"https://www.bbb.org{bbb.url}"
        bbb.rating = best.get("rating", "")
        bbb.accredited = best.get("isAccredited", False)
        bbb.complaints = best.get("numberOfComplaints", 0)

        parts = []
        if bbb.rating:
            parts.append(f"BBB Rating: {bbb.rating}")
        if bbb.accredited:
            parts.append("BBB Accredited")
        if bbb.complaints > 0:
            parts.append(f"{bbb.complaints} complaints")
        bbb.summary = " · ".join(parts) if parts else "Listed on BBB"

        return bbb

    except Exception as exc:
        logger.debug("BBB API search failed: %s", exc)
        return None


async def _try_direct_bbb(
    client: httpx.AsyncClient,
    business_name: str,
    city: str,
    state: str,
) -> BBBResult | None:
    """Try to fetch a BBB profile page by constructing the URL slug."""
    try:
        # BBB URLs look like: /us/ga/newnan/profile/roofing-contractors/eagle-watch-roofing-inc-0443-90021873
        state_lower = state.lower() if state else ""
        city_lower = city.lower().replace(" ", "-") if city else ""
        name_slug = re.sub(r'[^a-z0-9]+', '-', business_name.lower()).strip('-')

        # Try searching Google-style for the BBB page
        search_url = f"https://www.bbb.org/us/{state_lower}/{city_lower}"
        resp = await client.get(search_url)

        if resp.status_code == 200:
            html = resp.text
            # Look for profile links matching the business name
            profile_links = re.findall(
                r'href="(https://www\.bbb\.org/us/[^"]+/profile/[^"]+)"', html
            )

            for link in profile_links:
                if name_slug[:10] in link.lower():
                    # Found a match — fetch the profile
                    return await _parse_bbb_profile(client, link)

        return None

    except Exception as exc:
        logger.debug("Direct BBB lookup failed: %s", exc)
        return None


async def _parse_bbb_profile(
    client: httpx.AsyncClient, url: str
) -> BBBResult | None:
    """Fetch and parse a BBB profile page."""
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None

        html = resp.text
        bbb = BBBResult(url=url)

        # Extract rating
        rating_match = re.search(
            r'(?:BBB Rating|bbb-rating)[^>]*>?\s*([A-F][+-]?)\b', html, re.IGNORECASE
        )
        if not rating_match:
            rating_match = re.search(r'"ratingValue"\s*:\s*"([A-F][+-]?)"', html)
        if rating_match:
            bbb.rating = rating_match.group(1)

        # Accreditation
        bbb.accredited = bool(re.search(
            r'BBB Accredited|accredited business|is-accredited', html, re.IGNORECASE
        ))

        # Complaints
        complaint_match = re.search(
            r'(\d+)\s*(?:complaints?|complaint[s]? closed)', html, re.IGNORECASE
        )
        if complaint_match:
            bbb.complaints = int(complaint_match.group(1))

        parts = []
        if bbb.rating:
            parts.append(f"BBB Rating: {bbb.rating}")
        if bbb.accredited:
            parts.append("BBB Accredited")
        if bbb.complaints > 0:
            parts.append(f"{bbb.complaints} complaints")
        bbb.summary = " · ".join(parts) if parts else "Listed on BBB"

        return bbb

    except Exception as exc:
        logger.debug("BBB profile parse failed: %s", exc)
        return None
