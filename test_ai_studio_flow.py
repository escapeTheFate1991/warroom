#!/usr/bin/env python3
"""
AI Studio Core Flow Test Script

Tests the complete flow: Blueprint Selection → Auto-Fill → Pipeline → My Projects

This script verifies that the critical fixes work end-to-end.
"""

import asyncio
import aiohttp
import json
import os
import sys
from typing import Dict, Any

# Test configuration
API_BASE = "http://localhost:8100"  # Adjust based on actual backend port
TEST_USER_ID = 1  # Adjust based on test user
HEADERS = {
    "Content-Type": "application/json",
    # Add authentication headers if needed
}

class AIStudioTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_api_health(self) -> bool:
        """Test if the API is responding."""
        try:
            async with self.session.get(f"{self.base_url}/health") as resp:
                return resp.status == 200
        except Exception as e:
            print(f"❌ API health check failed: {e}")
            return False
    
    async def test_blueprints_list(self) -> Dict[str, Any]:
        """Test blueprint listing."""
        try:
            async with self.session.get(
                f"{self.base_url}/api/ai-studio/ugc/blueprints?limit=5",
                headers=HEADERS
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Blueprints list: {len(data.get('blueprints', []))} found")
                    return data
                else:
                    print(f"❌ Blueprints list failed: {resp.status} - {await resp.text()}")
                    return {}
        except Exception as e:
            print(f"❌ Blueprints list error: {e}")
            return {}
    
    async def test_blueprint_auto_fill(self, post_id: int) -> Dict[str, Any]:
        """Test blueprint auto-fill functionality."""
        try:
            payload = {
                "digital_copy_id": None,
                "brand_topic": "test product"
            }
            async with self.session.post(
                f"{self.base_url}/api/ai-studio/ugc/blueprints/{post_id}/auto-fill",
                headers=HEADERS,
                json=payload
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    print(f"✅ Blueprint auto-fill successful for post {post_id}")
                    return data
                else:
                    print(f"❌ Blueprint auto-fill failed: {resp.status} - {data.get('detail', 'Unknown error')}")
                    return {}
        except Exception as e:
            print(f"❌ Blueprint auto-fill error: {e}")
            return {}
    
    async def test_digital_copies_list(self) -> Dict[str, Any]:
        """Test digital copies listing."""
        try:
            async with self.session.get(
                f"{self.base_url}/api/ai-studio/ugc/digital-copies",
                headers=HEADERS
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Digital copies list: {len(data.get('copies', []))} found")
                    return data
                else:
                    print(f"❌ Digital copies list failed: {resp.status} - {await resp.text()}")
                    return {}
        except Exception as e:
            print(f"❌ Digital copies list error: {e}")
            return {}
    
    async def test_project_creation(self) -> Dict[str, Any]:
        """Test video project creation."""
        try:
            payload = {
                "title": "Test Video Project",
                "template_id": "test_template",
                "digital_copy_id": None,
                "content_mode": "product",
                "script": "Test script content",
                "storyboard": [
                    {
                        "scene": 1,
                        "label": "Hook",
                        "direction": "Direct to camera"
                    }
                ]
            }
            async with self.session.post(
                f"{self.base_url}/api/ai-studio/ugc/projects",
                headers=HEADERS,
                json=payload
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    print(f"✅ Project creation successful: {data.get('project_id')}")
                    return data
                else:
                    print(f"❌ Project creation failed: {resp.status} - {data.get('detail', 'Unknown error')}")
                    return {}
        except Exception as e:
            print(f"❌ Project creation error: {e}")
            return {}
    
    async def test_projects_list(self) -> Dict[str, Any]:
        """Test projects listing."""
        try:
            async with self.session.get(
                f"{self.base_url}/api/ai-studio/ugc/projects",
                headers=HEADERS
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Projects list: {len(data.get('projects', []))} found")
                    return data
                else:
                    print(f"❌ Projects list failed: {resp.status} - {await resp.text()}")
                    return {}
        except Exception as e:
            print(f"❌ Projects list error: {e}")
            return {}
    
    async def test_pipeline_start(self) -> Dict[str, Any]:
        """Test pipeline execution start."""
        try:
            payload = {
                "reference_post_id": 1,  # Use a test post ID
                "digital_copy_id": None,
                "brand_context": {
                    "brand_name": "Test Brand",
                    "product_name": "Test Product",
                    "script": "Test script for pipeline"
                }
            }
            async with self.session.post(
                f"{self.base_url}/api/ai-studio/ugc/pipeline/start",
                headers=HEADERS,
                json=payload
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    print(f"✅ Pipeline start successful: {data.get('pipeline_id')}")
                    return data
                else:
                    print(f"❌ Pipeline start failed: {resp.status} - {data.get('detail', 'Unknown error')}")
                    return {}
        except Exception as e:
            print(f"❌ Pipeline start error: {e}")
            return {}

async def run_tests():
    """Run all AI Studio tests."""
    print("🚀 Starting AI Studio Core Flow Tests")
    print("=" * 50)
    
    async with AIStudioTester(API_BASE) as tester:
        # Test 1: API Health
        print("\n1. Testing API Health...")
        if not await tester.test_api_health():
            print("❌ API not responding. Ensure backend is running.")
            return False
        
        # Test 2: List Blueprints
        print("\n2. Testing Blueprints List...")
        blueprints_data = await tester.test_blueprints_list()
        blueprints = blueprints_data.get('blueprints', [])
        
        # Test 3: Auto-fill Blueprint (if blueprints exist)
        if blueprints:
            print(f"\n3. Testing Blueprint Auto-Fill...")
            first_blueprint = blueprints[0]
            post_id = first_blueprint.get('post_id')
            if post_id:
                await tester.test_blueprint_auto_fill(post_id)
            else:
                print("⚠️  No valid post_id found in blueprints")
        else:
            print("\n3. Skipping Blueprint Auto-Fill (no blueprints found)")
        
        # Test 4: List Digital Copies
        print("\n4. Testing Digital Copies List...")
        await tester.test_digital_copies_list()
        
        # Test 5: Create Project
        print("\n5. Testing Project Creation...")
        await tester.test_project_creation()
        
        # Test 6: List Projects
        print("\n6. Testing Projects List...")
        await tester.test_projects_list()
        
        # Test 7: Start Pipeline (if we have prerequisites)
        print("\n7. Testing Pipeline Start...")
        await tester.test_pipeline_start()
        
        print("\n" + "=" * 50)
        print("🎯 AI Studio Tests Completed")
        print("\nNote: Some tests may fail due to missing test data or authentication.")
        print("Check the specific error messages above for details.")

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        global API_BASE
        API_BASE = sys.argv[1]
        print(f"Using API base: {API_BASE}")
    
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()