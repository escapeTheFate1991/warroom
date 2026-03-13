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
    "/services", "/locations", "/our-work", "/testimonials",
    "/reviews", "/faq", "/footer", "/careers",
]

# Known junk phone numbers belonging to website builders / hosting / etc.
JUNK_PHONE_PREFIXES = {
    "8005551212",  # 411 directory
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


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
    return list(set(found))[:6]  # Limit to 6 subpages


def _find_nav_links(page_source: str, base_url: str) -> list[str]:
    """Extract internal links from navigation elements (nav, header, footer)."""
    try:
        soup = BeautifulSoup(page_source, "html.parser")
    except Exception:
        return []

    found = set()
    base_netloc = urlparse(base_url).netloc

    # Look in nav, header, and footer elements for internal links
    for container in soup.find_all(["nav", "header", "footer"]):
        for a_tag in container.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            # Only same-domain, no anchors-only, no external
            if parsed.netloc == base_netloc and parsed.path not in ("", "/"):
                # Skip files (images, PDFs, etc.)
                if not re.search(r"\.(jpg|jpeg|png|gif|svg|pdf|zip|mp4|mp3)$", parsed.path, re.IGNORECASE):
                    found.add(full_url.split("#")[0].split("?")[0])

    return list(found)[:8]


def _extract_tel_phones(page_source: str) -> set[str]:
    """Extract phone numbers from tel: href links — these are the most reliable."""
    tel_pattern = re.compile(r'href=["\']tel:([^"\']+)["\']', re.IGNORECASE)
    phones = set()
    for match in tel_pattern.finditer(page_source):
        raw = match.group(1).strip()
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 10:
            phones.add(raw)
    return phones


def _strip_script_style(page_source: str) -> str:
    """Remove <script> and <style> content to avoid extracting junk data."""
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", page_source, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)
    return cleaned


async def _scrape_page(url: str, session: httpx.AsyncClient) -> tuple[str, set[str], set[str], dict[str, str]]:
    """Visit a page and extract emails, phones, socials from content."""
    try:
        response = await session.get(url, timeout=15.0, follow_redirects=True, headers=HEADERS)
        if response.status_code != 200:
            return "", set(), set(), {}

        raw_content = response.text
        # Extract tel: links before stripping (most reliable phone source)
        tel_phones = _extract_tel_phones(raw_content)
        # Strip script/style to avoid junk emails/phones from JS bundles
        content = _strip_script_style(raw_content)
        emails = set(EMAIL_PATTERN.findall(content))
        phones = tel_phones | set(PHONE_PATTERN.findall(content))
        socials = _extract_socials(raw_content)  # Socials from full content (links)
        return raw_content, emails, phones, socials
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return "", set(), set(), {}


async def crawl_website(url: str) -> CrawlResult:
    """Crawl a business website for emails, socials, owner name, and platform."""
    result = CrawlResult(url=url)

    try:
        async with httpx.AsyncClient(timeout=25.0, headers=HEADERS) as session:
            # Scrape homepage
            homepage_content, all_emails, all_phones, all_socials = await _scrape_page(url, session)
            if not homepage_content:
                result.error = "Failed to load homepage"
                return result

            result.status_code = 200
            result.platform = _detect_platform(homepage_content)

            # Collect all subpages to crawl (deduplicated)
            visited = {url.rstrip("/")}
            subpages: list[str] = []

            # Priority 1: Contact/about pages (pattern-matched)
            contact_pages = _find_contact_pages(homepage_content, url)
            for p in contact_pages:
                normalized = p.rstrip("/")
                if normalized not in visited:
                    visited.add(normalized)
                    subpages.append(p)

            # Priority 2: Navigation links (nav, header, footer)
            nav_links = _find_nav_links(homepage_content, url)
            for p in nav_links:
                normalized = p.rstrip("/")
                if normalized not in visited:
                    visited.add(normalized)
                    subpages.append(p)

            # Limit total subpages to avoid hammering small sites
            subpages = subpages[:10]
            logger.info("Crawling %s: found %d subpages to scrape", url, len(subpages))

            for sub_url in subpages:
                await asyncio.sleep(0.8)  # Be polite
                _, page_emails, page_phones, page_socials = await _scrape_page(sub_url, session)
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