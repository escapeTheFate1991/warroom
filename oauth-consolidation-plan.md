# OAuth Consolidation Plan

## Current State ✓
- Central OAuth system (`social_oauth.py`) handles all platforms
- Single `SocialAccount` model stores tokens per platform
- Multi-tenant support with user_id/org_id encoding

## Issues to Fix ❌
1. **Recycle** as standalone nav item (should be post-level toggle)
2. **Redundant connections** - features ask for auth when already connected
3. **Fragmented checks** - each component reimplements connection status

## Solution Architecture

### 1. Shared OAuth Status Hook
**File:** `frontend/src/hooks/useSocialAccounts.ts`
```typescript
// Central hook that all features use to check connection status
export function useSocialAccounts() {
  // Returns connected platforms, triggers auth flows, handles refresh
}
```

### 2. Instagram Page Consolidation
**Current:** Multiple Instagram-related features scattered  
**Target:** Single `/content/instagram` page with tabs:
- **Feed** - OAuth-powered content view
- **Analytics** - performance metrics
- **Auto-Reply** - comment/DM automation
- **Scheduler** - posting calendar

### 3. Recycle Feature Redesign
**Current:** Standalone nav item with RecyclePanel  
**Target:** Post-level toggle throughout platform
- Remove "Recycle" from nav
- Add recycle toggle to individual post cards
- Integrate into Instagram page, scheduler, etc.

### 4. Unified Connection Flow
**Pattern:** All social features check `useSocialAccounts()` first
- If connected: proceed with feature
- If disconnected: show single OAuth connect button
- No duplicate connection prompts

## Implementation Steps

### Phase 1: Remove Recycle Nav Item ✓
1. Remove from navigation sections
2. Move RecyclePanel logic to post-level toggles
3. Update routes/tab handling

### Phase 2: Create Shared Hook ✓
1. Build `useSocialAccounts` hook
2. Centralize connection status logic
3. Handle token refresh automatically

### Phase 3: Consolidate Instagram Features ✓
1. Enhance Instagram page with tabs
2. Move auto-reply Instagram logic there
3. Integrate scheduling/recycling

### Phase 4: Update All Features ✓
1. Auto-reply uses shared hook
2. Scheduler uses shared hook
3. URL-to-social uses shared hook
4. Remove individual connection prompts

## File Changes Required

### Frontend
- `src/app/page.tsx` - Remove recycle nav item
- `src/hooks/useSocialAccounts.ts` - NEW shared hook
- `src/components/social/platforms/InstagramPage.tsx` - Enhance with tabs
- `src/components/auto-reply/AutoReplyPanel.tsx` - Use shared hook
- `src/components/scheduler/SchedulerCalendar.tsx` - Use shared hook

### Backend (if needed)
- OAuth system already consolidated ✓
- May need endpoint to check connection status

## Expected Outcomes
✅ Single OAuth connection per platform  
✅ No redundant "connect your account" prompts  
✅ Recycle as post-level feature, not navigation item  
✅ Consistent UX across all social features  
✅ Instagram as centralized social hub  