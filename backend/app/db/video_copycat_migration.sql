-- Video Copycat Migration - Storyboard analysis and script generation
-- Creates tables for Video Copycat pipeline in public schema

-- Video Storyboards Table
-- Stores analyzed video structure (JSON storyboard) and generated scripts
CREATE TABLE IF NOT EXISTS public.video_storyboards (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    source_url TEXT,
    source_competitor_id INTEGER,  -- FK to crm.competitors if from competitor
    storyboard JSONB NOT NULL,     -- the full VideoStoryboard as JSON
    generated_script JSONB,        -- the VideoScript if generated
    status TEXT DEFAULT 'analyzed' CHECK (status IN ('analyzing', 'analyzed', 'scripted', 'generating', 'composed', 'published')),
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for org-level queries (all video copycat operations are org-scoped)
CREATE INDEX IF NOT EXISTS idx_video_storyboards_org ON public.video_storyboards(org_id);

-- Index for user-level queries
CREATE INDEX IF NOT EXISTS idx_video_storyboards_user ON public.video_storyboards(user_id);

-- Index for competitor analysis queries
CREATE INDEX IF NOT EXISTS idx_video_storyboards_competitor ON public.video_storyboards(source_competitor_id) WHERE source_competitor_id IS NOT NULL;

-- Index for status-based filtering
CREATE INDEX IF NOT EXISTS idx_video_storyboards_status ON public.video_storyboards(org_id, status);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_video_storyboards_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_video_storyboards_updated_at ON public.video_storyboards;
CREATE TRIGGER trigger_update_video_storyboards_updated_at
    BEFORE UPDATE ON public.video_storyboards
    FOR EACH ROW
    EXECUTE FUNCTION update_video_storyboards_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.video_storyboards IS 'Video Copycat pipeline - stores analyzed video storyboards and generated scripts';
COMMENT ON COLUMN public.video_storyboards.storyboard IS 'Full VideoStoryboard object as JSON - contains scene breakdown, timing, and structure';
COMMENT ON COLUMN public.video_storyboards.generated_script IS 'VideoScript object as JSON if script generation was performed';
COMMENT ON COLUMN public.video_storyboards.source_competitor_id IS 'Optional FK to crm.competitors for competitor video analysis';
COMMENT ON COLUMN public.video_storyboards.status IS 'Pipeline status: analyzing -> analyzed -> scripted (with optional generating/composed/published stages)';