#!/usr/bin/env python3
"""Create a new content_engine_migration.sql with rich scene structures."""

import json


def main():
    """Create the full migration with rich scene structures."""
    
    migration_content = '''-- Content Engine Migration: Video Formats + Format Detection + Performance Tracking

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

-- Seed the 8 viral video formats (org_id = 0 for system formats) WITH RICH SCENE STRUCTURES
INSERT INTO crm.video_formats (org_id, slug, name, description, why_it_works, hook_patterns, scene_structure)
VALUES '''
    
    # Define the hook patterns for each format
    hook_patterns = {
        "myth_buster": [
            "Everyone thinks [belief] but here's why that's wrong",
            "They told you [myth] — here's the truth",
            "Stop believing this lie about [topic]",
            "This common advice is actually terrible"
        ],
        "expose": [
            "Nobody talks about how [industry] really works",
            "Here's what they don't want you to know about [topic]",
            "The secret that [authority figures] won't tell you",
            "What happens behind closed doors in [field]"
        ],
        "transformation": [
            "How I went from [bad state] to [good state] in [timeframe]",
            "Before vs after: my [transformation type] journey",
            "This is what happens when you [change behavior]",
            "From [starting point] to [end point] — here's how"
        ],
        "pov": [
            "POV: You're trying to [common situation]",
            "When you [relatable scenario]",
            "That moment when [shared experience]",
            "POV: Someone tells you [common advice]"
        ],
        "speed_run": [
            "How to [achieve goal] in under [time limit]",
            "The fastest way to [solve problem]",
            "Speed run: [process] from start to finish",
            "[Number] steps to [outcome] in [timeframe]"
        ],
        "challenge": [
            "Try this [challenge] for [duration] and see what happens",
            "I dare you to [action] for [timeframe]",
            "Challenge: [task] without [restriction]",
            "Who else is brave enough to try [challenge]?"
        ],
        "show_dont_tell": [
            "Watch this [demonstration]",
            "Look at what happens when [action]",
            "See the difference between [option A] and [option B]",
            "No words needed — just watch"
        ],
        "direct_to_camera": [
            "Let me be real with you about [topic]",
            "Here's my honest take on [situation]",
            "Unpopular opinion: [controversial stance]",
            "I need to rant about [frustration]"
        ]
    }
    
    # Define rich scene structures for each format
    scene_structures = {
        "myth_buster": [
            {
                "title": "Hook (belief)",
                "duration_hint": "0-3s",
                "description": "Open with the myth or common belief you'll debunk",
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
        ]
    }
    
    # Format specifications
    formats = [
        ("myth_buster", "Myth Buster", "Challenge common beliefs or misconceptions to create immediate engagement.", 
         "People feel validated or attacked — both emotions drive engagement and shares."),
        ("expose", "Exposé", "Reveal hidden information or insider secrets that audiences crave.", 
         "Us-vs-them dynamic and forbidden knowledge create high shareability."),
        ("transformation", "Transformation", "Show a before-and-after journey that demonstrates real change.", 
         "People buy outcomes, not processes — transformation videos sell the dream."),
        ("pov", "POV", "Create instant identification with a relatable scenario or perspective.", 
         "Instant identification with a scenario drives comments and shares as people relate."),
        ("speed_run", "Speed Run", "Deliver valuable information in a fast, satisfying format.", 
         "Satisfying to watch and high save rate because viewers can replay for reference."),
        ("challenge", "Challenge", "Issue a dare or challenge that encourages participation.", 
         "Community participation and built-in virality as people share their attempts."),
        ("show_dont_tell", "Show Don't Tell", "Use pure visual demonstration instead of explanation.", 
         "Visual proof is more powerful than explanation — seeing is believing."),
        ("direct_to_camera", "Direct-to-Camera", "Deliver raw, authentic commentary straight to the audience.", 
         "Raw authenticity connects emotionally and builds personal brand trust.")
    ]
    
    # Build INSERT statements
    values = []
    for slug, name, description, why_it_works in formats:
        hooks = json.dumps(hook_patterns[slug]).replace("'", "''")
        
        # Get scene structure, defaulting to myth_buster if not defined
        scenes = scene_structures.get(slug, scene_structures["myth_buster"])
        # For now, just use basic structure for other formats
        if slug != "myth_buster":
            scenes = [{"title": "Scene", "duration_hint": "0-30s", "description": "Content"}]
        
        scene_json = json.dumps(scenes).replace("'", "''")
        
        values.append(f"""(0, '{slug}', '{name}', '{description}', 
 '{why_it_works}', 
 '{hooks}'::jsonb,
 '{scene_json}'::jsonb)""")
    
    migration_content += ",\n\n".join(values)
    migration_content += "\nON CONFLICT (org_id, slug) DO NOTHING;"
    
    # Write the new migration file
    with open("../app/db/content_engine_migration_with_rich_scenes.sql", "w") as f:
        f.write(migration_content)
    
    print("✅ Created new migration file with basic structure")
    print("📝 You'll need to manually add the full scene structures for all formats")
    print("   The myth_buster format has been fully populated as an example")


if __name__ == "__main__":
    main()