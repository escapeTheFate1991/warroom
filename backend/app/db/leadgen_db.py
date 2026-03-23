"""Database configuration for LeadGen module — uses main database with public schema."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.config import settings

# Use main database
LEADGEN_DB_URL = settings.POSTGRES_URL

leadgen_engine = create_async_engine(LEADGEN_DB_URL, echo=False, pool_size=5, max_overflow=10)
leadgen_session = async_sessionmaker(leadgen_engine, class_=AsyncSession, expire_on_commit=False)


async def get_leadgen_db():
    """Database dependency for LeadGen — sets search_path to public schema."""
    async with leadgen_session() as session:
        await session.execute(text("SET search_path TO public"))
        yield session
