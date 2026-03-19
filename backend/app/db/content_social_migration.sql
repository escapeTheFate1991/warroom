-- Content Social Migration
-- Creates content_drafts table for Article → Social Media Posts pipeline

-- Content drafts table (stores extracted content + generated posts)
CREATE TABLE IF NOT EXISTS crm.content_drafts (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    source_url TEXT,
    extracted_content JSONB,           -- Raw extracted content from ContentExtractor
    generated_posts JSONB,             -- Generated posts per platform
    selected_platforms TEXT[],         -- Platforms selected for publishing
    approval_id INT,                   -- References crm.approvals(id) if approval required
    status TEXT DEFAULT 'draft',      -- draft|pending_approval|approved|scheduled|published|rejected
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Add foreign key constraint for approval
    CONSTRAINT fk_content_drafts_approval 
        FOREIGN KEY (approval_id) REFERENCES crm.approvals(id) 
        ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_drafts_org_id ON crm.content_drafts(org_id);
CREATE INDEX IF NOT EXISTS idx_content_drafts_status ON crm.content_drafts(status);
CREATE INDEX IF NOT EXISTS idx_content_drafts_created_at ON crm.content_drafts(created_at);
CREATE INDEX IF NOT EXISTS idx_content_drafts_approval_id ON crm.content_drafts(approval_id);

-- Comments for documentation
COMMENT ON TABLE crm.content_drafts IS 'Content extraction and social post generation pipeline';
COMMENT ON COLUMN crm.content_drafts.extracted_content IS 'Raw content extracted from URLs (title, body_text, images, etc.)';
COMMENT ON COLUMN crm.content_drafts.generated_posts IS 'Platform-specific generated posts with text, hashtags, media suggestions';
COMMENT ON COLUMN crm.content_drafts.selected_platforms IS 'Array of platforms selected for publishing (instagram, tiktok, twitter, linkedin, facebook)';
COMMENT ON COLUMN crm.content_drafts.status IS 'Draft lifecycle: draft → pending_approval → approved → scheduled → published';