-- Multi-Tenant Migration — Phase 0
-- Adds org_id to all CRM, LeadGen, and Public tables for tenant isolation.
-- Run AFTER creating at least one org in crm.organizations_tenant.
--
-- NOTE: org_id is NULLABLE for now — existing data has no org assigned.
-- After backfilling existing rows with the correct org_id, run:
--   ALTER TABLE crm.<table> ALTER COLUMN org_id SET NOT NULL;
-- for each table to enforce the constraint going forward.

BEGIN;

-- ═══════════════════════════════════════════════════════════════════
-- 1. RBAC Hierarchy Support
-- ═══════════════════════════════════════════════════════════════════

-- hierarchy_level on roles: Director=30, Manager=20, Employee=10
ALTER TABLE crm.roles ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.roles ADD COLUMN IF NOT EXISTS hierarchy_level INTEGER DEFAULT 10;

-- reports_to on users for org hierarchy (parent-child)
ALTER TABLE crm.users ADD COLUMN IF NOT EXISTS reports_to INTEGER REFERENCES crm.users(id);

-- ═══════════════════════════════════════════════════════════════════
-- 2. CRM Schema — Core Entities
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.deals ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.persons ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.organizations ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.tags ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.activities ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- ═══════════════════════════════════════════════════════════════════
-- 3. CRM Schema — Email & Communications
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.emails ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.email_attachments ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.email_templates ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.call_logs ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.sms_messages ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- ═══════════════════════════════════════════════════════════════════
-- 4. CRM Schema — Pipeline & Config
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.pipelines ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.pipeline_stages ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.lead_sources ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.lead_types ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.groups ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.products ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- ═══════════════════════════════════════════════════════════════════
-- 5. CRM Schema — Deals sub-tables
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.quotes ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.quote_items ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.deal_products ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- Junction tables (deal_quotes, deal_tags, person_tags, deal_activities,
-- person_activities, activity_participants) inherit isolation through their
-- FK parents. No org_id needed on pure junction tables.

-- ═══════════════════════════════════════════════════════════════════
-- 6. CRM Schema — Social & Intelligence
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.social_accounts ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.social_analytics ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.competitors ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.competitor_posts ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.content_scripts ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- ═══════════════════════════════════════════════════════════════════
-- 7. CRM Schema — Marketing
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.marketing_events ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.marketing_campaigns ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- ═══════════════════════════════════════════════════════════════════
-- 8. CRM Schema — Automation
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.workflows ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.workflow_templates ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.workflow_executions ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.webhooks ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- ═══════════════════════════════════════════════════════════════════
-- 9. CRM Schema — EAV & Meta
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE crm.attributes ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.attribute_options ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.attribute_values ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.audit_log ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.imports ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);
ALTER TABLE crm.saved_filters ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES crm.organizations_tenant(id);

-- ═══════════════════════════════════════════════════════════════════
-- 10. LeadGen Schema
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE leadgen.search_jobs ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE leadgen.leads ADD COLUMN IF NOT EXISTS org_id INTEGER;

-- ═══════════════════════════════════════════════════════════════════
-- 11. Public Schema — Settings (NULL = global platform setting)
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.settings ADD COLUMN IF NOT EXISTS org_id INTEGER;

-- ═══════════════════════════════════════════════════════════════════
-- 12. Indexes — org_id on every table for fast tenant-scoped queries
-- ═══════════════════════════════════════════════════════════════════

-- CRM core
CREATE INDEX IF NOT EXISTS idx_deals_org_id ON crm.deals(org_id);
CREATE INDEX IF NOT EXISTS idx_persons_org_id ON crm.persons(org_id);
CREATE INDEX IF NOT EXISTS idx_organizations_org_id ON crm.organizations(org_id);
CREATE INDEX IF NOT EXISTS idx_tags_org_id ON crm.tags(org_id);
CREATE INDEX IF NOT EXISTS idx_activities_org_id ON crm.activities(org_id);

-- Email & comms
CREATE INDEX IF NOT EXISTS idx_emails_org_id ON crm.emails(org_id);
CREATE INDEX IF NOT EXISTS idx_email_templates_org_id ON crm.email_templates(org_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_org_id ON crm.call_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_sms_messages_org_id ON crm.sms_messages(org_id);

-- Pipeline & config
CREATE INDEX IF NOT EXISTS idx_pipelines_org_id ON crm.pipelines(org_id);
CREATE INDEX IF NOT EXISTS idx_roles_org_id ON crm.roles(org_id);
CREATE INDEX IF NOT EXISTS idx_groups_org_id ON crm.groups(org_id);
CREATE INDEX IF NOT EXISTS idx_products_org_id ON crm.products(org_id);

-- Social & intel
CREATE INDEX IF NOT EXISTS idx_social_accounts_org_id ON crm.social_accounts(org_id);
CREATE INDEX IF NOT EXISTS idx_competitors_org_id ON crm.competitors(org_id);

-- Marketing
CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_org_id ON crm.marketing_campaigns(org_id);

-- Automation
CREATE INDEX IF NOT EXISTS idx_workflows_org_id ON crm.workflows(org_id);
CREATE INDEX IF NOT EXISTS idx_workflow_templates_org_id ON crm.workflow_templates(org_id);

-- EAV & meta
CREATE INDEX IF NOT EXISTS idx_attributes_org_id ON crm.attributes(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_org_id ON crm.audit_log(org_id);

-- Quotes
CREATE INDEX IF NOT EXISTS idx_quotes_org_id ON crm.quotes(org_id);

-- LeadGen
CREATE INDEX IF NOT EXISTS idx_leadgen_search_jobs_org_id ON leadgen.search_jobs(org_id);
CREATE INDEX IF NOT EXISTS idx_leadgen_leads_org_id ON leadgen.leads(org_id);

-- Public
CREATE INDEX IF NOT EXISTS idx_settings_org_id ON public.settings(org_id);

-- Hierarchy
CREATE INDEX IF NOT EXISTS idx_users_reports_to ON crm.users(reports_to);
CREATE INDEX IF NOT EXISTS idx_roles_hierarchy ON crm.roles(hierarchy_level);

COMMIT;
