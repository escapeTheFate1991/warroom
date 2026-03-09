"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft, Save, Trash2, Loader2, Plus,
  Bot, Pen, Palette, Code, Search, BarChart3, Headphones, Globe, Cog,
  Monitor, Server, ShieldCheck, Wrench, Brain,
  ChevronDown, ChevronRight,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */

interface Skill {
  id: string;
  name: string;
  description: string;
  categories?: string[];
  subcategories?: string[];
  source: string;
  enabled: boolean;
}

interface AgentFormData {
  name: string;
  role: string;
  description: string;
  model: string;
  skills: string[];
  soul_md: string;
}

const EMPTY_FORM: AgentFormData = {
  name: "",
  role: "custom",
  description: "",
  model: "anthropic/claude-sonnet-4-20250514",
  skills: [],
  soul_md: "",
};

/* ── Constants ─────────────────────────────────────────── */

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

const ROLE_PRESETS: { role: string; description: string; model: string; categories: string[]; patterns: string[] }[] = [
  { role: "copywriter", description: "Sales copy, cold emails, website content, marketing material", model: "anthropic/claude-sonnet-4-20250514", categories: ["marketing", "documentation"], patterns: ["copy", "content", "email", "seo", "brand"] },
  { role: "designer", description: "UI/UX design, layouts, responsive UI, Tailwind CSS", model: "anthropic/claude-sonnet-4-20250514", categories: ["design"], patterns: ["ui-", "ux-", "css", "tailwind", "responsive", "figma", "accessibility"] },
  { role: "developer", description: "Full-stack development, Next.js, APIs, databases, deployment", model: "anthropic/claude-sonnet-4-20250514", categories: ["development", "devops"], patterns: ["clean-code", "api-", "architecture", "testing", "debug", "git"] },
  { role: "frontend-dev", description: "React, Next.js, Tailwind CSS, responsive UI, component architecture", model: "anthropic/claude-sonnet-4-20250514", categories: ["development", "design"], patterns: ["react", "next", "angular", "vue", "tailwind", "css", "ui-", "component", "responsive", "state-management", "accessibility", "3d-web"] },
  { role: "backend-dev", description: "FastAPI, Node.js, PostgreSQL, Docker, API design, microservices", model: "anthropic/claude-sonnet-4-20250514", categories: ["development", "devops", "data"], patterns: ["api-", "fastapi", "django", "express", "postgres", "docker", "architecture", "database", "redis", "queue", "async-python", "clean-code"] },
  { role: "security-dev", description: "Penetration testing, API security, auth systems, threat modeling", model: "anthropic/claude-sonnet-4-20250514", categories: ["security"], patterns: ["security", "pentest", "penetration", "auth", "attack", "vulnerability", "threat", "fuzzing", "active-directory", "aws-penetration", "anti-reversing"] },
  { role: "researcher", description: "Market research, competitor analysis, data collection", model: "anthropic/claude-haiku-3-5-20241022", categories: ["data", "marketing"], patterns: ["research", "competitor", "market", "scraper", "apify", "trend"] },
  { role: "analyst", description: "Data analysis, reporting, metrics, insights", model: "anthropic/claude-haiku-3-5-20241022", categories: ["data"], patterns: ["analytics", "data-", "metrics", "report", "visualization"] },
  { role: "support", description: "Customer support scripts, ticket triage, response templates", model: "anthropic/claude-haiku-3-5-20241022", categories: ["automation"], patterns: ["support", "ticket", "email", "template", "workflow"] },
  { role: "seo", description: "SEO optimization, keyword research, content strategy", model: "anthropic/claude-sonnet-4-20250514", categories: ["marketing"], patterns: ["seo", "keyword", "content-strat", "analytics", "search"] },
  { role: "custom", description: "", model: "anthropic/claude-sonnet-4-20250514", categories: [], patterns: [] },
];

