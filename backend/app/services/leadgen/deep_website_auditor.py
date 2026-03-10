"""Deep AI-powered website auditor — comprehensive analysis with Claude Haiku.

Scores across 5 categories: Technical SEO, Content Quality, Local SEO,
On-Page SEO, and AI Search Readiness. Includes competitor gap analysis.
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-3-5-20241022"

# ── Patterns ──────────────────────────────────────────────────────────────

SCHEMA_PATTERN = re.compile(r'"@type"\s*:\s*"([^"]+)"', re.IGNORECASE)
CANONICAL_PATTERN = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]*>', re.IGNORECASE)
OG_PATTERN = re.compile(r'<meta[^>]+property=["\']og:', re.IGNORECASE)
FAQ_PATTERN = re.compile(r'faq|frequently\s+asked|common\s+questions', re.IGNORECASE)
BLOG_LINK_PATTERN = re.compile(r'/blog|/news|/articles|/resources|/insights', re.IGNORECASE)
CTA_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'get\s+(a\s+)?free\s+quote', r'schedule\s+(a\s+)?consultation',
        r'call\s+(us\s+)?now', r'contact\s+us', r'request\s+(a\s+)?quote',
        r'book\s+(a\s+|an\s+)?appointment', r'free\s+estimate',
        r'get\s+started', r'sign\s+up', r'learn\s+more',
    ]
]
REVIEW_WIDGET_PATTERNS = [
    'google-reviews', 'trustpilot', 'birdeye', 'podium', 'yotpo',
    'review-widget', 'testimonial', 'customer-review',
]
GOOGLE_MAPS_PATTERN = re.compile(
    r'maps\.google|google\.com/maps|maps\.googleapis', re.IGNORECASE
)
NAP_PHONE = re.compile(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
NAP_ADDRESS = re.compile(
    r'\d+\s+[\w\s]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ln|Lane|Ct|Court|Way|Pkwy|Hwy)',
    re.IGNORECASE,
)
SOCIAL_PATTERNS = {
    "facebook": re.compile(r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._\-]+/?'),
    "instagram": re.compile(r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._\-]+/?'),
    "linkedin": re.compile(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9._\-]+/?'),
    "twitter": re.compile(r'https?://(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9._\-]+/?'),
    "tiktok": re.compile(r'https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9._\-]+/?'),
    "youtube": re.compile(r'https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)[a-zA-Z0-9._\-]+/?'),
    "yelp": re.compile(r'https?://(?:www\.)?yelp\.com/biz/[a-zA-Z0-9._\-]+/?'),
    "nextdoor": re.compile(r'https?://(?:www\.)?nextdoor\.com/[a-zA-Z0-9._\-/]+/?'),
}


# ── Data Structures ───────────────────────────────────────────────────────

@dataclass
class SiteExtraction:
    """Raw data extracted from a website."""
    url: str = ""
    final_url: str = ""
    is_https: bool = False
    status_code: int = 0
    load_time_ms: int = 0
    html_size_bytes: int = 0
    title: str = ""
    meta_description: str = ""
    has_viewport: bool = False
    has_canonical: bool = False
    has_og_tags: bool = False
    has_robots_txt: bool = False
    robots_txt_content: str = ""
    has_sitemap: bool = False
    sitemap_url_count: int = 0
    schema_types: list[str] = field(default_factory=list)
    headings: dict[str, list[str]] = field(default_factory=dict)  # h1: [...], h2: [...]
    word_count: int = 0
    text_content: str = ""  # first ~3000 chars of visible text
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    images_total: int = 0
    images_with_alt: int = 0
    images_without_alt: int = 0
    forms_count: int = 0
    scripts_external: int = 0
    stylesheets_external: int = 0
    social_links: dict[str, str] = field(default_factory=dict)
    has_google_maps: bool = False
    has_nap_phone: bool = False
    has_nap_address: bool = False
    has_faq: bool = False
    has_blog_link: bool = False
    cta_found: list[str] = field(default_factory=list)
    has_review_widget: bool = False
    has_testimonials: bool = False
    pages_crawled: int = 1
    internal_page_urls: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class Finding:
    """Single audit finding."""
    category: str  # technical_seo, content_quality, local_seo, onpage_seo, ai_readiness
    metric: str
    status: str  # pass, warn, fail
    score: int  # 0-100 contribution to category
    finding: str
    recommendation: str
    impact: str  # high, medium, low


@dataclass
class CompetitorSnapshot:
    """Quick extraction from a competitor site."""
    url: str = ""
    business_name: str = ""
    word_count: int = 0
    pages_found: int = 0
    has_blog: bool = False
    blog_post_count: int = 0
    schema_types: list[str] = field(default_factory=list)
    social_link_count: int = 0
    has_review_widget: bool = False
    has_testimonials: bool = False
    has_google_maps: bool = False
    has_faq: bool = False
    title: str = ""
    meta_description: str = ""
    error: str = ""


@dataclass
class DeepAuditResult:
    """Full deep audit result."""
    url: str = ""
    overall_score: int = 0
    overall_grade: str = "F"
    audited_at: str = ""
    duration_seconds: float = 0
    categories: dict[str, dict] = field(default_factory=dict)
    # {category: {score, weight, weighted_score, findings: [Finding]}}
    findings: list[dict] = field(default_factory=list)
    ai_summary: str = ""
    ai_recommendations: list[str] = field(default_factory=list)
    competitor_analysis: list[dict] = field(default_factory=list)
    competitor_comparison: dict = field(default_factory=dict)
    extraction: dict = field(default_factory=dict)  # raw extraction data for reference
    error: str = ""


# ── Extraction ────────────────────────────────────────────────────────────

async def _fetch_page(url: str, client: httpx.AsyncClient) -> tuple[str, int, float]:
    """Fetch a page, return (html, status, load_time_ms)."""
    start = time.monotonic()
    try:
        resp = await client.get(url, follow_redirects=True, timeout=15.0)
        elapsed = (time.monotonic() - start) * 1000
        return resp.text, resp.status_code, elapsed
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        logger.warning("Failed to fetch %s: %s", url, exc)
        return "", 0, elapsed


def _extract_visible_text(soup: BeautifulSoup) -> str:
    """Extract visible text content from parsed HTML."""
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _count_internal_pages(html: str, base_url: str) -> list[str]:
    """Find internal page links."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.replace("www.", "")
    found = set()
    href_re = re.compile(r'href=["\']([^"\'#]+)["\']', re.IGNORECASE)
    for match in href_re.finditer(html):
        href = match.group(1)
        if href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
            continue
        full = urljoin(base_url, href)
        link_domain = urlparse(full).netloc.replace("www.", "")
        if link_domain == base_domain:
            # Normalize: strip query/fragment
            path = urlparse(full).path.rstrip("/") or "/"
            normalized = f"{parsed_base.scheme}://{parsed_base.netloc}{path}"
            if normalized != base_url.rstrip("/"):
                found.add(normalized)
    return sorted(found)[:50]  # cap at 50


