# Instagram Scraper Fix Plan — Sub-Agent Delegation

## Problem Statement

The Competitor Intel sync button triggers `POST /api/scraper/instagram/sync?background=1`.
The Playwright-based scraper should login to Instagram, scrape competitor profiles, and
update the database. 4 bugs confirmed via code reading and runtime verification.

## CRITICAL CONTEXT

**This is a multi-tenant application.** All social media credentials are stored PER ACCOUNT
in the `public.social_accounts` table, managed via Settings > Social Accounts in the app.
Environment variables for Instagram credentials (INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD,
INSTAGRAM_TOTP_SECRET) should NOT be used. They were added by a previous AI and are wrong.
The social accounts table has encrypted credentials that are decryptable and verified working.

## 4 Confirmed Bugs

### Bug 1: Credential resolution uses env vars instead of social accounts table
**File**: `backend/app/services/instagram_account_manager.py`
**Function**: `get_instagram_credentials_for_scraping()` (starts ~line 170)
**Problem**: Checks env vars FIRST. Since INSTAGRAM_USERNAME is set in .env, it always
returns env var creds and never reads the social accounts table. This is wrong for a
multi-tenant app. Credentials should ONLY come from the social accounts table.
**Runtime proof**: Function returns `Source: env_vars, Account ID: None`

### Bug 2: Cookie path doesn't match Docker volume mount
**File**: `backend/app/services/instagram_scraper.py`, line 30
**Problem**: `COOKIE_PATH = Path(os.getenv("INSTAGRAM_COOKIE_PATH", "/tmp/instagram_cookies.json"))`
Docker volume `instagram-cookies` is mounted at `/data`. Cookies saved to `/tmp` are lost
on container restart. `/tmp/instagram_cookies.json` does not exist. `/data/instagram_cookies.json`
exists but contains only unauthenticated cookies (no sessionid).

### Bug 3: Background sync swallows all errors
**File**: `backend/app/api/scraper.py`, function `_run_instagram_sync_in_background()` (~line 562)
**Problem**: Catches all exceptions and only logs them. Frontend polls `/api/scraper/status`
but only sees `sync_running: true/false`. No error message, no success/fail counts. User
sees "sync finished" with no indication of what happened.

### Bug 4: Each scrape_profile() launches its own browser
**File**: `backend/app/services/instagram_scraper.py`
**Problem**: `scrape_multiple()` at line 930 calls `scrape_profile()` in a loop. Each call
launches a new Playwright browser + new auth context. Docstring claims shared session but
implementation doesn't share. Lower priority — wasteful but not blocking.

---

## AGENT 1: Fix Credential Resolution

**File to edit**: `backend/app/services/instagram_account_manager.py`

### Exact changes to `get_instagram_credentials_for_scraping()`:

1. **DELETE the env var check block entirely** (lines ~170-177). This is a multi-tenant app.
   Credentials come from the social accounts table only. Remove:
   ```python
   # First try environment variables (for backward compatibility)
   username = getattr(settings, 'INSTAGRAM_USERNAME', None)
   password = getattr(settings, 'INSTAGRAM_PASSWORD', None)
   totp_secret = getattr(settings, 'INSTAGRAM_TOTP_SECRET', None)
   
   if username and password:
       logger.info("Using Instagram credentials from environment variables")
       return username, password, totp_secret, None
   ```

2. **DELETE the legacy settings table fallback** (the entire third try block ~lines 198-230).
   The settings table stores API keys, not scraper credentials. Remove the block that does
   `SELECT value FROM public.settings WHERE key = :k`. Dead code.

3. **Make the social accounts table lookup the ONLY source**. The existing code at ~line 181
   already does this correctly via `InstagramAccountManager`. Just make it the only path.

4. **Add clear logging**:
   - `logger.info("SCRAPER_CRED: Looking up Instagram scraping account from social_accounts table")`
   - On success: `logger.info("SCRAPER_CRED: Found account @%s (id=%d) with password=%s, totp=%s", username, account_id, bool(password), bool(totp_secret))`
   - On failure: `logger.error("SCRAPER_CRED: No active Instagram scraping account found in social_accounts table. Add one in Settings > Social Accounts.")`

