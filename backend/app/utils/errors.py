"""Standard error response helpers for consistent API error handling.

Provides standardized error response format across all endpoints
and helper functions for common HTTP error scenarios.
"""
import logging
from typing import Optional, Any, Dict
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def api_error(status_code: int, detail: str, error_code: str = None) -> HTTPException:
    """Create standardized HTTP exception with consistent error format.
    
    Args:
        status_code: HTTP status code
        detail: Human-readable error message 
        error_code: Optional machine-readable error code
        
    Returns:
        HTTPException with standardized detail format
        
    Example:
        raise api_error(400, "Invalid email format", "VALIDATION_ERROR")
        # Returns: {"message": "Invalid email format", "code": "VALIDATION_ERROR"}
    """
    error_detail = {"message": detail}
    if error_code:
        error_detail["code"] = error_code
    
    return HTTPException(status_code=status_code, detail=error_detail)


def validation_error(message: str, field: str = None) -> HTTPException:
    """Standard validation error (400)."""
    error_code = "VALIDATION_ERROR"
    if field:
        error_code = f"VALIDATION_ERROR_{field.upper()}"
    return api_error(400, message, error_code)


def not_found_error(resource: str = "Resource") -> HTTPException:
    """Standard not found error (404)."""
    return api_error(404, f"{resource} not found", "NOT_FOUND")


def unauthorized_error(message: str = "Authentication required") -> HTTPException:
    """Standard unauthorized error (401)."""
    return api_error(401, message, "UNAUTHORIZED")


def forbidden_error(message: str = "Access forbidden") -> HTTPException:
    """Standard forbidden error (403)."""
    return api_error(403, message, "FORBIDDEN")


def conflict_error(message: str, resource: str = None) -> HTTPException:
    """Standard conflict error (409)."""
    error_code = "CONFLICT"
    if resource:
        error_code = f"CONFLICT_{resource.upper()}_EXISTS"
    return api_error(409, message, error_code)


def rate_limit_error(message: str = "Too many requests") -> HTTPException:
    """Standard rate limit error (429)."""
    return api_error(429, message, "RATE_LIMIT_EXCEEDED")


def internal_error(message: str = "An internal error occurred") -> HTTPException:
    """Standard internal server error (500)."""
    return api_error(500, message, "INTERNAL_ERROR")


def tenant_isolation_error() -> HTTPException:
    """Standard tenant isolation violation (403)."""
    return api_error(403, "Access denied - tenant isolation violation", "TENANT_ISOLATION")


def csrf_error() -> HTTPException:
    """Standard CSRF protection error (403)."""
    return api_error(403, "Invalid origin or referer header", "CSRF_VIOLATION")


def sanitize_error_for_production(error: Exception) -> Dict[str, Any]:
    """Sanitize error details for production - remove sensitive information.
    
    Args:
        error: Exception to sanitize
        
    Returns:
        Dict with sanitized error information safe for client consumption
    """
    # Log full error details for debugging
    logger.error("Internal error: %s", str(error), exc_info=True)
    
    # Return generic message to client (don't leak implementation details)
    return {
        "message": "An internal error occurred. Please try again later.",
        "code": "INTERNAL_ERROR"
    }