def _count_blog_posts(html: str) -> int:
    """Estimate blog post count from a blog/news page."""
    soup = BeautifulSoup(html, "html.parser")
    # Look for article tags or common blog post patterns
    articles = soup.find_all("article")
    if articles:
        return len(articles)
    # Look for repeated post-like structures
    for cls in ["post", "blog-post", "entry", "article-card", "news-item"]:
        items = soup.find_all(class_=re.compile(cls, re.IGNORECASE))
        if items:
            return len(items)
    # Count h2/h3 tags as proxy
    headings = soup.find_all(["h2", "h3"])
    if len(headings) > 3:
        return len(headings)
    return 0


async def extract_site_data(url: str) -> SiteExtraction:
    """Extract comprehensive data from a website."""
    ext = SiteExtraction(url=url)

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": "WarRoom-Auditor/1.0"},
            limits=httpx.Limits(max_connections=5),
        ) as client:
            # 1. Fetch homepage
            html, status, load_time = await _fetch_page(url, client)
            if not html or status == 0:
                ext.error = f"Failed to load homepage (status {status})"
                return ext

            ext.status_code = status
            ext.load_time_ms = int(load_time)
            ext.html_size_bytes = len(html.encode("utf-8", errors="ignore"))
            ext.final_url = url
            ext.is_https = urlparse(url).scheme == "https"

            soup = BeautifulSoup(html, "html.parser")

            # Title
            title_tag = soup.find("title")
            ext.title = title_tag.get_text(strip=True) if title_tag else ""

            # Meta description
            meta = soup.find("meta", attrs={"name": "description"})
            ext.meta_description = meta.get("content", "") if meta else ""

            # Viewport
            ext.has_viewport = bool(soup.find("meta", attrs={"name": "viewport"}))

            # Canonical
            ext.has_canonical = bool(CANONICAL_PATTERN.search(html))

            # OG tags
            ext.has_og_tags = bool(OG_PATTERN.search(html))

            # Headings
            for level in ["h1", "h2", "h3", "h4"]:
                tags = soup.find_all(level)
                if tags:
                    ext.headings[level] = [t.get_text(strip=True) for t in tags][:20]

            # Visible text
            text_content = _extract_visible_text(BeautifulSoup(html, "html.parser"))
            ext.word_count = len(text_content.split())
            ext.text_content = text_content[:3000]

            # Images
            imgs = soup.find_all("img")
            ext.images_total = len(imgs)
            ext.images_with_alt = sum(1 for img in imgs if img.get("alt", "").strip())
            ext.images_without_alt = ext.images_total - ext.images_with_alt

            # Forms
            ext.forms_count = len(soup.find_all("form"))

            # External scripts/styles
            ext.scripts_external = len([
                s for s in soup.find_all("script", src=True)
                if s["src"].startswith("http")
            ])
            ext.stylesheets_external = len([
                l for l in soup.find_all("link", rel="stylesheet")
                if l.get("href", "").startswith("http")
            ])

            # Links
            internal_pages = _count_internal_pages(html, url)
            ext.internal_page_urls = internal_pages
            ext.internal_links = internal_pages
            ext.pages_crawled = 1

            # External links
            parsed_base = urlparse(url)
            base_domain = parsed_base.netloc.replace("www.", "")
            ext.external_links = list(set(
                a["href"] for a in soup.find_all("a", href=True)
                if a["href"].startswith("http")
                and urlparse(a["href"]).netloc.replace("www.", "") != base_domain
            ))[:30]

            # Schema markup
            ext.schema_types = list(set(SCHEMA_PATTERN.findall(html)))

            # Social links
            for platform, pattern in SOCIAL_PATTERNS.items():
                match = pattern.search(html)
                if match:
                    ext.social_links[platform] = match.group(0).rstrip("/")

            # Google Maps
            ext.has_google_maps = bool(GOOGLE_MAPS_PATTERN.search(html))

            # NAP
            ext.has_nap_phone = bool(NAP_PHONE.search(text_content))
            ext.has_nap_address = bool(NAP_ADDRESS.search(text_content))

            # FAQ
            ext.has_faq = bool(FAQ_PATTERN.search(html))

            # Blog link
            ext.has_blog_link = bool(BLOG_LINK_PATTERN.search(html))

            # CTAs
            for pattern in CTA_PATTERNS:
                match = pattern.search(text_content)
                if match:
                    ext.cta_found.append(match.group(0))
            ext.cta_found = list(set(ext.cta_found))

            # Review widgets / testimonials
            html_lower = html.lower()
            ext.has_review_widget = any(p in html_lower for p in REVIEW_WIDGET_PATTERNS)
            ext.has_testimonials = "testimonial" in html_lower or "customer review" in html_lower

            # 2. Check robots.txt
            robots_url = f"{parsed_base.scheme}://{parsed_base.netloc}/robots.txt"
            try:
                robots_html, robots_status, _ = await _fetch_page(robots_url, client)
                ext.has_robots_txt = robots_status == 200 and "user-agent" in robots_html.lower()
                if ext.has_robots_txt:
                    ext.robots_txt_content = robots_html[:500]
            except Exception:
                pass

            # 3. Check sitemap.xml
            sitemap_url = f"{parsed_base.scheme}://{parsed_base.netloc}/sitemap.xml"
            try:
                sitemap_html, sitemap_status, _ = await _fetch_page(sitemap_url, client)
                ext.has_sitemap = sitemap_status == 200 and "<url" in sitemap_html.lower()
                if ext.has_sitemap:
                    ext.sitemap_url_count = sitemap_html.lower().count("<url>")
            except Exception:
                pass

            # 4. Crawl a few internal pages for word count boost
            pages_to_crawl = internal_pages[:4]
            blog_url = None
            for page_url in pages_to_crawl:
                await asyncio.sleep(0.5)
                page_html, page_status, _ = await _fetch_page(page_url, client)
                if page_status == 200 and page_html:
                    ext.pages_crawled += 1
                    page_text = _extract_visible_text(BeautifulSoup(page_html, "html.parser"))
                    ext.word_count += len(page_text.split())
                    # Check if it's a blog page
                    if BLOG_LINK_PATTERN.search(page_url):
                        blog_url = page_url

    except Exception as exc:
        ext.error = str(exc)
        logger.error("Site extraction failed for %s: %s", url, exc)

    return ext


