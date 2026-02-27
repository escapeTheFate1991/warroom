-- CRM Phase 2 Database Schema Migration
-- War Room CRM - Full Krayin CRM Schema

BEGIN;

-- Create CRM schema
CREATE SCHEMA IF NOT EXISTS crm;

-- Users & ACL
CREATE TABLE IF NOT EXISTS crm.roles (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    permission_type TEXT NOT NULL DEFAULT 'custom', -- all, custom
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.groups (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    image TEXT,
    status BOOLEAN DEFAULT true,
    role_id INTEGER REFERENCES crm.roles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.user_groups (
    group_id INTEGER REFERENCES crm.groups(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, user_id)
);

-- Contacts
CREATE TABLE IF NOT EXISTS crm.organizations (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    address JSONB,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL,
    -- Link to leadgen business if originated from lead gen
    leadgen_lead_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.persons (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    emails JSONB DEFAULT '[]',    -- [{value: "x@y.com", label: "work"}]
    contact_numbers JSONB,         -- [{value: "555-1234", label: "mobile"}]
    job_title TEXT,
    organization_id INTEGER REFERENCES crm.organizations(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tags (shared across entities)
CREATE TABLE IF NOT EXISTS crm.tags (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipelines & Stages (Sales Management)
CREATE TABLE IF NOT EXISTS crm.pipelines (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    rotten_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.pipeline_stages (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    probability INTEGER DEFAULT 0,  -- 0-100%
    sort_order INTEGER DEFAULT 0,
    pipeline_id INTEGER REFERENCES crm.pipelines(id) ON DELETE CASCADE,
    UNIQUE(code, pipeline_id),
    UNIQUE(name, pipeline_id)
);

-- Lead Sources & Types
CREATE TABLE IF NOT EXISTS crm.lead_sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.lead_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deals (Krayin calls these "leads" but we already use "leads" for leadgen)
CREATE TABLE IF NOT EXISTS crm.deals (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    deal_value DECIMAL(12, 4),
    status BOOLEAN,  -- NULL=open, true=won, false=lost
    lost_reason TEXT,
    expected_close_date DATE,
    closed_at TIMESTAMPTZ,
    
    -- Foreign keys
    user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL,
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE SET NULL,
    organization_id INTEGER REFERENCES crm.organizations(id) ON DELETE SET NULL,
    source_id INTEGER REFERENCES crm.lead_sources(id) ON DELETE SET NULL,
    type_id INTEGER REFERENCES crm.lead_types(id) ON DELETE SET NULL,
    pipeline_id INTEGER REFERENCES crm.pipelines(id) ON DELETE SET NULL,
    stage_id INTEGER REFERENCES crm.pipeline_stages(id) ON DELETE SET NULL,
    
    -- Link to leadgen if deal originated from a lead
    leadgen_lead_id INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Products/Services
CREATE TABLE IF NOT EXISTS crm.products (
    id SERIAL PRIMARY KEY,
    sku TEXT UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    quantity INTEGER DEFAULT 0,
    price DECIMAL(12, 4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deal-Products junction
CREATE TABLE IF NOT EXISTS crm.deal_products (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES crm.products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    price DECIMAL(12, 4),
    amount DECIMAL(12, 4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Activities (calls, meetings, notes, tasks)
CREATE TABLE IF NOT EXISTS crm.activities (
    id SERIAL PRIMARY KEY,
    title TEXT,
    type TEXT NOT NULL,  -- call, meeting, note, task, email, lunch
    comment TEXT,
    additional JSONB,
    location TEXT,
    schedule_from TIMESTAMPTZ,
    schedule_to TIMESTAMPTZ,
    is_done BOOLEAN DEFAULT false,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Activity participants
CREATE TABLE IF NOT EXISTS crm.activity_participants (
    activity_id INTEGER REFERENCES crm.activities(id) ON DELETE CASCADE,
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, person_id)
);

-- Junction tables for activities
CREATE TABLE IF NOT EXISTS crm.deal_activities (
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    activity_id INTEGER REFERENCES crm.activities(id) ON DELETE CASCADE,
    PRIMARY KEY (deal_id, activity_id)
);

CREATE TABLE IF NOT EXISTS crm.person_activities (
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE CASCADE,
    activity_id INTEGER REFERENCES crm.activities(id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, activity_id)
);

-- Tag junctions
CREATE TABLE IF NOT EXISTS crm.deal_tags (
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES crm.tags(id) ON DELETE CASCADE,
    PRIMARY KEY (deal_id, tag_id)
);

CREATE TABLE IF NOT EXISTS crm.person_tags (
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES crm.tags(id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, tag_id)
);

-- Emails
CREATE TABLE IF NOT EXISTS crm.emails (
    id SERIAL PRIMARY KEY,
    subject TEXT,
    source TEXT NOT NULL,  -- web, imap
    name TEXT,
    reply TEXT,
    is_read BOOLEAN DEFAULT false,
    folders JSONB,
    from_addr JSONB,
    sender JSONB,
    reply_to JSONB,
    cc JSONB,
    bcc JSONB,
    unique_id TEXT UNIQUE,
    message_id TEXT UNIQUE,
    reference_ids JSONB,
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE SET NULL,
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE SET NULL,
    parent_id INTEGER REFERENCES crm.emails(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.email_attachments (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES crm.emails(id) ON DELETE CASCADE,
    name TEXT,
    content_type TEXT,
    size INTEGER,
    filepath TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email Templates
CREATE TABLE IF NOT EXISTS crm.email_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    subject TEXT,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Marketing
CREATE TABLE IF NOT EXISTS crm.marketing_events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.marketing_campaigns (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    subject TEXT,
    status BOOLEAN DEFAULT false,
    type TEXT,  -- newsletter, event
    mail_to TEXT,
    spooling TEXT,
    template_id INTEGER REFERENCES crm.email_templates(id) ON DELETE SET NULL,
    event_id INTEGER REFERENCES crm.marketing_events(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Quotes
CREATE TABLE IF NOT EXISTS crm.quotes (
    id SERIAL PRIMARY KEY,
    subject TEXT NOT NULL,
    description TEXT,
    billing_address JSONB,
    shipping_address JSONB,
    discount_percent DECIMAL(12, 4) DEFAULT 0,
    discount_amount DECIMAL(12, 4),
    tax_amount DECIMAL(12, 4),
    adjustment_amount DECIMAL(12, 4),
    sub_total DECIMAL(12, 4),
    grand_total DECIMAL(12, 4),
    expired_at TIMESTAMPTZ,
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.quote_items (
    id SERIAL PRIMARY KEY,
    quote_id INTEGER REFERENCES crm.quotes(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES crm.products(id) ON DELETE SET NULL,
    sku TEXT,
    name TEXT,
    quantity INTEGER DEFAULT 1,
    price DECIMAL(12, 4) DEFAULT 0,
    discount_percent DECIMAL(12, 4) DEFAULT 0,
    discount_amount DECIMAL(12, 4) DEFAULT 0,
    tax_percent DECIMAL(12, 4) DEFAULT 0,
    tax_amount DECIMAL(12, 4) DEFAULT 0,
    total DECIMAL(12, 4) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.deal_quotes (
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    quote_id INTEGER REFERENCES crm.quotes(id) ON DELETE CASCADE,
    PRIMARY KEY (deal_id, quote_id)
);

-- Custom Attributes (EAV pattern)
CREATE TABLE IF NOT EXISTS crm.attributes (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- text, textarea, boolean, number, date, datetime, select, multiselect, email, phone, lookup
    lookup_type TEXT,
    entity_type TEXT NOT NULL,  -- deal, person, organization, product, quote
    sort_order INTEGER,
    validation TEXT,
    is_required BOOLEAN DEFAULT false,
    is_unique BOOLEAN DEFAULT false,
    quick_add BOOLEAN DEFAULT false,
    is_user_defined BOOLEAN DEFAULT true,
    UNIQUE(code, entity_type),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.attribute_options (
    id SERIAL PRIMARY KEY,
    attribute_id INTEGER REFERENCES crm.attributes(id) ON DELETE CASCADE,
    name TEXT,
    sort_order INTEGER
);

CREATE TABLE IF NOT EXISTS crm.attribute_values (
    id SERIAL PRIMARY KEY,
    entity_type TEXT DEFAULT 'deals',
    entity_id INTEGER NOT NULL,
    attribute_id INTEGER REFERENCES crm.attributes(id) ON DELETE CASCADE,
    text_value TEXT,
    boolean_value BOOLEAN,
    integer_value INTEGER,
    float_value DOUBLE PRECISION,
    datetime_value TIMESTAMPTZ,
    date_value DATE,
    json_value JSONB,
    UNIQUE(entity_type, entity_id, attribute_id)
);

-- Automation Workflows
CREATE TABLE IF NOT EXISTS crm.workflows (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    entity_type TEXT,  -- deal, person, activity, email
    event TEXT,        -- created, updated, stage_changed, etc.
    condition_type TEXT DEFAULT 'and',  -- and, or
    conditions JSONB,
    actions JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.webhooks (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT,
    description TEXT,
    method TEXT,  -- POST, GET, PUT
    end_point TEXT,
    query_params JSONB,
    headers JSONB,
    payload_type TEXT,
    raw_payload_type TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit trail
CREATE TABLE IF NOT EXISTS crm.audit_log (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,  -- created, updated, deleted, stage_changed
    user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL,
    old_values JSONB,
    new_values JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data imports
CREATE TABLE IF NOT EXISTS crm.imports (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    file_path TEXT,
    status TEXT DEFAULT 'pending',
    total_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Saved filters
CREATE TABLE IF NOT EXISTS crm.saved_filters (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    filters JSONB NOT NULL,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_deals_pipeline ON crm.deals(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_deals_stage ON crm.deals(stage_id);
CREATE INDEX IF NOT EXISTS idx_deals_user ON crm.deals(user_id);
CREATE INDEX IF NOT EXISTS idx_deals_status ON crm.deals(status);
CREATE INDEX IF NOT EXISTS idx_deals_person ON crm.deals(person_id);
CREATE INDEX IF NOT EXISTS idx_deals_org ON crm.deals(organization_id);
CREATE INDEX IF NOT EXISTS idx_persons_org ON crm.persons(organization_id);
CREATE INDEX IF NOT EXISTS idx_activities_type ON crm.activities(type);
CREATE INDEX IF NOT EXISTS idx_activities_user ON crm.activities(user_id);
CREATE INDEX IF NOT EXISTS idx_activities_schedule ON crm.activities(schedule_from);
CREATE INDEX IF NOT EXISTS idx_emails_deal ON crm.emails(deal_id);
CREATE INDEX IF NOT EXISTS idx_emails_person ON crm.emails(person_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON crm.audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_attribute_values_entity ON crm.attribute_values(entity_type, entity_id);

-- Default seed data

-- Default pipeline
INSERT INTO crm.pipelines (name, is_default, rotten_days) 
VALUES ('Default Pipeline', true, 30) 
ON CONFLICT DO NOTHING;

-- Default stages for the pipeline (Krayin pattern)
INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) 
SELECT 'new', 'New', 10, 1, p.id FROM crm.pipelines p WHERE p.is_default = true
ON CONFLICT (code, pipeline_id) DO NOTHING;

INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) 
SELECT 'contacted', 'Contacted', 20, 2, p.id FROM crm.pipelines p WHERE p.is_default = true
ON CONFLICT (code, pipeline_id) DO NOTHING;

INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) 
SELECT 'qualified', 'Qualified', 40, 3, p.id FROM crm.pipelines p WHERE p.is_default = true
ON CONFLICT (code, pipeline_id) DO NOTHING;

INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) 
SELECT 'proposal', 'Proposal Made', 60, 4, p.id FROM crm.pipelines p WHERE p.is_default = true
ON CONFLICT (code, pipeline_id) DO NOTHING;

INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) 
SELECT 'negotiation', 'Negotiation', 80, 5, p.id FROM crm.pipelines p WHERE p.is_default = true
ON CONFLICT (code, pipeline_id) DO NOTHING;

INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) 
SELECT 'won', 'Won', 100, 6, p.id FROM crm.pipelines p WHERE p.is_default = true
ON CONFLICT (code, pipeline_id) DO NOTHING;

INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) 
SELECT 'lost', 'Lost', 0, 7, p.id FROM crm.pipelines p WHERE p.is_default = true
ON CONFLICT (code, pipeline_id) DO NOTHING;

-- Default lead sources
INSERT INTO crm.lead_sources (name) VALUES
    ('Lead Gen'), ('Email'), ('Web'), ('Phone'), ('Referral'), ('Social Media'), ('Cold Call')
ON CONFLICT DO NOTHING;

-- Default lead types
INSERT INTO crm.lead_types (name) VALUES
    ('New Business'), ('Existing Business'), ('Upsell')
ON CONFLICT DO NOTHING;

-- Default admin role
INSERT INTO crm.roles (name, description, permission_type) VALUES
    ('Administrator', 'Full access', 'all'),
    ('Sales Agent', 'Sales operations', 'custom'),
    ('Viewer', 'Read-only access', 'custom')
ON CONFLICT DO NOTHING;

-- Default admin user (eddy)
INSERT INTO crm.users (name, email, role_id, status) 
SELECT 'Eddy', 'admin@warroom.local', r.id, true
FROM crm.roles r WHERE r.name = 'Administrator'
ON CONFLICT (email) DO NOTHING;

COMMIT;