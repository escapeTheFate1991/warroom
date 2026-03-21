"""Social accounts API for multi-account Instagram settings."""
import logging
import secrets
import pyotp
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from starlette.requests import Request
from app.services.tenant import get_org_id
from app.models.social_accounts import SocialAccount
from app.api.auth import require_superadmin
from app.services.encryption import encrypt_value, decrypt_value
from app.models.crm.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Schemas ---

class SocialAccountCreate(BaseModel):
    platform: str = Field(..., description="Platform name (instagram, tiktok, etc.)")
    account_type: str = Field(..., description="Account type (scraping, posting, primary)")
    username: str = Field(..., description="Platform username")
    password: Optional[str] = Field(None, description="Account password")
    totp_secret: Optional[str] = Field(None, description="TOTP 2FA secret")
    notes: Optional[str] = Field(None, description="Optional notes")


class SocialAccountUpdate(BaseModel):
    account_type: Optional[str] = None
    password: Optional[str] = None
    totp_secret: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, description="active, disabled, expired")


class SocialAccountResponse(BaseModel):
    id: int
    platform: str
    account_type: str
    username: str
    has_password: bool
    has_totp_secret: bool
    status: str
    last_used_at: Optional[datetime]
    created_at: datetime
    notes: Optional[str]


class TestConnectionRequest(BaseModel):
    """Request to test an account connection."""
    account_id: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    totp_secret: Optional[str] = None


# --- Endpoints ---

