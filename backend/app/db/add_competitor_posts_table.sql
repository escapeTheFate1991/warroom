-- Add competitor_posts table for caching competitor content
CREATE TABLE IF NOT EXISTS crm.competitor_posts (
    id SERIAL PRIMARY KEY,
    competitor_id INTEGER REFERENCES crm.competitors(id) ON DELETE CASCADE,
    platform VARCHAR NOT NULL,
    post_text TEXT,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    engagement_score FLOAT DEFAULT 0,
    hook TEXT,
    post_url VARCHAR,
    posted_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_competitor_posts_competitor_id ON crm.competitor_posts(competitor_id);
CREATE INDEX IF NOT EXISTS idx_competitor_posts_engagement ON crm.competitor_posts(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_posts_posted_at ON crm.competitor_posts(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_posts_fetched_at ON crm.competitor_posts(fetched_at DESC);