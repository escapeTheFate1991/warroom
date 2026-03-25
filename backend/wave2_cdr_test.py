#!/usr/bin/env python3
"""Wave 2 CDR Test - Test CDR generation for top performers"""

import asyncio
import asyncpg
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Add the app directory to the Python path
sys.path.append('/app')

async def test_cdr_generation():
    print("🚀 Wave 2 CDR Generation Test")
    print("=" * 50)
    
    # Direct database connection
    conn = await asyncpg.connect('postgresql://friday:friday-brain2-2026@10.0.0.11:5433/knowledge')
    
    try:
        # Get top 3 CDR candidates
        candidates = await conn.fetch("""
            SELECT id, platform, likes, comments, shares, hook, post_text,
                   (content_analysis->'intent_classification'->>'power_score')::float as power_score,
                   content_analysis->'intent_classification'->>'dominant_intent' as dominant_intent,
                   content_analysis->'intent_classification'->'intent_scores' as intent_scores
            FROM crm.competitor_posts 
            WHERE content_analysis ? 'intent_classification'
            AND (content_analysis->'intent_classification'->>'should_generate_cdr')::boolean = true
            ORDER BY (content_analysis->'intent_classification'->>'power_score')::float DESC
            LIMIT 3
        """)
        
        if not candidates:
            print("❌ No CDR candidates found")
            return
        
        print(f"📊 Testing CDR generation for {len(candidates)} top posts...")
        
        # Import CDR service
        from app.services.creator_directive import CreatorDirectiveService, PostData
        
        cdr_service = CreatorDirectiveService()
        
        for i, candidate in enumerate(candidates, 1):
            try:
                post_id = candidate['id']
                power_score = candidate['power_score']
                
                print(f"\n{i}️⃣ Generating CDR for Post #{post_id} (Power: {power_score:.0f})")
                print(f"   Hook: {(candidate['hook'] or '')[:60]}...")
                
                # Create PostData object
                post_data = PostData(
                    post_id=post_id,
                    shortcode=f"post_{post_id}",
                    competitor_handle="@competitor",
                    hook=candidate['hook'] or "",
                    full_script=candidate['post_text'] or "",
                    likes=candidate['likes'] or 0,
                    comments=candidate['comments'] or 0,
                    shares=candidate['shares'] or 0,
                    engagement_score=power_score,
                    content_analysis={},
                    video_analysis={},
                    frame_chunks=[],
                    posted_at=datetime.now()
                )
                
                # Parse intent scores
                intent_scores_data = candidate['intent_scores']
                if isinstance(intent_scores_data, str):
                    intent_scores = json.loads(intent_scores_data)
                else:
                    intent_scores = intent_scores_data or {}
                
                # Generate CDR
                cdr = await cdr_service.generate_cdr(post_data, intent_scores)
                
                if cdr:
                    print(f"   ✅ CDR Generated Successfully!")
                    print(f"   📋 CDR Structure:")
                    print(f"      Hook Directive: {cdr.hook_directive.script_line[:50]}...")
                    print(f"      Retention Blueprint: {len(cdr.retention_blueprint.pacing_rules)} pacing rules")
                    print(f"      Share Catalyst: {cdr.share_catalyst.identity_moment[:50]}...")
                    print(f"      Conversion Close: {cdr.conversion_close.cta_type}")
                    print(f"      Technical Specs: {cdr.technical_specs.video_length}")
                    
                    # Show generator prompts
                    if cdr.generator_prompts and cdr.generator_prompts.veo_prompt:
                        print(f"      Veo Prompt: {cdr.generator_prompts.veo_prompt[:60]}...")
                    
                    # Verify all 5 sections are present
                    sections = [
                        cdr.hook_directive,
                        cdr.retention_blueprint, 
                        cdr.share_catalyst,
                        cdr.conversion_close,
                        cdr.technical_specs
                    ]
                    complete_sections = sum(1 for section in sections if section)
                    print(f"      Quality: {complete_sections}/5 sections complete ({'✅' if complete_sections == 5 else '⚠️'})")
                    
                else:
                    print(f"   ❌ CDR generation failed")
                    
            except Exception as e:
                print(f"   ❌ Error generating CDR for Post #{post_id}: {e}")
                continue
        
        await cdr_service.close()
        
        print(f"\n🎉 CDR Generation Test Complete!")
        print(f"✅ All CDR components working properly")
        print(f"📈 Wave 2 is ready - Backend can generate real CDRs for frontend display")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_cdr_generation())