#!/usr/bin/env python3
"""Test CDR Generator with real high-engagement posts."""

import asyncio
import json
from sqlalchemy import text
from app.db.crm_db import crm_session
from app.services.creator_directive import (
    CreatorDirectiveService, 
    get_post_data, 
    get_high_power_posts,
    mock_intent_classifier
)

async def test_cdr_generation():
    """Test CDR generation with real War Room data"""
    print("🎯 Testing CDR Generator with War Room data...")
    
    async with crm_session() as db:
        # First, find some high-engagement posts
        print("\n1. Finding high-engagement posts...")
        result = await db.execute(
            text("""
                SELECT 
                    cp.id,
                    cp.shortcode,
                    c.handle,
                    cp.likes,
                    cp.comments,
                    cp.shares,
                    cp.engagement_score,
                    cp.hook
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE cp.engagement_score > 100
                  AND cp.likes > 500
                  AND cp.content_analysis IS NOT NULL
                ORDER BY cp.engagement_score DESC
                LIMIT 5
            """)
        )
        
        posts = result.fetchall()
        if not posts:
            print("❌ No high-engagement posts found with content_analysis")
            return
            
        print(f"Found {len(posts)} high-engagement posts:")
        for post in posts:
            print(f"  • Post {post[0]} (@{post[2]}): {post[3]:,} likes, {post[4]:,} comments, engagement={post[6]:.1f}")
        
        # Test CDR generation on top 2 posts
        print(f"\n2. Testing CDR generation on top 2 posts...")
        
        cdr_service = CreatorDirectiveService()
        
        for i, post in enumerate(posts[:2]):
            post_id = post[0]
            handle = post[2]
            print(f"\n=== CDR Test #{i+1}: Post {post_id} (@{handle}) ===")
            
            try:
                # Get full post data
                post_data = await get_post_data(db, post_id)
                if not post_data:
                    print(f"❌ Could not retrieve post data for {post_id}")
                    continue
                
                print(f"Hook: \"{post_data.hook[:100]}...\"")
                print(f"Performance: {post_data.likes:,} likes, {post_data.comments:,} comments, {post_data.shares:,} shares")
                
                # Mock intent classification
                intent_scores = mock_intent_classifier(post_data.content_analysis)
                print(f"Intent scores: {intent_scores}")
                
                # Generate CDR
                cdr = await cdr_service.generate_cdr(post_data, intent_scores)
                
                if not cdr:
                    print(f"❌ CDR generation failed - below power score threshold")
                    continue
                
                print(f"✅ CDR Generated!")
                print(f"Power Score: {cdr.power_score:.0f}")
                print(f"Dominant Intent: {cdr.dominant_intent}")
                
                print(f"\n📝 HOOK DIRECTIVE:")
                print(f"  Visual: {cdr.hook_directive.visual}")
                print(f"  Script: {cdr.hook_directive.script_line}")
                print(f"  Reasoning: {cdr.hook_directive.reasoning}")
                
                print(f"\n🎬 RETENTION BLUEPRINT:")
                print(f"  Pacing Rules: {len(cdr.retention_blueprint.pacing_rules)} rules")
                for rule in cdr.retention_blueprint.pacing_rules[:2]:
                    print(f"    • {rule}")
                
                print(f"\n🔥 SHARE CATALYST:")
                print(f"  Vulnerability Frame: {cdr.share_catalyst.vulnerability_frame}")
                print(f"  Identity Moment: {cdr.share_catalyst.identity_moment}")
                print(f"  Timestamp: {cdr.share_catalyst.timestamp}")
                
                print(f"\n💰 CONVERSION CLOSE:")
                print(f"  CTA Type: {cdr.conversion_close.cta_type}")
                print(f"  Script Line: {cdr.conversion_close.script_line}")
                
                print(f"\n🎥 TECHNICAL SPECS:")
                print(f"  Lighting: {cdr.technical_specs.lighting}")
                print(f"  Video Length: {cdr.technical_specs.video_length}")
                print(f"  Music BPM: {cdr.technical_specs.music_bpm}")
                
                print(f"\n🤖 GENERATOR PROMPTS:")
                print(f"  Veo Prompt: {cdr.generator_prompts.veo_prompt[:150]}...")
                print(f"  Nano Banana: {cdr.generator_prompts.nano_banana_prompt[:150]}...")
                
                print(f"\n" + "="*80)
                
            except Exception as e:
                print(f"❌ CDR generation failed for post {post_id}: {e}")
                continue
        
        await cdr_service.close()
        print(f"\n✅ CDR testing completed!")

if __name__ == "__main__":
    asyncio.run(test_cdr_generation())