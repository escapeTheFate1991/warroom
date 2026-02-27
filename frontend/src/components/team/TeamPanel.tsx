"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bot, Activity, Clock, Circle, ArrowRight, BarChart3,
  RefreshCw, Plus, Trash2, Edit2, X, Check, Zap,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Agent {
  id: string;
  name: string;
  emoji: string;
  role: string;
  model: string;
  color: string;
}

interface AgentEvent {
  id: number;
  event_type: string;
  from_agent: string;
  to_agent: string;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

interface Flow {
  from_agent: string;
  to_agent: string;
  count: number;
  last_at: string;
}

interface AgentStats {
  [agent: string]: {
    events_24h: number;
    last_active: string;
  };
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  spawn: "bg-blue-500/20 text-blue-400",
  complete: "bg-green-500/20 text-green-400",
  error: "bg-red-500/20 text-red-400",
  message: "bg-warroom-accent/20 text-warroom-accent",
  handoff: "bg-purple-500/20 text-purple-400",
  heartbeat: "bg-warroom-muted/20 text-warroom-muted",
};

const timeAgo = (date: string): string => {
  const diff = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

export default function TeamPanel() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [flows, setFlows] = useState<Flow[]>([]);
  const [stats, setStats] = useState<AgentStats>({});
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<"activity" | "flows">("activity");
  const [editingAgent, setEditingAgent] = useState<string | null>(null);
  const [showAddAgent, setShowAddAgent] = useState(false);
  const [newAgent, setNewAgent] = useState({ id: "", name: "", emoji: "🤖", role: "", model: "sonnet", color: "#3b82f6" });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [agentsRes, eventsRes, flowsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/team/agents`),
        fetch(`${API}/api/team/events?limit=100&hours=168`),
        fetch(`${API}/api/team/flows`),
        fetch(`${API}/api/team/stats`),
      ]);

      const agentsData = await agentsRes.json();
      const eventsData = await eventsRes.json();
      const flowsData = await flowsRes.json();
      const statsData = await statsRes.json();

      const agentList = agentsData.agents || agentsData || [];
      const friday: Agent = { id: "friday", name: "Friday", emoji: "🖤", role: "Orchestrator", model: "opus", color: "#6366f1" };
      setAgents([friday, ...agentList]);
      setEvents(eventsData.events || []);
      setFlows(flowsData.flows || []);
      setStats(statsData.stats || {});
    } catch {
      console.error("Failed to fetch team data");
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const deleteAgent = async (id: string) => {
    if (!confirm(`Delete agent "${id}"?`)) return;
    await fetch(`${API}/api/team/agents/${id}`, { method: "DELETE" });
    fetchAll();
  };

  const addAgent = async () => {
    if (!newAgent.id || !newAgent.name || !newAgent.role) return;
    await fetch(`${API}/api/team/agents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newAgent),
    });
    setShowAddAgent(false);
    setNewAgent({ id: "", name: "", emoji: "🤖", role: "", model: "sonnet", color: "#3b82f6" });
    fetchAll();
  };

  const getAgentStats = (agentId: string) => stats[agentId];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3">
        <h2 className="text-sm font-semibold">Team</h2>
        <span className="text-xs text-warroom-muted">{agents.length} agents</span>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setShowAddAgent(true)}
            className="flex items-center gap-1 text-xs bg-warroom-accent/20 text-warroom-accent px-3 py-1.5 rounded-lg hover:bg-warroom-accent/30 transition"
          >
            <Plus size={12} /> Add Agent
          </button>
          <button onClick={fetchAll} disabled={loading} className="text-warroom-muted hover:text-warroom-text transition">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Agent Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {agents.map((agent) => {
            const agentStat = getAgentStats(agent.id);
            return (
              <div
                key={agent.id}
                className="bg-warroom-surface border border-warroom-border rounded-lg p-4 hover:border-warroom-accent/30 transition group relative"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{agent.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{agent.name}</p>
                    <p className="text-xs text-warroom-muted">{agent.role}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Circle
                      size={8}
                      className={
                        agentStat
                          ? "fill-warroom-success text-warroom-success"
                          : agent.id === "friday"
                          ? "fill-warroom-success text-warroom-success"
                          : "fill-warroom-muted/30 text-warroom-muted/30"
                      }
                    />
                    <span className="text-[9px] text-warroom-muted">{agent.model}</span>
                  </div>
                </div>

                {/* Stats row */}
                {agentStat && (
                  <div className="mt-2 pt-2 border-t border-warroom-border/50 flex items-center justify-between text-[10px] text-warroom-muted">
                    <span className="flex items-center gap-1">
                      <Zap size={10} /> {agentStat.events_24h} events (24h)
                    </span>
                    <span>{timeAgo(agentStat.last_active)}</span>
                  </div>
                )}

                {/* Delete button (not for friday) */}
                {agent.id !== "friday" && (
                  <button
                    onClick={() => deleteAgent(agent.id)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-warroom-muted hover:text-warroom-danger transition p-1"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Add Agent Form */}
        {showAddAgent && (
          <div className="bg-warroom-surface border border-warroom-accent/30 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium">Add New Agent</h4>
              <button onClick={() => setShowAddAgent(false)} className="text-warroom-muted hover:text-warroom-text">
                <X size={16} />
              </button>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              <input value={newAgent.id} onChange={(e) => setNewAgent({ ...newAgent, id: e.target.value.toLowerCase().replace(/\s/g, "-") })}
                placeholder="id (e.g. research)" className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm" />
              <input value={newAgent.name} onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                placeholder="Name" className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm" />
              <input value={newAgent.emoji} onChange={(e) => setNewAgent({ ...newAgent, emoji: e.target.value })}
                placeholder="Emoji" className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm w-20" />
              <input value={newAgent.role} onChange={(e) => setNewAgent({ ...newAgent, role: e.target.value })}
                placeholder="Role" className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm" />
              <select value={newAgent.model} onChange={(e) => setNewAgent({ ...newAgent, model: e.target.value })}
                className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm">
                <option value="haiku">Haiku</option>
                <option value="sonnet">Sonnet</option>
                <option value="opus">Opus</option>
              </select>
              <button onClick={addAgent} className="bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg px-4 py-2 text-sm font-medium flex items-center justify-center gap-1 transition">
                <Check size={14} /> Create
              </button>
            </div>
          </div>
        )}

        {/* View Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveView("activity")}
            className={`text-xs px-3 py-1.5 rounded-lg transition ${
              activeView === "activity" ? "bg-warroom-accent/20 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text"
            }`}
          >
            <Activity size={12} className="inline mr-1" /> Activity ({events.length})
          </button>
          <button
            onClick={() => setActiveView("flows")}
            className={`text-xs px-3 py-1.5 rounded-lg transition ${
              activeView === "flows" ? "bg-warroom-accent/20 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text"
            }`}
          >
            <BarChart3 size={12} className="inline mr-1" /> Flows ({flows.length})
          </button>
        </div>

        {/* Activity Feed */}
        {activeView === "activity" && (
          <div className="space-y-2">
            {events.length === 0 && (
              <div className="text-center py-8 text-warroom-muted">
                <Activity size={32} className="mx-auto mb-3 opacity-20" />
                <p className="text-sm">No recent activity</p>
                <p className="text-xs mt-1">Events appear when sub-agents are spawned, complete work, or communicate</p>
              </div>
            )}
            {events.map((event) => (
              <div
                key={event.id}
                className="flex items-start gap-3 bg-warroom-surface border border-warroom-border rounded-lg p-3 group"
              >
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium mt-0.5 ${EVENT_TYPE_COLORS[event.event_type] || "bg-warroom-border text-warroom-muted"}`}>
                  {event.event_type}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">
                    {event.from_agent && <span className="font-medium">{event.from_agent}</span>}
                    {event.from_agent && event.to_agent && (
                      <ArrowRight size={12} className="inline mx-1.5 text-warroom-muted" />
                    )}
                    {event.to_agent && <span className="font-medium">{event.to_agent}</span>}
                  </p>
                  <p className="text-xs text-warroom-muted mt-0.5 line-clamp-2">{event.summary}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-[10px] text-warroom-muted">{timeAgo(event.created_at)}</span>
                  <button
                    onClick={async () => {
                      await fetch(`${API}/api/team/events/${event.id}`, { method: "DELETE" });
                      fetchAll();
                    }}
                    className="opacity-0 group-hover:opacity-100 text-warroom-muted hover:text-warroom-danger transition"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Flows View */}
        {activeView === "flows" && (
          <div className="space-y-2">
            {flows.length === 0 && (
              <div className="text-center py-8 text-warroom-muted">
                <BarChart3 size={32} className="mx-auto mb-3 opacity-20" />
                <p className="text-sm">No communication flows yet</p>
                <p className="text-xs mt-1">Shows inter-agent communication patterns from the last 7 days</p>
              </div>
            )}
            {flows.map((flow, i) => (
              <div key={i} className="flex items-center gap-3 bg-warroom-surface border border-warroom-border rounded-lg p-3">
                <span className="text-sm font-medium w-20 text-right">{flow.from_agent}</span>
                <div className="flex-1 relative h-2 bg-warroom-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-warroom-accent rounded-full"
                    style={{ width: `${Math.min(100, (flow.count / Math.max(...flows.map((f) => f.count))) * 100)}%` }}
                  />
                </div>
                <span className="text-sm font-medium w-20">{flow.to_agent}</span>
                <span className="text-xs text-warroom-muted w-16 text-right">{flow.count} msgs</span>
                <span className="text-[10px] text-warroom-muted">{timeAgo(flow.last_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