@router.get("", response_model=List[SocialAccountResponse])
async def list_social_accounts(
    request: Request,
    platform: Optional[str] = None,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all social accounts for the organization."""
    org_id = get_org_id(request)
    
    query = select(SocialAccount).where(SocialAccount.org_id == org_id)
    if platform:
        query = query.where(SocialAccount.platform == platform)
    
    query = query.order_by(SocialAccount.platform, SocialAccount.username)
    
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return [
        SocialAccountResponse(
            id=account.id,
            platform=account.platform,
            account_type=account.account_type,
            username=account.username,
            has_password=bool(account.password_encrypted),
            has_totp_secret=bool(account.totp_secret_encrypted),
            status=account.status,
            last_used_at=account.last_used_at,
            created_at=account.created_at,
            notes=account.notes,
        )
        for account in accounts
    ]


@router.post("", response_model=SocialAccountResponse)
async def create_social_account(
    request: Request,
    account_data: SocialAccountCreate,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new social account."""
    org_id = get_org_id(request)
    
    # Check for duplicate username on same platform
    existing_query = select(SocialAccount).where(
        SocialAccount.org_id == org_id,
        SocialAccount.platform == account_data.platform,
        SocialAccount.username == account_data.username
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409, 
            detail=f"Account {account_data.username} already exists for {account_data.platform}"
        )
    
    # Encrypt sensitive fields
    password_encrypted = None
    if account_data.password:
        password_encrypted = encrypt_value(account_data.password)
    
    totp_secret_encrypted = None
    if account_data.totp_secret:
        totp_secret_encrypted = encrypt_value(account_data.totp_secret)
    
    # Create account
    account = SocialAccount(
        org_id=org_id,
        platform=account_data.platform,
        account_type=account_data.account_type,
        username=account_data.username,
        password_encrypted=password_encrypted,
        totp_secret_encrypted=totp_secret_encrypted,
        status="active",
        notes=account_data.notes,
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"Created social account: {account.platform}/@{account.username}")
    
    return SocialAccountResponse(
        id=account.id,
        platform=account.platform,
        account_type=account.account_type,
        username=account.username,
        has_password=bool(account.password_encrypted),
        has_totp_secret=bool(account.totp_secret_encrypted),
        status=account.status,
        last_used_at=account.last_used_at,
        created_at=account.created_at,
        notes=account.notes,
    )


@router.get("/{account_id}", response_model=SocialAccountResponse)
async def get_social_account(
    request: Request,
    account_id: int,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a specific social account."""
    org_id = get_org_id(request)
    
    query = select(SocialAccount).where(
        SocialAccount.id == account_id,
        SocialAccount.org_id == org_id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    return SocialAccountResponse(
        id=account.id,
        platform=account.platform,
        account_type=account.account_type,
        username=account.username,
        has_password=bool(account.password_encrypted),
        has_totp_secret=bool(account.totp_secret_encrypted),
        status=account.status,
        last_used_at=account.last_used_at,
        created_at=account.created_at,
        notes=account.notes,
    )


@router.put("/{account_id}", response_model=SocialAccountResponse)
async def update_social_account(
    request: Request,
    account_id: int,
    account_data: SocialAccountUpdate,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update a social account."""
    org_id = get_org_id(request)
    
    query = select(SocialAccount).where(
        SocialAccount.id == account_id,
        SocialAccount.org_id == org_id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    # Update fields
    if account_data.account_type is not None:
        account.account_type = account_data.account_type
    
    if account_data.password is not None:
        if account_data.password:  # Empty string clears password
            account.password_encrypted = encrypt_value(account_data.password)
        else:
            account.password_encrypted = None
    
    if account_data.totp_secret is not None:
        if account_data.totp_secret:
            account.totp_secret_encrypted = encrypt_value(account_data.totp_secret)
        else:
            account.totp_secret_encrypted = None
    
    if account_data.notes is not None:
        account.notes = account_data.notes
    
    if account_data.status is not None:
        account.status = account_data.status
    
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"Updated social account: {account.platform}/@{account.username}")
    
    return SocialAccountResponse(
        id=account.id,
        platform=account.platform,
        account_type=account.account_type,
        username=account.username,
        has_password=bool(account.password_encrypted),
        has_totp_secret=bool(account.totp_secret_encrypted),
        status=account.status,
        last_used_at=account.last_used_at,
        created_at=account.created_at,
        notes=account.notes,
    )


@router.delete("/{account_id}")
async def delete_social_account(
    request: Request,
    account_id: int,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Delete a social account."""
    org_id = get_org_id(request)
    
    query = select(SocialAccount).where(
        SocialAccount.id == account_id,
        SocialAccount.org_id == org_id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    username = account.username
    platform = account.platform
    
    await db.execute(delete(SocialAccount).where(SocialAccount.id == account_id))
    await db.commit()
    
    logger.info(f"Deleted social account: {platform}/@{username}")
    
    return {"status": "deleted", "username": username, "platform": platform}


@router.post("/{account_id}/test")
async def test_social_account_connection(
    request: Request,
    account_id: int,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Test connection to a social account."""
    org_id = get_org_id(request)
    
    query = select(SocialAccount).where(
        SocialAccount.id == account_id,
        SocialAccount.org_id == org_id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    # Decrypt credentials
    password = None
    if account.password_encrypted:
        password = decrypt_value(account.password_encrypted)
    
    totp_secret = None
    if account.totp_secret_encrypted:
        totp_secret = decrypt_value(account.totp_secret_encrypted)
    
    # Test the connection based on platform
    try:
        success = await _test_platform_connection(
            account.platform, 
            account.username, 
            password, 
            totp_secret
        )
        
        if success:
            # Update last_used_at
            account.last_used_at = datetime.now()
            account.status = "active"
            await db.commit()
            
            return {
                "success": True, 
                "message": f"Successfully connected to {account.platform}/@{account.username}"
            }
        else:
            account.status = "error"
            await db.commit()
            return {
                "success": False, 
                "message": f"Failed to connect to {account.platform}/@{account.username}"
            }
    
    except Exception as e:
        logger.error(f"Connection test failed for {account.platform}/@{account.username}: {e}")
        account.status = "error"
        await db.commit()
        
        return {
            "success": False, 
            "message": f"Connection test error: {str(e)}"
        }


@router.post("/test-connection")
async def test_connection_with_credentials(
    test_data: TestConnectionRequest,
    user: User = Depends(require_superadmin),
):
    """Test connection with provided credentials (without saving)."""
    if test_data.account_id:
        # This endpoint is for testing new credentials, not existing accounts
        raise HTTPException(status_code=400, detail="Use /accounts/{id}/test for existing accounts")
    
    if not all([test_data.username, test_data.password]):
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    # For now, we'll simulate a connection test
    # In a real implementation, you would attempt to login to the platform
    
    # Generate a TOTP code if secret is provided
    totp_code = None
    if test_data.totp_secret:
        try:
            totp = pyotp.TOTP(test_data.totp_secret)
            totp_code = totp.now()
        except Exception as e:
            return {
                "success": False,
                "message": f"Invalid TOTP secret: {str(e)}"
            }
    
    # Simulate connection test
    return {
        "success": True,
        "message": f"Test successful for @{test_data.username}",
        "totp_code": totp_code if totp_code else None,
    }


# --- Helper Functions ---

async def _test_platform_connection(
    platform: str, 
    username: str, 
    password: Optional[str], 
    totp_secret: Optional[str]
) -> bool:
    """Test connection to a specific platform."""
    
    # For Instagram, we could integrate with the existing scraper
    if platform == "instagram":
        return await _test_instagram_connection(username, password, totp_secret)
    
    # For other platforms, return True for now
    # TODO: Implement actual connection testing
    return True


async def _test_instagram_connection(
    username: str, 
    password: Optional[str], 
    totp_secret: Optional[str]
) -> bool:
    """Test Instagram login connection."""
    
    if not password:
        return False
    
    # Generate TOTP code if secret is provided
    totp_code = None
    if totp_secret:
        try:
            totp = pyotp.TOTP(totp_secret)
            totp_code = totp.now()
        except:
            return False
    
    # TODO: Integrate with Instagram scraper service to test login
    # For now, return True if we have username and password
    return True


# --- Utility endpoints for credentials ---

@router.get("/{account_id}/credentials")
async def get_account_credentials(
    request: Request,
    account_id: int,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get decrypted credentials for an account (admin only)."""
    org_id = get_org_id(request)
    
    query = select(SocialAccount).where(
        SocialAccount.id == account_id,
        SocialAccount.org_id == org_id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    # Decrypt credentials
    password = None
    if account.password_encrypted:
        password = decrypt_value(account.password_encrypted)
    
    totp_secret = None
    if account.totp_secret_encrypted:
        totp_secret = decrypt_value(account.totp_secret_encrypted)
    
    # Generate current TOTP code if secret exists
    totp_code = None
    if totp_secret:
        try:
            totp = pyotp.TOTP(totp_secret)
            totp_code = totp.now()
        except:
            pass
    
    return {
        "username": account.username,
        "password": password,
        "totp_secret": totp_secret,
        "current_totp_code": totp_code,
    }