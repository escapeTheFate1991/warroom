-- Content Engine Migration: Video Formats + Format Detection + Performance Tracking

-- Video Formats table
CREATE TABLE IF NOT EXISTS crm.video_formats (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    why_it_works TEXT,
    hook_patterns JSONB DEFAULT '[]',
    scene_structure JSONB DEFAULT '[]',
    avg_engagement_score FLOAT,
    post_count INT DEFAULT 0,
    is_system BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, slug)
);

-- Add detected_format to competitor_posts
ALTER TABLE crm.competitor_posts ADD COLUMN IF NOT EXISTS detected_format TEXT;

-- Content performance feedback table (for Phase 4)
CREATE TABLE IF NOT EXISTS crm.content_performance_feedback (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    scheduled_post_id INT,
    competitor_inspiration_ids INT[],
    format_slug TEXT,
    hook_text TEXT,
    hook_score FLOAT,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    saves INT DEFAULT 0,
    reach INT DEFAULT 0,
    views INT DEFAULT 0,
    engagement_score FLOAT,
    competitor_avg_engagement FLOAT,
    performance_delta FLOAT,
    performance_tier TEXT,
    audience_feedback JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_video_formats_org_id ON crm.video_formats(org_id);
CREATE INDEX IF NOT EXISTS idx_video_formats_slug ON crm.video_formats(slug);
CREATE INDEX IF NOT EXISTS idx_video_formats_system ON crm.video_formats(is_system);
CREATE INDEX IF NOT EXISTS idx_competitor_posts_detected_format ON crm.competitor_posts(detected_format);
CREATE INDEX IF NOT EXISTS idx_content_performance_org_id ON crm.content_performance_feedback(org_id);
CREATE INDEX IF NOT EXISTS idx_content_performance_format ON crm.content_performance_feedback(format_slug);

-- Seed the 8 viral video formats (org_id = 0 for system formats)
INSERT INTO crm.video_formats (org_id, slug, name, description, why_it_works, hook_patterns, scene_structure, is_system)
VALUES 
(0, 'myth_buster', 'Myth Buster', 'Challenge common beliefs or misconceptions to create immediate engagement.', 
 'People feel validated or attacked — both emotions drive engagement and shares.', 
 '[
   "Everyone thinks [belief] but here''s why that''s wrong",
   "They told you [myth] — here''s the truth",
   "Stop believing this lie about [topic]",
   "This common advice is actually terrible"
 ]'::jsonb,
 '[
   {"title": "Hook (belief)", "duration_hint": "0-3s", "description": "Open with the myth or common belief that you''ll debunk"},
   {"title": "Counter-evidence", "duration_hint": "3-15s", "description": "Present your contrarian evidence or perspective"},
   {"title": "Proof", "duration_hint": "15-25s", "description": "Back up your claims with data, examples, or authority"},
   {"title": "CTA", "duration_hint": "25-30s", "description": "Ask viewers to share their experience or follow for more truth"}
 ]'::jsonb),

(0, 'expose', 'Exposé', 'Reveal hidden information or insider secrets that audiences crave.', 
 'Us-vs-them dynamic and forbidden knowledge create high shareability.', 
 '[
   "Nobody talks about how [industry] really works",
   "Here''s what they don''t want you to know about [topic]",
   "The secret that [authority figures] won''t tell you",
   "What happens behind closed doors in [field]"
 ]'::jsonb,
 '[
   {"title": "Hook (secret)", "duration_hint": "0-2s", "description": "Tease the forbidden knowledge you''re about to reveal"},
   {"title": "Setup", "duration_hint": "2-8s", "description": "Establish why this information is hidden or suppressed"},
   {"title": "Reveal 1", "duration_hint": "8-18s", "description": "Share the first layer of insider information"},
   {"title": "Reveal 2", "duration_hint": "18-25s", "description": "Go deeper with more shocking or valuable details"},
   {"title": "CTA", "duration_hint": "25-30s", "description": "Invite viewers to share what secrets they know or follow for more exposés"}
 ]'::jsonb),

(0, 'transformation', 'Transformation', 'Show a before-and-after journey that demonstrates real change.', 
 'People buy outcomes, not processes — transformation videos sell the dream.', 
 '[
   "How I went from [bad state] to [good state] in [timeframe]",
   "Before vs after: my [transformation type] journey",
   "This is what happens when you [change behavior]",
   "From [starting point] to [end point] — here''s how"
 ]'::jsonb,
 '[
   {"title": "Before (pain)", "duration_hint": "0-8s", "description": "Show the starting state, problem, or pain point clearly"},
   {"title": "Process (montage)", "duration_hint": "8-20s", "description": "Quick montage of the work, steps, or journey in between"},
   {"title": "After (result)", "duration_hint": "20-30s", "description": "Reveal the transformation and invite viewers to start their journey"}
 ]'::jsonb),

