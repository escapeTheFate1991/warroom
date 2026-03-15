"""Multi-tenant isolation middleware for the War Room API.

Runs AFTER AuthGuardMiddleware. Ensures every authenticated request
has a valid org_id, and makes it available for downstream DB queries.

Superadmins (platform-level) can operate without an org_id for
cross-tenant administration.
"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def get_current_org_id(request: Request) -> int:
    """Extract org_id from request state. Raises 403-equivalent if missing.

    Use in route handlers:
        org_id = get_current_org_id(request)
    """
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        # Superadmins may not have org_id — callers should check is_superadmin
        is_superadmin = getattr(request.state, "is_superadmin", False)
        if is_superadmin:
            return None
        raise ValueError("No organization assigned to this user")
    return int(org_id)


class TenantGuardMiddleware(BaseHTTPMiddleware):
    """Enforce org_id on all authenticated /api/* requests.

    - If user has org_id → passes through (org_id already on request.state)
    - If user is superadmin with no org_id → passes through (platform admin)
    - If user has no org_id and is not superadmin → 403
    - Non-API and unauthenticated routes → passes through (handled by AuthGuard)
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only enforce on API routes
        if not path.startswith("/api"):
            return await call_next(request)

        # Skip if no user_id set (unauthenticated — AuthGuard handles this)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return await call_next(request)

        # Check org_id
        org_id = getattr(request.state, "org_id", None)
        is_superadmin = getattr(request.state, "is_superadmin", False)

        if not org_id and not is_superadmin:
            logger.warning(
                "User %s has no org_id and is not superadmin — blocking request to %s",
                user_id,
                path,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "No organization assigned. Contact your administrator."
                },
            )

        return await call_next(request)
