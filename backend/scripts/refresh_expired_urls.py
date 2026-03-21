#!/usr/bin/env python3
"""One-time URL refresh script for expired Instagram CDN media URLs.

This script:
1. Queries all posts where media_url contains 'scontent%cdninstagram'
2. For each competitor, re-scrapes their recent posts from Instagram
3. Matches by shortcode or post_url and updates the media_url and thumbnail_url
4. Logs how many URLs were refreshed

Usage:
    docker exec warroom-backend-1 python3 /app/scripts/refresh_expired_urls.py

WARNING: This makes direct requests to Instagram. Use sparingly.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.crm_db import crm_session
from app.services.instagram_scraper import scrape_profile
from app.models.crm.competitor import Competitor


async def get_expired_posts(db):
    """Get posts with expired Instagram CDN URLs."""
    result = await db.execute(
        text("""
            SELECT DISTINCT cp.id, cp.competitor_id, cp.media_url, cp.thumbnail_url, 
                   cp.shortcode, cp.post_url, cp.posted_at, c.handle, c.org_id
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE c.platform = 'instagram'
              AND (cp.media_url LIKE '%scontent%cdninstagram%' 
                   OR cp.thumbnail_url LIKE '%scontent%cdninstagram%')
              AND cp.posted_at < NOW() - INTERVAL '24 hours'
            ORDER BY c.handle, cp.posted_at DESC
        """)
    )
    return result.fetchall()


async def refresh_competitor_urls(db, handle: str, post_ids: List[int]) -> Dict[str, Any]:
    """Refresh URLs for a single competitor by re-scraping their profile."""
    try:
        print(f"  Re-scraping @{handle}...")
        profile = await scrape_profile(handle)
        
        if profile.error:
            print(f"    ❌ Failed to scrape @{handle}: {profile.error}")
            return {"success": False, "error": profile.error, "updated": 0}
        
        if not profile.posts:
            print(f"    ⚠️  No posts found for @{handle}")
            return {"success": False, "error": "No posts found", "updated": 0}
        
        # Create lookup by shortcode and post_url
        scraped_lookup = {}
        for post in profile.posts:
            if post.shortcode:
                scraped_lookup[post.shortcode] = post
            if post.post_url:
                scraped_lookup[post.post_url] = post
        
        updated_count = 0
        for post_id in post_ids:
            # Get existing post data
            result = await db.execute(
                text("SELECT shortcode, post_url FROM crm.competitor_posts WHERE id = :id"),
                {"id": post_id}
            )
            existing = result.fetchone()
            if not existing:
                continue
                
            shortcode, post_url = existing
            
            # Find matching scraped post
            fresh_post = None
            if shortcode and shortcode in scraped_lookup:
                fresh_post = scraped_lookup[shortcode]
            elif post_url and post_url in scraped_lookup:
                fresh_post = scraped_lookup[post_url]
            
            if fresh_post and fresh_post.media_url:
                # Update the URLs
                await db.execute(
                    text("""
                        UPDATE crm.competitor_posts 
                        SET media_url = :media_url, 
                            thumbnail_url = :thumbnail_url, 
                            fetched_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": post_id,
                        "media_url": fresh_post.media_url,
                        "thumbnail_url": fresh_post.thumbnail_url,
                    }
                )
                updated_count += 1
                print(f"    ✓ Updated post {post_id}")
        
        return {"success": True, "updated": updated_count}
        
    except Exception as e:
        print(f"    ❌ Error refreshing @{handle}: {e}")
        return {"success": False, "error": str(e), "updated": 0}


async def main():
    """Main script execution."""
    print("🔄 Starting expired URL refresh...")
    
    async with crm_session() as db:
        # Set search path
        await db.execute(text("SET search_path TO crm, public"))
        
        # Get all expired posts
        print("📋 Finding expired Instagram CDN URLs...")
        expired_posts = await get_expired_posts(db)
        
        if not expired_posts:
            print("✅ No expired URLs found!")
            return
        
        print(f"🔍 Found {len(expired_posts)} posts with expired URLs")
        
        # Group by competitor handle
        competitor_posts: Dict[str, List[int]] = {}
        for row in expired_posts:
            handle = row[7]  # handle column
            post_id = row[0]  # id column
            if handle not in competitor_posts:
                competitor_posts[handle] = []
            competitor_posts[handle].append(post_id)
        
        print(f"🎯 Need to refresh {len(competitor_posts)} competitors")
        
        # Refresh each competitor
        total_updated = 0
        total_failed = 0
        
        for handle, post_ids in competitor_posts.items():
            print(f"\n🔄 Processing @{handle} ({len(post_ids)} posts)...")
            
            result = await refresh_competitor_urls(db, handle, post_ids)
            
            if result["success"]:
                total_updated += result["updated"]
                print(f"  ✅ Refreshed {result['updated']}/{len(post_ids)} URLs")
            else:
                total_failed += len(post_ids)
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
            
            # Be nice to Instagram - small delay between competitors
            await asyncio.sleep(2)
        
        # Commit all changes
        await db.commit()
        
        print(f"\n🎉 Refresh complete!")
        print(f"   ✅ Updated: {total_updated} URLs")
        print(f"   ❌ Failed: {total_failed} URLs")
        print(f"   🏆 Success rate: {(total_updated / (total_updated + total_failed) * 100):.1f}%")


if __name__ == "__main__":
    asyncio.run(main())