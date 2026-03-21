"""Instagram Account Manager for multi-account scraping support."""
import logging
import pyotp
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_accounts import SocialAccount
from app.services.encryption import decrypt_value

logger = logging.getLogger(__name__)


class InstagramAccountManager:
    """Manages Instagram accounts for scraping operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_active_account(self, account_type: str = "scraping") -> Optional[dict]:
        """Get an active Instagram account for the specified type."""
        query = select(SocialAccount).where(
            SocialAccount.platform == "instagram",
            SocialAccount.account_type == account_type,
            SocialAccount.status == "active"
        ).order_by(SocialAccount.last_used_at.asc().nulls_first())
        
        result = await self.db.execute(query)
        account = result.scalar_one_or_none()
        
        if not account:
            return None
        
        # Decrypt credentials
        password = None
        if account.password_encrypted:
            password = decrypt_value(account.password_encrypted)
        
        totp_secret = None
        if account.totp_secret_encrypted:
            totp_secret = decrypt_value(account.totp_secret_encrypted)
        
        return {
            "id": account.id,
            "username": account.username,
            "password": password,
            "totp_secret": totp_secret,
            "notes": account.notes,
        }
    
    async def get_all_accounts(self, account_type: str = "scraping") -> List[dict]:
        """Get all active Instagram accounts for rotation."""
        query = select(SocialAccount).where(
            SocialAccount.platform == "instagram",
            SocialAccount.account_type == account_type,
            SocialAccount.status == "active"
        ).order_by(SocialAccount.last_used_at.asc().nulls_first())
        
        result = await self.db.execute(query)
        accounts = result.scalars().all()
        
        account_list = []
        for account in accounts:
            password = None
            if account.password_encrypted:
                password = decrypt_value(account.password_encrypted)
            
            totp_secret = None
            if account.totp_secret_encrypted:
                totp_secret = decrypt_value(account.totp_secret_encrypted)
            
            account_list.append({
                "id": account.id,
                "username": account.username,
                "password": password,
                "totp_secret": totp_secret,
                "notes": account.notes,
            })
        
        return account_list
    
    async def mark_account_used(self, account_id: int):
        """Update the last_used_at timestamp for an account."""
        query = update(SocialAccount).where(
            SocialAccount.id == account_id
        ).values(
            last_used_at=datetime.now(),
            status="active"
        )
        
        await self.db.execute(query)
        await self.db.commit()
    
    async def mark_account_error(self, account_id: int, error_msg: Optional[str] = None):
        """Mark an account as having an error."""
        query = update(SocialAccount).where(
            SocialAccount.id == account_id
        ).values(
            status="error"
        )
        
        if error_msg:
            # Optionally update notes with error message
            query = query.values(notes=error_msg)
        
        await self.db.execute(query)
        await self.db.commit()
    
    def generate_totp_code(self, secret: str) -> Optional[str]:
        """Generate a TOTP code from a secret."""
        if not secret:
            return None
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.now()
        except Exception as e:
            logger.error(f"Failed to generate TOTP code: {e}")
            return None
    
    async def rotate_to_next_account(self, current_account_id: int, account_type: str = "scraping") -> Optional[dict]:
        """Get the next account in rotation after the current one fails."""
        # Mark current account as having an error
        await self.mark_account_error(current_account_id, "Rotated due to error")
        
        # Get all other active accounts
        query = select(SocialAccount).where(
            SocialAccount.platform == "instagram",
            SocialAccount.account_type == account_type,
            SocialAccount.status == "active",
            SocialAccount.id != current_account_id
        ).order_by(SocialAccount.last_used_at.asc().nulls_first())
        
        result = await self.db.execute(query)
        account = result.scalar_one_or_none()
        
        if not account:
            logger.warning(f"No other active {account_type} Instagram accounts available for rotation")
            return None
        
        # Decrypt credentials
        password = None
        if account.password_encrypted:
            password = decrypt_value(account.password_encrypted)
        
        totp_secret = None
        if account.totp_secret_encrypted:
            totp_secret = decrypt_value(account.totp_secret_encrypted)
        
        logger.info(f"Rotated to Instagram account @{account.username} for {account_type}")
        
        return {
            "id": account.id,
            "username": account.username,
            "password": password,
            "totp_secret": totp_secret,
            "notes": account.notes,
        }


async def get_instagram_credentials_for_scraping() -> Tuple[Optional[str], Optional[str], Optional[str], Optional[int]]:
    """
    Get Instagram credentials for scraping. 
    Returns (username, password, totp_secret, account_id) or (None, None, None, None).
    
    This is the main integration point with the existing instagram_scraper.py.
    """
    from app.db.crm_db import get_tenant_session
    from app.config import settings
    
    # First try environment variables (for backward compatibility)
    username = getattr(settings, 'INSTAGRAM_USERNAME', None)
    password = getattr(settings, 'INSTAGRAM_PASSWORD', None)
    totp_secret = getattr(settings, 'INSTAGRAM_TOTP_SECRET', None)
    
    if username and password:
        logger.info("Using Instagram credentials from environment variables")
        return username, password, totp_secret, None
    
    # Try new social accounts system
    try:
        async with get_tenant_session() as db:
            manager = InstagramAccountManager(db)
            account = await manager.get_active_account("scraping")
            
            if account and account["password"]:
                logger.info(f"Using Instagram account @{account['username']} from social accounts")
                return account["username"], account["password"], account["totp_secret"], account["id"]
    
    except Exception as e:
        logger.warning(f"Failed to get Instagram account from social accounts: {e}")
    
    # Fall back to old settings table (for backward compatibility)
    try:
        from sqlalchemy import text as sa_text
        from sqlalchemy.ext.asyncio import create_async_engine
        
        engine = create_async_engine(settings.CRM_DB_URL, echo=False)
        async with engine.connect() as conn:
            for key, attr in [
                ("instagram_scraper_username", "username"), 
                ("instagram_scraper_password", "password"), 
                ("instagram_totp_secret", "totp")
            ]:
                r = await conn.execute(
                    sa_text(f"SELECT value FROM public.settings WHERE key = :k AND value != ''"), 
                    {"k": key}
                )
                row = r.first()
                if row:
                    if attr == "username":
                        username = row[0]
                    elif attr == "password":
                        password = row[0]
                    elif attr == "totp":
                        totp_secret = row[0]
        
        await engine.dispose()
        
        if username and password:
            logger.info("Using Instagram credentials from legacy settings table")
            return username, password, totp_secret, None
    
    except Exception as e:
        logger.warning(f"Failed to get Instagram credentials from settings: {e}")
    
    return None, None, None, None


async def mark_instagram_account_used(account_id: Optional[int]):
    """Mark an Instagram account as used (if account_id is provided)."""
    if not account_id:
        return
    
    try:
        from app.db.crm_db import get_tenant_session
        
        async with get_tenant_session() as db:
            manager = InstagramAccountManager(db)
            await manager.mark_account_used(account_id)
    
    except Exception as e:
        logger.warning(f"Failed to mark Instagram account as used: {e}")


async def mark_instagram_account_error(account_id: Optional[int], error_msg: Optional[str] = None):
    """Mark an Instagram account as having an error (if account_id is provided)."""
    if not account_id:
        return
    
    try:
        from app.db.crm_db import get_tenant_session
        
        async with get_tenant_session() as db:
            manager = InstagramAccountManager(db)
            await manager.mark_account_error(account_id, error_msg)
    
    except Exception as e:
        logger.warning(f"Failed to mark Instagram account error: {e}")


async def rotate_instagram_account(current_account_id: Optional[int]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[int]]:
    """
    Rotate to the next Instagram account after the current one fails.
    Returns new credentials or (None, None, None, None) if no accounts available.
    """
    if not current_account_id:
        return None, None, None, None
    
    try:
        from app.db.crm_db import get_tenant_session
        
        async with get_tenant_session() as db:
            manager = InstagramAccountManager(db)
            account = await manager.rotate_to_next_account(current_account_id, "scraping")
            
            if account:
                return account["username"], account["password"], account["totp_secret"], account["id"]
    
    except Exception as e:
        logger.warning(f"Failed to rotate Instagram account: {e}")
    
    return None, None, None, None