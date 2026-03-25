# socialRecycle — Master Wave Plan

## Completed
- **Wave 1:** ✅ Frame-by-frame MCP integration
- **Wave 2:** ✅ AI Studio + Competitor Intel bug fixes
- **Wave 3:** ✅ Scraper login + worker fix + Veo/Nano Banana API fixes
- **Wave 4:** ✅ ML comment analysis + content gaps + video topics
- **Wave 5:** ✅ Standalone media-understanding service + video analysis pipeline working

---

## Wave 6: Backend Decomposition — Monolith → Microservices (CURRENT)

### Goal
Break the 8.1GB backend monolith into focused microservices. Each service: small image, fast build, independent failure.

### Research Summary

**Current backend = 8.1GB:**
- nvidia/CUDA + torch + triton: 4.5GB (openai-whisper pulls all GPU libs)
- Playwright + Chromium: 883MB (two copies of playwright)
- scikit-learn + scipy: 158MB
- Core FastAPI + everything else: ~400MB

**Key finding:** The heavy services (scraper, ML, whisper) have ZERO internal app imports. They're already self-contained — just need HTTP wrappers.

### Target Architecture

| Service | Image | Size Est | Port | Contains |
|---------|-------|----------|------|----------|
| **backend** | python:3.12-slim | ~400MB | 8300 | FastAPI core, auth, DB, all API routes |
| **scraper** | mcr.microsoft.com/playwright/python | ~800MB | 18797 | instagram_scraper, comment_scraper, scrapling |
| **ml-pipeline** | python:3.12-slim + scikit-learn | ~300MB | 18798 | comment_analyzer + FastEmbed client |
| **media-understanding** | node:22-slim + ffmpeg | ~500MB | 18796 | Video frame analysis (DONE) |
| **frontend** | node:20-alpine | ~200MB | 3300 | Next.js (unchanged) |
| **worker** | python:3.12-slim | ~200MB | — | Arq tasks (unchanged) |

**Total: ~2.4GB across 6 containers vs 8.1GB in one.**

### Tasks

#### Wave 6A: Create scraper service (2 agents parallel)

@@@task
# Task 1: Create scraper HTTP service
**Agent:** Sonnet | **Est:** ~30 min

Build `services/scraper/` as a standalone FastAPI service wrapping instagram_scraper.py, comment_scraper.py, and scraping.py.

## Scope
- CREATE: `services/scraper/Dockerfile` (use mcr.microsoft.com/playwright/python:v1.49.0-jammy)
- CREATE: `services/scraper/requirements.txt` (playwright, scrapling, httpx, fastapi, uvicorn)
- CREATE: `services/scraper/main.py` — FastAPI app with endpoints:
  - `POST /scrape-profile` — scrape an Instagram profile
  - `POST /scrape-comments` — scrape comments from a post
  - `POST /follow` — follow an Instagram user
  - `GET /health`
- COPY: `instagram_scraper.py`, `comment_scraper.py`, `scraping.py` into services/scraper/
- Add to docker-compose.yml as `scraper` service on port 18797
- Mount instagram-cookies volume at /data

## Definition of Done
- Service starts and /health returns 200
- Dockerfile builds in < 2 minutes
- No Playwright imports in backend requirements.txt

## Verification
```bash
docker compose build scraper && docker compose up -d scraper
curl -s http://localhost:18797/health
```
@@@

@@@task
# Task 2: Create ML pipeline service
**Agent:** Sonnet | **Est:** ~20 min

Build `services/ml-pipeline/` as a standalone FastAPI service wrapping comment_analyzer.py.

## Scope
- CREATE: `services/ml-pipeline/Dockerfile` (python:3.12-slim + scikit-learn)
- CREATE: `services/ml-pipeline/requirements.txt` (scikit-learn, numpy, httpx, fastapi, uvicorn)
- CREATE: `services/ml-pipeline/main.py` — FastAPI app with endpoints:
  - `POST /analyze-comments` — run ML comment analysis
  - `GET /health`