5. **Final function should be approximately**:
   ```python
   async def get_instagram_credentials_for_scraping():
       from app.db.crm_db import crm_session
       
       try:
           async with crm_session() as db:
               await db.execute(text("SET search_path TO crm, public"))
               manager = InstagramAccountManager(db)
               account = await manager.get_active_account("scraping")
               
               if account and account["password"]:
                   logger.info("SCRAPER_CRED: Found account @%s (id=%d)", account["username"], account["id"])
                   return account["username"], account["password"], account["totp_secret"], account["id"]
       except Exception as e:
           logger.error("SCRAPER_CRED: Database error looking up Instagram account: %s", e)
       
       logger.error("SCRAPER_CRED: No active Instagram scraping account found. Add one in Settings > Social Accounts.")
       return None, None, None, None
   ```

**DO NOT touch**: The `InstagramAccountManager` class, `mark_instagram_account_used()`, or `mark_instagram_account_error()`. They work correctly.

**Verification**:
```bash
docker exec -w /app warroom-backend-1 python -c "
import asyncio
from app.services.instagram_account_manager import get_instagram_credentials_for_scraping
async def test():
    u, p, t, aid = await get_instagram_credentials_for_scraping()
    assert aid is not None, 'FAIL: account_id is None — still using env vars'
    assert u == 'whimsy_estates', f'FAIL: wrong username: {u}'
    assert bool(p), 'FAIL: no password'
    assert bool(t), 'FAIL: no TOTP secret'
    print('PASS: Credentials from social accounts table, account_id=%d' % aid)
asyncio.run(test())
"
```

---

## AGENT 2: Fix Cookie Path + Add Scraper Logging

**File to edit**: `backend/app/services/instagram_scraper.py`

### Change 1 — Fix cookie path (line 30):
```python
# BEFORE:
COOKIE_PATH = Path(os.getenv("INSTAGRAM_COOKIE_PATH", "/tmp/instagram_cookies.json"))

# AFTER:
COOKIE_PATH = Path(os.getenv("INSTAGRAM_COOKIE_PATH", "/data/instagram_cookies.json"))
```
This matches the Docker volume mount `instagram-cookies:/data` in docker-compose.yml.

### Change 2 — Add logging in `_get_authenticated_context()` (~line 570):
Insert after existing code points (DO NOT restructure):
- After `saved_cookies = await _load_cookies()`: `logger.info("SCRAPER_AUTH: Cookie file exists=%s at %s", COOKIE_PATH.exists(), COOKIE_PATH)`
- After `if saved_cookies:` + `if await _has_valid_session(context):`: `logger.info("SCRAPER_AUTH: Saved cookies valid, reusing session")`
- Before `await context.clear_cookies()`: `logger.info("SCRAPER_AUTH: Saved cookies expired, clearing")`
- Before `logged_in = await _login_to_instagram(context)`: `logger.info("SCRAPER_AUTH: Starting fresh login")`
- After login result: `logger.info("SCRAPER_AUTH: Login result=%s", logged_in)`

### Change 3 — Add logging in `_login_to_instagram()` (~line 392):
Insert at these EXISTING code points (DO NOT restructure the function):
- After credentials are loaded (~line 400): `logger.info("SCRAPER_LOGIN: Credentials loaded, username=@%s, has_totp=%s, source=%s", username, bool(totp_secret), "db" if account_id else "env")`
- After `await page.goto(...)` login page load: `logger.info("SCRAPER_LOGIN: Login page loaded")`
- After `await username_input.fill(username)`: `logger.info("SCRAPER_LOGIN: Username entered")`
- After `await password_input.press("Enter")`: `logger.info("SCRAPER_LOGIN: Login form submitted")`
- After the 5s sleep, at `current_url = page.url`: `logger.info("SCRAPER_LOGIN: Post-submit URL: %s", current_url)`
- When 2FA detected: `logger.info("SCRAPER_LOGIN: 2FA challenge detected")`
- After TOTP code generated: `logger.info("SCRAPER_LOGIN: TOTP code generated")`
- After 2FA submit: `logger.info("SCRAPER_LOGIN: 2FA submitted, waiting for result")`
- After 2FA passes/fails: `logger.info("SCRAPER_LOGIN: 2FA result: %s", "passed" if not on_2fa_page else "failed")`
- After cookies saved: `logger.info("SCRAPER_LOGIN: Success, %d cookies saved", len(cookies))`
- In each error path: `logger.error("SCRAPER_LOGIN: Failed — %s", specific_reason)`

