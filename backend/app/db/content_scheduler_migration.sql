-- Content Scheduler Database Migration
-- Video Copycat Stages 5-6: Composition + Content Scheduling + Performance Tracking

-- ═══════════════════════════════════════════════════════════════════
-- Scheduled Posts Table
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.scheduled_posts (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('instagram', 'tiktok', 'youtube-shorts', 'facebook')),
    content_type TEXT DEFAULT 'video' CHECK (content_type IN ('video', 'image', 'carousel')),
    media_path TEXT,
    cloud_url TEXT,
    caption TEXT DEFAULT '',
    hashtags JSONB DEFAULT '[]',
    scheduled_for TIMESTAMP,
    published_at TIMESTAMP,
    published_url TEXT,
    storyboard_id INTEGER,  -- FK to video_storyboards (future table)
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'publishing', 'published', 'failed', 'cancelled')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_org ON public.scheduled_posts(org_id, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON public.scheduled_posts(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_platform ON public.scheduled_posts(platform);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_storyboard ON public.scheduled_posts(storyboard_id);

-- ═══════════════════════════════════════════════════════════════════
-- Content Metrics Table  
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.content_metrics (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL REFERENCES public.scheduled_posts(id) ON DELETE CASCADE,
    snapshot_at TIMESTAMP DEFAULT NOW(),
    
    -- Basic engagement metrics
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    
    -- Calculated metrics
    engagement_rate NUMERIC(8,4) DEFAULT 0,  -- (likes+comments+shares+saves)/views * 100
    watch_time_avg NUMERIC(8,2) DEFAULT 0,   -- Average watch time in seconds
    hook_retention NUMERIC(5,2) DEFAULT 0,   -- % who watch past 3 seconds
    viral_score NUMERIC(5,2) DEFAULT 0,      -- Calculated viral score 0-100
    
    -- Raw platform data for future analysis
    raw_data JSONB DEFAULT '{}'
);

-- Indexes for performance analytics
CREATE INDEX IF NOT EXISTS idx_content_metrics_org ON public.content_metrics(org_id);
CREATE INDEX IF NOT EXISTS idx_content_metrics_post ON public.content_metrics(post_id, snapshot_at);
CREATE INDEX IF NOT EXISTS idx_content_metrics_viral ON public.content_metrics(org_id, viral_score DESC);
CREATE INDEX IF NOT EXISTS idx_content_metrics_time ON public.content_metrics(snapshot_at);

-- ═══════════════════════════════════════════════════════════════════
-- NOTE: video_storyboards table is owned by video_copycat_migration.sql
-- Video Compositions Table (Remotion configs) — references video_storyboards
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.video_compositions (
    id SERIAL PRIMARY KEY,
    storyboard_id INTEGER NOT NULL,  -- FK to video_storyboards (created by video_copycat migration)
    
    -- Composition metadata
    composition_name TEXT NOT NULL,
    remotion_config JSONB NOT NULL,     -- Full Remotion configuration
    
    -- Render status
    rendered_video_path TEXT,           -- Path to rendered video
    render_status TEXT DEFAULT 'pending' CHECK (render_status IN ('pending', 'rendering', 'completed', 'failed')),
    render_error TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_compositions_storyboard ON public.video_compositions(storyboard_id);

-- ═══════════════════════════════════════════════════════════════════
-- Content Templates Table (for copycat patterns)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.content_templates (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    
    -- Template structure
    template_type TEXT DEFAULT 'video' CHECK (template_type IN ('video', 'image', 'carousel')),
    scene_structure JSONB DEFAULT '[]',  -- Template scene structure
    caption_template TEXT DEFAULT '',    -- Template caption with placeholders
    hashtag_groups JSONB DEFAULT '[]',   -- Suggested hashtag groups
    
    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    avg_performance NUMERIC(5,2) DEFAULT 0,  -- Average viral score of content using this template
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER,                  -- User who created template
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_templates_org ON public.content_templates(org_id);
CREATE INDEX IF NOT EXISTS idx_content_templates_category ON public.content_templates(category);
CREATE INDEX IF NOT EXISTS idx_content_templates_performance ON public.content_templates(avg_performance DESC);

-- ═══════════════════════════════════════════════════════════════════
-- Update Triggers
-- ═══════════════════════════════════════════════════════════════════

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
DROP TRIGGER IF EXISTS update_scheduled_posts_updated_at ON public.scheduled_posts;
CREATE TRIGGER update_scheduled_posts_updated_at
    BEFORE UPDATE ON public.scheduled_posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_video_compositions_updated_at ON public.video_compositions;
CREATE TRIGGER update_video_compositions_updated_at
    BEFORE UPDATE ON public.video_compositions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_content_templates_updated_at ON public.content_templates;
CREATE TRIGGER update_content_templates_updated_at
    BEFORE UPDATE ON public.content_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ═══════════════════════════════════════════════════════════════════
-- Sample Data (Optional)
-- ═══════════════════════════════════════════════════════════════════

-- Insert sample content templates
INSERT INTO public.content_templates (org_id, name, description, category, scene_structure, caption_template, hashtag_groups, created_by)
VALUES 
(1, 'Hormozi Hook', 'Alex Hormozi style attention-grabbing opener', 'marketing', 
 '[{"type": "hook", "duration": 3}, {"type": "proof", "duration": 4}, {"type": "cta", "duration": 2}]',
 'If you {problem}, here''s what you need to know... {solution} {cta}',
 '["#entrepreneurship", "#business", "#marketing"]', 1),
 
(1, 'Product Demo', 'Quick product demonstration with benefits', 'product',
 '[{"type": "problem", "duration": 2}, {"type": "demo", "duration": 5}, {"type": "benefits", "duration": 3}]',
 'Watch me {action} in {time}... This {product} will {benefit} {cta}',
 '["#product", "#demo", "#review"]', 1),
 
(1, 'Behind Scenes', 'Behind the scenes content for engagement', 'lifestyle',
 '[{"type": "setup", "duration": 2}, {"type": "process", "duration": 6}, {"type": "result", "duration": 2}]',
 'Behind the scenes: {process}... Here''s what happened {result}',
 '["#behindthescenes", "#process", "#authentic"]', 1)
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════
-- Views for Analytics
-- ═══════════════════════════════════════════════════════════════════

-- Performance summary view
CREATE OR REPLACE VIEW content_performance_summary AS
SELECT 
    sp.org_id,
    sp.platform,
    sp.content_type,
    COUNT(*) as total_posts,
    COUNT(CASE WHEN sp.status = 'published' THEN 1 END) as published_posts,
    AVG(cm.viral_score) as avg_viral_score,
    AVG(cm.engagement_rate) as avg_engagement_rate,
    AVG(cm.hook_retention) as avg_hook_retention,
    SUM(cm.views) as total_views,
    SUM(cm.likes + cm.comments + cm.shares + cm.saves) as total_engagements
FROM public.scheduled_posts sp
LEFT JOIN public.content_metrics cm ON sp.id = cm.post_id
WHERE sp.created_at >= NOW() - INTERVAL '30 days'
GROUP BY sp.org_id, sp.platform, sp.content_type;

-- Top performing content view
CREATE OR REPLACE VIEW top_performing_content AS
SELECT 
    sp.id,
    sp.org_id,
    sp.platform,
    sp.caption,
    sp.published_at,
    cm.views,
    cm.likes,
    cm.comments,
    cm.shares,
    cm.saves,
    cm.engagement_rate,
    cm.viral_score,
    RANK() OVER (PARTITION BY sp.org_id ORDER BY cm.viral_score DESC) as viral_rank
FROM public.scheduled_posts sp
JOIN public.content_metrics cm ON sp.id = cm.post_id
WHERE sp.status = 'published'
AND sp.published_at >= NOW() - INTERVAL '90 days';

-- ═══════════════════════════════════════════════════════════════════
-- Cleanup and Maintenance
-- ═══════════════════════════════════════════════════════════════════

-- Function to clean up old metrics (keep last 1000 per post)
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH old_metrics AS (
        SELECT id
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY post_id ORDER BY snapshot_at DESC) as rn
            FROM public.content_metrics
        ) ranked
        WHERE rn > 1000
    )
    DELETE FROM public.content_metrics
    WHERE id IN (SELECT id FROM old_metrics);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════

-- Migration complete
SELECT 'Content Scheduler migration completed successfully' as status;