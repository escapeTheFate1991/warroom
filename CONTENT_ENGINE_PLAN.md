# War Room Content Machine — Master Plan v3
## From Isolated Tools → Content Manufacturing Plant

_Last updated: 2026-03-16_

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE LAYER                        │
│  Competitor Intel (29 competitors, 530+ posts)               │
│  ↓ viral pattern detection + format classification           │
│  ↓ comment analysis → audience demand signals                │
│  ↓ emerging format anomaly detection                         │
├─────────────────────────────────────────────────────────────┤
│                    CREATION LAYER                             │
│  Hook Lab (trained classifier, competitor-powered gen)        │
│  ↓ 3-part script: Hook / Body / CTA                         │
│  ↓ AI voiceover (ElevenLabs/Lyria 3 voice clones)           │
│  ↓ Remotion assembly (skeleton) + Veo/Nano (soul scenes)    │
├─────────────────────────────────────────────────────────────┤
│                    DISTRIBUTION LAYER                        │
│  Sub-Account Randomizer (unique file hashes per account)     │
│  ↓ staggered posting across main + 15-40 sub-accounts       │
│  ↓ platform-adapted captions + metadata                     │
│  ↓ residential proxy rotation (anti-burst detection)         │
├─────────────────────────────────────────────────────────────┤
│                    OPTIMIZATION LAYER                        │
│  48hr performance collection via social sync                 │
│  ↓ YOUR results vs competitor benchmark delta                │
│  ↓ format/hook leaderboards + time heatmaps                 │
│  ↓ retrain script gen weights → back to top                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Format Templates + Hook Lab + Competitor-Powered Script Gen

### 1A. Viral Formats as First-Class Templates

**Current:** Generic templates ("Product Showcase", "Testimonial", "Social Media Ad")
**New:** Logan Forsyth viral archetypes as the template system

