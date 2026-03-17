-- Mirofish Swarm Persona System + Social Friction Test Backend

-- Swarm personas table (audience archetypes)
CREATE TABLE IF NOT EXISTS crm.swarm_personas (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    name TEXT NOT NULL,
    archetype TEXT NOT NULL,
    demographics JSONB DEFAULT '{}',
    psychographics JSONB DEFAULT '{}',
    behavioral_logic JSONB DEFAULT '{}',
    collective_memory JSONB DEFAULT '[]',
    source_competitors TEXT[],
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Simulation results table (social friction test outputs)
CREATE TABLE IF NOT EXISTS crm.simulation_results (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    script_hook TEXT,
    script_body TEXT,
    script_cta TEXT,
    format_slug TEXT,
    persona_ids INT[],
    engagement_score INT,
    predicted_metrics JSONB DEFAULT '{}',
    drop_off_timeline JSONB DEFAULT '[]',
    predicted_comments JSONB DEFAULT '[]',
    optimization_recommendation JSONB DEFAULT '{}',
    scene_friction_map JSONB DEFAULT '[]',
    audio_recommendation JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_swarm_personas_org ON crm.swarm_personas(org_id);
CREATE INDEX IF NOT EXISTS idx_simulation_results_org ON crm.simulation_results(org_id);
CREATE INDEX IF NOT EXISTS idx_swarm_personas_system ON crm.swarm_personas(is_system);
CREATE INDEX IF NOT EXISTS idx_swarm_personas_archetype ON crm.swarm_personas(archetype);

-- Add unique constraint for persona names within org
CREATE UNIQUE INDEX IF NOT EXISTS idx_swarm_personas_org_name ON crm.swarm_personas(org_id, name);

-- Seed default personas based on tech/AI niche (org_id = 0 for system personas)
INSERT INTO crm.swarm_personas (org_id, name, archetype, demographics, psychographics, behavioral_logic, is_system)
VALUES 
(0, 'Skeptical Early Adopter', 'skeptical_dev', 
 '{
   "age_range": "24-40",
   "primary_roles": ["Software Engineer", "Solo-Founder"],
   "tech_stack_affinity": ["Python", "Claude", "n8n"]
 }'::jsonb,
 '{
   "core_desires": ["Eliminate manual tasks", "Stay ahead of AI curve", "Build profitable micro-SaaS"],
   "friction_points": ["Hates AI influencer fluff", "Wary of subscription costs", "Distrusts black-box solutions"],
   "content_bias": {
     "format_preference": "speed_run",
     "hook_sensitivity": 0.85,
     "visual_style": "dark_mode_technical"
   }
 }'::jsonb,
 '{
   "interaction_triggers": {
     "comment_on": ["Technical errors", "Unseen features", "Cost saving hacks"],
     "share_on": ["Unique insights", "Controversial takes on big tech"],
     "bookmark_on": ["Step-by-step guides", "Prompt templates"]
   },
   "comment_style": {
     "tone": "dry_technical_sarcastic",
     "vocabulary_keywords": ["latency", "tokens", "wrapper", "inference", "context window"]
   }
 }'::jsonb,
 true),

(0, 'Hustle Culture Builder', 'hustle_builder',
 '{
   "age_range": "22-35",
   "primary_roles": ["Entrepreneur", "Growth Hacker", "Content Creator"]
 }'::jsonb,
 '{
   "core_desires": ["Scale fast", "Automate everything", "Build audience"],
   "friction_points": ["Hates slow tutorials", "Impatient with theory", "Wants results not process"],
   "content_bias": {
     "format_preference": "transformation",
     "hook_sensitivity": 0.6,
     "visual_style": "high_energy_bright"
   }
 }'::jsonb,
 '{
   "interaction_triggers": {
     "comment_on": ["Revenue numbers", "Growth hacks", "Tool recommendations"],
     "share_on": ["Before/after results", "Mind-blowing automations"],
     "bookmark_on": ["Money-making blueprints", "Tool stacks"]
   },
   "comment_style": {
     "tone": "enthusiastic_emoji_heavy",
     "vocabulary_keywords": ["scale", "passive income", "automation", "10x", "game changer"]
   }
 }'::jsonb,
 true),

(0, 'Curious General Audience', 'general_curious',
 '{
   "age_range": "18-50",
   "primary_roles": ["Professional", "Student", "Curious Observer"]
 }'::jsonb,
 '{
   "core_desires": ["Understand AI trends", "Not get left behind", "Find practical uses"],
   "friction_points": ["Confused by jargon", "Overwhelmed by options", "Skeptical of hype"],
   "content_bias": {
     "format_preference": "myth_buster",
     "hook_sensitivity": 0.5,
     "visual_style": "clean_simple"
   }
 }'::jsonb,
 '{
   "interaction_triggers": {
     "comment_on": ["Simple explanations", "Relatable analogies", "Shocking stats"],
     "share_on": ["Wow factor content", "Things that make them look informed"],
     "bookmark_on": ["Beginner guides", "Comparison posts"]
   },
   "comment_style": {
     "tone": "casual_questioning",
     "vocabulary_keywords": ["how", "what", "explain", "does this mean", "ELI5"]
   }
 }'::jsonb,
 true)
ON CONFLICT (org_id, name) DO NOTHING;