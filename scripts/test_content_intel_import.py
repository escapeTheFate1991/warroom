#!/usr/bin/env python3
"""Dependency-light regression checks for competitor content-intel helpers."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
if (ROOT / "backend").exists():
    sys.path.insert(0, str(ROOT / "backend"))
elif (ROOT / "app").exists():
    sys.path.insert(0, str(ROOT))
else:
    raise RuntimeError(f"Unable to locate backend package from {ROOT}")

DUMMY_DB_URL = "postgresql+asyncpg://user:pass@127.0.0.1:5432/warroom"
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("POSTGRES_URL", DUMMY_DB_URL)
os.environ.setdefault("LEADGEN_DB_URL", DUMMY_DB_URL)
os.environ.setdefault("CRM_DB_URL", DUMMY_DB_URL)

from app.api.content_intel import (  # noqa: E402
    GeneratedScript,
    SimilarVideoReference,
    _collect_candidate_topics,
    _post_engagement_score,
    _parse_script_metadata,
    _post_engagement_rate,
    _post_hook,
    _post_virality_score,
    _serialize_script_metadata,
    _sorted_posts_for_analysis,
    build_competitor_script_ideas,
)


def make_post(**overrides):
    now = datetime.now(timezone.utc)
    post = {
        "likes": 120,
        "comments": 12,
        "shares": 8,
        "followers": 1000,
        "views": 0,
        "platform": "instagram",
        "handle": "alpha",
        "hook": "",
        "post_text": "Stop posting random content. Use this retention loop to turn viewers into buyers.",
        "post_url": "https://example.com/post/1",
        "posted_at": now - timedelta(days=2),
    }
    post.update(overrides)
    return post


def test_engagement_and_hook_helpers():
    post = make_post()
    expected_rate = _post_engagement_score(post) / 1000
    assert round(_post_engagement_rate(post), 3) == round(expected_rate, 3)
    assert _post_hook(post) == "Stop posting random content"

    stored_hook_post = make_post(hook="Do this before you scale", post_text="Ignored fallback text")
    assert _post_hook(stored_hook_post) == "Do this before you scale"


def test_virality_sorting_prefers_recent_high_rate_posts():
    posts = [
        make_post(post_url="https://example.com/high-rate", followers=900, posted_at=datetime.now(timezone.utc) - timedelta(days=1)),
        make_post(
            post_url="https://example.com/old-large",
            followers=10000,
            likes=140,
            comments=5,
            shares=0,
            posted_at=datetime.now(timezone.utc) - timedelta(days=30),
        ),
    ]

    ranked = _sorted_posts_for_analysis(posts)
    assert ranked[0]["post_url"] == "https://example.com/high-rate"
    assert _post_virality_score(ranked[0]) > _post_virality_score(ranked[1])


def test_candidate_topics_dedupe_and_priority():
    topics = _collect_candidate_topics(
        posts=[
            make_post(post_text="Content repurposing systems help close inbound clients faster."),
            make_post(post_text="Customer proof clips drive more replies from warm leads."),
        ],
        trending_topics=["AI Outreach", "Customer Retention", "AI Outreach"],
        requested_topic="Customer Retention",
        max_topics=3,
    )

    assert topics[0] == "Customer Retention"
    assert topics.count("AI Outreach") == 1
    assert len(topics) == 3


def test_metadata_round_trip_and_legacy_parse():
    script = GeneratedScript(
        platform="instagram",
        title="Hook title",
        hook="Hook title",
        body_outline="Scene body",
        cta="Send us a DM",
        estimated_duration="45-60 seconds",
        predicted_views=18000,
        predicted_engagement=420.0,
        predicted_engagement_rate=4.2,
        virality_score=812.4,
        business_alignment_score=88.0,
        business_alignment_label="High",
        business_alignment_reason="Aligned with retention messaging.",
        source_competitors=["alpha", "beta"],
        similar_videos=[
            SimilarVideoReference(
                competitor_handle="beta",
                platform="instagram",
                source_url="https://example.com/beta",
                hook="Use proof before pitch",
                engagement_score=310.0,
            )
        ],
        scene_map=[{"scene": "Hook", "direction": "Open strong", "goal": "Stop the scroll"}],
    )

    metadata = _parse_script_metadata(_serialize_script_metadata(script))
    assert metadata["estimated_duration"] == "45-60 seconds"
    assert metadata["similar_videos"][0]["competitor_handle"] == "beta"
    assert metadata["scenes"][0]["scene"] == "Hook"

    legacy = _parse_script_metadata(json.dumps([{"scene": "Legacy"}]))
    assert legacy["scenes"][0]["scene"] == "Legacy"


def test_build_competitor_script_ideas_uses_live_post_signals():
    posts = [
        make_post(post_url="https://example.com/post/a", handle="alpha", followers=900),
        make_post(
            post_url="https://example.com/post/b",
            handle="beta",
            likes=180,
            comments=15,
            shares=10,
            followers=1200,
            post_text="Here is the client-acquisition script that keeps getting qualified replies.",
        ),
        make_post(
            post_url="https://example.com/post/c",
            handle="gamma",
            likes=95,
            comments=30,
            shares=12,
            followers=800,
            post_text="The easiest way to make case studies sell for you is to lead with proof.",
        ),
    ]
    business_settings = {
        "business_name": "War Room",
        "business_tagline": "AI-powered growth systems",
        "primary_offer": "content systems",
        "ideal_customer": "founders",
    }

    scripts = build_competitor_script_ideas(
        competitor_handle="alpha",
        platform="tiktok",
        posts=posts,
        business_settings=business_settings,
        count=3,
        requested_topic="Lead Capture",
        hook_style="bold_claim",
        trending_topics=["Lead Capture", "Client Proof"],
    )

    assert len(scripts) == 3
    assert all(script.topic == "Lead Capture" for script in scripts)
    assert all(script.estimated_duration == "30-45 seconds" for script in scripts)
    assert all(script.scene_map for script in scripts)
    assert all(script.similar_videos for script in scripts)
    assert all(script.predicted_views > 0 for script in scripts)
    assert all(script.predicted_engagement_rate > 0 for script in scripts)
    assert all("Delivery note:" in script.body_outline for script in scripts)
    assert all(script.business_alignment_label in {"High", "Medium", "Low"} for script in scripts)
    assert all(script.source_competitors and script.source_competitors[0] == "alpha" for script in scripts)


def main():
    tests = [
        ("engagement and hook helpers", test_engagement_and_hook_helpers),
        ("virality sorting", test_virality_sorting_prefers_recent_high_rate_posts),
        ("candidate topics", test_candidate_topics_dedupe_and_priority),
        ("metadata round trip", test_metadata_round_trip_and_legacy_parse),
        ("competitor-driven script generation", test_build_competitor_script_ideas_uses_live_post_signals),
    ]

    for name, test_fn in tests:
        test_fn()
        print(f"✅ {name}")

    print(f"\n🎉 Passed {len(tests)} content-intel regression checks.")


if __name__ == "__main__":
    main()