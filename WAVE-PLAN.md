# socialRecycle — Master Wave Plan

## Status
- **Wave 1:** ✅ COMPLETE — Frame-by-frame MCP integration
- **Wave 2:** ✅ COMPLETE — AI Studio + Competitor Intel bug fixes
- **Wave 3:** 🔄 NEXT — Scraper hardening + worker fix + Veo/Nano Banana verification
- **Wave 4:** ⏳ PLANNED — ML comment analysis + content gap detection
- **Wave 5:** ⏳ PLANNED — Video cloning pipeline (analyze → VEO chunks → stitch)
- **Wave 6:** ⏳ PLANNED — Deployment to DigitalOcean/Linode

## Completed Work (Waves 1-2)
- 5 ugc_studio.py endpoints fixed (missing request: Request)
- 4 carousel.py endpoints fixed (http_request param naming)
- video_analysis_service.py MCP integration (stdio subprocess)
- Frame analysis badges + tab in CompetitorIntel/PostDetailModal
- Social accounts settings page (router order + auth guard DB fallback)
- Instagram scraper login working (Meta unified form handled)
- Cookie invalidation bug fixed (private profiles no longer nuke session)
- Auto-follow competitors feature (on add + bulk follow-all endpoint)

---

## Wave 3: Scraper Hardening + Worker Fix + API Verification

### Goal
Make the scraper reliably handle both Meta unified login and classic Instagram forms. Fix the crashed worker. Verify Veo and Nano Banana API calls work end-to-end.

### Research Needed
- [ ] Read `instagram_scraper.py` login flow fully — map both Meta form (name="email", name="pass") and classic form (name="username", name="password")
- [ ] Read worker config — find `workflow_queue` import that crashes it
- [ ] Read `nano_banana.py` — verify Gemini image gen payload (responseModalities)
- [ ] Read Veo generate endpoint — verify `predictLongRunning` API structure
- [ ] Check Arq worker entry point and what tasks it runs

### Tasks

@@@task
# Task 1: Fix scraper login to handle both Instagram form variants
**Agent:** Sonnet | **Est:** ~15 min

Update `_login_to_instagram()` in `instagram_scraper.py` to detect which login form is shown (Meta unified vs classic Instagram) and use the correct selectors.

## Scope
- ONLY: `backend/app/services/instagram_scraper.py` — `_login_to_instagram()` function
- Meta form: `input[name="email"]` + `input[name="pass"]`
- Classic form: `input[name="username"]` + `input[name="password"]` OR `input[aria-label="Phone number, username, or email"]` + `input[aria-label="Password"]`
- Try Meta form first, fall back to classic if not found
- Don't change cookie loading/saving logic

## Verification
```bash
python3 -c "import ast; ast.parse(open('backend/app/services/instagram_scraper.py').read()); print('OK')"
grep -c 'name="email"\|name="pass"\|name="username"\|name="password"' backend/app/services/instagram_scraper.py  # Should be > 0
```
@@@

@@@task
# Task 2: Fix worker crash — remove workflow_queue import
**Agent:** Haiku | **Est:** ~5 min

Worker crashes on startup: `ModuleNotFoundError: No module named 'app.services.workflow_queue'`. This was removed during socialRecycle cleanup. Fix the worker entry point.

## Scope  
- Find the Arq worker config that imports `workflow_queue`
- Remove or stub the import
- Check `docker-compose.yml` worker command for the entry point file

## Verification
```bash
grep -r "workflow_queue" backend/app/ --include="*.py" -l  # Should be 0 files or only stubs
python3 -c "import ast; ast.parse(open('<worker_file>').read()); print('OK')"
```
@@@

@@@task
# Task 3: Verify and fix Nano Banana image generation API
**Agent:** Sonnet | **Est:** ~20 min

`nano_banana.py` calls Gemini for image generation. Verify the API payload structure is correct for current Gemini models. The `responseModalities: ["TEXT", "IMAGE"]` parameter may be needed for image gen to work.

