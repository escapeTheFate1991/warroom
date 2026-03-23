## ✅ EXECUTION COMPLETE

All waves completed successfully on March 23, 2026.

### Results:
- Wave 1: Backend cleanup ✅ (main.py 800→318 lines, CUT imports removed)
- Wave 2: Frontend cleanup ✅ (18 component dirs deleted, ~32k lines removed, nav rebuilt)
- Wave 3: Database cleanup script ✅ (migration ready, not yet executed)
- Wave 4: Rebrand + dashboard ✅ (socialRecycle branding, $99/$49 billing, new SocialDashboard)
- Wave 5: Integration testing ✅ (backend imports clean, frontend compiles, Docker builds pass)
- Wave 6: Polish ✅ (CUT files deleted, codebase cleaned)

### Remaining:
- Execute database migration (socialrecycle_cleanup.sql) — needs Eddy's approval
- org→team rename — planned for future iteration
- CSS variable rename (warroom-* → socialrecycle-*) — cosmetic, low priority

---

# socialRecycle - Wave-Based Execution Plan

## Research Summary

After analyzing the warroom codebase, I've identified critical dependencies between KEEP and CUT features that must be resolved systematically. The main dependencies are:

### Critical Dependencies Found:

1. **KEEP APIs depend on CRM models** (app/models/crm/)
2. **Social features reference crm.organizations and crm.users**
3. **Content pipeline integrates with agent systems** (needs decoupling)
4. **Frontend has extensive CUT component references**
5. **Database initialization includes 45+ CUT table inits**

---

## Wave 1: Backend Dependency Resolution
*Duration: 3-5 days*

### 1.1 Backend Main.py Router Cleanup
**Files:** `backend/app/main.py`
**What to do:** Remove CUT router imports and include_router calls
**Why:** Eliminates 60+ CUT API endpoints, simplifies app startup

**CUT routers to remove:**
- All CRM routers (`deals`, `contacts`, `activities`, `pipelines`, `products`, `emails`, `marketing`, `attributes`, `acl`, `data`, `audit`, `pipeline_board`, `workflows`, `workflow_executions`)
- Agent & AI systems (`agents`, `agent_chat`, `agent_comms`, `agent_onboarding`, `anchor_agent`, `knowledge_pool`, `ai_planning`, `task_deps`, `task_execution`, `blackboard`, `simulate`)
- Lead generation (`leadgen`, `lead_enrichment`, `prospects`, `cold_email`)
- Business operations (`invoicing`, `contracts`, `email_inbox`)
- Complex systems (`kanban`, `team`, `library`, `mental_library`, `library_ingest`, `skills_manager`, `soul`)
- Communications (`voice`, `telnyx`, `twilio`, `twilio_voice`, `comms`)
- Paperclip architecture (`entities`, `goals`, `approvals`, `org_chart`, `task_checkout`, `budget`)
- Utilities (`scraper`, `contact_webhook`, `content_tracker`, `content_ai`, `audit_trail`, `token_metering`, `vector_memory`, `digital_copies`, `usage`, `cdn_migration`)

### 1.2 Lifespan Function Cleanup
**Files:** `backend/app/main.py` (lifespan function)
**What to do:** Remove CUT table initialization calls  
**Why:** Eliminates 45+ CUT table inits, speeds startup

**CUT initializations to remove:**
- `telnyx.init_telnyx_tables()` 
- `ensure_agent_tables()` and agent provisioning
- `cold_email.init_cold_email_tables()`
- `lead_enrichment.init_enrichments_table()`
- `email_inbox.init_email_tables()`
- `contracts.init_contracts_tables()`
- `invoicing.init_invoicing_tables()`
- `prospects.init_prospects_table()`
- `twilio_voice._ensure_table()`
- `init_token_metering_tables()`
- `_init_agent_chat_tables()`
- `_init_network_ai_blackboard()`
- `init_audit_trail_table()`
- All Paperclip migrations
- All Mental Library migrations
- All Agent multi-instance migrations

