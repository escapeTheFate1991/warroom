# War Room — Paperclip-Inspired Architecture Upgrades

## Track 1: Unified Entity Model (Pipeline Stages, Not Separate Tables)

### Current State
- `leadgen.leads` — 69 rows, 80+ columns (enrichment, audit, contact history)
- `crm.persons` — 10 rows (name, emails, phones, job_title)
- `crm.deals` — 13 rows (title, value, status, stage_id)
- `public.prospects_meta` — exists but empty
- `crm.pipeline_stages` — 7 stages: New → Contacted → Qualified → Proposal Made → Negotiation → Won → Lost

### Problem
Lead, Contact, Person, Prospect, Deal are fragmented. Converting a lead creates a deal + person but the lead still exists separately. Editing one doesn't update the other.

### Solution: `crm.entities` table (unified)

```sql
CREATE TABLE crm.entities (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    
    -- Stage progression (replaces separate tables)
    stage TEXT NOT NULL DEFAULT 'lead',  -- lead | prospect | qualified | deal | client | churned
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
    deal_status TEXT,  -- open | won | lost
    lost_reason TEXT,
    expected_close_date DATE,
    closed_at TIMESTAMPTZ,
    pipeline_stage_id INT REFERENCES crm.pipeline_stages(id),
    
    -- Lead gen fields
    lead_source TEXT,
    lead_score INT,
    lead_tier TEXT,
    google_place_id TEXT,
    google_rating NUMERIC(3,2),
    yelp_url TEXT,
    
    -- Enrichment (from leadgen)
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
    
    -- Source tracking
    source_lead_id INT,  -- original leadgen.leads.id for migration
    source_deal_id INT,  -- original crm.deals.id for migration
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration: INSERT INTO crm.entities SELECT ... FROM leadgen.leads
-- Migration: UPDATE crm.entities SET stage = 'deal' WHERE source_deal_id IS NOT NULL
```

### Stage Transitions
- `lead` → `prospect`: First outreach or reply detected
- `prospect` → `qualified`: Meets criteria (has budget, needs service)
- `qualified` → `deal`: Proposal sent or meeting scheduled
- `deal` → `client`: Won (closed)
- Any → `churned`: Lost or inactive

### API Changes
- `GET /api/entities` — replaces leads list, contacts list, prospects
- `PATCH /api/entities/:id/stage` — advance stage (auto-timestamps)
- `GET /api/entities?stage=lead` — filter by stage
- Keep old endpoints as thin wrappers for backward compat


## Track 2: Atomic Task Checkout

### Add to `kanban_tasks` or `agent_task_queue`:
```sql
ALTER TABLE kanban_tasks ADD COLUMN locked_by_agent_id TEXT;
ALTER TABLE kanban_tasks ADD COLUMN locked_at TIMESTAMPTZ;
ALTER TABLE kanban_tasks ADD COLUMN execution_run_id TEXT;
```

### Checkout flow:
```sql
UPDATE kanban_tasks 
SET locked_by_agent_id = :agent_id, 
    locked_at = NOW(),
    status = 'in_progress'
WHERE id = :task_id 
  AND locked_by_agent_id IS NULL
RETURNING *;
```

If returns 0 rows → task already checked out. No double work.

### Release on completion:
```sql
UPDATE kanban_tasks 
SET locked_by_agent_id = NULL, 
    locked_at = NULL,
    status = 'done'
WHERE id = :task_id;
```


## Track 3: Goal Hierarchy

```sql
CREATE TABLE crm.goals (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    level TEXT NOT NULL DEFAULT 'task',  -- company | campaign | project | task
    status TEXT NOT NULL DEFAULT 'planned',  -- planned | active | completed | archived
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

-- Link entities to goals
ALTER TABLE crm.entities ADD COLUMN goal_id INT REFERENCES crm.goals(id);
-- Link tasks to goals  
ALTER TABLE kanban_tasks ADD COLUMN goal_id INT REFERENCES crm.goals(id);
```


## Track 4: Approval Gates

```sql
CREATE TABLE crm.approvals (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    type TEXT NOT NULL,  -- cold_email | cold_call | social_dm | contract | budget
    requested_by_agent_id INT,
    requested_by_user_id INT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    payload JSONB NOT NULL,  -- the actual email/message/action to approve
    decision_note TEXT,
    decided_by_user_id INT,
    decided_at TIMESTAMPTZ,
    entity_id INT REFERENCES crm.entities(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```


## Track 5: Budget Caps Per Agent

```sql
ALTER TABLE agents ADD COLUMN budget_monthly_cents INT DEFAULT 0;
ALTER TABLE agents ADD COLUMN spent_monthly_cents INT DEFAULT 0;
ALTER TABLE agents ADD COLUMN budget_reset_day INT DEFAULT 1;

-- Cost event tracking
CREATE TABLE crm.agent_cost_events (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    agent_id INT NOT NULL,
    task_id INT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    cost_cents INT NOT NULL,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);
```
