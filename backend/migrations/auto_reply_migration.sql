-- Auto-Reply Rules Engine tables (crm schema)

CREATE TABLE IF NOT EXISTS crm.auto_reply_rules (
  id SERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  platform TEXT NOT NULL DEFAULT 'instagram',
  rule_type TEXT NOT NULL CHECK (rule_type IN ('comment', 'dm', 'follow')),
  name TEXT NOT NULL,
  keywords TEXT[] DEFAULT '{}',  -- Optional for follow triggers
  replies TEXT[] NOT NULL,
  match_mode TEXT DEFAULT 'any' CHECK (match_mode IN ('any', 'all', 'exact')),
  case_sensitive BOOLEAN NOT NULL DEFAULT false,
  is_active BOOLEAN NOT NULL DEFAULT true,
  delivery_channels TEXT[] NOT NULL DEFAULT '{dm}' CHECK (array_length(delivery_channels, 1) > 0),  -- comment, dm, or both
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT valid_follow_rule CHECK (
    rule_type != 'follow' OR (
      array_length(keywords, 1) IS NULL AND 
      'dm' = ANY(delivery_channels)
    )
  ),
  CONSTRAINT valid_comment_dm_rule CHECK (
    rule_type = 'follow' OR array_length(keywords, 1) > 0
  )
);

CREATE TABLE IF NOT EXISTS crm.auto_reply_log (
  id SERIAL PRIMARY KEY,
  rule_id INTEGER REFERENCES crm.auto_reply_rules(id) ON DELETE SET NULL,
  org_id INTEGER NOT NULL,
  platform TEXT NOT NULL,
  rule_type TEXT NOT NULL,
  trigger_type TEXT NOT NULL DEFAULT 'keyword',  -- keyword, follow
  original_text TEXT DEFAULT '',  -- Empty for follow events
  matched_keyword TEXT,
  reply_sent TEXT,
  delivery_channel TEXT NOT NULL,  -- comment, dm
  social_account_id INTEGER,
  external_id TEXT,
  username TEXT,  -- For follow events
  status TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'failed', 'skipped')),
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auto_reply_rules_org ON crm.auto_reply_rules(org_id, is_active);
CREATE INDEX IF NOT EXISTS idx_auto_reply_log_org ON crm.auto_reply_log(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auto_reply_log_external ON crm.auto_reply_log(external_id);
