# War Room Content Machine — Master Plan v4
## From Isolated Tools → Content Manufacturing Plant with Predictive Intelligence

_Last updated: 2026-03-16 22:55 EDT_

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 PHASE 6: PREDICTIVE SANDBOX                  │
│  Mirofish Swarm Intelligence Engine                          │
│  ↓ 1,000 AI agents with audience psychographics              │
│  ↓ "Social Friction Test" before spending a single dollar    │
│  ↓ Scene-level drop-off prediction + optimization            │
├─────────────────────────────────────────────────────────────┤
│                    INTELLIGENCE LAYER                         │
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
│  ↓ feed reality back into Mirofish collective memory         │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Format Templates + Hook Lab + Competitor-Powered Script Gen ✅ COMPLETE

### 1A. Viral Formats as First-Class Templates ✅
- 8 formats seeded with rich scene structures (Remotion templates, AI actions, camera hints)
- Format classifier running on 530+ posts (189 classified, 341 unclassified)
- video_formats table with CRUD API

### 1B. The Hook Lab ✅
- 3-part script editor (Hook / Body / CTA)
- Hook Score classifier (1-10, pattern matching against competitor data)
- "Generate Script using Competitor Intel" button (no more toggle)
- Comment-driven topic injection from audience demand signals
- Competitor sidebar shows reference posts AFTER generation

### 1C. Templatizer → Create Bridge ✅
- Format badges on all Competitor Intel video cards
- "Generate Variant" button passes format + hook + topic to AI Studio
- "Use This Script Structure" in examples drawer

### UX Overhaul ✅
- Templates + Formats merged into single view
- Creative Method selector (AI Avatar / Product-Focused / Stock-Text)
- Full-width layout
- View Original links on example posts
- Storyboard auto-populates from format scene_structure

---

## Phase 2: Remotion-First Video Assembly + Audio Pipeline 🔄 IN PROGRESS

### The Strategy: Skeleton + Soul
- **Remotion** = the skeleton. Text overlays, animations, diagrams, split-screens, captions, CTAs, transitions.
- **Veo 3.1 / Nano Banana** = the soul. Used surgically for 1-2 key scenes only.
- **ElevenLabs / Google Lyria 3** = the voice. Cloned voice with format-matched delivery.
- **ffmpeg / Video Editor skill** = the stitcher.

### 8 New Remotion Templates (building now)
| Template | What | Use Case |
|----------|------|----------|
| `TextOverlay` | Bold text with animation (typewriter, slide, fade, slam) | Hook slides, key points, stamps (❌ FALSE) |
| `Diagram` | Animated charts/flowcharts/lists/comparisons | @raycfu-style explainer content |
| `SplitScreen` | Before/after comparison (vertical, horizontal, wipe) | Transformation format |
| `ImageSequence` | Ken Burns effect on stills | B-roll, screenshots |
| `CaptionTrack` | Auto-captions synced to voiceover | Accessibility + engagement |
| `CTASlide` | Call to action with animated button | Closers |
| `BRoll` | Stock footage/images with overlay text | Filler, transitions |
| `CodeWalkthrough` | Animated code blocks with highlights | Tech/dev content |

### Backend: compose-from-scenes (building now)
- Takes mixed scene types (remotion, ai_generated, image, stock)
- Calculates cost estimates (remotion = free, AI = $0.05/scene)
- Creates video_projects with status tracking
- Storyboard UI shows scene type selector, template picker, cost badges

### Audio Pipeline (next)
- ElevenLabs voice cloning from Eddy's voice samples
- Format-matched delivery presets (Myth Buster = aggressive, POV = conversational)
- Auto-sync with CaptionTrack template

### Render Scaling
- Phase 2: local Remotion renders (fine for 1-5 videos/day)
- Phase 3: Remotion Lambda or headless Chrome cluster on Brain 3

---

## Phase 3: Smart Multi-Account Distribution + Anti-Detection

