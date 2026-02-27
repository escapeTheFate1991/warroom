#!/usr/bin/env python3
"""Run CRM schema migration using the CRM database module."""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.db.crm_db import init_crm_schema

async def main():
    """Run the CRM schema migration."""
    print("🚀 Starting CRM schema migration...")
    
    success = await init_crm_schema()
    
    if success:
        print("✅ CRM schema migration completed successfully!")
        return 0
    else:
        print("❌ CRM schema migration failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())