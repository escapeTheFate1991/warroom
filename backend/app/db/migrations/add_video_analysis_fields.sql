-- Add frame-by-frame video analysis fields to competitor_posts
-- Wave 1: Competitor Intel Enhancement for video cloning pipeline

ALTER TABLE crm.competitor_posts 
ADD COLUMN IF NOT EXISTS video_analysis JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS frame_chunks JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS analysis_status VARCHAR DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP DEFAULT NULL;

-- Create index for analysis queries
CREATE INDEX IF NOT EXISTS idx_competitor_posts_analysis_status ON crm.competitor_posts(analysis_status);
CREATE INDEX IF NOT EXISTS idx_competitor_posts_analyzed_at ON crm.competitor_posts(analyzed_at DESC);

-- Analysis status values:
-- 'pending': Not analyzed yet
-- 'processing': Currently being analyzed 
-- 'completed': Analysis finished successfully
-- 'failed': Analysis failed
-- 'skipped': Not a video or analysis not needed

COMMENT ON COLUMN crm.competitor_posts.video_analysis IS 'Full @dymoo/media-understanding analysis output';
COMMENT ON COLUMN crm.competitor_posts.frame_chunks IS 'Array of 8-second chunks with timestamps, descriptions, and VEO prompts';
COMMENT ON COLUMN crm.competitor_posts.analysis_status IS 'pending|processing|completed|failed|skipped';
COMMENT ON COLUMN crm.competitor_posts.analyzed_at IS 'Timestamp when frame analysis was completed';