#!/usr/bin/env python3
"""Test script to run the social accounts migration manually."""

import asyncio
import os
import sys

# Add the backend directory to the Python path
backend_dir = "/home/eddy/Development/warroom/backend"
sys.path.insert(0, backend_dir)

# Set minimal environment variables
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-migration")
os.environ.setdefault("POSTGRES_URL", "postgresql://user:pass@localhost:5432/warroom")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql://user:pass@localhost:5432/warroom")

async def run_migration():
    """Run the social accounts migration manually."""
    try:
        # Import after setting environment variables
        from app.config import settings
        from sqlalchemy.ext.asyncio import create_async_engine
        import asyncpg
        
        print("Connecting to database...")
        
        # Connect directly with asyncpg to run the migration
        db_url = settings.CRM_DB_URL.replace('postgresql+asyncpg://', 'postgresql://')
        conn = await asyncpg.connect(db_url)
        
        try:
            # Check if table already exists
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'social_accounts'
                )
            """)
            
            if exists:
                print("✅ social_accounts table already exists")
                return True
            
            print("Creating social_accounts table...")
            
            # Run the migration SQL
            migration_sql = """
                CREATE TABLE social_accounts (
                    id SERIAL PRIMARY KEY,
                    org_id UUID NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    account_type VARCHAR(20) NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    password_encrypted TEXT,
                    totp_secret_encrypted TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    notes TEXT,
                    CONSTRAINT uq_social_accounts_org_platform_username 
                        UNIQUE (org_id, platform, username)
                );
                
                CREATE INDEX ix_social_accounts_org_id ON social_accounts (org_id);
                CREATE INDEX ix_social_accounts_platform ON social_accounts (platform);
                CREATE INDEX ix_social_accounts_status ON social_accounts (status);
            """
            
            await conn.execute(migration_sql)
            print("✅ Successfully created social_accounts table and indexes")
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

async def test_encryption():
    """Test the encryption service."""
    try:
        from app.services.encryption import encrypt_value, decrypt_value
        
        test_password = "test_password_123"
        encrypted = encrypt_value(test_password)
        decrypted = decrypt_value(encrypted)
        
        print(f"🔒 Encryption test:")
        print(f"   Original: {test_password}")
        print(f"   Encrypted: {encrypted[:50]}...")
        print(f"   Decrypted: {decrypted}")
        print(f"   ✅ Encryption works: {test_password == decrypted}")
        
        return test_password == decrypted
        
    except Exception as e:
        print(f"❌ Encryption test failed: {e}")
        return False

async def test_social_accounts_model():
    """Test creating a social account."""
    try:
        from app.services.encryption import encrypt_value
        from app.config import settings
        from sqlalchemy.ext.asyncio import create_async_engine
        import asyncpg
        import uuid
        
        print("🧪 Testing social account creation...")
        
        db_url = settings.CRM_DB_URL.replace('postgresql+asyncpg://', 'postgresql://')
        conn = await asyncpg.connect(db_url)
        
        try:
            # Create a test social account
            test_org_id = str(uuid.uuid4())
            encrypted_password = encrypt_value("test_password")
            encrypted_totp = encrypt_value("JBSWY3DPEHPK3PXP")
            
            await conn.execute("""
                INSERT INTO social_accounts (
                    org_id, platform, account_type, username, 
                    password_encrypted, totp_secret_encrypted, notes
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, test_org_id, "instagram", "scraping", "test_user", 
                encrypted_password, encrypted_totp, "Test account from migration script")
            
            print("✅ Successfully created test social account")
            
            # Verify we can read it back
            row = await conn.fetchrow("""
                SELECT username, platform, account_type FROM social_accounts
                WHERE org_id = $1
            """, test_org_id)
            
            print(f"   Retrieved: @{row['username']} on {row['platform']} ({row['account_type']})")
            
            # Clean up test data
            await conn.execute("DELETE FROM social_accounts WHERE org_id = $1", test_org_id)
            print("✅ Cleaned up test data")
            
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"❌ Social accounts test failed: {e}")
        return False

async def main():
    print("=== Social Accounts Migration Test ===")
    
    # Test 1: Run migration
    print("\n1. Running database migration...")
    migration_success = await run_migration()
    
    # Test 2: Test encryption
    print("\n2. Testing encryption service...")
    encryption_success = await test_encryption()
    
    # Test 3: Test social accounts creation
    print("\n3. Testing social accounts model...")
    model_success = await test_social_accounts_model()
    
    # Summary
    print("\n=== Summary ===")
    print(f"Migration:  {'✅' if migration_success else '❌'}")
    print(f"Encryption: {'✅' if encryption_success else '❌'}")
    print(f"Model test: {'✅' if model_success else '❌'}")
    
    if all([migration_success, encryption_success, model_success]):
        print("\n🎉 All tests passed! Social accounts system is ready.")
        return 0
    else:
        print("\n💥 Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)