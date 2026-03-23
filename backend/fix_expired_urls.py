#!/usr/bin/env python3
"""Quick fix for expired Instagram CDN URLs."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

# Set required env vars
os.environ['PYTHONPATH'] = '/home/eddy/Development/warroom/backend'

async def main():
    """Fix expired Instagram CDN URLs."""
    try:
        from sqlalchemy import text
        from app.db.crm_db import crm_session
        from app.services.instagram_scraper import scrape_profile
        
        print("🔄 Fixing expired Instagram CDN URLs...")
        
        async with crm_session() as db:
            await db.execute(text('SET search_path TO crm, public'))
            
            # Get competitors with expired URLs (limit to top 5 to avoid overwhelming Instagram)
            result = await db.execute(
                text('''
                    SELECT DISTINCT c.handle, COUNT(*) as expired_count
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE c.platform = 'instagram'
                      AND cp.media_url LIKE '%scontent%cdninstagram%'
                      AND cp.posted_at < NOW() - INTERVAL '24 hours'
                    GROUP BY c.handle
                    ORDER BY expired_count DESC
                    LIMIT 5
                ''')
            )
            competitors = result.fetchall()
            
            if not competitors:
                print("✅ No competitors with expired URLs found!")
                return
            
            print(f"🎯 Found {len(competitors)} competitors with expired URLs")
            total_updated = 0
            
            for handle, count in competitors:
                print(f"\n🔄 Processing @{handle} ({count} expired URLs)...")
                
                try:
                    # Re-scrape the profile
                    profile = await scrape_profile(handle)
                    
                    if profile.error:
                        print(f"   ❌ Failed: {profile.error}")
                        continue
                    
                    if not profile.posts:
                        print(f"   ⚠️  No posts found")
                        continue
                    
                    print(f"   ✅ Scraped {len(profile.posts)} posts")
                    
                    # Get posts that need updating
                    posts_result = await db.execute(
                        text('''
                            SELECT cp.id, cp.shortcode, cp.post_url
                            FROM crm.competitor_posts cp
                            JOIN crm.competitors c ON cp.competitor_id = c.id
                            WHERE c.handle = :handle
                              AND c.platform = 'instagram'
                              AND cp.media_url LIKE '%scontent%cdninstagram%'
                              AND cp.posted_at < NOW() - INTERVAL '24 hours'
                        '''),
                        {"handle": handle}
                    )
                    existing_posts = posts_result.fetchall()
                    
                    # Create lookup by shortcode
                    scraped_lookup = {}
                    for post in profile.posts:
                        if post.shortcode:
                            scraped_lookup[post.shortcode] = post
                        if post.post_url:
                            scraped_lookup[post.post_url] = post
                    
                    updated_count = 0
                    for post_id, shortcode, post_url in existing_posts:
                        # Find matching fresh post
                        fresh_post = None
                        if shortcode and shortcode in scraped_lookup:
                            fresh_post = scraped_lookup[shortcode]
                        elif post_url and post_url in scraped_lookup:
                            fresh_post = scraped_lookup[post_url]
                        
                        if fresh_post and fresh_post.media_url:
                            # Update the URLs
                            await db.execute(
                                text('''
                                    UPDATE crm.competitor_posts 
                                    SET media_url = :media_url, 
                                        thumbnail_url = :thumbnail_url
                                    WHERE id = :id
                                '''),
                                {
                                    "id": post_id,
                                    "media_url": fresh_post.media_url,
                                    "thumbnail_url": fresh_post.thumbnail_url,
                                }
                            )
                            updated_count += 1
                    
                    await db.commit()
                    total_updated += updated_count
                    print(f"   ✅ Updated {updated_count} URLs")
                    
                    # Small delay to be nice to Instagram
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    continue
            
            print(f"\n🎉 Refresh complete! Updated {total_updated} URLs")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())