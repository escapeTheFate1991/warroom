"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search, X, Package, Wrench, ExternalLink, Bot, ChevronDown,
  Loader2, Clock,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */

interface Skill {
  id: string;
  name: string;
  description: string;
  categories?: string[];
  subcategories?: string[];
  source: "workspace" | "bundled";
  enabled: boolean;
  path: string;
}

interface AgentSummary {
  id: string;
  name: string;
  role: string;
  skills: string[];
  status: string;
}

/* ── Use-case generator ────────────────────────────────── */

function generateUseCases(skill: Skill): string[] {
  const desc = (skill.description || "").toLowerCase();
  const name = skill.name.toLowerCase();

  // Generate contextual use cases from the description/name
  if (desc.includes("security") || desc.includes("penetration") || desc.includes("vulnerability")) {
    return ["Run security audits on APIs and web applications", "Identify vulnerabilities before deployment to production"];
  }
  if (desc.includes("seo") || desc.includes("search engine")) {
    return ["Optimize page content for higher search rankings", "Audit technical SEO issues across your site"];
  }
  if (desc.includes("api") && (desc.includes("design") || desc.includes("document"))) {
    return ["Generate OpenAPI specs from existing code", "Create developer-friendly API documentation"];
  }
  if (desc.includes("scrape") || desc.includes("scraping") || desc.includes("lead")) {
    return ["Extract business data from online directories", "Build targeted prospect lists from public sources"];
  }
  if (desc.includes("copy") || desc.includes("content") || desc.includes("writing")) {
    return ["Generate conversion-focused landing page copy", "Write email sequences that match your brand voice"];
  }
  if (desc.includes("test") || desc.includes("testing")) {
    return ["Automate test creation for critical user flows", "Validate API responses against expected schemas"];
  }
  if (desc.includes("deploy") || desc.includes("docker") || desc.includes("devops")) {
    return ["Automate container builds and deployments", "Set up CI/CD pipelines for staging and production"];
  }
  if (desc.includes("design") || desc.includes("ui") || desc.includes("ux")) {
    return ["Build responsive component layouts with Tailwind", "Create accessible UI patterns following WCAG standards"];
  }
  if (desc.includes("agent") || desc.includes("ai") || desc.includes("llm")) {
    return ["Build autonomous AI agents for specific workflows", "Orchestrate multi-agent systems for complex tasks"];
  }
  if (desc.includes("data") || desc.includes("analytics") || desc.includes("report")) {
    return ["Generate automated reports from multiple data sources", "Track KPIs and surface actionable insights"];
  }
  // Default
  return [
    `Integrate ${skill.name} into your agent's workflow`,
    `Automate tasks related to ${(skill.categories || ["general"])[0]} operations`,
  ];
}

/* ── Component ─────────────────────────────────────────── */

