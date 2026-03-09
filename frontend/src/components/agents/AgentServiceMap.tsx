"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  X,
  Cpu,
  Clock,
  CheckCircle,
  Loader2,
  ChevronRight,
  Activity,
  LayoutGrid,
  Network,
  ArrowRight,
  Timer,
  Hash,
  RefreshCw,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

const TEAM_API = "/api/team";
const POLL_INTERVAL = 15_000;

/* ─── Types ─────────────────────────────────────────────────────── */

interface AgentData {
  id: string;
  name: string;
  emoji: string;
  role: string;
  model: string;
  color: string;
}

interface EventData {
  event_type: string;
  from_agent: string;
  to_agent: string;
  summary: string;
  timestamp: string;
  metadata?: { session_key?: string; label?: string; duration?: number };
}

type AgentStatus = "working" | "idle";

interface DerivedAgent extends AgentData {
  status: AgentStatus;
  currentTask: string | null;
  lastActive: string | null;
  taskCount: number;
  activeTasks: EventData[];
  history: { event: EventData; spawn: EventData; durationMs: number }[];
  pipelineTo: string[];
  pipelineFrom: string[];
}

/* ─── Friday (always present, even if API doesn't list it) ────── */

const FRIDAY_AGENT: AgentData = {
  id: "friday",
  name: "Friday",
  emoji: "🖤",
  role: "Orchestrator",
  model: "claude-opus",
  color: "#6366f1",
};

/* ─── Helpers ───────────────────────────────────────────────────── */

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 0) return "just now";
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  return `${d}d ago`;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return "<1s";
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const rem = sec % 60;
  if (min < 60) return rem > 0 ? `${min}m ${rem}s` : `${min}m`;
  const hr = Math.floor(min / 60);
  return `${hr}h ${min % 60}m`;
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

function normalizeTeamAgents(payload: any): AgentData[] {
  const rawAgents = Array.isArray(payload?.agents)
    ? payload.agents
    : Array.isArray(payload)
      ? payload
      : [];

  return rawAgents
    .filter(Boolean)
    .map((agent: any) => ({
      id: String(agent?.id || agent?.name || "unknown"),
      name: String(agent?.name || agent?.id || "Unknown Agent"),
      emoji: agent?.emoji || "🤖",
      role: agent?.role || "Agent",
      model: agent?.model || "unknown",
      color: agent?.color || "#6366f1",
    }));
}

function normalizeTeamEvents(payload: any): EventData[] {
  const rawEvents = Array.isArray(payload?.events)
    ? payload.events
    : Array.isArray(payload)
      ? payload
      : [];

  return rawEvents.map((event: any) => ({
    event_type: event?.event_type || "unknown",
    from_agent: event?.from_agent || "unknown",
    to_agent: event?.to_agent || "unknown",
    summary: event?.summary || "",
    timestamp: event?.timestamp || event?.created_at || new Date().toISOString(),
    metadata: event?.metadata,
  }));
}

/* ─── Derive agent state from raw API + events ──────────────────── */

