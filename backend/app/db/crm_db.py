"""Database configuration for CRM module.

Two DB dependencies are available:

  get_crm_db()     — Original. Sets search_path only. Use for backward
                     compatibility with existing endpoints.

  get_tenant_db()  — Tenant-aware. Sets search_path AND app.current_org_id
                     from the request. New endpoints should use this so that
                     all queries can be filtered by org_id automatically.

Migration path: move endpoints from get_crm_db → get_tenant_db one at a time.
Once all endpoints are migrated, deprecate get_crm_db.
"""
import logging
from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event, text

from app.config import settings

logger = logging.getLogger(__name__)

# Reuse knowledge DB connection (same as leadgen_db.py pattern)
CRM_DB_URL = settings.CRM_DB_URL

crm_engine = create_async_engine(CRM_DB_URL, echo=False, pool_size=5, max_overflow=10)
crm_session = async_sessionmaker(crm_engine, class_=AsyncSession, expire_on_commit=False)


# For async engines, we'll set search_path in get_crm_db instead of using events


async def get_crm_db():
    """Database dependency for CRM — original, no tenant filtering."""
    async with crm_session() as session:
        await session.execute(text("SET search_path TO crm, public"))
        yield session


async def get_tenant_db(request: Request):
    """Tenant-aware database dependency.

    Sets search_path AND app.current_org_id so downstream queries can
    filter by org. Uses SET LOCAL so the setting is scoped to the
    current transaction and doesn't leak across connections.

    Usage in a route:
        @router.get("/api/deals")
        async def list_deals(db=Depends(get_tenant_db)):
            result = await db.execute(
                text("SELECT * FROM deals WHERE org_id = current_setting('app.current_org_id')::int")
            )
    """
    org_id = getattr(request.state, "org_id", None)

    async with crm_session() as session:
        await session.execute(text("SET search_path TO crm, public"))
        if org_id:
            # SET LOCAL scopes to current transaction — no cross-request leakage
            # NOTE: SET cannot use parameterized queries in asyncpg, so we
            # sanitize by casting to int first (prevents SQL injection)
            safe_org_id = int(org_id)
            await session.execute(
                text(f"SET LOCAL app.current_org_id = '{safe_org_id}'")
            )
        yield session


async def init_crm_schema():
    """Initialize CRM schema by reading and executing crm_schema.sql."""
    schema_file = Path(__file__).parent / "crm_schema.sql"
    
    if not schema_file.exists():
        raise FileNotFoundError(f"CRM schema file not found: {schema_file}")
    
    try:
        # Read the schema SQL
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema using session
        async with crm_session() as session:
            await session.execute(text("SET search_path TO crm, public"))
            await session.execute(text(schema_sql))
            await session.commit()
        
        logger.info("CRM schema initialized successfully")
        return True
        
    except Exception as e:
        logger.error("Failed to initialize CRM schema: %s", e)
        return False


async def run_multi_tenant_migration():
    """Run the multi-tenant migration (adds org_id to all tables).

    Safe to run multiple times — all statements are idempotent (IF NOT EXISTS).
    Uses raw asyncpg connection to execute multi-statement SQL (asyncpg's
    prepared statement mode doesn't support multiple commands).
    """
    migration_file = Path(__file__).parent / "multi_tenant_migration.sql"

    if not migration_file.exists():
        logger.warning("Multi-tenant migration file not found: %s", migration_file)
        return False

    try:
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        # Use raw asyncpg connection for multi-statement execution
        # (SQLAlchemy's text() doesn't support multiple commands in one call)
        async with crm_engine.connect() as conn:
            raw_conn = await conn.get_raw_connection()
            await raw_conn.driver_connection.execute(migration_sql)
            await conn.commit()

        logger.info("Multi-tenant migration completed successfully")
        return True

    except Exception as e:
        logger.error("Multi-tenant migration failed: %s", e)
        return False