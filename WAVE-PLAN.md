# AI Studio + Competitor Intel — Fix Everything

## Goal
Fix all broken API endpoints in AI Studio (video generation, carousel, templatizer) and wire frame-by-frame video analysis into the competitor intel UI so top content cards show analysis data.

## Research Summary

### Data Flow: Video Generation (Veo)
```
Frontend "Generate" button
  → POST /api/ai-studio/ugc/generate { project_id }
  → ugc_studio.generate_video(body, user, db)  ← CRASHES: references `request` (undefined)
  → _build_scene_prompt() → Veo API (veo-3.0-fast-generate-001:predictLongRunning)
  → Poll /api/ai-studio/ugc/generate/{id}/status  ← ALSO CRASHES: same bug
```

### Data Flow: Carousel
```
Frontend "Create Carousel" tab → POST /api/carousel/generate { text, format }
  → carousel.generate_carousel(request, user, db)
  → calls get_org_id(http_request)  ← CRASHES: param is `request` not `http_request`
  → CarouselGenerator.split_text_to_slides()
  → INSERT INTO crm.carousel_posts  ← table exists ✓
```

### Data Flow: Frame-by-Frame Analysis
```
POST /api/competitors/analyze-video { post_id }
  → competitors.py calls video_analysis_service.analyze_competitor_video()
  → _download_video() via httpx
  → _analyze_with_media_understanding() → POST http://localhost:18796/mcp  ← DEAD: no server
  → _create_frame_chunks() → _generate_veo_prompt() per chunk
  → _store_analysis_results() → UPDATE crm.competitor_posts (frame_chunks, video_analysis)
  → CompetitorIntel.tsx  ← NEVER RENDERS frame data
```

### Bugs Found (exact locations)

**ugc_studio.py — 5 endpoints missing `request: Request` param:**
- Line 619: `generate_video()` — params: [body, user, db]
- Line 719: `check_generation_status()` — params: [project_id, user, db]
- Line 785: `preview_prompt()` — params: [body, user]
- Line 954: `templatize_video()` — params: [body, user, db]
- Line 1078: `templatize_competitor_post()` — params: [body, user, db]

**carousel.py — 4 endpoints with wrong param names:**
- Line 61: `generate_carousel()` — has `request` but calls `get_org_id(http_request)`
- Line 112: `generate_carousel_images()` — same issue
- Line 209: `update_carousel()` — same issue
- Line 269: `publish_carousel()` — has `request` and `req` but calls `get_org_id(http_request)`

**video_analysis_service.py — MCP integration dead:**
- Line 35: `self.media_understanding_url = "http://localhost:18796"` — no server exists
- Line 151: POSTs to `{url}/mcp` — @dymoo/media-understanding is an npm MCP tool, not HTTP

**CompetitorIntel.tsx + PostDetailModal.tsx — no frame analysis rendering:**
- Competitor post cards have no UI for frame_chunks/video_analysis data
- DB columns exist and are populated by the analysis service

### Interface Checks
- `carousel_posts` table: exists ✓, 13 columns match carousel.py queries ✓
- `competitor_posts` columns: frame_chunks, video_analysis, analysis_status, analyzed_at all exist ✓
- CarouselGenerator + InstagramPublisher services: exist ✓
- nano_banana.py _get_api_key: checks env then DB, consistent with other services ✓

---

## Tasks

### Wave 1: Backend Parameter Fixes (2 parallel agents)

@@@task
# Task 1: Fix ugc_studio.py missing Request parameters

Add `request: Request` from fastapi to the 5 broken endpoint functions so get_org_id(request) works.

## Scope
- ONLY file: `backend/app/api/ugc_studio.py`
- Add `from fastapi import Request` if not already imported (it is — check line 7)
- Add `request: Request` parameter to these 5 functions:
  - `generate_video()` (line 619)
  - `check_generation_status()` (line 719)
  - `preview_prompt()` (line 785)
  - `templatize_video()` (line 954)
  - `templatize_competitor_post()` (line 1078)

## Definition of Done
- All 5 functions have `request: Request` in their signature
- No other functions are modified
- File parses without errors

## Verification
```bash
python3 -c "import ast; ast.parse(open('backend/app/api/ugc_studio.py').read()); print('OK')"
# Should print OK

python3 -c "
import ast
with open('backend/app/api/ugc_studio.py') as f: tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name in ('generate_video','check_generation_status','preview_prompt','templatize_video','templatize_competitor_post'):
        params = [a.arg for a in node.args.args]
        has_req = 'request' in params
        print(f'{node.name}: request param = {has_req}')
        assert has_req, f'{node.name} still missing request param!'
print('ALL PASS')
"
```
@@@

@@@task
# Task 2: Fix carousel.py parameter naming

Fix the 4 endpoints that reference `http_request` but have the param named `request`.

## Scope
- ONLY file: `backend/app/api/carousel.py`
- For each broken endpoint, rename the variable usage from `http_request` to match the actual param name, OR rename the param. Choose whichever is simpler.
- Endpoints to fix:
  - `generate_carousel()` (line 61) — param is `request`, code uses `http_request`
  - `generate_carousel_images()` (line 112) — same
  - `update_carousel()` (line 209) — same
  - `publish_carousel()` (line 269) — has both `request` (Pydantic) and `req` (Request), uses `http_request`
