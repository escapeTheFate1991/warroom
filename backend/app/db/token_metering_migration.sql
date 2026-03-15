-- Token metering migration
-- 3-tier token allocation and usage tracking system

-- Token allocations per org
CREATE TABLE IF NOT EXISTS public.token_allocations (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('org', 'dept', 'user')),
    target_id INTEGER NOT NULL,  -- org_id, dept_id, or user_id depending on tier
    monthly_limit BIGINT NOT NULL DEFAULT 0,  -- 0 = unlimited
    used_this_month BIGINT NOT NULL DEFAULT 0,
    reset_day INTEGER NOT NULL DEFAULT 1,  -- day of month to reset
    last_reset TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, tier, target_id)
);

-- Token usage log (append-only audit trail)
CREATE TABLE IF NOT EXISTS public.token_usage_log (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    agent_id TEXT,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0,
    endpoint TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_token_usage_org ON public.token_usage_log(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_user ON public.token_usage_log(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_token_allocations_org_tier ON public.token_allocations(org_id, tier);
CREATE INDEX IF NOT EXISTS idx_token_allocations_target ON public.token_allocations(tier, target_id);

-- Auto-update updated_at on token_allocations
CREATE OR REPLACE FUNCTION update_token_allocation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_token_allocation_timestamp_trigger ON public.token_allocations;
CREATE TRIGGER update_token_allocation_timestamp_trigger
    BEFORE UPDATE ON public.token_allocations
    FOR EACH ROW
    EXECUTE FUNCTION update_token_allocation_timestamp();