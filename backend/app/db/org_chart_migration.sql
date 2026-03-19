-- Org Chart & Goal Ancestry Migration for War Room
-- Adds organizational structure and goal hierarchy tracking

BEGIN;

-- Set schema to CRM where this functionality belongs
SET search_path TO crm, public;

-- Organizational Members Table
CREATE TABLE IF NOT EXISTS crm.org_members (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    member_type TEXT NOT NULL DEFAULT 'agent', -- 'human' | 'agent'
    agent_id INT,
    user_id INT,
    name TEXT NOT NULL,
    title TEXT,
    department TEXT,
    reports_to_id INT REFERENCES crm.org_members(id) ON DELETE SET NULL,
    role TEXT DEFAULT 'employee', -- 'ceo' | 'director' | 'manager' | 'employee' | 'contractor'
    skills JSONB DEFAULT '[]'::jsonb,
    budget_allocation NUMERIC(12,2) DEFAULT 0,
    status TEXT DEFAULT 'active', -- 'active' | 'onboarding' | 'offboarded'
    hired_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Goals Table with hierarchy support
CREATE TABLE IF NOT EXISTS crm.goals (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    parent_goal_id INT REFERENCES crm.goals(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    goal_type TEXT DEFAULT 'project', -- 'mission' | 'department' | 'project' | 'task'
    owner_member_id INT REFERENCES crm.org_members(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'active', -- 'active' | 'paused' | 'completed' | 'cancelled'
    progress INT DEFAULT 0,
    due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON crm.org_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_reports_to ON crm.org_members(reports_to_id);
CREATE INDEX IF NOT EXISTS idx_org_members_status ON crm.org_members(status);
CREATE INDEX IF NOT EXISTS idx_goals_org_id ON crm.goals(org_id);
CREATE INDEX IF NOT EXISTS idx_goals_parent ON crm.goals(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_goals_owner ON crm.goals(owner_member_id);

-- Add some initial demo data for organization "Stuff N Things" (org_id = 1)
INSERT INTO crm.org_members (org_id, member_type, name, title, role, department, status)
VALUES 
    (1, 'human', 'Eddy Stuff', 'CEO & Founder', 'ceo', 'Executive', 'active'),
    (1, 'agent', 'Friday AI', 'Chief AI Officer', 'director', 'Technology', 'active'),
    (1, 'agent', 'Copy Agent', 'Content Lead', 'manager', 'Marketing', 'active'),
    (1, 'agent', 'Design Agent', 'Creative Director', 'manager', 'Design', 'active'),
    (1, 'agent', 'Dev Agent', 'Engineering Lead', 'manager', 'Technology', 'active')
ON CONFLICT DO NOTHING;

-- Set up reporting structure (CEO at top, agents reporting to appropriate leads)
UPDATE crm.org_members SET reports_to_id = (
    SELECT id FROM crm.org_members WHERE name = 'Eddy Stuff' AND org_id = 1
) WHERE name IN ('Friday AI') AND org_id = 1;

UPDATE crm.org_members SET reports_to_id = (
    SELECT id FROM crm.org_members WHERE name = 'Friday AI' AND org_id = 1
) WHERE name IN ('Copy Agent', 'Design Agent', 'Dev Agent') AND org_id = 1;

-- Add some demo goals
INSERT INTO crm.goals (org_id, title, description, goal_type, status, progress)
VALUES 
    (1, 'Build War Room Platform', 'Complete development of the War Room CRM and AI platform', 'mission', 'active', 75),
    (1, 'Implement Org Chart System', 'Build visual org chart with agent/human hierarchy', 'project', 'active', 0),
    (1, 'Launch Marketing Campaign', 'Execute go-to-market strategy for War Room', 'department', 'active', 25)
ON CONFLICT DO NOTHING;

-- Set goal ownership and hierarchy
UPDATE crm.goals SET owner_member_id = (
    SELECT id FROM crm.org_members WHERE name = 'Eddy Stuff' AND org_id = 1
) WHERE title = 'Build War Room Platform' AND org_id = 1;

UPDATE crm.goals SET 
    parent_goal_id = (SELECT id FROM crm.goals WHERE title = 'Build War Room Platform' AND org_id = 1),
    owner_member_id = (SELECT id FROM crm.org_members WHERE name = 'Dev Agent' AND org_id = 1)
WHERE title = 'Implement Org Chart System' AND org_id = 1;

UPDATE crm.goals SET owner_member_id = (
    SELECT id FROM crm.org_members WHERE name = 'Copy Agent' AND org_id = 1
) WHERE title = 'Launch Marketing Campaign' AND org_id = 1;

COMMIT;