### Sub-Account Randomizer
- Background color shift (±5% hue), font rotation, music pitch shift
- Caption positioning variation, intro/outro frame variation
- Each render produces unique file hash

### Distribution Controls
- Account grid (main + sub-accounts)
- Stagger slider (2h / 6h / 12h / 24h / 3d)
- Cluster-based: post to 5 accounts, wait 45min, repeat
- Auto caption variations per account
- Platform adaptation (hashtags for IG, clean for X, description for YT)

### Anti-Burst Detection
- Staggered posting prevents same-IP burst
- Future: residential proxy rotation per sub-account

---

## Phase 4: Performance Feedback Loop

### Performance Tracking
- 48hr metrics collection via social sync
- content_performance_feedback table (already created)
- Performance delta: YOUR score vs competitor inspiration avg
- Tiers: outperform (>+20%) / match (±20%) / underperform (<-20%)

### Feedback Weight Formula
```
Day 1:   competitor_weight = 1.0, your_weight = 0.0
Day 30:  competitor_weight = 0.7, your_weight = 0.3
Day 90:  competitor_weight = 0.4, your_weight = 0.6
Day 180: competitor_weight = 0.2, your_weight = 0.8
```

### Performance Dashboard
- Format Leaderboard, Hook Leaderboard, Time Heatmap, Format Trends
- "Seed for Next Batch" button on winning videos
- Audience Demand Feed from YOUR comments

---

## Phase 5: Emerging Format Detection

### Format Classifier + Anomaly Detection
- Classify new posts on each sync
- Cluster unclassified high-engagement posts
- Trigger: 3+ posts from 3+ different competitors, top 20% engagement, similar structure
- Auto-generate name + description + draft format entry
- Surface as ✨ Emerging badge on Competitor Intel cards

---

## Phase 6: Mirofish Predictive Sandbox — "Reality Rehearsal Lab"

### The Concept
Before spending a single dollar on AI generation or posting to any account, run the content through a **swarm intelligence simulation**. 1,000 AI agents with the exact psychological profiles of your target audience predict engagement, identify drop-off points, and recommend optimizations.

**This is "Zero-Waste Content Creation."** Simulate 100 versions in 60 seconds, only generate the one that Mirofish predicts will explode.

### Architecture Position
Mirofish sits between Intelligence Layer and Creation Layer:
```
Competitor Intel (What worked for THEM)
    ↓
Mirofish Simulation (Will it work for YOU?)
    ↓ [Prediction: "Change hook from 'Exposé' to 'Myth Buster' → Share rate +15%"]
AI Studio (Generate the optimized version)
    ↓
Post-publish analytics feed back into Mirofish collective memory
```

### 6A. Swarm Persona System

