-- War Room Audit Trail System Migration
-- Creates an immutable audit trail for all platform activities

CREATE TABLE IF NOT EXISTS public.audit_trail (
    id BIGSERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    actor_id INTEGER NOT NULL,          -- user who performed the action
    actor_email TEXT,                   -- denormalized for quick display
    action TEXT NOT NULL,               -- e.g., 'view', 'create', 'update', 'delete', 'export', 'login', 'permission_change'
    resource_type TEXT NOT NULL,        -- e.g., 'deal', 'contact', 'setting', 'user', 'agent'
    resource_id TEXT,                   -- ID of the affected resource
    target_user_id INTEGER,             -- if action affects another user (admin viewing employee data)
    details JSONB DEFAULT '{}',         -- action-specific metadata (old_value, new_value, etc.)
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_audit_trail_org ON public.audit_trail(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trail_actor ON public.audit_trail(actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trail_resource ON public.audit_trail(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_action ON public.audit_trail(action);
CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at ON public.audit_trail(created_at DESC);

-- Comment to document the table purpose
COMMENT ON TABLE public.audit_trail IS 'Immutable audit trail for all War Room platform activities';
COMMENT ON COLUMN public.audit_trail.actor_id IS 'User who performed the action';
COMMENT ON COLUMN public.audit_trail.actor_email IS 'Denormalized email for quick display without joins';
COMMENT ON COLUMN public.audit_trail.target_user_id IS 'Used when action affects another user (e.g., admin viewing employee data)';
COMMENT ON COLUMN public.audit_trail.details IS 'Action-specific metadata including old/new values, context, etc.';