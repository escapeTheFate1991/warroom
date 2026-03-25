#!/usr/bin/env python3
"""
Build Master Taxonomy from existing War Room comment data.

This script:
1. Extracts comment data from the database (posts with 10+ comments)
2. Scrapes fresh comments for each post via the scraper service
3. Sends all comments to the ML pipeline's taxonomy builder
4. Saves the resulting Master Taxonomy
5. Re-analyzes all posts with the new taxonomy

Usage (from backend container):
    docker exec warroom-backend-1 python3 /app/scripts/build_taxonomy.py
"""
import asyncio
import httpx
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

SCRAPER_URL = "http://localhost:18797"
ML_URL = "http://localhost:18798"
DB_URL = "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"

async def main():
    print("🏗️ Building Master Taxonomy from War Room comment data...\n")
    
    # 1. Get top 100 posts with most comments (we want quality data for taxonomy)
    print("1️⃣ Fetching posts with comments from database...")
    engine = create_async_engine(DB_URL)
    async with AsyncSession(engine) as db:
        await db.execute(text("SET search_path TO crm, public"))
        result = await db.execute(text("""
            SELECT cp.id, cp.shortcode, cp.post_text, cp.comments
            FROM crm.competitor_posts cp
            WHERE cp.shortcode IS NOT NULL AND cp.comments > 10
            ORDER BY cp.comments DESC
            LIMIT 100
        """))
        posts = result.fetchall()
    await engine.dispose()
    
    print(f"   Found {len(posts)} posts with 10+ comments")
    if not posts:
        print("❌ No posts found with sufficient comment data. Exiting.")
        return
    
    # 2. Scrape comments for each post (rate limited)
    print("\n2️⃣ Scraping fresh comments from Instagram...")
    comments_by_post = {}
    total_comments = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, (post_id, shortcode, caption, comment_count) in enumerate(posts, 1):
            try:
                print(f"   [{i:3d}/{len(posts)}] {shortcode} ({comment_count} comments)...", end="")
                resp = await client.post(f"{SCRAPER_URL}/scrape-comments", 
                    json={"shortcode": shortcode, "limit": 50})
                
                if resp.status_code == 200:
                    comments = resp.json().get("comments", [])
                    if len(comments) >= 3:
                        comments_by_post[post_id] = comments
                        total_comments += len(comments)
                        print(f" ✅ {len(comments)} comments")
                    else:
                        print(f" ⏭️ only {len(comments)} comments (skipped)")
                else:
                    print(f" ❌ HTTP {resp.status_code}")
                
                # Rate limit: 3 seconds between requests
                await asyncio.sleep(3)
            except Exception as e:
                print(f" ❌ Error: {e}")
                continue
    
    print(f"\n   Collected {total_comments:,} comments from {len(comments_by_post)} posts")
    
    if not comments_by_post:
        print("❌ No comment data collected. Cannot build taxonomy. Exiting.")
        return
    
    # 3. Send to taxonomy builder
    print("\n3️⃣ Building taxonomy from comments...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(f"{ML_URL}/taxonomy/build",
                json={"comments_by_post": {str(k): v for k, v in comments_by_post.items()}})
            
            if resp.status_code == 200:
                taxonomy = resp.json()
                print(f"   🎯 Taxonomy built successfully!")
                print(f"   Categories: {len(taxonomy.get('categories', []))}")
                
                for cat in taxonomy.get("categories", []):
                    subs = len(cat.get("sub_topics", []))
                    sub_text = f" [+{subs} sub-topics]" if subs else ""
                    print(f"     - {cat['label']} ({cat['safety_label']}){sub_text}")
                
                # Save locally
                taxonomy_file = "/tmp/master_taxonomy.json"
                with open(taxonomy_file, "w") as f:
                    json.dump(taxonomy, f, indent=2)
                print(f"\n   📄 Saved to {taxonomy_file}")
                
            else:
                print(f"❌ Taxonomy build failed: HTTP {resp.status_code}")
                print(f"   Response: {resp.text[:200]}...")
                return
                
        except Exception as e:
            print(f"❌ Failed to connect to ML pipeline: {e}")
            return
    
    # 4. Re-analyze all posts with the new taxonomy
    print("\n4️⃣ Re-analyzing posts with new taxonomy...")
    engine = create_async_engine(DB_URL)
    success = 0
    total = len(comments_by_post)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, (post_id, comments) in enumerate(comments_by_post.items(), 1):
            try:
                print(f"   [{i:3d}/{total}] Analyzing post {post_id}...", end="")
                
                # Get caption from database for context
                async with AsyncSession(engine) as db:
                    await db.execute(text("SET search_path TO crm, public"))
                    caption_result = await db.execute(text(
                        "SELECT post_text FROM crm.competitor_posts WHERE id = :id"
                    ), {"id": int(post_id)})
                    caption_row = caption_result.fetchone()
                    caption = caption_row[0] if caption_row else ""
                
                # Analyze comments with taxonomy
                resp = await client.post(f"{ML_URL}/analyze-comments",
                    json={"comments": comments, "post_caption": caption})
                
                if resp.status_code == 200:
                    analysis = resp.json()
                    
                    # Store analysis in DB
                    async with AsyncSession(engine) as db:
                        await db.execute(text("SET search_path TO crm, public"))
                        await db.execute(text(
                            "UPDATE crm.competitor_posts SET comments_data = :data WHERE id = :id"
                        ), {"data": json.dumps(analysis), "id": int(post_id)})
                        await db.commit()
                    
                    success += 1
                    print(" ✅")
                else:
                    print(f" ❌ HTTP {resp.status_code}")
                    
            except Exception as e:
                print(f" ❌ Error: {e}")
                continue
    
    await engine.dispose()
    
    # Final summary
    print(f"\n🎉 Taxonomy build complete!")
    print(f"   📊 Posts processed: {success}/{total}")
    print(f"   💬 Total comments analyzed: {total_comments:,}")
    print(f"   📄 Taxonomy saved: /tmp/master_taxonomy.json")
    print(f"   🔄 Database updated with {success} re-analyzed posts")

if __name__ == "__main__":
    asyncio.run(main())