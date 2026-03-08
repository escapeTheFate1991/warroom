# Competitor Intelligence Fix Guide

## Purpose of this document

This document explains the recent Competitor Intelligence fixes in a way that is useful for both:

- future maintainers who need to understand what changed
- junior developers who want to learn **how to reason about bugs, data flow, and safe validation**

It covers:

1. what was broken
2. why it was broken
3. what we changed in backend and frontend
4. why the changes were implemented this way
5. how we tested and validated the work
6. what engineering lessons to take away

---

## The user-facing problems we were solving

The Competitor Intelligence feature had several related regressions:

- recent competitor content often only appeared after drilling into a competitor
- Top Performing Posts and hashtag cloud were blank or stale
- engagement rate showed `0.0%` or suspiciously tiny/random values
- hooks were not reliably reflecting the actual opening language competitors used
- Generate New was not truly driven by current competitor performance data
- generated scripts did not provide the right metrics, drill-down detail, or save-path compatibility with the rest of the content workflow

These issues were all symptoms of the same broader problem:

> the feature was not consistently using a single, reliable, refreshed source of truth for competitor post data

---

## What the feature should do

The intended product behavior is:

- use **real scraped competitor posts** as the source data
- recalculate useful metrics from those posts instead of trusting stale stored summaries
- show the best current content across the active competitor lineup
- extract hooks from the actual opening lines of winning posts
- generate new script ideas based on what is winning right now
- allow those generated ideas to flow into the existing content pipeline without inventing a second storage format

That means the feature is less like a static report and more like a **cache-backed intelligence system**.

---

## Key design principles behind the fixes

Before looking at the code changes, it helps to understand the principles that guided them.

### 1. Recompute from raw signals when possible

If we already store likes, comments, shares, follower counts, and post timestamps, we should derive:

- engagement score
- engagement rate
- virality score
- ranking order

from those raw values.

Why?

Because precomputed summary fields can become stale when the data model changes, when a sync only partially updates, or when older rows were created with a different formula.

### 2. All related reads should share the same cache/self-heal path

If competitor drill-down can trigger a cache fill, but top-content and hashtag routes cannot, the UI becomes inconsistent:

- one screen shows data
- another screen looks empty
- users think the app is broken

So the fix was to make related reads rely on the same cache-backed logic.

### 3. Frontend and backend contracts must evolve together

If backend starts returning a list of rich script objects but frontend still expects one simple object, the feature breaks even though both sides are “valid” in isolation.

This is why the backend and frontend changes were intentionally completed together.

### 4. Save into the existing workflow instead of inventing a parallel system

Generated scripts are only useful if they can be used elsewhere in the app. Instead of creating a new persistence format, the save action was aligned to the existing `PlatformContent` localStorage contract.

That keeps the system simpler and more predictable.

---

## Backend changes

Primary file:

- `backend/app/api/content_intel.py`

Related backend file touched earlier in the flow:

- `backend/app/api/scraper.py`

### 1. Shared cache/self-healing behavior for competitor content reads

One of the original problems was that a user often had to drill into a competitor before other surfaces started showing data.

That usually means one route is doing extra work that the others are not.

The fix was to ensure these reads use the same cache-backed behavior:

- competitor content
- top videos / top content style reads
- hashtag aggregation reads

This matters because **aggregate views should not depend on a human clicking a detail view first**.

### 2. Engagement rate now comes from actual cached post data and follower counts

The engagement problem was not just a formatting issue. The real issue was that some paths were depending on stale stored values instead of consistently recomputing from current cached signals.

Important helper behavior now includes:

- `_post_engagement_score(post)` recomputes engagement from interaction counts
- `_post_engagement_rate(post)` uses interaction score divided by follower count
- `load_cached_posts(...)` now selects competitor followers via `COALESCE(c.followers, 0) AS followers`

This is important because engagement rate without follower count is usually meaningless.

### 3. Virality-based ranking for Top Content and Hooks

Top Content and Hooks need to reflect what is winning **now**, not what happened to be stored earlier.

To support that, the backend now includes:

- `_post_virality_score(post)`
- `_sorted_posts_for_analysis(posts)`

The sorting blends:

- raw engagement
- engagement rate
- recency

This is a better model than “largest raw like count wins” because a newer post with a stronger response rate is often more interesting than an older post with bigger but less relevant totals.

### 4. Better hook extraction

Hooks should represent the opening language the competitor used to stop the scroll.

The backend now uses:

- `_post_hook(post)`

This helper:

- prefers a stored hook if available
- otherwise falls back to extracting the opening text from the post body

