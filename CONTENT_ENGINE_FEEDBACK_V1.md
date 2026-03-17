# Content Engine Phase 1 — User Feedback & Action Items
## From Eddy's review session (2026-03-16 22:13 EDT)

---

## 🔴 BUGS (Fix Now)

1. **"See Examples" button crashes the page** — likely null reference when competitor data hasn't loaded
2. **"Infuse Competitor Intel" toggle crashes the page** — same class of bug, state management issue
3. **Layout not using full width** — centered narrow container instead of dashboard layout

## 🟡 UX Issues (Fix This Sprint)

4. **Templates vs Viral Formats are redundant** — merge into single view. Format = the "Soul", then user picks Creative Method (AI Avatar / Product-Focused / Stock-Text)
5. **Toggle + Button redundancy** — kill the toggle, use single "✨ Generate Script using Competitor Intel" button. Sidebar populates with reference posts AFTER generation.
6. **Storyboard starts blank** — should auto-populate from format's `scene_structure` JSON when advancing from script step
7. **"See Examples" drawer needs "View Original" link** — opens IG/TikTok/YT post in new tab
8. **Full-width layout** — switch from `max-width: 1200px` centered to `width: 100%` with `padding: 2rem`

## 🟢 Phase 2 Enhancements (Next Sprint)

9. **Digital Copies Lab** — guided upload with Do/Don't photo grid, 20+ photos for training
10. **Action Templates** — "Selling", "Car Talking", "Stream", "Podcast" motion presets for avatars
11. **Horizontal Timeline Storyboard** — top row: script segments, middle: Remotion previews, bottom: AI gen status
12. **Step 2 (Settings) as Asset Mapping** — pick Avatar + Tone of Voice + Branding
13. **"Use This Script Structure" button** in examples drawer → pre-fills script lab

## 🔵 Phase 3 Enhancements (Distribution)

14. **Visibility Score algorithm** — V_h (hash uniqueness) × 0.4 + V_t (temporal stagger) × 0.3 + V_c (caption entropy) × 0.2 + V_a (account health) × 0.1
15. **Distribution Dashboard** — Left 40%: visibility gauge + variation breakdown. Right 60%: 40-account grid with departure times
16. **Anti-ban safety check** — if 10+ accounts posting from same proxy range within 5min, auto-drop visibility score by 30
17. **Launch animation** — accounts transition from Queued (grey) → Uploading (blue) → Active (green) with live links
18. **Cluster-based stagger** — post to 5 accounts, wait 45min, repeat (not linear stagger)

## Key Architecture Decisions from Feedback

- **Format = Soul, Creative Method = Body** — decouple content strategy from visual execution
- **Action Templates table** — `action_templates` with remotion_config + kling_params JSON
- **Scene structure → Storyboard auto-population** — map script lines to format's scene_structure
- **Prompt construction formula** — Digital Copy [name] + Action [style] + Script [text] + Format [description] → AI video prompt
