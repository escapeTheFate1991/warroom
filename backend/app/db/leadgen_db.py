"""Database configuration for LeadGen module."""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

LEADGEN_DB_URL = os.getenv("LEADGEN_DB_URL", "postgresql+asyncpg://leadgen:leadgen-yieldlabs-2026@10.0.0.1:5434/leadgen")

leadgen_engine = create_async_engine(LEADGEN_DB_URL, echo=False, pool_size=5, max_overflow=10)
leadgen_session = async_sessionmaker(leadgen_engine, class_=AsyncSession, expire_on_commit=False)


async def get_leadgen_db():
    """Database dependency for LeadGen."""
    async with leadgen_session() as session:
        yield session