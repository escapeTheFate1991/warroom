#!/usr/bin/env python3
"""
Run database migration for AI Automation Services products
"""
import asyncio
import os
import asyncpg

async def run_migration():
    # Connection string from environment
    db_url = "postgresql://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
    
    migration_sql = """
    -- Migration: Product Tiers and Pricing Enhancement
    -- Description: Add AI Automation Services pricing tiers and grandfathering support
    
    -- Add new columns to products table
    ALTER TABLE crm.products 
    ADD COLUMN IF NOT EXISTS billing_interval TEXT DEFAULT 'monthly',
    ADD COLUMN IF NOT EXISTS features JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS stripe_price_id TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS tier_level INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'general';
    
    -- Add grandfathering support to users table
    ALTER TABLE crm.users 
    ADD COLUMN IF NOT EXISTS is_grandfathered BOOLEAN DEFAULT false;
    
    -- Add comments for documentation
    COMMENT ON COLUMN crm.products.billing_interval IS 'Billing frequency: monthly, yearly, one-time';
    COMMENT ON COLUMN crm.products.features IS 'JSON array of feature descriptions';
    COMMENT ON COLUMN crm.products.stripe_price_id IS 'Stripe Price ID for billing integration';
    COMMENT ON COLUMN crm.products.is_active IS 'Product availability status';
    COMMENT ON COLUMN crm.products.tier_level IS 'Pricing tier: 1=Starter, 2=Professional, 3=Enterprise';
    COMMENT ON COLUMN crm.products.category IS 'Product category: ai-automation, crm, etc.';
    COMMENT ON COLUMN crm.users.is_grandfathered IS 'First 100 customers locked at founding member pricing';
    
    -- Add index for faster category queries
    CREATE INDEX IF NOT EXISTS idx_products_category ON crm.products(category);
    CREATE INDEX IF NOT EXISTS idx_products_tier_level ON crm.products(tier_level);
    CREATE INDEX IF NOT EXISTS idx_users_grandfathered ON crm.users(is_grandfathered);
    """
    
    products_sql = """
    -- Insert AI Automation Services products (only if they don't exist)
    INSERT INTO crm.products (
        org_id, sku, name, description, price, billing_interval, features, 
        is_active, tier_level, category, quantity
    ) 
    SELECT 1, 'ALEC-STARTER', 'AI Automation Starter (Foundation)', 
           'Perfect for small businesses starting their AI journey', 99.00, 'monthly',
           '["1 Managed OpenClaw Agent", "1,000,000 Standard Tokens", "24/7 Heartbeat (every 30 min)", "WhatsApp or Telegram messaging", "Email support (48h response)", "First 100 Customers — Founding Member Pricing"]'::jsonb,
           true, 1, 'ai-automation', 999
    WHERE NOT EXISTS (SELECT 1 FROM crm.products WHERE sku = 'ALEC-STARTER');
    
    INSERT INTO crm.products (
        org_id, sku, name, description, price, billing_interval, features, 
        is_active, tier_level, category, quantity
    ) 
    SELECT 1, 'ALEC-PRO', 'AI Automation Professional', 
           'Ideal for growing businesses ready to scale automation', 299.00, 'monthly',
           '["3 Dedicated OpenClaw Agents", "5,000,000 Standard Tokens", "24/7 Heartbeat (every 5 min)", "WhatsApp + Discord + Slack messaging", "Priority Slack support (12h response)", "Advanced CRM orchestration", "Custom business logic"]'::jsonb,
           true, 2, 'ai-automation', 999
    WHERE NOT EXISTS (SELECT 1 FROM crm.products WHERE sku = 'ALEC-PRO');
    
    INSERT INTO crm.products (
        org_id, sku, name, description, price, billing_interval, features, 
        is_active, tier_level, category, quantity
    ) 
    SELECT 1, 'ALEC-ENTERPRISE', 'AI Automation Enterprise', 
           'Custom solution for enterprise-scale operations', 0.00, 'custom',
           '["Unlimited OpenClaw Agents", "Unlimited tokens / BYO API key", "Real-time / custom heartbeat", "All channels + API access", "Dedicated AI Engineer"]'::jsonb,
           true, 3, 'ai-automation', 999
    WHERE NOT EXISTS (SELECT 1 FROM crm.products WHERE sku = 'ALEC-ENTERPRISE');
    """
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # Run schema migration
        print("Running schema migration...")
        await conn.execute(migration_sql)
        print("✅ Schema migration completed!")
        
        # Insert products
        print("Creating AI Automation Services products...")
        await conn.execute(products_sql)
        print("✅ Products created!")
        
        # Check results
        result = await conn.fetch("""
            SELECT name, category, tier_level, price, billing_interval
            FROM crm.products 
            WHERE category = 'ai-automation'
            ORDER BY tier_level
        """)
        
        print(f"✅ Found {len(result)} AI automation products:")
        for row in result:
            print(f"  - {row['name']} (Tier {row['tier_level']}): ${row['price']}/{row['billing_interval']}")
        
        # Check schema changes
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'crm' 
              AND table_name = 'products' 
              AND column_name IN ('billing_interval', 'features', 'stripe_price_id', 'is_active', 'tier_level', 'category')
            ORDER BY column_name
        """)
        
        print(f"✅ Product table columns added: {len(columns)}")
        for col in columns:
            print(f"  - {col['column_name']} ({col['data_type']})")
        
        # Close connection
        await conn.close()
        print("\n🎉 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())