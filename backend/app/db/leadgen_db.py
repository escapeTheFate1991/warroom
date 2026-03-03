"""Database configuration for LeadGen module — uses knowledge DB with leadgen schema."""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

# Same DB as CRM, different schema
LEADGEN_DB_URL = os.getenv(
    "LEADGEN_DB_URL",
    "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
)

leadgen_engine = create_async_engine(LEADGEN_DB_URL, echo=False, pool_size=5, max_overflow=10)
leadgen_session = async_sessionmaker(leadgen_engine, class_=AsyncSession, expire_on_commit=False)


async def get_leadgen_db():
    """Database dependency for LeadGen — sets search_path to leadgen schema."""
    async with leadgen_session() as session:
        await session.execute(text("SET search_path TO leadgen, public"))
        yield session
