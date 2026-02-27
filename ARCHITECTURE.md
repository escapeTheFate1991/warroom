# WAR ROOM — Architecture Document

## Overview

WAR ROOM is yieldlabs' mission-critical business dashboard. It consolidates team management, task tracking, knowledge management, lead generation, and AI chat into a single interface.

---

## ⚡ HARD RULE: Server Roles

| Brain | Host | Role | What Lives Here |
|-------|------|------|-----------------|
| **Brain 1** | Workstation (10.0.0.1) | **UI + Gateway** | OpenClaw, app frontends, internet access, routing |
| **Brain 2** | Server 1 / Enforcement (10.0.0.11) | **App Backends** | API servers, databases, app services |
| **Brain 3** | Server 2 (10.0.0.12) | **AI Infrastructure** | Vector DB, embeddings, skill network, AI models |

**No exceptions.** All new services follow this rule. Existing services will be migrated.

---

## Target Architecture (after migration)

```
┌─────────────────────────────────────────────────────────┐
│  Brain 1 — Workstation (10.0.0.1)                       │
│  ROLE: UI + Gateway                                     │
│                                                         │
│  ┌──────────────────┐                                   │
│  │ WAR ROOM Frontend │  Port 3300                       │
│  │ Next.js (Docker)  │                                  │
│  └──────────────────┘                                   │
│  ┌──────────────────┐                                   │
│  │ AI Marketing Web  │  Port 3002 (future: frontend only)│
│  └──────────────────┘                                   │
│  ┌──────────────────┐                                   │
│  │ OpenClaw Gateway  │  Port 18789                      │
│  └──────────────────┘                                   │
│  • router-dnsmasq (DNS/routing)                         │
│  • traefik (reverse proxy)                              │
└─────────────────────────────────────────────────────────┘
                        │
                   LAN 10.0.0.x
                        │
┌─────────────────────────────────────────────────────────┐
│  Brain 2 — Server 1 / Enforcement (10.0.0.11)           │
│  ROLE: App Backends & Services                          │
│                                                         │
│  ┌──────────────────────────────────────────┐           │
│  │  WAR ROOM Backend (FastAPI)    :8300     │           │
│  │  Mental Library Backend        :8100     │           │
│  │  Kanban API                    :18794    │           │
│  │  Team Dashboard API            :18795    │           │
│  │  PostgreSQL (knowledge)        :5433     │           │
│  │  PostgreSQL (leadgen)          :5434     │           │
│  │  Redis                         :6379     │           │
│  │  Garage S3                     :3900     │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────────────┐
│  Brain 3 — Server 2 (10.0.0.12)                         │
│  ROLE: AI Infrastructure                                │
│                                                         │
│  ┌──────────────────────────────────────────┐           │
│  │  Qdrant (vector DB)            :6333     │           │
│  │  FastEmbed (embeddings)        :11435    │           │
│  │  Whisper STT Server            :8200     │           │
│  │  Garage S3 Replica             :3900     │           │
│  │  (Future: Qwen3-30B, LoRA)              │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## WAR ROOM Services

### Frontend (Brain 1)
- **Container:** `warroom-frontend-1`
- **Tech:** Next.js 14, React 18, Tailwind CSS, TypeScript
- **Port:** 3300 → 3000
- **Compose:** `~/Development/warroom/docker-compose.yml`
- **Build args (baked into JS at build time):**
  - `NEXT_PUBLIC_API_URL=http://10.0.0.11:8300`
  - `NEXT_PUBLIC_WS_URL=ws://10.0.0.1:18789`

### Backend (Brain 2, host network)
- **Container:** `warroom-backend`
- **Tech:** Python FastAPI, uvicorn
- **Port:** 8300
- **Network:** host mode (direct access to Brain 2 local services + Brain 3 AI)
- **Compose:** `~/warroom/docker-compose.yml` on Brain 2 (`lowkeyshift@10.0.0.11`)
- **Source sync:** `rsync` from Brain 1 `~/Development/warroom/backend/` → Brain 2 `~/warroom/backend/`
- **Volumes:**
  - Mental Library SQLite: `/home/lowkeyshift/warroom/mental-library-data:/data/mental-library:ro`