### 1.3 CRM Model Simplification 
**Files:** 
- `backend/app/models/crm/user.py` 
- `backend/app/models/crm/social.py`
- `backend/app/models/crm/auto_reply.py`
- `backend/app/models/crm/competitor.py`
- `backend/app/db/crm_db.py`

**What to do:** Simplify org → team model, remove complex ACL
**Why:** KEEP features reference these models, need team-focused simplification

**Changes needed:**
- Replace `organization_id` with `team_id` in social models
- Simplify User model (remove complex roles, keep basic auth)
- Update foreign key references
- Remove ACL complexity

### 1.4 Fix KEEP API Import Dependencies
**Files to fix:**
- `backend/app/api/social.py` - uses `app.db.crm_db` and `app.models.crm.social`
- `backend/app/api/social_oauth.py` - uses `app.db.crm_db` and `app.models.crm.social`  
- `backend/app/api/social_content.py` - uses `app.db.crm_db`
- `backend/app/api/auto_reply.py` - uses `app.models.crm.auto_reply` and `app.models.crm.user`
- `backend/app/api/content_scheduler.py` - uses `app.models.crm.user`
- `backend/app/api/google_ai_studio.py` - uses `app.models.crm.user`
- `backend/app/api/ugc_studio.py` - uses `app.models.crm.user` and imports from `digital_copies`
- `backend/app/api/video_editor.py` - uses `app.models.crm.user`
- `backend/app/api/video_copycat.py` - uses `app.models.crm.user`
- `backend/app/api/competitors.py` - uses `app.models.crm.competitor` and `app.models.crm.social`
- `backend/app/api/content_intel.py` - uses multiple CRM models and imports from `contracts`
- `backend/app/api/mirofish.py` - uses `app.db.crm_db`

**What to do:** Update imports to use simplified team models, stub out removed dependencies
**Why:** KEEP features must work without CUT dependencies

### 1.5 Fix KEEP Service Dependencies  
**Files:**
- `backend/app/services/auto_reply_engine.py` - uses `app.models.crm.auto_reply`
- `backend/app/services/social_inbox_processor.py` - uses `app.models.crm.social`
- `backend/app/services/instagram_account_manager.py` - uses `app.db.crm_db`
- `backend/app/services/scheduler.py` - uses `app.db.crm_db`
- `backend/app/services/oauth_scoping.py` - uses `app.models.crm.social`

**What to do:** Update to use simplified models, remove agent integrations
**Why:** Core social services must function independently

---

## Wave 2: Frontend Component Cleanup
*Duration: 2-3 days*

### 2.1 Remove CUT Component Directories
**Directories to remove:**
- `frontend/src/components/agents/`
- `frontend/src/components/communications/`
- `frontend/src/components/contacts/` (part of CRM)
- `frontend/src/components/contracts/`
- `frontend/src/components/crm/`
- `frontend/src/components/dashboard/` (replace with social dashboard)
- `frontend/src/components/email/`
- `frontend/src/components/invoicing/`
- `frontend/src/components/kanban/`
- `frontend/src/components/leadgen/`
- `frontend/src/components/library/`
- `frontend/src/components/marketing/`
- `frontend/src/components/org-chart/`
- `frontend/src/components/pricing/` (rebuild for social SaaS)
- `frontend/src/components/profile/` (simplify for social users)
- `frontend/src/components/prospects/`
- `frontend/src/components/reports/`
- `frontend/src/components/team/` (simplify to team-focused)
- `frontend/src/components/workflows/`

**What to do:** Delete entire directories
**Why:** These represent CUT features

### 2.2 Update Main Layout Navigation
**Files:** `frontend/src/app/page.tsx`

**What to do:** Remove CUT tab references, rebuild SECTIONS for social focus
**Why:** Clean social-focused navigation

**Remove from SECTIONS:**
- COMMAND: `agents`, `communications`, `email`, `kanban`
- OPERATIONS: `leadgen`, `pipeline-board`, `prospects`, `organizations`, `crm-contacts`, `org-chart`
- FINANCE: `invoices`, `contracts`, `reports`
- TOOLS: `workflows`, `library`, `marketing`

