"""Scraping utility — ALL web scraping MUST go through this module.

RULE: Never use raw httpx/requests/beautifulsoup for scraping websites.
Always use scrapling first. It handles anti-bot, Cloudflare, dynamic pages,
and adaptive element tracking out of the box.

Usage:
    from app.services.scraping import fetch_page, fetch_stealthy, fetch_dynamic

    # Simple fetch (fast, no JS rendering)
    page = await fetch_page("https://example.com")
    titles = page.css("h1::text").getall()

    # Stealthy fetch (bypasses Cloudflare, anti-bot)
    page = await fetch_stealthy("https://example.com")

    # Dynamic fetch (full browser, JS rendering)
    page = await fetch_dynamic("https://example.com")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy imports — scrapling is heavy, only load when needed
_fetcher = None
_async_fetcher = None


def _get_fetcher():
    """Lazy-load Scrapling Fetcher."""
    global _fetcher
    if _fetcher is None:
        from scrapling.fetchers import Fetcher
        _fetcher = Fetcher
    return _fetcher


def _get_async_fetcher():
    """Lazy-load Scrapling AsyncFetcher."""
    global _async_fetcher
    if _async_fetcher is None:
        from scrapling.fetchers import AsyncFetcher
        _async_fetcher = AsyncFetcher
    return _async_fetcher


async def fetch_page(
    url: str,
    *,
    timeout: int = 30,
    headers: Optional[dict] = None,
    proxy: Optional[str] = None,
) -> object:
    """Fetch a page using Scrapling's async fetcher.
    
    Returns a Scrapling Adaptor with CSS/XPath selection, text extraction, etc.
    This is the default — use for most scraping tasks.
    """
    AsyncFetcher = _get_async_fetcher()
    kwargs = {"timeout": timeout}
    if headers:
        kwargs["headers"] = headers
    if proxy:
        kwargs["proxy"] = proxy

    try:
        page = await AsyncFetcher.fetch(url, **kwargs)
        return page
    except Exception as exc:
        logger.warning("Scrapling fetch failed for %s: %s", url, exc)
        raise


def fetch_page_sync(
    url: str,
    *,
    timeout: int = 30,
    headers: Optional[dict] = None,
) -> object:
    """Synchronous fetch using Scrapling's Fetcher.
    
    Use when you can't use async (rare — prefer fetch_page).
    """
    Fetcher = _get_fetcher()
    kwargs = {"timeout": timeout}
    if headers:
        kwargs["headers"] = headers

    try:
        page = Fetcher.fetch(url, **kwargs)
        return page
    except Exception as exc:
        logger.warning("Scrapling sync fetch failed for %s: %s", url, exc)
        raise


async def fetch_stealthy(
    url: str,
    *,
    headless: bool = True,
    network_idle: bool = True,
    timeout: int = 30,
) -> object:
    """Fetch using Scrapling's StealthyFetcher — bypasses Cloudflare/anti-bot.
    
    Use for sites that block regular requests (Yelp, Glassdoor, etc.).
    Requires playwright browsers installed.
    """
    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch(
            url,
            headless=headless,
            network_idle=network_idle,
        )
        return page
    except ImportError:
        logger.warning("StealthyFetcher not available — falling back to regular fetch")
        return await fetch_page(url, timeout=timeout)
    except Exception as exc:
        logger.warning("Stealthy fetch failed for %s: %s", url, exc)
        raise


async def fetch_dynamic(
    url: str,
    *,
    headless: bool = True,
    timeout: int = 30,
) -> object:
    """Fetch using Scrapling's DynamicFetcher — full browser with JS rendering.
    
    Use for SPAs and pages that render content with JavaScript.
    Requires playwright browsers installed.
    """
    try:
        from scrapling.fetchers import DynamicFetcher
        page = DynamicFetcher.fetch(
            url,
            headless=headless,
        )
        return page
    except ImportError:
        logger.warning("DynamicFetcher not available — falling back to regular fetch")
        return await fetch_page(url, timeout=timeout)
    except Exception as exc:
        logger.warning("Dynamic fetch failed for %s: %s", url, exc)
        raise


def extract_text(page, selector: str) -> str:
    """Extract text from a CSS selector, handling None gracefully."""
    try:
        result = page.css(selector)
        if result:
            return result.get_text() if hasattr(result, 'get_text') else str(result)
    except Exception:
        pass
    return ""


def extract_all_text(page, selector: str) -> list[str]:
    """Extract all text matches from a CSS selector."""
    try:
        results = page.css(selector)
        if results:
            return [r.text for r in results if hasattr(r, 'text')]
    except Exception:
        pass
    return []
