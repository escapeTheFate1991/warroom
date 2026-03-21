-- Add music_info column to competitor_posts table
ALTER TABLE crm.competitor_posts ADD COLUMN IF NOT EXISTS music_info JSONB;

-- Create index for music queries
CREATE INDEX IF NOT EXISTS idx_competitor_posts_music_info ON crm.competitor_posts USING GIN(music_info);

-- Add comment
COMMENT ON COLUMN crm.competitor_posts.music_info IS 'Music metadata from Instagram posts: {track_name, artist, is_original}';