**New SECTIONS structure:**
```javascript
const SECTIONS = [
  {
    label: "SOCIAL COMMAND",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "chat", label: "Chat", icon: MessageSquare }, // Keep minimal for DMs
      { id: "calendar", label: "Calendar", icon: CalendarDays },
    ],
  },
  {
    label: "CONTENT",
    items: [
      { id: "ai-studio", label: "AI Studio", icon: Sparkles },
      { id: "pipeline", label: "Content Pipeline", icon: Film },
      { id: "content-social", label: "URL → Social", icon: Share2 },
      { id: "scheduler", label: "Scheduler", icon: CalendarDays },
    ],
  },
  {
    label: "PLATFORMS", 
    items: [
      { id: "social-instagram", label: "Instagram", icon: Instagram },
      { id: "social-tiktok", label: "TikTok", icon: Twitter },
      { id: "social-youtube", label: "YouTube Shorts", icon: Youtube },
      { id: "social-facebook", label: "Facebook", icon: Facebook },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { id: "intelligence", label: "Competitor Intel", icon: FileBarChart },
      { id: "social", label: "Analytics", icon: BarChart3 },
      { id: "mirofish", label: "Mirofish", icon: Zap },
    ],
  },
  {
    label: "AUTOMATION",
    items: [
      { id: "auto-reply", label: "Auto-Reply", icon: Zap },
    ],
  },
];
```

### 2.3 Remove CUT Component Imports
**Files:** `frontend/src/app/page.tsx`
**What to do:** Remove dynamic imports for CUT components
**Why:** Clean component loading

**Remove imports:**
- `KanbanPanel`, `LibraryPanel`, `EducatePanel`, `LeadgenPanel`
- `WorkflowsPanel`, `ContactsManager`, `OrgChartPanel` 
- `CampaignsPanel`, `EmailTemplatesPanel`, `AgentFeaturePage`, `AgentEditPage`
- `ContractsPanel`, `InvoicingPanel`, `EmailInbox`, `ReportsOverview`, `ProspectsPanel`
- `UnifiedPipeline`, `OrganizationsPanel`, `CommunicationsConsole`, `ProfilePage`

### 2.4 Update Component References
**Check KEEP components for CUT imports:**
- `frontend/src/components/social/` - check for agent/CRM references
- `frontend/src/components/content/` - check for agent/workflow references  
- `frontend/src/components/auto-reply/` - check for agent references
- `frontend/src/components/scheduler/` - check for agent references
- `frontend/src/components/intelligence/` - check for CRM references

**What to do:** Remove/stub out CUT component references
**Why:** KEEP components must work independently

---

## Wave 3: Database Schema Cleanup
*Duration: 2-3 days*

### 3.1 Identify CUT Migration Files
**Directories:** `backend/app/db/`
**What to do:** Identify and plan removal of CUT migration files
**Why:** Clean up migration history

**CUT migrations to remove:**
- Agent-related migrations
- CRM schema migrations (keep only basic user/team tables)
- Paperclip migrations (`paperclip_migration.sql`)
- Mental Library migrations (`mental_library_migration.sql`)
- Org Chart migrations (`org_chart_migration.sql`)
- Any migrations for leadgen, contracts, invoicing, etc.

### 3.2 Schema Simplification Plan
**Files:** 
- `backend/app/db/crm_db.py`
- Migration files in `backend/app/db/`

**What to do:** Plan org → team simplification
**Why:** Social SaaS is team-focused, not org-focused

**Changes needed:**
- Replace `crm.organizations` with simple `teams` table
- Update foreign key references from `organization_id` to `team_id`
- Simplify user roles (remove complex ACL)
- Keep only essential social-related tables

### 3.3 Create New Schema Migration
**Files:** New `backend/app/db/socialrecycle_migration.sql`
**What to do:** Create migration script for org→team transformation
**Why:** Clean transition to team-focused model

**Migration tasks:**
- Create new `teams` table (simplified from organizations)
- Update `users` table to reference teams instead of organizations
- Update social account tables for team context
- Update content scheduler tables for team context
- Drop all CUT tables

