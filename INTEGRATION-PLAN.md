# War Room — New Feature Integration Plan

## Current Sidebar Structure
```
COMMAND
  Dashboard    → CommandCenter
  Chat         → ChatPanel
  Agents       → AgentServiceMap
  Tasks        → KanbanPanel

SOCIALS
  Tracker      → ContentTracker
  Analytics    → SocialDashboard

CONTENT
  Pipeline     → ContentPipeline
  Reports      → CompetitorIntel
  Instagram    → PlatformContent
  YouTube      → PlatformContent
  Facebook     → PlatformContent
  X            → PlatformContent

OPERATIONS
  Leads        → LeadgenPanel
  CRM (flyout) → Deals, Contacts, Activities, Products

TOOLS
  Library (flyout) → Search, Educate
  Marketing (flyout) → Campaigns, Templates

[bottom]
  Settings     → SettingsPanel
  Logout
```

## New Features — Where They Go

### 1. Usage Widget (in header/nav, NOT sidebar)
- **Location:** Top-right of the main content area, as a floating pill
- **Component:** `UsageWidget.tsx`
- **Integration:** Add to `page.tsx` main area, positioned absolute top-right
- **Why not sidebar:** It's always visible, not a page — like a status indicator
- **Shows:** Current model name + session usage % as a compact pill
- **Expands:** Click to see full usage breakdown + model switcher dropdown

### 2. Skills Manager
- **Location:** TOOLS section, new sidebar item
- **Nav item:** `{ id: "skills", label: "Skills", icon: Package }`
- **Component:** `SkillsManager.tsx`
- **Tab ID:** `"skills"`
- **Integration:** Add to SECTIONS.TOOLS.items, add TabId, add route in main content
- **No conflicts:** New tab ID, new component, new API endpoints

### 3. Activity Calendar
- **Location:** COMMAND section, after Agents
- **Nav item:** `{ id: "calendar", label: "Calendar", icon: Calendar }`
- **Component:** `ActivityCalendar.tsx`
- **Tab ID:** `"calendar"`
- **Note:** Calendar icon already imported from lucide, used in CRM Activities.
  Use `CalendarDays` icon instead to differentiate.

### 4. Soul Editor
- **Location:** TOOLS section, new sidebar item OR under Settings as a sub-tab
- **Option A (standalone):** `{ id: "soul", label: "Soul", icon: Heart }` in TOOLS
- **Option B (under Settings):** Add as a tab within SettingsPanel
- **Recommendation:** Standalone in TOOLS — it's important enough
- **Component:** `SoulEditor.tsx`
- **Tab ID:** `"soul"`

## Updated Sidebar (after integration)
```
COMMAND
  Dashboard
  Chat
  Agents
  Calendar     ← NEW (activity calendar)
  Tasks

SOCIALS
  Tracker
  Analytics

CONTENT
  Pipeline
  Reports
  Instagram
  YouTube
  Facebook
  X

OPERATIONS
  Leads
  CRM (flyout)

TOOLS
  Skills       ← NEW (skills manager)
  Soul         ← NEW (soul editor)
  Library (flyout)
  Marketing (flyout)

[bottom]
  [Usage pill]  ← NEW (floating, always visible)
  Settings
  Logout
```

## Backend Integration (main.py)
New imports to add:
```python
from app.api import usage, skills_manager, soul, calendar as cal
```

New routers:
```python
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])
app.include_router(skills_manager.router, prefix="/api", tags=["skills"])
app.include_router(soul.router, prefix="/api", tags=["soul"])
app.include_router(cal.router, prefix="/api", tags=["calendar"])
```

## Frontend Integration (page.tsx)
1. Add imports for new components
2. Add new TabIds to the type union
3. Add new items to SECTIONS
4. Add new routes in main content area
5. Add UsageWidget as floating element

## Risk Assessment
- **Zero breaking changes** — all existing tabs, routes, and components untouched
- **New files only** — except main.py (backend router registration) and page.tsx (nav + routes)
- **Independent features** — each new feature has its own API + component, no shared state with existing features
- **No database changes** — usage reads files, skills reads filesystem, soul reads/writes markdown, calendar reads memory files