**Backend: `swarm_personas` table**
```sql
CREATE TABLE IF NOT EXISTS crm.swarm_personas (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    name TEXT NOT NULL,                    -- "Skeptical Early Adopter"
    archetype TEXT NOT NULL,               -- archetype label
    demographics JSONB DEFAULT '{}',       -- age_range, roles, tech_stack
    psychographics JSONB DEFAULT '{}',     -- core_desires, friction_points, content_bias
    behavioral_logic JSONB DEFAULT '{}',   -- interaction_triggers, comment_style
    collective_memory JSONB DEFAULT '[]',  -- recent viral exposure, brand perception
    source_competitors TEXT[],             -- which competitors' audiences this models
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Auto-generated from competitor data:**
- Analyze comments_data across all competitor posts
- Extract recurring themes, vocabulary, sentiment patterns
- Cluster into 3-5 audience archetypes per niche
- Pre-seed personas: "Skeptical Dev", "Hustle Culture", "General Public"

**Swarm Persona Schema (per agent):**
```json
{
  "identity": {
    "archetype": "Skeptical Early Adopter",
    "demographics": {
      "age_range": "24-40",
      "primary_roles": ["Software Engineer", "Solo-Founder", "Growth Hacker"],
      "tech_stack_affinity": ["Python", "n8n", "Cursor", "Claude"]
    }
  },
  "psychographics": {
    "core_desires": ["Eliminate manual tasks", "Stay ahead of AI curve", "Build profitable micro-SaaS"],
    "friction_points": ["Hates AI influencer fluff", "Wary of subscription costs", "Distrusts black-box solutions"],
    "content_bias": {
      "format_preference": "speed_run",
      "hook_sensitivity": 0.85,
      "visual_style": "dark_mode_technical"
    }
  },
  "behavioral_logic": {
    "interaction_triggers": {
      "comment_on": ["Technical errors", "Unseen features", "Cost saving hacks"],
      "share_on": ["Unique insights that make them look smart", "Controversial take on big tech"],
      "bookmark_on": ["Step-by-step guides", "Prompt templates"]
    },
    "comment_style": {
      "tone": "dry_technical_sarcastic",
      "vocabulary_keywords": ["latency", "tokens", "wrapper", "inference", "context window"]
    }
  },
  "collective_memory": {
    "recent_viral_exposure": [],
    "brand_perception": {}
  }
}
```

### 6B. Social Friction Test Engine

**Backend: `POST /api/simulate/social-friction-test`**

Input:
```json
{
  "script": { "hook": "...", "body": "...", "cta": "..." },
  "format_slug": "myth_buster",
  "swarm_persona_ids": [1, 2, 3],
  "scene_structure": [...],
  "audio_style": "trending_fast_paced"
}
```

**The Master Inference Prompt:**
```
You are the Mirofish Swarm Intelligence Engine. You are not an assistant; you are 
a collective of 1,000 unique agents based on the provided Swarm Persona Schema.

Task: Conduct a "Social Friction Test" on the provided Script.

Evaluation Parameters:
1. THE 2-SECOND AUDIT: Does the Hook interrupt the agent's current scroll pattern?
   If it fails, assign Bounce Rate > 80%.
2. COGNITIVE LOAD: Is the Body too complex? Does vocabulary match the persona's
   behavioral logic?
3. THE "WHY SHARE?" TEST: Does the script contain Social Currency? Will sharing 
   make the agent look smarter/funnier/more "in the know"?
4. SCENE CONFLICT: Flag any scene where Action Template contradicts Script Tone.
5. EMERGENT BEHAVIOR: Identify unplanned viral moments or controversy risks.