### Change 4 — Add logging in `scrape_profile()` (~line 604):
- At start: `logger.info("SCRAPER_PROFILE: Starting scrape for @%s", handle)`
- After browser launch: `logger.info("SCRAPER_PROFILE: Browser launched")`
- After auth context ready: `logger.info("SCRAPER_PROFILE: Auth context ready")`
- After page navigate + response: `logger.info("SCRAPER_PROFILE: Profile page loaded, status=%s", resp.status if resp else "none")`
- After data capture wait: `logger.info("SCRAPER_PROFILE: Data captured: %s", list(captured_data.keys()))`
- After profile built: `logger.info("SCRAPER_PROFILE: @%s result — followers=%d, posts=%d, error=%s", handle, result.followers, len(result.posts), result.error)`

**DO NOT change**: Login logic, 2FA handling, credential resolution, scraping logic, data parsing. Only ADD logging lines.

**Verification**:
```bash
docker exec -w /app warroom-backend-1 python -c "
from app.services.instagram_scraper import COOKIE_PATH
assert str(COOKIE_PATH) == '/data/instagram_cookies.json', f'FAIL: {COOKIE_PATH}'
print('PASS: Cookie path is /data/instagram_cookies.json')
"
```

---

## AGENT 3: Add Sync Error Reporting

**Files to edit**: 
- `backend/app/api/scraper.py`  
- `frontend/src/components/intelligence/CompetitorIntel.tsx`

### Backend changes (`scraper.py`):

1. **Add module-level result storage** near `_instagram_sync_task` (~line 39):
```python
_instagram_sync_result: Optional[Dict[str, Any]] = None
```

2. **Update `_run_instagram_sync_in_background()`** (~line 562) to store results:
```python
async def _run_instagram_sync_in_background() -> None:
    global _instagram_sync_result
    _instagram_sync_result = {"status": "running", "started_at": datetime.now().isoformat()}
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            result = await _execute_instagram_sync(db, org_id=1)
            await db.commit()
            _instagram_sync_result = {
                "status": "complete",
                "success": result.success,
                "failed": result.failed,
                "total": result.total,
                "posts_saved": result.posts_saved,
                "completed_at": datetime.now().isoformat(),
            }
            logger.info(
                "Background Instagram sync finished: %s/%s succeeded, %s posts cached",
                result.success, result.total, result.posts_saved,
            )
    except HTTPException as exc:
        _instagram_sync_result = {"status": "error", "error": exc.detail, "completed_at": datetime.now().isoformat()}
        logger.warning("Background Instagram sync skipped: %s", exc.detail)
    except Exception as exc:
        _instagram_sync_result = {"status": "error", "error": str(exc), "completed_at": datetime.now().isoformat()}
        logger.exception("Background Instagram sync failed: %s", exc)
```

3. **Add `sync_result` to `ScrapeStatusResponse`** (~line 84):
```python
class ScrapeStatusResponse(BaseModel):
    total_competitors: int
    total_cached_posts: int
    last_scrape: Optional[datetime] = None
    competitors: List[Dict[str, Any]] = []
    sync_running: bool = False
    sync_result: Optional[Dict[str, Any]] = None  # ADD THIS
```

4. **Populate `sync_result` in the `/scraper/status` endpoint** — in the return statements, add:
```python
sync_result=_instagram_sync_result,
```

### Frontend changes (`CompetitorIntel.tsx`):

5. **Update `waitForInstagramSyncCompletion()`** (~line 1162) to read and display sync_result:

Replace the `if (!status.sync_running)` block:
```typescript
if (!status.sync_running) {
    const sr = (status as any).sync_result;
    if (sr?.status === "error") {
        setError(`Instagram sync failed: ${sr.error}`);
    } else if (sr?.status === "complete") {
        setNotice(
            `Instagram sync complete: ${sr.success}/${sr.total} competitors scraped, ${sr.posts_saved} posts cached`
        );
    } else {
        setNotice("Instagram scrape finished.");
    }
    await refreshIntelligenceViews();
    return true;
}
```

**DO NOT change**: Sync trigger logic, background task creation, credential resolution, scraper code.

**Verification**: Login → Competitor Intel → Click Sync → Check that:
1. During sync: "sync started in background" message shows
2. On success: Shows "X/Y competitors scraped, Z posts cached"
3. On error: Shows the actual error message

---

## EXECUTION ORDER

```
AGENT 1 (Credentials)  →  AGENT 2 (Cookie + Logging)  →  Backend rebuild  →  AGENT 3 (Error reporting)  →  Full rebuild  →  Integration test
```

## RULES

1. Read the full function before editing
2. No curl testing
3. No new files, no new packages
4. str_replace exact match edits only
5. Log with SCRAPER_ prefix
6. Never display credentials
7. If unclear, STOP and ask