### Mental Library Backend (Brain 2, host network)
- **Container:** `mental-library-backend`
- **Tech:** Python FastAPI, spaCy, pipeline processing
- **Port:** 8100
- **Compose:** Same as backend (`~/warroom/docker-compose.yml` on Brain 2)
- **Volumes:**
  - Mental Library data: `/home/lowkeyshift/warroom/mental-library-data:/app/data`

### Backend API Routes

| Route | Proxies To | Service | Server (target) |
|-------|-----------|---------|----------------|
| `/health` | Multi-check | All service health | Brain 2 |
| `/api/kanban/*` | `:18794` | Kanban task board | Brain 2 |
| `/api/team/*` | `:18795` | Team dashboard (agents, events, flows, stats) | Brain 2 |
| `/api/library/collections` | `:6333` | Qdrant vector collections | Brain 3 ✅ |
| `/api/library/search` | `:6333` + `:11435` | Semantic search (embed → query) | Brain 3 ✅ |
| `/api/ml/videos` | SQLite | Mental Library videos | Brain 2 ✅ |
| `/api/ml/videos/:id` | SQLite | Video detail + chunks | Brain 2 ✅ |
| `/api/ml/stats` | SQLite | Video/chunk counts | Brain 2 ✅ |
| `/api/leadgen/*` | `:8200` | Lead gen scraper | Brain 1 (stays — DB on Brain 1) |
| `/api/chat/ws` | `:18789` | OpenClaw WebSocket relay | Brain 1 (stays) |
| `/api/voice/transcribe` | Whisper socket | Speech-to-text | 🔜 Brain 3 (not migrated yet) |
| `/api/voice/tts` | `edge-tts` CLI | Text-to-speech (MP3 stream) | Brain 2 ✅ |
| `/api/voice/tts/play` | `edge-tts` + Bose | TTS on physical speaker | Brain 1 (hardware) |

### Frontend Config (CRITICAL)

`NEXT_PUBLIC_API_URL` is baked into the JS bundle at build time. It must point to wherever the backend runs:
- **Current:** `http://10.0.0.11:8300` (backend on Brain 2) ✅

When backend moves, **rebuild frontend:** `docker compose build --no-cache frontend`

---

---

## Migration Plan (Current → Target)

### ✅ Already Correct
| Service | Currently | Target | Status |
|---------|-----------|--------|--------|
| WAR ROOM Frontend | Brain 1 :3300 | Brain 1 :3300 | ✅ Done |
| OpenClaw Gateway | Brain 1 :18789 | Brain 1 :18789 | ✅ Done |
| Kanban API | Brain 2 :18794 | Brain 2 :18794 | ✅ Done |
| Team Dashboard | Brain 2 :18795 | Brain 2 :18795 | ✅ Done |
| PostgreSQL (knowledge) | Brain 2 :5433 | Brain 2 :5433 | ✅ Done |
| Garage S3 | Brain 2 :3900 | Brain 2 :3900 | ✅ Done |
| router-dnsmasq | Brain 1 | Brain 1 | ✅ Done |

### 🔄 Brain 1 → Brain 2 (backends/services)
| Service | From | To | Status |
|---------|------|----|--------|
| WAR ROOM Backend | Brain 1 :8300 | Brain 2 :8300 | ✅ **DONE** (2026-02-26) |
| Mental Library Backend | Brain 1 :8100 | Brain 2 :8100 | ✅ **DONE** (2026-02-26) |
| LeadGen App Backend | Brain 1 :8200 | Brain 2 :8200 | 🔜 Not started (DB stays Brain 1) |
| ai-marketing-postgres | Brain 1 :5432 | Brain 2 :5432 | 🔜 Not started |
| ai-marketing-redis | Brain 1 :6379 | Brain 2 :6379 | 🔜 Not started |