async def extract_competitor_snapshot(url: str, name: str = "") -> CompetitorSnapshot:
    """Quick extraction from a competitor site for comparison."""
    snap = CompetitorSnapshot(url=url, business_name=name)

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "WarRoom-Auditor/1.0"},
        ) as client:
            html, status, _ = await _fetch_page(url, client)
            if not html or status != 200:
                snap.error = f"Failed to load (status {status})"
                return snap

            soup = BeautifulSoup(html, "html.parser")

            # Title / meta
            title_tag = soup.find("title")
            snap.title = title_tag.get_text(strip=True) if title_tag else ""
            meta = soup.find("meta", attrs={"name": "description"})
            snap.meta_description = meta.get("content", "") if meta else ""

            # Word count
            text = _extract_visible_text(BeautifulSoup(html, "html.parser"))
            snap.word_count = len(text.split())

            # Internal pages
            pages = _count_internal_pages(html, url)
            snap.pages_found = len(pages) + 1  # +1 for homepage

            # Blog
            snap.has_blog = bool(BLOG_LINK_PATTERN.search(html))
            if snap.has_blog:
                # Try to count posts
                for page_url in pages:
                    if BLOG_LINK_PATTERN.search(page_url):
                        try:
                            blog_html, blog_status, _ = await _fetch_page(page_url, client)
                            if blog_status == 200:
                                snap.blog_post_count = _count_blog_posts(blog_html)
                        except Exception:
                            pass
                        break

            # Schema
            snap.schema_types = list(set(SCHEMA_PATTERN.findall(html)))

            # Social links
            social_count = 0
            for _, pattern in SOCIAL_PATTERNS.items():
                if pattern.search(html):
                    social_count += 1
            snap.social_link_count = social_count

            # Reviews / testimonials
            html_lower = html.lower()
            snap.has_review_widget = any(p in html_lower for p in REVIEW_WIDGET_PATTERNS)
            snap.has_testimonials = "testimonial" in html_lower or "customer review" in html_lower
            snap.has_google_maps = bool(GOOGLE_MAPS_PATTERN.search(html))
            snap.has_faq = bool(FAQ_PATTERN.search(html))

    except Exception as exc:
        snap.error = str(exc)
        logger.warning("Competitor snapshot failed for %s: %s", url, exc)

    return snap


# ── Scoring Engine ────────────────────────────────────────────────────────

CATEGORY_WEIGHTS = {
    "technical_seo": 0.25,
    "content_quality": 0.25,
    "local_seo": 0.20,
    "onpage_seo": 0.15,
    "ai_readiness": 0.15,
}


def _score_technical_seo(ext: SiteExtraction) -> tuple[int, list[Finding]]:
    """Score technical SEO factors."""
    findings: list[Finding] = []
    points = 0
    max_points = 0

    # SSL (15 pts)
    max_points += 15
    if ext.is_https:
        points += 15
        findings.append(Finding("technical_seo", "SSL/HTTPS", "pass", 15,
                                "Site uses HTTPS", "", "high"))
    else:
        findings.append(Finding("technical_seo", "SSL/HTTPS", "fail", 0,
                                "Site does NOT use HTTPS — browsers show 'Not Secure' warning",
                                "Install an SSL certificate immediately. This is critical for trust and SEO rankings.",
                                "high"))

    # Viewport (10 pts)
    max_points += 10
    if ext.has_viewport:
        points += 10
        findings.append(Finding("technical_seo", "Mobile Viewport", "pass", 10,
                                "Viewport meta tag present", "", "medium"))
    else:
        findings.append(Finding("technical_seo", "Mobile Viewport", "fail", 0,
                                "Missing viewport meta tag — site likely not mobile-optimized",
                                "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
                                "high"))

    # Page speed indicators (15 pts)
    max_points += 15
    html_kb = ext.html_size_bytes / 1024
    if html_kb < 100:
        points += 10
        findings.append(Finding("technical_seo", "Page Size", "pass", 10,
                                f"HTML size is {html_kb:.0f}KB (lightweight)", "", "medium"))
    elif html_kb < 300:
        points += 5
        findings.append(Finding("technical_seo", "Page Size", "warn", 5,
                                f"HTML size is {html_kb:.0f}KB (moderate)",
                                "Consider optimizing images and minifying CSS/JS to reduce page weight.",
                                "medium"))
    else:
        findings.append(Finding("technical_seo", "Page Size", "fail", 0,
                                f"HTML size is {html_kb:.0f}KB (heavy — slow loading)",
                                "Page is bloated. Optimize images, lazy-load below-fold content, minify resources.",
                                "high"))

    if ext.scripts_external <= 5:
        points += 5
        findings.append(Finding("technical_seo", "External Scripts", "pass", 5,
                                f"{ext.scripts_external} external scripts (efficient)", "", "low"))
    else:
        findings.append(Finding("technical_seo", "External Scripts", "warn", 0,
                                f"{ext.scripts_external} external scripts — each one blocks page rendering",
                                "Audit third-party scripts. Remove unused ones, defer non-critical scripts.",
                                "medium"))

    # robots.txt (10 pts)
    max_points += 10
    if ext.has_robots_txt:
        points += 10
        findings.append(Finding("technical_seo", "robots.txt", "pass", 10,
                                "robots.txt found and configured", "", "medium"))
    else:
        findings.append(Finding("technical_seo", "robots.txt", "fail", 0,
                                "No robots.txt found — search engines have no crawl guidance",
                                "Create a robots.txt file to guide search engine crawlers.",
                                "medium"))

    # sitemap.xml (10 pts)
    max_points += 10
    if ext.has_sitemap:
        points += 10
        detail = f"sitemap.xml found with {ext.sitemap_url_count} URLs" if ext.sitemap_url_count else "sitemap.xml found"
        findings.append(Finding("technical_seo", "XML Sitemap", "pass", 10,
                                detail, "", "medium"))
    else:
        findings.append(Finding("technical_seo", "XML Sitemap", "fail", 0,
                                "No sitemap.xml found — search engines may miss pages",
                                "Generate and submit an XML sitemap to Google Search Console.",
                                "medium"))

    # Canonical tag (10 pts)
    max_points += 10
    if ext.has_canonical:
        points += 10
        findings.append(Finding("technical_seo", "Canonical Tag", "pass", 10,
                                "Canonical tag present — prevents duplicate content issues", "", "medium"))
    else:
        findings.append(Finding("technical_seo", "Canonical Tag", "warn", 0,
                                "No canonical tag found — risk of duplicate content in search results",
                                "Add a canonical link tag to each page to prevent duplicate content issues.",
                                "medium"))

    # Heading hierarchy (10 pts)
    max_points += 10
    h1s = ext.headings.get("h1", [])
    h2s = ext.headings.get("h2", [])
    if len(h1s) == 1 and len(h2s) >= 1:
        points += 10
        findings.append(Finding("technical_seo", "Heading Hierarchy", "pass", 10,
                                f"Good structure: 1 H1, {len(h2s)} H2s", "", "medium"))
    elif len(h1s) == 0:
        findings.append(Finding("technical_seo", "Heading Hierarchy", "fail", 0,
                                "No H1 tag found — every page needs exactly one H1",
                                "Add a single, descriptive H1 tag that includes your primary keyword.",
                                "high"))
    elif len(h1s) > 1:
        findings.append(Finding("technical_seo", "Heading Hierarchy", "warn", 3,
                                f"Multiple H1 tags ({len(h1s)}) — should be exactly one per page",
                                "Use only one H1 per page. Convert extra H1s to H2s.",
                                "medium"))
        points += 3
    else:
        points += 5
        findings.append(Finding("technical_seo", "Heading Hierarchy", "warn", 5,
                                f"H1 present but no H2 subheadings — content lacks structure",
                                "Break content into sections with H2 subheadings for better readability and SEO.",
                                "medium"))

    # Clean URL (10 pts)
    max_points += 10
    parsed = urlparse(ext.url)
    path = parsed.path
    if not re.search(r'[?&=].*[?&=]|\.php|\.asp|index\.html', ext.url):
        points += 10
        findings.append(Finding("technical_seo", "Clean URLs", "pass", 10,
                                "URL structure is clean and readable", "", "low"))
    else:
        findings.append(Finding("technical_seo", "Clean URLs", "warn", 3,
                                "URL contains query parameters or file extensions",
                                "Use clean, descriptive URLs without file extensions or query strings.",
                                "low"))
        points += 3

    score = int((points / max_points) * 100) if max_points > 0 else 0
    return score, findings