- COPY: `comment_analyzer.py` into services/ml-pipeline/
- Add to docker-compose.yml as `ml-pipeline` service on port 18798
- The service calls FastEmbed at http://10.0.0.11:11435/api/embed (same as now)

## Definition of Done
- Service starts and /health returns 200
- comment_analyzer.py works when called via HTTP
- No scikit-learn in backend requirements.txt

## Verification
```bash
docker compose build ml-pipeline && docker compose up -d ml-pipeline
curl -s http://localhost:18798/health
```
@@@

#### Wave 6B: Rewire backend to call services via HTTP (1 agent)

@@@task
# Task 3: Update backend to call scraper + ML services via HTTP
**Agent:** Sonnet | **Est:** ~30 min

Replace direct imports of instagram_scraper, comment_scraper, comment_analyzer in the backend API routes with HTTP calls to the new services.

## Scope
- MODIFY: `backend/app/api/scraper.py` — call scraper service at localhost:18797
- MODIFY: `backend/app/api/competitors.py` — call scraper service for follow/sync
- MODIFY: `backend/app/api/content_intel.py` — call ML service at localhost:18798
- MODIFY: `backend/app/services/comment_scraper.py` — call ML service instead of direct import
- MODIFY: `backend/requirements.txt` — remove playwright, scrapling, scikit-learn
- DO NOT modify the service files themselves (they're copied to new services)

## Definition of Done
- Backend starts without importing playwright or scikit-learn
- API routes call services via httpx
- Fallback: if service is down, return error (don't crash)

## Verification
```bash
python3 -c "import ast; ast.parse(open('backend/app/api/scraper.py').read()); print('OK')"
python3 -c "import ast; ast.parse(open('backend/app/api/competitors.py').read()); print('OK')"
grep -c "playwright\|scrapling\|scikit" backend/requirements.txt  # Should be 0
```
@@@

#### Wave 6C: Strip Whisper from backend (1 agent)

@@@task
# Task 4: Remove Whisper/torch from backend
**Agent:** Sonnet | **Est:** ~15 min

Remove openai-whisper (and its 4.5GB of nvidia/torch/triton deps) from the backend Dockerfile. The video_transcriber already calls Whisper via TCP to an external service. voice.py edge-tts can stay (lightweight).

## Scope
- MODIFY: `backend/Dockerfile` — remove `openai-whisper` from pip install line
- MODIFY: `backend/app/api/voice.py` — remove any direct whisper import, use external service
- VERIFY: video_transcriber.py calls Whisper via TCP (already does, no changes needed)

## Definition of Done
- Backend builds without torch/nvidia (image should be ~1GB not 8GB)
- voice.py doesn't import whisper directly
- video_transcriber.py unchanged (already uses TCP)

## Verification
```bash
docker compose build backend
docker images warroom-backend --format "{{.Size}}"  # Should be < 2GB
```
@@@

#### Wave 6D: Verify + rebuild all (1 agent)

@@@task
# Task 5: Full verification + deploy
**Agent:** Sonnet | **Est:** ~15 min

Verify all services start, communicate, and the app works end-to-end.

## Verification checklist
- [ ] `docker compose up -d` — all services start
- [ ] Backend image < 2GB
- [ ] `curl localhost:8300/docs` — API docs load
- [ ] `curl localhost:18796/health` — media-understanding
- [ ] `curl localhost:18797/health` — scraper
- [ ] `curl localhost:18798/health` — ml-pipeline
- [ ] `curl localhost:3300` — frontend loads
- [ ] Backend logs show no import errors
- [ ] tsc --noEmit passes
- [ ] AST check all modified Python files
- [ ] Git commit all changes
@@@

---

## Wave 7: Production Deployment (DigitalOcean/Linode)
*After Wave 6 — deploy the microservices architecture*

## Outstanding Items
- Instagram CDN S3 download job (615 expired URLs → Garage)
- Education/library → SQLite to PostgreSQL migration
- Wire OpenClaw multi-agent config to War Room agent records
