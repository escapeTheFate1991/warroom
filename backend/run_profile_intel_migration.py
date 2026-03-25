#!/usr/bin/env python3
"""
Run database migration for profile intelligence data pipeline
"""
import asyncio
import os
import asyncpg

async def run_migration():
    # Connection string from environment
    db_url = "postgresql://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
    
    migration_sql = """
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
    DROP TRIGGER IF EXISTS profile_intel_updated_at_trigger ON crm.profile_intel_data;
    CREATE TRIGGER profile_intel_updated_at_trigger
        BEFORE UPDATE ON crm.profile_intel_data
        FOR EACH ROW
        EXECUTE FUNCTION update_profile_intel_updated_at();
    """
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # Run migration
        await conn.execute(migration_sql)
        print("Profile Intel Data Pipeline migration completed successfully!")
        
        # Check if table was created
        result = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'crm' 
              AND table_name = 'profile_intel_data'
            ORDER BY ordinal_position
        """)
        
        print("Profile Intel Data table columns:")
        for row in result:
            print(f"  {row['column_name']}: {row['data_type']}")
        
        # Check if trigger was created
        trigger_result = await conn.fetch("""
            SELECT trigger_name 
            FROM information_schema.triggers 
            WHERE event_object_schema = 'crm' 
              AND event_object_table = 'profile_intel_data'
        """)
        
        print("Triggers:", [row['trigger_name'] for row in trigger_result])
        
        # Close connection
        await conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_migration())