-- Carousel Posts Migration
-- Creates tables for text-to-carousel functionality and Instagram Graph API posting

CREATE TABLE IF NOT EXISTS crm.carousel_posts (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    source_text TEXT,
    format TEXT DEFAULT 'portrait', -- portrait|square|story
    slides JSONB, -- [{"slide_num": 1, "text": "...", "image_url": "", "is_hook": true}, ...]
    caption TEXT,
    hashtags TEXT[],
    status TEXT DEFAULT 'draft', -- draft|generating|ready|publishing|published|failed
    instagram_post_id TEXT,
    published_url TEXT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_carousel_posts_org_id ON crm.carousel_posts(org_id);
CREATE INDEX IF NOT EXISTS idx_carousel_posts_status ON crm.carousel_posts(status);
CREATE INDEX IF NOT EXISTS idx_carousel_posts_created_at ON crm.carousel_posts(created_at);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_carousel_posts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_carousel_posts_updated_at
    BEFORE UPDATE ON crm.carousel_posts
    FOR EACH ROW
    EXECUTE FUNCTION update_carousel_posts_updated_at();