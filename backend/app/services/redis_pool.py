"""Redis connection pool for arq job queue.

Uses Redis database 2 to avoid conflicts with other services.
Reads REDIS_URL from env or falls back to localhost:6379/2.
"""

import logging
import os
from typing import Optional

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

logger = logging.getLogger(__name__)

_pool: Optional[ArqRedis] = None
_redis_available: Optional[bool] = None


def get_redis_settings() -> RedisSettings:
    """Parse REDIS_URL env var or return defaults."""
    url = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    # arq RedisSettings doesn't parse URLs directly — extract parts
    # Format: redis://host:port/db
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "2"),
        conn_timeout=5,
        conn_retries=1,
    )


REDIS_SETTINGS = get_redis_settings()


async def get_redis_pool() -> Optional[ArqRedis]:
    """Get or create the shared arq Redis pool.

    Returns None if Redis is unavailable (caller should fall back to asyncio).
    """
    global _pool, _redis_available

    # If we already know Redis is down, don't retry every call
    if _redis_available is False:
        return None

    if _pool is not None:
        try:
            await _pool.ping()
            return _pool
        except Exception:
            _pool = None

    try:
        _pool = await create_pool(REDIS_SETTINGS)
        _redis_available = True
        logger.info("Connected to Redis at %s:%d/%d", REDIS_SETTINGS.host, REDIS_SETTINGS.port, REDIS_SETTINGS.database)
        return _pool
    except Exception as exc:
        _redis_available = False
        _pool = None
        logger.warning("Redis unavailable (%s) — falling back to asyncio", exc)
        return None


async def check_redis() -> bool:
    """Check if Redis is reachable. Resets the cached availability flag."""
    global _redis_available
    _redis_available = None  # Reset so get_redis_pool retries
    pool = await get_redis_pool()
    return pool is not None


async def close_redis_pool() -> None:
    """Close the shared pool on shutdown."""
    global _pool, _redis_available
    if _pool:
        await _pool.close()
        _pool = None
    _redis_available = None
