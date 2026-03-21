#!/usr/bin/env python3
"""Test script for CDN migration endpoints."""

import requests
import time
import json

# Test configuration
BASE_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BASE_URL}/api/auth/login"
MIGRATION_ENDPOINT = f"{BASE_URL}/api/jobs/migrate-cdn-urls/test"
STATUS_ENDPOINT = f"{BASE_URL}/api/jobs/cdn-migration/status"

def test_migration():
    """Test the CDN migration endpoints."""
    
    # First, get an auth token (you'll need to replace these credentials)
    print("🔑 Getting auth token...")
    
    # For testing purposes, let's try without auth first to see the endpoints exist
    try:
        # Test status endpoint without auth
        print("📊 Testing status endpoint...")
        response = requests.get(STATUS_ENDPOINT)
        print(f"Status response: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
        
        # Test migration endpoint without auth  
        print("🧪 Testing migration endpoint...")
        response = requests.post(MIGRATION_ENDPOINT)
        print(f"Migration response: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend. Is it running on port 8000?")
        print("Start it with: cd /home/eddy/Development/warroom/backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_migration()