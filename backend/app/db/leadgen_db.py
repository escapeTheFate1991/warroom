"""Database configuration for LeadGen module — uses knowledge DB with leadgen schema."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.config import settings

# Same DB as CRM, different schema
LEADGEN_DB_URL = settings.LEADGEN_DB_URL

leadgen_engine = create_async_engine(LEADGEN_DB_URL, echo=False, pool_size=5, max_overflow=10)
leadgen_session = async_sessionmaker(leadgen_engine, class_=AsyncSession, expire_on_commit=False)


async def get_leadgen_db():
    """Database dependency for LeadGen — sets search_path to leadgen schema."""
    async with leadgen_session() as session:
        await session.execute(text("SET search_path TO leadgen, public"))
        yield session