(0, 'pov', 'POV', 'Create instant identification with a relatable scenario or perspective.', 
 'Instant identification with a scenario drives comments and shares as people relate.', 
 '[
   "POV: You''re trying to [common situation]",
   "When you [relatable scenario]",
   "That moment when [shared experience]",
   "POV: Someone tells you [common advice]"
 ]'::jsonb,
 '[
   {"title": "Setup (scenario)", "duration_hint": "0-5s", "description": "Establish the relatable situation or point of view"},
   {"title": "Reaction", "duration_hint": "5-20s", "description": "Show the realistic reaction or internal monologue"},
   {"title": "Punchline/CTA", "duration_hint": "20-30s", "description": "Deliver the payoff and ask viewers to relate in comments"}
 ]'::jsonb),

(0, 'speed_run', 'Speed Run', 'Deliver valuable information in a fast, satisfying format.', 
 'Satisfying to watch and high save rate because viewers can replay for reference.', 
 '[
   "How to [achieve goal] in under [time limit]",
   "The fastest way to [solve problem]",
   "Speed run: [process] from start to finish",
   "[Number] steps to [outcome] in [timeframe]"
 ]'::jsonb,
 '[
   {"title": "Hook (promise)", "duration_hint": "0-3s", "description": "Promise quick delivery of valuable information"},
   {"title": "Step 1", "duration_hint": "3-10s", "description": "First clear, actionable step"},
   {"title": "Step 2-3 (fast)", "duration_hint": "10-25s", "description": "Rapid-fire delivery of remaining steps"},
   {"title": "Result", "duration_hint": "25-30s", "description": "Show the outcome and encourage saves"}
 ]'::jsonb),

(0, 'challenge', 'Challenge', 'Issue a dare or challenge that encourages participation.', 
 'Community participation and built-in virality as people share their attempts.', 
 '[
   "Try this [challenge] for [duration] and see what happens",
   "I dare you to [action] for [timeframe]",
   "Challenge: [task] without [restriction]",
   "Who else is brave enough to try [challenge]?"
 ]'::jsonb,
 '[
   {"title": "Hook (dare)", "duration_hint": "0-5s", "description": "Issue the challenge with clear parameters"},
   {"title": "Attempt", "duration_hint": "5-20s", "description": "Show yourself or others attempting the challenge"},
   {"title": "Result", "duration_hint": "20-25s", "description": "Reveal what happened during the challenge"},
   {"title": "CTA (join)", "duration_hint": "25-30s", "description": "Invite viewers to try it themselves and share results"}
 ]'::jsonb),

(0, 'show_dont_tell', 'Show Don''t Tell', 'Use pure visual demonstration instead of explanation.', 
 'Visual proof is more powerful than explanation — seeing is believing.', 
 '[
   "Watch this [demonstration]",
   "Look at what happens when [action]",
   "See the difference between [option A] and [option B]",
   "No words needed — just watch"
 ]'::jsonb,
 '[
   {"title": "Hook (tease)", "duration_hint": "0-3s", "description": "Tease what viewers are about to see"},
   {"title": "Demo (visual proof)", "duration_hint": "3-25s", "description": "Show the demonstration without heavy explanation"},
   {"title": "CTA", "duration_hint": "25-30s", "description": "Ask viewers to try it themselves or share what they noticed"}
 ]'::jsonb),

(0, 'direct_to_camera', 'Direct-to-Camera', 'Deliver raw, authentic commentary straight to the audience.', 
 'Raw authenticity connects emotionally and builds personal brand trust.', 
 '[
   "Let me be real with you about [topic]",
   "Here''s my honest take on [situation]",
   "Unpopular opinion: [controversial stance]",
   "I need to rant about [frustration]"
 ]'::jsonb,
 '[
   {"title": "Hook (bold claim)", "duration_hint": "0-5s", "description": "Make a bold statement or opinion that grabs attention"},
   {"title": "Argument", "duration_hint": "5-25s", "description": "Explain your reasoning with passion and authenticity"},
   {"title": "CTA", "duration_hint": "25-30s", "description": "Ask for agreement, disagreement, or personal experiences"}
 ]'::jsonb)
ON CONFLICT (org_id, slug) DO NOTHING;