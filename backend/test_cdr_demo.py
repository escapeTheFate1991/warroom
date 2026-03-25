#!/usr/bin/env python3
"""Demo CDR Generator with mock data to test functionality."""

import asyncio
import json
from datetime import datetime
from app.services.creator_directive import (
    CreatorDirectiveService, 
    PostData,
    mock_intent_classifier
)

def create_mock_post_data():
    """Create mock high-engagement post data for testing"""
    return [
        PostData(
            post_id=1,
            shortcode="demo_post_1",
            competitor_handle="viral_creator",
            hook="This one simple habit changed everything for me",
            full_script="This one simple habit changed everything for me. For years I struggled with productivity until I discovered the power of time blocking. Here's exactly how I do it: I take every Sunday evening and plan my entire week in 2-hour blocks. Work blocks, focus blocks, even social blocks. The result? I doubled my output in half the time. Try this for one week and tell me in the comments what changed for you.",
            likes=45000,
            comments=2800,
            shares=1200,
            engagement_score=8500,
            content_analysis={
                "hook": {
                    "text": "This one simple habit changed everything for me",
                    "type": "bold_claim",
                    "strength": 0.85
                },
                "value": {
                    "text": "For years I struggled with productivity until I discovered the power of time blocking. Here's exactly how I do it: I take every Sunday evening and plan my entire week in 2-hour blocks.",
                    "key_points": [
                        "Time blocking technique",
                        "Sunday planning ritual",
                        "2-hour block strategy"
                    ]
                },
                "cta": {
                    "text": "Try this for one week and tell me in the comments what changed for you",
                    "type": "engagement",
                    "phrase": "tell me in the comments"
                },
                "structure_score": 0.92
            },
            video_analysis={
                "duration": 42.5,
                "cuts": 12,
                "text_overlays": True
            },
            frame_chunks=[
                {"timestamp": "0-3s", "description": "Creator speaking directly to camera"},
                {"timestamp": "3-15s", "description": "Split screen showing before/after calendar"},
                {"timestamp": "15-35s", "description": "Screen recording of planning process"},
                {"timestamp": "35-42s", "description": "Creator back on camera for CTA"}
            ],
            posted_at=datetime(2024, 3, 15)
        ),
        PostData(
            post_id=2,
            shortcode="demo_post_2", 
            competitor_handle="business_guru",
            hook="POV: You're scared to start because you think you need to be perfect",
            full_script="POV: You're scared to start because you think you need to be perfect. I used to think the same thing. I waited 3 years to launch my first course because I wanted everything to be flawless. Biggest mistake ever. When I finally launched my 'imperfect' course, it made $50k in the first month. Perfect is the enemy of progress. Your messy action beats their perfect inaction every single time. What are you waiting for?",
            likes=67000,
            comments=4200,
            shares=2100,
            engagement_score=12500,
            content_analysis={
                "hook": {
                    "text": "POV: You're scared to start because you think you need to be perfect",
                    "type": "identity_share",
                    "strength": 0.78
                },
                "value": {
                    "text": "I used to think the same thing. I waited 3 years to launch my first course because I wanted everything to be flawless. Biggest mistake ever. When I finally launched my 'imperfect' course, it made $50k in the first month.",
                    "key_points": [
                        "Personal vulnerability story",
                        "Concrete outcome ($50k)",
                        "Lesson learned"
                    ]
                },
                "cta": {
                    "text": "What are you waiting for?",
                    "type": "engagement", 
                    "phrase": "what are you waiting for"
                },
                "structure_score": 0.87
            },
            video_analysis={
                "duration": 38.2,
                "cuts": 8,
                "text_overlays": True
            },
            frame_chunks=[
                {"timestamp": "0-5s", "description": "Bold text overlay with hook"},
                {"timestamp": "5-20s", "description": "Creator telling story"},
                {"timestamp": "20-35s", "description": "Revenue screenshot shown"},
                {"timestamp": "35-38s", "description": "Direct camera challenge"}
            ],
            posted_at=datetime(2024, 3, 10)
        )
    ]