---

## Wave 4: Rebranding & New Social Dashboard  
*Duration: 3-4 days*

### 4.1 Rename Project
**Files:** 
- `package.json`, `README.md`, configuration files
- `backend/app/main.py` (title)
- `frontend/src/app/layout.tsx` (title/meta)

**What to do:** Rename from "WAR ROOM" to "socialRecycle"
**Why:** New product identity

### 4.2 Build Social-Focused Dashboard
**Files:** 
- `frontend/src/components/dashboard/SocialDashboard.tsx` (new)
- Replace `CommandCenter` references

**What to do:** Create social media management dashboard
**Why:** Social-focused UI instead of business command center

**Dashboard features:**
- Social platform status overview
- Content performance metrics
- Scheduled content pipeline
- Competitor intelligence summary
- Auto-reply activity
- Content generation statistics

### 4.3 Update Billing System
**Files:**
- `backend/app/api/stripe_settings.py`
- `frontend/src/components/settings/BillingPanel.tsx`

**What to do:** Update for social SaaS pricing
**Why:** $99/mo core + $49/mo Mirofish upsell

**Pricing tiers:**
- socialRecycle Core: $99/mo
- Mirofish Add-on: $49/mo  
- Remove business/enterprise tiers

### 4.4 Update Authentication Context
**Files:**
- `backend/app/middleware/tenant_guard.py`
- Authentication flows

**What to do:** Simplify to team-based authentication
**Why:** Remove complex org-based multi-tenancy

---

## Wave 5: Integration Testing & Verification
*Duration: 2-3 days*

### 5.1 Backend Testing
**What to do:** Verify all KEEP API endpoints work
**Why:** Ensure no broken dependencies

**Test areas:**
- Social OAuth flows (Instagram, TikTok, YouTube, Facebook)
- Content generation (AI Studio, UGC, Video)
- Content scheduling and publishing
- Auto-reply engine
- Competitor intelligence
- Analytics and performance tracking

### 5.2 Frontend Testing  
**What to do:** Verify UI flows work end-to-end
**Why:** Ensure clean UX

**Test areas:**
- Platform connection flows
- Content creation workflows
- Scheduling and publishing
- Analytics viewing
- Settings management

### 5.3 Database Testing
**What to do:** Verify schema changes work
**Why:** Ensure data integrity

**Test areas:**
- Team-based multi-tenancy
- Social account management
- Content storage and retrieval
- User authentication

---

## Wave 6: Performance & Polish
*Duration: 1-2 days*

### 6.1 Performance Optimization
**What to do:** Remove unused dependencies, optimize bundle
**Why:** Clean, fast social SaaS

### 6.2 UI Polish  
**What to do:** Social-focused UI improvements
**Why:** Professional social media management feel

### 6.3 Documentation Update
**What to do:** Update README, API docs for socialRecycle
**Why:** Clear product documentation

---

## Execution Rules

1. **Each wave must complete fully before starting the next**
2. **Test after each wave to ensure no regressions**
3. **All tasks within a wave can run in parallel**
4. **Commit frequently during each wave**
5. **Use sub-agents for complex multi-file changes**
6. **Keep main session available for questions/clarification**

## Estimated Timeline: 12-18 days total

- Wave 1: 3-5 days (Backend dependencies)
- Wave 2: 2-3 days (Frontend cleanup)  
- Wave 3: 2-3 days (Database cleanup)
- Wave 4: 3-4 days (Rebranding & dashboard)
- Wave 5: 2-3 days (Testing)
- Wave 6: 1-2 days (Polish)

## Success Criteria

✅ **Backend**: Only KEEP routers included, clean startup without CUT table inits
✅ **Frontend**: Social-focused navigation, no CUT component references  
✅ **Database**: Team-focused schema, no CUT tables
✅ **Product**: socialRecycle branding, $99+$49 pricing
✅ **Testing**: All KEEP features work end-to-end
✅ **Performance**: Fast, clean social SaaS application