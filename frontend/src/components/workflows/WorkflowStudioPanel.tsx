"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Copy, GitBranch, History, Plus, RefreshCcw, Save, ShieldCheck, Sparkles } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import WorkflowStudio, { buildWorkflowStudioDraft, serializeWorkflowStudioDraft, type WorkflowStudioDraft } from "@/components/workflows/WorkflowStudio";

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

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function normalizeOption<T extends readonly string[]>(value: string | null | undefined, options: T) {
  return value && options.includes(value as T[number]) ? value : options[0];
}

function EmptyState({ message }: { message: string }) {
  return <div className="rounded-xl border border-dashed border-warroom-border p-8 text-sm text-warroom-muted">{message}</div>;
}

export default function WorkflowStudioPanel() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | null>(null);
  const [editorSource, setEditorSource] = useState<EditorSource>(null);
  const [editorError, setEditorError] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formEntityType, setFormEntityType] = useState<string>(ENTITY_OPTIONS[0]);
  const [formEvent, setFormEvent] = useState<string>(EVENT_OPTIONS[0]);
  const [formConditionType, setFormConditionType] = useState("and");
  const [studioDraft, setStudioDraft] = useState<WorkflowStudioDraft>(() => buildWorkflowStudioDraft([], []));
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
        throw new Error("Failed to load workflow studio data");
      }

      const [templateData, workflowData] = await Promise.all([
        templateRes.json() as Promise<WorkflowTemplate[]>,
        workflowRes.json() as Promise<WorkflowRecord[]>,
      ]);

      setTemplates(templateData);
      setWorkflows(workflowData);
      if (templateData.length > 0) {
        setSelectedTemplateId((current) => current ?? templateData[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workflow studio data");
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

  const selectedTemplateDraft = useMemo(
    () => buildWorkflowStudioDraft(selectedTemplate?.conditions, selectedTemplate?.actions),
    [selectedTemplate],
  );

  const selectedWorkflowDraft = useMemo(
    () => buildWorkflowStudioDraft(selectedWorkflow?.conditions, selectedWorkflow?.actions),
    [selectedWorkflow],
  );

  function hydrateEditor(options: {
    source: Exclude<EditorSource, null>;
    name: string;
    description: string | null;
    entityType: string | null;
    event: string | null;
    conditionType: string | null;
    conditions: unknown;
    actions: unknown;
    isActive: boolean;
  }) {
    setEditorSource(options.source);
    setEditorError(null);
    setFormName(options.name);
    setFormDescription(options.description || "");
    setFormEntityType(normalizeOption(options.entityType, ENTITY_OPTIONS));
    setFormEvent(normalizeOption(options.event, EVENT_OPTIONS));
    setFormConditionType(options.conditionType === "or" ? "or" : "and");
    setStudioDraft(buildWorkflowStudioDraft(options.conditions, options.actions));
    setFormIsActive(options.isActive);
  }

  function resetEditor() {
    setEditorSource(null);
    setEditorError(null);
    setSaving(false);
  }

  function startFromTemplate(template: WorkflowTemplate) {
    setSelectedTemplateId(template.id);
    setSelectedWorkflowId(null);
    hydrateEditor({
      source: { kind: "template", id: template.id },
      name: `${template.name} — custom`,
      description: template.description,
      entityType: template.entity_type,
      event: template.event,
      conditionType: template.condition_type,
      conditions: template.conditions,
      actions: template.actions,
      isActive: false,
    });
  }

  function startBlankWorkflow() {
    setSelectedWorkflowId(null);
    hydrateEditor({
      source: { kind: "blank" },
      name: "",
      description: "",
      entityType: ENTITY_OPTIONS[0],
      event: EVENT_OPTIONS[0],
      conditionType: "and",
      conditions: [],
      actions: [],
      isActive: true,
    });
  }

  function startFromWorkflow(workflow: WorkflowRecord) {
    setSelectedWorkflowId(workflow.id);
    setSelectedTemplateId(workflow.template_id);
    hydrateEditor({
      source: { kind: "workflow", id: workflow.id },
      name: `${workflow.name} v${workflow.version + 1}`,
      description: workflow.description,
      entityType: workflow.entity_type,
      event: workflow.event,
      conditionType: workflow.condition_type,
      conditions: workflow.conditions,
      actions: workflow.actions,
      isActive: workflow.is_active,
    });
  }

  function importSelectedTemplateIntoStudio() {
    if (!editorSource || !selectedTemplate) return;
    setEditorError(null);
    setFormEntityType(normalizeOption(selectedTemplate.entity_type, ENTITY_OPTIONS));
    setFormEvent(normalizeOption(selectedTemplate.event, EVENT_OPTIONS));
    setFormConditionType(selectedTemplate.condition_type === "or" ? "or" : "and");
    setStudioDraft(buildWorkflowStudioDraft(selectedTemplate.conditions, selectedTemplate.actions));
    if (!formName.trim()) setFormName(`${selectedTemplate.name} — custom`);
    if (!formDescription.trim()) setFormDescription(selectedTemplate.description || "");
  }

  async function handleSaveAsNew(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editorSource || !formName.trim()) return;

    const { conditions, actions } = serializeWorkflowStudioDraft(studioDraft);

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
            entity_type: formEntityType,
            event: formEvent,
            condition_type: formConditionType,
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
      setEditorError(err instanceof Error ? err.message : "Failed to save workflow version");
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
              Workflow Studio
            </h2>
            <p className="mt-1 text-xs text-warroom-muted">
              Open starter templates, drag/reorder nodes, edit edges and step metadata, then save versioned custom workflows.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={startBlankWorkflow}
              className="inline-flex items-center gap-1.5 rounded-lg bg-warroom-accent px-3 py-1.5 text-xs font-medium text-white transition hover:bg-warroom-accent/80"
            >
              <Plus size={13} />
              New workflow
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
              Starter gallery
            </div>
            <div className="mt-3 space-y-2">
              {templates.map((template) => (
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
                  <p className="mt-2 text-[10px] text-warroom-muted">
                    {template.entity_type} • {template.event}
                  </p>
                </button>
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
                    <p className="mt-1 text-[11px] text-warroom-muted">{workflow.provenance.template_name || "No template"}</p>
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
                        ? "Customize starter as new workflow"
                        : "Create a new workflow version"}
                  </h3>
                  <p className="mt-1 text-sm text-warroom-muted">
                    {editorSource.kind === "blank"
                      ? "Use the blank canvas when none of the starters fit and build the flow visually."
                      : "Studio edits preserve the source record and save a versioned custom workflow."}
                  </p>
                </div>
                <button type="button" onClick={resetEditor} className="text-sm text-warroom-muted transition hover:text-warroom-text">
                  Cancel
                </button>
              </div>

              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                <input
                  value={formName}
                  onChange={(event) => setFormName(event.target.value)}
                  placeholder="Workflow name"
                  className="rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                  required
                />
                <div className="rounded-xl border border-warroom-border bg-warroom-surface/40 px-3 py-2 text-sm text-warroom-muted">
                  <div className="text-[11px] uppercase tracking-wide">Import into canvas</div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <div className="min-w-0 text-warroom-text">{selectedTemplate?.name || "Select a starter from the gallery"}</div>
                    <button
                      type="button"
                      onClick={importSelectedTemplateIntoStudio}
                      disabled={!selectedTemplate}
                      className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-warroom-border px-2.5 py-1.5 text-xs text-warroom-text transition hover:border-warroom-accent disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <Copy size={12} />
                      Import starter
                    </button>
                  </div>
                </div>
              </div>

              <textarea
                value={formDescription}
                onChange={(event) => setFormDescription(event.target.value)}
                placeholder="Describe what this workflow should do"
                rows={3}
                className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
              />

              <WorkflowStudio
                draft={studioDraft}
                entityType={formEntityType}
                event={formEvent}
                conditionType={formConditionType}
                entityOptions={ENTITY_OPTIONS}
                eventOptions={EVENT_OPTIONS}
                onDraftChange={setStudioDraft}
                onEntityTypeChange={setFormEntityType}
                onEventChange={setFormEvent}
                onConditionTypeChange={setFormConditionType}
              />

              <label className="inline-flex items-center gap-2 text-sm text-warroom-muted">
                <input type="checkbox" checked={formIsActive} onChange={(event) => setFormIsActive(event.target.checked)} />
                Mark this saved version as active
              </label>

              {editorError && <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">{editorError}</div>}

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
                  Open in studio
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
                    <dd className="mt-1 text-warroom-text">
                      {selectedWorkflow.entity_type} • {selectedWorkflow.event}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-warroom-muted">Saved</dt>
                    <dd className="mt-1 text-warroom-text">{formatDate(selectedWorkflow.updated_at)}</dd>
                  </div>
                </dl>
              </div>

              <WorkflowStudio
                draft={selectedWorkflowDraft}
                entityType={selectedWorkflow.entity_type || ""}
                event={selectedWorkflow.event || ""}
                conditionType={selectedWorkflow.condition_type || "and"}
                entityOptions={ENTITY_OPTIONS}
                eventOptions={EVENT_OPTIONS}
                readOnly
              />
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
                  Open in studio
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

              <WorkflowStudio
                draft={selectedTemplateDraft}
                entityType={selectedTemplate.entity_type || ""}
                event={selectedTemplate.event || ""}
                conditionType={selectedTemplate.condition_type || "and"}
                entityOptions={ENTITY_OPTIONS}
                eventOptions={EVENT_OPTIONS}
                readOnly
              />
            </div>
          ) : (
            <EmptyState message="Select a workflow starter from the gallery to preview or open it in Workflow Studio." />
          )}
        </section>
      </div>
    </div>
  );
}