const CATEGORY_LABELS: Record<string, string> = {
  development: "Development", devops: "DevOps & Cloud", "ai-ml": "AI & ML",
  security: "Security", marketing: "Marketing & SEO", design: "Design & UX",
  data: "Data & Analytics", automation: "Automation", documentation: "Documentation", other: "Other",
};

const MODEL_OPTIONS = [
  { value: "anthropic/claude-opus-4-6", label: "Claude Opus ($$$$)" },
  { value: "anthropic/claude-sonnet-4-20250514", label: "Claude Sonnet ($$)" },
  { value: "anthropic/claude-haiku-3-5-20241022", label: "Claude Haiku ($)" },
  { value: "ollama/llama3.1:8b-cpu", label: "Llama 3.1 8B (Free)" },
  { value: "ollama/qwen3:4b", label: "Qwen3 4B (Free)" },
];

const SUB_TABS = [
  { id: "details", label: "Details" },
  { id: "skills", label: "Skills" },
  { id: "soul", label: "Soul" },
] as const;

type SubTab = (typeof SUB_TABS)[number]["id"];

/* ── Component ─────────────────────────────────────────── */

interface AgentEditPageProps {
  mode: "create" | "edit";
  agentId?: string;
  onNavigate: (tab: string, params?: Record<string, string>) => void;
}

