"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Plus, Zap, Play, Pause, Copy, Trash2, Loader2, ChevronRight,
  GitBranch, Bot, Search, LayoutGrid, Sparkles, ArrowLeft,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import dynamic from "next/dynamic";

const WorkflowCanvas = dynamic(() => import("./WorkflowCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <Loader2 className="animate-spin text-warroom-accent" size={24} />
    </div>
  ),
});

/* ── Types ─────────────────────────────────────────────── */

interface WorkflowTemplate {
  id: number;
  name: string;
  description: string | null;
  category: string | null;
  entity_type: string;
  event: string;
  condition_type: string;
  conditions: any[];
  actions: any[];
  is_seed: boolean;
}

interface WorkflowRecord {
  id: number;
  name: string;
  description: string | null;
  entity_type: string | null;
  event: string | null;
  condition_type: string;
  conditions: any;
  actions: any;
  is_active: boolean;
  template_id: number | null;
  version: number;
  created_at: string;
  updated_at: string;
}

type ViewMode = "list" | "canvas" | "template-gallery";

/* ── Humanize helpers ──────────────────────────────────── */

const ENTITY_LABELS: Record<string, string> = {
  deal: "Deal", person: "Contact", activity: "Activity", email: "Email",
};
const EVENT_LABELS: Record<string, string> = {
  created: "is created", updated: "is updated", deleted: "is deleted", stage_changed: "changes stage",
};
const CATEGORY_LABELS: Record<string, string> = {
  sales: "Sales", pipeline: "Pipeline", "Home services • Appointment reminders": "Appointments",
  "Home services • Estimates": "Estimates", "Home services • Dispatch": "Dispatch",
  "Real estate • Lead nurture": "Lead Nurture", "Real estate • Transaction lifecycle": "Transactions",
};

