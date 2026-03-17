-- Digital Copies Migration
-- Soul ID system for persistent AI characters with uploaded photos and consistent appearance

CREATE TABLE IF NOT EXISTS crm.digital_copies (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    user_id INT NOT NULL,
    name TEXT NOT NULL,
    trigger_token TEXT UNIQUE,
    status TEXT DEFAULT 'draft',
    base_model TEXT DEFAULT 'veo_3.1',
    training_meta JSONB DEFAULT '{}',
    prompt_anchor TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.digital_copy_images (
    id SERIAL PRIMARY KEY,
    digital_copy_id INT REFERENCES crm.digital_copies(id) ON DELETE CASCADE,
    image_type TEXT NOT NULL,
    image_url TEXT NOT NULL,
    angle TEXT,
    resolution_width INT,
    resolution_height INT,
    quality_score FLOAT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm.digital_copy_performance (
    id SERIAL PRIMARY KEY,
    digital_copy_id INT REFERENCES crm.digital_copies(id) ON DELETE CASCADE,
    avg_engagement FLOAT DEFAULT 0,
    trust_index FLOAT DEFAULT 0,
    top_format_slug TEXT,
    last_simulated TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS crm.action_templates (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    remotion_config JSONB DEFAULT '{}',
    ai_params JSONB DEFAULT '{}',
    prompt_fragment TEXT,
    is_system BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_digital_copies_org ON crm.digital_copies(org_id);
CREATE INDEX IF NOT EXISTS idx_digital_copy_images_copy ON crm.digital_copy_images(digital_copy_id);
CREATE INDEX IF NOT EXISTS idx_action_templates_org ON crm.action_templates(org_id);

-- Seed default action templates
INSERT INTO crm.action_templates (org_id, slug, name, description, prompt_fragment, ai_params, is_system, created_at)
VALUES 
    (0, 'selling_ugc', 'Selling / UGC', 'High energy sales-focused UGC content', 
     'high energy, hand gestures, speaking directly to camera, studio lighting', 
     '{"camera_zoom": 1.25, "animation_profile": "energetic"}', 
     true, NOW()),
    (0, 'car_talking', 'Car Talking POV', 'Casual conversation from car interior', 
     'sitting in car, natural morning light, slight head tilt, casual speaking', 
     '{"camera_zoom": 1.1, "camera_rotation": 2.5, "animation_profile": "handheld"}', 
     true, NOW()),
    (0, 'podcast_seated', 'Podcast / Seated', 'Professional seated conversation setup', 
     'seated at desk, professional setting, neon accent lighting, headphones', 
     '{"camera_zoom": 1.0, "animation_profile": "calm"}', 
     true, NOW()),
    (0, 'walking_vlog', 'Walking Vlog', 'Dynamic outdoor vlog style', 
     'walking outdoors, dynamic movement, selfie angle, natural light', 
     '{"camera_zoom": 1.15, "animation_profile": "dynamic"}', 
     true, NOW()),
    (0, 'presentation', 'Presentation', 'Professional presentation style', 
     'standing, gesturing at screen/whiteboard, professional attire', 
     '{"camera_zoom": 0.9, "animation_profile": "professional"}', 
     true, NOW())
ON CONFLICT (org_id, slug) DO NOTHING;