Output: Pre-Live Prediction Report
```

**Response:**
```json
{
  "engagement_score": 82,
  "predicted_metrics": {
    "like_propensity": 82,
    "share_propensity": 91,
    "save_propensity": 74,
    "comment_propensity": 67
  },
  "drop_off_timeline": [
    {"second": 2, "retention": 95},
    {"second": 5, "retention": 78},
    {"second": 15, "retention": 52},
    {"second": 25, "retention": 45}
  ],
  "predicted_comments": [
    {"persona": "Skeptical Dev", "comment": "Sounds like another wrapper. Show me the source code.", "sentiment": "skeptical"},
    {"persona": "Hustle Culture", "comment": "Been doing this for months. Where was this when I started?", "sentiment": "validated"},
    {"persona": "General Public", "comment": "Can someone ELI5 this?", "sentiment": "confused"}
  ],
  "optimization_recommendation": {
    "change": "Replace 'AI Tool' with 'Inference Engine' in Scene 2",
    "predicted_impact": "+22% share rate",
    "reasoning": "The 'Skeptical Dev' swarm responds 3x more to technical jargon than marketing language"
  },
  "scene_friction_map": [
    {"scene": 1, "friction": "low", "note": "Strong hook, matches format expectations"},
    {"scene": 2, "friction": "high", "note": "Transition too slow — 60% drop-off predicted at 0:04"},
    {"scene": 3, "friction": "medium", "note": "CTA is generic — customize for platform"}
  ],
  "audio_recommendation": {
    "best_match": "trending_fast_paced",
    "reason": "Triggered 'Save' behavior in 40% more agents vs lo-fi or cinematic"
  }
}
```

### 6C. Scene-Level Optimization

**Storyboard Heatmap Overlay:**
- After simulation, each scene in the storyboard gets a friction indicator
- 🟢 Low friction (keep as-is)
- 🟡 Medium friction (consider adjustments)
- 🔴 High friction (predicted drop-off point)
- One-click "Magic Edit" suggestions per scene

**A/B Testing in Simulation:**
- "God View" toggle: run same script as Myth Buster vs Exposé format
- Side-by-side prediction comparison
- Pick the winner before generating

### 6D. "Talk to the Audience" — Deep Interaction Lab

**`POST /api/simulate/persona-chat`**

Spawn a chat session with a simulated persona who just "watched" your video:
```json
{
  "persona_id": 1,
  "script": {...},
  "user_message": "Why did you keep scrolling past the hook?"
}
```

Response:
```json
{
  "persona_name": "Skeptical Early Adopter",
  "response": "You said 'n8n' in the first 2 seconds, but I'm looking for 'Claude' solutions. It felt irrelevant immediately.",
  "behavioral_trigger": "friction_points.hates_ai_fluff",
  "suggested_fix": "Lead with the solution outcome, not the tool name"
}
```

### 6E. Collective Memory Feedback

After posts go live and collect real metrics (Phase 4):
1. Feed actual comments and engagement back into Mirofish
2. Update `collective_memory` on matching personas
3. Next simulation includes brand perception: "your_studio: high technical credibility"
4. The swarm literally learns your audience over time

### 6F. UI Integration

**"Simulate" Button** — appears in Step 3 (Hook Lab) next to "Generate with Competitor Intel"
- Runs social friction test
- Shows "Vibe Check" gauge (Red/Yellow/Green)
- Comment preview: "3 Agents are already typing..."
- Predicted engagement score with breakdown
- One-click "Magic Edit" optimization

**Prediction Report Overlay** — transparent layer on Step 4 (Storyboard)
- Drop-off heatmap per scene
- Friction indicators on each scene card
- Audio recommendation badge

**Persona Selector Sidebar** — choose which swarm to simulate against
- Pre-built swarms from competitor data
- Custom swarm creation from manual persona entry

### Implementation Priority
| Priority | What | Backend | Frontend | Dependency |
|----------|------|---------|----------|-----------|
| First | Swarm persona table + auto-gen from comments | New table + extraction logic | Persona selector UI | Phase 1 (comment data) |
| Second | Social friction test endpoint | AI inference endpoint | Simulate button + report overlay | Swarm personas |
| Third | Scene-level optimization | Friction scoring per scene | Storyboard heatmap overlay | Simulation engine |
| Fourth | Persona chat | Chat endpoint with persona context | Chat modal in Hook Lab | Swarm personas |
| Fifth | Collective memory feedback | Post-publish → persona update | None (background) | Phase 4 (analytics) |

---

## Implementation Roadmap (Updated)

### ✅ Week 1: Phase 1 (COMPLETE)
- Hook Lab, Format Templates, Competitor-powered script gen
- Format badges, Generate Variant button
- UX overhaul, full-width, auto-populate storyboard

### 🔄 Week 2: Phase 2 (IN PROGRESS)
- 8 Remotion templates
- compose-from-scenes endpoint + video_projects table
- Storyboard scene type selector UI
- Audio pipeline (ElevenLabs integration)

### Week 3: Phase 3 — Distribution
- Smart-distribute endpoint with randomizer
- Account grid + stagger controls
- Caption variation generation
- Cluster-based posting

### Week 4: Phase 4 + 5 — Feedback + Detection
- content_performance_feedback collection
- Feedback weight calculation
- Emerging format anomaly detection
- Performance dashboard

### Week 5-6: Phase 6 — Mirofish Predictive Sandbox
- Swarm persona generation from competitor comments
- Social friction test engine
- Pre-Live Prediction Report UI
- Scene-level optimization heatmap
- Persona chat lab
- Collective memory feedback loop
