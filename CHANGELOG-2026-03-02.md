# War Room — Session Log: 2026-03-02

Everything done this session, documented so we never repeat it.

---

## 1. Kanban Task Board — Delete + Detail Modal

**Commits:** `91cbc02`, part of `c1d0ef8`

**Problem:** Task cards could only be dragged between columns. No way to delete a card, no way to see full details.

**Changes (`frontend/src/components/kanban/KanbanPanel.tsx`):**

### Delete Button
- Added `Trash2` icon from lucide-react, visible on hover (same pattern as grip icon)
- `onClick` stops propagation (doesn't trigger modal), shows `window.confirm`
- Calls `DELETE /api/kanban/tasks/${taskId}`
- Fires best-effort agent kill: `DELETE /api/kanban/tasks/${taskId}/agent` (fire-and-forget, `.catch(() => {})`)
- Confirmation message warns that agent will also be stopped

### Detail Modal
- Click on card opens full-detail modal overlay
- **Click vs drag detection:** tracks `mouseDownPosition`, only opens modal if mouse moved < 5px between mousedown and mouseup
- Modal shows: title, description (full, not truncated), status, assignee, priority (colored badge), tags, created date, completed date
- Dark backdrop (`bg-black/50`), centered card, X close button
- Styled with existing `warroom-*` color classes
- `formatDate()` helper for readable timestamps

### State additions
- `selectedTask: Task | null` — controls modal
- `mouseDownPosition: { x, y } | null` — drag vs click detection

---

## 2. Voice Conversation Mode — Hard Kill Fix

**Commit:** `9254734`

**Problem:** Hitting the End button didn't fully stop conversation mode. TTS audio kept playing through headphones, and mic continued listening briefly after stop.

**Root cause:**
- VAD loop used a **local variable** `isListening` inside `startConversationMode()` — `stopConversationMode()` never had access to flip it, so the loop continued running until `cancelAnimationFrame` caught it (race window)
- TTS audio (`new Audio()`) was created without any reference, so there was no way to stop it mid-playback
- The `speakText` trigger in the WebSocket handler checked React state (`isConversationMode`) which could be stale in the closure

**Fix — new refs added:**
```typescript
const conversationActiveRef = useRef<boolean>(false);  // replaces local isListening
const currentAudioRef = useRef<HTMLAudioElement | null>(null);  // tracks playing audio
```

**Changes:**
- `startConversationMode()`: sets `conversationActiveRef.current = true`, VAD loop checks ref instead of local var
- `speakText()`: checks `conversationActiveRef.current` before fetching TTS and before playing; stores audio element in `currentAudioRef`
- WebSocket `final` handler: checks `conversationActiveRef.current` instead of `isConversationMode` state
- `stopConversationMode()` now does a **hard kill**:
  1. `conversationActiveRef.current = false` — VAD loop dies on next frame
  2. `cancelAnimationFrame(vadFrameRef.current)` — immediate frame kill
  3. `currentAudioRef.current.pause()` + `.src = ""` — kills any playing TTS audio
  4. `conversationStreamRef.current.getTracks().forEach(t => t.stop())` — kills mic
  5. `analyserRef.current = null` + `audioContextRef.current.close()` — cleans up Web Audio

---

## 3. TTS Audio Queue — No Overlapping Playback

**Commit:** `c1d0ef8`

**Problem:** Multiple TTS responses played simultaneously, overlapping each other. Each new response started immediately without waiting for the previous one to finish.

**Fix — audio queue system:**
```typescript
const audioQueueRef = useRef<(() => Promise<void>)[]>([]);
const audioPlayingRef = useRef<boolean>(false);
```

**How it works:**
- `speakText()` wraps each TTS fetch+play in a `playTask` async function and pushes it to the queue
- `processAudioQueue()` pops the next task, sets `audioPlayingRef = true`, awaits the play (using `onended` promise), then processes next
- Each audio element returns a Promise that resolves on `onended` or `onerror`
- `stopConversationMode()` clears the queue: `audioQueueRef.current = []` + `audioPlayingRef.current = false`

---

## 4. Memory System (FastEmbed) — Restored

**Not a code change — infrastructure fix on Brain 2 (10.0.0.11)**

**Problem:** `memory_recall` returning "Memory system offline" — all Qdrant-backed memory tools broken.

**Diagnosis:**
- Qdrant healthy on port 6333 (all collections intact)
- `fastembed-server` container exited cleanly (exit code 0) on 2026-02-27 ~10:29 PM EST
- Docker logs showed Garage health check failures and closed FIFOs around the same time — Docker instability likely sent a clean shutdown signal
- Restart policy was `unless-stopped` — once explicitly stopped, it stayed down

**Fix:**
```bash
ssh lowkeyshift@10.0.0.11 "docker start fastembed-server && docker update --restart always fastembed-server"
```

**Prevention:** Changed restart policy from `unless-stopped` to `always` — container will now auto-restart even after clean shutdowns or Docker daemon restarts.

**Verification:** `curl http://10.0.0.11:11435/health` → `{"status":"ok","model":"nomic-ai/nomic-embed-text-v1.5","ready":true}`

---

## 5. Stuff N Things — Copy Rewrite (Sub-Agent)

**Separate codebase:** `/home/eddy/Development/stuffnthings/`

Sub-agent rewrote all landing page copy across 9 components with tightened messaging:
- Core message: "We're your web team — not a design shop that builds and disappears"
- Pillars: ongoing partnership, verifiable Lighthouse scores, free friction audit hook, no contracts
- Copy only — no structural or styling changes
- Phase 2 (pending): visual/design cleanup based on UI/UX learnings

---

## Build Status

**⚠️ All frontend changes require a rebuild to take effect.**

The War Room runs as a production build. Changes are committed to git but NOT live until rebuilt:

```bash
cd /home/eddy/Development/warroom
docker compose build --no-cache frontend
docker compose up -d frontend
```

**Note from architecture doc:** If/when backend moves to Brain 2, rebuild with:
```bash
NEXT_PUBLIC_API_URL=http://10.0.0.11:8300 docker compose build --no-cache frontend
```
(URL is baked into JS at build time, not read at runtime)

---

## Commits This Session

| Hash | Description |
|------|-------------|
| `91cbc02` | feat: kanban delete + detail modal, voice/chat improvements |
| `9254734` | fix: hard kill on conversation mode stop |
| `c1d0ef8` | fix: queue TTS audio — finish one before playing next |
