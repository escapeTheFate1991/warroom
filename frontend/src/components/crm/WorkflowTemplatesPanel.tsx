"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Copy, GitBranch, History, Plus, RefreshCcw, Save, ShieldCheck, Sparkles } from "lucide-react";
import { API, authFetch } from "@/lib/api";

const ENTITY_OPTIONS = ["deal", "person", "activity", "email"] as const;
const EVENT_OPTIONS = ["created", "updated", "deleted", "stage_changed"] as const;

type WorkflowTemplate = {
  id: number;
  name: string;
  description: string | null;
  category: string | null;
  entity_type: string | null;
  event: string | null;
  condition_type: string;
  conditions: unknown;
  actions: unknown;
  is_seed: boolean;
  seed_key: string | null;
  version: number;
  provenance: {
    kind: "seed" | "custom";
    seed_key: string | null;
    derived_from_template_id: number | null;
    root_template_id: number | null;
    version: number;
  };
  created_at: string;
  updated_at: string;
};

type WorkflowRecord = {
  id: number;
  name: string;
  description: string | null;
  entity_type: string | null;
  event: string | null;
  condition_type: string;
  conditions: unknown;
  actions: unknown;
  is_active: boolean;
  template_id: number | null;
  derived_from_workflow_id: number | null;
  root_workflow_id: number | null;
  version: number;
  provenance: {
    template_id: number | null;
    template_name: string | null;
    template_seed_key: string | null;
    derived_from_workflow_id: number | null;
    derived_from_workflow_name: string | null;
    root_workflow_id: number | null;
    root_workflow_name: string | null;
    version: number;
  };
  created_at: string;
  updated_at: string;
};

type EditorSource = { kind: "blank" } | { kind: "template" | "workflow"; id: number } | null;
type WorkflowStep = Record<string, unknown> & {
  type?: string;
  title?: string;
  channel?: string;
  goal?: string;
  message?: string;
  body?: string;
  subject?: string;
  duration?: string;
  sla?: string;
  sla_duration?: string;
  escalation?: Record<string, unknown>;
  activity_type?: string;
  approval_required?: boolean;
  approval_reason?: string;
  required_for?: string[];
  notes?: string;
};

type PackKey = "real-estate" | "home-services" | "general";
type TemplateSummary = {
  channels: string[];
  aiAssists: string[];
  approvals: string[];
  sla: string | null;
  escalation: string | null;
  outline: string[];
};

const PACK_ORDER: PackKey[] = ["real-estate", "home-services", "general"];
const PACK_META: Record<PackKey, { label: string; description: string }> = {
  "real-estate": {
    label: "Real estate starter pack",
    description: "Lead response, property follow-up, pipeline orchestration, and post-close nurture.",
  },
  "home-services": {
    label: "Home services starter pack",
    description: "Missed-call capture, reminders, dispatch updates, estimate follow-up, and payment nudges.",
  },
  general: {
    label: "General templates",
    description: "Existing workflow seeds that do not belong to the first domain packs.",
  },
};

