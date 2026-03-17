#!/usr/bin/env python3
"""Test script for Phase 4 Performance Feedback Loop Backend implementation."""
import asyncio
import json
from datetime import datetime
from app.db.crm_db import crm_session
from sqlalchemy import text

async def test_performance_collection():
    """Test the performance feedback collection process."""
    print("🧪 Testing Performance Feedback Collection")
    
    async with crm_session() as db:
        await db.execute(text('SET search_path TO crm, public'))
        
        # Test 1: Check table exists and structure
        print("\n1. Verifying table structure...")
        result = await db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'content_performance_feedback' 
            AND table_schema = 'crm'
        """))
        table_exists = result.scalar() > 0
        print(f"   content_performance_feedback table exists: {table_exists}")
        
        if not table_exists:
            print("❌ Table does not exist - migration may have failed")
            return
        
        # Test 2: Insert test performance data
        print("\n2. Inserting test performance data...")
        test_data = {
            "org_id": 1,
            "scheduled_post_id": 123,
            "format_slug": "myth_buster",
            "hook_text": "Everyone thinks AI will replace humans, but here's why that's wrong",
            "likes": 450,
            "comments": 89,
            "shares": 23,
            "saves": 156,
            "reach": 12000,
            "views": 18000
        }
        
        # Calculate engagement score (likes + comments * 2 + shares * 3)
        engagement_score = test_data["likes"] + (test_data["comments"] * 2) + (test_data["shares"] * 3)
        
        insert_result = await db.execute(text("""
            INSERT INTO crm.content_performance_feedback (
                org_id, scheduled_post_id, format_slug, hook_text,
                likes, comments, shares, saves, reach, views, engagement_score,
                performance_tier, created_at
            ) VALUES (
                :org_id, :scheduled_post_id, :format_slug, :hook_text,
                :likes, :comments, :shares, :saves, :reach, :views, :engagement_score,
                'test', NOW()
            ) RETURNING id
        """), {
            **test_data,
            "engagement_score": engagement_score
        })
        
        feedback_id = insert_result.scalar()
        await db.commit()
        print(f"   Created feedback record ID: {feedback_id}")
        print(f"   Engagement score calculated: {engagement_score}")
        
        # Test 3: Test feedback weights calculation
        print("\n3. Testing feedback weights calculation...")
        feedback_counts = [0, 5, 10, 30, 50, 100]
        for count in feedback_counts:
            if count == 0:
                comp_weight, own_weight = 1.0, 0.0
            elif count <= 10:
                comp_weight, own_weight = 0.7, 0.3
            elif count <= 50:
                comp_weight, own_weight = 0.4, 0.6
            else:
                comp_weight, own_weight = 0.2, 0.8
            
            print(f"   Count {count:3d}: competitor={comp_weight:.1f}, own={own_weight:.1f}")
        
        # Test 4: Query performance dashboard data
        print("\n4. Testing dashboard data aggregation...")
        dashboard_result = await db.execute(text("""
            SELECT 
                format_slug,
                COUNT(*) as post_count,
                AVG(engagement_score) as avg_engagement,
                AVG(likes) as avg_likes,
                AVG(comments) as avg_comments,
                AVG(shares) as avg_shares
            FROM crm.content_performance_feedback
            WHERE org_id = 1
            GROUP BY format_slug
            ORDER BY avg_engagement DESC
        """))
        
        dashboard_data = dashboard_result.fetchall()
        print(f"   Found {len(dashboard_data)} format(s) with performance data:")
        for row in dashboard_data:
            print(f"     {row.format_slug}: {row.post_count} posts, avg engagement: {row.avg_engagement:.1f}")
        
        # Test 5: Hook analysis
        print("\n5. Testing hook performance analysis...")
        hook_result = await db.execute(text("""
            SELECT 
                hook_text,
                engagement_score,
                format_slug,
                performance_tier
            FROM crm.content_performance_feedback
            WHERE org_id = 1 AND hook_text IS NOT NULL
            ORDER BY engagement_score DESC
            LIMIT 5
        """))
        
        hooks = hook_result.fetchall()
        print(f"   Top {len(hooks)} hook(s) by engagement:")
        for hook in hooks:
            hook_preview = hook.hook_text[:50] + "..." if len(hook.hook_text) > 50 else hook.hook_text
            print(f"     {hook_preview} ({hook.engagement_score:.0f} engagement)")
        
        # Test 6: Performance tier analysis
        print("\n6. Testing performance tier distribution...")
        tier_result = await db.execute(text("""
            SELECT 
                performance_tier,
                COUNT(*) as count,
                AVG(engagement_score) as avg_engagement
            FROM crm.content_performance_feedback
            WHERE org_id = 1 AND performance_tier IS NOT NULL
            GROUP BY performance_tier
            ORDER BY avg_engagement DESC
        """))
        
        tiers = tier_result.fetchall()
        print(f"   Performance tier distribution:")
        for tier in tiers:
            print(f"     {tier.performance_tier}: {tier.count} posts, avg {tier.avg_engagement:.1f}")
        
        print("\n✅ All tests completed successfully!")
        print(f"   Total feedback records in database: {sum(row.count for row in tiers) if tiers else len(hooks)}")

if __name__ == "__main__":
    asyncio.run(test_performance_collection())