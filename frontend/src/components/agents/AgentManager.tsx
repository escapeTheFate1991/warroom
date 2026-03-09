"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus, Trash2, Bot, Cpu, Wrench,
  Loader2, Settings, Zap,
  Users, Pen, Palette, Code, Search,
  BarChart3, Headphones, Globe, Cog, Monitor, Server, ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AgentSummary } from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";

/* ── Icons ─────────────────────────────────────────────── */

const ROLE_ICON_MAP: Record<string, LucideIcon> = {
  copywriter: Pen, designer: Palette, developer: Code,
  "frontend-dev": Monitor, "backend-dev": Server, "security-dev": ShieldCheck,
  researcher: Search, analyst: BarChart3, support: Headphones,
  seo: Globe, custom: Cog,
};

function AgentIcon({ role, size = 16, className = "" }: { role: string; size?: number; className?: string }) {
  const Icon = ROLE_ICON_MAP[role] || Bot;
  return <Icon size={size} className={className} />;
}

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-gray-500",
  working: "bg-green-500 animate-pulse",
  paused: "bg-amber-500",
  error: "bg-red-500",
};

/* ── Component ─────────────────────────────────────────── */

interface AgentManagerProps {
  onNavigate?: (tab: string, params?: Record<string, string>) => void;
}

export default function AgentManager({ onNavigate }: AgentManagerProps) {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/agents`);
      if (res.ok) setAgents(await res.json());
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const handleDelete = async (agentId: string) => {
    try {
      await authFetch(`${API}/api/agents/${agentId}`, { method: "DELETE" });
      setDeleteConfirm(null);
      fetchAgents();
    } catch (err) {
      console.error("Failed to delete agent:", err);
    }
  };

  const navigateToCreate = () => {
    onNavigate?.("agent-create");
  };

  const navigateToEdit = (agentId: string) => {
    onNavigate?.("agent-edit", { id: agentId });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-warroom-accent" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-warroom-accent/10 flex items-center justify-center">
            <Users size={20} className="text-warroom-accent" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-warroom-text">AI Agents</h2>
            <p className="text-xs text-warroom-muted">{agents.length} agents configured</p>
          </div>
        </div>
        <button
          onClick={navigateToCreate}
          className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white rounded-xl text-sm font-medium hover:bg-warroom-accent/80 transition"
        >
          <Plus size={16} />
          New Agent
        </button>
      </div>

      {/* Agent Grid */}
      {agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-warroom-muted">
          <Bot size={48} className="mb-4 opacity-30" />
          <p className="text-lg font-medium text-warroom-text mb-1">No agents yet</p>
          <p className="text-sm mb-4">Create specialized AI agents to handle different tasks</p>
          <button
            onClick={navigateToCreate}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white rounded-xl text-sm hover:bg-warroom-accent/80 transition"
          >
            <Plus size={16} />
            Create Your First Agent
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {agents.map(agent => (
            <div
              key={agent.id}
              onClick={() => navigateToEdit(agent.id)}
              className="bg-warroom-surface border border-warroom-border rounded-2xl overflow-hidden hover:border-warroom-accent/30 transition group cursor-pointer"
            >
              {/* Card Header */}
              <div className="px-4 pt-4 pb-3 flex items-start justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-warroom-accent/10 flex items-center justify-center flex-shrink-0">
                    <AgentIcon role={agent.role} size={20} className="text-warroom-accent" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-warroom-text truncate">{agent.name}</h3>
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_COLORS[agent.status] || STATUS_COLORS.idle}`} />
                    </div>
                    <p className="text-[10px] text-warroom-muted capitalize">{agent.role}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                  <button
                    onClick={(e) => { e.stopPropagation(); navigateToEdit(agent.id); }}
                    className="p-1 rounded-lg hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition"
                  >
                    <Settings size={14} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeleteConfirm(agent.id); }}
                    className="p-1 rounded-lg hover:bg-red-500/10 text-warroom-muted hover:text-red-400 transition"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Description */}
              {agent.description && (
                <p className="px-4 text-xs text-warroom-muted line-clamp-2 mb-2">{agent.description}</p>
              )}

              {/* Stats Bar */}
              <div className="px-4 pb-3 flex items-center gap-3 text-[10px] text-warroom-muted">
                <span className="flex items-center gap-1">
                  <Cpu size={10} />
                  {agent.model.split("/").pop()?.replace("claude-", "")}
                </span>
                <span className="flex items-center gap-1">
                  <Wrench size={10} />
                  {(agent.skills || []).length} skills
                </span>
                <span className="flex items-center gap-1">
                  <Zap size={10} />
                  {agent.active_assignments ?? agent.active_tasks} assignments
                </span>
              </div>

              {/* Skill Tags */}
              {(agent.skills || []).length > 0 && (
                <div className="px-4 pb-3 flex flex-wrap gap-1">
                  {(agent.skills || []).slice(0, 5).map(skill => (
                    <span key={skill} className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full text-[10px]">
                      {skill}
                    </span>
                  ))}
                  {(agent.skills || []).length > 5 && (
                    <span className="px-2 py-0.5 bg-warroom-border/50 text-warroom-muted rounded-full text-[10px]">
                      +{(agent.skills || []).length - 5} more
                    </span>
                  )}
                </div>
              )}

              {/* Delete confirmation */}
              {deleteConfirm === agent.id && (
                <div className="border-t border-red-500/30 bg-red-500/5 px-4 py-3 flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
                  <p className="text-xs text-red-400">Delete this agent?</p>
                  <div className="flex gap-2">
                    <button onClick={() => setDeleteConfirm(null)} className="text-xs text-warroom-muted hover:text-warroom-text px-2 py-1">Cancel</button>
                    <button onClick={() => handleDelete(agent.id)} className="text-xs text-red-400 hover:text-red-300 bg-red-500/10 px-3 py-1 rounded-lg">Delete</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
