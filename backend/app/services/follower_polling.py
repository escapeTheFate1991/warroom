"""
Instagram Follower Polling Service
Periodically checks for new followers via Graph API and triggers auto-reply DMs.
Respects Meta's rate limits (200 DMs/hr) and 24-hour messaging window.

Since Instagram Graph API doesn't expose a direct /followers list endpoint,
this service tracks follower_count changes and captures individual follower
identities from message interactions, comments, etc.
"""
import logging
import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import crm_session
from app.models.crm.social import SocialAccount
from app.services.social_inbox_processor import process_follow

logger = logging.getLogger(__name__)

IG_GRAPH_API = "https://graph.instagram.com/v21.0"

# Rate limiting: Track API calls per account
_api_call_timestamps: Dict[str, List[float]] = {}
MAX_API_CALLS_PER_HOUR = 200
API_CALL_WINDOW = 3600  # 1 hour in seconds


def _is_api_rate_limited(account_key: str) -> bool:
    """Check if an account has exceeded the Instagram API rate limit."""
    now = time.time()
    
    if account_key not in _api_call_timestamps:
        _api_call_timestamps[account_key] = []
    
    # Remove calls older than 1 hour
    _api_call_timestamps[account_key] = [
        ts for ts in _api_call_timestamps[account_key] 
        if now - ts < API_CALL_WINDOW
    ]
    
    return len(_api_call_timestamps[account_key]) >= MAX_API_CALLS_PER_HOUR


def _record_api_call(account_key: str):
    """Record an API call timestamp for rate limiting."""
    if account_key not in _api_call_timestamps:
        _api_call_timestamps[account_key] = []
    _api_call_timestamps[account_key].append(time.time())


