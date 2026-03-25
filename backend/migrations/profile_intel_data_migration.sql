-- Profile Intelligence Data Pipeline table (crm schema)

CREATE TABLE IF NOT EXISTS crm.profile_intel_data (
  id SERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  profile_id VARCHAR(255) NOT NULL,
  platform VARCHAR(50) NOT NULL DEFAULT 'instagram',
  last_synced_at TIMESTAMPTZ,
  
  -- OAuth data from connected accounts (JSONB)
  -- Structure: {followerCount, followingCount, postCount, reachMetrics, audienceDemographics, topPerformingPosts, engagementRate, replyRate, avgReplyTime}
  oauth_data JSONB,
  
  -- Scraped public profile data (JSONB)
  -- Structure: {bio, profilePicUrl, linkInBio, highlightCovers, recentPostCaptions, gridAesthetic, postingFrequency, hashtagUsage}
  scraped_data JSONB,
  
  -- Analyzed videos (JSONB)
  -- Structure: [{videoId, grade, strengths, weaknesses}]
  processed_videos JSONB,
  
  -- Profile grades across 6 categories (JSONB)
  -- Structure: {profileOptimization: {score, details}, videoMessaging, storyboarding, audienceEngagement, contentConsistency, replyQuality}
  grades JSONB,
  
  -- AI-generated recommendations (JSONB)
  -- Structure: {profileChanges: [{what, why, priority}], videosToDelete: [{videoId, reason}], keepDoing: [{what, evidence}], stopDoing: [{what, evidence}], nextSteps: [{action, expectedImpact, priority}]}
  recommendations JSONB,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Ensure unique profile per org/platform
  CONSTRAINT unique_profile_org_platform UNIQUE (org_id, profile_id, platform)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_profile_intel_org ON crm.profile_intel_data(org_id);
CREATE INDEX IF NOT EXISTS idx_profile_intel_profile ON crm.profile_intel_data(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_intel_platform ON crm.profile_intel_data(platform);
CREATE INDEX IF NOT EXISTS idx_profile_intel_synced ON crm.profile_intel_data(last_synced_at);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_profile_intel_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update the updated_at column
CREATE TRIGGER profile_intel_updated_at_trigger
    BEFORE UPDATE ON crm.profile_intel_data
    FOR EACH ROW
    EXECUTE FUNCTION update_profile_intel_updated_at();