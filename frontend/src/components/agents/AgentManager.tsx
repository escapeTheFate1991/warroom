"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus, Trash2, Edit3, Save, X, Bot, Cpu, Wrench,
  ChevronDown, ChevronRight, Loader2, Settings,
  Play, Pause, CheckCircle, AlertCircle, Zap,
  Users, LayoutGrid, Pen, Palette, Code, Search,
  BarChart3, Headphones, Globe, Cog,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */

interface Agent {
  id: string;
  name: string;
  emoji: string;
  role: string;
  description: string;
  model: string;
  skills: string[];
  config: Record<string, any>;
  status: string;
  openclaw_agent_id: string | null;
  active_tasks: number;
  created_at: string;
  updated_at: string;
}

interface Skill {
  id: string;
  name: string;
  description: string;
  source: string;
  enabled: boolean;
}

interface CreateAgentData {
  name: string;
  role: string;
  description: string;
  model: string;
  skills: string[];
}

const ROLE_ICON_MAP: Record<string, LucideIcon> = {
  copywriter: Pen,
  designer: Palette,
  developer: Code,
  researcher: Search,
  analyst: BarChart3,
  support: Headphones,
  seo: Globe,
  custom: Cog,
};

function AgentIcon({ role, size = 16, className = "" }: { role: string; size?: number; className?: string }) {
  const Icon = ROLE_ICON_MAP[role] || Bot;
  return <Icon size={size} className={className} />;
}

const ROLE_PRESETS: { role: string; description: string; model: string; skills: string[] }[] = [
  { role: "copywriter", description: "Sales copy, cold emails, website content, marketing material", model: "anthropic/claude-sonnet-4-20250514", skills: [] },
  { role: "designer", description: "UI/UX design, layouts, responsive UI, Tailwind CSS", model: "anthropic/claude-sonnet-4-20250514", skills: [] },
  { role: "developer", description: "Full-stack development, Next.js, APIs, databases, deployment", model: "anthropic/claude-sonnet-4-20250514", skills: [] },
  { role: "researcher", description: "Market research, competitor analysis, data collection", model: "anthropic/claude-haiku-3-5-20241022", skills: [] },
  { role: "analyst", description: "Data analysis, reporting, metrics, insights", model: "anthropic/claude-haiku-3-5-20241022", skills: [] },
  { role: "support", description: "Customer support scripts, ticket triage, response templates", model: "anthropic/claude-haiku-3-5-20241022", skills: [] },
  { role: "seo", description: "SEO optimization, keyword research, content strategy", model: "anthropic/claude-sonnet-4-20250514", skills: [] },
  { role: "custom", description: "", model: "anthropic/claude-sonnet-4-20250514", skills: [] },
];

const MODEL_OPTIONS = [
  { value: "anthropic/claude-opus-4-6", label: "Claude Opus ($$$$)" },
  { value: "anthropic/claude-sonnet-4-20250514", label: "Claude Sonnet ($$)" },
  { value: "anthropic/claude-haiku-3-5-20241022", label: "Claude Haiku ($)" },
  { value: "ollama/llama3.1:8b-cpu", label: "Llama 3.1 8B (Free)" },
  { value: "ollama/qwen3:4b", label: "Qwen3 4B (Free)" },
];

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-gray-500",
  working: "bg-green-500 animate-pulse",
  paused: "bg-amber-500",
  error: "bg-red-500",
};

/* ── Component ─────────────────────────────────────────── */

