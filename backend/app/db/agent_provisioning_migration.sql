-- Agent Provisioning Migration (Phase 3)
-- Anchor Agent template system + auto-provisioning for new employees

BEGIN;

-- Agent Templates — role-based templates for provisioning personal AI agents
CREATE TABLE IF NOT EXISTS crm.agent_templates (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    role_id INTEGER,  -- FK to roles, NULL = default template
    soul_template TEXT NOT NULL DEFAULT '',  -- SOUL.md template with {{variables}}
    default_skills JSONB DEFAULT '[]',  -- skill IDs to assign
    default_model TEXT DEFAULT 'anthropic/claude-sonnet-4-20250514',
    max_daily_tokens INTEGER DEFAULT 100000,
    description TEXT DEFAULT '',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_templates_org ON crm.agent_templates(org_id);

-- Agent Instances — personalized agents provisioned for each employee
CREATE TABLE IF NOT EXISTS crm.agent_instances (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,  -- the employee this agent belongs to
    template_id INTEGER REFERENCES crm.agent_templates(id),
    agent_name TEXT NOT NULL,
    soul_md TEXT NOT NULL DEFAULT '',  -- personalized SOUL.md
    memory_namespace TEXT NOT NULL,  -- Qdrant collection name
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'archived')),
    config JSONB DEFAULT '{}',  -- additional config
    last_active TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, user_id)  -- one anchor agent per user per org
);

CREATE INDEX IF NOT EXISTS idx_agent_instances_org ON crm.agent_instances(org_id);
CREATE INDEX IF NOT EXISTS idx_agent_instances_user ON crm.agent_instances(user_id);

COMMIT;