- Note: `publish_carousel` is special — it already has `req: Request` as a separate param. Fix it to use `req` instead of `http_request` for `get_org_id()`.
- For the other 3: add `http_request: Request` param OR rename `http_request` → `request` in the function body. Careful: `request` may shadow the Pydantic model param in `generate_carousel` and `generate_carousel_images`.

## Definition of Done
- All 4 endpoints can resolve `get_org_id()` without NameError
- File parses without errors

## Verification
```bash
python3 -c "import ast; ast.parse(open('backend/app/api/carousel.py').read()); print('OK')"

python3 -c "
import ast
with open('backend/app/api/carousel.py') as f: tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef):
        params = [a.arg for a in node.args.args]
        uses_undef = False
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id == 'http_request' and 'http_request' not in params:
                uses_undef = True
        if uses_undef:
            print(f'BUG: {node.name} still uses http_request without param')
        else:
            print(f'OK: {node.name}')
"
```
@@@

### Wave 2: Video Analysis MCP Fix + Frontend Integration (2 parallel agents)

@@@task
# Task 3: Fix video_analysis_service.py MCP integration

The service tries to POST to http://localhost:18796/mcp but no server runs there. @dymoo/media-understanding is an npm package with CLI/MCP tools. Fix the service to actually call the tool.

## Scope
- ONLY file: `backend/app/services/video_analysis_service.py`
- Replace the HTTP call in `_analyze_with_media_understanding()` with a subprocess call to the @dymoo/media-understanding CLI
- The npm package is installed at: `/home/eddy/Development/warroom/node_modules/@dymoo/media-understanding/`
- Check `node_modules/@dymoo/media-understanding/dist/cli.js` or `package.json` bin field for the CLI entry point
- The tool should accept a video file path and return analysis JSON
- Keep the same return structure so `_create_frame_chunks()` still works

## Inputs
- Check: `cat /home/eddy/Development/warroom/node_modules/@dymoo/media-understanding/package.json` for bin/main
- Check: The CLI help or README for command syntax

## Definition of Done
- `_analyze_with_media_understanding()` calls the actual tool (subprocess or MCP stdio)
- No reference to localhost:18796 remains
- File parses without errors
- Return structure compatible with `_create_frame_chunks()`

## Verification
```bash
python3 -c "import ast; ast.parse(open('backend/app/services/video_analysis_service.py').read()); print('OK')"
grep -c "localhost:18796" backend/app/services/video_analysis_service.py  # Should be 0
```
@@@

@@@task
# Task 4: Add frame analysis display to CompetitorIntel cards

Wire the frame_chunks and video_analysis data into the competitor intel UI. When a video post has been analyzed (analysis_status = 'completed'), show an indicator on the card and render the analysis in PostDetailModal.

## Scope
- Files: `frontend/src/components/intelligence/CompetitorIntel.tsx`, `frontend/src/components/intelligence/PostDetailModal.tsx`
- Add a visual indicator (badge/icon) on video post cards when `analysis_status === 'completed'`
- In PostDetailModal, add a new tab "Frame Analysis" that shows:
  - List of frame chunks with timestamps, descriptions, and VEO prompts
  - Overall video analysis summary
- The competitor API already returns these fields — check the GET endpoint response shape
- Another agent is simultaneously fixing backend parameter bugs — don't modify any backend files

## Inputs
- Backend returns: `frame_chunks` (JSON array of chunks), `video_analysis` (JSON object), `analysis_status`, `analyzed_at`
- Check `/api/competitors/videos/{post_id}/frames` endpoint in competitors.py (line 786)

## Definition of Done
- Video cards show analysis status indicator
- PostDetailModal has "Frame Analysis" tab when data exists
- Frame chunks render with timestamps and descriptions
- Frontend compiles: `cd frontend && npx tsc --noEmit`

## Verification
```bash
cd /home/eddy/Development/warroom/frontend && npx tsc --noEmit
```
@@@

### Wave 3: Verification + Docker Rebuild

Verifier agent reads all modified files, traces data flows, checks interfaces, runs AST/tsc checks. Then rebuild containers and test live.

---

## Acceptance Criteria
- [ ] All AI Studio endpoints respond without 500 errors (no NameError on `request`)
- [ ] Carousel create flow works end-to-end (text → slides → preview)
- [ ] Video analysis service can actually analyze a video file
- [ ] Competitor intel cards show frame analysis data when available
- [ ] `python3 -c "import ast; ast.parse(open(f).read())"` passes for all modified .py files
- [ ] `cd frontend && npx tsc --noEmit` passes

## Non-Goals
- Veo API billing/quota validation (Wave 3)
- Nano Banana image gen fixes (Wave 3)
- Multi-platform publish (Wave 4)
- Mirofish integration (Wave 5)

## Assumptions
- Google AI Studio API key is configured in DB settings
- @dymoo/media-understanding npm package is installed and functional
- PostgreSQL columns for frame analysis already exist (verified: they do)
- Carousel table exists (verified: it does)
