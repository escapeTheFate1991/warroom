#!/usr/bin/env python3
"""
Test version of taxonomy builder with smaller sample and forced output flushing.
"""
import asyncio
import httpx
import json
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

SCRAPER_URL = "http://localhost:18797"
ML_URL = "http://localhost:18798"
DB_URL = "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"

def log(msg):
    """Print with forced flush."""
    print(msg)
    sys.stdout.flush()

async def main():
    log("🏗️ Testing taxonomy builder with small sample...\n")
    
    # 1. Get just 5 posts for testing
    log("1️⃣ Fetching 5 posts with comments...")
    engine = create_async_engine(DB_URL)
    async with AsyncSession(engine) as db:
        await db.execute(text("SET search_path TO crm, public"))
        result = await db.execute(text("""
            SELECT cp.id, cp.shortcode, cp.post_text, cp.comments
            FROM crm.competitor_posts cp
            WHERE cp.shortcode IS NOT NULL AND cp.comments > 10
            ORDER BY cp.comments DESC
            LIMIT 5
        """))
        posts = result.fetchall()
    await engine.dispose()
    
    log(f"   Found {len(posts)} posts")
    
    # 2. Try to scrape one post to test
    log("\n2️⃣ Testing comment scraping...")
    if posts:
        post_id, shortcode, caption, comment_count = posts[0]
        log(f"   Testing with {shortcode} ({comment_count} comments)")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{SCRAPER_URL}/scrape-comments", 
                    json={"shortcode": shortcode, "limit": 10})
                
                if resp.status_code == 200:
                    comments = resp.json().get("comments", [])
                    log(f"   ✅ Got {len(comments)} comments")
                    
                    # Test taxonomy builder
                    log("\n3️⃣ Testing taxonomy builder...")
                    test_data = {str(post_id): comments[:5]}  # Just 5 comments for test
                    
                    resp = await client.post(f"{ML_URL}/taxonomy/build",
                        json={"comments_by_post": test_data})
                    
                    if resp.status_code == 200:
                        taxonomy = resp.json()
                        log(f"   ✅ Taxonomy built! Categories: {len(taxonomy.get('categories', []))}")
                        
                        # Save test taxonomy
                        with open("/tmp/test_taxonomy.json", "w") as f:
                            json.dump(taxonomy, f, indent=2)
                        log("   📄 Saved to /tmp/test_taxonomy.json")
                    else:
                        log(f"   ❌ Taxonomy build failed: {resp.status_code}")
                        log(f"   Response: {resp.text}")
                else:
                    log(f"   ❌ Scraping failed: {resp.status_code}")
                    log(f"   Response: {resp.text}")
        except Exception as e:
            log(f"   ❌ Error: {e}")
    
    log("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(main())