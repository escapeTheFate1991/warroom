-- Migration: Product Tiers and Pricing Enhancement
-- Description: Add AI Automation Services pricing tiers and grandfathering support
-- Date: 2026-03-19

BEGIN;

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

-- Insert AI Automation Services products
INSERT INTO crm.products (
    org_id, sku, name, description, price, billing_interval, features, 
    is_active, tier_level, category, quantity
) VALUES
-- Tier 1: Starter (Foundation)
(1, 'ALEC-STARTER', 'AI Automation Starter (Foundation)', 
 'Perfect for small businesses starting their AI journey', 99.00, 'monthly',
 '["1 Managed OpenClaw Agent", "1,000,000 Standard Tokens", "24/7 Heartbeat (every 30 min)", "WhatsApp or Telegram messaging", "Email support (48h response)", "First 100 Customers — Founding Member Pricing"]'::jsonb,
 true, 1, 'ai-automation', 999),

-- Tier 2: Professional
(1, 'ALEC-PRO', 'AI Automation Professional', 
 'Ideal for growing businesses ready to scale automation', 299.00, 'monthly',
 '["3 Dedicated OpenClaw Agents", "5,000,000 Standard Tokens", "24/7 Heartbeat (every 5 min)", "WhatsApp + Discord + Slack messaging", "Priority Slack support (12h response)", "Advanced CRM orchestration", "Custom business logic"]'::jsonb,
 true, 2, 'ai-automation', 999),

-- Tier 3: Enterprise
(1, 'ALEC-ENTERPRISE', 'AI Automation Enterprise', 
 'Custom solution for enterprise-scale operations', 0.00, 'custom',
 '["Unlimited OpenClaw Agents", "Unlimited tokens / BYO API key", "Real-time / custom heartbeat", "All channels + API access", "Dedicated AI Engineer"]'::jsonb,
 true, 3, 'ai-automation', 999);

-- Add index for faster category queries
CREATE INDEX IF NOT EXISTS idx_products_category ON crm.products(category);
CREATE INDEX IF NOT EXISTS idx_products_tier_level ON crm.products(tier_level);
CREATE INDEX IF NOT EXISTS idx_users_grandfathered ON crm.users(is_grandfathered);

COMMIT;