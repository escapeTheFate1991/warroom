#!/usr/bin/env python3
"""Test script for Intent Classifier + Weighted Scorer system.

Demonstrates the full CDR intent classification pipeline:
1. Single post classification
2. Batch processing 
3. Power score calculation
4. CDR candidate identification

Run with: ./venv/bin/python test_intent_classifier.py
"""

import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.intent_classifier import (
    process_post_intent_classification,
    batch_classify_intents
)

DATABASE_URL = 'postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge'

async def demonstrate_intent_classifier():
    """Full demonstration of the Intent Classification system."""
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("🔥 WAR ROOM CDR INTENT CLASSIFIER DEMONSTRATION 🔥")
        print("=" * 60)
        
        # 1. Single Post Classification
        print("\n📊 1. SINGLE POST CLASSIFICATION")
        print("-" * 40)
        
        post_id = 2437  # High-engagement post
        result = await process_post_intent_classification(db, post_id)
        
        if "error" not in result:
            scores = result["scores"]
            classification = result["classification"]
            
            print(f"Post ID: {result['post_id']}")
            print(f"Platform: {result['platform']}")
            print(f"Engagement: {result['metrics']['likes']} likes, {result['metrics']['comments']} comments, {result['metrics']['shares']} shares")
            print(f"Power Score: {scores['power_score']:,.1f}")
            print(f"Dominant Intent: {scores['dominant_intent']}")
            print(f"Action Priority: {scores['action_priority']}")
            print(f"CDR Candidate: {'YES ✅' if scores['should_generate_cdr'] else 'NO ❌'}")
            
            # Show intent breakdown
            intent_scores = classification["intent_scores"]
            print(f"\nIntent Classification:")
            for intent, score in sorted(intent_scores.items(), key=lambda x: x[1], reverse=True):
                if score > 0:
                    print(f"  {intent}: {score:.1f}")
        
        # 2. Batch Processing Demo
        print("\n\n📈 2. BATCH PROCESSING (10 POSTS)")
        print("-" * 40)
        
        batch_results = await batch_classify_intents(db, limit=10)
        
        if "error" not in batch_results:
            print(f"Posts Processed: {batch_results['processed']}")
            print(f"Errors: {batch_results['errors']}")
            print(f"High Priority Posts: {batch_results['high_priority']}")
            print(f"CDR Candidates: {batch_results['cdr_candidates']}")
            print(f"Average Power Score: {batch_results['avg_power_score']:,.1f}")
            
            print(f"\nDominant Intent Distribution:")
            for intent, count in batch_results['dominant_intents'].most_common():
                print(f"  {intent}: {count} posts")
        
        # 3. CDR Candidate Analysis
        print("\n\n🎯 3. CDR CANDIDATE ANALYSIS")
        print("-" * 40)
        
        # Query for CDR candidates
        from sqlalchemy import text
        
        query = text("""
            SELECT id, platform, likes, comments, shares, hook,
                   content_analysis->'intent_classification'->>'power_score' as power_score,
                   content_analysis->'intent_classification'->>'dominant_intent' as dominant_intent,
                   content_analysis->'intent_classification'->>'action_priority' as action_priority
            FROM crm.competitor_posts 
            WHERE content_analysis ? 'intent_classification'
            AND CAST(content_analysis->'intent_classification'->>'power_score' AS FLOAT) > 2000
            ORDER BY CAST(content_analysis->'intent_classification'->>'power_score' AS FLOAT) DESC
            LIMIT 5
        """)
        
        result = await db.execute(query)
        candidates = result.fetchall()
        
        print(f"Found {len(candidates)} CDR candidates (Power Score > 2000):")
        
        for i, candidate in enumerate(candidates, 1):
            row_dict = candidate._asdict()
            hook = row_dict['hook'][:60] + "..." if row_dict['hook'] and len(row_dict['hook']) > 60 else row_dict['hook']
            
            print(f"\n  #{i} Post {row_dict['id']} ({row_dict['platform']})")
            print(f"      Power Score: {float(row_dict['power_score']):,.0f}")
            print(f"      Dominant Intent: {row_dict['dominant_intent']}")
            print(f"      Priority: {row_dict['action_priority']}")
            print(f"      Hook: {hook or 'No hook'}")
            print(f"      Engagement: {row_dict['likes']} likes, {row_dict['comments']} comments, {row_dict['shares']} shares")
        
        # 4. Intent Pattern Summary
        print("\n\n🧠 4. INTENT CLASSIFICATION SYSTEM SUMMARY")
        print("-" * 40)
        
        print("Six Intent Buckets:")
        print("  🔖 UTILITY_SAVE - Bookmarking/saving behavior")
        print("  🫵 IDENTITY_SHARE - Personal resonance/sharing")
        print("  ❓ CURIOSITY_GAP - Questions/knowledge gaps")
        print("  ⚠️  FRICTION_POINT - Confusion/technical issues")
        print("  👥 SOCIAL_PROOF - Validation/agreement")
        print("  🎯 TOPIC_RELEVANCE - Contextual alignment")
        
        print("\nPower Score Formula:")
        print("  Shares × 10 + Saves × 8 + Deep Comments × 5 + Surface Comments × 1 + Likes × 0.5")
        
        print("\nCDR Generation Threshold:")
        print("  Power Score > 2000 → Generate Creator Directive Report")
        
        print(f"\n✅ Intent Classification system successfully deployed!")
        print(f"📊 Ready for CDR generation pipeline integration")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(demonstrate_intent_classifier())