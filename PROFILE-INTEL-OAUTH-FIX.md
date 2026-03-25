# Profile Intel OAuth Integration Fix

## Problem
The Profile Intel feature in War Room's Competitor Intelligence was not using the centralized OAuth session handling properly, potentially causing inconsistencies with other components that use the `useSocialAccounts` hook.

## Root Cause Analysis
The Profile Intel component was already using the centralized `useSocialAccounts` hook, but had a few consistency and user experience issues:

1. Missing loading state check for `socialAccounts.loading` 
2. No error handling for OAuth connection errors
3. No loading states for connection attempts
4. Data not properly cleared when disconnected
5. Some redundant calls to `fetchInstagramAdvice()` in refresh flows

## Changes Made

### 1. Enhanced OAuth State Management
```typescript
// Added missing loading and error states from useSocialAccounts
const { connected, isConnected, connect, loading: socialAccountsLoading, error: socialAccountsError } = useSocialAccounts();

// Added connecting state for better UX
const [connectingInstagram, setConnectingInstagram] = useState(false);
```

### 2. Improved Loading State Logic
```typescript
{socialAccountsLoading ? (
  <div className="text-center py-16">
    <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
    <p className="text-sm text-warroom-muted">Loading connection status…</p>
  </div>
) : loadingInstagramAdvice ? (
  // ... profile analysis loading state
) : !isConnected('instagram') ? (
  // ... connection prompt
```

### 3. Added Error Handling
```typescript
) : socialAccountsError ? (
  <div className="text-center py-16 text-warroom-muted">
    <User size={48} className="mx-auto mb-4 opacity-20 text-red-400" />
    <p className="text-sm font-medium text-red-400">Connection Error</p>
    <p className="text-xs mt-1 text-warroom-muted">{socialAccountsError}</p>
    <button onClick={() => window.location.reload()}>Reload Page</button>
  </div>
```

### 4. Enhanced Connection Button
```typescript
<button
  onClick={async () => {
    setConnectingInstagram(true);
    try {
      await connect('instagram');
    } catch (error) {
      console.error('Failed to connect Instagram:', error);
    } finally {
      setConnectingInstagram(false);
    }
  }}
  disabled={connectingInstagram}
  className="... flex items-center gap-2"
>
  {connectingInstagram && <Loader2 size={16} className="animate-spin" />}
  {connectingInstagram ? 'Connecting...' : 'Connect Instagram'}
</button>
```

### 5. Improved Data Management
```typescript
// Monitor OAuth connection status for Profile Intel
useEffect(() => {
  if (activeTab === "profile-intel" && !socialAccountsLoading) {
    if (isConnected('instagram')) {
      fetchInstagramAdvice();
    } else {
      // Clear Profile Intel data when disconnected
      setInstagramAdvice(null);
      setLoadingInstagramAdvice(false);
    }
  }
}, [connected, activeTab, socialAccountsLoading]);
```

### 6. Cleaned Up Redundant Calls
```typescript
// Removed fetchInstagramAdvice() calls from refresh flows since it's now handled by OAuth useEffect
const refreshIntelligenceViews = async () => {
  // ... other calls
  // fetchInstagramAdvice() is now handled by OAuth useEffect
};
```

## Benefits

1. **Consistency**: Profile Intel now uses the exact same OAuth patterns as other components (Instagram Page, Auto-Reply)
2. **Better UX**: Proper loading states and error handling
3. **Reliability**: Data is properly cleared when disconnected, preventing stale data issues
4. **Performance**: Eliminates redundant API calls by centralizing OAuth-driven data loading
5. **Maintainability**: Follows the established OAuth pattern throughout the app

## Testing
- [✅] Build compiles successfully
- [✅] Frontend service restarts cleanly
- [✅] Components follow consistent OAuth patterns
- [✅] Error states are handled gracefully
- [✅] Loading states provide clear feedback

## Files Modified
- `frontend/src/components/intelligence/CompetitorIntel.tsx`

## Verification Steps
1. Navigate to Competitor Intelligence → Profile Intel tab
2. Should show "Loading connection status..." initially  
3. If not connected: shows Instagram connect button with proper loading state
4. If connection fails: shows error message with reload option
5. If connected: loads profile data and analysis
6. All states should be consistent with Instagram Page and Auto-Reply components