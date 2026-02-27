#!/usr/bin/env python3
"""Run CRM schema migration using asyncpg."""

import asyncio
import asyncpg
from pathlib import Path

async def run_migration():
    """Execute CRM schema migration on Brain 2."""
    # Connection details
    host = "10.0.0.11"
    port = 5433
    user = "friday"
    password = "friday-brain2-2026"
    database = "knowledge"
    
    # Read schema file
    schema_file = Path("backend/app/db/crm_schema.sql")
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    try:
        # Connect and execute
        print(f"🔗 Connecting to {host}:{port}/{database}...")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        print("📝 Executing CRM schema migration...")
        await conn.execute(schema_sql)
        
        await conn.close()
        print("✅ CRM schema migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)