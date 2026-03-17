#!/usr/bin/env python3
"""Test Simulate API endpoints for Mirofish Swarm Persona System."""
import asyncio
import json
import aiohttp

async def test_simulate_endpoints():
    """Test the simulate API endpoints."""
    print("🧠 Testing Mirofish Swarm Persona System API Endpoints")
    
    base_url = "http://localhost:8300"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: List personas endpoint
        print("\n1. Testing list personas endpoint...")
        try:
            headers = {"X-Org-ID": "1"}
            
            async with session.get(
                f"{base_url}/api/simulate/personas",
                headers=headers
            ) as resp:
                status = resp.status
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json()
                    print(f"   Found {len(data)} personas")
                    for persona in data:
                        print(f"   - {persona['name']} ({persona['archetype']}) [system: {persona['is_system']}]")
                else:
                    text = await resp.text()
                    print(f"   Error: {text[:200]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 2: Get specific persona endpoint
        print("\n2. Testing get specific persona endpoint...")
        try:
            headers = {"X-Org-ID": "1"}
            
            async with session.get(
                f"{base_url}/api/simulate/personas/1",
                headers=headers
            ) as resp:
                status = resp.status
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json()
                    print(f"   Persona: {data['name']}")
                    print(f"   Archetype: {data['archetype']}")
                    print(f"   Demographics: {json.dumps(data['demographics'], indent=4)[:100]}...")
                else:
                    text = await resp.text()
                    print(f"   Error: {text[:200]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 3: Create custom persona endpoint
        print("\n3. Testing create custom persona endpoint...")
        try:
            headers = {"X-Org-ID": "1", "Content-Type": "application/json"}
            
            payload = {
                "name": "Test Custom Persona",
                "archetype": "test_archetype",
                "demographics": {"age_range": "25-35", "roles": ["Tester"]},
                "psychographics": {"desires": ["Test functionality"], "friction_points": ["Broken APIs"]},
                "behavioral_logic": {
                    "interaction_triggers": {
                        "comment_on": ["API responses"],
                        "share_on": ["Working code"],
                        "bookmark_on": ["Useful tests"]
                    }
                }
            }
            
            async with session.post(
                f"{base_url}/api/simulate/personas",
                headers=headers,
                json=payload
            ) as resp:
                status = resp.status
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json()
                    print(f"   Created persona with ID: {data.get('id')}")
                else:
                    text = await resp.text()
                    print(f"   Error: {text[:300]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 4: Social friction test endpoint
        print("\n4. Testing social friction test endpoint...")
        try:
            headers = {"X-Org-ID": "1", "Content-Type": "application/json"}
            
            payload = {
                "script": {
                    "hook": "Nobody talks about this AI secret...",
                    "body": "Claude just shipped a feature that changes everything. Most developers miss this because they're still using ChatGPT.",
                    "cta": "Follow for more insider tips"
                },
                "format_slug": "expose",
                "persona_ids": [1, 2, 3],
                "scene_count": 4,
                "audio_style": "trending_fast_paced"
            }
            
            async with session.post(
                f"{base_url}/api/simulate/social-friction-test",
                headers=headers,
                json=payload
            ) as resp:
                status = resp.status
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json()
                    print(f"   Engagement score: {data.get('engagement_score')}")
                    print(f"   Like propensity: {data.get('predicted_metrics', {}).get('like_propensity')}")
                    print(f"   Comments generated: {len(data.get('predicted_comments', []))}")
                    print(f"   Optimization suggestion: {data.get('optimization_recommendation', {}).get('change', 'N/A')}")
                else:
                    text = await resp.text()
                    print(f"   Error: {text[:300]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 5: Persona chat endpoint
        print("\n5. Testing persona chat endpoint...")
        try:
            headers = {"X-Org-ID": "1", "Content-Type": "application/json"}
            
            payload = {
                "persona_id": 1,
                "script": {
                    "hook": "Nobody talks about this AI secret...",
                    "body": "Claude just shipped a feature that changes everything.",
                    "cta": "Follow for more insider tips"
                },
                "format_slug": "expose",
                "user_message": "Why didn't you engage with this content?"
            }
            
            async with session.post(
                f"{base_url}/api/simulate/persona-chat",
                headers=headers,
                json=payload
            ) as resp:
                status = resp.status
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json()
                    print(f"   Persona: {data.get('persona_name')}")
                    print(f"   Response: {data.get('response')[:150]}...")
                    print(f"   Behavioral trigger: {data.get('behavioral_trigger')}")
                    print(f"   Suggested fix: {data.get('suggested_fix')}")
                else:
                    text = await resp.text()
                    print(f"   Error: {text[:300]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 6: Simulation history endpoint
        print("\n6. Testing simulation history endpoint...")
        try:
            headers = {"X-Org-ID": "1"}
            
            async with session.get(
                f"{base_url}/api/simulate/history",
                headers=headers
            ) as resp:
                status = resp.status
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json()
                    print(f"   Found {len(data)} simulation results")
                    if data:
                        latest = data[0]
                        print(f"   Latest: {latest.get('script_hook', 'N/A')[:50]}... (score: {latest.get('engagement_score')})")
                else:
                    text = await resp.text()
                    print(f"   Error: {text[:200]}")
        
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 7: Generate personas from competitors
        print("\n7. Testing generate personas from competitors...")
        try:
            headers = {"X-Org-ID": "1", "Content-Type": "application/json"}
            
            async with session.post(
                f"{base_url}/api/simulate/generate-personas",
                headers=headers
            ) as resp:
                status = resp.status
                print(f"   Status: {status}")
                
                if status == 200:
                    data = await resp.json()
                    print(f"   Generated {len(data.get('generated_personas', []))} personas")
                    print(f"   Analyzed {data.get('analyzed_comments', 0)} comments")
                    for persona in data.get('generated_personas', []):
                        print(f"   - {persona.get('name')} ({persona.get('archetype')})")
                else:
                    text = await resp.text()
                    print(f"   Error: {text[:300]}")
        
        except Exception as e:
            print(f"   Exception: {e}")

    print("\n✅ Testing completed!")

if __name__ == "__main__":
    asyncio.run(test_simulate_endpoints())