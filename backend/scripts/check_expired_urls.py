#!/usr/bin/env python3
"""Quick check for expired Instagram CDN URLs."""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.crm_db import crm_session


async def main():
    """Check for expired URLs."""
    print("🔍 Checking for expired Instagram CDN URLs...")
    
    async with crm_session() as db:
        # Set search path
        await db.execute(text("SET search_path TO crm, public"))
        
        # Check total posts with Instagram CDN URLs
        result = await db.execute(
            text("""
                SELECT COUNT(*) as total_posts
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE c.platform = 'instagram'
                  AND (cp.media_url LIKE '%scontent%cdninstagram%' 
                       OR cp.thumbnail_url LIKE '%scontent%cdninstagram%')
            """)
        )
        total = result.scalar()
        print(f"📊 Total posts with Instagram CDN URLs: {total}")
        
        # Check posts older than 24 hours (likely expired)
        result = await db.execute(
            text("""
                SELECT COUNT(*) as expired_posts
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE c.platform = 'instagram'
                  AND (cp.media_url LIKE '%scontent%cdninstagram%' 
                       OR cp.thumbnail_url LIKE '%scontent%cdninstagram%')
                  AND cp.posted_at < NOW() - INTERVAL '24 hours'
            """)
        )
        expired = result.scalar()
        print(f"⏰ Posts older than 24 hours (likely expired): {expired}")
        
        # Show some examples
        result = await db.execute(
            text("""
                SELECT cp.id, cp.media_url, cp.posted_at, c.handle
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE c.platform = 'instagram'
                  AND cp.media_url LIKE '%scontent%cdninstagram%'
                  AND cp.posted_at < NOW() - INTERVAL '24 hours'
                ORDER BY cp.posted_at DESC
                LIMIT 5
            """)
        )
        examples = result.fetchall()
        
        if examples:
            print(f"\n🎯 Sample expired URLs:")
            for row in examples:
                print(f"  Post {row[0]} (@{row[3]}): {row[1][:60]}... ({row[2]})")
        else:
            print("✨ No expired URLs found!")


if __name__ == "__main__":
    asyncio.run(main())