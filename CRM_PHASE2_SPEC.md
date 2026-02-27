# CRM Phase 2 — Full Krayin CRM Conversion for War Room

## Architecture
- **Backend:** FastAPI + SQLAlchemy async (existing stack)
- **Frontend:** Next.js 14 + TypeScript + Tailwind (existing stack)
- **Database:** PostgreSQL on Brain 2 (`knowledge` DB), new `crm` schema
- **Existing leadgen:** Stays in its own tables, CRM deals link TO leadgen leads
- **Reference:** Krayin source at `/tmp/krayin-ref/` (READ ONLY, PHP → TypeScript conversion)

## Database Schema (crm schema in knowledge DB)

All tables below go in `CREATE SCHEMA IF NOT EXISTS crm;`

### Core CRM Tables

```sql
-- Users & ACL
CREATE TABLE crm.users (
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

CREATE TABLE crm.roles (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    permission_type TEXT NOT NULL DEFAULT 'custom', -- all, custom
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crm.groups (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crm.user_groups (
    group_id INTEGER REFERENCES crm.groups(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, user_id)
);

-- Contacts
CREATE TABLE crm.organizations (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    address JSONB,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL,
    -- Link to leadgen business if originated from lead gen
    leadgen_lead_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crm.persons (
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
CREATE TABLE crm.tags (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipelines & Stages (Sales Management)
CREATE TABLE crm.pipelines (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    rotten_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crm.pipeline_stages (
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
CREATE TABLE crm.lead_sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crm.lead_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deals (Krayin calls these "leads" but we already use "leads" for leadgen)
CREATE TABLE crm.deals (
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

-- Deal-Products junction
CREATE TABLE crm.deal_products (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES crm.products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    price DECIMAL(12, 4),
    amount DECIMAL(12, 4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Products/Services
CREATE TABLE crm.products (
    id SERIAL PRIMARY KEY,
    sku TEXT UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    quantity INTEGER DEFAULT 0,
    price DECIMAL(12, 4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Activities (calls, meetings, notes, tasks)
CREATE TABLE crm.activities (
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
CREATE TABLE crm.activity_participants (
    activity_id INTEGER REFERENCES crm.activities(id) ON DELETE CASCADE,
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, person_id)
);

-- Junction tables for activities
CREATE TABLE crm.deal_activities (
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    activity_id INTEGER REFERENCES crm.activities(id) ON DELETE CASCADE,
    PRIMARY KEY (deal_id, activity_id)
);

CREATE TABLE crm.person_activities (
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE CASCADE,
    activity_id INTEGER REFERENCES crm.activities(id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, activity_id)
);

-- Tag junctions
CREATE TABLE crm.deal_tags (
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES crm.tags(id) ON DELETE CASCADE,
    PRIMARY KEY (deal_id, tag_id)
);

CREATE TABLE crm.person_tags (
    person_id INTEGER REFERENCES crm.persons(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES crm.tags(id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, tag_id)
);

-- Emails
CREATE TABLE crm.emails (
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

CREATE TABLE crm.email_attachments (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES crm.emails(id) ON DELETE CASCADE,
    name TEXT,
    content_type TEXT,
    size INTEGER,
    filepath TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email Templates
CREATE TABLE crm.email_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    subject TEXT,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Marketing
CREATE TABLE crm.marketing_events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crm.marketing_campaigns (
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
CREATE TABLE crm.quotes (
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

CREATE TABLE crm.quote_items (
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

CREATE TABLE crm.deal_quotes (
    deal_id INTEGER REFERENCES crm.deals(id) ON DELETE CASCADE,
    quote_id INTEGER REFERENCES crm.quotes(id) ON DELETE CASCADE,
    PRIMARY KEY (deal_id, quote_id)
);

-- Custom Attributes (EAV pattern)
CREATE TABLE crm.attributes (
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

CREATE TABLE crm.attribute_options (
    id SERIAL PRIMARY KEY,
    attribute_id INTEGER REFERENCES crm.attributes(id) ON DELETE CASCADE,
    name TEXT,
    sort_order INTEGER
);

CREATE TABLE crm.attribute_values (
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
CREATE TABLE crm.workflows (
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

CREATE TABLE crm.webhooks (
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
CREATE TABLE crm.audit_log (
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
CREATE TABLE crm.imports (
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
CREATE TABLE crm.saved_filters (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    filters JSONB NOT NULL,
    user_id INTEGER REFERENCES crm.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_deals_pipeline ON crm.deals(pipeline_id);
CREATE INDEX idx_deals_stage ON crm.deals(stage_id);
CREATE INDEX idx_deals_user ON crm.deals(user_id);
CREATE INDEX idx_deals_status ON crm.deals(status);
CREATE INDEX idx_deals_person ON crm.deals(person_id);
CREATE INDEX idx_deals_org ON crm.deals(organization_id);
CREATE INDEX idx_persons_org ON crm.persons(organization_id);
CREATE INDEX idx_activities_type ON crm.activities(type);
CREATE INDEX idx_activities_user ON crm.activities(user_id);
CREATE INDEX idx_activities_schedule ON crm.activities(schedule_from);
CREATE INDEX idx_emails_deal ON crm.emails(deal_id);
CREATE INDEX idx_emails_person ON crm.emails(person_id);
CREATE INDEX idx_audit_entity ON crm.audit_log(entity_type, entity_id);
CREATE INDEX idx_attribute_values_entity ON crm.attribute_values(entity_type, entity_id);
```