**Backend: `video_formats` table**
```sql
CREATE TABLE IF NOT EXISTS crm.video_formats (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    slug TEXT NOT NULL,               -- 'myth_buster', 'expose', 'transformation'
    name TEXT NOT NULL,               -- 'Myth Buster'
    description TEXT,                 -- 'Flip a common belief on its head'
    why_it_works TEXT,                -- 'People feel validated or attacked — both engage'
    hook_patterns JSONB DEFAULT '[]', -- proven hook structures for this format
    scene_structure JSONB DEFAULT '[]', -- default storyboard template (scene count, timing, camera)
    avg_engagement_score FLOAT,       -- calculated from competitor data
    post_count INT DEFAULT 0,         -- how many competitor posts match this format
    is_system BOOLEAN DEFAULT TRUE,   -- system vs user-created
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Seed with the 8 core formats + default storyboard structures:

| Format | Scenes | Default Structure |
|--------|--------|-------------------|
| Myth Buster | 4 | Hook (belief) → Counter-evidence → Proof → CTA |
| Exposé | 5 | Hook (secret) → Setup → Reveal 1 → Reveal 2 → CTA |
| Transformation | 3 | Before (pain) → Process (montage) → After (result) |
| POV | 3 | Setup (scenario) → Reaction → Punchline/CTA |
| Speed Run | 4 | Hook (promise) → Step 1 → Step 2-3 (fast) → Result |
| Challenge | 4 | Hook (dare) → Attempt → Result → CTA (join) |
| Show Don't Tell | 3 | Hook (tease) → Demo (visual proof) → CTA |
| Direct-to-Camera | 3 | Hook (bold claim) → Argument → CTA |

**Competitor Format Detection:**
- Add `detected_format TEXT` column to `competitor_posts`
- On sync/analysis, classify each post into one of the 8 formats (or "unknown/emerging")
- Classification logic (rules-based first, upgradeable to ML later):
  - Content contains "myth"/"everyone thinks"/"they told you" → Myth Buster
  - "nobody talks about"/"secret"/"they don't want you to know" → Exposé
  - Before/after language, transformation imagery → Transformation
  - "POV:"/"when you"/"that moment when" → POV
  - Step-by-step, numbered lists, tutorial language → Speed Run
  - "Try this"/"challenge"/"for 7 days" → Challenge
  - Minimal text, heavy visual demo → Show Don't Tell
  - Direct address, opinion, hot take → Direct-to-Camera
- Fallback: "unclassified" — tracked for emerging format detection (Phase 5)

**Frontend — Step 1: Template Picker Redesign**
- Replace current template grid with **8 format cards** (+ any user-created)
- Each card shows:
  - Format name + Lucide icon (no emoji)
  - "Why it works" tooltip on hover (info icon)
  - `{post_count} competitor posts · {avg_engagement_score} avg engagement`
  - **"See Viral Examples"** link → opens side drawer showing top 3-5 competitor posts using this format (from `competitor_posts WHERE detected_format = :slug ORDER BY engagement_score DESC`)
  - Thumbnail from the top-performing post for that format
- Selection auto-loads the format's default storyboard into the wizard (Step 4)

---

### 1B. The Hook Lab (Competitor-Powered Script Generation)

**This is the single highest-impact feature. Build it first.**

**Backend: Enhance `POST /api/ai-studio/ugc/generate-script`**
Add `use_competitor_intel: bool` flag. When true:
1. Pull top 30 competitor posts ranked by engagement_score
2. Filter to posts matching the selected format (if format selected)
3. Extract: hooks, caption patterns, content_analysis JSONB, comment themes from comments_data
4. **Comment-driven topic injection** (new): scan `comments_data` across top posts for recurring questions/pain points. If commenters are asking "Does this work with GPT-4?", auto-inject a "Myth Buster" scene addressing GPT-4 vs Claude. This achieves Market-Message Fit — the audience is literally telling you what to make.
5. Feed ALL as context to Gemini alongside user's format/hook/topic
6. Return: script (3-part) + `why_this_works` + `source_competitors` + `audience_demand_signals` (from comments)

**Backend: Hook Score Classifier**
Train a lightweight scoring model on the 530+ competitor posts:
- Input: hook text
- Features: word patterns, length, engagement-to-follower ratio of posts with similar hooks
- Output: score 1-10 based on predicted scroll-stopping potential
- **Implementation:** Not a neural net — a weighted scoring function:
  ```python
  def score_hook(hook_text: str, competitor_posts: list) -> float:
      score = 5.0  # baseline
      # Pattern matching against high-engagement hooks
      high_eng_hooks = [p.hook for p in posts if p.engagement_score > median]
      similarity = avg_ngram_overlap(hook_text, high_eng_hooks)
      score += similarity * 3  # up to +3 for pattern match
      # Length penalty (too short = vague, too long = scroll past)
      if 5 <= word_count(hook_text) <= 15: score += 1
      # Power words ("secret", "nobody", "just", "free")
      power_word_count = count_power_words(hook_text)
      score += min(power_word_count * 0.5, 1.5)
      # Format-specific boost
      if matches_format_hook_pattern(hook_text, selected_format): score += 1
      return min(max(score, 1), 10)
  ```
- Upgradeable: once you have 100+ of YOUR posts with engagement data, retrain on your own audience

**Frontend — Step 3: Script → "Hook Lab"**
- Split textarea into **3 distinct sections**: Hook (0-2s), Body (3-25s), CTA (last 3s)
- Each section is its own bordered textarea with timing label and character count
- **"✨ Infuse Competitor Intel" toggle** (prominent, above the sections)
  - When ON: sidebar slides in → "Winning Hooks Found"
  - Shows 5 high-performing hooks from competitor data for the selected format
  - Each hook shows: `@handle · {likes} likes · {format}` + "Apply" button
  - "Apply" drops the hook structure (adapted, not verbatim) into Hook section
  - Below hooks: **"Audience Demand Signals"** — top 3 recurring questions/topics from competitor comments
    - Each signal has a "Write About This" button → injects into Body section
- **Hook Score meter** — circular gauge (1-10) next to Hook textarea
  - Updates in real-time as you type
  - Color: red (1-3), yellow (4-6), green (7-10)
  - Tooltip explains the score: "Strong pattern match with @bennettx.ai's 50K-like hook"
- **"Browse Hooks" library** pulls from BOTH static library AND competitor data (merged, deduplicated)

---

### 1C. Templatizer → Create Bridge

**Frontend — Templatizer tab**
- On each competitor video card, add **"Generate Variant"** button alongside "Templatize"
- "Generate Variant" action:
  1. Auto-detects the format of the competitor video (from `detected_format` column)
  2. Jumps to Create Video wizard with:
     - Step 1: format pre-selected
     - Step 3: hook structure pre-filled (adapted for your brand, not copied verbatim)
     - Competitor context toggle auto-ON
     - Body section pre-filled with topic spin from the original
  3. User refines and generates

---

## Phase 2: Remotion-First Video Assembly + Audio Pipeline

### The Strategy: Skeleton + Soul
- **Remotion** = the skeleton. Text overlays, animations, diagrams, split-screens, captions, CTAs, transitions. Renders locally, instant, full control.
- **Veo 3.1 / Nano Banana** = the soul. Used surgically for 1-2 key scenes: talking head, product shots, b-roll that needs AI generation. NOT the full video.
- **ElevenLabs / Google Lyria 3** = the voice. Cloned voice with high inflection, matched to format energy. A "Myth Buster" needs aggressive, confident delivery. A "Show Don't Tell" needs calm narration. Standard TTS sounds robotic — voice clones are non-negotiable.
- **ffmpeg / Video Editor skill** = the stitcher. Trims, syncs audio, format-converts, exports.

### Audio Pipeline (NEW — critical for short-form)
```json
{
  "voiceover": {
    "provider": "elevenlabs",          // or "lyria3"
    "voice_id": "eddy_clone_v1",       // cloned from Eddy's voice samples
    "style": "confident_fast",         // format-matched delivery style
    "sections": [
      {"text": "Nobody is talking about this...", "emotion": "urgent", "pace": "fast"},
      {"text": "Here's what actually happens.", "emotion": "calm", "pace": "normal"},
      {"text": "Link in bio for the full guide.", "emotion": "friendly", "pace": "slow"}
    ]
  }
}
```
- Voice clone created once from 3-5 minutes of Eddy's voice samples
- Each script section maps to an emotion/pace preset
- Auto-synced with Remotion CaptionTrack template for captions
- Format presets: Myth Buster = aggressive + fast, POV = conversational, Exposé = dramatic pauses

### Backend: `POST /api/video/compose-from-scenes`
Takes a storyboard with mixed scene types:
```json
{
  "scenes": [
    {"type": "remotion", "template": "text_overlay", "props": {"text": "Wait...", "style": "bold_center", "animation": "typewriter"}},
    {"type": "veo", "prompt": "Person looking at phone, surprised expression, modern office"},
    {"type": "remotion", "template": "diagram", "props": {"data": [...], "animation": "slide_in"}},
    {"type": "image", "url": "/assets/screenshot.png", "animation": "ken_burns"},
    {"type": "remotion", "template": "cta", "props": {"text": "Link in bio", "style": "pulse"}}
  ],
  "audio": {
    "voiceover": "...",   // URL to generated voiceover
    "music": "...",       // background music track
    "music_volume": 0.15  // ducked under voiceover
  }
}
```

### Remotion Templates Needed
| Template | What | Use Case |
|----------|------|----------|
| `TextOverlay` | Bold text with animation (slide, fade, typewriter) | Hook slides, key points |
| `Diagram` | Animated charts/flowcharts | @raycfu-style explainer content |
| `SplitScreen` | Before/after comparison | Transformation format |
| `ImageSequence` | Ken Burns effect on stills | B-roll, screenshots |
| `CaptionTrack` | Auto-captions synced to voiceover | Accessibility + engagement |
| `CTASlide` | Call to action with animated button | Closers |
| `BRoll` | Stock footage/images with overlay text | Filler, transitions |
| `CodeWalkthrough` | Animated code blocks with highlights | Tech/dev content |

### Render Scaling Concern
At 40 sub-accounts × 3 videos/day = **120 renders/day**. Local rendering won't cut it at scale.

**Phase 2 approach (local):** Remotion renders on the War Room server. Fine for 1-5 videos/day.
**Phase 3 upgrade (cloud):** When scaling past 10 videos/day:
- Option A: Remotion Lambda (AWS) — serverless, pay-per-render (~$0.01/render)
- Option B: Headless Chrome cluster on Brain 3 (self-hosted, 4 concurrent renders)
- Option C: Remotion Cloud (their hosted service, simplest)
- Decision deferred until we hit the scaling threshold

### Frontend — Storyboard Step Enhancement
- Each scene in the storyboard gets a **type selector**: Remotion / AI Generated / Image / Stock
- Remotion scenes show a live preview thumbnail (rendered via Remotion Player)
- AI Generated scenes show estimated cost + generation time
- Audio section below scenes: voiceover preview, music selector, volume slider
- User controls the mix — mostly Remotion with AI only where needed

---

## Phase 3: Smart Multi-Account Distribution + Anti-Detection

### The Sub-Account Shield

The Logan Forsyth strategy lives or dies by the algorithm's "Duplicate Content" filter. Posting identical content across 40 accounts gets flagged. The Sub-Account Randomizer solves this.

**Backend: Sub-Account Randomizer**
When `auto_variations: true`, for each sub-account version:
1. **Caption variation** — Gemini generates unique caption per account (different wording, same message)
2. **Metadata uniqueness** — different hashtag sets, different first comment text
3. **Remotion render variation** — slight tweaks to make the file hash unique:
   - Background color shift (±5% hue)
   - Font style rotation (3-4 font variants per template)
   - Music pitch shift (±2-3% — imperceptible but different hash)
   - Intro/outro frame variation (different gradient, different text animation)
   - Caption positioning shift (top vs bottom vs alternating)
4. **File hash guarantee** — each render produces a unique file hash, bypassing "low-effort" shadowbans

**Frontend — "Sub-Account Randomizer" toggle**
- In Step 5, under the account grid
- Toggle ON: "Each sub-account gets a unique render variant"
- Shows preview: "Main: bold_white font, blue gradient · Sub-1: sans-serif, teal gradient · Sub-2: mono, purple gradient"
- Advanced settings (collapsible): adjust randomization intensity (subtle/medium/aggressive)

### Distribution Controls

**Frontend — Step 5: "Generate & Distribute"**

```
Main Accounts:    [✓ IG] [✓ TK] [  YT] [  X]
Sub-Accounts:     [✓ @clips] [✓ @reels] [  @bestof] [+ Add]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Sub-Account Randomizer    [ON ●]
   Variation: [Subtle ▾]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Auto Caption Variations   [ON ●]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱  Stagger: [2h ▾] [6h] [12h] [24h] [3d]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Preview:
  @main     → Mon 6:00pm (IG + TK)
  @clips    → Mon 8:00pm (IG)
  @reels    → Mon 10:00pm (IG)
