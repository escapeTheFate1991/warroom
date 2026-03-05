"""Create content_scripts table for competitive intelligence feature."""
import asyncio
import os
from sqlalchemy import text
from backend.app.db.crm_db import crm_engine

async def create_content_scripts_table():
    """Create the content_scripts table in the CRM schema."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS crm.content_scripts (
            id SERIAL PRIMARY KEY,
            competitor_id INTEGER REFERENCES crm.competitors(id),
            platform VARCHAR NOT NULL,
            title VARCHAR,
            hook TEXT,
            body TEXT,
            cta TEXT,
            topic VARCHAR,
            source_post_url VARCHAR,
            status VARCHAR DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_content_scripts_competitor_id ON crm.content_scripts(competitor_id)",
        "CREATE INDEX IF NOT EXISTS idx_content_scripts_platform ON crm.content_scripts(platform)",
        "CREATE INDEX IF NOT EXISTS idx_content_scripts_status ON crm.content_scripts(status)",
        "CREATE INDEX IF NOT EXISTS idx_content_scripts_created_at ON crm.content_scripts(created_at DESC)"
    ]
    
    try:
        async with crm_engine.begin() as conn:
            for statement in statements:
                await conn.execute(text(statement))
            print("✅ Successfully created content_scripts table and indexes")
    except Exception as e:
        print(f"❌ Failed to create content_scripts table: {e}")

if __name__ == "__main__":
    asyncio.run(create_content_scripts_table())