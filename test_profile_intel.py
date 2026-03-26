#!/usr/bin/env python3
"""Test Profile Intel Service with enhanced recommendations."""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Change to backend directory for proper imports
os.chdir(backend_path)

from app.database import get_db_session
from app.services.profile_intel_service import profile_intel_service


async def test_profile_intel_recommendations():
    """Test the enhanced profile intel service with a real user."""
    try:
        async with get_db_session() as db:
            # Use org_id=1 and test with a known profile
            org_id = 1
            profile_id = "ai.jason"  # Example user profile
            
            print(f"Testing Profile Intel for {profile_id}...")
            
            # Generate profile intel with enhanced recommendations
            result = await profile_intel_service.get_or_create_profile_intel(
                db=db,
                org_id=org_id,
                profile_id=profile_id,
                platform="instagram",
                force_refresh=True
            )
            
            print(f"\n=== PROFILE INTEL RESULTS FOR {profile_id.upper()} ===")
            
            # Overall Grade
            overall_grade = result.grades.get("overall", {})
            print(f"\nOVERALL GRADE: {overall_grade.score}")
            print(f"Details: {overall_grade.details}")
            
            # Category Breakdowns
            print(f"\n=== CATEGORY GRADES ===")
            for category, grade_info in result.grades.items():
                if category != "overall":
                    print(f"{category.upper()}: {grade_info.score}/100")
                    print(f"  → {grade_info.details}")
            
            # Enhanced Recommendations
            print(f"\n=== ENHANCED RECOMMENDATIONS ===")
            
            # What's Working
            if result.recommendations.get("keepDoing"):
                print(f"\n✅ WHAT'S WORKING:")
                for item in result.recommendations["keepDoing"]:
                    print(f"  • {item.get('what', 'N/A')}")
                    print(f"    Evidence: {item.get('evidence', 'N/A')}")
                    if item.get('whyItWorks'):
                        print(f"    Why: {item.get('whyItWorks')}")
                    if item.get('doubleDown'):
                        print(f"    Double Down: {item.get('doubleDown')}")
                    print()
            
            # What to Stop Doing
            if result.recommendations.get("stopDoing"):
                print(f"\n🛑 WHAT TO IMPROVE:")
                for item in result.recommendations["stopDoing"]:
                    print(f"  • {item.get('what', 'N/A')} [{item.get('priority', 'MEDIUM')} PRIORITY]")
                    print(f"    Evidence: {item.get('evidence', 'N/A')}")
                    print(f"    Impact: {item.get('impactOfStopping', 'N/A')}")
                    print()
            
            # Profile Changes (Enhanced)
            if result.recommendations.get("profileChanges"):
                print(f"\n🎯 PROFILE CHANGES:")
                for item in result.recommendations["profileChanges"]:
                    print(f"  • {item.get('what', 'N/A')}")
                    if item.get('example'):
                        print(f"    Example: {item.get('example')}")
                    if item.get('competitorContext'):
                        print(f"    Competitor Context: {item.get('competitorContext')}")
                    if item.get('howToImplement'):
                        print(f"    How To: {item.get('howToImplement')}")
                    if item.get('impactEstimate'):
                        print(f"    Impact: {item.get('impactEstimate')}")
                    print(f"    Priority: {item.get('priority', 'medium')}")
                    print()
            
            # Content Recommendations
            if result.recommendations.get("contentRecommendations"):
                print(f"\n📹 CREATE NEXT:")
                for item in result.recommendations["contentRecommendations"]:
                    print(f"  • {item.get('what', 'N/A')}")
                    print(f"    Evidence: {item.get('evidence', 'N/A')}")
                    if item.get('whyNow'):
                        print(f"    Why Now: {item.get('whyNow')}")
                    if item.get('formatSuggestion'):
                        print(f"    Format: {item.get('formatSuggestion')}")
                    if item.get('timeEstimate'):
                        print(f"    Time: {item.get('timeEstimate')}")
                    print(f"    Priority: {item.get('priority', 'medium')}")
                    print()
            
            # Next Steps (Top 5)
            if result.recommendations.get("nextSteps"):
                print(f"\n📋 NEXT STEPS (This Week):")
                for i, item in enumerate(result.recommendations["nextSteps"], 1):
                    print(f"  {i}. {item.get('action', 'N/A')} [{item.get('priority', 'MEDIUM')}]")
                    print(f"     Time: {item.get('timeEstimate', 'Unknown')}")
                    print(f"     Impact: {item.get('expectedImpact', 'N/A')}")
                    if item.get('howTo'):
                        print(f"     How: {item.get('howTo')}")
                    print()
            
            # Videos to Remove
            if result.recommendations.get("videosToRemove"):
                print(f"\n🗑️ VIDEOS TO CONSIDER REMOVING:")
                for item in result.recommendations["videosToRemove"]:
                    video_title = item.get('videoTitle', item.get('videoId', 'Unknown'))
                    print(f"  • {video_title}")
                    print(f"    Reason: {item.get('reason', 'N/A')}")
                    if item.get('currentGrade'):
                        print(f"    Grade: {item.get('currentGrade')}")
                    print(f"    Action: {item.get('action', 'Review performance')}")
                    print()
            
            # Data Sources
            print(f"\n=== DATA SOURCES ===")
            print(f"OAuth Connected: {'Yes' if result.oauth_data else 'No'}")
            print(f"Scraped Data: {'Yes' if result.scraped_data else 'No'}")
            print(f"Videos Analyzed: {len(result.processed_videos) if result.processed_videos else 0}")
            print(f"Last Synced: {result.last_synced_at}")
            
            return True
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Set backend environment
    os.environ.setdefault("ENV", "development")
    
    success = asyncio.run(test_profile_intel_recommendations())
    sys.exit(0 if success else 1)