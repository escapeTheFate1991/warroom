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

-- Seed the 8 viral video formats with RICH SCENE STRUCTURES (org_id = 0 for system formats)
INSERT INTO crm.video_formats (org_id, slug, name, description, why_it_works, hook_patterns, scene_structure)
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
   {
     "title": "Hook (belief)",
     "duration_hint": "0-3s",
     "description": "Open with the myth or common belief you''ll debunk",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "bold_center",
       "animation": "typewriter",
       "text_source": "hook"
     },
     "ai_action": "surprised_direct",
     "ai_action_description": "Avatar looks directly at camera with surprised expression",
     "graphic_overlay": "❌ FALSE stamp overlay, bold red",
     "camera_hint": "close-up, direct eye contact"
   },
   {
     "title": "Counter-evidence",
     "duration_hint": "3-15s",
     "description": "Present your contrarian evidence or perspective",
     "remotion_template": "diagram",
     "remotion_props": {
       "style": "animated_list",
       "animation": "slide_in",
       "data_source": "counter_points"
     },
     "ai_action": "explaining_side",
     "ai_action_description": "Avatar explaining with hand gestures, side-view angle",
     "graphic_overlay": "Animated truth list with checkmarks",
     "camera_hint": "medium shot, professional angle"
   },
   {
     "title": "Proof",
     "duration_hint": "15-25s",
     "description": "Back up your claims with data, examples, or authority",
     "remotion_template": "image_sequence",
     "remotion_props": {
       "style": "split_screen",
       "animation": "ken_burns",
       "data_source": "evidence"
     },
     "ai_action": "confident_presenting",
     "ai_action_description": "Avatar presenting data with authority, direct gaze",
     "graphic_overlay": "Data charts and authority quotes overlay",
     "camera_hint": "split-screen with evidence display"
   },
   {
     "title": "CTA",
     "duration_hint": "25-30s",
     "description": "Ask viewers to share their experience or follow for more truth",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "pulsing_button",
       "animation": "bounce",
       "text": "Follow for more"
     },
     "ai_action": "pointing_direct",
     "ai_action_description": "Avatar pointing at viewer with confident expression",
     "graphic_overlay": "Follow for more pulse animation button",
     "camera_hint": "close-up, direct engagement"
   }
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
   {
     "title": "Hook (secret)",
     "duration_hint": "0-2s",
     "description": "Tease the forbidden knowledge you''re about to reveal",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "mysterious",
       "animation": "fade_whisper",
       "text": "They''re lying to you"
     },
     "ai_action": "shushing_secretive",
     "ai_action_description": "Avatar with finger to lips, secretive expression",
     "graphic_overlay": "Darkened background with whisper text",
     "camera_hint": "intimate close-up, conspiratorial"
   },
   {
     "title": "Setup",
     "duration_hint": "2-5s",
     "description": "Establish why this information is hidden or suppressed",
     "remotion_template": "b_roll",
     "remotion_props": {
       "style": "blurred_docs",
       "animation": "blur_reveal",
       "overlay": "leaked_stamp"
     },
     "ai_action": "handheld_leaked",
     "ai_action_description": "Avatar in handheld style, leaked document vibe",
     "graphic_overlay": "Blurred background documents with LEAKED stamp",
     "camera_hint": "handheld, documentary style"
   },
   {
     "title": "Reveal 1",
     "duration_hint": "5-12s",
     "description": "Share the first layer of insider information",
     "remotion_template": "diagram",
     "remotion_props": {
       "style": "bullet_reveal",
       "animation": "pop_in",
       "data_source": "secrets"
     },
     "ai_action": "revealing_excited",
     "ai_action_description": "Avatar revealing secrets with animated expressions",
     "graphic_overlay": "Animated bullet points with reveal effects",
     "camera_hint": "medium shot, engaging"
   },
   {
     "title": "Reveal 2",
     "duration_hint": "12-22s",
     "description": "Go deeper with more shocking or valuable details",
     "remotion_template": "image_sequence",
     "remotion_props": {
       "style": "comparison_split",
       "animation": "slide_compare",
       "data_source": "evidence"
     },
     "ai_action": "deep_dive_serious",
     "ai_action_description": "Avatar in serious mode, deep investigation vibe",
     "graphic_overlay": "Split-screen comparison with evidence overlay",
     "camera_hint": "split-screen with evidence display"
   },
   {
     "title": "CTA",
     "duration_hint": "22-25s",
     "description": "Invite viewers to share what secrets they know or follow for more exposés",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "bio_link",
       "animation": "urgent_pulse",
       "text": "Check bio for full doc"
     },
     "ai_action": "direct_stare",
     "ai_action_description": "Avatar with intense direct stare, serious tone",
     "graphic_overlay": "Check bio for full document link",
     "camera_hint": "intense close-up, direct eye contact"
   }
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
   {
     "title": "Before (pain)",
     "duration_hint": "0-5s",
     "description": "Show the starting state, problem, or pain point clearly",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "before_label",
       "animation": "fade_in",
       "filter": "black_white"
     },
     "ai_action": "looking_down_sad",
     "ai_action_description": "Avatar looking down with sad expression, defeated posture",
     "graphic_overlay": "BEFORE label with black/white filter",
     "camera_hint": "slightly downward angle, melancholic"
   },
   {
     "title": "Process (montage)",
     "duration_hint": "5-20s",
     "description": "Quick montage of the work, steps, or journey in between",
     "remotion_template": "split_screen",
     "remotion_props": {
       "style": "before_after_montage",
       "animation": "quick_cuts",
       "transition": "snap_happy"
     },
     "ai_action": "transformation_montage",
     "ai_action_description": "Avatar transitioning from sad to happy in quick cuts",
     "graphic_overlay": "Montage transition effects, progress indicators",
     "camera_hint": "dynamic angles, energy building"
   },
   {
     "title": "After (result)",
     "duration_hint": "20-30s",
     "description": "Reveal the transformation and invite viewers to start their journey",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "after_reveal",
       "animation": "celebration",
       "filter": "full_color"
     },
     "ai_action": "thumbs_up_happy",
     "ai_action_description": "Avatar with thumbs up, bright happy expression",
     "graphic_overlay": "AFTER label, Get this result button",
     "camera_hint": "upward angle, triumphant lighting"
   }
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
   {
     "title": "Setup (scenario)",
     "duration_hint": "0-5s",
     "description": "Establish the relatable situation or point of view",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "pov_bubble",
       "animation": "bubble_pop",
       "position": "top_center"
     },
     "ai_action": "selfie_natural",
     "ai_action_description": "Avatar in natural selfie style, relatable expression",
     "graphic_overlay": "POV: text bubble at top center",
     "camera_hint": "selfie angle, natural lighting"
   },
   {
     "title": "Reaction",
     "duration_hint": "5-20s",
     "description": "Show the realistic reaction or internal monologue",
     "remotion_template": "b_roll",
     "remotion_props": {
       "style": "emoji_float",
       "animation": "floating_reactions",
       "overlay": "relatable_emojis"
     },
     "ai_action": "walking_dynamic",
     "ai_action_description": "Avatar walking or in dynamic movement, expressive",
     "graphic_overlay": "Relatable emoji floating around avatar",
     "camera_hint": "following shot, dynamic movement"
   },
   {
     "title": "Punchline/CTA",
     "duration_hint": "20-30s",
     "description": "Deliver the payoff and ask viewers to relate in comments",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "tag_friend",
       "animation": "wave_gesture",
       "text": "Tag a friend"
     },
     "ai_action": "waving_friendly",
     "ai_action_description": "Avatar waving at camera with friendly expression",
     "graphic_overlay": "Tag a friend overlay with wave animation",
     "camera_hint": "friendly medium shot, welcoming"
   }
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
   {
     "title": "Hook (promise)",
     "duration_hint": "0-3s",
     "description": "Promise quick delivery of valuable information",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "timer_graphic",
       "animation": "countdown",
       "text": "X in 60 seconds"
     },
     "ai_action": "fast_talking_excited",
     "ai_action_description": "Avatar fast-talking with excited, energetic expression",
     "graphic_overlay": "Timer graphic showing 60 seconds countdown",
     "camera_hint": "high energy, tight frame"
   },
   {
     "title": "Step 1",
     "duration_hint": "3-10s",
     "description": "First clear, actionable step",
     "remotion_template": "diagram",
     "remotion_props": {
       "style": "step_highlight",
       "animation": "rapid_reveal",
       "overlay": "screen_clips"
     },
     "ai_action": "voiceover_only",
     "ai_action_description": "Voiceover narration over screen recording",
     "graphic_overlay": "Step 1 highlight with rapid screen clips",
     "camera_hint": "screen recording focus, minimal face"
   },
   {
     "title": "Steps 2-3 (fast)",
     "duration_hint": "10-22s",
     "description": "Rapid-fire delivery of remaining steps",
     "remotion_template": "image_sequence",
     "remotion_props": {
       "style": "rapid_sequence",
       "animation": "quick_cuts",
       "duration_per_clip": "0.5s"
     },
     "ai_action": "rapid_demonstration",
     "ai_action_description": "Fast-paced demonstration with quick cuts",
     "graphic_overlay": "Rapid 0.5s screen clips with step indicators",
     "camera_hint": "fast cuts, high pace editing"
   },
   {
     "title": "Result",
     "duration_hint": "22-30s",
     "description": "Show the outcome and encourage saves",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "download_link",
       "animation": "final_reveal",
       "text": "Download template"
     },
     "ai_action": "smiling_satisfied",
     "ai_action_description": "Avatar smiling with satisfied expression, job done",
     "graphic_overlay": "Download template link, save button",
     "camera_hint": "satisfied close-up, achievement feel"
   }
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
   {
     "title": "Hook (dare)",
     "duration_hint": "0-3s",
     "description": "Issue the challenge with clear parameters",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "challenge_text",
       "animation": "bold_appear",
       "text": "Can you do this?"
     },
     "ai_action": "pointing_at_viewer",
     "ai_action_description": "Avatar pointing directly at viewer with challenge expression",
     "graphic_overlay": "Can you do this? bold challenge text",
     "camera_hint": "direct pointing gesture, challenging gaze"
   },
   {
     "title": "Attempt",
     "duration_hint": "3-15s",
     "description": "Show yourself or others attempting the challenge",
     "remotion_template": "split_screen",
     "remotion_props": {
       "style": "me_vs_you",
       "animation": "side_comparison",
       "layout": "vertical_split"
     },
     "ai_action": "demonstrating_focused",
     "ai_action_description": "Avatar demonstrating the challenge with focused concentration",
     "graphic_overlay": "Me vs. You split-screen comparison",
     "camera_hint": "split-screen demonstration view"
   },
   {
     "title": "Result",
     "duration_hint": "15-22s",
     "description": "Reveal what happened during the challenge",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "achievement_reveal",
       "animation": "celebration",
       "overlay": "achievement_badges"
     },
     "ai_action": "celebrating_victory",
     "ai_action_description": "Avatar celebrating with victory expression",
     "graphic_overlay": "Achievement animation with success indicators",
     "camera_hint": "celebration shot, triumphant"
   },
   {
     "title": "CTA (join)",
     "duration_hint": "22-30s",
     "description": "Invite viewers to try it themselves and share results",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "stitch_icon",
       "animation": "challenge_invite",
       "text": "Stitch this"
     },
     "ai_action": "challenging_expression",
     "ai_action_description": "Avatar with challenging expression, daring viewers",
     "graphic_overlay": "Stitch this icon with challenge invitation",
     "camera_hint": "confident challenge pose"
   }
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
   {
     "title": "Hook (tease)",
     "duration_hint": "0-3s",
     "description": "Tease what viewers are about to see",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "minimal_tease",
       "animation": "subtle_fade",
       "text": "Watch this"
     },
     "ai_action": "side_profile_watching",
     "ai_action_description": "Avatar in side profile, watching something off-camera",
     "graphic_overlay": "Minimal text tease, understated",
     "camera_hint": "side profile, mysterious watching"
   },
   {
     "title": "Demo (visual proof)",
     "duration_hint": "3-22s",
     "description": "Show the demonstration without heavy explanation",
     "remotion_template": "image_sequence",
     "remotion_props": {
       "style": "product_demo",
       "animation": "highlight_circles",
       "overlay": "floating_highlights"
     },
     "ai_action": "minimal_presence",
     "ai_action_description": "Avatar with minimal presence, letting demo speak",
     "graphic_overlay": "Large product/UI demo with floating highlight circles",
     "camera_hint": "demo-focused, avatar secondary"
   },
   {
     "title": "CTA",
     "duration_hint": "22-30s",
     "description": "Ask viewers to try it themselves or share what they noticed",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "shop_tag",
       "animation": "product_link",
       "text": "Shop the drop"
     },
     "ai_action": "direct_smile",
     "ai_action_description": "Avatar with direct smile, approachable expression",
     "graphic_overlay": "Shop the drop tag overlay",
     "camera_hint": "warm direct smile, inviting"
   }
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
   {
     "title": "Hook (bold claim)",
     "duration_hint": "0-3s",
     "description": "Make a bold statement or opinion that grabs attention",
     "remotion_template": "text_overlay",
     "remotion_props": {
       "style": "lower_third",
       "animation": "professional_fade",
       "text": "name/title"
     },
     "ai_action": "podcast_professional",
     "ai_action_description": "Avatar in podcast/professional speaking mode",
     "graphic_overlay": "Subtle name/title lower-third",
     "camera_hint": "professional speaking angle, confident"
   },
   {
     "title": "Argument",
     "duration_hint": "3-22s",
     "description": "Explain your reasoning with passion and authenticity",
     "remotion_template": "diagram",
     "remotion_props": {
       "style": "bullet_points",
       "animation": "point_by_point",
       "overlay": "key_takeaways"
     },
     "ai_action": "deep_explanation",
     "ai_action_description": "Avatar in deep explanation mode, passionate delivery",
     "graphic_overlay": "Key takeaway bullet points appearing",
     "camera_hint": "engaged speaking, authentic passion"
   },
   {
     "title": "CTA",
     "duration_hint": "22-30s",
     "description": "Ask for agreement, disagreement, or personal experiences",
     "remotion_template": "cta",
     "remotion_props": {
       "style": "follow_part2",
       "animation": "nodding_close",
       "text": "Follow for Part 2"
     },
     "ai_action": "nodding_closing",
     "ai_action_description": "Avatar nodding with closing expression, wrapping up",
     "graphic_overlay": "Follow for Part 2 text overlay",
     "camera_hint": "closing shot, nodding agreement"
   }
 ]'::jsonb)
ON CONFLICT (org_id, slug) DO NOTHING;