-- Add columns for emerging format detection to competitor_posts table

ALTER TABLE crm.competitor_posts 
ADD COLUMN IF NOT EXISTS detected_format VARCHAR(50),
ADD COLUMN IF NOT EXISTS format_confidence REAL,
ADD COLUMN IF NOT EXISTS classified_at TIMESTAMP WITH TIME ZONE;

-- Create index for efficient format queries
CREATE INDEX IF NOT EXISTS idx_competitor_posts_detected_format 
ON crm.competitor_posts(detected_format);

CREATE INDEX IF NOT EXISTS idx_competitor_posts_org_format 
ON crm.competitor_posts(competitor_id, detected_format, engagement_score);

-- Add columns to video_formats table for stats tracking
ALTER TABLE crm.video_formats 
ADD COLUMN IF NOT EXISTS post_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_engagement_score REAL DEFAULT 0,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Update existing video_formats with timestamps
UPDATE crm.video_formats 
SET updated_at = NOW() 
WHERE updated_at IS NULL;

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_video_formats_updated_at 
BEFORE UPDATE ON crm.video_formats 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();