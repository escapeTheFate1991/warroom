"""Authentication & authorization for the War Room.

Endpoints: signup, login, verify-email, forgot-password, reset-password, me, refresh.
JWT tokens with 7-day sessions. Email verification codes for signup + password reset.
Organization-aware: every authenticated user carries their org context.
"""
import logging
import time
import threading
import bcrypt
import jwt
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.user import User, Role
from app.models.crm.organization import Tenant as Organization
from app.config import settings
from app.services.email import (
    generate_code, send_verification_email, send_password_reset_email,
)

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)  # auto_error=False allows optional auth

# ── Config ──────────────────────────────────────────────────────────
JWT_SECRET = settings.JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
VERIFICATION_EXPIRE_MINUTES = 15
RESET_EXPIRE_MINUTES = 15

# ── Rate Limiting ────────────────────────────────────────────────────
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 15 * 60  # 15 minutes


class _RateLimiter:
    """Simple in-memory rate limiter for login attempts.
    
    LIMITATION: This is single-instance only - won't work in load-balanced deployments.
    For production scaling, replace with Redis-backed rate limiting.
    
    TODO: Migrate to distributed rate limiting solution when scaling beyond single instance.
    """

    def __init__(self):
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()

    def _cleanup(self):
        """Remove expired entries to prevent memory leaks."""
        now = time.monotonic()
        if now - self._last_cleanup < 60:  # cleanup at most once per minute
            return
        
        self._last_cleanup = now
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        keys_to_delete = []
        
        for key, timestamps in list(self._attempts.items()):
            # Filter out expired timestamps
            self._attempts[key] = [t for t in timestamps if t > cutoff]
            # Mark empty entries for deletion
            if not self._attempts[key]:
                keys_to_delete.append(key)
        
        # Delete empty entries to prevent memory leaks
        for key in keys_to_delete:
            del self._attempts[key]
        
        # Log cleanup stats for monitoring
        if keys_to_delete:
            logger.debug("Rate limiter cleanup: removed %d expired entries", len(keys_to_delete))

    def check(self, key: str) -> bool:
        """Record an attempt and return True if allowed, False if rate-limited.
        
        Args:
            key: Unique identifier for rate limiting (e.g., "email:user@example.com")
            
        Returns:
            True if request is allowed, False if rate-limited
        """
        with self._lock:
            self._cleanup()
            now = time.monotonic()
            cutoff = now - RATE_LIMIT_WINDOW_SECONDS
            
            # Filter expired attempts for this key
            self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]
            
            # Check if rate limit exceeded
            if len(self._attempts[key]) >= RATE_LIMIT_MAX_ATTEMPTS:
                logger.warning("Rate limit exceeded for key: %s", key)
                return False
            
            # Record this attempt
            self._attempts[key].append(now)
            return True


_login_limiter = _RateLimiter()


# ── Request/Response Models ──────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    invite_code: Optional[str] = None  # For org invites


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    email_verified: bool
    is_superadmin: bool
    org: Optional[dict] = None
    role: Optional[dict] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(user: User) -> tuple[str, int]:
    """Create JWT with user_id, email, org_id, role, superadmin flag. Returns (token, expires_in_seconds)."""
    expires_in = ACCESS_TOKEN_EXPIRE_DAYS * 86400
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "user_id": user.id,
        "email": user.email,
        "org_id": user.org_id,
        "is_superadmin": user.is_superadmin or False,
        "exp": expire,
    }
    if user.role:
        payload["role"] = user.role.name
        payload["permissions"] = user.role.permissions or []
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token, expires_in


def _user_dict(user: User) -> dict:
    """Serialize user for response."""
    result = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "email_verified": user.email_verified or False,
        "is_superadmin": user.is_superadmin or False,
    }
    if user.org:
        result["org"] = {"id": user.org.id, "name": user.org.name, "slug": user.org.slug}
    if user.role:
        result["role"] = {"id": user.role.id, "name": user.role.name, "permissions": user.role.permissions or []}
    return result