export default function AgentManager() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const [createData, setCreateData] = useState<CreateAgentData>({
    name: "", role: "custom", description: "", model: "anthropic/claude-sonnet-4-20250514", skills: [],
  });

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

  const fetchSkills = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/skills`);
      if (res.ok) setSkills(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchSkills();
  }, [fetchAgents, fetchSkills]);

  const handleCreate = async () => {
    if (!createData.name.trim()) return;
    try {
      const res = await authFetch(`${API}/api/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createData),
      });
      if (res.ok) {
        setShowCreate(false);
        setCreateData({ name: "", role: "custom", description: "", model: "anthropic/claude-sonnet-4-20250514", skills: [] });
        fetchAgents();
      }
    } catch (err) {
      console.error("Failed to create agent:", err);
    }
  };

  const handleUpdate = async (agentId: string, updates: Partial<Agent>) => {
    try {
      const res = await authFetch(`${API}/api/agents/${agentId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        setEditingId(null);
        fetchAgents();
      }
    } catch (err) {
      console.error("Failed to update agent:", err);
    }
  };

  const handleDelete = async (agentId: string) => {
    try {
      await authFetch(`${API}/api/agents/${agentId}`, { method: "DELETE" });
      setDeleteConfirm(null);
      fetchAgents();
    } catch (err) {
      console.error("Failed to delete agent:", err);
    }
  };

  const toggleSkill = (skillName: string, currentSkills: string[], agentId: string) => {
    const updated = currentSkills.includes(skillName)
      ? currentSkills.filter(s => s !== skillName)
      : [...currentSkills, skillName];
    handleUpdate(agentId, { skills: updated });
  };

  const applyPreset = (preset: typeof ROLE_PRESETS[0]) => {
    setCreateData(prev => ({
      ...prev,
      role: preset.role,
      description: preset.description,
      model: preset.model,
    }));
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
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white rounded-xl text-sm font-medium hover:bg-warroom-accent/80 transition"
        >
          <Plus size={16} />
          New Agent
        </button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-warroom-text">Create New Agent</h3>
            <button onClick={() => setShowCreate(false)} className="text-warroom-muted hover:text-warroom-text">
              <X size={16} />
            </button>
          </div>

          {/* Role Presets */}
          <div>
            <label className="text-xs text-warroom-muted uppercase tracking-wide mb-2 block">Quick Presets</label>
            <div className="flex flex-wrap gap-2">
              {ROLE_PRESETS.map(preset => (
                <button
                  key={preset.role}
                  onClick={() => applyPreset(preset)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition ${
                    createData.role === preset.role
                      ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent"
                      : "border-warroom-border text-warroom-muted hover:text-warroom-text hover:border-warroom-text/30"
                  }`}
                >
                  <AgentIcon role={preset.role} size={12} />
                  {preset.role}
                </button>
              ))}
            </div>
          </div>

          {/* Fields */}
          <div>
            <label className="text-xs text-warroom-muted mb-1 block">Name</label>
            <input
              value={createData.name}
              onChange={(e) => setCreateData(p => ({ ...p, name: e.target.value }))}
              placeholder="e.g. Copy Agent"
              className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50"
            />
          </div>

          <div>
            <label className="text-xs text-warroom-muted mb-1 block">Description</label>
            <textarea
              value={createData.description}
              onChange={(e) => setCreateData(p => ({ ...p, description: e.target.value }))}
              placeholder="What does this agent specialize in?"
              rows={2}
              className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50 resize-none"
            />
          </div>

          <div>
            <label className="text-xs text-warroom-muted mb-1 block">Model</label>
            <select
              value={createData.model}
              onChange={(e) => setCreateData(p => ({ ...p, model: e.target.value }))}
              className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50"
            >
              {MODEL_OPTIONS.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {/* Skill Assignment */}
          <div>
            <label className="text-xs text-warroom-muted uppercase tracking-wide mb-2 block">
              Assign Skills ({createData.skills.length} selected)
            </label>
            <div className="max-h-40 overflow-y-auto space-y-1 bg-warroom-bg rounded-xl p-2 border border-warroom-border">
              {skills.filter(s => s.enabled).map(skill => (
                <label
                  key={skill.id}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-warroom-surface cursor-pointer text-xs"
                >
                  <input
                    type="checkbox"
                    checked={createData.skills.includes(skill.name)}
                    onChange={() => {
                      setCreateData(p => ({
                        ...p,
                        skills: p.skills.includes(skill.name)
                          ? p.skills.filter(s => s !== skill.name)
                          : [...p.skills, skill.name],
                      }));
                    }}
                    className="rounded border-warroom-border text-warroom-accent focus:ring-warroom-accent"
                  />
                  <Wrench size={12} className="text-warroom-muted flex-shrink-0" />
                  <span className="text-warroom-text">{skill.name}</span>
                  <span className="text-warroom-muted/50 truncate ml-auto text-[10px]">{skill.description?.slice(0, 60)}</span>
                </label>
              ))}
              {skills.filter(s => s.enabled).length === 0 && (
                <p className="text-xs text-warroom-muted text-center py-2">No skills available. Add skills in Skill Management first.</p>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-warroom-muted hover:text-warroom-text transition">
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={!createData.name.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white rounded-xl text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-40 transition"
            >
              <Plus size={14} />
              Create Agent
            </button>
          </div>
        </div>
      )}

      {/* Agent Grid */}
      {agents.length === 0 && !showCreate ? (
        <div className="flex flex-col items-center justify-center py-16 text-warroom-muted">
          <Bot size={48} className="mb-4 opacity-30" />
          <p className="text-lg font-medium text-warroom-text mb-1">No agents yet</p>
          <p className="text-sm mb-4">Create specialized AI agents to handle different tasks</p>
          <button
            onClick={() => setShowCreate(true)}
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
              className="bg-warroom-surface border border-warroom-border rounded-2xl overflow-hidden hover:border-warroom-accent/30 transition group"
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
                    onClick={() => setExpandedId(expandedId === agent.id ? null : agent.id)}
                    className="p-1 rounded-lg hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition"
                  >
                    <Settings size={14} />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(agent.id)}
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
                  {agent.active_tasks} tasks
                </span>
              </div>

              {/* Skill Tags */}
              {(agent.skills || []).length > 0 && (
                <div className="px-4 pb-3 flex flex-wrap gap-1">
                  {(agent.skills || []).slice(0, 5).map(skill => (
                    <span
                      key={skill}
                      className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full text-[10px]"
                    >
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

              {/* Expanded Settings */}
              {expandedId === agent.id && (
                <div className="border-t border-warroom-border px-4 py-3 space-y-3 bg-warroom-bg/50">
                  {/* Model selector */}
                  <div>
                    <label className="text-[10px] text-warroom-muted uppercase tracking-wide mb-1 block">Model</label>
                    <select
                      value={agent.model}
                      onChange={(e) => handleUpdate(agent.id, { model: e.target.value })}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent/50"
                    >
                      {MODEL_OPTIONS.map(m => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Skill assignment */}
                  <div>
                    <label className="text-[10px] text-warroom-muted uppercase tracking-wide mb-1 block">
                      Skills ({(agent.skills || []).length})
                    </label>
                    <div className="max-h-32 overflow-y-auto space-y-1">
                      {skills.filter(s => s.enabled).map(skill => (
                        <label
                          key={skill.id}
                          className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-warroom-surface cursor-pointer text-[11px]"
                        >
                          <input
                            type="checkbox"
                            checked={(agent.skills || []).includes(skill.name)}
                            onChange={() => toggleSkill(skill.name, agent.skills || [], agent.id)}
                            className="rounded border-warroom-border text-warroom-accent focus:ring-warroom-accent"
                          />
                          <span className="text-warroom-text">{skill.name}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Status toggle */}
                  <div className="flex items-center gap-2">
                    <label className="text-[10px] text-warroom-muted uppercase tracking-wide">Status</label>
                    <div className="flex gap-1">
                      {["idle", "working", "paused"].map(s => (
                        <button
                          key={s}
                          onClick={() => handleUpdate(agent.id, { status: s })}
                          className={`px-2 py-0.5 rounded text-[10px] capitalize transition ${
                            agent.status === s
                              ? "bg-warroom-accent/20 text-warroom-accent"
                              : "text-warroom-muted hover:text-warroom-text"
                          }`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Delete confirmation */}
              {deleteConfirm === agent.id && (
                <div className="border-t border-red-500/30 bg-red-500/5 px-4 py-3 flex items-center justify-between">
                  <p className="text-xs text-red-400">Delete this agent?</p>
                  <div className="flex gap-2">
                    <button onClick={() => setDeleteConfirm(null)} className="text-xs text-warroom-muted hover:text-warroom-text px-2 py-1">
                      Cancel
                    </button>
                    <button onClick={() => handleDelete(agent.id)} className="text-xs text-red-400 hover:text-red-300 bg-red-500/10 px-3 py-1 rounded-lg">
                      Delete
                    </button>
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
