# AI Video Editor Integration Plan

## Remotion + Claude Code Video Toolkit → War Room

**Date**: 2026-03-15  
**Status**: MVP Implementation  
**Author**: Friday (AI sub-agent)

---

## 1. Architecture Overview

### Current State
War Room already has a **UGC Video Studio** (`AIStudioPanel.tsx`) that generates videos via Google Veo 3.1 / Seeddance 1.5. It manages:
- Digital copies (AI avatars with uploaded assets)
- Video templates (storyboard-based scene definitions)
- Video projects (from template → generation → output)
- Templatizer (analyze competitor videos → extract reusable templates)
- Motion control (Kling 3.0 character animation)

### New Capability: Programmatic Video Editor (Remotion)
Adding a **Remotion-based video editor** gives War Room the ability to:
1. **Render videos client-side** using React components (no GPU API needed)
2. **Preview in-browser** with `@remotion/player` before committing to render
3. **Template-driven composition** — text overlays, image slideshows, transitions
4. **Server-side rendering** for final export via Remotion CLI / Lambda

### Architecture Diagram
```
┌─────────────────────────────────────────────┐
│  Frontend (Next.js)                         │
│  ┌───────────────────────────────────────┐  │
│  │ AIStudioPanel.tsx                     │  │
│  │  ├── UGC Studio (Veo 3.1) [existing] │  │
│  │  ├── Video Editor (Remotion) [NEW]    │  │
│  │  │    ├── @remotion/player (preview)  │  │
│  │  │    ├── Template compositions       │  │
│  │  │    └── Storyboard ↔ Composition    │  │
│  │  └── Motion Control [existing]        │  │
│  └───────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │ API calls
┌──────────────────▼──────────────────────────┐
│  Backend (FastAPI)                          │
│  ├── ugc_studio.py  [existing]             │
│  ├── video_editor.py [NEW]                 │
│  │    ├── POST /api/video/render           │
│  │    ├── POST /api/video/storyboard       │
│  │    └── GET  /api/video/templates        │
│  └── Remotion CLI (server-side render)     │
└─────────────────────────────────────────────┘
```

## 2. Backend API — New Endpoints

### `video_editor.py` — `/api/video/*`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/video/templates` | List Remotion video templates (product-showcase, social-ad, testimonial) |
| `GET` | `/api/video/templates/{id}` | Get a single template with its composition config |
| `POST` | `/api/video/storyboard` | AI-generate a storyboard from a text prompt (uses existing Gemini integration) |
| `POST` | `/api/video/render` | Queue a server-side Remotion render job |
| `GET` | `/api/video/render/{job_id}/status` | Poll render job status |

All endpoints use:
- `get_org_id(request)` from `app.services.tenant`
- `get_current_user` from `app.api.auth`
- `get_leadgen_db` for DB session (same pattern as UGC Studio)

### Integration with UGC Studio
- Video Editor templates reference UGC digital copies for avatar images
- Storyboard API can accept UGC storyboard format and convert to Remotion composition props
- Rendered videos are saved to same `/data/ugc-videos/` directory

## 3. Claude Code Video Toolkit Integration

### What It Provides
The toolkit (`github.com/digitalsamba/claude-code-video-toolkit`) is a **Remotion-based production framework** with:
- **Templates**: Sprint review, product demo structures
- **Shared components**: `AnimatedBackground`, `SlideTransition`, `Label`, transitions library
- **Brand system**: Colors, fonts, voice settings as JSON profiles
- **Transitions**: `glitch()`, `rgbSplit()`, `zoomBlur()`, `lightLeak()`, `fade()`, `slide()`, etc.

### How We Use It
1. **Borrow the transition library** — import into our Remotion compositions
2. **Adapt the component library** — `AnimatedBackground`, `SlideTransition` as base components
3. **Template structure pattern** — config-driven scenes with `sprint-config.ts` pattern
4. **Brand profile format** — extend War Room's existing branding to include Remotion colors/fonts

### What We DON'T Need
- Their CLI commands (`/video`, `/brand`) — War Room has its own UI
- Their Playwright recording — we have our own automation
- Their ElevenLabs/RunPod integrations — we already have voice sample upload + Veo generation

## 4. Workflow

```
User Flow:
1. User opens AI Studio → Video Editor tab
2. Selects a template (Product Showcase, Social Ad, Testimonial)
3. Customizes: text, images, colors, timing
4. Previews in-browser via @remotion/player
5. (Optional) AI storyboard: enters prompt → AI generates scene config
6. Clicks "Render" → backend runs Remotion CLI → outputs MP4
7. Video appears in My Projects tab (reuses UGC project system)
```

## 5. Tech Stack

### Frontend (already in War Room)
- Next.js 14, React 18, TypeScript
- **NEW**: `remotion`, `@remotion/cli`, `@remotion/player`

### Backend (already in War Room)
- FastAPI, SQLAlchemy (async), PostgreSQL
- **NEW**: Node.js subprocess for `npx remotion render` (server-side)

### External Dependencies
- **ffmpeg** — required by Remotion for video encoding (likely already installed)
- **Node.js 18+** — required for Remotion rendering (already have v22)

## 6. Phase Plan

### Phase 1: MVP (This Implementation) ✅
- Install Remotion packages in frontend
- Create `VideoEditor.tsx` component with `@remotion/player` preview
- 3 starter templates: Product Showcase, Social Media Ad, Testimonial
- Backend API: `/api/video/templates`, `/api/video/storyboard`, `/api/video/render`
- Wire into AI Studio panel as new tab

### Phase 2: AI Storyboarding (Future)
- Deep integration with Claude Code Video Toolkit's scene planning
- AI generates Remotion composition props from natural language
- Auto-select template + fill in content from prompt
- Voice-over script generation linked to scene timing

### Phase 3: Full Editor (Future)
- Timeline-based editor UI (drag scenes, adjust timing)
- Custom transitions between scenes (from toolkit's transition library)
- Asset library integration (drag images/videos into composition)
- Real-time collaboration on video projects
- Lambda rendering for faster output
- Brand system integration (auto-apply org colors/fonts)

## 7. Template Definitions

### Product Showcase
- **Duration**: 15s at 30fps (450 frames)
- **Scenes**: Product image (slide in) → Feature text overlay → CTA slide
- **Props**: `images[]`, `headline`, `features[]`, `ctaText`, `brandColor`

### Social Media Ad
- **Duration**: 12s at 30fps (360 frames)
- **Scenes**: Hook text (bold) → Body copy with background → CTA with button
- **Props**: `hookText`, `bodyText`, `ctaText`, `backgroundImage`, `brandColor`

### Testimonial
- **Duration**: 20s at 30fps (600 frames)
- **Scenes**: Quote text → Avatar + name → Brand logo + tagline
- **Props**: `quote`, `authorName`, `authorTitle`, `avatarUrl`, `brandLogo`, `brandColor`

## 8. Database Schema

Reuses existing `ugc_video_projects` table with additional fields:

```sql
ALTER TABLE public.ugc_video_projects
  ADD COLUMN IF NOT EXISTS composition_type TEXT DEFAULT 'veo',
  ADD COLUMN IF NOT EXISTS composition_props JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS render_progress FLOAT DEFAULT 0;
```

- `composition_type`: `'veo'` (existing) | `'remotion'` (new)
- `composition_props`: JSON props passed to Remotion composition
- `render_progress`: 0.0 to 1.0 for rendering progress tracking