def _score_content_quality(ext: SiteExtraction) -> tuple[int, list[Finding]]:
    """Score content quality."""
    findings: list[Finding] = []
    points = 0
    max_points = 0

    # Word count (20 pts)
    max_points += 20
    if ext.word_count >= 2000:
        points += 20
        findings.append(Finding("content_quality", "Word Count", "pass", 20,
                                f"{ext.word_count} words across {ext.pages_crawled} page(s) — solid content depth",
                                "", "high"))
    elif ext.word_count >= 1000:
        points += 12
        findings.append(Finding("content_quality", "Word Count", "warn", 12,
                                f"Only {ext.word_count} words across {ext.pages_crawled} page(s) — below industry standard",
                                "Top-ranking service pages average 2,000+ words. Add detailed service descriptions, process explanations, and FAQs.",
                                "high"))
    elif ext.word_count >= 300:
        points += 5
        findings.append(Finding("content_quality", "Word Count", "fail", 5,
                                f"Only {ext.word_count} words — thin content that Google may deprioritize",
                                "This is critically thin content. Competitors with 2,000+ words will outrank this site. Add comprehensive service pages.",
                                "high"))
    else:
        findings.append(Finding("content_quality", "Word Count", "fail", 0,
                                f"Only {ext.word_count} words — virtually no content for Google to index",
                                "The site has almost no indexable content. Create detailed pages for each service offered.",
                                "high"))

    # Multi-page (15 pts)
    max_points += 15
    page_count = len(ext.internal_page_urls) + 1
    if page_count >= 8:
        points += 15
        findings.append(Finding("content_quality", "Site Depth", "pass", 15,
                                f"{page_count} pages found — multi-page site with good depth", "", "high"))
    elif page_count >= 4:
        points += 10
        findings.append(Finding("content_quality", "Site Depth", "warn", 10,
                                f"Only {page_count} pages — site could benefit from more content",
                                "Add dedicated pages for each service, an About page, FAQ page, and blog section.",
                                "high"))
    elif page_count == 1:
        findings.append(Finding("content_quality", "Site Depth", "fail", 0,
                                "Single-page website — extremely limited for SEO",
                                "A single page cannot rank for multiple services/keywords. Create individual pages for each service you offer.",
                                "high"))
    else:
        points += 5
        findings.append(Finding("content_quality", "Site Depth", "fail", 5,
                                f"Only {page_count} pages — minimal site structure",
                                "Create more pages to target different keywords and services.",
                                "high"))

    # CTAs (15 pts)
    max_points += 15
    if len(ext.cta_found) >= 3:
        points += 15
        findings.append(Finding("content_quality", "Calls to Action", "pass", 15,
                                f"{len(ext.cta_found)} CTAs found: {', '.join(ext.cta_found[:3])}",
                                "", "medium"))
    elif len(ext.cta_found) >= 1:
        points += 8
        findings.append(Finding("content_quality", "Calls to Action", "warn", 8,
                                f"Only {len(ext.cta_found)} CTA(s) found — visitors need clear next steps",
                                "Add prominent CTAs on every page: 'Get a Free Quote', 'Schedule a Consultation', 'Call Now'.",
                                "high"))
    else:
        findings.append(Finding("content_quality", "Calls to Action", "fail", 0,
                                "No clear calls to action found — visitors don't know what to do next",
                                "Add prominent CTAs above the fold and after each section. Every page should have a clear next step.",
                                "high"))

    # Blog/resources (15 pts)
    max_points += 15
    if ext.has_blog_link:
        points += 15
        findings.append(Finding("content_quality", "Blog/Resources", "pass", 15,
                                "Blog or resources section found — great for ongoing SEO",
                                "", "medium"))
    else:
        findings.append(Finding("content_quality", "Blog/Resources", "fail", 0,
                                "No blog or resources section — missing ongoing content strategy",
                                "Start a blog with helpful articles about your industry. Fresh content signals authority to Google.",
                                "medium"))

    # FAQ (10 pts)
    max_points += 10
    if ext.has_faq:
        points += 10
        findings.append(Finding("content_quality", "FAQ Content", "pass", 10,
                                "FAQ section found — helps with featured snippets and voice search", "", "medium"))
    else:
        findings.append(Finding("content_quality", "FAQ Content", "fail", 0,
                                "No FAQ section — missing easy wins for search visibility",
                                "Add an FAQ section answering common customer questions. This helps with featured snippets and AI answers.",
                                "medium"))

    # Forms (10 pts)
    max_points += 10
    if ext.forms_count >= 1:
        points += 10
        findings.append(Finding("content_quality", "Contact Forms", "pass", 10,
                                f"{ext.forms_count} form(s) found — visitors can easily reach out", "", "medium"))
    else:
        findings.append(Finding("content_quality", "Contact Forms", "fail", 0,
                                "No contact forms found — visitors have no easy way to reach out",
                                "Add a contact form on every page, especially above the fold on the homepage.",
                                "high"))

    # Testimonials / reviews (15 pts)
    max_points += 15
    if ext.has_review_widget or ext.has_testimonials:
        points += 15
        label = "Review widget" if ext.has_review_widget else "Testimonials section"
        findings.append(Finding("content_quality", "Social Proof", "pass", 15,
                                f"{label} found — builds trust with visitors", "", "medium"))
    else:
        findings.append(Finding("content_quality", "Social Proof", "fail", 0,
                                "No testimonials or review widgets found — missing critical trust signals",
                                "Add customer testimonials or embed Google reviews. Social proof increases conversion rates by 15-30%.",
                                "high"))

    score = int((points / max_points) * 100) if max_points > 0 else 0
    return score, findings


