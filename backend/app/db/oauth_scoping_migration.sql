-- OAuth Scoping System Migration
-- Adds visibility control to social accounts and OAuth tokens
-- Private: only connecting user's agent can use it
-- Shared dept: users in same department can access
-- Shared org: any user in the org can access

BEGIN;

-- Add visibility columns to social_accounts
ALTER TABLE crm.social_accounts ADD COLUMN IF NOT EXISTS visibility_type TEXT NOT NULL DEFAULT 'private' CHECK (visibility_type IN ('private', 'shared_dept', 'shared_org'));
ALTER TABLE crm.social_accounts ADD COLUMN IF NOT EXISTS shared_by_user_id INTEGER REFERENCES crm.users(id) ON DELETE SET NULL;

-- Add visibility to any existing OAuth token tables
-- Check if there are other tables that store credentials/tokens that need scoping

-- Index for performance on visibility queries
CREATE INDEX IF NOT EXISTS idx_social_accounts_visibility ON crm.social_accounts(visibility_type, org_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_shared_by ON crm.social_accounts(shared_by_user_id);

COMMIT;