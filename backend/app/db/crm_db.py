"""Database configuration for CRM module."""
import os
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event, text

logger = logging.getLogger(__name__)

# Reuse knowledge DB connection (same as leadgen_db.py pattern)
CRM_DB_URL = os.getenv("CRM_DB_URL", "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge")

crm_engine = create_async_engine(CRM_DB_URL, echo=False, pool_size=5, max_overflow=10)
crm_session = async_sessionmaker(crm_engine, class_=AsyncSession, expire_on_commit=False)


# Set search_path to crm on connections using events
@event.listens_for(crm_engine.sync_engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    """Set search_path to crm for all connections."""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO crm, public")


async def get_crm_db():
    """Database dependency for CRM."""
    async with crm_session() as session:
        # Also set search_path for async connections
        await session.execute(text("SET search_path TO crm, public"))
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
        logger.error(f"Failed to initialize CRM schema: {e}")
        return False