def _score_local_seo(ext: SiteExtraction) -> tuple[int, list[Finding]]:
    """Score local SEO factors."""
    findings: list[Finding] = []
    points = 0
    max_points = 0

    # NAP - Phone (20 pts)
    max_points += 20
    if ext.has_nap_phone:
        points += 20
        findings.append(Finding("local_seo", "Phone Number Visible", "pass", 20,
                                "Phone number displayed on site", "", "high"))
    else:
        findings.append(Finding("local_seo", "Phone Number Visible", "fail", 0,
                                "No phone number visible on the site",
                                "Display your phone number prominently in the header and footer of every page.",
                                "high"))

    # NAP - Address (20 pts)
    max_points += 20
    if ext.has_nap_address:
        points += 20
        findings.append(Finding("local_seo", "Address Visible", "pass", 20,
                                "Physical address found on site", "", "high"))
    else:
        findings.append(Finding("local_seo", "Address Visible", "fail", 0,
                                "No physical address visible on the site",
                                "Display your business address on every page (footer is ideal). This is critical for local search rankings.",
                                "high"))

    # Google Maps embed (15 pts)
    max_points += 15
    if ext.has_google_maps:
        points += 15
        findings.append(Finding("local_seo", "Google Maps Embed", "pass", 15,
                                "Google Maps embed found — helps Google verify your location", "", "medium"))
    else:
        findings.append(Finding("local_seo", "Google Maps Embed", "fail", 0,
                                "No Google Maps embed — missing location verification signal",
                                "Embed a Google Map showing your business location. This reinforces your NAP for local SEO.",
                                "medium"))

    # Schema markup (25 pts)
    max_points += 25
    local_schemas = [s for s in ext.schema_types if s.lower() in (
        "localbusiness", "service", "organization", "place",
        "homeandconstructionbusiness", "roofingcontractor",
        "plumber", "electrician", "hvacbusiness", "autobody",
    )]
    if local_schemas:
        points += 25
        findings.append(Finding("local_seo", "Schema Markup", "pass", 25,
                                f"Schema markup found: {', '.join(local_schemas)}", "", "high"))
    elif ext.schema_types:
        points += 10
        findings.append(Finding("local_seo", "Schema Markup", "warn", 10,
                                f"Schema found ({', '.join(ext.schema_types)}) but no LocalBusiness or Service schema",
                                "Add LocalBusiness schema markup with your NAP, hours, and service area.",
                                "high"))
    else:
        findings.append(Finding("local_seo", "Schema Markup", "fail", 0,
                                "No schema markup at all — invisible to Google's rich results",
                                "Add LocalBusiness and Service schema markup. This enables rich results and knowledge panel features.",
                                "high"))

    # Social presence (20 pts)
    max_points += 20
    social_count = len(ext.social_links)
    if social_count >= 4:
        points += 20
        findings.append(Finding("local_seo", "Social Presence", "pass", 20,
                                f"{social_count} social profiles linked — strong online presence", "", "medium"))
    elif social_count >= 2:
        points += 12
        findings.append(Finding("local_seo", "Social Presence", "warn", 12,
                                f"Only {social_count} social profiles linked",
                                "Add links to all active social profiles. More presence = more trust signals for Google.",
                                "medium"))
    elif social_count >= 1:
        points += 5
        findings.append(Finding("local_seo", "Social Presence", "warn", 5,
                                f"Only {social_count} social profile linked — minimal presence",
                                "Create and link to Facebook, Instagram, LinkedIn, and Google Business Profile at minimum.",
                                "medium"))
    else:
        findings.append(Finding("local_seo", "Social Presence", "fail", 0,
                                "No social media links found — missing trust signals",
                                "Link to active social profiles. For local businesses, Facebook and Google Business are essential.",
                                "medium"))

    score = int((points / max_points) * 100) if max_points > 0 else 0
    return score, findings