async def _get_instagram_profile_stats(access_token: str) -> Optional[Dict]:
    """Fetch Instagram profile stats including follower count."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{IG_GRAPH_API}/me",
                params={
                    "fields": "id,username,followers_count,follows_count,media_count",
                    "access_token": access_token,
                }
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error("Instagram profile API error: %s %s", resp.status_code, resp.text[:200])
                return None
    except Exception as exc:
        logger.error("Failed to fetch Instagram profile: %s", exc)
        return None


async def _get_stored_follower_count(db: AsyncSession, social_account_id: int) -> int:
    """Get the last known follower count from the social_accounts table."""
    try:
        result = await db.execute(
            select(SocialAccount.follower_count)
            .where(SocialAccount.id == social_account_id)
        )
        row = result.scalar_one_or_none()
        return row or 0
    except Exception as exc:
        logger.error("Failed to get stored follower count: %s", exc)
        return 0


async def _update_follower_count(db: AsyncSession, social_account_id: int, org_id: int, new_count: int):
    """Update the follower count in social_accounts table."""
    try:
        await db.execute(
            text("UPDATE crm.social_accounts SET follower_count = :count, last_synced = NOW() WHERE id = :id AND org_id = :org_id"),
            {"count": new_count, "id": social_account_id, "org_id": org_id}
        )
        await db.commit()
    except Exception as exc:
        logger.error("Failed to update follower count: %s", exc)


async def _get_known_followers(db: AsyncSession, social_account_id: int) -> set:
    """Get set of known follower IG IDs from the instagram_followers table."""
    try:
        result = await db.execute(
            text("SELECT follower_ig_id FROM crm.instagram_followers WHERE social_account_id = :account_id"),
            {"account_id": social_account_id}
        )
        return {row[0] for row in result.fetchall()}
    except Exception as exc:
        logger.error("Failed to get known followers: %s", exc)
        return set()


async def _add_new_follower(
    db: AsyncSession, 
    social_account_id: int, 
    follower_ig_id: str, 
    follower_username: str = None
):
    """Add a new follower to the instagram_followers table."""
    try:
        await db.execute(
            text("""
                INSERT INTO crm.instagram_followers 
                (social_account_id, follower_ig_id, follower_username, detected_at) 
                VALUES (:account_id, :ig_id, :username, NOW())
                ON CONFLICT (social_account_id, follower_ig_id) DO NOTHING
            """),
            {
                "account_id": social_account_id,
                "ig_id": follower_ig_id,
                "username": follower_username
            }
        )
        await db.commit()
        logger.info("Added new follower %s (username: %s) to account %s", 
                   follower_ig_id, follower_username, social_account_id)
        return True
    except Exception as exc:
        logger.error("Failed to add new follower: %s", exc)
        return False


async def poll_new_followers(social_account_id: int) -> Dict:
    """
    Main function to poll for new followers on a specific Instagram account.
    
    Strategy:
    1. Check current follower_count via Graph API
    2. Compare against stored count to detect increase
    3. If increase detected, we know new followers joined but can't get their IDs directly
    4. Individual follower IDs will be captured when they interact (comment, DM, etc.)
    5. For now, log the follower count change for monitoring
    
    Returns summary of polling results.
    """
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            
            # Get account details
            result = await db.execute(
                select(SocialAccount)
                .where(SocialAccount.id == social_account_id)
                .where(SocialAccount.platform == 'instagram')
                .where(SocialAccount.status == 'connected')
            )
            account = result.scalar_one_or_none()
            
            if not account:
                return {"success": False, "error": "Account not found or not connected"}
            
            account_key = f"poll:{social_account_id}"
            
            # Rate limiting check
            if _is_api_rate_limited(account_key):
                logger.warning("API rate limited for account %s", social_account_id)
                return {"success": False, "error": "rate_limited"}
            
            # Fetch current profile stats
            _record_api_call(account_key)
            profile_data = await _get_instagram_profile_stats(account.access_token)
            
            if not profile_data:
                return {"success": False, "error": "Failed to fetch profile data"}
            
            current_count = profile_data.get("followers_count", 0)
            stored_count = await _get_stored_follower_count(db, social_account_id)
            
            # Update stored count
            await _update_follower_count(db, social_account_id, account.org_id, current_count)
            
            result_data = {
                "success": True,
                "account_id": social_account_id,
                "username": account.username,
                "current_followers": current_count,
                "previous_followers": stored_count,
                "follower_change": current_count - stored_count,
                "new_followers_detected": max(0, current_count - stored_count)
            }
            
            # If follower count increased, log the change
            if current_count > stored_count:
                new_followers = current_count - stored_count
                logger.info(
                    "Follower count increased for @%s: %d -> %d (+%d new followers)",
                    account.username, stored_count, current_count, new_followers
                )
                result_data["message"] = f"Detected {new_followers} new follower(s)"
                
                # Note: We can't directly identify the new followers from this API
                # They will be captured and processed when they interact via comments/DMs
                # through the existing webhook system in social_inbox_processor.py
            else:
                result_data["message"] = "No new followers detected"
            
            return result_data
            
    except Exception as exc:
        logger.error("Error polling followers for account %s: %s", social_account_id, exc)
        return {"success": False, "error": str(exc)}


async def capture_follower_from_interaction(
    social_account_id: int,
    user_ig_id: str,
    username: str = None,
    trigger_auto_reply: bool = True
) -> bool:
    """
    Capture a follower's identity from an interaction (comment, DM, etc.).
    This is called by webhook processors when they detect user interactions.
    
    If trigger_auto_reply=True and this is a new follower, triggers follow auto-reply rules.
    """
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            
            # Check if we already know this follower
            result = await db.execute(
                text("SELECT id FROM crm.instagram_followers WHERE social_account_id = :account_id AND follower_ig_id = :ig_id"),
                {"account_id": social_account_id, "ig_id": user_ig_id}
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Already known follower, just update username if provided
                if username:
                    await db.execute(
                        text("UPDATE crm.instagram_followers SET follower_username = :username WHERE id = :id"),
                        {"username": username, "id": existing}
                    )
                    await db.commit()
                return False  # Not a new follower
            
            # New follower - add to database
            success = await _add_new_follower(db, social_account_id, user_ig_id, username)
            
            if success and trigger_auto_reply:
                # Get account username for identifying the page
                result = await db.execute(
                    text("SELECT username FROM crm.social_accounts WHERE id = :id"),
                    {"id": social_account_id}
                )
                account_data = result.first()
                
                if account_data:
                    # Use "me" as page_id since that's the standard for business accounts
                    page_id = "me"
                    
                    # Trigger follow auto-reply processing
                    await process_follow(
                        page_id=page_id,
                        user_id=user_ig_id,
                        username=username or user_ig_id
                    )
                    logger.info("Triggered follow auto-reply for new follower %s", username or user_ig_id)
            
            return success
            
    except Exception as exc:
        logger.error("Error capturing follower interaction: %s", exc)
        return False


async def poll_all_accounts() -> Dict:
    """
    Poll all connected Instagram accounts for follower changes.
    Called by the scheduler every hour.
    """
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            
            # Get all connected Instagram accounts
            result = await db.execute(
                select(SocialAccount.id, SocialAccount.username, SocialAccount.org_id)
                .where(SocialAccount.platform == 'instagram')
                .where(SocialAccount.status == 'connected')
            )
            accounts = result.fetchall()
            
            if not accounts:
                logger.info("No connected Instagram accounts to poll")
                return {"success": True, "accounts_polled": 0, "results": []}
            
            results = []
            
            for account_id, username, org_id in accounts:
                logger.info("Polling followers for Instagram account @%s (ID: %d)", username, account_id)
                
                # Add delay between accounts to respect rate limits
                if results:  # Not the first account
                    await asyncio.sleep(2)
                
                account_result = await poll_new_followers(account_id)
                account_result["username"] = username
                results.append(account_result)
                
                # Log summary
                if account_result.get("success"):
                    change = account_result.get("follower_change", 0)
                    if change > 0:
                        logger.info("@%s: +%d new followers", username, change)
                    elif change < 0:
                        logger.info("@%s: %d followers lost", username, abs(change))
                    else:
                        logger.debug("@%s: no follower changes", username)
                else:
                    logger.warning("@%s: polling failed - %s", username, account_result.get("error"))
            
            total_new_followers = sum(r.get("new_followers_detected", 0) for r in results)
            
            return {
                "success": True,
                "accounts_polled": len(accounts),
                "total_new_followers": total_new_followers,
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as exc:
        logger.error("Error in poll_all_accounts: %s", exc)
        return {"success": False, "error": str(exc), "accounts_polled": 0, "results": []}


# Optional: Function to manually trigger follower capture for testing
async def test_capture_follower(social_account_id: int, test_user_id: str, test_username: str = None):
    """Test function to manually capture a follower and trigger auto-reply."""
    logger.info("Testing follower capture for account %d, user %s", social_account_id, test_user_id)
    result = await capture_follower_from_interaction(
        social_account_id=social_account_id,
        user_ig_id=test_user_id,
        username=test_username,
        trigger_auto_reply=True
    )
    logger.info("Test capture result: %s", result)
    return result