That makes hook extraction more reliable and keeps the UI focused on the actual opening line instead of a generic summary.

### 5. Candidate topic collection from current winners

Script generation should not depend only on a manually typed topic.

The new topic selection path combines:

- requested topic override, if the user provides one
- current trending topics
- derived topic labels from ranked posts

This behavior lives in:

- `_collect_candidate_topics(...)`
- `_derive_topic_label(post)`

This is important because it lets the system stay grounded in live competitor content while still allowing the user to steer the angle when needed.

### 6. Competitor-driven multi-script generation

The old generation flow was too generic. It did not fully use current competitor winners as the basis for new ideas.

The new generation flow now:

- ranks current cached posts
- analyzes trending topics from those posts
- reads business settings for brand alignment
- builds multiple ideas from those ranked source posts
- persists rich metadata with each script
- returns a list of richer script objects to the UI

Important backend helpers and routes involved:

- `build_competitor_script_ideas(...)`
- `generate_script_content(...)`
- `POST /api/content-intel/competitors/{competitor_id}/generate-script`
- `GET /api/content-intel/competitors/scripts`

The new script shape includes fields like:

- `title`
- `hook`
- `body_outline`
- `cta`
- `predicted_views`
- `predicted_engagement`
- `predicted_engagement_rate`
- `virality_score`
- `business_alignment_score`
- `business_alignment_label`
- `business_alignment_reason`
- `source_competitors`
- `similar_videos`
- `scene_map`

This is a much better fit for the product requirement because the UI needs to show both:

- a quick summary card
- a detailed drill-down panel

### 7. Metadata persistence that is backward-tolerant

Generated script details are persisted into `crm.content_scripts`, with richer metadata packed into `scene_map` JSON.

Important helpers:

- `_serialize_script_metadata(...)`
- `_parse_script_metadata(...)`
- `_content_script_to_response(...)`

This is important because it preserves compatibility with existing stored records while still allowing new richer responses.

Junior-dev lesson:

> When evolving a stored format, try to parse older shapes gracefully instead of assuming all historical data already matches the new schema.

### 8. Small but important bug fix: callable shadowing in topic analysis

The parameter in `analyze_trending_topics(...)` was renamed from `cluster_topics` to `enable_clustering`.

Why this matters:

- names should not accidentally shadow other callable concepts or create confusion
- readability matters even when a bug seems small
- “tiny” naming bugs can block bigger features if the wrong branch of logic runs

---

## Frontend changes

Primary file:

- `frontend/src/components/intelligence/CompetitorIntel.tsx`

Supporting files that were checked for compatibility:

- `frontend/src/components/content/PlatformContent.tsx`
- `frontend/src/components/social/SocialDashboard.tsx`

### 1. Frontend types were aligned to the new backend response

The UI used to expect an older, simpler script shape. The backend now returns a richer structure and can return multiple scripts in one request.

The frontend types were updated so the UI correctly understands fields like:

- `hook`
- `body_outline`
- `predicted_views`
- `predicted_engagement_rate`
- `virality_score`
- `business_alignment_*`
- `similar_videos`
- `scene_map`

Why this matters:

Type drift between frontend and backend is one of the most common sources of breakage in full-stack apps.

### 2. Top Content and Hooks now sort using virality first

The frontend now sorts incoming Top Content and Hooks using:

1. `virality_score`
2. `engagement_score`

This keeps the presentation aligned with the backend ranking model and makes the UI reflect current winners more consistently.

### 3. Generate New now supports multi-result, competitor-driven output

The generation modal was updated to:

- require only competitor selection
- make topic optional as an override
- allow generating multiple ideas at once (`3`, `6`, `9`)
- consume an array response from the backend
- select the first generated script automatically

This makes the workflow feel much closer to a real idea-generation tool than a one-off text generator.

### 4. Scripts tab redesigned into card grid + detail panel

The old scripts experience was a simple list. That was not enough for the desired workflow.

The new UI now provides:

- a card grid for quick scanning
- a detail panel for focused reading
- alignment badges
- predicted performance metrics
- scene map display
- similar competitor video references
- source post links

This is important because good UX separates:

- **browse mode** (many options quickly)
- **inspect mode** (one option in depth)

That is exactly why a card grid plus drill-down panel is a good fit here.

### 5. Save-to-platform now matches the existing pipeline contract

Instead of saving a custom object shape, scripts are now stored using the existing content-pipeline format with fields like:

- `id`
- `title`
- `description`
- `stage: "scripted"`
- `platform`
- `createdAt`
- `hook`
- `views`

Storage key format:

- `warroom_content_${platform}`

This was important because:

- other parts of the app already know how to read this contract
- it avoids duplicating pipeline logic
- saved competitor-intel scripts can move naturally into the rest of the workflow

---

## Why these changes were done this way

This is the most important section for a junior developer.

When a feature is broken in multiple places, it is tempting to patch each symptom separately. That usually creates more long-term complexity.

Instead, the better approach is:

### Step 1: find the shared cause

The shared causes here were:

- inconsistent cache behavior
- stale derived metrics
- backend/frontend contract drift
- UI not built for the richer workflow the product actually wanted

### Step 2: fix the source of truth

Instead of hardcoding display behavior, the implementation was centered around the source data:

- scraped competitor posts
- follower counts
- post timestamps
- business settings

### Step 3: make the output reusable

The generated script data was designed so the same object could support:

- the generation response
- the scripts list
- the detail panel
- persistence into stored scripts

### Step 4: validate with the smallest reliable checks

Rather than introducing a new test framework or installing packages, the validation used the tools already available in the repo and container.

This is a good real-world habit.

---

## Tests and validation that were run

### IDE diagnostics

Checked:

- `frontend/src/components/intelligence/CompetitorIntel.tsx`
- `backend/app/api/content_intel.py`
- `scripts/test_content_intel_import.py`

Result:

- no diagnostics

### Backend syntax validation

Command used:

```bash
python3 -m py_compile backend/app/api/content_intel.py
```

Why this matters:

- fast sanity check
- catches syntax errors before spending time on deeper validation

### Frontend production build

Command used:

```bash
cd frontend
npm run build
```

Why this matters:

- confirms the React/TypeScript/Next.js code actually compiles
- catches contract/type issues that diagnostics alone may miss

### Backend rebuild for runtime validation

Command used:

```bash
docker compose build backend && docker compose up -d backend
```

Why this matters:

- ensures the running backend container matches the edited code on disk
- avoids the very common mistake of testing stale container code

### Automated regression script

File:

- `scripts/test_content_intel_import.py`

The script now validates:

- engagement-rate calculation behavior
- hook extraction behavior
- virality-based sorting
- candidate topic dedupe and priority
- metadata serialize/parse round-trip
- competitor-driven script idea generation

Why this style of test was chosen:

- the repo does not currently have a mature pytest setup for this flow
- the user explicitly asked for tests without adding unnecessary dependency churn
- a dependency-light regression script was the safest, fastest way to create repeatable coverage

---

## Important engineering lessons for a junior developer

### Lesson 1: Fix the data path, not just the screen

If one page is blank and another page works, do not immediately assume the broken page needs a UI patch. Often the real bug is that the two pages are not reading from the same backend behavior.

### Lesson 2: Derived fields can lie

If a field like `engagement_score` is stored in the database, treat it carefully. Ask:

- when was it computed?
- with which formula?
- was it recomputed after sync?
- is there enough raw data to compute it live instead?

If raw inputs exist, recomputing is often safer.

### Lesson 3: UX should match the user’s real task

A simple list was not the right interface for evaluating many generated script ideas. The card-grid plus detail panel matches the actual decision-making workflow better.

### Lesson 4: Backward compatibility matters

When storing richer JSON metadata, parse older shapes safely. Real systems almost always contain historical data.

### Lesson 5: Validate in layers

Good validation often looks like this:

1. diagnostics
2. syntax check
3. build/type check
4. runtime validation
5. repeatable regression test

That sequence is fast, safe, and practical.

---

## What was intentionally not done

To stay conservative and avoid unnecessary risk, this work did **not**:

- install new dependencies
- introduce a brand-new test framework
- rewrite unrelated competitor systems
- change the rest of the content pipeline contract

This is important. Good engineering is not about changing the most code. It is about changing the **right** code.

---

## Suggested future follow-ups

If this area needs more hardening later, the next useful steps would be:

1. add route-level API regression tests around the content-intel endpoints
2. add a browser-level smoke test for the scripts tab UX
3. document the virality formula in product terms so PM/design/backend/frontend all use the same definition
4. consider centralizing competitor-intel scoring logic into a dedicated service/helper module if the feature expands further

---

## Final summary

The Competitor Intelligence fixes were successful because they focused on the right abstractions:

- shared cache-backed data flow
- recomputed metrics from real scraped data
- lineup-aware ranking and generation
- backend/frontend contract alignment
- reuse of the existing content-pipeline save contract
- layered validation with low-risk automated coverage

If you are a junior developer, the big lesson is this:

> When a feature feels inconsistent, look for the broken source-of-truth relationship first. Fixing that usually solves multiple symptoms at once.
