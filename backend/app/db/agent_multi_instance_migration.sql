-- Agent Multi-Instance Migration
-- Extends agent system to support multiple agents per user + shared org knowledge pool

BEGIN;

-- 1. Extend agent_instances to support multiple agents per user
ALTER TABLE crm.agent_instances ADD COLUMN IF NOT EXISTS is_anchor BOOLEAN DEFAULT false;
ALTER TABLE crm.agent_instances ADD COLUMN IF NOT EXISTS agent_type TEXT DEFAULT 'custom';
ALTER TABLE crm.agent_instances ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '[]';
ALTER TABLE crm.agent_instances ADD COLUMN IF NOT EXISTS model TEXT DEFAULT 'anthropic/claude-sonnet-4-20250514';
ALTER TABLE crm.agent_instances ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
ALTER TABLE crm.agent_instances ADD COLUMN IF NOT EXISTS avatar_emoji TEXT DEFAULT '🤖';

-- Drop the old unique constraint if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agent_instances_org_id_user_id_key') THEN
        ALTER TABLE crm.agent_instances DROP CONSTRAINT agent_instances_org_id_user_id_key;
    END IF;
END $$;

-- Add a new unique constraint: one ANCHOR per user per org (but allow multiple custom agents)
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_instances_anchor 
    ON crm.agent_instances(org_id, user_id) WHERE is_anchor = true;

-- 2. Create Shared Knowledge Pool table
CREATE TABLE IF NOT EXISTS public.org_knowledge_pool (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    contributed_by_agent_id INTEGER,  -- which agent instance contributed this
    contributed_by_user_id INTEGER,   -- which user's agent
    task_type TEXT NOT NULL,           -- 'research', 'analysis', 'code', 'content', 'design', etc.
    title TEXT NOT NULL,
    summary TEXT NOT NULL,             -- human-readable summary
    result_data JSONB DEFAULT '{}',    -- structured task output
    tags JSONB DEFAULT '[]',           -- searchable tags
    quality_score NUMERIC(3,2) DEFAULT 0,  -- 0.00-1.00 quality rating
    usage_count INTEGER DEFAULT 0,     -- how many times other agents referenced this
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'flagged')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_pool_org ON public.org_knowledge_pool(org_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_pool_type ON public.org_knowledge_pool(org_id, task_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_pool_tags ON public.org_knowledge_pool USING GIN(tags);

COMMIT;