export default function AgentEditPage({ mode, agentId, onNavigate }: AgentEditPageProps) {
  const [subTab, setSubTab] = useState<SubTab>("details");
  const [form, setForm] = useState<AgentFormData>({ ...EMPTY_FORM });
  const [originalForm, setOriginalForm] = useState<AgentFormData>({ ...EMPTY_FORM });
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(mode === "edit");
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Skill filters
  const [skillSearch, setSkillSearch] = useState("");
  const [skillCategoryFilter, setSkillCategoryFilter] = useState("all");
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [selectedSubcategories, setSelectedSubcategories] = useState<Set<string>>(new Set());

  const fetchSkills = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/skills`);
      if (res.ok) setSkills(await res.json());
    } catch {}
  }, []);

  const fetchAgent = useCallback(async () => {
    if (mode !== "edit" || !agentId) return;
    try {
      setLoading(true);
      const res = await authFetch(`${API}/api/agents/${agentId}`);
      if (res.ok) {
        const agent = await res.json();
        const data: AgentFormData = {
          name: agent.name || "",
          role: agent.role || "custom",
          description: agent.description || "",
          model: agent.model || "anthropic/claude-sonnet-4-20250514",
          skills: agent.skills || [],
          soul_md: agent.soul_md || "",
        };
        setForm(data);
        setOriginalForm(data);
      }
    } catch (err) {
      console.error("Failed to fetch agent:", err);
    } finally {
      setLoading(false);
    }
  }, [mode, agentId]);

  useEffect(() => { fetchSkills(); fetchAgent(); }, [fetchSkills, fetchAgent]);

  const hasChanges = JSON.stringify(form) !== JSON.stringify(originalForm);

  const applyPreset = (preset: typeof ROLE_PRESETS[0]) => {
    const autoSkills = skills
      .filter(s => s.enabled)
      .filter(s => {
        const cats = s.categories || [];
        const matchesCat = preset.categories.some(c => cats.includes(c));
        const matchesPattern = preset.patterns.some(p => s.id.toLowerCase().includes(p) || s.name.toLowerCase().includes(p));
        return matchesCat || matchesPattern;
      })
      .slice(0, 20)
      .map(s => s.name);
    const mandatory = ["prompt-improver", "network-ai"];
    const finalSkills = Array.from(new Set([...mandatory, ...autoSkills]));
    setForm(prev => ({ ...prev, role: preset.role, description: preset.description, model: preset.model, skills: finalSkills }));
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    setSaveSuccess(false);
    try {
      if (mode === "create") {
        const res = await authFetch(`${API}/api/agents`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
        if (res.ok) {
          onNavigate("agents");
          return;
        }
      } else if (agentId) {
        const res = await authFetch(`${API}/api/agents/${agentId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
        if (res.ok) {
          setOriginalForm({ ...form });
          setSaveSuccess(true);
          setTimeout(() => setSaveSuccess(false), 3000);
        }
      }
    } catch (err) {
      console.error("Failed to save agent:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!agentId) return;
    try {
      await authFetch(`${API}/api/agents/${agentId}`, { method: "DELETE" });
      onNavigate("agents");
    } catch (err) {
      console.error("Failed to delete agent:", err);
    }
  };

  const toggleSkill = (skillName: string) => {
    setForm(prev => ({
      ...prev,
      skills: prev.skills.includes(skillName)
        ? prev.skills.filter(s => s !== skillName)
        : [...prev.skills, skillName],
    }));
  };

  const clearAllFilters = () => {
    setSkillCategoryFilter("all");
    setSelectedSubcategories(new Set());
    setSkillSearch("");
  };

  const toggleCategoryExpand = (cat: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat); else next.add(cat);
      return next;
    });
  };

  const toggleSubcategory = (subcat: string) => {
    setSelectedSubcategories(prev => {
      const next = new Set(prev);
      if (next.has(subcat)) next.delete(subcat); else next.add(subcat);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-warroom-accent" size={32} />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate("agents")}
            className="flex items-center gap-1.5 text-sm text-warroom-muted hover:text-warroom-text transition"
          >
            <ArrowLeft size={16} />
            Back to Agents
          </button>
          <span className="text-warroom-border">|</span>
          <div className="flex items-center gap-2">
            <AgentIcon role={form.role} size={18} className="text-warroom-accent" />
            <h2 className="text-lg font-semibold text-warroom-text">
              {mode === "create" ? "Create Agent" : form.name || "Edit Agent"}
            </h2>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {saveSuccess && (
            <span className="text-xs text-green-400 mr-2">Saved ✓</span>
          )}
          {mode === "edit" && (
            <button
              onClick={() => setDeleteConfirm(true)}
              className="px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded-xl transition"
            >
              <Trash2 size={14} />
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={saving || !form.name.trim() || (mode === "edit" && !hasChanges)}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white rounded-xl text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-40 transition"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : mode === "create" ? <Plus size={14} /> : <Save size={14} />}
            {mode === "create" ? "Create Agent" : "Save Changes"}
          </button>
        </div>
      </div>

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="px-6 py-3 bg-red-500/5 border-b border-red-500/20 flex items-center justify-between flex-shrink-0">
          <p className="text-sm text-red-400">Are you sure you want to delete this agent?</p>
          <div className="flex gap-2">
            <button onClick={() => setDeleteConfirm(false)} className="text-xs text-warroom-muted hover:text-warroom-text px-3 py-1.5">Cancel</button>
            <button onClick={handleDelete} className="text-xs text-red-400 hover:text-red-300 bg-red-500/10 px-3 py-1.5 rounded-lg">Delete</button>
          </div>
        </div>
      )}

      {/* Sub-Tab Bar */}
      <div className="flex border-b border-warroom-border flex-shrink-0 px-6">
        {SUB_TABS.map((tab) => {
          const isActive = subTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setSubTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? "border-warroom-accent text-warroom-accent bg-warroom-accent/5"
                  : "border-transparent text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg"
              }`}
            >
              {tab.label}
              {tab.id === "skills" && form.skills.length > 0 && (
                <span className="ml-1.5 text-[10px] bg-warroom-accent/20 text-warroom-accent px-1.5 py-0.5 rounded-full">
                  {form.skills.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* ── Details Tab ── */}
        {subTab === "details" && (
          <div className="max-w-2xl space-y-6">
            {/* Role Presets */}
            <div>
              <label className="text-xs text-warroom-muted uppercase tracking-wide mb-2 block">Quick Presets</label>
              <div className="flex flex-wrap gap-2">
                {ROLE_PRESETS.map(preset => (
                  <button
                    key={preset.role}
                    onClick={() => applyPreset(preset)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition ${
                      form.role === preset.role
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

            {/* Name */}
            <div>
              <label className="text-xs text-warroom-muted mb-1 block">Name *</label>
              <input
                value={form.name}
                onChange={(e) => setForm(p => ({ ...p, name: e.target.value }))}
                placeholder="e.g. Copy Agent"
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50"
              />
            </div>

            {/* Description */}
            <div>
              <label className="text-xs text-warroom-muted mb-1 block">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm(p => ({ ...p, description: e.target.value }))}
                placeholder="What does this agent specialize in?"
                rows={3}
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50 resize-none"
              />
            </div>

            {/* Model */}
            <div>
              <label className="text-xs text-warroom-muted mb-1 block">Model</label>
              <select
                value={form.model}
                onChange={(e) => setForm(p => ({ ...p, model: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50"
              >
                {MODEL_OPTIONS.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>

            {/* Status (edit only) */}
            {mode === "edit" && (
              <div>
                <label className="text-xs text-warroom-muted mb-2 block">Status</label>
                {/* Status is displayed but not editable here — set via AgentManager or API */}
                <p className="text-sm text-warroom-text/60 italic">
                  Status is managed via the agent grid or API.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── Skills Tab ── */}
        {subTab === "skills" && (
          <div className="max-w-3xl space-y-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-warroom-muted uppercase tracking-wide">
                Assign Skills ({form.skills.length} selected)
              </label>
              {form.skills.length > 0 && (
                <button
                  onClick={() => setForm(p => ({ ...p, skills: [] }))}
                  className="text-[10px] text-warroom-muted hover:text-red-400 transition"
                >
                  Clear all
                </button>
              )}
            </div>

            {/* Search */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
              <input
                value={skillSearch}
                onChange={(e) => setSkillSearch(e.target.value)}
                placeholder="Search skills..."
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl pl-9 pr-3 py-2 text-xs text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50"
              />
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setSkillCategoryFilter("all")}
                className={`px-2.5 py-1 rounded-lg text-[10px] border transition ${
                  skillCategoryFilter === "all" ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent" : "border-warroom-border text-warroom-muted hover:text-warroom-text"
                }`}
              >All</button>
              <button
                onClick={() => setSkillCategoryFilter("selected")}
                className={`px-2.5 py-1 rounded-lg text-[10px] border transition ${
                  skillCategoryFilter === "selected" ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent" : "border-warroom-border text-warroom-muted hover:text-warroom-text"
                }`}
              >Selected ({form.skills.length})</button>
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => {
                const catSkills = skills.filter(s => s.enabled && (s.categories || []).includes(key));
                if (catSkills.length === 0) return null;
                const isExpanded = expandedCategories.has(key);
                const subcats = Array.from(new Set(catSkills.flatMap(s => s.subcategories || [])));
                return (
                  <div key={key} className="flex flex-col">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setSkillCategoryFilter(skillCategoryFilter === key ? "all" : key)}
                        className={`px-2.5 py-1 rounded-lg text-[10px] border transition ${
                          skillCategoryFilter === key ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent" : "border-warroom-border text-warroom-muted hover:text-warroom-text"
                        }`}
                      >{label} ({catSkills.length})</button>
                      {subcats.length > 0 && (
                        <button onClick={() => toggleCategoryExpand(key)} className="text-warroom-muted hover:text-warroom-text transition p-0.5">
                          {isExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                        </button>
                      )}
                    </div>
                    {isExpanded && subcats.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1 ml-2">
                        {subcats.map(sub => {
                          const subCount = catSkills.filter(s => (s.subcategories || []).includes(sub)).length;
                          const isSelected = selectedSubcategories.has(sub);
                          return (
                            <button
                              key={sub}
                              onClick={() => toggleSubcategory(sub)}
                              className={`px-2 py-0.5 rounded text-[9px] border transition ${
                                isSelected ? "border-blue-500 bg-blue-500/10 text-blue-400" : "border-warroom-border/50 text-warroom-muted/60 hover:text-warroom-text"
                              }`}
                            >{sub} ({subCount})</button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
              {(skillCategoryFilter !== "all" || selectedSubcategories.size > 0 || skillSearch) && (
                <button onClick={clearAllFilters} className="px-2.5 py-1 rounded-lg text-[10px] border border-red-500/30 text-red-400/70 hover:text-red-300 hover:border-red-500/50 transition">
                  Clear all
                </button>
              )}
            </div>

            {/* Skill List */}
            <div className="max-h-[calc(100vh-350px)] overflow-y-auto space-y-0.5 bg-warroom-bg rounded-xl p-2 border border-warroom-border">
              {(() => {
                const filtered = skills
                  .filter(s => s.enabled)
                  .filter(s => {
                    if (skillCategoryFilter === "selected") return form.skills.includes(s.name);
                    if (skillCategoryFilter !== "all" && !(s.categories || []).includes(skillCategoryFilter)) return false;
                    if (selectedSubcategories.size > 0) {
                      const subs = s.subcategories || [];
                      return Array.from(selectedSubcategories).some(sub => subs.includes(sub));
                    }
                    return true;
                  })
                  .filter(s => {
                    if (!skillSearch.trim()) return true;
                    const q = skillSearch.toLowerCase();
                    return s.id.toLowerCase().includes(q) || s.name.toLowerCase().includes(q) || (s.description || "").toLowerCase().includes(q) || (s.subcategories || []).some(sc => sc.toLowerCase().includes(q));
                  });

                if (filtered.length === 0) {
                  return <p className="text-xs text-warroom-muted text-center py-3">No skills match your search</p>;
                }

                return filtered.map(skill => (
                  <label
                    key={skill.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-warroom-surface cursor-pointer text-xs group"
                  >
                    <input
                      type="checkbox"
                      checked={form.skills.includes(skill.name)}
                      onChange={() => toggleSkill(skill.name)}
                      className="rounded border-warroom-border text-warroom-accent focus:ring-warroom-accent flex-shrink-0"
                    />
                    <Wrench size={11} className="text-warroom-muted flex-shrink-0" />
                    <span className="text-warroom-text truncate">{skill.name}</span>
                    {skill.subcategories && skill.subcategories.length > 0 && (
                      <span className="flex gap-1 flex-shrink-0">
                        {skill.subcategories.slice(0, 3).map(sc => (
                          <span key={sc} className="text-[8px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/30">{sc}</span>
                        ))}
                      </span>
                    )}
                    <span className="text-warroom-muted/50 truncate ml-auto text-[10px] max-w-[200px]">{skill.description?.slice(0, 50)}</span>
                  </label>
                ));
              })()}
            </div>
          </div>
        )}

        {/* ── Soul Tab ── */}
        {subTab === "soul" && (
          <div className="max-w-3xl space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Brain size={16} className="text-warroom-accent" />
              <h3 className="text-sm font-semibold text-warroom-text">Agent Soul</h3>
            </div>
            <p className="text-xs text-warroom-muted">
              Define this agent&apos;s personality, voice, behavior rules, and specialized instructions.
              This is the agent&apos;s unique identity — how it thinks, communicates, and approaches tasks.
            </p>
            <textarea
              value={form.soul_md}
              onChange={(e) => setForm(p => ({ ...p, soul_md: e.target.value }))}
              placeholder={`# ${form.name || "Agent"} Soul\n\n## Personality\n- Describe the agent's voice and tone\n- Communication style preferences\n\n## Expertise\n- Domain knowledge areas\n- Specialized skills\n\n## Rules\n- Behavioral guidelines\n- Output format preferences\n- Things to always/never do`}
              className="w-full min-h-[calc(100vh-400px)] bg-warroom-bg border border-warroom-border rounded-xl px-4 py-3 font-mono text-sm text-warroom-text placeholder-warroom-muted/30 focus:outline-none focus:ring-2 focus:ring-warroom-accent resize-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