function getString(value: unknown) {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function getStringArray(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function titleize(value: string) {
  return value
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDuration(value: string) {
  const match = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$/.exec(value);
  if (!match) return value;

  const [, days, hours, minutes] = match;
  const parts = [
    days ? `${days} day${days === "1" ? "" : "s"}` : null,
    hours ? `${hours} hour${hours === "1" ? "" : "s"}` : null,
    minutes ? `${minutes} min` : null,
  ].filter((part): part is string => Boolean(part));

  return parts.length > 0 ? parts.join(" ") : value;
}

function readSteps(value: unknown): WorkflowStep[] {
  if (Array.isArray(value)) {
    return value.filter((step): step is WorkflowStep => Boolean(step) && typeof step === "object");
  }
  if (value && typeof value === "object") {
    return [value as WorkflowStep];
  }
  return [];
}

function getPackKey(template: Pick<WorkflowTemplate, "seed_key">): PackKey {
  const seedKey = template.seed_key ?? "";
  if (seedKey.startsWith("starter-real-estate-")) return "real-estate";
  if (seedKey.startsWith("starter-home-services-")) return "home-services";
  return "general";
}

function getPackMeta(template: Pick<WorkflowTemplate, "seed_key">) {
  return PACK_META[getPackKey(template)];
}

function orderTemplates(templates: WorkflowTemplate[]) {
  return [...templates].sort((left, right) => {
    const packDiff = PACK_ORDER.indexOf(getPackKey(left)) - PACK_ORDER.indexOf(getPackKey(right));
    if (packDiff !== 0) return packDiff;

    const categoryDiff = (left.category ?? "").localeCompare(right.category ?? "");
    if (categoryDiff !== 0) return categoryDiff;
    return left.name.localeCompare(right.name);
  });
}

function getStepChannels(step: WorkflowStep) {
  const channels = new Set<string>();
  const explicitChannel = getString(step.channel);
  const type = getString(step.type);

  if (explicitChannel) channels.add(explicitChannel);
  if (type === "send_email") channels.add("email");
  if (type === "send_sms") channels.add("sms");
  if (type === "notify_owner") channels.add("inbox");
  if (type === "approval_gate") channels.add("manual");

  return Array.from(channels).map(titleize);
}

function summarizeEscalation(step: WorkflowStep) {
  const nestedEscalation = step.escalation;
  if (nestedEscalation && typeof nestedEscalation === "object" && !Array.isArray(nestedEscalation)) {
    const escalation = nestedEscalation as Record<string, unknown>;
    const after = getString(escalation.after);
    const channel = getString(escalation.channel);
    if (after) {
      return `Escalates after ${formatDuration(after)}${channel ? ` via ${titleize(channel)}` : ""}`;
    }
  }

  const directEscalation = getString(step.sla_duration ?? step.sla);
  return directEscalation ? `Target SLA ${formatDuration(directEscalation)}` : null;
}

function labelWorkflowStep(step: WorkflowStep) {
  const type = getString(step.type) ?? "step";

  if (type.startsWith("ai_")) {
    return `AI — ${getString(step.goal) ?? titleize(type.slice(3))}`;
  }
  if (type === "create_activity") {
    return getString(step.title) ?? `Create ${getString(step.activity_type) ?? "activity"}`;
  }
  if (type === "approval_gate") {
    const requiredFor = getStringArray(step.required_for);
    return requiredFor.length > 0 ? `Human approval — ${requiredFor[0]}` : "Human approval gate";
  }
  if (type === "delay") {
    const duration = getString(step.duration);
    return duration ? `Wait ${formatDuration(duration)}` : "Delay";
  }
  if (type === "send_email") {
    return getString(step.subject) ? `Send email — ${getString(step.subject)}` : "Send email";
  }
  if (type === "send_sms") {
    return "Send SMS";
  }
  if (type === "notify_owner") {
    return "Notify owner in inbox";
  }
  return titleize(type);
}

function buildTemplateSummary(template: WorkflowTemplate): TemplateSummary {
  const steps = readSteps(template.actions);
  const channels = Array.from(new Set(steps.flatMap(getStepChannels)));
  const aiAssists = Array.from(
    new Set(
      steps
        .filter((step) => (getString(step.type) ?? "").startsWith("ai_"))
        .map((step) => getString(step.goal) ?? titleize((getString(step.type) ?? "ai").replace(/^ai_/, ""))),
    ),
  );
  const approvals = Array.from(
    new Set(
      steps.flatMap((step) => {
        const type = getString(step.type);
        if (type === "approval_gate") {
          const requiredFor = getStringArray(step.required_for).map(titleize);
          return requiredFor.length > 0 ? requiredFor : [getString(step.notes) ?? "Human approval required"];
        }
        if (step.approval_required) {
          return [getString(step.approval_reason) ?? "Human approval required before send"];
        }
        return [];
      }),
    ),
  );
  const slaValue = steps.map((step) => getString(step.sla_duration ?? step.sla)).find((value): value is string => Boolean(value)) ?? null;
  const escalation = steps.map(summarizeEscalation).find((value): value is string => Boolean(value)) ?? null;

  return {
    channels,
    aiAssists,
    approvals,
    sla: slaValue ? formatDuration(slaValue) : null,
    escalation,
    outline: steps.map(labelWorkflowStep),
  };
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function stringifyJson(value: unknown) {
  return JSON.stringify(value ?? [], null, 2);
}

function JsonPreview({ value }: { value: unknown }) {
  return (
    <pre className="max-h-72 overflow-auto rounded-xl border border-warroom-border bg-warroom-bg/70 p-3 text-xs leading-5 text-warroom-text/90">
      {stringifyJson(value)}
    </pre>
  );
}

export default function WorkflowTemplatesPanel() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | null>(null);
  const [editorSource, setEditorSource] = useState<EditorSource>(null);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formEntityType, setFormEntityType] = useState<string>(ENTITY_OPTIONS[0]);
  const [formEvent, setFormEvent] = useState<string>(EVENT_OPTIONS[0]);
  const [formConditionType, setFormConditionType] = useState("and");
  const [formConditions, setFormConditions] = useState("[]");
  const [formActions, setFormActions] = useState("[]");
  const [formIsActive, setFormIsActive] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [templateRes, workflowRes] = await Promise.all([
        authFetch(`${API}/api/crm/workflow-templates`),
        authFetch(`${API}/api/crm/workflows`),
      ]);

      if (!templateRes.ok || !workflowRes.ok) {
        throw new Error("Failed to load workflow templates");
      }

      const [templateData, workflowData] = await Promise.all([
        templateRes.json() as Promise<WorkflowTemplate[]>,
        workflowRes.json() as Promise<WorkflowRecord[]>,
      ]);

      const orderedTemplates = orderTemplates(templateData);
      setTemplates(orderedTemplates);
      setWorkflows(workflowData);
      if (orderedTemplates.length > 0) {
        setSelectedTemplateId((current) => current ?? orderedTemplates[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workflow templates");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? null,
    [templates, selectedTemplateId],
  );

  const selectedWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.id === selectedWorkflowId) ?? null,
    [workflows, selectedWorkflowId],
  );

  const visibleWorkflows = useMemo(() => {
    if (selectedTemplateId == null) return workflows;
    return workflows.filter((workflow) => workflow.template_id === selectedTemplateId);
  }, [workflows, selectedTemplateId]);

  const templateSections = useMemo(
    () =>
      PACK_ORDER.map((packKey) => ({
        packKey,
        meta: PACK_META[packKey],
        templates: templates.filter((template) => getPackKey(template) === packKey),
      })).filter((section) => section.templates.length > 0),
    [templates],
  );

  const selectedTemplateSummary = useMemo(
    () => (selectedTemplate ? buildTemplateSummary(selectedTemplate) : null),
    [selectedTemplate],
  );

  function resetEditor() {
    setEditorSource(null);
    setJsonError(null);
    setSaving(false);
  }

  function startFromTemplate(template: WorkflowTemplate) {
    setSelectedTemplateId(template.id);
    setSelectedWorkflowId(null);
    setEditorSource({ kind: "template", id: template.id });
    setJsonError(null);
    setFormName(`${template.name} — custom`);
    setFormDescription(template.description || "");
    setFormEntityType(template.entity_type || "");
    setFormEvent(template.event || "");
    setFormConditionType(template.condition_type || "and");
    setFormConditions(stringifyJson(template.conditions));
    setFormActions(stringifyJson(template.actions));
    setFormIsActive(false);
  }

  function startBlankWorkflow() {
    setSelectedWorkflowId(null);
    setEditorSource({ kind: "blank" });
    setJsonError(null);
    setFormName("");
    setFormDescription("");
    setFormEntityType(ENTITY_OPTIONS[0]);
    setFormEvent(EVENT_OPTIONS[0]);
    setFormConditionType("and");
    setFormConditions("[]");
    setFormActions("[]");
    setFormIsActive(true);
  }

  function startFromWorkflow(workflow: WorkflowRecord) {
    setSelectedWorkflowId(workflow.id);
    setSelectedTemplateId(workflow.template_id);
    setEditorSource({ kind: "workflow", id: workflow.id });
    setJsonError(null);
    setFormName(`${workflow.name} v${workflow.version + 1}`);
    setFormDescription(workflow.description || "");
    setFormEntityType(workflow.entity_type || "");
    setFormEvent(workflow.event || "");
    setFormConditionType(workflow.condition_type || "and");
    setFormConditions(stringifyJson(workflow.conditions));
    setFormActions(stringifyJson(workflow.actions));
    setFormIsActive(workflow.is_active);
  }

  async function handleSaveAsNew(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editorSource || !formName.trim()) return;

    let conditions: unknown;
    let actions: unknown;
    try {
      conditions = JSON.parse(formConditions);
      actions = JSON.parse(formActions);
      setJsonError(null);
    } catch {
      setJsonError("Conditions and actions must be valid JSON before saving.");
      return;
    }

    setSaving(true);
    try {
      const response = await authFetch(
        editorSource.kind === "blank"
          ? `${API}/api/crm/workflows`
          : editorSource.kind === "template"
            ? `${API}/api/crm/workflow-templates/${editorSource.id}/clone`
            : `${API}/api/crm/workflows/${editorSource.id}/clone`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: formName.trim(),
            description: formDescription || null,
            entity_type: formEntityType || null,
            event: formEvent || null,
            condition_type: formConditionType || "and",
            conditions,
            actions,
            is_active: formIsActive,
          }),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to save workflow version");
      }

      const createdWorkflow = (await response.json()) as WorkflowRecord;
      await loadData();
      setSelectedTemplateId(createdWorkflow.template_id);
      setSelectedWorkflowId(createdWorkflow.id);
      resetEditor();
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : "Failed to save workflow version");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-warroom-border px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
              <GitBranch size={16} />
              Workflow templates
            </h2>
            <p className="mt-1 text-xs text-warroom-muted">
              Starter seeds stay immutable. Customizing a template or a saved workflow always creates a new versioned copy.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={startBlankWorkflow}
              className="inline-flex items-center gap-1.5 rounded-lg bg-warroom-accent px-3 py-1.5 text-xs font-medium text-white transition hover:bg-warroom-accent/80"
            >
              <Plus size={13} />
              Start from scratch
            </button>
            <button
              type="button"
              onClick={() => void loadData()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-warroom-border px-3 py-1.5 text-xs text-warroom-muted transition hover:text-warroom-text"
            >
              <RefreshCcw size={13} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[340px_minmax(0,1fr)] overflow-hidden">
        <aside className="min-h-0 overflow-y-auto border-r border-warroom-border bg-warroom-surface/40">
          <div className="border-b border-warroom-border px-4 py-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-warroom-muted">
              <Sparkles size={12} className="text-warroom-accent" />
              Template gallery
            </div>
            <div className="mt-3 space-y-4">
              {templateSections.map((section) => (
                <div key={section.packKey} className="space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-warroom-muted">{section.meta.label}</div>
                      <p className="mt-1 text-[11px] text-warroom-muted">{section.meta.description}</p>
                    </div>
                    <span className="rounded-full border border-warroom-border px-2 py-0.5 text-[10px] text-warroom-muted">
                      {section.templates.length}
                    </span>
                  </div>

                  {section.templates.map((template) => {
                    const summary = buildTemplateSummary(template);

                    return (
                      <button
                        key={template.id}
                        type="button"
                        onClick={() => {
                          setSelectedTemplateId(template.id);
                          setSelectedWorkflowId(null);
                          resetEditor();
                        }}
                        className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                          selectedTemplateId === template.id && !selectedWorkflowId
                            ? "border-warroom-accent bg-warroom-accent/10"
                            : "border-warroom-border bg-warroom-bg/60 hover:bg-warroom-surface"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium text-warroom-text">{template.name}</span>
                          <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] uppercase text-emerald-300">
                            {template.is_seed ? "seed" : "template"}
                          </span>
                        </div>
                        {template.category && <p className="mt-1 text-[11px] text-warroom-muted">{template.category}</p>}
                        <p className="mt-2 line-clamp-2 text-xs text-warroom-muted">{template.description || "No description yet."}</p>
                        <p className="mt-2 text-[10px] text-warroom-muted">{template.entity_type} • {template.event}</p>
                        <p className="mt-1 text-[10px] text-warroom-muted">
                          {(summary.channels.join(" • ") || "Manual review")}
                          {summary.sla ? ` • SLA ${summary.sla}` : ""}
                        </p>
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          <div className="px-4 py-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-warroom-muted">
              <History size={12} className="text-warroom-accent" />
              Saved workflow versions
            </div>
            <div className="mt-3 space-y-2">
              {visibleWorkflows.length === 0 ? (
                <div className="rounded-xl border border-dashed border-warroom-border px-3 py-4 text-xs text-warroom-muted">
                  No workflow versions saved for this template yet.
                </div>
              ) : (
                visibleWorkflows.map((workflow) => (
                  <button
                    key={workflow.id}
                    type="button"
                    onClick={() => {
                      setSelectedWorkflowId(workflow.id);
                      setSelectedTemplateId(workflow.template_id);
                      resetEditor();
                    }}
                    className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                      selectedWorkflowId === workflow.id
                        ? "border-warroom-accent bg-warroom-accent/10"
                        : "border-warroom-border bg-warroom-bg/60 hover:bg-warroom-surface"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-warroom-text">{workflow.name}</span>
                      <span className="rounded border border-warroom-accent/30 bg-warroom-accent/10 px-1.5 py-0.5 text-[10px] uppercase text-warroom-accent">
                        v{workflow.version}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-warroom-muted">
                      {workflow.provenance.template_name || "No template"}
                    </p>
                    <p className="mt-2 text-[10px] text-warroom-muted">
                      {workflow.is_active ? "Active" : "Draft"} • Updated {formatDate(workflow.updated_at)}
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
        </aside>

        <section className="min-h-0 overflow-y-auto p-6">
          {loading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-warroom-accent border-t-transparent" />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-200">{error}</div>
          ) : editorSource ? (
            <form onSubmit={handleSaveAsNew} className="space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-warroom-text">
                    {editorSource.kind === "blank"
                      ? "Create workflow from scratch"
                      : editorSource.kind === "template"
                        ? "Customize seed as new workflow"
                        : "Save as new workflow version"}
                  </h3>
                  <p className="mt-1 text-sm text-warroom-muted">
                    {editorSource.kind === "blank"
                      ? "Use the blank builder when none of the starter templates fit the workflow you need."
                      : "This save creates a new workflow record and preserves the source unchanged for provenance."}
                  </p>
                </div>
                <button type="button" onClick={resetEditor} className="text-sm text-warroom-muted transition hover:text-warroom-text">
                  Cancel
                </button>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <input
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Workflow name"
                  className="rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                  required
                />
                <select
                  value={formEvent}
                  onChange={(e) => setFormEvent(e.target.value)}
                  className="rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                >
                  {EVENT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
                <select
                  value={formEntityType}
                  onChange={(e) => setFormEntityType(e.target.value)}
                  className="rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                >
                  {ENTITY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
                <select
                  value={formConditionType}
                  onChange={(e) => setFormConditionType(e.target.value)}
                  className="rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                >
                  <option value="and">All conditions must match</option>
                  <option value="or">Any condition can match</option>
                </select>
              </div>

              <textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Describe what this workflow should do"
                rows={3}
                className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
              />

              <div className="grid gap-4 lg:grid-cols-2">
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-warroom-muted">Conditions JSON</label>
                  <textarea
                    value={formConditions}
                    onChange={(e) => setFormConditions(e.target.value)}
                    rows={14}
                    className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 font-mono text-xs text-warroom-text outline-none focus:border-warroom-accent"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-warroom-muted">Actions JSON</label>
                  <textarea
                    value={formActions}
                    onChange={(e) => setFormActions(e.target.value)}
                    rows={14}
                    className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 font-mono text-xs text-warroom-text outline-none focus:border-warroom-accent"
                  />
                </div>
              </div>

              <label className="inline-flex items-center gap-2 text-sm text-warroom-muted">
                <input type="checkbox" checked={formIsActive} onChange={(e) => setFormIsActive(e.target.checked)} />
                Mark this saved version as active
              </label>

              {jsonError && <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">{jsonError}</div>}

              <div className="flex justify-end gap-3">
                <button type="button" onClick={resetEditor} className="px-3 py-2 text-sm text-warroom-muted transition hover:text-warroom-text">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-xl bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Save size={14} />
                  {saving ? "Saving…" : editorSource.kind === "blank" ? "Create workflow" : "Save as new"}
                </button>
              </div>
            </form>
          ) : selectedWorkflow ? (
            <div className="space-y-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-semibold text-warroom-text">{selectedWorkflow.name}</h3>
                    <span className="rounded border border-warroom-accent/30 bg-warroom-accent/10 px-2 py-0.5 text-xs uppercase text-warroom-accent">
                      v{selectedWorkflow.version}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-warroom-muted">{selectedWorkflow.description || "No description provided."}</p>
                </div>
                <button
                  type="button"
                  onClick={() => startFromWorkflow(selectedWorkflow)}
                  className="inline-flex items-center gap-2 rounded-xl border border-warroom-border px-3 py-2 text-sm text-warroom-text transition hover:border-warroom-accent"
                >
                  <Copy size={14} />
                  Save as new version
                </button>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                  <div className="text-xs uppercase tracking-wide">Template</div>
                  <div className="mt-2 text-warroom-text">{selectedWorkflow.provenance.template_name || "Unlinked"}</div>
                </div>
                <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                  <div className="text-xs uppercase tracking-wide">Derived from</div>
                  <div className="mt-2 text-warroom-text">{selectedWorkflow.provenance.derived_from_workflow_name || "Template clone"}</div>
                </div>
                <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                  <div className="text-xs uppercase tracking-wide">Root lineage</div>
                  <div className="mt-2 text-warroom-text">{selectedWorkflow.provenance.root_workflow_name || selectedWorkflow.name}</div>
                </div>
              </div>

              <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
                  <ShieldCheck size={16} className="text-warroom-accent" />
                  Provenance
                </div>
                <dl className="mt-3 grid gap-3 text-sm md:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Seed key</dt>
                    <dd className="mt-1 text-warroom-text">{selectedWorkflow.provenance.template_seed_key || "Custom"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Status</dt>
                    <dd className="mt-1 text-warroom-text">{selectedWorkflow.is_active ? "Active" : "Draft"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Entity / event</dt>
                    <dd className="mt-1 text-warroom-text">{selectedWorkflow.entity_type} • {selectedWorkflow.event}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Saved</dt>
                    <dd className="mt-1 text-warroom-text">{formatDate(selectedWorkflow.updated_at)}</dd>
                  </div>
                </dl>
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div>
                  <h4 className="mb-2 text-sm font-semibold text-warroom-text">Conditions</h4>
                  <JsonPreview value={selectedWorkflow.conditions} />
                </div>
                <div>
                  <h4 className="mb-2 text-sm font-semibold text-warroom-text">Actions</h4>
                  <JsonPreview value={selectedWorkflow.actions} />
                </div>
              </div>
            </div>
          ) : selectedTemplate ? (
            <div className="space-y-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-semibold text-warroom-text">{selectedTemplate.name}</h3>
                    <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs uppercase text-emerald-300">
                      immutable seed
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-warroom-muted">{selectedTemplate.description || "No description provided."}</p>
                </div>
                <button
                  type="button"
                  onClick={() => startFromTemplate(selectedTemplate)}
                  className="inline-flex items-center gap-2 rounded-xl bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80"
                >
                  <Copy size={14} />
                  Customize as new
                </button>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                  <div className="text-xs uppercase tracking-wide">Category</div>
                  <div className="mt-2 text-warroom-text">{selectedTemplate.category || "General"}</div>
                </div>
                <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                  <div className="text-xs uppercase tracking-wide">Entity type</div>
                  <div className="mt-2 text-warroom-text">{selectedTemplate.entity_type}</div>
                </div>
                <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                  <div className="text-xs uppercase tracking-wide">Trigger event</div>
                  <div className="mt-2 text-warroom-text">{selectedTemplate.event}</div>
                </div>
              </div>

              {selectedTemplateSummary && (
                <>
                  <div className="grid gap-4 lg:grid-cols-3">
                    <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                      <div className="text-xs uppercase tracking-wide">Starter pack</div>
                      <div className="mt-2 text-warroom-text">{getPackMeta(selectedTemplate).label}</div>
                      <p className="mt-2 text-xs text-warroom-muted">{getPackMeta(selectedTemplate).description}</p>
                    </div>
                    <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                      <div className="text-xs uppercase tracking-wide">Primary channels</div>
                      <div className="mt-2 text-warroom-text">
                        {selectedTemplateSummary.channels.length > 0 ? selectedTemplateSummary.channels.join(" • ") : "Manual only"}
                      </div>
                      {selectedTemplateSummary.sla && <p className="mt-2 text-xs text-warroom-muted">SLA {selectedTemplateSummary.sla}</p>}
                    </div>
                    <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4 text-sm text-warroom-muted">
                      <div className="text-xs uppercase tracking-wide">Escalation</div>
                      <div className="mt-2 text-warroom-text">{selectedTemplateSummary.escalation || "No explicit escalation metadata"}</div>
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4">
                      <h4 className="text-sm font-semibold text-warroom-text">AI assists</h4>
                      <ul className="mt-3 space-y-2 text-sm text-warroom-muted">
                        {selectedTemplateSummary.aiAssists.length > 0 ? (
                          selectedTemplateSummary.aiAssists.map((item) => <li key={item}>• {item}</li>)
                        ) : (
                          <li>• No explicit AI assist metadata</li>
                        )}
                      </ul>
                    </div>
                    <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4">
                      <h4 className="text-sm font-semibold text-warroom-text">Human approval boundaries</h4>
                      <ul className="mt-3 space-y-2 text-sm text-warroom-muted">
                        {selectedTemplateSummary.approvals.length > 0 ? (
                          selectedTemplateSummary.approvals.map((item) => <li key={item}>• {item}</li>)
                        ) : (
                          <li>• No explicit approval gate</li>
                        )}
                      </ul>
                    </div>
                  </div>

                  <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4">
                    <h4 className="text-sm font-semibold text-warroom-text">Starter flow outline</h4>
                    <ol className="mt-3 space-y-2 text-sm text-warroom-muted">
                      {selectedTemplateSummary.outline.map((step, index) => (
                        <li key={`${selectedTemplate.id}-${step}-${index}`}>{index + 1}. {step}</li>
                      ))}
                    </ol>
                  </div>
                </>
              )}

              <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
                  <ShieldCheck size={16} className="text-warroom-accent" />
                  Seed provenance
                </div>
                <dl className="mt-3 grid gap-3 text-sm md:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Seed key</dt>
                    <dd className="mt-1 text-warroom-text">{selectedTemplate.seed_key || "Not assigned"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Template version</dt>
                    <dd className="mt-1 text-warroom-text">v{selectedTemplate.version}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Immutability</dt>
                    <dd className="mt-1 text-warroom-text">Starter seeds can only be cloned, never edited in place.</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Updated</dt>
                    <dd className="mt-1 text-warroom-text">{formatDate(selectedTemplate.updated_at)}</dd>
                  </div>
                </dl>
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div>
                  <h4 className="mb-2 text-sm font-semibold text-warroom-text">Seed conditions</h4>
                  <JsonPreview value={selectedTemplate.conditions} />
                </div>
                <div>
                  <h4 className="mb-2 text-sm font-semibold text-warroom-text">Seed actions</h4>
                  <JsonPreview value={selectedTemplate.actions} />
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-warroom-border p-8 text-sm text-warroom-muted">
              Select a workflow seed from the gallery to get started.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}