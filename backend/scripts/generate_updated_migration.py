#!/usr/bin/env python3
"""Generate the updated content_engine_migration.sql with rich scene structures."""

import json


def generate_scene_structure_json(format_name, scene_data):
    """Generate properly formatted JSON for SQL insertion."""
    return json.dumps(scene_data, separators=(',', ':')).replace("'", "''")


def main():
    """Generate the updated migration SQL."""
    
    # Define rich scene structures for each format
    formats_data = {
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
        ],
        "expose": [
            {
                "title": "Hook (secret)",
                "duration_hint": "0-2s",
                "description": "Tease the forbidden knowledge you're about to reveal",
                "remotion_template": "text_overlay",
                "remotion_props": {
                    "style": "mysterious",
                    "animation": "fade_whisper",
                    "text": "They're lying to you"
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
        ]
    }
    
    # Print the SQL fragments for easy copy-paste
    print("-- Updated scene_structure data for content_engine_migration.sql")
    print("-- Replace the INSERT statements with these:")
    print()
    
    for format_slug, scenes in formats_data.items():
        scene_json = generate_scene_structure_json(format_slug, scenes)
        print(f"-- {format_slug}")
        print(f"'{scene_json}'::jsonb")
        print()


if __name__ == "__main__":
    main()