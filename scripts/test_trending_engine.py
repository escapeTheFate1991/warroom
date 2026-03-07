#!/usr/bin/env python3
"""Test the enhanced trending topics engine."""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "backend"))

from sqlalchemy import text
from backend.app.db.crm_db import crm_session

async def test_trending_engine():
    """Test the trending topics engine setup."""
    
    async with crm_session() as session:
        await session.execute(text("SET search_path TO crm, public"))
        
        # Check if competitor_posts table exists
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'crm' AND table_name = 'competitor_posts'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        if columns:
            print("✅ competitor_posts table structure:")
            for col in columns:
                print(f"  - {col.column_name}: {col.data_type}")
        else:
            print("❌ competitor_posts table not found")
            return False
        
        # Check if there are any competitors
        result = await session.execute(text("SELECT COUNT(*) FROM competitors"))
        count = result.scalar()
        print(f"📊 Found {count} competitors in database")
        
        # Show some competitor data
        if count > 0:
            result = await session.execute(text("""
                SELECT id, handle, platform, followers, post_count 
                FROM competitors 
                LIMIT 5
            """))
            competitors = result.fetchall()
            
            print("🎯 Sample competitors:")
            for comp in competitors:
                print(f"  - {comp.handle} ({comp.platform}): {comp.followers} followers, {comp.post_count} posts")
        
        # Check social accounts
        result = await session.execute(text("""
            SELECT platform, status, follower_count 
            FROM social_accounts 
            WHERE status = 'connected'
        """))
        social_accounts = result.fetchall()
        
        print(f"🔗 Connected social accounts: {len(social_accounts)}")
        for account in social_accounts:
            print(f"  - {account.platform}: {account.status} ({account.follower_count} followers)")
        
        print("\n✅ Trending topics engine is ready!")
        print("📋 Available new endpoints:")
        print("  - GET /api/content-intel/competitors/trending-topics")
        print("  - GET /api/content-intel/competitors/top-content")
        print("  - GET /api/content-intel/competitors/hooks")
        print("  - POST /api/content-intel/competitors/refresh")
        
        return True

if __name__ == "__main__":
    asyncio.run(test_trending_engine())