### Brain 2 → Brain 3 (AI infrastructure)
| Service | From | To | Status |
|---------|------|----|--------|
| Qdrant | Brain 2 :6333 | Brain 3 :6333 | ✅ **DONE** — old Brain 2 instance stopped |
| FastEmbed | Brain 2 :11435 | Brain 3 :11435 | ✅ **DONE** — old Brain 2 instance stopped |
| Whisper STT | Brain 1 (process) | Brain 3 :8200 | 🔜 Not started |
| Garage S3 Replica | — | Brain 3 :3900 | ✅ Already running on Brain 3 |

### ✅ Cleanup Completed (2026-02-26)
- ✅ Old Qdrant + FastEmbed stopped on Brain 2
- ✅ Old mental-library-backend removed from Brain 1
- ✅ Old warroom-backend removed from Brain 1
- ✅ Frontend rebuilt with `NEXT_PUBLIC_API_URL=http://10.0.0.11:8300`

### Remaining Cleanup
- LeadGen Postgres stays on Brain 1 (:5434) — Eddy's decision
- ai-marketing-postgres/redis → Brain 2 (lower priority)
- Whisper STT → Brain 3 (lower priority)

### Brain 1 Exceptions (stay by design)
| Container | Reason |
|-----------|--------|
| `hummingbot_v7` | Eddy is testing |
| `ai-marketing-ngrok` | Frontend testing |
| `garage-ui` | It's a frontend — belongs on Brain 1 |

---

## Current State (post-migration, 2026-02-26)

### Brain 1 Containers (10.0.0.1)
| Container | Port | Role |
|-----------|------|------|
| `warroom-frontend-1` | 3300 | WAR ROOM UI |
| `leadgen-app-db-1` | 5434 | LeadGen PostgreSQL |
| `ai-marketing-web` | 3002 | Marketing frontend |
| `ai-marketing-postgres` | 5432 | Marketing DB (→ Brain 2 later) |
| `ai-marketing-redis` | 6379 | Marketing cache (→ Brain 2 later) |
| `ai-marketing-traefik` | 80/8080 | Reverse proxy |
| `ai-marketing-ngrok` | 4040 | Frontend testing tunnel |
| `router-dnsmasq` | — | DNS/routing |
| `garage-ui` | — | S3 frontend |
| `hummingbot_v7` | — | Trading bot (testing) |

### Brain 2 Containers (10.0.0.11)
| Container | Port | Role |
|-----------|------|------|
| `warroom-backend` | 8300 | WAR ROOM API (host network) |
| `mental-library-backend` | 8100 | Video pipeline (host network) |
| `kanban-api` | 18794 | Task API |
| `team-dashboard` | 18795 | Agent API |
| `brain2-postgres` | 5433 | Knowledge DB |
| `garage` | 3900 | S3 storage |
| `nginx-proxy` | 80/443 | Reverse proxy |

### Brain 3 Containers (10.0.0.12)
| Container | Port | Role |
|-----------|------|------|
| `qdrant` | 6333 | Vector DB |
| `fastembed-server` | 11435 | Embedding server |
| `garage` | 3900 | S3 replica |

---

## Data Locations

| Data | Location |
|------|----------|
| Mental Library SQLite + audio + FAISS | Brain 2: `~/warroom/mental-library-data/` |
| Mental Library source (Brain 1 copy) | Brain 1: `~/.openclaw/workspace/skills/mental-library/backend/data/` |
| LeadGen DB | Brain 1: PostgreSQL :5434 |
| Knowledge DB | Brain 2: PostgreSQL :5433 |
| Vector embeddings (7 collections) | Brain 3: Qdrant :6333 |
| Embedding models | Brain 3: FastEmbed :11435 |
| Whisper model | Brain 1: `skills/voice-io/.venv/` (→ Brain 3 later) |
| Skills/workspace | Brain 1: `~/.openclaw/workspace/skills/` |
| S3 objects | Brain 2 + Brain 3: Garage :3900 (replicated) |
