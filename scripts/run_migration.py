#!/usr/bin/env python3
"""Run database migration to add competitor_posts table."""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "backend"))

from sqlalchemy import text
from backend.app.db.crm_db import crm_engine

async def run_migration():
    """Execute the migration SQL."""
    # Read the migration SQL
    migration_file = Path(__file__).parent / "backend" / "app" / "db" / "add_competitor_posts_table.sql"
    
    if not migration_file.exists():
        print(f"Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    try:
        # Execute the migration
        async with crm_engine.begin() as conn:
            await conn.execute(text("SET search_path TO crm, public"))
            
            # Split SQL into individual statements
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            for stmt in statements:
                if stmt:  # Skip empty statements
                    await conn.execute(text(stmt))
                    
            print("✅ Migration completed successfully - competitor_posts table created")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(run_migration())