-- Video Copycat Assets & Digital Copies Migration
-- Stage 3: Asset Generation + Stage 4: Avatar Swap

-- Video assets table for storing generated assets (backgrounds, product shots, overlays, etc.)
CREATE TABLE IF NOT EXISTS public.video_assets (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    storyboard_id INTEGER NOT NULL,
    scene_index INTEGER NOT NULL,
    asset_type TEXT NOT NULL,  -- "product-shot", "background", "infographic", "text-overlay", "logo"
    file_path TEXT,
    cloud_url TEXT,
    prompt_used TEXT,
    dimensions TEXT,  -- "1080x1920" format
    format TEXT,  -- "png", "jpg", "webm"
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'complete', 'failed')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_video_assets_org ON public.video_assets(org_id);
CREATE INDEX IF NOT EXISTS idx_video_assets_storyboard ON public.video_assets(storyboard_id);
CREATE INDEX IF NOT EXISTS idx_video_assets_status ON public.video_assets(status);

-- Digital copies table for user avatars and voice clones
CREATE TABLE IF NOT EXISTS crm.digital_copies (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    avatar_images JSONB DEFAULT '[]',  -- list of reference image paths
    voice_clone_id TEXT,
    voice_provider TEXT DEFAULT 'edge-tts',  -- "elevenlabs", "google-tts", "edge-tts"
    default_style TEXT DEFAULT 'professional',  -- "professional", "casual", "energetic"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

-- Indexes for digital copies
CREATE INDEX IF NOT EXISTS idx_digital_copies_org ON crm.digital_copies(org_id);
CREATE INDEX IF NOT EXISTS idx_digital_copies_user ON crm.digital_copies(user_id);