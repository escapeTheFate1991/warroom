#!/usr/bin/env python3
"""Add creator_directive_report column to competitor_posts table."""

import asyncio
from sqlalchemy import text
from app.db.crm_db import crm_session

async def add_cdr_column():
    """Add JSONB column for storing CDRs"""
    print("Adding creator_directive_report column to crm.competitor_posts...")
    
    async with crm_session() as db:
        # Check if column already exists
        result = await db.execute(
            text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'crm' 
                  AND table_name = 'competitor_posts' 
                  AND column_name = 'creator_directive_report'
            """)
        )
        
        if result.fetchone():
            print("✅ Column already exists")
            return
        
        # Add the column
        await db.execute(
            text("""
                ALTER TABLE crm.competitor_posts 
                ADD COLUMN creator_directive_report JSONB
            """)
        )
        
        await db.commit()
        print("✅ Added creator_directive_report column")

if __name__ == "__main__":
    # This will fail due to DB config, but shows the intent
    print("Note: This requires proper DB connection setup")
    print("Column should be added via Alembic migration in production")