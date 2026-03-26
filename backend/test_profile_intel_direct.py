#!/usr/bin/env python3
"""Direct test of profile intel service (bypassing API auth)."""

import asyncio
import sys
import json
from sqlalchemy import text
from app.db.crm_db import crm_session
from app.services.profile_intel_service import profile_intel_service

async def test_profile_intel_direct():
    """Test profile intel service directly with database."""
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            
            org_id = 1
            profile_id = "ai.jason"
            
            print(f"🧠 Testing Profile Intel for {profile_id} (org_id={org_id})")
            print("=" * 60)
            
            # Test the enhanced recommendations
            result = await profile_intel_service.get_or_create_profile_intel(
                db=db,
                org_id=org_id,
                profile_id=profile_id,
                platform="instagram",
                force_refresh=True
            )
            
            print(f"\n📊 OVERALL GRADE: {result.grades.get('overall', {}).score}")
            print(f"Details: {result.grades.get('overall', {}).details}")
            
            # Show enhanced recommendations
            recommendations = result.recommendations
            
            if recommendations.get('profileChanges'):
                print(f"\n🎯 PROFILE CHANGES:")
                for i, rec in enumerate(recommendations['profileChanges'][:2], 1):
                    print(f"  {i}. {rec.get('what', 'N/A')}")
                    if rec.get('example'):
                        print(f"     Example: {rec['example']}")
                    if rec.get('competitorContext'):
                        print(f"     Context: {rec['competitorContext']}")
                    if rec.get('howToImplement'):
                        print(f"     How: {rec['howToImplement']}")
                    if rec.get('impactEstimate'):
                        print(f"     Impact: {rec['impactEstimate']}")
                    print(f"     Priority: {rec.get('priority', 'medium')}")
                    print()
            
            if recommendations.get('keepDoing'):
                print(f"\n✅ WHAT'S WORKING:")
                for rec in recommendations['keepDoing'][:3]:
                    print(f"  • {rec.get('what', 'N/A')}")
                    print(f"    Evidence: {rec.get('evidence', 'N/A')}")
                    if rec.get('whyItWorks'):
                        print(f"    Why: {rec['whyItWorks']}")
                    if rec.get('doubleDown'):
                        print(f"    Double Down: {rec['doubleDown']}")
                    print()
            
            if recommendations.get('stopDoing'):
                print(f"\n🛑 WHAT TO IMPROVE:")
                for rec in recommendations['stopDoing'][:3]:
                    print(f"  • {rec.get('what', 'N/A')} [{rec.get('priority', 'MEDIUM')} PRIORITY]")
                    print(f"    Evidence: {rec.get('evidence', 'N/A')}")
                    print(f"    Impact: {rec.get('impactOfStopping', 'N/A')}")
                    print()
            
            if recommendations.get('contentRecommendations'):
                print(f"\n📹 CREATE NEXT:")
                for rec in recommendations['contentRecommendations'][:2]:
                    print(f"  • {rec.get('what', 'N/A')}")
                    print(f"    Evidence: {rec.get('evidence', 'N/A')}")
                    if rec.get('whyNow'):
                        print(f"    Why Now: {rec['whyNow']}")
                    if rec.get('formatSuggestion'):
                        print(f"    Format: {rec['formatSuggestion']}")
                    if rec.get('timeEstimate'):
                        print(f"    Time: {rec['timeEstimate']}")
                    print()
            
            if recommendations.get('nextSteps'):
                print(f"\n📋 NEXT STEPS (This Week):")
                for i, rec in enumerate(recommendations['nextSteps'][:5], 1):
                    print(f"  {i}. {rec.get('action', 'N/A')} [{rec.get('priority', 'MEDIUM')}]")
                    print(f"     Time: {rec.get('timeEstimate', 'Unknown')}")
                    print(f"     Impact: {rec.get('expectedImpact', 'N/A')}")
                    if rec.get('howTo'):
                        print(f"     How: {rec['howTo']}")
                    print()
            
            # Show data sources
            print(f"\n📊 DATA SOURCES:")
            print(f"  OAuth Data: {'✓' if result.oauth_data else '✗'} ({len(result.oauth_data) if result.oauth_data else 0} metrics)")
            print(f"  Scraped Data: {'✓' if result.scraped_data else '✗'} ({len(result.scraped_data) if result.scraped_data else 0} fields)")
            print(f"  Videos Analyzed: {len(result.processed_videos) if result.processed_videos else 0}")
            print(f"  Last Updated: {result.last_synced_at}")
            
            # Show category grades  
            print(f"\n🏆 CATEGORY BREAKDOWN:")
            for category, grade in result.grades.items():
                if category != 'overall':
                    score = grade.score if hasattr(grade, 'score') else grade.get('score', 'N/A')
                    print(f"  {category.upper()}: {score}")
                    details = grade.details if hasattr(grade, 'details') else grade.get('details', '')
                    if details and len(details) < 100:
                        print(f"    → {details}")
            
            print(f"\n✅ Profile Intel test completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_profile_intel_direct())
    sys.exit(0 if success else 1)