def _score_onpage_seo(ext: SiteExtraction) -> tuple[int, list[Finding]]:
    """Score on-page SEO factors."""
    findings: list[Finding] = []
    points = 0
    max_points = 0

    # Title tag (25 pts)
    max_points += 25
    title_len = len(ext.title)
    if 30 <= title_len <= 60:
        points += 25
        findings.append(Finding("onpage_seo", "Title Tag", "pass", 25,
                                f"Title tag is {title_len} chars (optimal 30-60): \"{ext.title}\"", "", "high"))
    elif title_len > 0:
        points += 12
        status = "too long" if title_len > 60 else "too short"
        findings.append(Finding("onpage_seo", "Title Tag", "warn", 12,
                                f"Title tag is {title_len} chars ({status}): \"{ext.title[:70]}\"",
                                "Optimize title to 30-60 characters. Include your primary keyword and location.",
                                "high"))
    else:
        findings.append(Finding("onpage_seo", "Title Tag", "fail", 0,
                                "No title tag found — critical for SEO",
                                "Add a descriptive title tag with your primary keyword, business name, and location.",
                                "high"))

    # Meta description (20 pts)
    max_points += 20
    desc_len = len(ext.meta_description)
    if 120 <= desc_len <= 160:
        points += 20
        findings.append(Finding("onpage_seo", "Meta Description", "pass", 20,
                                f"Meta description is {desc_len} chars (optimal)", "", "high"))
    elif desc_len > 0:
        points += 10
        status = "too long" if desc_len > 160 else "too short"
        findings.append(Finding("onpage_seo", "Meta Description", "warn", 10,
                                f"Meta description is {desc_len} chars ({status})",
                                "Write a compelling meta description between 120-160 characters with a clear CTA.",
                                "high"))
    else:
        findings.append(Finding("onpage_seo", "Meta Description", "fail", 0,
                                "No meta description — Google will generate one (poorly)",
                                "Write a compelling meta description that includes your services and location.",
                                "high"))

    # H1 tag (15 pts)
    max_points += 15
    h1s = ext.headings.get("h1", [])
    if len(h1s) == 1:
        points += 15
        findings.append(Finding("onpage_seo", "H1 Tag", "pass", 15,
                                f"H1: \"{h1s[0][:80]}\"", "", "high"))
    elif len(h1s) == 0:
        findings.append(Finding("onpage_seo", "H1 Tag", "fail", 0,
                                "No H1 tag — the most important on-page SEO element is missing",
                                "Add a single H1 tag with your primary keyword and service description.",
                                "high"))
    else:
        points += 7
        findings.append(Finding("onpage_seo", "H1 Tag", "warn", 7,
                                f"{len(h1s)} H1 tags found — should be exactly 1",
                                "Use only one H1 per page. It should be your primary keyword-rich headline.",
                                "medium"))

    # Image alt tags (15 pts)
    max_points += 15
    if ext.images_total == 0:
        points += 10
        findings.append(Finding("onpage_seo", "Image Alt Tags", "warn", 10,
                                "No images found on the site", "Add relevant images with descriptive alt tags.",
                                "low"))
    elif ext.images_without_alt == 0:
        points += 15
        findings.append(Finding("onpage_seo", "Image Alt Tags", "pass", 15,
                                f"All {ext.images_total} images have alt tags", "", "medium"))
    else:
        ratio = ext.images_with_alt / ext.images_total
        pts = int(15 * ratio)
        points += pts
        findings.append(Finding("onpage_seo", "Image Alt Tags", "warn" if ratio > 0.5 else "fail", pts,
                                f"{ext.images_without_alt} of {ext.images_total} images missing alt tags",
                                "Add descriptive alt tags to all images. Include keywords naturally.",
                                "medium"))

    # Internal linking (10 pts)
    max_points += 10
    internal_count = len(ext.internal_links)
    if internal_count >= 5:
        points += 10
        findings.append(Finding("onpage_seo", "Internal Linking", "pass", 10,
                                f"{internal_count} internal links — good site structure", "", "medium"))
    elif internal_count >= 2:
        points += 5
        findings.append(Finding("onpage_seo", "Internal Linking", "warn", 5,
                                f"Only {internal_count} internal links — weak site structure",
                                "Add more internal links between related pages to help Google crawl and rank your content.",
                                "medium"))
    else:
        findings.append(Finding("onpage_seo", "Internal Linking", "fail", 0,
                                "Minimal or no internal linking — site structure is flat",
                                "Create a logical internal linking structure connecting related pages.",
                                "medium"))

    # OG tags (15 pts)
    max_points += 15
    if ext.has_og_tags:
        points += 15
        findings.append(Finding("onpage_seo", "Social Meta Tags", "pass", 15,
                                "Open Graph tags present — links will display nicely on social media", "", "low"))
    else:
        findings.append(Finding("onpage_seo", "Social Meta Tags", "fail", 0,
                                "No Open Graph tags — links shared on social media will look generic",
                                "Add og:title, og:description, og:image tags for better social sharing.",
                                "low"))

    score = int((points / max_points) * 100) if max_points > 0 else 0
    return score, findings


def _score_ai_readiness(ext: SiteExtraction) -> tuple[int, list[Finding]]:
    """Score AI search readiness."""
    findings: list[Finding] = []
    points = 0
    max_points = 0

    # Structured content with clear headers (20 pts)
    max_points += 20
    h2_count = len(ext.headings.get("h2", []))
    h3_count = len(ext.headings.get("h3", []))
    if h2_count >= 4 and h3_count >= 2:
        points += 20
        findings.append(Finding("ai_readiness", "Structured Content", "pass", 20,
                                f"Well-structured with {h2_count} H2s and {h3_count} H3s — easy for AI to extract",
                                "", "high"))
    elif h2_count >= 2:
        points += 10
        findings.append(Finding("ai_readiness", "Structured Content", "warn", 10,
                                f"Some structure ({h2_count} H2s) but could be better organized",
                                "Use clear H2/H3 headings to structure your content. AI systems extract info from well-organized pages.",
                                "high"))
    else:
        findings.append(Finding("ai_readiness", "Structured Content", "fail", 0,
                                "Content lacks structure — AI systems will struggle to extract useful information",
                                "Structure content with clear headings (H2, H3). Use definitive statements AI can cite.",
                                "high"))

    # FAQ content (20 pts)
    max_points += 20
    if ext.has_faq:
        points += 20
        findings.append(Finding("ai_readiness", "FAQ-Style Content", "pass", 20,
                                "FAQ section found — directly answers questions AI systems are asked", "", "high"))
    else:
        findings.append(Finding("ai_readiness", "FAQ-Style Content", "fail", 0,
                                "No FAQ content — missing the #1 format AI systems use to answer questions",
                                "Add a comprehensive FAQ section. When someone asks ChatGPT 'best roofer near me', FAQ content gets cited.",
                                "high"))

    # Schema markup for rich results (20 pts)
    max_points += 20
    good_schemas = [s for s in ext.schema_types if s.lower() in (
        "faqpage", "howto", "service", "localbusiness", "product", "review",
        "aggregaterating", "organization",
    )]
    if len(good_schemas) >= 2:
        points += 20
        findings.append(Finding("ai_readiness", "Rich Result Schema", "pass", 20,
                                f"Multiple schemas for rich results: {', '.join(good_schemas)}", "", "high"))
    elif good_schemas:
        points += 10
        findings.append(Finding("ai_readiness", "Rich Result Schema", "warn", 10,
                                f"Some schema markup ({', '.join(good_schemas)}) but could add more",
                                "Add FAQPage, HowTo, and AggregateRating schema for maximum AI visibility.",
                                "high"))
    else:
        findings.append(Finding("ai_readiness", "Rich Result Schema", "fail", 0,
                                "No rich result schemas — invisible to AI knowledge extraction",
                                "Add FAQPage, Service, and LocalBusiness schema. These are the primary data sources for AI answers.",
                                "high"))

    # Content depth (20 pts) — enough for AI to reference
    max_points += 20
    if ext.word_count >= 1500:
        points += 20
        findings.append(Finding("ai_readiness", "Content Depth for AI", "pass", 20,
                                f"{ext.word_count} words — enough depth for AI systems to reference", "", "high"))
    elif ext.word_count >= 500:
        points += 10
        findings.append(Finding("ai_readiness", "Content Depth for AI", "warn", 10,
                                f"Only {ext.word_count} words — AI systems prefer comprehensive sources",
                                "AI assistants cite authoritative, detailed pages. Thin content gets skipped.",
                                "high"))
    else:
        findings.append(Finding("ai_readiness", "Content Depth for AI", "fail", 0,
                                f"Only {ext.word_count} words — too thin for AI citation",
                                "AI systems like ChatGPT and Perplexity cite detailed, authoritative content. This site has too little to reference.",
                                "high"))

    # Content freshness signals (20 pts)
    max_points += 20
    if ext.has_blog_link:
        points += 20
        findings.append(Finding("ai_readiness", "Content Freshness", "pass", 20,
                                "Blog/resources section suggests ongoing content creation", "", "medium"))
    else:
        findings.append(Finding("ai_readiness", "Content Freshness", "fail", 0,
                                "No blog or fresh content — AI systems prefer recently updated sources",
                                "Start publishing regular content. AI systems weight recency when deciding what to cite.",
                                "medium"))

    score = int((points / max_points) * 100) if max_points > 0 else 0
    return score, findings


