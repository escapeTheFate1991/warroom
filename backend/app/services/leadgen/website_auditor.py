"""Website auditor for scoring website quality and identifying improvement opportunities."""

import asyncio
import logging
import re
import ssl
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
SOCIAL_PATTERNS = {
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._\-]+/?"),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._\-]+/?"),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9._\-]+/?"),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9._\-]+/?"),
}


@dataclass
class WebsiteAudit:
    url: str
    score: int = 0
    grade: str = "F"
    summary: str = ""
    top_fixes: list[str] = None
    
    # Audit details
    has_ssl: bool = False
    has_email: bool = False
    has_phone: bool = False
    has_meta_description: bool = False
    has_viewport: bool = False
    has_socials: int = 0
    page_title_length: int = 0
    meta_description_length: int = 0
    
    def __post_init__(self):
        if self.top_fixes is None:
            self.top_fixes = []


async def audit_website(url: str) -> WebsiteAudit:
    """Audit a website and return a score with improvement recommendations."""
    audit = WebsiteAudit(url=url)
    
    try:
        # Check SSL and fetch content
        parsed = urlparse(url)
        audit.has_ssl = parsed.scheme == "https"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, follow_redirects=True)
            
            if response.status_code != 200:
                audit.summary = f"Website returned status {response.status_code}"
                return audit
            
            content = response.text
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for email
            audit.has_email = bool(EMAIL_PATTERN.search(content))
            
            # Check for phone
            audit.has_phone = bool(PHONE_PATTERN.search(content))
            
            # Check meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                audit.has_meta_description = True
                audit.meta_description_length = len(meta_desc["content"])
            
            # Check viewport meta tag
            viewport = soup.find("meta", attrs={"name": "viewport"})
            audit.has_viewport = bool(viewport)
            
            # Check page title
            title = soup.find("title")
            if title:
                audit.page_title_length = len(title.text.strip())
            
            # Count social links
            for platform, pattern in SOCIAL_PATTERNS.items():
                if pattern.search(content):
                    audit.has_socials += 1
            
            # Calculate score
            audit.score = _calculate_audit_score(audit)
            audit.grade = _score_to_grade(audit.score)
            audit.summary = _generate_summary(audit)
            audit.top_fixes = _generate_top_fixes(audit)
            
    except Exception as exc:
        logger.error("Website audit failed for %s: %s", url, exc)
        audit.summary = f"Audit failed: {str(exc)}"
        audit.score = 0
        audit.grade = "F"
    
    return audit


def _calculate_audit_score(audit: WebsiteAudit) -> int:
    """Calculate audit score based on best practices."""
    score = 0
    
    # SSL (critical)
    if audit.has_ssl:
        score += 25
    
    # Contact info (very important for local business)
    if audit.has_email:
        score += 20
    if audit.has_phone:
        score += 15
    
    # SEO basics
    if audit.has_meta_description:
        score += 10
        if 120 <= audit.meta_description_length <= 160:
            score += 5  # Optimal length
    
    if 30 <= audit.page_title_length <= 60:
        score += 10  # Good title length
    
    # Mobile responsiveness
    if audit.has_viewport:
        score += 10
    
    # Social presence
    if audit.has_socials >= 2:
        score += 5
    
    return min(score, 100)


def _score_to_grade(score: int) -> str:
    """Convert numeric score to letter grade."""
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


def _generate_summary(audit: WebsiteAudit) -> str:
    """Generate human-readable audit summary."""
    issues = []
    
    if not audit.has_ssl:
        issues.append("no SSL certificate")
    if not audit.has_email:
        issues.append("no email contact")
    if not audit.has_phone:
        issues.append("no phone number")
    if not audit.has_meta_description:
        issues.append("missing meta description")
    if not audit.has_viewport:
        issues.append("not mobile-optimized")
    if audit.has_socials == 0:
        issues.append("no social media links")
    
    if not issues:
        return "Website follows most best practices"
    
    return f"Issues found: {', '.join(issues)}"


def _generate_top_fixes(audit: WebsiteAudit) -> list[str]:
    """Generate prioritized list of fixes."""
    fixes = []
    
    if not audit.has_ssl:
        fixes.append("Install SSL certificate (critical for trust and SEO)")
    
    if not audit.has_email:
        fixes.append("Add contact email address to website")
    
    if not audit.has_phone:
        fixes.append("Display phone number prominently")
    
    if not audit.has_viewport:
        fixes.append("Add viewport meta tag for mobile optimization")
    
    if not audit.has_meta_description:
        fixes.append("Add meta description for better search results")
    
    if audit.has_socials == 0:
        fixes.append("Link to social media profiles")
    
    if audit.page_title_length > 60:
        fixes.append("Shorten page title for better SEO")
    
    return fixes[:5]  # Top 5 most important