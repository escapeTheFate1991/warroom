"""Social media presence scanner — verify profiles exist and grab basic info."""

import logging
import re
from dataclasses import dataclass

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


async def scan_social_profiles(
    facebook_url: str = "",
    instagram_url: str = "",
    linkedin_url: str = "",
    twitter_url: str = "",
    tiktok_url: str = "",
    youtube_url: str = "",
) -> dict:
    """Check each social URL for existence and extract basic meta info.

    Returns dict: {platform: {url, exists, title, description, followers}}
    """
    profiles = {}
    urls = {
        "facebook": facebook_url,
        "instagram": instagram_url,
        "linkedin": linkedin_url,
        "twitter": twitter_url,
        "tiktok": tiktok_url,
        "youtube": youtube_url,
    }

    async with httpx.AsyncClient(
        timeout=12.0, follow_redirects=True, headers=BROWSER_HEADERS
    ) as client:
        for platform, url in urls.items():
            if not url:
                continue

            try:
                resp = await client.get(url)
                exists = resp.status_code == 200

                title = ""
                description = ""
                followers = None

                if exists:
                    html = resp.text[:50000]  # Limit parse size

                    # Extract title
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()[:100]

                    # Extract meta description
                    desc_match = re.search(
                        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)',
                        html, re.IGNORECASE,
                    )
                    if desc_match:
                        description = desc_match.group(1).strip()[:200]

                    # Platform-specific follower extraction
                    followers = _extract_followers(platform, html)

                profiles[platform] = {
                    "url": url,
                    "exists": exists,
                    "title": title,
                    "description": description,
                    "followers": followers,
                }

            except Exception as exc:
                logger.debug("Social scan failed for %s (%s): %s", platform, url, exc)
                profiles[platform] = {
                    "url": url,
                    "exists": None,  # Unknown
                    "title": "",
                    "description": "",
                    "followers": None,
                    "error": str(exc)[:100],
                }

    return profiles


def _extract_followers(platform: str, html: str) -> int | None:
    """Try to extract follower count from page HTML."""
    try:
        if platform == "instagram":
            # Instagram meta tag: "X Followers"
            match = re.search(r'([\d,.]+[KMkm]?)\s*Followers', html, re.IGNORECASE)
            if match:
                return _parse_count(match.group(1))

        elif platform == "facebook":
            # "X people like this" or "X followers"
            match = re.search(r'([\d,.]+[KMkm]?)\s*(?:people like|followers)', html, re.IGNORECASE)
            if match:
                return _parse_count(match.group(1))

        elif platform == "twitter":
            # Twitter/X: "X Followers"
            match = re.search(r'([\d,.]+[KMkm]?)\s*Followers', html, re.IGNORECASE)
            if match:
                return _parse_count(match.group(1))

        elif platform == "youtube":
            # "X subscribers"
            match = re.search(r'([\d,.]+[KMkm]?)\s*subscribers', html, re.IGNORECASE)
            if match:
                return _parse_count(match.group(1))

        elif platform == "tiktok":
            match = re.search(r'([\d,.]+[KMkm]?)\s*Followers', html, re.IGNORECASE)
            if match:
                return _parse_count(match.group(1))

    except Exception:
        pass
    return None


def _parse_count(s: str) -> int | None:
    """Parse '1.2K', '15,000', '3.4M' etc. into int."""
    s = s.strip().replace(",", "")
    multiplier = 1
    if s.upper().endswith("K"):
        multiplier = 1000
        s = s[:-1]
    elif s.upper().endswith("M"):
        multiplier = 1_000_000
        s = s[:-1]
    try:
        return int(float(s) * multiplier)
    except ValueError:
        return None
