-- Migration: Veo 3.1 Video Operations Table
-- Created: 2026-03-17
-- Description: Track video generation operations for Digital Copies

CREATE TABLE IF NOT EXISTS crm.video_operations (
    id SERIAL PRIMARY KEY,
    digital_copy_id INTEGER NOT NULL REFERENCES crm.digital_copies(id) ON DELETE CASCADE,
    operation_id VARCHAR(255) NOT NULL UNIQUE,
    prompt TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    s3_url TEXT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_video_operations_digital_copy_id ON crm.video_operations(digital_copy_id);
CREATE INDEX IF NOT EXISTS idx_video_operations_operation_id ON crm.video_operations(operation_id);
CREATE INDEX IF NOT EXISTS idx_video_operations_status ON crm.video_operations(status);
CREATE INDEX IF NOT EXISTS idx_video_operations_created_at ON crm.video_operations(created_at);

-- Comments
COMMENT ON TABLE crm.video_operations IS 'Tracks Veo 3.1 video generation operations for Digital Copies';
COMMENT ON COLUMN crm.video_operations.operation_id IS 'Unique operation ID from Veo API';
COMMENT ON COLUMN crm.video_operations.status IS 'pending, running, complete, failed';
COMMENT ON COLUMN crm.video_operations.progress IS 'Completion percentage 0-100';
COMMENT ON COLUMN crm.video_operations.s3_url IS 'S3 URL after video is downloaded and stored';