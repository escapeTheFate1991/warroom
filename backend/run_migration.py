#!/usr/bin/env python3
"""
Run database migration for emerging format detection
"""
import asyncio
import os
import asyncpg

async def run_migration():
    # Connection string from environment
    db_url = "postgresql://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
    
    migration_sql = """
    -- Add columns for emerging format detection to competitor_posts table
    
    ALTER TABLE crm.competitor_posts 
    ADD COLUMN IF NOT EXISTS detected_format VARCHAR(50),
    ADD COLUMN IF NOT EXISTS format_confidence REAL,
    ADD COLUMN IF NOT EXISTS classified_at TIMESTAMP WITH TIME ZONE;
    
    -- Create index for efficient format queries
    CREATE INDEX IF NOT EXISTS idx_competitor_posts_detected_format 
    ON crm.competitor_posts(detected_format);
    
    CREATE INDEX IF NOT EXISTS idx_competitor_posts_org_format 
    ON crm.competitor_posts(competitor_id, detected_format, engagement_score);
    
    -- Add columns to video_formats table for stats tracking
    ALTER TABLE crm.video_formats 
    ADD COLUMN IF NOT EXISTS post_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS avg_engagement_score REAL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    
    -- Update existing video_formats with timestamps
    UPDATE crm.video_formats 
    SET updated_at = NOW() 
    WHERE updated_at IS NULL;
    """
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # Run migration
        await conn.execute(migration_sql)
        print("Migration completed successfully!")
        
        # Check if columns were added
        result = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'crm' 
              AND table_name = 'competitor_posts' 
              AND column_name IN ('detected_format', 'format_confidence', 'classified_at')
        """)
        
        print("Added columns:", [dict(row) for row in result])
        
        # Close connection
        await conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_migration())