# ── AI Analysis ───────────────────────────────────────────────────────────

async def _get_api_key() -> str:
    """Get Anthropic API key from env or settings DB."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        try:
            from app.services.twilio_client import get_setting_value
            key = await get_setting_value("anthropic_api_key") or ""
        except Exception:
            pass
    return key


async def _call_claude(prompt: str, max_tokens: int = 2048) -> str:
    """Call Claude Haiku for AI analysis."""
    api_key = await _get_api_key()
    if not api_key:
        logger.warning("No Anthropic API key — skipping AI analysis")
        return ""

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code not in (200, 201):
                logger.error("Claude API error %d: %s", resp.status_code, resp.text[:300])
                return ""

            data = resp.json()
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            return text.strip()
    except Exception as exc:
        logger.error("Claude API call failed: %s", exc)
        return ""


async def _ai_analyze(
    ext: SiteExtraction,
    categories: dict[str, dict],
    competitors: list[CompetitorSnapshot],
    industry: str = "",
) -> tuple[str, list[str]]:
    """Send site data to Claude for comprehensive AI analysis."""

    # Build competitor section
    comp_section = ""
    if competitors:
        comp_lines = []
        for c in competitors:
            comp_lines.append(
                f"  - {c.business_name} ({c.url}): {c.word_count} words, "
                f"{c.pages_found} pages, blog={'Yes ('+str(c.blog_post_count)+' posts)' if c.has_blog else 'No'}, "
                f"schema={', '.join(c.schema_types) if c.schema_types else 'None'}, "
                f"{c.social_link_count} social links, "
                f"reviews={'Yes' if c.has_review_widget or c.has_testimonials else 'No'}, "
                f"maps={'Yes' if c.has_google_maps else 'No'}, "
                f"FAQ={'Yes' if c.has_faq else 'No'}"
            )
        comp_section = "\n\nCOMPETITOR DATA:\n" + "\n".join(comp_lines)

    # Build category summary
    cat_summary = []
    for cat_name, cat_data in categories.items():
        label = cat_name.replace("_", " ").title()
        cat_summary.append(f"  {label}: {cat_data['score']}/100")

    prompt = f"""Analyze this website for a {industry or 'local service'} business. You are a brutally honest website auditor. This analysis is a sales tool — it shows prospects exactly why they need professional help with their website.

SITE DATA:
- URL: {ext.url}
- Title: "{ext.title}"
- Meta Description: "{ext.meta_description[:200]}"
- Word Count: {ext.word_count} (across {ext.pages_crawled} pages)
- Internal Pages Found: {len(ext.internal_page_urls)}
- Has SSL: {ext.is_https}
- Has robots.txt: {ext.has_robots_txt}
- Has sitemap.xml: {ext.has_sitemap}
- Schema Types: {', '.join(ext.schema_types) if ext.schema_types else 'None'}
- Social Links: {len(ext.social_links)} ({', '.join(ext.social_links.keys()) if ext.social_links else 'none'})
- Has Google Maps: {ext.has_google_maps}
- Has Phone Visible: {ext.has_nap_phone}
- Has Address Visible: {ext.has_nap_address}
- Has FAQ: {ext.has_faq}
- Has Blog: {ext.has_blog_link}
- Has Review Widget: {ext.has_review_widget}
- CTAs Found: {', '.join(ext.cta_found) if ext.cta_found else 'None'}
- Images: {ext.images_total} total ({ext.images_without_alt} missing alt tags)
- Forms: {ext.forms_count}
- Headings: H1={ext.headings.get('h1', [])}, H2={ext.headings.get('h2', [])}

CATEGORY SCORES:
{chr(10).join(cat_summary)}
{comp_section}

CONTENT EXCERPT (first 2000 chars):
{ext.text_content[:2000]}

Respond in this exact JSON format:
{{
  "summary": "2-3 sentence executive summary of the site's biggest problems. Be specific, not generic.",
  "recommendations": [
    "Specific, actionable recommendation 1 (include expected impact)",
    "Specific, actionable recommendation 2",
    "Specific, actionable recommendation 3",
    "Specific, actionable recommendation 4",
    "Specific, actionable recommendation 5"
  ]{', "competitor_insights": "2-3 sentences comparing this site against the competitors. What are competitors doing that this site is not? Be specific about the gap and its impact on search visibility."' if competitors else ''}
}}

