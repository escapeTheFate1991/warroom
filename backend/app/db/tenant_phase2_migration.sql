-- Phase 2: Settings, OAuth, Notifications, and remaining public tables
-- Idempotent — safe to run multiple times

-- 1. Settings
ALTER TABLE public.settings ADD COLUMN IF NOT EXISTS org_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_settings_org_id ON public.settings(org_id);
UPDATE public.settings SET org_id = 1 WHERE org_id IS NULL;

-- 2. OAuth tokens (has no id column — service is the key)
ALTER TABLE public.oauth_tokens ADD COLUMN IF NOT EXISTS org_id INTEGER DEFAULT 1;
ALTER TABLE public.oauth_tokens ADD COLUMN IF NOT EXISTS user_id INTEGER;

-- 3. Notifications
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS org_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_notifications_org_id ON public.notifications(org_id);
UPDATE public.notifications SET org_id = 1 WHERE org_id IS NULL;

-- 4. Invoices + Invoice templates
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.invoice_templates ADD COLUMN IF NOT EXISTS org_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_invoices_org_id ON public.invoices(org_id);
UPDATE public.invoices SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.invoice_templates SET org_id = 1 WHERE org_id IS NULL;

-- 5. Contracts + Contract templates
ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.contract_templates ADD COLUMN IF NOT EXISTS org_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_contracts_org_id ON public.contracts(org_id);
UPDATE public.contracts SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.contract_templates SET org_id = 1 WHERE org_id IS NULL;

-- 6. Cold email
ALTER TABLE public.cold_email_drafts ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.cold_email_templates ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.cold_email_drafts SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.cold_email_templates SET org_id = 1 WHERE org_id IS NULL;

-- 7. Email accounts + messages
ALTER TABLE public.email_accounts ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.email_messages ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.email_accounts SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.email_messages SET org_id = 1 WHERE org_id IS NULL;

-- 8. Stripe products
ALTER TABLE public.products_stripe ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.products_stripe SET org_id = 1 WHERE org_id IS NULL;

-- 9. AI Planning
ALTER TABLE public.ai_plans ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.task_dependencies ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.task_executions ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.ai_plans SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.task_dependencies SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.task_executions SET org_id = 1 WHERE org_id IS NULL;

-- 10. UGC Studio
ALTER TABLE public.ugc_video_projects ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.ugc_digital_copies ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.ugc_video_projects SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.ugc_digital_copies SET org_id = 1 WHERE org_id IS NULL;

-- 11. Call intakes
ALTER TABLE public.call_intakes ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.call_intakes SET org_id = 1 WHERE org_id IS NULL;

-- 12. Prospects
ALTER TABLE public.prospects_meta ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.prospects_meta SET org_id = 1 WHERE org_id IS NULL;

-- 13. Lead enrichments
ALTER TABLE public.lead_enrichments ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.lead_enrichments SET org_id = 1 WHERE org_id IS NULL;

-- 14. Contact submissions
ALTER TABLE public.contact_submissions ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.contact_submissions SET org_id = 1 WHERE org_id IS NULL;

-- 15. Blackboard (public schema version)
ALTER TABLE public.blackboard ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.blackboard SET org_id = 1 WHERE org_id IS NULL;

-- 16. Outbound emails
ALTER TABLE public.outbound_emails ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.outbound_emails SET org_id = 1 WHERE org_id IS NULL;

-- 17. Agents + agent tables (may already exist from sub-agent work)
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.agent_task_assignments ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.agent_events ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE public.team_agents ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE public.agents SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.agent_task_assignments SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.agent_events SET org_id = 1 WHERE org_id IS NULL;
UPDATE public.team_agents SET org_id = 1 WHERE org_id IS NULL;

-- 18. CRM junction tables that were skipped
ALTER TABLE crm.blackboard ADD COLUMN IF NOT EXISTS org_id INTEGER;
ALTER TABLE crm.social_snapshots ADD COLUMN IF NOT EXISTS org_id INTEGER;
UPDATE crm.blackboard SET org_id = 1 WHERE org_id IS NULL;
UPDATE crm.social_snapshots SET org_id = 1 WHERE org_id IS NULL;

-- Unique constraint update for settings (key must be unique PER org, not globally)
-- Drop the old unique constraint and add a composite one
DO $$
BEGIN
    -- Drop existing unique constraint on settings.key if it exists
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'settings_key_key') THEN
        ALTER TABLE public.settings DROP CONSTRAINT settings_key_key;
    END IF;
    -- Add composite unique on (key, org_id)
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_settings_key_org') THEN
        ALTER TABLE public.settings ADD CONSTRAINT uq_settings_key_org UNIQUE (key, org_id);
    END IF;
END $$;