function humanizeName(name: string): string {
  return name
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function humanizeCategory(cat: string | null): string {
  if (!cat) return "General";
  return CATEGORY_LABELS[cat] || cat.split("•").pop()?.trim() || cat;
}

function triggerSummary(entityType: string, event: string): string {
  return `When a ${ENTITY_LABELS[entityType] || entityType} ${EVENT_LABELS[event] || event}`;
}

function actionCount(actions: any[]): string {
  const n = actions?.length || 0;
  return n === 1 ? "1 action" : `${n} actions`;
}

/* ── Component ─────────────────────────────────────────── */

export default function WorkflowStudioPanel() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("list");
  const [search, setSearch] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowRecord | null>(null);
  const [cloning, setCloning] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tRes, wRes] = await Promise.all([
        authFetch(`${API}/api/crm/workflow-templates`),
        authFetch(`${API}/api/crm/workflows`),
      ]);
      if (!tRes.ok || !wRes.ok) throw new Error("Failed to load workflows");
      setTemplates(await tRes.json());
      setWorkflows(await wRes.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCloneTemplate = async (template: WorkflowTemplate) => {
    setCloning(true);
    try {
      const res = await authFetch(`${API}/api/crm/workflow-templates/${template.id}/clone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: `${humanizeName(template.name)}` }),
      });
      if (res.ok) {
        const workflow = await res.json();
        await loadData();
        setSelectedWorkflow(workflow);
        setSelectedTemplate(null);
        setView("canvas");
      }
    } catch {} finally {
      setCloning(false);
    }
  };

  const handleToggleActive = async (workflow: WorkflowRecord) => {
    try {
      await authFetch(`${API}/api/crm/workflows/${workflow.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !workflow.is_active }),
      });
      loadData();
    } catch {}
  };

  const handleDelete = async (workflow: WorkflowRecord) => {
    try {
      await authFetch(`${API}/api/crm/workflows/${workflow.id}`, { method: "DELETE" });
      if (selectedWorkflow?.id === workflow.id) {
        setSelectedWorkflow(null);
        setView("list");
      }
      loadData();
    } catch {}
  };

  const filteredTemplates = templates.filter(t =>
    !search || t.name.toLowerCase().includes(search.toLowerCase()) ||
    (t.description || "").toLowerCase().includes(search.toLowerCase())
  );

  const groupedTemplates = filteredTemplates.reduce<Record<string, WorkflowTemplate[]>>((acc, t) => {
    const cat = humanizeCategory(t.category);
    (acc[cat] = acc[cat] || []).push(t);
    return acc;
  }, {});

  // Active canvas data
  const canvasData = selectedWorkflow
    ? {
        entity_type: selectedWorkflow.entity_type || "deal",
        event: selectedWorkflow.event || "created",
        condition_type: selectedWorkflow.condition_type || "and",
        conditions: selectedWorkflow.conditions || [],
        actions: selectedWorkflow.actions || [],
      }
    : selectedTemplate
      ? {
          entity_type: selectedTemplate.entity_type,
          event: selectedTemplate.event,
          condition_type: selectedTemplate.condition_type,
          conditions: selectedTemplate.conditions,
          actions: selectedTemplate.actions,
        }
      : null;

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="animate-spin text-warroom-accent" size={32} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 text-sm mb-2">{error}</p>
          <button onClick={loadData} className="text-xs text-warroom-accent hover:underline">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          {(view === "canvas" || view === "template-gallery") && (
            <button
              onClick={() => { setView("list"); setSelectedTemplate(null); setSelectedWorkflow(null); }}
              className="p-1.5 rounded-lg hover:bg-warroom-bg text-warroom-muted hover:text-warroom-text transition"
            >
              <ArrowLeft size={16} />
            </button>
          )}
          <GitBranch size={18} className="text-warroom-accent" />
          <h2 className="text-lg font-bold text-warroom-text">
            {view === "canvas"
              ? (selectedWorkflow?.name || selectedTemplate?.name || "Workflow Editor")
              : view === "template-gallery"
                ? "Start from a Template"
                : "Workflows"
            }
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {view === "list" && (
            <>
              <button
                onClick={() => setView("template-gallery")}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-warroom-border rounded-xl text-warroom-muted hover:text-warroom-text hover:border-warroom-accent/30 transition"
              >
                <Sparkles size={12} />
                Templates
              </button>
              <button
                onClick={() => setView("template-gallery")}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent text-white rounded-xl text-xs font-medium hover:bg-warroom-accent/80 transition"
              >
                <Plus size={14} />
                New Workflow
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">

        {/* ── List View ── */}
        {view === "list" && (
          <div className="h-full overflow-y-auto p-6">
            {workflows.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <GitBranch size={48} className="text-warroom-muted/20 mb-4" />
                <h3 className="text-lg font-semibold text-warroom-text mb-1">No workflows yet</h3>
                <p className="text-sm text-warroom-muted mb-4 text-center max-w-md">
                  Workflows automate repetitive tasks — follow up with leads, notify your team,
                  create tasks, and more. Start from a template or build your own.
                </p>
                <button
                  onClick={() => setView("template-gallery")}
                  className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white rounded-xl text-sm font-medium hover:bg-warroom-accent/80 transition"
                >
                  <Sparkles size={16} />
                  Browse Templates
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {workflows.map(wf => (
                  <div
                    key={wf.id}
                    onClick={() => { setSelectedWorkflow(wf); setView("canvas"); }}
                    className="bg-warroom-surface border border-warroom-border rounded-2xl p-4 cursor-pointer hover:border-warroom-accent/30 transition group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                          wf.is_active ? "bg-emerald-500/20" : "bg-warroom-bg"
                        }`}>
                          <Zap size={18} className={wf.is_active ? "text-emerald-400" : "text-warroom-muted"} />
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm font-semibold text-warroom-text truncate">
                            {humanizeName(wf.name)}
                          </h4>
                          <p className="text-xs text-warroom-muted">
                            {triggerSummary(wf.entity_type || "deal", wf.event || "created")} · {actionCount(wf.actions)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleToggleActive(wf)}
                          className={`p-1.5 rounded-lg transition ${
                            wf.is_active ? "text-emerald-400 hover:bg-emerald-500/10" : "text-warroom-muted hover:bg-warroom-bg"
                          }`}
                          title={wf.is_active ? "Pause" : "Activate"}
                        >
                          {wf.is_active ? <Pause size={14} /> : <Play size={14} />}
                        </button>
                        <button
                          onClick={() => handleDelete(wf)}
                          className="p-1.5 rounded-lg text-warroom-muted hover:text-red-400 hover:bg-red-500/10 transition"
                        >
                          <Trash2 size={14} />
                        </button>
                        <ChevronRight size={14} className="text-warroom-muted" />
                      </div>
                    </div>
                    {wf.description && (
                      <p className="text-xs text-warroom-muted mt-2 pl-[52px] line-clamp-1">{wf.description}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Template Gallery ── */}
        {view === "template-gallery" && (
          <div className="h-full overflow-y-auto p-6 space-y-6">
            {/* Search */}
            <div className="relative max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search templates..."
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl pl-9 pr-3 py-2 text-xs text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50"
              />
            </div>

            {/* Grouped Templates */}
            {Object.entries(groupedTemplates).map(([category, catTemplates]) => (
              <div key={category}>
                <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-3">{category}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {catTemplates.map(template => (
                    <div
                      key={template.id}
                      className="bg-warroom-surface border border-warroom-border rounded-2xl p-4 hover:border-warroom-accent/30 transition group"
                    >
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-9 h-9 rounded-xl bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
                          <Zap size={16} className="text-emerald-400" />
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm font-semibold text-warroom-text">
                            {humanizeName(template.name)}
                          </h4>
                          <p className="text-[10px] text-warroom-muted">
                            {triggerSummary(template.entity_type, template.event)} · {actionCount(template.actions)}
                          </p>
                        </div>
                      </div>
                      {template.description && (
                        <p className="text-xs text-warroom-muted leading-relaxed line-clamp-2 mb-3">
                          {template.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => { setSelectedTemplate(template); setView("canvas"); }}
                          className="flex-1 text-xs text-warroom-muted hover:text-warroom-text text-center py-1.5 rounded-lg border border-warroom-border hover:border-warroom-accent/30 transition"
                        >
                          Preview
                        </button>
                        <button
                          onClick={() => handleCloneTemplate(template)}
                          disabled={cloning}
                          className="flex-1 flex items-center justify-center gap-1 text-xs bg-warroom-accent text-white py-1.5 rounded-lg hover:bg-warroom-accent/80 transition disabled:opacity-40"
                        >
                          {cloning ? <Loader2 size={12} className="animate-spin" /> : <Copy size={12} />}
                          Use Template
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {filteredTemplates.length === 0 && (
              <p className="text-sm text-warroom-muted text-center py-8">
                No templates found{search && ` matching "${search}"`}
              </p>
            )}
          </div>
        )}

        {/* ── Canvas View ── */}
        {view === "canvas" && canvasData && (
          <div className="h-full flex flex-col">
            {/* Canvas toolbar */}
            <div className="px-6 py-2 border-b border-warroom-border flex items-center gap-4 text-xs text-warroom-muted flex-shrink-0">
              <span className="flex items-center gap-1">
                <Zap size={11} className="text-emerald-400" />
                {triggerSummary(canvasData.entity_type, canvasData.event)}
              </span>
              <span>·</span>
              <span>{canvasData.conditions?.length || 0} conditions</span>
              <span>·</span>
              <span>{canvasData.actions?.length || 0} actions</span>
              {selectedTemplate && !selectedWorkflow && (
                <>
                  <span className="ml-auto" />
                  <button
                    onClick={() => handleCloneTemplate(selectedTemplate)}
                    disabled={cloning}
                    className="flex items-center gap-1 px-3 py-1 bg-warroom-accent text-white rounded-lg hover:bg-warroom-accent/80 transition disabled:opacity-40"
                  >
                    {cloning ? <Loader2 size={12} className="animate-spin" /> : <Copy size={12} />}
                    Use This Template
                  </button>
                </>
              )}
            </div>
            {/* React Flow Canvas */}
            <div className="flex-1">
              <WorkflowCanvas workflow={canvasData} readOnly={!!selectedTemplate && !selectedWorkflow} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
