-- Content Distribution System Migration
-- Adds smart multi-account distribution with anti-detection measures

-- Content distributions table
CREATE TABLE IF NOT EXISTS crm.content_distributions (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    user_id INT NOT NULL,
    video_project_id INT,
    original_caption TEXT,
    total_posts INT DEFAULT 0,
    stagger_hours FLOAT DEFAULT 2,
    cluster_size INT DEFAULT 5,
    visibility_score INT,
    randomizer_config JSONB DEFAULT '{}',
    status TEXT DEFAULT 'scheduled',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Distribution posts table
CREATE TABLE IF NOT EXISTS crm.distribution_posts (
    id SERIAL PRIMARY KEY,
    distribution_id INT REFERENCES crm.content_distributions(id),
    account_id INT,
    platform TEXT NOT NULL,
    scheduled_time TIMESTAMPTZ NOT NULL,
    caption_variant TEXT,
    video_variant_hash TEXT,
    status TEXT DEFAULT 'queued',
    post_url TEXT,
    posted_at TIMESTAMPTZ,
    error TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_distributions_org_id ON crm.content_distributions(org_id);
CREATE INDEX IF NOT EXISTS idx_content_distributions_user_id ON crm.content_distributions(user_id);
CREATE INDEX IF NOT EXISTS idx_content_distributions_status ON crm.content_distributions(status);
CREATE INDEX IF NOT EXISTS idx_distribution_posts_distribution_id ON crm.distribution_posts(distribution_id);
CREATE INDEX IF NOT EXISTS idx_distribution_posts_account_id ON crm.distribution_posts(account_id);
CREATE INDEX IF NOT EXISTS idx_distribution_posts_platform ON crm.distribution_posts(platform);
CREATE INDEX IF NOT EXISTS idx_distribution_posts_scheduled_time ON crm.distribution_posts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_distribution_posts_status ON crm.distribution_posts(status);