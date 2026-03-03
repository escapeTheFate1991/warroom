# War Room UI Rebuild — Build Specification

## Tech Stack
- Frontend: Next.js 14 + TypeScript + Tailwind CSS
- Backend: FastAPI (Python) at localhost:8300
- Theme: Dark (bg: #0a0a0f, surface: #12131a, border: #1e2030, accent: #6366f1/indigo)
- All components use "use client" directive
- Icons: lucide-react

## Project Structure
- Frontend: `frontend/src/components/` — one folder per feature
- Backend: `backend/app/api/` — FastAPI routers
- Backend: `backend/app/models/` — SQLAlchemy models

## EXISTING Backend APIs (DO NOT MODIFY BACKEND)
- `GET /api/social/accounts` — returns SocialAccount[]
- `GET /api/social/analytics?platform=X` — returns SocialSummary
- `GET /api/social/oauth/{platform}/authorize` — starts OAuth flow
- `DELETE /api/social/accounts/{id}` — disconnect
- Team dashboard: `http://10.0.0.11:18795/agents` — agent status
- Team dashboard: `http://10.0.0.11:18795/events` — agent events

## Build Items (in order)

### 1. Social Performance Dashboard (rewrite `frontend/src/components/social/SocialDashboard.tsx`)

Inspired by CTRL dashboard. Replace current basic layout with:

**Top summary row (4 cards):**
- Total Followers (all platforms combined) — blue accent
- Engagement Rate (average across platforms) — green accent
- Total Impressions — purple accent  
- Accounts Connected (count) — orange accent
- Each card: value, label, trend arrow (↑/↓ with percentage if data available)

**Platform cards (horizontal row, one per connected account):**
- Each card shows: platform icon + name, LIVE badge (green pulse dot), username
- Follower count, engagement rate, post count
- Mini sparkline chart (7 data points, last 7 days — use SVG polyline)
- Top performing post this week (title/preview if available)
- "View Details" link

**Unconnected platforms:** Show as dimmed cards with "Connect" button that triggers OAuth

**Connect flow:** Keep existing OAuth flow (openConnectModal function)

**Recent Published Content section:**
- Grid of recent posts across all platforms
- Each post: platform icon, thumbnail placeholder, caption preview, engagement metrics (likes, comments, shares)
- "View All" link

**Style guidelines:**
- Use rounded-2xl for cards
- Subtle gradient borders (border-opacity tricks)
- Glow effects on hover (shadow with accent color)
- Platform-specific colors for accents: Instagram #E4405F, Facebook #1877F2, YouTube #FF0000, X #000, TikTok #00F2EA, Threads #888

### 2. Agent Service Map (NEW: `frontend/src/components/agents/AgentServiceMap.tsx`)

Datadog-style service trace map for agent communication.

**Canvas area (SVG-based):**
- Central node: "FRIDAY" (primary, larger, accent glow)
- Surrounding nodes: Copy, Design, Dev, Docs, Support, Inbox
- Each node: circle with agent emoji/icon, name label, status color ring
  - Green ring = running, Gray = idle, Red = error, Blue pulse = active communication
- Connection lines between nodes showing delegation flow
  - Friday → Copy, Friday → Design, Friday → Dev, Friday → Docs, Friday → Support, Friday → Inbox
  - Lines use SVG path with slight curves (quadratic bezier)
  - Active connections: animated dashed stroke (CSS animation)
  - Idle connections: subtle gray

**Agent data (hardcoded defaults, will be live later):**
```
AGENTS = [
  { id: "friday", name: "Friday", emoji: "🖤", role: "Orchestrator", model: "claude-opus-4-6", x: 50, y: 50 },
  { id: "copy", name: "Copy", emoji: "📝", role: "Copywriter", model: "claude-sonnet", x: 20, y: 20 },
  { id: "design", name: "Design", emoji: "🎨", role: "UI/UX Designer", model: "claude-sonnet", x: 80, y: 20 },
  { id: "dev", name: "Dev", emoji: "💻", role: "Full-Stack Developer", model: "claude-sonnet", x: 80, y: 80 },
  { id: "docs", name: "Docs", emoji: "📚", role: "Documentation", model: "claude-haiku", x: 20, y: 80 },
  { id: "support", name: "Support", emoji: "📞", role: "Call Center", model: "claude-haiku", x: 15, y: 50 },
  { id: "inbox", name: "Inbox", emoji: "📧", role: "Email Reader", model: "claude-haiku", x: 85, y: 50 },
]
```

**Click on node → Slide-out drawer from right:**
- Agent name + emoji + role
- Model: badge showing model name
- Status: running/idle/error with colored badge
- Current Task: description + progress bar (if running)
- Task Queue: list of pending tasks
- Pipeline: "After this → [next agent name]" 
- Recent Completions: last 5 tasks with timestamp + duration
- Token Usage: input/output tokens, estimated cost
- Close button (X) top right

**Data source:** 
- Try to fetch from `http://10.0.0.11:18795/agents` and `http://10.0.0.11:18795/events`
- If API unavailable, show hardcoded defaults with "Demo Mode" badge
- Poll every 30 seconds for live data

**Style:**
- Dark background matching theme
- Nodes have subtle glow on hover
- Selected node has bright accent ring
- Connection lines animate when agents communicate
- Use CSS keyframe animation for the pulse effect on active nodes

### 3. Content Pipeline (NEW: `frontend/src/components/content/ContentPipeline.tsx`)

Kanban board specifically for content lifecycle.

**Columns:** Idea → Script → Filming → Editing → Scheduled → Posted

**Cards in each column:**
- Content title/hook
- Platform tags (Instagram, TikTok, etc.) as colored pills
- Assigned agent badge (if any)
- Due date (if set)
- Drag handle indicator (visual only for now, drag-drop can be added later)
- Status dot matching column

**Add card button** at top of "Idea" column — opens inline form:
- Title, platform select (multi), notes textarea
- Save creates card in Idea column

**Data:** Store in localStorage for now (no backend needed initially)

**Style:** Same dark theme, horizontal scroll if needed, cards are compact

### 4. Competitor Intelligence (NEW: `frontend/src/components/intelligence/CompetitorIntel.tsx`)

**Competitor Profiles section:**
- Cards for tracked competitors
- Each card: avatar placeholder, handle, platform, follower count, posting frequency, top angles (bullet list)
- "Add Competitor" button → modal with handle + platform input

**Trending Topics section:**
- List of trending topics in niche (hardcoded seed data for now)
- Each topic: title, heat score (1-5 flame emojis), source platform

**Hook Formulas section:**
- Numbered list of proven hook templates
- Each formula: name, template with [fill-in] placeholders, "Use This" button
- Seed with 6 formulas:
  1. The Comparison — "My [person] did [X] in [time]. AI did it in [Y]."
  2. The Bold Claim — "[Category] is dead. Here's what replaced it."
  3. The Identity Challenge — "If you're still doing [task] manually, you're losing."
  4. The Confession — "I was wrong about [thing]. Here's what actually works."
  5. The Results — "I tried [thing] for [time]. Here are the real numbers."
  6. The Prediction — "In 12 months, [prediction]. Here's why."

**Data:** localStorage for competitor profiles, hardcoded for topics/formulas

### 5. Quick Capture + Activity Feed

**Quick Capture (add to Social Dashboard as floating element):**
- Text input: "Drop an idea, topic, or rough hook here..."
- Platform toggle: TikTok / Instagram / Both / All
- "Capture" button → saves to Content Pipeline as new Idea card

**Activity Feed (NEW: `frontend/src/components/agents/ActivityFeed.tsx`):**
- Vertical timeline of agent actions
- Each entry: timestamp, agent emoji + name, action description
- Auto-scroll to latest
- Fetch from team dashboard events API (`http://10.0.0.11:18795/events`)
- If API unavailable, show demo entries
- Max 50 entries visible, auto-prune old ones

## Navigation Changes (update `frontend/src/app/page.tsx`)

Reorganize sidebar to match this structure:

**COMMAND**
- Dashboard (new overview page — can be placeholder)
- Chat (existing)
- Agents (Agent Service Map) ← NEW

**CONTENT**  
- Social Media (Social Performance Dashboard — existing, redesigned)
- Content Pipeline ← NEW
- Intelligence (Competitor Intel) ← NEW

**OPERATIONS**
- Lead Gen (existing)
- CRM Deals (existing)
- CRM Contacts (existing)

**SETTINGS**
- Settings (existing)

Remove or consolidate: Kanban (merge into Content Pipeline), Team (merge into Agents), Library tabs, Marketing sub-tabs, CRM Activities, CRM Products (keep in CRM but simplify)

## IMPORTANT
- Do NOT modify any backend Python files
- All new data can use localStorage until backend APIs are built
- Use the existing warroom theme colors (bg-warroom-bg, bg-warroom-surface, border-warroom-border, text-warroom-text, text-warroom-muted, text-warroom-accent, bg-warroom-accent)
- Responsive: works at 1440px+ width minimum
- Every component must be "use client" and have proper TypeScript types