```

### Backend: `POST /api/scheduler/smart-distribute`
```json
{
  "video_project_id": 42,
  "caption": "...",
  "accounts": [
    {"id": 1, "type": "main", "platforms": ["instagram", "tiktok"]},
    {"id": 5, "type": "sub", "platforms": ["instagram"]},
    {"id": 6, "type": "sub", "platforms": ["instagram"]}
  ],
  "stagger_hours": 2,
  "auto_variations": true,
  "randomizer": {
    "enabled": true,
    "intensity": "subtle"
  },
  "platform_adapt": true
}
```

### Anti-Burst Detection
- Staggered posting prevents platforms from seeing a burst of similar content from the same IP range
- **Future (when scaling):** residential proxy rotation per sub-account
  - Each sub-account posts from a different IP
  - Proxy pool managed in settings, rotated per post
  - Not needed now (1-5 accounts), critical at 20+ accounts

---

## Phase 4: Performance Feedback Loop

### Backend: Performance Tracking

**New table: `content_performance_feedback`**
```sql
CREATE TABLE IF NOT EXISTS crm.content_performance_feedback (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    video_project_id INT REFERENCES crm.video_projects(id),
    scheduled_post_id INT,
    competitor_inspiration_ids INT[],     -- which competitor posts inspired this
    format_slug TEXT,                      -- which format was used
    hook_text TEXT,                        -- the hook that was used
    hook_score FLOAT,                     -- the predicted score at creation time
    -- Performance metrics (collected 48hr post-publish)
    likes INT, comments INT, shares INT, saves INT, reach INT, views INT,
    engagement_score FLOAT,
    -- Benchmark comparison
    competitor_avg_engagement FLOAT,      -- avg engagement of inspiration posts
    performance_delta FLOAT,              -- YOUR score - competitor avg (positive = outperform)
    performance_tier TEXT,                 -- 'outperform' / 'match' / 'underperform'
    -- Learning signals
    audience_feedback JSONB,              -- extracted themes from YOUR comments
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**48hr collection cycle:**
1. Post goes live → social sync picks up metrics at next sync interval
2. After 48hrs, snapshot the metrics into `content_performance_feedback`
3. Calculate `performance_delta` = your engagement_score - avg of competitor inspiration posts
4. Classify: outperform (>+20%), match (±20%), underperform (<-20%)

### The Feedback Mechanism
Script generation now weighs TWO data sources:

```
Final Weight = (competitor_weight × competitor_score) + (your_weight × your_score)

Day 1:   competitor_weight = 1.0, your_weight = 0.0  (no data yet)
Day 30:  competitor_weight = 0.7, your_weight = 0.3  (some posts)
Day 90:  competitor_weight = 0.4, your_weight = 0.6  (enough data)
Day 180: competitor_weight = 0.2, your_weight = 0.8  (YOUR data dominates)
```

- If "Myth Buster" outperforms for you: boosted in format suggestions
- If "POV" underperforms despite competitor success: deprioritized for your account
- Hook patterns that work for YOU get higher scores in the Hook Score classifier
- Comment themes from YOUR audience influence topic injection (not just competitor comments)

### Frontend — "My Projects" → Performance Dashboard
- Each project card shows **Performance vs. Benchmark** badge:
  - 🟢 `+120% vs competitor avg` (green border glow)
  - 🟡 `On par` (neutral)
  - 🔴 `-40% below avg` (red border)
- **"Seed for Next Batch"** button on 🟢 videos → feeds that video's format/hook/topic back as YOUR proven data
- **Insight View toggle** — switch from list to analytics:
  - **Format Leaderboard**: horizontal bar chart — which of the 8 formats performs best for YOUR accounts
  - **Hook Leaderboard**: your top 10 hooks ranked by engagement
  - **Time Heatmap**: 7×24 grid showing when your posts get the most engagement
  - **Format Trends**: line chart over time — are Myth Busters declining? Exposés rising?
  - **Audience Demand Feed**: what YOUR commenters are asking for (aggregated from comment analysis)

---

## Phase 5: Emerging Format Detection

### The Signal
Your competitor data isn't static. New viral formats emerge constantly. The system should detect them before you do.

### Backend: Format Classifier + Anomaly Detection
On each competitor sync:
1. Classify each new post into known formats using rules from Phase 1A
2. Track `unclassified` posts with engagement scores
3. Cluster unclassified posts by structural similarity (ngram overlap on hooks + content_analysis patterns)
4. **Trigger condition:** 3+ unclassified posts from 3+ different competitors, all in top 20% engagement, sharing similar structure
5. When triggered:
   - Auto-generate a name + description from the shared patterns
   - Create a draft `video_format` entry with `is_system = FALSE`
   - Notify user: "🔥 New Format Detected: '{name}' — seen across @handle1, @handle2, @handle3"

### Frontend: Competitor Intel Cards
- Every video card in Top Content gets a **format badge** (small pill):
  - Known: `Myth Buster` (blue), `Exposé` (purple), `Speed Run` (green), etc.
  - Unknown: `Unclassified` (gray)
  - Emerging: `✨ Emerging` (gold glow + pulse animation)
- Clicking an `✨ Emerging` badge shows:
  - The pattern details (what these posts have in common)
  - Example posts from different competitors
  - "Add to My Formats" button → creates a new format template with auto-generated storyboard

---

## Implementation Roadmap

### Week 1: The Hook Lab (Phase 1B) — HIGHEST IMPACT
- [ ] Backend: `detected_format` column + format classifier on competitor_posts
- [ ] Backend: Hook Score classifier function
- [ ] Backend: Enhance generate-script with competitor intel + comment-driven topics
- [ ] Frontend: Hook Lab UI (3-part script, competitor sidebar, hook score meter)
- [ ] Frontend: "Audience Demand Signals" from competitor comments

### Week 2: Format Templates + Templatizer Bridge (Phase 1A + 1C)
- [ ] Backend: video_formats table + seed 8 formats with storyboards
- [ ] Backend: Format detection runs on existing 530 posts (backfill)
- [ ] Frontend: Template picker redesign with viral examples drawer
- [ ] Frontend: "Generate Variant" button on Templatizer cards

### Week 3: Remotion Assembly + Audio (Phase 2)
- [ ] Backend: compose-from-scenes endpoint
- [ ] Backend: Audio pipeline integration (ElevenLabs API)
- [ ] Frontend: Scene type selector in storyboard
- [ ] Frontend: Audio section (voiceover, music, volume)
- [ ] Remotion: Build 8 core templates (TextOverlay, Diagram, SplitScreen, etc.)

### Week 4: Distribution + Anti-Detection (Phase 3)
- [ ] Backend: smart-distribute endpoint with randomizer
- [ ] Backend: Caption variation generation
- [ ] Frontend: Account grid + Sub-Account Randomizer toggle + stagger controls
- [ ] Frontend: Distribution preview

### Week 5-6: Feedback Loop + Emerging Formats (Phase 4 + 5)
- [ ] Backend: content_performance_feedback table + 48hr collection
- [ ] Backend: Feedback weight calculation for script gen
- [ ] Backend: Emerging format anomaly detection
- [ ] Frontend: Performance Dashboard (leaderboards, heatmaps, trends)
- [ ] Frontend: Format badges on Competitor Intel cards

---

## Files Affected

### Backend (new)
- `app/api/video_formats.py` — CRUD for viral format templates
- `app/api/performance_feedback.py` — feedback collection + scoring
- `app/db/content_engine_migration.sql` — all new tables + columns

### Backend (modified)
- `app/api/ugc_studio.py` — enhance generate-script, add compose-from-scenes
- `app/api/content_intel.py` — format classifier, format detection on sync, emerging detection
- `app/api/content_scheduler.py` — smart-distribute, randomizer
- `app/main.py` — migration runner for new tables

### Frontend (modified)
- `AIStudioPanel.tsx` — template picker, Hook Lab, scene type selector, account grid
- `CompetitorIntel.tsx` — format badges, emerging format detection
- `SchedulerCalendar.tsx` — multi-account selection

### Frontend (new)
- `components/ai-studio/HookLab.tsx` — 3-part script editor with competitor sidebar
- `components/ai-studio/FormatPicker.tsx` — viral format template grid with examples drawer
- `components/ai-studio/DistributionPanel.tsx` — account grid, randomizer, stagger controls
- `components/ai-studio/PerformanceDashboard.tsx` — leaderboards, heatmaps, trends
- `components/ai-studio/remotion/` — 8 Remotion template components

### Skills
- `skills/viral-content-engine/SKILL.md` — already created, reference for format definitions
- `skills/video-io/` — ffmpeg post-processing, stitching

### External Integrations
- **ElevenLabs API** — voice cloning + text-to-speech with emotion presets
- **Google Lyria 3** — alternative voice provider (Gemini ecosystem)
- **Remotion Lambda** — cloud rendering at scale (deferred until 10+ videos/day)