Be brutally honest. Reference specific numbers. This is a sales tool — show the prospect exactly what they're losing by not fixing these issues."""

    raw = await _call_claude(prompt, max_tokens=1024)
    if not raw:
        return "", []

    # Parse JSON from response
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            summary = data.get("summary", "")
            recs = data.get("recommendations", [])
            # Append competitor insights to summary if present
            comp_insights = data.get("competitor_insights", "")
            if comp_insights:
                summary += f"\n\nCompetitor Gap: {comp_insights}"
            return summary, recs
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("Failed to parse Claude JSON: %s", exc)

    return raw[:500], []


# ── Main Audit Function ──────────────────────────────────────────────────

def _score_to_grade(score: int) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def _finding_to_dict(f: Finding) -> dict:
    return {
        "category": f.category,
        "metric": f.metric,
        "status": f.status,
        "score": f.score,
        "finding": f.finding,
        "recommendation": f.recommendation,
        "impact": f.impact,
    }


async def run_deep_audit(
    url: str,
    industry: str = "",
    competitor_urls: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run a comprehensive deep website audit with AI analysis.

    Args:
        url: Website URL to audit.
        industry: Business category/industry for context.
        competitor_urls: Optional list of {"url": "...", "name": "..."} for comparison.

    Returns:
        Full audit result as a dict (stored in deep_audit_results JSONB).
    """
    import datetime

    start_time = time.monotonic()

    # 1. Extract site data
    logger.info("Deep audit: extracting data from %s", url)
    ext = await extract_site_data(url)

    if ext.error and ext.status_code == 0:
        return {
            "url": url,
            "overall_score": 0,
            "overall_grade": "F",
            "audited_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "error": ext.error,
            "categories": {},
            "findings": [],
            "ai_summary": "",
            "ai_recommendations": [],
            "competitor_analysis": [],
            "competitor_comparison": {},
        }

    # 2. Score each category
    logger.info("Deep audit: scoring categories for %s", url)
    categories = {}
    all_findings: list[Finding] = []

    scorers = {
        "technical_seo": _score_technical_seo,
        "content_quality": _score_content_quality,
        "local_seo": _score_local_seo,
        "onpage_seo": _score_onpage_seo,
        "ai_readiness": _score_ai_readiness,
    }

    for cat_name, scorer in scorers.items():
        score, findings = scorer(ext)
        weight = CATEGORY_WEIGHTS[cat_name]
        categories[cat_name] = {
            "score": score,
            "weight": weight,
            "weighted_score": round(score * weight, 1),
            "findings": [_finding_to_dict(f) for f in findings],
        }
        all_findings.extend(findings)

    # Overall score (weighted)
    overall_score = int(sum(c["weighted_score"] for c in categories.values()))
    overall_grade = _score_to_grade(overall_score)

    # 3. Competitor analysis (parallel)
    competitors: list[CompetitorSnapshot] = []
    if competitor_urls:
        logger.info("Deep audit: analyzing %d competitors", len(competitor_urls))
        tasks = [
            extract_competitor_snapshot(c["url"], c.get("name", ""))
            for c in competitor_urls[:3]  # max 3 competitors
        ]
        competitors = await asyncio.gather(*tasks)
        competitors = [c for c in competitors if not c.error]

    # Build comparison table data
    comparison = {}
    if competitors:
        comparison = {
            "client": {
                "name": ext.title or urlparse(url).netloc,
                "url": url,
                "word_count": ext.word_count,
                "pages": len(ext.internal_page_urls) + 1,
                "has_blog": ext.has_blog_link,
                "blog_post_count": 0,
                "schema_types": ext.schema_types,
                "social_link_count": len(ext.social_links),
                "has_review_widget": ext.has_review_widget or ext.has_testimonials,
                "has_google_maps": ext.has_google_maps,
                "has_faq": ext.has_faq,
            },
            "competitors": [
                {
                    "name": c.business_name or urlparse(c.url).netloc,
                    "url": c.url,
                    "word_count": c.word_count,
                    "pages": c.pages_found,
                    "has_blog": c.has_blog,
                    "blog_post_count": c.blog_post_count,
                    "schema_types": c.schema_types,
                    "social_link_count": c.social_link_count,
                    "has_review_widget": c.has_review_widget or c.has_testimonials,
                    "has_google_maps": c.has_google_maps,
                    "has_faq": c.has_faq,
                }
                for c in competitors
            ],
        }

    # 4. AI analysis
    logger.info("Deep audit: running AI analysis for %s", url)
    ai_summary, ai_recommendations = await _ai_analyze(ext, categories, competitors, industry)

    duration = time.monotonic() - start_time

    result = {
        "url": url,
        "overall_score": overall_score,
        "overall_grade": overall_grade,
        "audited_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "duration_seconds": round(duration, 1),
        "categories": categories,
        "findings": [_finding_to_dict(f) for f in all_findings],
        "ai_summary": ai_summary,
        "ai_recommendations": ai_recommendations,
        "competitor_analysis": [
            {
                "url": c.url,
                "name": c.business_name,
                "word_count": c.word_count,
                "pages": c.pages_found,
                "has_blog": c.has_blog,
                "blog_post_count": c.blog_post_count,
                "schema_types": c.schema_types,
                "social_link_count": c.social_link_count,
                "has_review_widget": c.has_review_widget or c.has_testimonials,
                "has_google_maps": c.has_google_maps,
                "has_faq": c.has_faq,
            }
            for c in competitors
        ],
        "competitor_comparison": comparison,
        "extraction": {
            "word_count": ext.word_count,
            "pages_crawled": ext.pages_crawled,
            "internal_pages_found": len(ext.internal_page_urls),
            "html_size_bytes": ext.html_size_bytes,
            "load_time_ms": ext.load_time_ms,
            "has_ssl": ext.is_https,
            "has_robots_txt": ext.has_robots_txt,
            "has_sitemap": ext.has_sitemap,
            "schema_types": ext.schema_types,
            "social_links": ext.social_links,
            "images_total": ext.images_total,
            "images_without_alt": ext.images_without_alt,
            "forms_count": ext.forms_count,
            "has_faq": ext.has_faq,
            "has_blog": ext.has_blog_link,
            "cta_found": ext.cta_found,
        },
    }

    logger.info(
        "Deep audit complete for %s: score=%d grade=%s duration=%.1fs",
        url, overall_score, overall_grade, duration,
    )

    return result
