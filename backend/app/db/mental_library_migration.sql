-- Mental Library Migration — Creates ml_videos + ml_chunks tables in CRM schema
-- This migration ensures the Mental Library tables exist with proper org_id filtering

BEGIN;

-- Create ml_videos table in CRM schema
CREATE TABLE IF NOT EXISTS crm.ml_videos (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT DEFAULT '',
    author TEXT DEFAULT '',
    description TEXT DEFAULT '',
    duration INTEGER DEFAULT 0,
    thumbnail_url TEXT DEFAULT '',
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    transcript_path TEXT DEFAULT '',
    audio_path TEXT DEFAULT '',
    topic_tags TEXT DEFAULT '',
    language TEXT DEFAULT 'en',
    chunk_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT DEFAULT '',
    document_text TEXT DEFAULT '',
    org_id INTEGER NOT NULL REFERENCES crm.organizations_tenant(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ml_service_id INTEGER DEFAULT NULL, -- Foreign key to ML service's internal ID
    -- Additional columns from library_ingest
    media_type TEXT DEFAULT 'video',
    source_url TEXT,
    ingestion_method TEXT DEFAULT 'manual'
);

-- Create ml_chunks table in CRM schema
CREATE TABLE IF NOT EXISTS crm.ml_chunks (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES crm.ml_videos(id) ON DELETE CASCADE,
    chunk_index INTEGER DEFAULT 0,
    text TEXT DEFAULT '',
    start_time REAL DEFAULT 0,
    end_time REAL DEFAULT 0,
    embedding_vector_id TEXT DEFAULT '',
    token_count INTEGER DEFAULT 0,
    topic_tags TEXT DEFAULT '',
    confidence_score REAL DEFAULT 0,
    org_id INTEGER NOT NULL REFERENCES crm.organizations_tenant(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Additional columns from library_ingest
    source_url TEXT,
    chunk_type TEXT DEFAULT 'transcript',
    frame_data JSONB DEFAULT '{}'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ml_videos_org_id ON crm.ml_videos(org_id);
CREATE INDEX IF NOT EXISTS idx_ml_videos_status ON crm.ml_videos(status);
CREATE INDEX IF NOT EXISTS idx_ml_videos_url ON crm.ml_videos(url);
CREATE INDEX IF NOT EXISTS idx_ml_videos_ml_service_id ON crm.ml_videos(ml_service_id);
CREATE INDEX IF NOT EXISTS idx_ml_videos_processed_at ON crm.ml_videos(processed_at DESC);

CREATE INDEX IF NOT EXISTS idx_ml_chunks_org_id ON crm.ml_chunks(org_id);
CREATE INDEX IF NOT EXISTS idx_ml_chunks_video_id ON crm.ml_chunks(video_id);
CREATE INDEX IF NOT EXISTS idx_ml_chunks_chunk_index ON crm.ml_chunks(video_id, chunk_index);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_ml_videos_title_trgm ON crm.ml_videos USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ml_videos_author_trgm ON crm.ml_videos USING gin(author gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ml_videos_tags_trgm ON crm.ml_videos USING gin(topic_tags gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ml_chunks_text_trgm ON crm.ml_chunks USING gin(text gin_trgm_ops);

-- Enable pg_trgm extension for trigram search (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMIT;