# Multi-Agent Setup Guide — War Room × OpenClaw × Network-AI

## Architecture

```
War Room UI (Agents page)
    ↓ CRUD via /api/agents
PostgreSQL (agents table)
    ↓ openclaw_agent_id links to
OpenClaw Multi-Agent (openclaw agents)
    ↓ Orchestrated by
Network-AI (shared blackboard, guardrails, budgets)
    ↓ Tasks dispatched from
Kanban Board (priority-ordered queue)
```

## Current State

- **War Room agents DB:** ✅ Created (agents + agent_task_assignments tables)
- **Agent CRUD UI:** ✅ Built (create/edit/delete with skill assignment)
- **Network-AI skill:** ✅ Installed at `skills/network-ai/`
- **OpenClaw multi-agent:** 🔲 Only `main` agent exists

## Step 1: Create OpenClaw Agents

For each permanent War Room agent, create a matching OpenClaw agent:

```bash
# Example: create a developer agent
openclaw agents add dev-agent

# Example: create a copywriter agent  
openclaw agents add copy-agent
```

Each gets its own:
- Workspace: `~/.openclaw/workspace-<agentId>`
- Agent dir: `~/.openclaw/agents/<agentId>/agent`
- Session store: `~/.openclaw/agents/<agentId>/sessions`
- SOUL.md with role-specific personality

## Step 2: Configure Agent Workspaces

Each agent workspace needs:
- `SOUL.md` — Agent personality and specialization
- `AGENTS.md` — Agent-specific instructions
- `skills/` — Symlink or copy of assigned skills

## Step 3: Set Up Bindings

Route War Room chat sessions to specific agents:

```json5
// openclaw.json
{
  "agents": {
    "list": [
      { "id": "main", "workspace": "~/.openclaw/workspace" },
      { "id": "dev-agent", "workspace": "~/.openclaw/workspace-dev-agent" },
      { "id": "copy-agent", "workspace": "~/.openclaw/workspace-copy-agent" }
    ]
  },
  "bindings": [
    // War Room chat routes to main by default
    // Specific task dispatch goes through API
  ]
}
```

## Step 4: Wire War Room → OpenClaw

The War Room backend needs an endpoint to dispatch tasks to specific agents:

```python
# Backend: POST /api/agents/{id}/dispatch
# 1. Look up agent's openclaw_agent_id
# 2. Create a session on that agent via OpenClaw API
# 3. Send the task message to that session
# 4. Stream results back to the kanban board
```

## Step 5: Network-AI Orchestration

For multi-agent collaboration on complex tasks:

```typescript
import { createSwarmOrchestrator } from 'network-ai';

const swarm = createSwarmOrchestrator({
  agents: [
    { id: 'dev', adapter: 'openclaw', config: { agentId: 'dev-agent' } },
    { id: 'copy', adapter: 'openclaw', config: { agentId: 'copy-agent' } },
  ],
  blackboard: { backend: 'memory' }, // or 'file' for persistence
  budget: { maxTokensPerAgent: 100000 },
});
```

## Step 6: Kanban → Agent Task Pipeline

1. User assigns task to agent on kanban board (drag to agent column or assign via dropdown)
2. Backend creates `agent_task_assignments` record with priority
3. Agent picks up highest-priority queued task
4. Progress updates flow back to kanban card
5. Completion updates task status

## Security Notes

- Each agent has isolated auth profiles — `main` credentials NOT shared
- If agents need API access, copy `auth-profiles.json` to their agent dir
- Network-AI provides HMAC audit logging for all agent actions
- AuthGuardian gating prevents scope escalation

## Gateway Restart Required

After adding agents to `openclaw.json`, restart is needed:
```bash
openclaw gateway restart
```

⚠️ **Do not run this without Eddy's approval** — per SOUL.md self-modification rules.