function deriveAgents(
  rawAgents: AgentData[],
  events: EventData[]
): DerivedAgent[] {
  // Ensure Friday is included
  const agentMap = new Map<string, AgentData>();
  agentMap.set(FRIDAY_AGENT.id, FRIDAY_AGENT);
  for (const a of rawAgents) agentMap.set(a.id, a);

  const result: DerivedAgent[] = [];

  for (const agent of Array.from(agentMap.values())) {
    const agentEvents = events.filter(
      (e) => e.from_agent === agent.id || e.to_agent === agent.id
    );

    // Match spawns to completes by session_key
    const spawns = agentEvents.filter((e) => e.event_type === "spawn");
    const completes = agentEvents.filter((e) => e.event_type === "complete");

    const completedKeysArr = completes
      .map((e) => e.metadata?.session_key)
      .filter((k): k is string => !!k);
    const completedKeys = new Set(completedKeysArr);

    // Filter active tasks — exclude completed AND stale (>2h old)
    const STALE_MS = 2 * 60 * 60 * 1000; // 2 hours
    const now = Date.now();
    const activeTasks = spawns.filter(
      (s) =>
        s.metadata?.session_key &&
        !completedKeys.has(s.metadata.session_key) &&
        now - new Date(s.timestamp).getTime() < STALE_MS
    );

    // Build history: match complete → spawn by session_key
    const spawnByKey = new Map<string, EventData>();
    for (const s of spawns) {
      if (s.metadata?.session_key) spawnByKey.set(s.metadata.session_key, s);
    }

    const history: { event: EventData; spawn: EventData; durationMs: number }[] = [];
    for (const c of completes) {
      const key = c.metadata?.session_key;
      const spawn = key ? spawnByKey.get(key) : undefined;
      if (spawn) {
        const durationMs =
          c.metadata?.duration ??
          new Date(c.timestamp).getTime() - new Date(spawn.timestamp).getTime();
        history.push({ event: c, spawn, durationMs });
      }
    }
    history.sort(
      (a, b) =>
        new Date(b.event.timestamp).getTime() -
        new Date(a.event.timestamp).getTime()
    );

    // Pipeline relationships
    const pipelineToSet = new Set(
      events
        .filter((e) => e.from_agent === agent.id && e.to_agent !== agent.id)
        .map((e) => e.to_agent)
    );
    const pipelineTo = Array.from(pipelineToSet);
    const pipelineFromSet = new Set(
      events
        .filter((e) => e.to_agent === agent.id && e.from_agent !== agent.id)
        .map((e) => e.from_agent)
    );
    const pipelineFrom = Array.from(pipelineFromSet);

    // Last active = most recent event timestamp involving this agent
    const sorted = agentEvents.sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
    const lastActive = sorted[0]?.timestamp ?? null;

    const status: AgentStatus = activeTasks.length > 0 ? "working" : "idle";
    const currentTask =
      activeTasks.length > 0 ? activeTasks[0].summary : null;

    result.push({
      ...agent,
      status,
      currentTask,
      lastActive,
      taskCount: completes.length,
      activeTasks,
      history,
      pipelineTo,
      pipelineFrom,
    });
  }

  // Sort: working first, then by task count desc
  result.sort((a, b) => {
    if (a.id === "friday") return -1;
    if (b.id === "friday") return 1;
    if (a.status !== b.status) return a.status === "working" ? -1 : 1;
    return b.taskCount - a.taskCount;
  });

  return result;
}

/* ─── Status Badge ──────────────────────────────────────────────── */

function StatusBadge({ status }: { status: AgentStatus }) {
  if (status === "working") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-500/15 text-green-400">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
        </span>
        Working
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-500/15 text-gray-400">
      <span className="h-2 w-2 rounded-full bg-gray-500" />
      Idle
    </span>
  );
}

/* ─── Indeterminate Progress Bar ────────────────────────────────── */

