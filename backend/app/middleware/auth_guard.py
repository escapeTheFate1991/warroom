"""Global authentication middleware for the War Room API.

Enforces JWT auth on ALL /api/* routes except explicitly whitelisted paths.
This prevents any endpoint from accidentally being publicly accessible.
"""
import logging
import re

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

JWT_SECRET = settings.JWT_SECRET
ALGORITHM = "HS256"

# ── Public paths (no auth required) ──────────────────────────────────
# Exact matches
PUBLIC_PATHS = {
    # Auth endpoints
    "/api/auth/login",
    "/api/auth/signup",
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    # Health check
    "/health",
    "/api/health",
    # SSE (uses ?token= query param for auth)
    "/api/notifications/stream",
    # Contact form webhook (public-facing)
    "/api/webhooks/contact",
    # Telnyx voice webhook (public-facing)
    "/api/telnyx/webhook",
    # Twilio voice webhooks (public-facing, called by Twilio)
    "/api/twilio/voice/welcome",
    "/api/twilio/voice/gather-tasks",
    "/api/twilio/voice/gather-services",
    "/api/twilio/voice/gather-schedule",
    "/api/twilio/voice/complete",
    "/api/twilio/voice/status",
}

# Prefix matches (OAuth callbacks only — authorize endpoints require auth
# because they're called from inside the app with a valid session)
PUBLIC_PREFIXES = [
    "/api/social/oauth/meta/callback",
    "/api/social/oauth/instagram/callback",
    "/api/social/oauth/threads/callback",
    "/api/social/oauth/x/callback",
    "/api/social/oauth/tiktok/callback",
    "/api/social/oauth/google/callback",
    "/api/calendar/google/callback",
    "/api/email/accounts/gmail/callback",
]

# Regex patterns for dynamic public paths
PUBLIC_PATTERNS = [
    re.compile(r"^/api/social/oauth/\w+/callback$"),  # Only callbacks, not authorize
]


def _is_public(path: str) -> bool:
    """Check if the request path is in the public whitelist."""
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    for pattern in PUBLIC_PATTERNS:
        if pattern.match(path):
            return True
    return False


def _validate_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        if not payload.get("user_id"):
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


class AuthGuardMiddleware(BaseHTTPMiddleware):
    """Require valid JWT for all /api/* routes unless whitelisted."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Non-API routes (frontend pages, static files) — pass through
        if not path.startswith("/api"):
            return await call_next(request)

        # Public API paths — pass through
        if _is_public(path):
            return await call_next(request)

        # OPTIONS (CORS preflight) — pass through
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
            )

        token = auth_header[7:]  # Strip "Bearer "
        payload = _validate_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        # Attach user info to request state for downstream use
        request.state.user_id = payload["user_id"]
        request.state.user_email = payload.get("email")
        request.state.org_id = payload.get("org_id")
        request.state.is_superadmin = payload.get("is_superadmin", False)

        return await call_next(request)
