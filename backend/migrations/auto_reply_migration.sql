-- Auto-Reply Rules Engine tables (crm schema)

CREATE TABLE IF NOT EXISTS crm.auto_reply_rules (
  id SERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  platform TEXT NOT NULL DEFAULT 'instagram',
  rule_type TEXT NOT NULL CHECK (rule_type IN ('comment', 'dm')),
  name TEXT NOT NULL,
  keywords TEXT[] NOT NULL,
  replies TEXT[] NOT NULL,
  match_mode TEXT NOT NULL DEFAULT 'any' CHECK (match_mode IN ('any', 'all', 'exact')),
  case_sensitive BOOLEAN NOT NULL DEFAULT false,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.auto_reply_log (
  id SERIAL PRIMARY KEY,
  rule_id INTEGER REFERENCES crm.auto_reply_rules(id) ON DELETE SET NULL,
  org_id INTEGER NOT NULL,
  platform TEXT NOT NULL,
  rule_type TEXT NOT NULL,
  original_text TEXT NOT NULL,
  matched_keyword TEXT,
  reply_sent TEXT,
  social_account_id INTEGER,
  external_id TEXT,
  status TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'failed', 'skipped')),
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auto_reply_rules_org ON crm.auto_reply_rules(org_id, is_active);
CREATE INDEX IF NOT EXISTS idx_auto_reply_log_org ON crm.auto_reply_log(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auto_reply_log_external ON crm.auto_reply_log(external_id);