## Scope
- ONLY: `backend/app/services/nano_banana.py`
- Read the `call_gemini_api()` function and `generate_*` functions
- Verify model names are current (gemini-2.0-flash-exp, imagen-3.0-generate-002)
- Add `responseModalities` if missing for image generation calls
- Test by checking the API docs: https://ai.google.dev/gemini-api/docs/image-generation

## Verification
```bash
python3 -c "import ast; ast.parse(open('backend/app/services/nano_banana.py').read()); print('OK')"
```
@@@

@@@task  
# Task 4: Verify Veo video generation endpoint
**Agent:** Sonnet | **Est:** ~15 min

The Veo endpoint uses `veo-3.0-fast-generate-001` via `predictLongRunning`. Verify the API URL structure, payload format, and polling mechanism are correct per Google's current docs.

## Scope
- ONLY: `backend/app/api/ugc_studio.py` — `generate_video()` and `check_generation_status()`
- Verify the URL pattern: `{GEMINI_API_BASE}/models/{model}:predictLongRunning`
- Verify payload: `instances[].prompt` + `parameters.aspectRatio/durationSeconds`
- Verify polling: GET to `{GEMINI_API_BASE}/{generation_id}` with API key
- Check: https://ai.google.dev/gemini-api/docs/video

## Verification
```bash
python3 -c "import ast; ast.parse(open('backend/app/api/ugc_studio.py').read()); print('OK')"
```
@@@

### Wave 3 Verification
Dedicated verifier agent after all 4 tasks complete:
- AST check all modified files
- Trace login flow end-to-end
- Rebuild backend + worker containers
- Test worker starts without crash
- Commit all changes

---

## Wave 4: ML Comment Analysis + Content Gap Detection

### Goal
Replace regex-based comment analysis with a local ML pipeline. Build "unanswered questions" detection and content gap analysis. No external API tokens — all local.

### Research Needed
- [ ] Evaluate ML options that run on CPU (no GPU): spaCy NER + topic modeling, sentence-transformers for clustering
- [ ] Design comment analysis pipeline: raw comments → topic clusters → question extraction → gap detection
- [ ] Check FastEmbed on Brain 2 — can it handle comment embeddings at scale?
- [ ] Design DB schema for storing ML analysis results

### Tasks (TBD after research)
- Rewrite `_analyze_comments()` in `comment_scraper.py`
- Add topic clustering using sentence-transformers + HDBSCAN
- Add unanswered question detection (questions with no replies)
- Add content gap analysis (what audience asks but influencer never covers)
- Add video topic suggestion engine from gaps
- Frontend: redesign Audience Intel panel with meaningful data

---

## Wave 5: Video Cloning Pipeline

### Goal
End-to-end: analyze competitor video → extract frame chunks → generate VEO clips per chunk → stitch into full recreation.

### Tasks (TBD after Wave 3)
- Test frame-by-frame analysis on top 5 competitor videos
- Wire blueprints UI to show analysis + one-click "clone this video"
- VEO generation per 8-second chunk
- Video stitching service
- MiroFish scoring on generated content before publish

---

## Wave 6: Production Deployment

### Goal
Deploy socialRecycle to DigitalOcean or Linode by end of March 2026.

### Tasks (TBD)
- Containerize for cloud deployment (docker-compose → production)
- Set up domain, SSL, DNS
- PostgreSQL managed instance or self-hosted
- Qdrant + FastEmbed deployment
- CI/CD pipeline
- Environment variable management
- Cloudflare tunnel → proper reverse proxy
- Execute DB migration (socialrecycle_cleanup.sql)
- Monitoring + alerting

---

## Outstanding Items (non-wave)
- Instagram CDN S3 download job (615 expired URLs → Garage)
- Education/library → SQLite to PostgreSQL migration  
- Wire OpenClaw multi-agent config to War Room agent records
- SNT changes deployed (committed but not deployed)
