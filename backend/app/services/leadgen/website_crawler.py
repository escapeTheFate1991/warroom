"""Website crawler for contact enrichment — emails, socials, owner names."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)
PHONE_PATTERN = re.compile(
    r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
)
SOCIAL_PATTERNS = {
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._\-]+/?"),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._\-]+/?"),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9._\-]+/?"),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9._\-]+/?"),
    "tiktok": re.compile(r"https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9._\-]+/?"),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)[a-zA-Z0-9._\-]+/?"),
    "yelp": re.compile(r"https?://(?:www\.)?yelp\.com/biz/[a-zA-Z0-9._\-]+/?"),
}
JUNK_EMAIL_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "googleapis.com",
    "w3.org", "schema.org", "gravatar.com", "wordpress.org",
}
PLATFORM_SIGNATURES = {
    "squarespace": ["squarespace.com", "static1.squarespace.com"],
    "wix": ["wixsite.com", "parastorage.com", "wix.com"],
    "wordpress": ["wp-content", "wp-includes", "wordpress"],
    "shopify": ["cdn.shopify.com", "myshopify.com"],
    "webflow": ["webflow.com", "assets-global.website-files.com"],
    "godaddy": ["godaddy.com", "secureserver.net"],
    "weebly": ["weebly.com"],
}
CONTACT_PAGE_PATTERNS = [
    "/contact", "/about", "/team", "/our-team", "/about-us",
    "/contact-us", "/meet-the-team", "/staff", "/people",
]


def _clean_phones(raw_phones: set[str]) -> list[str]:
    """Deduplicate and normalize phone numbers."""
    cleaned = set()
    for phone in raw_phones:
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            cleaned.add(f"({digits[:3]}) {digits[3:6]}-{digits[6:]}")
    return sorted(cleaned)


@dataclass
class CrawlResult:
    url: str
    status_code: int = 0
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    owner_name: str = ""
    facebook: str = ""
    instagram: str = ""
    linkedin: str = ""
    twitter: str = ""
    tiktok: str = ""
    youtube: str = ""
    yelp: str = ""
    platform: str = ""
    error: str = ""


def _clean_emails(raw_emails: set[str]) -> list[str]:
    """Remove junk emails (tracking pixels, CMS internals, etc.)."""
    cleaned = []
    for email in raw_emails:
        domain = email.split("@")[1].lower()
        if domain in JUNK_EMAIL_DOMAINS:
            continue
        if any(ext in domain for ext in [".png", ".jpg", ".gif", ".svg", ".js", ".css"]):
            continue
        cleaned.append(email.lower())
    return sorted(set(cleaned))


def _detect_platform(page_source: str) -> str:
    source_lower = page_source.lower()
    for platform, signatures in PLATFORM_SIGNATURES.items():
        if any(sig in source_lower for sig in signatures):
            return platform
    return "custom"


def _extract_socials(page_source: str) -> dict[str, str]:
    socials = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        match = pattern.search(page_source)
        if match:
            socials[platform] = match.group(0).rstrip("/")
    return socials


def _find_contact_pages(page_source: str, base_url: str) -> list[str]:
    """Find links to contact/about/team pages."""
    found = []
    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
    for match in href_pattern.finditer(page_source):
        href = match.group(1).lower()
        for pattern in CONTACT_PAGE_PATTERNS:
            if pattern in href:
                full_url = urljoin(base_url, match.group(1))
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    found.append(full_url)
                break
    return list(set(found))[:3]  # Limit to 3 pages


async def _scrape_page(url: str, session: httpx.AsyncClient) -> tuple[str, set[str], set[str], dict[str, str]]:
    """Visit a page and extract emails, phones, socials from content."""
    try:
        response = await session.get(url, timeout=15.0, follow_redirects=True)
        if response.status_code != 200:
            return "", set(), set(), {}
        
        content = response.text
        emails = set(EMAIL_PATTERN.findall(content))
        phones = set(PHONE_PATTERN.findall(content))
        socials = _extract_socials(content)
        return content, emails, phones, socials
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return "", set(), set(), {}


async def crawl_website(url: str) -> CrawlResult:
    """Crawl a business website for emails, socials, owner name, and platform."""
    result = CrawlResult(url=url)

    try:
        async with httpx.AsyncClient(timeout=20.0) as session:
            # Scrape homepage
            homepage_content, all_emails, all_phones, all_socials = await _scrape_page(url, session)
            if not homepage_content:
                result.error = "Failed to load homepage"
                return result

            result.status_code = 200
            result.platform = _detect_platform(homepage_content)

            # Find and scrape contact/about pages
            contact_pages = _find_contact_pages(homepage_content, url)
            for contact_url in contact_pages:
                await asyncio.sleep(1)  # Be polite
                _, page_emails, page_phones, page_socials = await _scrape_page(contact_url, session)
                all_emails.update(page_emails)
                all_phones.update(page_phones)
                for platform, link in page_socials.items():
                    if platform not in all_socials:
                        all_socials[platform] = link

            result.emails = _clean_emails(all_emails)
            result.phones = _clean_phones(all_phones)
            result.facebook = all_socials.get("facebook", "")
            result.instagram = all_socials.get("instagram", "")
            result.linkedin = all_socials.get("linkedin", "")
            result.twitter = all_socials.get("twitter", "")
            result.tiktok = all_socials.get("tiktok", "")
            result.youtube = all_socials.get("youtube", "")
            result.yelp = all_socials.get("yelp", "")

    except Exception as exc:
        result.error = str(exc)
        logger.error("Crawl failed for %s: %s", url, exc)

    return result