async def demo_cdr_generation():
    """Demonstrate CDR generation with mock high-performing posts"""
    print("🎯 CDR Generator Demo - War Room Strategic Intelligence")
    print("="*80)
    
    mock_posts = create_mock_post_data()
    cdr_service = CreatorDirectiveService()
    
    for i, post_data in enumerate(mock_posts, 1):
        print(f"\n🎬 DEMO CDR #{i}: @{post_data.competitor_handle}")
        print(f"📊 Performance: {post_data.likes:,} likes, {post_data.comments:,} comments, {post_data.shares:,} shares")
        print(f"🎯 Hook: \"{post_data.hook}\"")
        
        try:
            # Generate intent scores
            intent_scores = mock_intent_classifier(post_data.content_analysis)
            print(f"🧠 Intent Analysis: {intent_scores}")
            
            # Generate CDR
            cdr = await cdr_service.generate_cdr(post_data, intent_scores)
            
            if not cdr:
                print(f"❌ CDR generation failed - below power score threshold")
                continue
            
            print(f"⚡ Power Score: {cdr.power_score:.0f}")
            print(f"🎪 Dominant Intent: {cdr.dominant_intent}")
            
            print(f"\n📝 HOOK DIRECTIVE ({cdr.dominant_intent}):")
            print(f"  🎥 Visual: {cdr.hook_directive.visual}")
            print(f"  🎵 Audio: {cdr.hook_directive.audio}")
            print(f"  💬 Script: \"{cdr.hook_directive.script_line}\"")
            print(f"  📱 Overlay: {cdr.hook_directive.overlay}")
            print(f"  🧩 Strategy: {cdr.hook_directive.reasoning}")
            
            print(f"\n🎬 RETENTION BLUEPRINT:")
            print(f"  ⏱️ Pacing Rules:")
            for rule in cdr.retention_blueprint.pacing_rules:
                print(f"    • {rule}")
            print(f"  ⚡ Pattern Interrupts:")
            for interrupt in cdr.retention_blueprint.pattern_interrupts[:2]:
                print(f"    • {interrupt}")
            
            print(f"\n🔥 SHARE CATALYST:")
            print(f"  💔 Vulnerability: {cdr.share_catalyst.vulnerability_frame}")
            print(f"  🪞 Identity Moment: {cdr.share_catalyst.identity_moment}")
            print(f"  🎨 Visual Shift: {cdr.share_catalyst.visual_style_shift}")
            print(f"  ⏰ Timing: {cdr.share_catalyst.timestamp}")
            
            print(f"\n💰 CONVERSION CLOSE:")
            print(f"  🎯 CTA Type: {cdr.conversion_close.cta_type.upper()}")
            print(f"  💬 Script: \"{cdr.conversion_close.script_line}\"")
            print(f"  🔄 Open Loop: {cdr.conversion_close.open_loop_topic}")
            print(f"  🤖 Auto Trigger: {cdr.conversion_close.automation_trigger}")
            
            print(f"\n🎥 TECHNICAL SPECS:")
            print(f"  💡 Lighting: {cdr.technical_specs.lighting}")
            print(f"  📐 Aspect Ratio: {cdr.technical_specs.aspect_ratio}")
            print(f"  🎨 Colors: {cdr.technical_specs.color_palette}")
            print(f"  🎵 Music: {cdr.technical_specs.music_bpm}")
            print(f"  ⏱️ Length: {cdr.technical_specs.video_length}")
            
            print(f"\n🤖 GENERATOR PROMPTS:")
            print(f"  🎬 VEO PROMPT:")
            print(f"    \"{cdr.generator_prompts.veo_prompt[:200]}...\"")
            print(f"  🍌 NANO BANANA PROMPT:")
            print(f"    \"{cdr.generator_prompts.nano_banana_prompt[:200]}...\"")
            
            print(f"\n" + "="*80)
            
        except Exception as e:
            print(f"❌ CDR generation failed: {e}")
            continue
    
    await cdr_service.close()
    print(f"\n✅ CDR Demo completed! Ready for War Room deployment.")
    print(f"🚀 Next: Test with /api/content-intel/creator-directive/{{post_id}} endpoint")

if __name__ == "__main__":
    asyncio.run(demo_cdr_generation())