### Default Seed Data
```sql
-- Default pipeline
INSERT INTO crm.pipelines (name, is_default, rotten_days) VALUES ('Default Pipeline', true, 30);

-- Default stages for the pipeline (Krayin pattern)
INSERT INTO crm.pipeline_stages (code, name, probability, sort_order, pipeline_id) VALUES
    ('new', 'New', 10, 1, 1),
    ('contacted', 'Contacted', 20, 2, 1),
    ('qualified', 'Qualified', 40, 3, 1),
    ('proposal', 'Proposal Made', 60, 4, 1),
    ('negotiation', 'Negotiation', 80, 5, 1),
    ('won', 'Won', 100, 6, 1),
    ('lost', 'Lost', 0, 7, 1);

-- Default lead sources
INSERT INTO crm.lead_sources (name) VALUES
    ('Lead Gen'), ('Email'), ('Web'), ('Phone'), ('Referral'), ('Social Media'), ('Cold Call');

-- Default lead types
INSERT INTO crm.lead_types (name) VALUES
    ('New Business'), ('Existing Business'), ('Upsell');

-- Default admin role
INSERT INTO crm.roles (name, description, permission_type) VALUES
    ('Administrator', 'Full access', 'all'),
    ('Sales Agent', 'Sales operations', 'custom'),
    ('Viewer', 'Read-only access', 'custom');

-- Default admin user (eddy)
INSERT INTO crm.users (name, email, role_id, status) VALUES
    ('Eddy', 'admin@warroom.local', 1, true);
```

## Build Plan — 6 Sub-Agent Tasks

### Task A: Schema + Models + Migration (Backend Foundation)
- Create `backend/app/db/crm_schema.sql` with full schema above
- Create `backend/app/db/crm_db.py` — connection + session factory (reuse knowledge DB, set search_path to crm)
- Create `backend/app/models/crm/` directory with all SQLAlchemy models:
  - `user.py` (User, Role, Group)
  - `contact.py` (Person, Organization)
  - `deal.py` (Deal, Pipeline, PipelineStage, LeadSource, LeadType)
  - `activity.py` (Activity, ActivityParticipant)
  - `product.py` (Product, DealProduct)
  - `email.py` (Email, EmailAttachment, EmailTemplate)
  - `marketing.py` (Campaign, MarketingEvent)
  - `quote.py` (Quote, QuoteItem)
  - `attribute.py` (Attribute, AttributeOption, AttributeValue)
  - `automation.py` (Workflow, Webhook)
  - `audit.py` (AuditLog, Import, SavedFilter)
- Run migration on Brain 2 knowledge DB
- All models use `__table_args__ = {"schema": "crm"}`