export default function SkillsManager() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [assignAgent, setAssignAgent] = useState<string>("");
  const [assigning, setAssigning] = useState(false);
  const [assignSuccess, setAssignSuccess] = useState(false);

  const fetchSkills = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/skills`);
      if (res.ok) setSkills(await res.json());
    } catch (err) {
      console.error("Failed to fetch skills:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/agents`);
      if (res.ok) setAgents(await res.json());
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    }
  }, []);

  useEffect(() => {
    fetchSkills();
    fetchAgents();
  }, [fetchSkills, fetchAgents]);

  const handleAssign = async () => {
    if (!selectedSkill || !assignAgent) return;
    setAssigning(true);
    setAssignSuccess(false);
    try {
      const agent = agents.find(a => a.id === assignAgent);
      if (!agent) return;
      const updatedSkills = agent.skills.includes(selectedSkill.name)
        ? agent.skills
        : [...agent.skills, selectedSkill.name];
      const res = await authFetch(`${API}/api/agents/${assignAgent}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skills: updatedSkills }),
      });
      if (res.ok) {
        setAssignSuccess(true);
        fetchAgents();
        setTimeout(() => setAssignSuccess(false), 3000);
      }
    } catch (err) {
      console.error("Failed to assign skill:", err);
    } finally {
      setAssigning(false);
    }
  };

  const filteredSkills = skills.filter(skill =>
    skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (skill.description || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  const workspaceSkills = filteredSkills.filter(s => s.source === "workspace");
  const bundledSkills = filteredSkills.filter(s => s.source === "bundled");

  const truncateDescription = (desc: string) => {
    const words = desc.split(" ");
    return words.length > 20 ? words.slice(0, 20).join(" ") + "..." : desc;
  };

  const activeAgents = agents.filter(a => a.status === "idle" || a.status === "working");

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="animate-spin text-warroom-accent" size={32} />
      </div>
    );
  }

  const SkillCard = ({ skill }: { skill: Skill }) => (
    <div
      onClick={() => { setSelectedSkill(skill); setAssignAgent(""); setAssignSuccess(false); }}
      className="bg-warroom-surface border border-warroom-border rounded-2xl p-4 cursor-pointer hover:border-warroom-accent/30 transition group"
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-semibold text-warroom-text text-sm truncate pr-2">{skill.name}</h4>
        <span className={`px-2 py-0.5 rounded-full text-[10px] flex-shrink-0 ${
          skill.source === "workspace"
            ? "bg-green-400/20 text-green-400"
            : "bg-blue-400/20 text-blue-400"
        }`}>
          {skill.source}
        </span>
      </div>
      {skill.description && (
        <p className="text-xs text-warroom-muted leading-relaxed line-clamp-2">
          {truncateDescription(skill.description)}
        </p>
      )}
      {skill.categories && skill.categories.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {skill.categories.slice(0, 3).map(cat => (
            <span key={cat} className="text-[9px] px-1.5 py-0.5 rounded bg-warroom-bg text-warroom-muted border border-warroom-border/50">
              {cat}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Search */}
      <div className="px-6 py-4 border-b border-warroom-border flex-shrink-0">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
          <input
            type="text"
            placeholder="Search skills..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 bg-warroom-bg border border-warroom-border rounded-xl text-sm text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent/50"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-8">
          {/* Workspace Skills */}
          {workspaceSkills.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Wrench size={16} className="text-green-400" />
                <h3 className="text-sm font-semibold text-warroom-text">Workspace</h3>
                <span className="bg-green-400/20 text-green-400 px-2 py-0.5 rounded-full text-[10px] font-medium">
                  {workspaceSkills.length}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {workspaceSkills.map(skill => <SkillCard key={skill.id} skill={skill} />)}
              </div>
            </div>
          )}

          {/* Bundled Skills */}
          {bundledSkills.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Package size={16} className="text-blue-400" />
                <h3 className="text-sm font-semibold text-warroom-text">Bundled</h3>
                <span className="bg-blue-400/20 text-blue-400 px-2 py-0.5 rounded-full text-[10px] font-medium">
                  {bundledSkills.length}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {bundledSkills.map(skill => <SkillCard key={skill.id} skill={skill} />)}
              </div>
            </div>
          )}

          {filteredSkills.length === 0 && (
            <div className="text-center py-16 text-warroom-muted">
              <Wrench size={32} className="mx-auto mb-3 opacity-20" />
              <p className="text-sm">No skills found{searchTerm && ` matching "${searchTerm}"`}</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Skill Detail Modal (Desktop) ── */}
      {selectedSkill && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setSelectedSkill(null)}>
          <div
            className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-lg overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between p-5 border-b border-warroom-border">
              <div className="min-w-0">
                <h3 className="text-lg font-bold text-warroom-text">{selectedSkill.name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                    selectedSkill.source === "workspace"
                      ? "bg-green-400/20 text-green-400"
                      : "bg-blue-400/20 text-blue-400"
                  }`}>
                    {selectedSkill.source}
                  </span>
                  {selectedSkill.categories?.map(cat => (
                    <span key={cat} className="text-[10px] px-1.5 py-0.5 rounded bg-warroom-bg text-warroom-muted border border-warroom-border/50">
                      {cat}
                    </span>
                  ))}
                </div>
              </div>
              <button onClick={() => setSelectedSkill(null)} className="p-1 text-warroom-muted hover:text-warroom-text">
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="p-5 space-y-5">
              {/* Description */}
              <div>
                <p className="text-sm text-warroom-text/80 leading-relaxed">
                  {selectedSkill.description || "No description available."}
                </p>
              </div>

              {/* Use Cases */}
              <div>
                <h4 className="text-xs text-warroom-muted uppercase tracking-wide mb-2">Use Cases</h4>
                <div className="space-y-2">
                  {generateUseCases(selectedSkill).map((useCase, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-warroom-text/70">
                      <span className="text-warroom-accent mt-0.5">•</span>
                      {useCase}
                    </div>
                  ))}
                </div>
              </div>

              {/* Meta */}
              <div className="flex items-center gap-4 text-[11px] text-warroom-muted">
                <span className="flex items-center gap-1">
                  <Clock size={11} />
                  Source: {selectedSkill.source}
                </span>
                {selectedSkill.source === "workspace" && (
                  <a
                    href={`https://github.com/openclaw/openclaw`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-warroom-accent hover:underline"
                  >
                    <ExternalLink size={11} />
                    View on GitHub
                  </a>
                )}
                {selectedSkill.source === "bundled" && (
                  <a
                    href={`https://clawhub.com`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-warroom-accent hover:underline"
                  >
                    <ExternalLink size={11} />
                    ClawHub
                  </a>
                )}
              </div>

              {/* Assign to Agent */}
              <div className="border-t border-warroom-border pt-4">
                <h4 className="text-xs text-warroom-muted uppercase tracking-wide mb-2">Assign to Agent</h4>
                {activeAgents.length === 0 ? (
                  <p className="text-xs text-warroom-muted">No active agents. Create one first.</p>
                ) : (
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Bot size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
                      <select
                        value={assignAgent}
                        onChange={(e) => { setAssignAgent(e.target.value); setAssignSuccess(false); }}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-xl pl-9 pr-8 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50 appearance-none"
                      >
                        <option value="">Select an agent...</option>
                        {activeAgents.map(agent => {
                          const alreadyAssigned = agent.skills.includes(selectedSkill.name);
                          return (
                            <option key={agent.id} value={agent.id} disabled={alreadyAssigned}>
                              {agent.name} ({agent.role}){alreadyAssigned ? " ✓ assigned" : ""}
                            </option>
                          );
                        })}
                      </select>
                      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" />
                    </div>
                    <button
                      onClick={handleAssign}
                      disabled={!assignAgent || assigning}
                      className="px-4 py-2 bg-warroom-accent text-white rounded-xl text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-40 transition flex-shrink-0"
                    >
                      {assigning ? <Loader2 size={14} className="animate-spin" /> : "Assign"}
                    </button>
                  </div>
                )}
                {assignSuccess && (
                  <p className="text-xs text-green-400 mt-2">
                    ✓ Skill assigned to {agents.find(a => a.id === assignAgent)?.name}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
