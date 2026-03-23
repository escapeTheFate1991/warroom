#!/usr/bin/env python3
"""
Run the CDN migration job to fix Instagram thumbnail issues.
"""
import asyncio
import sys
import os

# Add the backend to Python path
sys.path.insert(0, '/home/eddy/Development/warroom/backend')

from app.jobs.cdn_migration import migrate_cdn_urls, get_migration_status

async def main():
    print("🚀 Starting CDN Migration Job")
    print("This will download expired Instagram CDN URLs and store them in Garage S3")
    print()
    
    try:
        await migrate_cdn_urls()
        
        # Show final status
        status = get_migration_status()
        print("\n" + "="*50)
        print("📊 MIGRATION COMPLETE")
        print("="*50)
        print(f"Status: {status['status']}")
        print(f"Total posts: {status['total']}")
        print(f"Successfully migrated: {status['success_count']}")
        print(f"Errors: {status['error_count']}")
        
        if status.get('errors'):
            print(f"\n❌ Sample errors ({len(status['errors'])} total):")
            for error in status['errors'][:5]:
                print(f"  • {error}")
        
        if status['status'] == 'complete':
            print("\n✅ All thumbnails should now work!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())