# ── Auth Dependency (used across all endpoints) ──────────────────────

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_tenant_db),
) -> User:
    """Extract and validate current user from JWT. Raises 401 if invalid."""
    org_id = get_org_id(request)
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        result = await db.execute(
            select(User)
            .options(selectinload(User.org), selectinload(User.role))
            .where(User.id == user_id, User.status == True)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or deactivated")
        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_tenant_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401."""
    org_id = get_org_id(request)
    if not credentials:
        return None
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


def require_permission(permission: str):
    """Dependency factory: require a specific RBAC permission."""
    async def checker(user: User = Depends(get_current_user)):
        if not user.has_permission(permission):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return user
    return checker


def require_superadmin():
    """Dependency: require superadmin status."""
    async def checker(user: User = Depends(get_current_user)):
        if not user.is_superadmin:
            raise HTTPException(status_code=403, detail="Superadmin access required")
        return user
    return checker


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(request: Request, data: SignupRequest, db: AsyncSession = Depends(get_tenant_db)):
    """Create account. Sends verification code to email."""
    org_id = get_org_id(request)
    # Check existing
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Password validation
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Create user
    code = generate_code()
    user = User(
        name=data.name,
        email=data.email,
        password_hash=_hash_password(data.password),
        email_verified=False,
        verification_code=code,
        verification_expires=datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_EXPIRE_MINUTES),
        status=True,
        login_count=0,
    )

    # Assign to org via invite code (future: lookup invite)
    # For now, first user becomes superadmin
    user_count = await db.execute(select(User))
    existing_users = user_count.scalars().all()
    if len(existing_users) == 0:
        user.is_superadmin = True

    # Assign default "member" role  
    role_result = await db.execute(select(Role).where(Role.name == "member").limit(1))
    member_role = role_result.scalar_one_or_none()
    if member_role:
        user.role_id = member_role.id

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Load relationships for token
    result = await db.execute(
        select(User).options(selectinload(User.org), selectinload(User.role)).where(User.id == user.id)
    )
    user = result.scalar_one()

    # Send verification email
    send_verification_email(data.email, data.name, code)

    token, expires_in = _create_token(user)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=_user_dict(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_tenant_db)):
    """Authenticate and return JWT. Token valid for 7 days from last login."""
    # Rate limit by email and IP
    client_ip = request.client.host if request.client else "unknown"
    if not _login_limiter.check(f"email:{data.email}"):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 15 minutes.")
    if not _login_limiter.check(f"ip:{client_ip}"):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 15 minutes.")

    result = await db.execute(
        select(User)
        .options(selectinload(User.org), selectinload(User.role))
        .where(User.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.status:
        raise HTTPException(status_code=403, detail="Account deactivated")

    if not _verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    user.login_count = (user.login_count or 0) + 1
    await db.commit()

    token, expires_in = _create_token(user)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=_user_dict(user),
    )


@router.post("/verify-email")
async def verify_email(request: Request, data: VerifyEmailRequest, db: AsyncSession = Depends(get_tenant_db)):
    """Verify email with 6-digit code."""
    org_id = get_org_id(request)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email_verified:
        return {"message": "Email already verified"}

    if not user.verification_code or user.verification_code != data.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    if user.verification_expires and user.verification_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired — request a new one")

    user.email_verified = True
    user.verification_code = None
    user.verification_expires = None
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_tenant_db)):
    """Resend email verification code."""
    org_id = get_org_id(request)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "If that email exists, a code has been sent"}  # Don't leak existence

    if user.email_verified:
        return {"message": "Email already verified"}

    code = generate_code()
    user.verification_code = code
    user.verification_expires = datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_EXPIRE_MINUTES)
    await db.commit()

    send_verification_email(user.email, user.name, code)
    return {"message": "Verification code sent"}


@router.post("/forgot-password")
async def forgot_password(request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_tenant_db)):
    """Send password reset code to email."""
    org_id = get_org_id(request)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Always return success (don't leak whether email exists)
    if not user:
        return {"message": "If that email exists, a reset code has been sent"}

    code = generate_code()
    user.reset_code = code
    user.reset_expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_EXPIRE_MINUTES)
    await db.commit()

    send_password_reset_email(user.email, user.name, code)
    return {"message": "If that email exists, a reset code has been sent"}


@router.post("/reset-password")
async def reset_password(request: Request, data: ResetPasswordRequest, db: AsyncSession = Depends(get_tenant_db)):
    """Reset password using code from email."""
    org_id = get_org_id(request)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset code")

    if not user.reset_code or user.reset_code != data.code:
        raise HTTPException(status_code=400, detail="Invalid reset code")

    if user.reset_expires and user.reset_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset code expired — request a new one")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.password_hash = _hash_password(data.new_password)
    user.reset_code = None
    user.reset_expires = None
    await db.commit()

    return {"message": "Password reset successfully — you can now log in"}


@router.post("/change-password")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Change password (requires current password)."""
    org_id = get_org_id(request)
    if not _verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.password_hash = _hash_password(data.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user profile with org and role."""
    return _user_dict(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user: User = Depends(get_current_user)):
    """Refresh JWT token (extends session by 7 more days)."""
    token, expires_in = _create_token(user)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=_user_dict(user),
    )
