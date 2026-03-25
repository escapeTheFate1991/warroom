#!/usr/bin/env python3
"""Test script for the scraper microservice."""

import asyncio
import json
from instagram_scraper import scrape_profile
from comment_scraper import scrape_post_comments

async def test_profile_scraping():
    """Test profile scraping functionality."""
    print("Testing profile scraping...")
    profile = await scrape_profile("instagram")  # Official Instagram account
    
    print(f"Handle: {profile.handle}")
    print(f"Followers: {profile.followers}")
    print(f"Posts: {len(profile.posts)}")
    print(f"Error: {profile.error}")
    
    if profile.posts:
        print(f"First post shortcode: {profile.posts[0].shortcode}")
    
    return profile.posts[0].shortcode if profile.posts else None

async def test_comment_scraping(shortcode):
    """Test comment scraping functionality."""
    if not shortcode:
        print("No shortcode available for comment testing")
        return
    
    print(f"Testing comment scraping for {shortcode}...")
    comments = await scrape_post_comments(shortcode, limit=10)
    
    print(f"Comments scraped: {len(comments)}")
    if comments:
        print(f"First comment: {comments[0]}")

async def main():
    print("🔍 Testing scraper microservice components...")
    
    # Test profile scraping
    shortcode = await test_profile_scraping()
    
    # Test comment scraping  
    await test_comment_scraping(shortcode)
    
    print("✅ Tests completed")

if __name__ == "__main__":
    asyncio.run(main())