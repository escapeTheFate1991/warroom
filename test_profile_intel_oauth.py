#!/usr/bin/env python3
"""Test Profile Intel OAuth detection directly."""

import asyncio
import sys
import os

# Add the app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from sqlalchemy import text
from app.db.crm_db import crm_session
from app.services.profile_intel_service import profile_intel_service

async def test_oauth_detection():
    """Test if Profile Intel can detect the OAuth connection."""
    async with crm_session() as db:
        print("🔍 Testing Profile Intel OAuth detection...")
        
        # Check what social accounts we have
        result = await db.execute(text("""
            SELECT id, org_id, user_id, platform, username, status 
            FROM crm.social_accounts 
            WHERE platform = 'instagram' AND status = 'connected'
        """))
        accounts = result.fetchall()
        
        print(f"\n📱 Found {len(accounts)} connected Instagram accounts:")
        for acc in accounts:
            print(f"   ID: {acc.id}, Org: {acc.org_id}, User: {acc.user_id}, Username: {acc.username}")
        
        if not accounts:
            print("❌ No connected Instagram accounts found!")
            return
        
        # Test with the first account
        account = accounts[0]
        org_id = account.org_id
        user_id = account.user_id
        username = account.username
        
        print(f"\n🧪 Testing OAuth detection for user {user_id}, username '{username}'...")
        
        # Test the _fetch_user_oauth_data method directly
        oauth_data = await profile_intel_service._fetch_user_oauth_data(
            db, org_id, username, "instagram", user_id
        )
        
        if oauth_data:
            print("✅ SUCCESS: OAuth data detected!")
            print(f"   Follower Count: {oauth_data.get('followerCount', 'N/A')}")
            print(f"   Engagement Rate: {oauth_data.get('engagementRate', 'N/A')}")
            print(f"   Reply Rate: {oauth_data.get('replyRate', 'N/A')}")
            print(f"   Keys: {list(oauth_data.keys())}")
        else:
            print("❌ FAILED: OAuth data is None")
            
            # Debug: try the old query pattern
            print("\n🔧 Debug: Testing old query pattern...")
            from sqlalchemy import select, and_
            from app.models.crm.social import SocialAccount
            
            old_result = await db.execute(
                select(SocialAccount).where(
                    and_(
                        SocialAccount.org_id == org_id,
                        SocialAccount.platform == "instagram",
                        SocialAccount.username == username,
                        SocialAccount.status == "connected"
                    )
                )
            )
            old_account = old_result.scalar_one_or_none()
            print(f"   Old pattern result: {'Found' if old_account else 'Not found'}")
            
            # Debug: try the new query pattern
            print("\n🔧 Debug: Testing new query pattern...")
            new_result = await db.execute(
                select(SocialAccount).where(
                    and_(
                        SocialAccount.user_id == user_id,
                        SocialAccount.org_id == org_id,
                        SocialAccount.platform == "instagram",
                        SocialAccount.status == "connected"
                    )
                )
            )
            new_account = new_result.scalar_one_or_none()
            print(f"   New pattern result: {'Found' if new_account else 'Not found'}")
            if new_account:
                print(f"   Found account: {new_account.username}, ID: {new_account.id}")

if __name__ == "__main__":
    asyncio.run(test_oauth_detection())