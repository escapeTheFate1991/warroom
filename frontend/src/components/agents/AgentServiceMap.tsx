"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { X, Cpu, Clock, Zap, CheckCircle, AlertCircle, Loader2, ChevronRight, Activity } from "lucide-react";

const TEAM_API = "http://10.0.0.11:18795";

interface Agent {
  id: string;
  name: string;
  emoji: string;
  role: string;
  model: string;
  status: "running" | "idle" | "error";
  currentTask?: string;
  taskProgress?: number;
  taskQueue: string[];
  nextAgent?: string;
  recentTasks: { task: string; duration: string; timestamp: string }[];
  tokenUsage: { input: number; output: number; cost: string };
  cx: number; // percentage x
  cy: number; // percentage y
}

interface AgentEvent {
  event_type: string;
  from_agent: string;
  to_agent: string;
  summary: string;
  timestamp: string;
}

const DEFAULT_AGENTS: Agent[] = [
  { id: "friday", name: "Friday", emoji: "🖤", role: "Orchestrator", model: "claude-opus-4-6", status: "running", currentTask: "Coordinating team operations", taskProgress: 100, taskQueue: [], nextAgent: undefined, recentTasks: [{ task: "Built Social Dashboard", duration: "12m", timestamp: "2m ago" }, { task: "Fixed OAuth flow", duration: "8m", timestamp: "1h ago" }], tokenUsage: { input: 45200, output: 12800, cost: "$0.42" }, cx: 50, cy: 50 },
  { id: "copy", name: "Copy", emoji: "📝", role: "Copywriter", model: "claude-sonnet", status: "idle", taskQueue: ["Write cold email sequence"], recentTasks: [{ task: "Website copy for stuffnthings.io", duration: "15m", timestamp: "3h ago" }], tokenUsage: { input: 8400, output: 3200, cost: "$0.08" }, cx: 25, cy: 18 },
  { id: "design", name: "Design", emoji: "🎨", role: "UI/UX Designer", model: "claude-sonnet", status: "idle", taskQueue: [], recentTasks: [{ task: "War Room dashboard layout", duration: "20m", timestamp: "5h ago" }], tokenUsage: { input: 12000, output: 5600, cost: "$0.12" }, cx: 75, cy: 18 },
  { id: "dev", name: "Dev", emoji: "💻", role: "Full-Stack Developer", model: "claude-sonnet", status: "idle", taskQueue: ["Deploy content pipeline API"], recentTasks: [{ task: "Social OAuth integration", duration: "25m", timestamp: "2h ago" }], tokenUsage: { input: 32000, output: 18000, cost: "$0.35" }, cx: 82, cy: 55 },
  { id: "docs", name: "Docs", emoji: "📚", role: "Documentation", model: "claude-haiku", status: "idle", taskQueue: [], recentTasks: [{ task: "Updated ARCHITECTURE.md", duration: "5m", timestamp: "1d ago" }], tokenUsage: { input: 2400, output: 1800, cost: "$0.01" }, cx: 18, cy: 82 },
  { id: "support", name: "Support", emoji: "📞", role: "Call Center", model: "claude-haiku", status: "idle", taskQueue: [], recentTasks: [], tokenUsage: { input: 0, output: 0, cost: "$0.00" }, cx: 18, cy: 55 },
  { id: "inbox", name: "Inbox", emoji: "📧", role: "Email Reader", model: "claude-haiku", status: "idle", taskQueue: [], recentTasks: [], tokenUsage: { input: 0, output: 0, cost: "$0.00" }, cx: 82, cy: 82 },
];

const CONNECTIONS = [
  { from: "friday", to: "copy" },
  { from: "friday", to: "design" },
  { from: "friday", to: "dev" },
  { from: "friday", to: "docs" },
  { from: "friday", to: "support" },
  { from: "friday", to: "inbox" },
  { from: "copy", to: "design" },
  { from: "design", to: "dev" },
];

