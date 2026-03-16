-- Paperclip Architecture Upgrades — Migration SQL
-- All DDL is idempotent (IF NOT EXISTS / IF NOT EXISTS patterns)

-- ══════════════════════════════════════════════════════════════
-- Track 1: Unified Entity Model
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS crm.entities (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,

    -- Stage progression
    stage TEXT NOT NULL DEFAULT 'lead',
    stage_changed_at TIMESTAMPTZ,

    -- Core identity
    business_name TEXT,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,

    -- Business details
    business_category TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,

    -- Deal fields (populated when stage >= 'deal')
    deal_value NUMERIC(12,2),
    deal_status TEXT,
    lost_reason TEXT,
    expected_close_date DATE,
    closed_at TIMESTAMPTZ,
    pipeline_stage_id INT,

    -- Lead gen fields
    lead_source TEXT,
    lead_score INT,
    lead_tier TEXT,
    google_place_id TEXT,
    google_rating NUMERIC(3,2),
    yelp_url TEXT,

    -- Enrichment
    enrichment_status TEXT,
    website_audit_score INT,
    website_audit_grade TEXT,
    deep_audit_results JSONB,
    social_scan JSONB,

    -- Contact history
    outreach_status TEXT,
    contacted_by TEXT,
    contacted_at TIMESTAMPTZ,
    contact_outcome TEXT,
    contact_notes TEXT,
    contact_history JSONB,

    -- Social links
    facebook_url TEXT,
    instagram_url TEXT,
    linkedin_url TEXT,
    twitter_url TEXT,
    tiktok_url TEXT,
    youtube_url TEXT,

    -- Metadata
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    assigned_user_id INT,
    assigned_agent_id INT,

    -- Source tracking (migration)
    source_lead_id INT,
    source_deal_id INT,

    -- Goal link
    goal_id INT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_org_id ON crm.entities(org_id);
CREATE INDEX IF NOT EXISTS idx_entities_stage ON crm.entities(stage);
CREATE INDEX IF NOT EXISTS idx_entities_org_stage ON crm.entities(org_id, stage);
CREATE INDEX IF NOT EXISTS idx_entities_email ON crm.entities(email);
CREATE INDEX IF NOT EXISTS idx_entities_source_lead ON crm.entities(source_lead_id);
CREATE INDEX IF NOT EXISTS idx_entities_source_deal ON crm.entities(source_deal_id);
CREATE INDEX IF NOT EXISTS idx_entities_goal ON crm.entities(goal_id);

-- ══════════════════════════════════════════════════════════════
-- Track 2: Atomic Task Checkout
-- ══════════════════════════════════════════════════════════════

-- agent_task_assignments (War Room DB — used for agent task dispatch)
ALTER TABLE public.agent_task_assignments ADD COLUMN IF NOT EXISTS locked_by_agent_id TEXT;
ALTER TABLE public.agent_task_assignments ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE public.agent_task_assignments ADD COLUMN IF NOT EXISTS execution_run_id TEXT;
ALTER TABLE public.agent_task_assignments ADD COLUMN IF NOT EXISTS goal_id INT;

-- ══════════════════════════════════════════════════════════════
-- Track 3: Goal Hierarchy
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS crm.goals (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    level TEXT NOT NULL DEFAULT 'task',
    status TEXT NOT NULL DEFAULT 'planned',
    parent_id INT REFERENCES crm.goals(id),
    owner_agent_id INT,
    owner_user_id INT,
    target_metric TEXT,
    target_value NUMERIC,
    current_value NUMERIC DEFAULT 0,
    deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goals_org_id ON crm.goals(org_id);
CREATE INDEX IF NOT EXISTS idx_goals_parent ON crm.goals(parent_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON crm.goals(org_id, status);

-- ══════════════════════════════════════════════════════════════
-- Track 4: Approval Gates
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS crm.approvals (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    type TEXT NOT NULL,
    requested_by_agent_id INT,
    requested_by_user_id INT,
    status TEXT NOT NULL DEFAULT 'pending',
    payload JSONB NOT NULL,
    decision_note TEXT,
    decided_by_user_id INT,
    decided_at TIMESTAMPTZ,
    entity_id INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approvals_org_id ON crm.approvals(org_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON crm.approvals(org_id, status);
CREATE INDEX IF NOT EXISTS idx_approvals_entity ON crm.approvals(entity_id);

-- ══════════════════════════════════════════════════════════════
-- Track 5: Budget Caps
-- ══════════════════════════════════════════════════════════════

-- agents table lives in public schema
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS budget_monthly_cents INT DEFAULT 0;
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS spent_monthly_cents INT DEFAULT 0;
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS budget_reset_day INT DEFAULT 1;

CREATE TABLE IF NOT EXISTS crm.agent_cost_events (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    cost_cents INT NOT NULL,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_events_org ON crm.agent_cost_events(org_id);
CREATE INDEX IF NOT EXISTS idx_cost_events_agent ON crm.agent_cost_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_cost_events_occurred ON crm.agent_cost_events(occurred_at);
