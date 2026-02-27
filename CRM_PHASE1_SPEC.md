# CRM Phase 1 — LeadGen Fixes + Micro-CRM + Business Detail Drawer

## Reference Code
Krayin CRM (PHP/Laravel) is at `/tmp/krayin-ref/` — READ ONLY. Use it for logic/workflow reference, NOT copy-paste. Everything must be TypeScript (frontend) and Python/FastAPI (backend).

## Warroom Stack
- **Backend:** FastAPI + SQLAlchemy async + PostgreSQL (see `backend/app/`)
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS (see `frontend/src/`)
- **API base:** `const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300"`
- **Existing leadgen:** `backend/app/api/leadgen.py`, `backend/app/models/lead.py`, `frontend/src/components/leadgen/LeadgenPanel.tsx`
- **Nav:** Sidebar tabs in `frontend/src/app/page.tsx` — add new tabs there

## TASK 1: Fix Tier Scoring (BROKEN)

The lead scorer at `backend/app/services/leadgen/lead_scorer.py` calculates scores but **scores are never applied to leads**. 

Fix: After enrichment completes in `backend/app/services/leadgen/enrichment.py`, call `score_lead()` for each lead and save the `lead_score` and `lead_tier` to the database. Also add a `/api/leadgen/leads/rescore` endpoint that rescores ALL leads (for fixing existing data).

## TASK 2: Business Detail Side Drawer

When clicking a business card in the leads list, a **slide-out drawer** should appear from the right side (not a new page).

### Drawer Layout:
**Top section (fixed):**
- Business name (large), category, tier badge (colored: hot=red, warm=orange, cold=blue)
- Address, phone, website link, Google rating + review count
- Social links (icons for FB, IG, LinkedIn, Twitter — only show if URL exists)
- Lead score bar (visual 0-100)
- Contacted status indicator (green=contacted, yellow=in progress, gray=not contacted)

**Scrollable body — tabbed sections:**

**Tab 1: Audit Lite**
- Quick surface-level website audit summary
- If `audit_lite_flags` exist, show as pill badges
- If `website_audit_score` exists, show score + grade + top fixes
- Button to trigger full audit (`POST /api/leadgen/leads/{id}/audit`)
- This is the "talking points" tab — what to say on the call

**Tab 2: Contact Log**
- Form to log a contact attempt:
  - `contacted_by` (text input — who made the call)
  - `who_answered` (text input)
  - `owner_name`, `economic_buyer`, `champion` (text inputs)
  - `outcome` (radio: won / lost / follow_up / no_answer / callback)
  - `notes` (textarea — call notes, why won/lost)
  - Submit button → `POST /api/leadgen/leads/{id}/contact`
- Below form: historical contact log timeline (from `contact_history` JSONB array)

**Tab 3: Scripts**
- Auto-generated cold call script based on business data:
  - Use business name, category, website status, audit findings
  - "Hi, I'm calling from yieldlabs. I noticed [business_name] is [using Wix / has no website / has a site scoring X]. We specialize in..."
  - Include 3 talking points pulled from audit_lite_flags
- Auto-generated cold email template (similar data, email format)
- Copy-to-clipboard button for each

**Tab 4: Notes**
- Free-form notes textarea (saves to `lead.notes`)
- Tags management (add/remove tags)

## TASK 3: Contacted/Assigned Status

**In the leads list (LeadgenPanel.tsx):**
- Color-code business cards by outreach status:
  - `none` → default dark card
  - `contacted` → left border accent (subtle blue)
  - `in_progress` → left border yellow  
  - `won` → left border green + ✓ badge
  - `lost` → left border red + dimmed opacity
- Show who contacted and when (small text below business name)
- Add filter buttons: All | Not Contacted | In Progress | Won | Lost

## TASK 4: Contacts History Page

Add a new nav tab "Contacts" (icon: Users or Phone) in `frontend/src/app/page.tsx`.

This page shows ALL contacted businesses as a table/list:
- Business name, contacted by, date, outcome, notes preview
- Click row → opens the same side drawer from Task 2
- Filters: by outcome, by contacted_by, date range
- Uses `GET /api/leadgen/contacts` endpoint (already exists)

## TASK 5: Settings Tab Structure  

Update `frontend/src/components/settings/SettingsPanel.tsx` to use a **top-of-page horizontal tab bar** for organizing settings by feature. Each feature gets its own settings page:

Tabs (implement the tab structure + placeholder content for now):
- **General** (existing settings)
- **Email Integration** (placeholder: "Configure Gmail/SMTP connection")
- **Social Media** (placeholder: "Connect social accounts") 
- **Lead Scoring** (show current scoring weights from lead_scorer.py, make them editable in the future)
- **Automation** (placeholder: "Configure OpenClaw automation rules")
- **Access Control** (placeholder: "Manage roles and permissions")

## Technical Requirements

1. All new components go in `frontend/src/components/` in appropriate subdirectories
2. Use existing Tailwind classes matching the warroom dark theme (look at existing components for the color palette — `bg-warroom-surface`, `border-warroom-border`, `text-warroom-text`, etc.)
3. Backend endpoints use the existing `get_leadgen_db` dependency
4. No new Docker services — everything runs inside the existing backend/frontend containers
5. Use `frontend/src/components/leadgen/LeadgenPanel.tsx` as reference for API call patterns and styling

## Files to Create/Modify

### Backend:
- MODIFY `backend/app/services/leadgen/enrichment.py` — call scorer after enrichment
- MODIFY `backend/app/api/leadgen.py` — add rescore endpoint
- MODIFY `backend/app/api/leadgen_schemas.py` — add any missing response fields

### Frontend:
- CREATE `frontend/src/components/leadgen/LeadDrawer.tsx` — the side drawer
- CREATE `frontend/src/components/leadgen/AuditLiteTab.tsx`
- CREATE `frontend/src/components/leadgen/ContactLogTab.tsx`  
- CREATE `frontend/src/components/leadgen/ScriptsTab.tsx`
- CREATE `frontend/src/components/leadgen/NotesTab.tsx`
- CREATE `frontend/src/components/contacts/ContactsPanel.tsx` — contacts history page
- MODIFY `frontend/src/components/leadgen/LeadgenPanel.tsx` — add drawer trigger, status colors, filters
- MODIFY `frontend/src/components/settings/SettingsPanel.tsx` — add tab structure
- MODIFY `frontend/src/app/page.tsx` — add Contacts nav tab

## DO NOT:
- Use PHP or any PHP frameworks
- Create new Docker services
- Modify docker-compose.yml
- Touch chat.py or ChatPanel.tsx
- Install heavy new dependencies (keep it lean)
