"""CSRF Protection Middleware

Provides CSRF protection for state-changing operations through:
1. Origin/Referer header validation for JWT-based APIs
2. SameSite cookie enforcement where applicable

Note: Since this API uses JWT tokens (not cookie-based sessions), 
traditional CSRF risks are reduced. However, this provides defense
in depth against malicious cross-origin requests.
"""
import logging
from typing import List
from urllib.parse import urlparse

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Allowed origins for CSRF protection
ALLOWED_ORIGINS = [
    "https://warroom.stuffnthings.io",
    "https://stuffnthings.io", 
    "https://www.stuffnthings.io",
    "http://localhost:3300",
    "http://localhost:3000",
    "http://192.168.1.94:3300",
]

# Methods that require CSRF protection
CSRF_PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Endpoints that should bypass CSRF (public webhooks, etc.)
CSRF_EXEMPT_PATHS = [
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/contact-webhook",
    "/api/telnyx/webhook",
    "/api/twilio/webhook",
    "/health",
]


class CSRFGuardMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations."""
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ALLOWED_ORIGINS
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method not in CSRF_PROTECTED_METHODS:
            return await call_next(request)
        
        # Skip CSRF check for exempt paths
        if any(request.url.path.startswith(path) for path in CSRF_EXEMPT_PATHS):
            return await call_next(request)
        
        # Validate Origin or Referer header
        if not self._validate_origin(request):
            logger.warning(
                "CSRF validation failed - invalid origin/referer: %s %s", 
                request.method, 
                request.url.path
            )
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid origin or referer header", "code": "CSRF_VIOLATION"}
            )
        
        return await call_next(request)
    
    def _validate_origin(self, request: Request) -> bool:
        """Validate Origin or Referer header against allowed origins."""
        # Check Origin header first (more reliable)
        origin = request.headers.get("origin")
        if origin:
            return self._is_allowed_origin(origin)
        
        # Fallback to Referer header
        referer = request.headers.get("referer")
        if referer:
            parsed_referer = urlparse(referer)
            origin_from_referer = f"{parsed_referer.scheme}://{parsed_referer.netloc}"
            return self._is_allowed_origin(origin_from_referer)
        
        # No Origin or Referer header - reject for security
        # Note: Some legitimate API clients might not send these headers,
        # but for web applications this is required for CSRF protection
        logger.warning("Request missing both Origin and Referer headers")
        return False
    
    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is in the allowed list."""
        # Normalize origin (remove trailing slash)
        origin = origin.rstrip("/")
        
        for allowed in self.allowed_origins:
            allowed = allowed.rstrip("/")
            if origin == allowed:
                return True
        
        return False