function IndeterminateBar() {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes wr-indeterminate {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(350%); }
        }
      `}} />
      <div className="h-1 bg-warroom-border rounded-full overflow-hidden">
        <div
          className="h-full bg-warroom-accent rounded-full"
          style={{
            width: "40%",
            animation: "wr-indeterminate 1.5s ease-in-out infinite",
          }}
        />
      </div>
    </>
  );
}

/* ─── Agent Card ────────────────────────────────────────────────── */

function AgentCard({
  agent,
  isSelected,
  onClick,
}: {
  agent: DerivedAgent;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border p-4 transition-all duration-200 hover:border-warroom-accent/40 hover:bg-warroom-accent/5 ${
        isSelected
          ? "border-warroom-accent bg-warroom-accent/10 ring-1 ring-warroom-accent/20"
          : "border-warroom-border bg-warroom-surface"
      }`}
    >
      {/* Top row: emoji + name + status */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl leading-none">{agent.emoji}</span>
          <div>
            <h3 className="text-sm font-semibold text-warroom-text">
              {agent.name}
            </h3>
            <p className="text-[11px] text-warroom-muted">{agent.role}</p>
          </div>
        </div>
        <StatusBadge status={agent.status} />
      </div>

      {/* Current task or idle message */}
      {agent.currentTask ? (
        <div className="mt-2 mb-2">
          <p className="text-xs text-warroom-text/80 line-clamp-2">
            {truncate(agent.currentTask, 80)}
          </p>
          <div className="mt-1.5">
            <IndeterminateBar />
          </div>
        </div>
      ) : (
        <p className="text-xs text-warroom-muted/60 mt-2 mb-2 italic">
          No active tasks
        </p>
      )}

      {/* Bottom row: model + last active + task count */}
      <div className="flex items-center gap-3 text-[10px] text-warroom-muted mt-1">
        <span className="flex items-center gap-1">
          <Cpu size={10} /> {agent.model}
        </span>
        {agent.lastActive && (
          <span className="flex items-center gap-1">
            <Clock size={10} /> {timeAgo(agent.lastActive)}
          </span>
        )}
        <span className="flex items-center gap-1 ml-auto">
          <CheckCircle size={10} /> {agent.taskCount}
        </span>
      </div>
    </button>
  );
}

/* ─── Detail Sidebar ────────────────────────────────────────────── */