const STATUS_COLORS = {
  running: { ring: "#22c55e", glow: "0 0 20px rgba(34,197,94,0.3)", bg: "bg-green-500/10", text: "text-green-400", label: "Running" },
  idle: { ring: "#64748b", glow: "none", bg: "bg-gray-500/10", text: "text-gray-400", label: "Idle" },
  error: { ring: "#ef4444", glow: "0 0 20px rgba(239,68,68,0.3)", bg: "bg-red-500/10", text: "text-red-400", label: "Error" },
};

function formatTokens(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return n.toString();
}

export default function AgentServiceMap() {
  const [agents, setAgents] = useState<Agent[]>(DEFAULT_AGENTS);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [demoMode, setDemoMode] = useState(true);
  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Try to fetch live data from team dashboard
  const fetchAgentData = useCallback(async () => {
    try {
      const [agentsResp, eventsResp] = await Promise.all([
        fetch(`${TEAM_API}/agents`).catch(() => null),
        fetch(`${TEAM_API}/events?limit=20`).catch(() => null),
      ]);
      if (agentsResp?.ok) {
        const data = await agentsResp.json();
        if (Array.isArray(data) && data.length > 0) {
          setDemoMode(false);
          // Merge live data with default positions
          setAgents(prev => prev.map(a => {
            const live = data.find((d: any) => d.id === a.id || d.name?.toLowerCase() === a.id);
            return live ? { ...a, status: live.status || a.status, currentTask: live.current_task || a.currentTask } : a;
          }));
        }
      }
      if (eventsResp?.ok) {
        const data = await eventsResp.json();
        if (Array.isArray(data)) setEvents(data.slice(0, 20));
      }
    } catch { /* demo mode stays */ }
  }, []);

  useEffect(() => {
    fetchAgentData();
    const interval = setInterval(fetchAgentData, 30000);
    return () => clearInterval(interval);
  }, [fetchAgentData]);

  const getAgentPos = (id: string) => {
    const a = agents.find(x => x.id === id);
    return a ? { x: a.cx, y: a.cy } : { x: 50, y: 50 };
  };

  const activeConnections = new Set(events.slice(0, 5).map(e => `${e.from_agent}-${e.to_agent}`));

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Activity size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Agent Service Map</h2>
        {demoMode && (
          <span className="ml-2 px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent text-[10px] font-medium rounded-full">DEMO</span>
        )}
        <div className="ml-auto flex items-center gap-4 text-xs text-warroom-muted">
          <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-green-400" /> {agents.filter(a => a.status === "running").length} Running</span>
          <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-gray-500" /> {agents.filter(a => a.status === "idle").length} Idle</span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Service Map */}
        <div className="flex-1 relative bg-warroom-bg">
          {/* Grid pattern background */}
          <div className="absolute inset-0 opacity-5" style={{
            backgroundImage: "radial-gradient(circle, #6366f1 1px, transparent 1px)",
            backgroundSize: "30px 30px",
          }} />

          <svg ref={svgRef} className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
            <defs>
              <filter id="glow-green">
                <feGaussianBlur stdDeviation="1" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="glow-accent">
                <feGaussianBlur stdDeviation="1.5" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            {/* Connection lines */}
            {CONNECTIONS.map(conn => {
              const from = getAgentPos(conn.from);
              const to = getAgentPos(conn.to);
              const midX = (from.x + to.x) / 2;
              const midY = (from.y + to.y) / 2 - 3;
              const isActive = activeConnections.has(`${conn.from}-${conn.to}`) || activeConnections.has(`${conn.to}-${conn.from}`);
              const isHighlighted = hoveredAgent === conn.from || hoveredAgent === conn.to || selectedAgent?.id === conn.from || selectedAgent?.id === conn.to;

              return (
                <g key={`${conn.from}-${conn.to}`}>
                  <path
                    d={`M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`}
                    fill="none"
                    stroke={isActive ? "#6366f1" : isHighlighted ? "#4b5563" : "#1e2030"}
                    strokeWidth={isActive ? 0.4 : 0.2}
                    strokeDasharray={isActive ? "1 1" : "none"}
                    opacity={isHighlighted || isActive ? 1 : 0.5}
                  >
                    {isActive && (
                      <animate attributeName="stroke-dashoffset" from="10" to="0" dur="2s" repeatCount="indefinite" />
                    )}
                  </path>
                </g>
              );
            })}

            {/* Agent nodes */}
            {agents.map(agent => {
              const sc = STATUS_COLORS[agent.status];
              const isSelected = selectedAgent?.id === agent.id;
              const isHovered = hoveredAgent === agent.id;
              const isFriday = agent.id === "friday";
              const r = isFriday ? 6 : 4.5;

              return (
                <g key={agent.id}
                  onClick={() => setSelectedAgent(isSelected ? null : agent)}
                  onMouseEnter={() => setHoveredAgent(agent.id)}
                  onMouseLeave={() => setHoveredAgent(null)}
                  className="cursor-pointer"
                >
                  {/* Outer glow ring */}
                  {(agent.status === "running" || isSelected) && (
                    <circle cx={agent.cx} cy={agent.cy} r={r + 1.5}
                      fill="none" stroke={isSelected ? "#6366f1" : sc.ring} strokeWidth="0.3" opacity="0.4">
                      <animate attributeName="r" values={`${r + 1};${r + 2.5};${r + 1}`} dur="3s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.4;0.1;0.4" dur="3s" repeatCount="indefinite" />
                    </circle>
                  )}

                  {/* Main circle */}
                  <circle cx={agent.cx} cy={agent.cy} r={r}
                    fill="#12121a" stroke={isSelected ? "#6366f1" : isHovered ? "#4b5563" : sc.ring}
                    strokeWidth={isSelected ? 0.6 : 0.3}
                    filter={agent.status === "running" ? "url(#glow-green)" : isSelected ? "url(#glow-accent)" : undefined}
                  />

                  {/* Emoji */}
                  <text x={agent.cx} y={agent.cy + 1.2} textAnchor="middle" fontSize={isFriday ? "5" : "3.5"} className="select-none">
                    {agent.emoji}
                  </text>

                  {/* Name label */}
                  <text x={agent.cx} y={agent.cy + r + 3} textAnchor="middle"
                    fontSize="2.5" fill={isSelected ? "#e2e8f0" : "#64748b"} fontWeight={isSelected ? "600" : "400"}
                    className="select-none">
                    {agent.name}
                  </text>

                  {/* Role label */}
                  <text x={agent.cx} y={agent.cy + r + 5.5} textAnchor="middle"
                    fontSize="1.8" fill="#475569" className="select-none">
                    {agent.role}
                  </text>

                  {/* Status dot */}
                  <circle cx={agent.cx + r - 1} cy={agent.cy - r + 1} r="1"
                    fill={sc.ring}>
                    {agent.status === "running" && (
                      <animate attributeName="opacity" values="1;0.3;1" dur="1.5s" repeatCount="indefinite" />
                    )}
                  </circle>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Agent Detail Drawer */}
        <div className={`border-l border-warroom-border bg-warroom-surface transition-all duration-300 overflow-y-auto ${
          selectedAgent ? "w-80" : "w-0"
        }`}>
          {selectedAgent && (
            <div className="p-5 min-w-[320px]">
              {/* Header */}
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{selectedAgent.emoji}</span>
                  <div>
                    <h3 className="font-semibold">{selectedAgent.name}</h3>
                    <p className="text-xs text-warroom-muted">{selectedAgent.role}</p>
                  </div>
                </div>
                <button onClick={() => setSelectedAgent(null)} className="text-warroom-muted hover:text-warroom-text">
                  <X size={18} />
                </button>
              </div>

              {/* Status + Model */}
              <div className="flex gap-2 mb-5">
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs ${STATUS_COLORS[selectedAgent.status].bg} ${STATUS_COLORS[selectedAgent.status].text}`}>
                  {selectedAgent.status === "running" ? <Loader2 size={12} className="animate-spin" /> : selectedAgent.status === "error" ? <AlertCircle size={12} /> : <CheckCircle size={12} />}
                  {STATUS_COLORS[selectedAgent.status].label}
                </span>
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-warroom-accent/10 text-warroom-accent">
                  <Cpu size={12} /> {selectedAgent.model}
                </span>
              </div>

              {/* Current Task */}
              {selectedAgent.currentTask && (
                <div className="mb-5">
                  <h4 className="text-xs text-warroom-muted font-medium mb-2">Current Task</h4>
                  <div className="bg-warroom-bg border border-warroom-border rounded-xl p-3">
                    <p className="text-sm">{selectedAgent.currentTask}</p>
                    {selectedAgent.taskProgress !== undefined && (
                      <div className="mt-2">
                        <div className="flex justify-between text-[10px] text-warroom-muted mb-1">
                          <span>Progress</span>
                          <span>{selectedAgent.taskProgress}%</span>
                        </div>
                        <div className="h-1.5 bg-warroom-border rounded-full overflow-hidden">
                          <div className="h-full bg-warroom-accent rounded-full transition-all" style={{ width: `${selectedAgent.taskProgress}%` }} />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Task Queue */}
              {selectedAgent.taskQueue.length > 0 && (
                <div className="mb-5">
                  <h4 className="text-xs text-warroom-muted font-medium mb-2">Queue ({selectedAgent.taskQueue.length})</h4>
                  <div className="space-y-1.5">
                    {selectedAgent.taskQueue.map((task, i) => (
                      <div key={i} className="flex items-center gap-2 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2">
                        <span className="text-[10px] text-warroom-muted">{i + 1}</span>
                        <span className="text-xs">{task}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pipeline */}
              {selectedAgent.nextAgent && (
                <div className="mb-5">
                  <h4 className="text-xs text-warroom-muted font-medium mb-2">Pipeline</h4>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2 py-1 bg-warroom-accent/10 text-warroom-accent rounded">{selectedAgent.name}</span>
                    <ChevronRight size={14} className="text-warroom-muted" />
                    <span className="px-2 py-1 bg-warroom-bg border border-warroom-border rounded">
                      {agents.find(a => a.id === selectedAgent.nextAgent)?.emoji} {agents.find(a => a.id === selectedAgent.nextAgent)?.name}
                    </span>
                  </div>
                </div>
              )}

              {/* Recent Completions */}
              {selectedAgent.recentTasks.length > 0 && (
                <div className="mb-5">
                  <h4 className="text-xs text-warroom-muted font-medium mb-2">Recent Completions</h4>
                  <div className="space-y-1.5">
                    {selectedAgent.recentTasks.map((t, i) => (
                      <div key={i} className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2">
                        <p className="text-xs">{t.task}</p>
                        <div className="flex items-center gap-3 mt-1 text-[10px] text-warroom-muted">
                          <span className="flex items-center gap-1"><Clock size={10} /> {t.duration}</span>
                          <span>{t.timestamp}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Token Usage */}
              <div>
                <h4 className="text-xs text-warroom-muted font-medium mb-2">Token Usage</h4>
                <div className="bg-warroom-bg border border-warroom-border rounded-xl p-3">
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <p className="text-sm font-bold">{formatTokens(selectedAgent.tokenUsage.input)}</p>
                      <p className="text-[10px] text-warroom-muted">Input</p>
                    </div>
                    <div>
                      <p className="text-sm font-bold">{formatTokens(selectedAgent.tokenUsage.output)}</p>
                      <p className="text-[10px] text-warroom-muted">Output</p>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-warroom-accent">{selectedAgent.tokenUsage.cost}</p>
                      <p className="text-[10px] text-warroom-muted">Cost</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