### Task B: CRM API Endpoints (Backend)
Create `backend/app/api/crm/` with:
- `deals.py` — CRUD deals, move between stages, list by pipeline/stage, forecasting
- `contacts.py` — CRUD persons + organizations, search, merge/dedup
- `activities.py` — CRUD activities, list by deal/person/date, mark done
- `products.py` — CRUD products
- `pipelines.py` — CRUD pipelines + stages, reorder
- `emails.py` — list, compose (Gmail SMTP), track threads
- `marketing.py` — campaigns, events, send
- `quotes.py` — CRUD quotes + items, generate PDF
- `attributes.py` — CRUD custom attributes, get/set values
- `automation.py` — CRUD workflows + webhooks
- `data.py` — import/export CSV, deduplication
- `audit.py` — audit trail log viewer
- `acl.py` — roles, permissions, users
- `schemas.py` — all Pydantic request/response models
- Register all routers in `backend/app/main.py` under `/api/crm/`

### Task C: Pipeline/Deals UI (Frontend — Core Sales)
Create `frontend/src/components/crm/`:
- `DealsKanban.tsx` — kanban board of deals by pipeline stage (drag-and-drop between columns)
- `DealDrawer.tsx` — slide-out with deal details, activities, products, emails, quotes
- `DealForm.tsx` — create/edit deal modal
- `PipelineSelector.tsx` — switch between pipelines
- `ForecastPanel.tsx` — deal value aggregation by stage, win probability
Add "Deals" tab to main nav in `page.tsx`

### Task D: Contacts + Activities UI (Frontend)
- `ContactsManager.tsx` — list/search persons & organizations with filters
- `PersonDrawer.tsx` — person detail with activities, deals, emails
- `OrgDrawer.tsx` — organization detail with persons, deals
- `ActivitiesPanel.tsx` — calendar/list view of all activities (calls, meetings, tasks)
- `ActivityForm.tsx` — create/edit activity, link to deal/person
Add "CRM" dropdown in nav with: Deals, Contacts, Activities

### Task E: Email + Marketing UI (Frontend)
- `EmailInbox.tsx` — inbox view (folders, read/unread, thread view)
- `EmailComposer.tsx` — compose email with template selection
- `EmailTemplates.tsx` — manage email templates
- `CampaignsPanel.tsx` — list/create/manage marketing campaigns
- Wire to settings: Email Integration tab gets Gmail IMAP/SMTP config
- Wire to settings: Social Media tab gets account connection config

### Task F: Settings Completion + Data Management (Frontend + Backend)
- Complete settings tabs from Phase 1 scaffolding:
  - **Email Integration** — Gmail SMTP/IMAP config form, test connection
  - **Social Media** — placeholder with connect buttons
  - **Lead Scoring** — editable weights table, save/apply
  - **Automation** — workflow builder (entity + event + conditions + actions)
  - **Access Control** — roles CRUD, permissions matrix, user management
- `DataManager.tsx` — import CSV, export, deduplication tool
- `AuditTrail.tsx` — filterable audit log viewer
- `CustomFields.tsx` — manage custom attributes per entity type

## LeadGen ↔ CRM Bridge
When a leadgen lead is marked "won", auto-create:
1. A `crm.organization` from the business data
2. A `crm.person` from contact fields (who_answered, owner_name, etc.)
3. A `crm.deal` in the default pipeline at "New" stage, linked to org + person
4. Set `leadgen_lead_id` on the deal and org for traceability

This bridge logic goes in `backend/app/api/leadgen.py` when `contact_outcome == "won"`.

## Technical Rules
- All new files under `backend/app/models/crm/`, `backend/app/api/crm/`, `frontend/src/components/crm/`
- Use existing warroom dark theme colors
- Do NOT modify existing leadgen code (except the bridge)
- Do NOT touch chat.py or ChatPanel.tsx
- Use lucide-react for icons
- TypeScript strict mode
- No PHP. No PHP frameworks.

## Nav Structure (Updated)
Sidebar tabs:
1. Chat (existing)
2. Tasks/Kanban (existing)
3. Team (existing)
4. Library (existing dropdown)
5. **CRM** (new dropdown):
   - Deals (kanban)
   - Contacts
   - Activities
   - Products
6. Lead Gen (existing)
7. Contacts History (Phase 1)
8. **Marketing** (new):
   - Campaigns
   - Email Templates
9. Settings (existing, with new tabs)