function DetailSidebar({
  agent,
  allAgents,
  onClose,
}: {
  agent: DerivedAgent;
  allAgents: DerivedAgent[];
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"active" | "history">("active");

  const avgDuration = useMemo(() => {
    if (agent.history.length === 0) return null;
    const total = agent.history.reduce((sum, h) => sum + h.durationMs, 0);
    return formatDuration(total / agent.history.length);
  }, [agent.history]);

  const findAgent = (id: string) => allAgents.find((a) => a.id === id);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-3 sm:p-5 border-b border-warroom-border flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-2xl leading-none">{agent.emoji}</span>
            <div className="min-w-0">
              <h3 className="font-semibold text-base text-warroom-text truncate">
                {agent.name}
              </h3>
              <p className="text-[11px] text-warroom-muted">{agent.role}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-warroom-muted hover:text-warroom-text transition-colors p-1.5 rounded-lg hover:bg-warroom-border/50 flex-shrink-0"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex gap-1.5 flex-wrap">
          <StatusBadge status={agent.status} />
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-warroom-accent/10 text-warroom-accent truncate max-w-[200px]">
            <Cpu size={10} className="flex-shrink-0" /> {agent.model}
          </span>
        </div>
      </div>

      {/* Progress */}
      {agent.status === "working" && agent.currentTask && (
        <div className="px-3 sm:px-5 py-3 border-b border-warroom-border flex-shrink-0">
          <p className="text-[11px] text-warroom-muted font-medium mb-1">
            Current Task
          </p>
          <p className="text-xs text-warroom-text mb-2 leading-relaxed">
            {truncate(agent.currentTask, 120)}
          </p>
          <IndeterminateBar />
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-1 px-3 sm:px-5 py-3 border-b border-warroom-border flex-shrink-0">
        <div className="text-center min-w-0">
          <p className="text-base font-bold text-warroom-text">
            {agent.taskCount}
          </p>
          <p className="text-[9px] text-warroom-muted">Completed</p>
        </div>
        <div className="text-center min-w-0">
          <p className="text-base font-bold text-warroom-text truncate px-1">
            {avgDuration ?? "—"}
          </p>
          <p className="text-[9px] text-warroom-muted">Avg Time</p>
        </div>
        <div className="text-center min-w-0">
          <p className="text-base font-bold text-warroom-text truncate px-1">
            {agent.lastActive ? timeAgo(agent.lastActive) : "—"}
          </p>
          <p className="text-[9px] text-warroom-muted">Last Active</p>
        </div>
      </div>

      {/* Pipeline */}
      {(agent.pipelineTo.length > 0 || agent.pipelineFrom.length > 0) && (
        <div className="px-5 py-3 border-b border-warroom-border flex-shrink-0">
          <p className="text-xs text-warroom-muted font-medium mb-2">
            Pipeline
          </p>
          <div className="space-y-1.5">
            {agent.pipelineFrom.map((id) => {
              const src = findAgent(id);
              return src ? (
                <div
                  key={`from-${id}`}
                  className="flex items-center gap-2 text-xs"
                >
                  <span className="px-2 py-0.5 bg-warroom-bg border border-warroom-border rounded text-warroom-muted">
                    {src.emoji} {src.name}
                  </span>
                  <ArrowRight size={12} className="text-warroom-muted" />
                  <span className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded font-medium">
                    {agent.emoji} {agent.name}
                  </span>
                </div>
              ) : null;
            })}
            {agent.pipelineTo.map((id) => {
              const dst = findAgent(id);
              return dst ? (
                <div
                  key={`to-${id}`}
                  className="flex items-center gap-2 text-xs"
                >
                  <span className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded font-medium">
                    {agent.emoji} {agent.name}
                  </span>
                  <ArrowRight size={12} className="text-warroom-muted" />
                  <span className="px-2 py-0.5 bg-warroom-bg border border-warroom-border rounded text-warroom-muted">
                    {dst.emoji} {dst.name}
                  </span>
                </div>
              ) : null;
            })}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-warroom-border flex-shrink-0">
        <button
          onClick={() => setTab("active")}
          className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
            tab === "active"
              ? "text-warroom-accent border-b-2 border-warroom-accent"
              : "text-warroom-muted hover:text-warroom-text"
          }`}
        >
          Active Tasks ({agent.activeTasks.length})
        </button>
        <button
          onClick={() => setTab("history")}
          className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
            tab === "history"
              ? "text-warroom-accent border-b-2 border-warroom-accent"
              : "text-warroom-muted hover:text-warroom-text"
          }`}
        >
          History ({agent.history.length})
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {tab === "active" && (
          <>
            {agent.activeTasks.length === 0 && (
              <p className="text-xs text-warroom-muted/60 italic text-center py-6">
                No active tasks
              </p>
            )}
            {agent.activeTasks.map((t, i) => (
              <div
                key={t.metadata?.session_key ?? i}
                className="bg-warroom-bg border border-warroom-border rounded-lg p-3"
              >
                <p className="text-xs text-warroom-text">
                  {truncate(t.summary, 120)}
                </p>
                <div className="flex items-center gap-3 mt-1.5 text-[10px] text-warroom-muted">
                  <span className="flex items-center gap-1">
                    <Timer size={10} /> {timeAgo(t.timestamp)}
                  </span>
                  {t.from_agent && (
                    <span className="flex items-center gap-1">
                      <ChevronRight size={10} /> from{" "}
                      {findAgent(t.from_agent)?.name ?? t.from_agent}
                    </span>
                  )}
                </div>
                <div className="mt-2">
                  <IndeterminateBar />
                </div>
              </div>
            ))}
          </>
        )}
        {tab === "history" && (
          <>
            {agent.history.length === 0 && (
              <p className="text-xs text-warroom-muted/60 italic text-center py-6">
                No completed tasks
              </p>
            )}
            {agent.history.map((h, i) => (
              <div
                key={h.event.metadata?.session_key ?? i}
                className="bg-warroom-bg border border-warroom-border rounded-lg p-3"
              >
                <p className="text-xs text-warroom-text">
                  {truncate(h.event.summary, 120)}
                </p>
                <div className="flex items-center gap-3 mt-1.5 text-[10px] text-warroom-muted flex-wrap">
                  <span className="flex items-center gap-1">
                    <Clock size={10} /> {formatDuration(h.durationMs)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Timer size={10} /> {timeAgo(h.event.timestamp)}
                  </span>
                  {h.spawn.from_agent && h.event.to_agent && (
                    <span className="flex items-center gap-1">
                      {findAgent(h.spawn.from_agent)?.emoji ?? "?"}{" "}
                      <ArrowRight size={10} />{" "}
                      {findAgent(h.event.to_agent)?.emoji ?? "?"}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

/* ─── Service Map (SVG) ─────────────────────────────────────────── */

function ServiceMapView({
  agents,
  events,
  selectedId,
  onSelect,
}: {
  agents: DerivedAgent[];
  events: EventData[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  // Position agents in hub layout — Friday center, others in a circle
  const positions = useMemo(() => {
    const pos = new Map<string, { x: number; y: number }>();
    const others = agents.filter((a) => a.id !== "friday");
    const cx = 50,
      cy = 50,
      r = 32;
    pos.set("friday", { x: cx, y: cy });
    others.forEach((a, i) => {
      const angle = (2 * Math.PI * i) / others.length - Math.PI / 2;
      pos.set(a.id, {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      });
    });
    return pos;
  }, [agents]);

  // Build connections from events
  const connections = useMemo(() => {
    const pairs = new Set<string>();
    const conns: { from: string; to: string }[] = [];
    for (const e of events) {
      const key = [e.from_agent, e.to_agent].sort().join("-");
      if (!pairs.has(key) && positions.has(e.from_agent) && positions.has(e.to_agent)) {
        pairs.add(key);
        conns.push({ from: e.from_agent, to: e.to_agent });
      }
    }
    // Always connect Friday to everyone if no events
    if (conns.length === 0) {
      for (const a of agents) {
        if (a.id !== "friday") conns.push({ from: "friday", to: a.id });
      }
    }
    return conns;
  }, [events, agents, positions]);

  // Recent handoffs (last 5 min)
  const recentHandoffs = useMemo(() => {
    const cutoff = Date.now() - 5 * 60 * 1000;
    return new Set(
      events
        .filter((e) => new Date(e.timestamp).getTime() > cutoff)
        .map((e) => [e.from_agent, e.to_agent].sort().join("-"))
    );
  }, [events]);

  return (
    <div className="w-full h-full relative">
      <div
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage:
            "radial-gradient(circle, #6366f1 1px, transparent 1px)",
          backgroundSize: "30px 30px",
        }}
      />
      <svg
        className="w-full h-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <filter id="glow-green">
            <feGaussianBlur stdDeviation="1" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-accent">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Connections */}
        {connections.map((conn) => {
          const from = positions.get(conn.from)!;
          const to = positions.get(conn.to)!;
          const key = [conn.from, conn.to].sort().join("-");
          const isActive = recentHandoffs.has(key);
          const isHighlighted =
            hovered === conn.from ||
            hovered === conn.to ||
            selectedId === conn.from ||
            selectedId === conn.to;

          return (
            <g key={key}>
              <line
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={
                  isActive
                    ? "#6366f1"
                    : isHighlighted
                    ? "#4b5563"
                    : "#1e2030"
                }
                strokeWidth={isActive ? 0.4 : 0.2}
                strokeDasharray={isActive ? "1 1" : "none"}
                opacity={isHighlighted || isActive ? 1 : 0.5}
              >
                {isActive && (
                  <animate
                    attributeName="stroke-dashoffset"
                    from="10"
                    to="0"
                    dur="2s"
                    repeatCount="indefinite"
                  />
                )}
              </line>
            </g>
          );
        })}

        {/* Agent Nodes */}
        {agents.map((agent) => {
          const pos = positions.get(agent.id);
          if (!pos) return null;
          const isFriday = agent.id === "friday";
          const isSelected = selectedId === agent.id;
          const isHovered = hovered === agent.id;
          const isWorking = agent.status === "working";
          const r = isFriday ? 6 : 4.5;
          const ringColor = isWorking ? "#22c55e" : "#64748b";

          return (
            <g
              key={agent.id}
              onClick={() =>
                onSelect(isSelected ? null : agent.id)
              }
              onMouseEnter={() => setHovered(agent.id)}
              onMouseLeave={() => setHovered(null)}
              className="cursor-pointer"
            >
              {/* Pulse ring for working / selected */}
              {(isWorking || isSelected) && (
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 1.5}
                  fill="none"
                  stroke={isSelected ? "#6366f1" : ringColor}
                  strokeWidth="0.3"
                  opacity="0.4"
                >
                  <animate
                    attributeName="r"
                    values={`${r + 1};${r + 2.5};${r + 1}`}
                    dur="3s"
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    values="0.4;0.1;0.4"
                    dur="3s"
                    repeatCount="indefinite"
                  />
                </circle>
              )}

              {/* Node circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill="#12121a"
                stroke={
                  isSelected
                    ? "#6366f1"
                    : isHovered
                    ? "#4b5563"
                    : ringColor
                }
                strokeWidth={isSelected ? 0.6 : 0.3}
                filter={
                  isWorking
                    ? "url(#glow-green)"
                    : isSelected
                    ? "url(#glow-accent)"
                    : undefined
                }
              />

              {/* Emoji */}
              <text
                x={pos.x}
                y={pos.y + 1.2}
                textAnchor="middle"
                fontSize={isFriday ? "5" : "3.5"}
                className="select-none"
              >
                {agent.emoji}
              </text>

              {/* Name */}
              <text
                x={pos.x}
                y={pos.y + r + 3}
                textAnchor="middle"
                fontSize="2.5"
                fill={isSelected ? "#e2e8f0" : "#64748b"}
                fontWeight={isSelected ? "600" : "400"}
                className="select-none"
              >
                {agent.name}
              </text>

              {/* Role */}
              <text
                x={pos.x}
                y={pos.y + r + 5.5}
                textAnchor="middle"
                fontSize="1.8"
                fill="#475569"
                className="select-none"
              >
                {agent.role}
              </text>

              {/* Status dot */}
              <circle
                cx={pos.x + r - 1}
                cy={pos.y - r + 1}
                r="1"
                fill={ringColor}
              >
                {isWorking && (
                  <animate
                    attributeName="opacity"
                    values="1;0.3;1"
                    dur="1.5s"
                    repeatCount="indefinite"
                  />
                )}
              </circle>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ─── Main Component ────────────────────────────────────────────── */

export default function AgentServiceMap() {
  const [rawAgents, setRawAgents] = useState<AgentData[]>([]);
  const [events, setEvents] = useState<EventData[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<"grid" | "map">("grid");
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const [agentsResp, eventsResp] = await Promise.all([
        authFetch(`${API}/api/agents`).catch(() => null),
        authFetch(`${API}${TEAM_API}/events`).catch(() => null),
      ]);

      if (agentsResp?.ok) {
        const data = await agentsResp.json();
        // Use DB agents as source of truth (from /api/agents)
        const dbAgents = Array.isArray(data) ? data : [];
        const mapped: AgentData[] = dbAgents.map((a: any) => ({
          id: a.id || a.name?.toLowerCase().replace(/\s+/g, "-") || "unknown",
          name: a.name || "Unknown",
          emoji: a.emoji || "🤖",
          role: a.role || "Agent",
          model: (a.model || "unknown").replace("anthropic/", "").replace("google/", ""),
          color: a.color || "#6366f1",
        }));
        if (mapped.length > 0) {
          setRawAgents(mapped);
        }
      }

      if (eventsResp?.ok) {
        const data = await eventsResp.json();
        if (Array.isArray(data?.events) || Array.isArray(data)) {
          setEvents(normalizeTeamEvents(data));
        }
      }

      setLastRefresh(new Date());
    } catch {
      // silently fail, keep existing data
    } finally {
      setLoading(false);
      if (isManual) setTimeout(() => setRefreshing(false), 300);
    }
  }, []);

  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(() => fetchData(), POLL_INTERVAL);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchData]);

  const agents = useMemo(
    () => deriveAgents(rawAgents, events),
    [rawAgents, events]
  );

  const selectedAgent = agents.find((a) => a.id === selectedId) ?? null;

  const workingCount = agents.filter((a) => a.status === "working").length;
  const idleCount = agents.filter((a) => a.status === "idle").length;
  const totalTasks = agents.reduce((s, a) => s + a.taskCount, 0);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-warroom-border flex flex-wrap items-center gap-2 px-3 sm:px-5 py-2 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-warroom-accent" />
          <h2 className="text-sm font-semibold text-warroom-text whitespace-nowrap">
            Agent Dashboard
          </h2>
        </div>

        {/* Stats (compact) */}
        <div className="flex items-center gap-2.5 text-[11px] text-warroom-muted">
          <span className="flex items-center gap-1">
            <Hash size={10} /> {totalTasks}<span className="hidden sm:inline"> tasks</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="relative flex h-1.5 w-1.5">
              {workingCount > 0 && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              )}
              <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${workingCount > 0 ? "bg-green-500" : "bg-gray-500"}`} />
            </span>
            {workingCount}<span className="hidden sm:inline"> Working</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-gray-500" />
            {idleCount}<span className="hidden sm:inline"> Idle</span>
          </span>
        </div>

        {/* View toggle + refresh */}
        <div className="ml-auto flex items-center gap-1.5">
          <div className="flex bg-warroom-bg rounded-lg border border-warroom-border overflow-hidden">
            <button
              onClick={() => setView("grid")}
              className={`flex items-center gap-1 px-2 py-1.5 text-[10px] font-medium transition-colors ${
                view === "grid"
                  ? "bg-warroom-accent/15 text-warroom-accent"
                  : "text-warroom-muted hover:text-warroom-text"
              }`}
            >
              <LayoutGrid size={11} /> <span className="hidden sm:inline">Grid</span>
            </button>
            <button
              onClick={() => setView("map")}
              className={`flex items-center gap-1 px-2 py-1.5 text-[10px] font-medium transition-colors ${
                view === "map"
                  ? "bg-warroom-accent/15 text-warroom-accent"
                  : "text-warroom-muted hover:text-warroom-text"
              }`}
            >
              <Network size={11} /> <span className="hidden sm:inline">Map</span>
            </button>
          </div>
          <button
            onClick={() => fetchData(true)}
            className="p-1.5 text-warroom-muted hover:text-warroom-text transition-colors"
            title={lastRefresh ? `Last: ${lastRefresh.toLocaleTimeString()}` : "Refresh"}
          >
            <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel */}
        <div
          className={`flex-1 overflow-y-auto transition-all duration-300 ${
            selectedAgent ? "" : ""
          }`}
        >
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2
                size={24}
                className="animate-spin text-warroom-accent"
              />
            </div>
          ) : view === "grid" ? (
            <div className="p-3 sm:p-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {agents.map((agent) => (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    isSelected={selectedId === agent.id}
                    onClick={() =>
                      setSelectedId(
                        selectedId === agent.id ? null : agent.id
                      )
                    }
                  />
                ))}
              </div>
            </div>
          ) : (
            <ServiceMapView
              agents={agents}
              events={events}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
        </div>

        {/* Right Panel — full overlay on mobile, sidebar on lg+ */}
        {selectedAgent && (
          <>
            {/* Mobile: full-screen overlay */}
            <div className="lg:hidden fixed inset-0 z-50 bg-warroom-bg flex flex-col">
              <DetailSidebar
                agent={selectedAgent}
                allAgents={agents}
                onClose={() => setSelectedId(null)}
              />
            </div>
            {/* Desktop: sidebar */}
            <div className="hidden lg:block w-96 border-l border-warroom-border bg-warroom-surface overflow-hidden flex-shrink-0">
              <DetailSidebar
                agent={selectedAgent}
                allAgents={agents}
                onClose={() => setSelectedId(null)}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
