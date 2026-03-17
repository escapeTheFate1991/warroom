#!/usr/bin/env python3
"""Test API endpoints for Phase 4 Performance Feedback Loop Backend."""
import asyncio
import json
import aiohttp

async def test_api_endpoints():
    """Test the API endpoints directly."""
    print("🌐 Testing Performance Feedback API Endpoints")
    
    base_url = "http://localhost:8300"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Test /generation-context endpoint
        print("\n1. Testing generation-context endpoint...")
        try:
            # Create a mock request with org_id header (bypassing auth for test)
            headers = {"X-Org-ID": "1"}  # This might not work, but worth trying
            
            async with session.get(
                f"{base_url}/api/content-intel/generation-context",
                headers=headers
            ) as resp:
                status = resp.status
                text = await resp.text()
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json() if resp.content_type == 'application/json' else None
                    if data:
                        print(f"   Competitor weight: {data.get('competitor_weight', 'N/A')}")
                        print(f"   Own weight: {data.get('own_weight', 'N/A')}")
                        print(f"   Recommendations count: {len(data.get('recommendations', []))}")
                    else:
                        print(f"   Response: {text[:200]}")
                else:
                    print(f"   Error: {text[:200]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 2: Test /performance-dashboard endpoint
        print("\n2. Testing performance-dashboard endpoint...")
        try:
            headers = {"X-Org-ID": "1"}
            
            async with session.get(
                f"{base_url}/api/content-intel/performance-dashboard",
                headers=headers
            ) as resp:
                status = resp.status
                text = await resp.text()
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json() if resp.content_type == 'application/json' else None
                    if data:
                        print(f"   Total posts: {data.get('total_posts', 'N/A')}")
                        print(f"   Avg engagement: {data.get('avg_engagement', 'N/A')}")
                        print(f"   Best format: {data.get('best_format', 'N/A')}")
                        print(f"   Format leaderboard entries: {len(data.get('format_leaderboard', []))}")
                    else:
                        print(f"   Response: {text[:200]}")
                else:
                    print(f"   Error: {text[:200]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 3: Test /collect-performance endpoint with POST
        print("\n3. Testing collect-performance endpoint...")
        try:
            headers = {"X-Org-ID": "1", "Content-Type": "application/json"}
            test_data = {
                "distribution_post_id": 999,
                "video_project_id": 1,
                "format_slug": "expose",
                "hook_text": "Nobody talks about this secret Instagram algorithm trick",
                "competitor_inspiration_ids": [1, 2],
                "metrics": {
                    "likes": 750,
                    "comments": 120,
                    "shares": 45,
                    "saves": 280,
                    "reach": 15000,
                    "views": 22000
                }
            }
            
            async with session.post(
                f"{base_url}/api/content-intel/collect-performance",
                headers=headers,
                json=test_data
            ) as resp:
                status = resp.status
                text = await resp.text()
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json() if resp.content_type == 'application/json' else None
                    if data:
                        print(f"   Created feedback ID: {data.get('id', 'N/A')}")
                        print(f"   Engagement score: {data.get('engagement_score', 'N/A')}")
                        print(f"   Performance tier: {data.get('performance_tier', 'N/A')}")
                        print(f"   Hook score: {data.get('hook_score', 'N/A')}")
                    else:
                        print(f"   Response: {text[:200]}")
                else:
                    print(f"   Error: {text[:200]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("\n📊 API endpoint testing completed!")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())