"use client";

import type { DragEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Bot, Clock3, Filter, GitBranch, GripVertical, Play, Plus, ShieldCheck, Sparkles, Trash2 } from "lucide-react";

type WorkflowNodeLane = "condition" | "action";
export type WorkflowNodeKind = "condition" | "action" | "delay" | "approval" | "ai_agent";

type StudioField = {
  id: string;
  key: string;
  value: string;
};

export type WorkflowStudioNode = {
  id: string;
  lane: WorkflowNodeLane;
  kind: WorkflowNodeKind;
  label: string;
  notes: string;
  nextId: string | null;
  fields: StudioField[];
};

export type WorkflowStudioDraft = {
  conditionNodes: WorkflowStudioNode[];
  actionNodes: WorkflowStudioNode[];
};

type WorkflowStudioProps = {
  draft: WorkflowStudioDraft;
  entityType: string;
  event: string;
  conditionType: string;
  entityOptions: readonly string[];
  eventOptions: readonly string[];
  onDraftChange?: (draft: WorkflowStudioDraft) => void;
  onEntityTypeChange?: (value: string) => void;
  onEventChange?: (value: string) => void;
  onConditionTypeChange?: (value: string) => void;
  readOnly?: boolean;
};

type StudioMetadata = {
  node_id?: string;
  kind?: WorkflowNodeKind;
  label?: string;
  notes?: string;
  next?: string | null;
};

let studioSequence = 0;

const KIND_ORDER: WorkflowNodeKind[] = ["action", "delay", "approval", "ai_agent"];

const NODE_META: Record<WorkflowNodeKind, { label: string; defaults: Array<[string, string]>; badgeClass: string; icon: typeof Filter }> = {
  condition: {
    label: "Condition",
    defaults: [
      ["field", "status"],
      ["operator", "equals"],
      ["value", "qualified"],
    ],
    badgeClass: "border-amber-500/30 bg-amber-500/10 text-amber-200",
    icon: Filter,
  },
  action: {
    label: "Action",
    defaults: [
      ["type", "custom_action"],
      ["title", "Do something important"],
    ],
    badgeClass: "border-sky-500/30 bg-sky-500/10 text-sky-200",
    icon: GitBranch,
  },
  delay: {
    label: "Delay",
    defaults: [
      ["type", "delay"],
      ["duration", "1 day"],
    ],
    badgeClass: "border-indigo-500/30 bg-indigo-500/10 text-indigo-200",
    icon: Clock3,
  },
  approval: {
    label: "Approval",
    defaults: [
      ["type", "request_approval"],
      ["approver_role", "manager"],
      ["reason", "Review before the workflow continues"],
    ],
    badgeClass: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
    icon: ShieldCheck,
  },
  ai_agent: {
    label: "AI agent",
    defaults: [
      ["type", "run_ai_agent"],
      ["agent_name", "Lead qualifier"],
      ["objective", "Summarize context and recommend the next step"],
    ],
    badgeClass: "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-200",
    icon: Bot,
  },
};

function createStudioId(prefix: string) {
  studioSequence += 1;
  return `${prefix}-${studioSequence}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function coerceStepList(value: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(value)) return value.filter(isRecord);
  if (isRecord(value)) return [value];
  return [];
}

function serializeFieldValue(value: unknown) {
  if (typeof value === "string") return value;
  return JSON.stringify(value ?? "");
}

function parseFieldValue(value: string): unknown {
  const trimmed = value.trim();
  if (!trimmed) return "";

  const looksJsonLike =
    trimmed.startsWith("{") ||
    trimmed.startsWith("[") ||
    trimmed.startsWith('"') ||
    trimmed === "true" ||
    trimmed === "false" ||
    trimmed === "null" ||
    /^-?[0-9]+(\.[0-9]+)?$/.test(trimmed);

  if (looksJsonLike) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return value;
    }
  }

  return value;
}

function defaultActionType(kind: WorkflowNodeKind) {
  if (kind === "delay") return "delay";
  if (kind === "approval") return "request_approval";
  if (kind === "ai_agent") return "run_ai_agent";
  return "custom_action";
}

function inferActionKind(step: Record<string, unknown>, meta?: StudioMetadata): WorkflowNodeKind {
  if (meta?.kind && KIND_ORDER.includes(meta.kind)) return meta.kind;
  const actionType = typeof step.type === "string" ? step.type : null;
  if (actionType === "delay") return "delay";
  if (actionType === "approval" || actionType === "request_approval") return "approval";
  if (actionType === "ai_agent" || actionType === "run_ai_agent") return "ai_agent";
  return "action";
}

function deriveNodeLabel(kind: WorkflowNodeKind, step: Record<string, unknown>, meta?: StudioMetadata) {
  if (typeof meta?.label === "string" && meta.label.trim()) return meta.label;
  if (kind === "condition") {
    const field = typeof step.field === "string" ? step.field : "field";
    const operator = typeof step.operator === "string" ? step.operator : "matches";
    const value = step.value == null ? "" : serializeFieldValue(step.value);
    return `${field} ${operator}${value ? ` ${value}` : ""}`;
  }
  if (kind === "delay") {
    return typeof step.duration === "string" && step.duration.trim() ? `Wait ${step.duration}` : "Delay step";
  }
  if (kind === "approval") {
    return typeof step.approver_role === "string" && step.approver_role.trim() ? `Approval: ${step.approver_role}` : "Approval request";
  }
  if (kind === "ai_agent") {
    return typeof step.agent_name === "string" && step.agent_name.trim() ? step.agent_name : "AI agent task";
  }
  if (typeof step.title === "string" && step.title.trim()) return step.title;
  if (typeof step.type === "string" && step.type.trim()) return step.type;
  return NODE_META[kind].label;
}

function createField(key = "", value = ""): StudioField {
  return { id: createStudioId("field"), key, value };
}

function createNode(kind: WorkflowNodeKind): WorkflowStudioNode {
  const lane: WorkflowNodeLane = kind === "condition" ? "condition" : "action";
  return {
    id: createStudioId("node"),
    lane,
    kind,
    label: NODE_META[kind].label,
    notes: "",
    nextId: null,
    fields: NODE_META[kind].defaults.map(([key, value]) => createField(key, value)),
  };
}

function buildNodesFromSteps(steps: unknown, lane: WorkflowNodeLane): WorkflowStudioNode[] {
  return coerceStepList(steps).map((step) => {
    const studio = isRecord(step._studio) ? (step._studio as StudioMetadata) : undefined;
    const kind = lane === "condition" ? "condition" : inferActionKind(step, studio);
    return {
      id: typeof studio?.node_id === "string" && studio.node_id ? studio.node_id : createStudioId("node"),
      lane,
      kind,
      label: deriveNodeLabel(kind, step, studio),
      notes: typeof studio?.notes === "string" ? studio.notes : "",
      nextId: typeof studio?.next === "string" && studio.next ? studio.next : null,
      fields: Object.entries(step)
        .filter(([key]) => key !== "_studio")
        .map(([key, value]) => createField(key, serializeFieldValue(value))),
    };
  });
}

function sanitizeDraft(draft: WorkflowStudioDraft): WorkflowStudioDraft {
  const ids = new Set([...draft.conditionNodes, ...draft.actionNodes].map((node) => node.id));
  const cleanNode = (node: WorkflowStudioNode): WorkflowStudioNode => ({
    ...node,
    nextId: node.nextId && node.nextId !== node.id && ids.has(node.nextId) ? node.nextId : null,
  });
  return {
    conditionNodes: draft.conditionNodes.map(cleanNode),
    actionNodes: draft.actionNodes.map(cleanNode),
  };
}

export function buildWorkflowStudioDraft(conditions: unknown, actions: unknown): WorkflowStudioDraft {
  return sanitizeDraft({
    conditionNodes: buildNodesFromSteps(conditions, "condition"),
    actionNodes: buildNodesFromSteps(actions, "action"),
  });
}

function serializeNodes(nodes: WorkflowStudioNode[]): Array<Record<string, unknown>> {
  return nodes.map((node) => {
    const step: Record<string, unknown> = {};
    for (const field of node.fields) {
      const key = field.key.trim();
      if (!key) continue;
      step[key] = parseFieldValue(field.value);
    }
    if (node.lane === "action" && typeof step.type !== "string") {
      step.type = defaultActionType(node.kind);
    }
    step._studio = {
      node_id: node.id,
      kind: node.kind,
      label: node.label.trim() || undefined,
      notes: node.notes.trim() || undefined,
      next: node.nextId || undefined,
    };
    return step;
  });
}

export function serializeWorkflowStudioDraft(draft: WorkflowStudioDraft) {
  const cleanDraft = sanitizeDraft(draft);
  return {
    conditions: serializeNodes(cleanDraft.conditionNodes),
    actions: serializeNodes(cleanDraft.actionNodes),
  };
}

function summarizeNode(node: WorkflowStudioNode) {
  const importantFields = node.fields.filter((field) => field.key.trim()).slice(0, 2);
  if (importantFields.length === 0) return node.kind === "condition" ? "Add field logic" : "Add action details";
  return importantFields.map((field) => `${field.key}: ${field.value}`).join(" • ");
}

function readableConditionType(value: string) {
  return value === "or" ? "Any condition can match" : "All conditions must match";
}

function displayValue(value: string) {
  return value.trim() || "Not set";
}

export default function WorkflowStudio({
  draft,
  entityType,
  event,
  conditionType,
  entityOptions,
  eventOptions,
  onDraftChange,
  onEntityTypeChange,
  onEventChange,
  onConditionTypeChange,
  readOnly = false,
}: WorkflowStudioProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);

  const allNodes = useMemo(() => [...draft.conditionNodes, ...draft.actionNodes], [draft]);
  const selectedNode = useMemo(() => allNodes.find((node) => node.id === selectedNodeId) ?? null, [allNodes, selectedNodeId]);

  useEffect(() => {
    if (selectedNodeId && !allNodes.some((node) => node.id === selectedNodeId)) {
      setSelectedNodeId(null);
    }
  }, [allNodes, selectedNodeId]);

  function commitDraft(nextDraft: WorkflowStudioDraft) {
    if (!onDraftChange) return;
    onDraftChange(sanitizeDraft(nextDraft));
  }

  function updateNode(nodeId: string, updater: (node: WorkflowStudioNode) => WorkflowStudioNode) {
    const updateCollection = (nodes: WorkflowStudioNode[]) => nodes.map((node) => (node.id === nodeId ? updater(node) : node));
    if (draft.conditionNodes.some((node) => node.id === nodeId)) {
      commitDraft({ ...draft, conditionNodes: updateCollection(draft.conditionNodes) });
      return;
    }
    commitDraft({ ...draft, actionNodes: updateCollection(draft.actionNodes) });
  }

  function removeNode(nodeId: string) {
    commitDraft({
      conditionNodes: draft.conditionNodes.filter((node) => node.id !== nodeId),
      actionNodes: draft.actionNodes.filter((node) => node.id !== nodeId),
    });
    if (selectedNodeId === nodeId) setSelectedNodeId(null);
  }

  function addNode(kind: WorkflowNodeKind) {
    const node = createNode(kind);
    if (node.lane === "condition") {
      commitDraft({ ...draft, conditionNodes: [...draft.conditionNodes, node] });
    } else {
      commitDraft({ ...draft, actionNodes: [...draft.actionNodes, node] });
    }
    setSelectedNodeId(node.id);
  }

  function reorderNode(targetLane: WorkflowNodeLane, targetIndex: number) {
    if (!draggedNodeId) return;
    const sourceNodes = targetLane === "condition" ? [...draft.conditionNodes] : [...draft.actionNodes];
    const currentIndex = sourceNodes.findIndex((node) => node.id === draggedNodeId);
    if (currentIndex === -1) return;
    const [moved] = sourceNodes.splice(currentIndex, 1);
    const insertIndex = currentIndex < targetIndex ? targetIndex - 1 : targetIndex;
    sourceNodes.splice(insertIndex, 0, moved);
    if (targetLane === "condition") {
      commitDraft({ ...draft, conditionNodes: sourceNodes });
    } else {
      commitDraft({ ...draft, actionNodes: sourceNodes });
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>, lane: WorkflowNodeLane, index: number) {
    event.preventDefault();
    reorderNode(lane, index);
    setDraggedNodeId(null);
  }

  function renderDropZone(lane: WorkflowNodeLane, index: number) {
    if (readOnly) return null;
    return (
      <div
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => handleDrop(event, lane, index)}
        className="h-2 rounded-full border border-dashed border-warroom-border bg-warroom-bg/40"
      />
    );
  }

  function renderNodeCard(node: WorkflowStudioNode) {
    const Icon = NODE_META[node.kind].icon;
    const routeTarget = node.nextId ? allNodes.find((candidate) => candidate.id === node.nextId) : null;
    const isSelected = selectedNodeId === node.id;

    return (
      <div
        key={node.id}
        draggable={!readOnly}
        onDragStart={() => setDraggedNodeId(node.id)}
        onDragEnd={() => setDraggedNodeId(null)}
        onClick={() => !readOnly && setSelectedNodeId(node.id)}
        className={`rounded-2xl border p-4 transition ${
          isSelected
            ? "border-warroom-accent bg-warroom-accent/10"
            : "border-warroom-border bg-warroom-bg/70 hover:border-warroom-accent/40"
        } ${readOnly ? "cursor-default" : "cursor-pointer"}`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${NODE_META[node.kind].badgeClass}`}>
                {NODE_META[node.kind].label}
              </span>
              <div className="flex items-center gap-1 text-xs text-warroom-muted">
                <Icon size={12} />
                {node.lane}
              </div>
            </div>
            <h4 className="mt-2 truncate text-sm font-semibold text-warroom-text">{node.label || NODE_META[node.kind].label}</h4>
          </div>
          {!readOnly && <GripVertical size={16} className="mt-0.5 shrink-0 text-warroom-muted" />}
        </div>
        <p className="mt-2 text-xs leading-5 text-warroom-muted">{summarizeNode(node)}</p>
        {node.notes && <p className="mt-2 line-clamp-2 text-xs leading-5 text-warroom-text/80">{node.notes}</p>}
        <div className="mt-3 flex items-center gap-2 text-[11px] text-warroom-muted">
          <ArrowRight size={12} className="text-warroom-accent" />
          {routeTarget ? `Routes to ${routeTarget.label}` : "Follows lane order"}
        </div>
      </div>
    );
  }

  function renderLane(lane: WorkflowNodeLane, title: string, description: string, nodes: WorkflowStudioNode[]) {
    const laneKinds = lane === "condition" ? (["condition"] as WorkflowNodeKind[]) : KIND_ORDER;
    return (
      <div className="rounded-2xl border border-warroom-border bg-warroom-surface/40 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-warroom-text">{title}</h3>
            <p className="mt-1 text-xs leading-5 text-warroom-muted">{description}</p>
          </div>
          <span className="rounded-full border border-warroom-border px-2 py-0.5 text-[11px] text-warroom-muted">{nodes.length}</span>
        </div>

        {!readOnly && (
          <div className="mt-4 flex flex-wrap gap-2">
            {laneKinds.map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={() => addNode(kind)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-warroom-border bg-warroom-bg px-2.5 py-1.5 text-xs text-warroom-text transition hover:border-warroom-accent"
              >
                <Plus size={12} />
                {NODE_META[kind].label}
              </button>
            ))}
          </div>
        )}

        <div className="mt-4 space-y-3">
          {nodes.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-warroom-border px-4 py-6 text-center text-xs text-warroom-muted">
              {readOnly ? "No nodes in this lane yet." : `Add ${title.toLowerCase()} nodes to build this workflow.`}
            </div>
          ) : (
            nodes.map((node, index) => (
              <div key={node.id} className="space-y-3">
                {renderDropZone(lane, index)}
                {renderNodeCard(node)}
              </div>
            ))
          )}
          {renderDropZone(lane, nodes.length)}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-warroom-border bg-warroom-surface/20 p-4">
      <div className={`grid gap-4 ${readOnly ? "" : "xl:grid-cols-[minmax(0,1fr)_320px]"}`}>
        <div className="space-y-4">
          <div className="rounded-2xl border border-warroom-border bg-warroom-surface/40 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
                  <Play size={15} className="text-warroom-accent" />
                  Trigger
                </div>
                <p className="mt-1 text-xs leading-5 text-warroom-muted">Define what event starts the workflow and how conditions should be evaluated.</p>
              </div>
              <span className="rounded-full border border-warroom-accent/30 bg-warroom-accent/10 px-2 py-0.5 text-[11px] uppercase text-warroom-accent">
                Workflow Studio
              </span>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-warroom-border bg-warroom-bg/70 p-3 text-sm text-warroom-muted">
                <div className="text-[11px] uppercase tracking-wide">Entity</div>
                {readOnly ? (
                  <div className="mt-2 text-warroom-text">{displayValue(entityType)}</div>
                ) : (
                  <select
                    value={entityType}
                    onChange={(event) => onEntityTypeChange?.(event.target.value)}
                    className="mt-2 w-full rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                  >
                    {entityOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="rounded-xl border border-warroom-border bg-warroom-bg/70 p-3 text-sm text-warroom-muted">
                <div className="text-[11px] uppercase tracking-wide">Event</div>
                {readOnly ? (
                  <div className="mt-2 text-warroom-text">{displayValue(event)}</div>
                ) : (
                  <select
                    value={event}
                    onChange={(eventValue) => onEventChange?.(eventValue.target.value)}
                    className="mt-2 w-full rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                  >
                    {eventOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="rounded-xl border border-warroom-border bg-warroom-bg/70 p-3 text-sm text-warroom-muted">
                <div className="text-[11px] uppercase tracking-wide">Condition logic</div>
                {readOnly ? (
                  <div className="mt-2 text-warroom-text">{readableConditionType(conditionType)}</div>
                ) : (
                  <select
                    value={conditionType}
                    onChange={(eventValue) => onConditionTypeChange?.(eventValue.target.value)}
                    className="mt-2 w-full rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                  >
                    <option value="and">All conditions must match</option>
                    <option value="or">Any condition can match</option>
                  </select>
                )}
              </div>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            {renderLane("condition", "Conditions", readableConditionType(conditionType), draft.conditionNodes)}
            {renderLane("action", "Actions", "Drag to reorder outcomes and route steps using the inspector.", draft.actionNodes)}
          </div>
        </div>

        {!readOnly && (
          <aside className="rounded-2xl border border-warroom-border bg-warroom-surface/40 p-4 xl:sticky xl:top-0 xl:h-fit">
            {selectedNode ? (
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
                      <Sparkles size={15} className="text-warroom-accent" />
                      Node inspector
                    </div>
                    <p className="mt-1 text-xs leading-5 text-warroom-muted">Edit labels, routing, and step properties without dropping to raw JSON.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeNode(selectedNode.id)}
                    className="inline-flex items-center gap-1 rounded-lg border border-red-500/20 bg-red-500/10 px-2 py-1 text-xs text-red-200 transition hover:bg-red-500/20"
                  >
                    <Trash2 size={12} />
                    Remove
                  </button>
                </div>

                {selectedNode.lane === "action" && (
                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-warroom-muted">Node type</label>
                    <select
                      value={selectedNode.kind}
                      onChange={(event) =>
                        updateNode(selectedNode.id, (node) => {
                          const nextKind = event.target.value as WorkflowNodeKind;
                          const nextFields = [...node.fields];
                          const typeIndex = nextFields.findIndex((field) => field.key === "type");
                          const nextType = defaultActionType(nextKind);
                          if (typeIndex === -1) {
                            nextFields.unshift(createField("type", nextType));
                          } else {
                            nextFields[typeIndex] = { ...nextFields[typeIndex], value: nextType };
                          }
                          return { ...node, kind: nextKind, fields: nextFields };
                        })
                      }
                      className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                    >
                      {KIND_ORDER.map((kind) => (
                        <option key={kind} value={kind}>
                          {NODE_META[kind].label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-warroom-muted">Node label</label>
                  <input
                    value={selectedNode.label}
                    onChange={(event) => updateNode(selectedNode.id, (node) => ({ ...node, label: event.target.value }))}
                    className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-warroom-muted">Notes</label>
                  <textarea
                    value={selectedNode.notes}
                    onChange={(event) => updateNode(selectedNode.id, (node) => ({ ...node, notes: event.target.value }))}
                    rows={3}
                    className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                    placeholder="Add editor notes, approval guidance, or handoff detail"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-warroom-muted">Edge routing</label>
                  <select
                    value={selectedNode.nextId ?? ""}
                    onChange={(event) => updateNode(selectedNode.id, (node) => ({ ...node, nextId: event.target.value || null }))}
                    className="w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                  >
                    <option value="">Automatic lane order</option>
                    {allNodes
                      .filter((node) => node.id !== selectedNode.id)
                      .map((node) => (
                        <option key={node.id} value={node.id}>
                          {node.label}
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <label className="block text-xs font-semibold uppercase tracking-wide text-warroom-muted">Properties</label>
                    <button
                      type="button"
                      onClick={() => updateNode(selectedNode.id, (node) => ({ ...node, fields: [...node.fields, createField()] }))}
                      className="inline-flex items-center gap-1 rounded-lg border border-warroom-border px-2 py-1 text-xs text-warroom-text transition hover:border-warroom-accent"
                    >
                      <Plus size={12} />
                      Add property
                    </button>
                  </div>

                  <div className="space-y-3">
                    {selectedNode.fields.map((field) => (
                      <div key={field.id} className="rounded-xl border border-warroom-border bg-warroom-bg/60 p-3">
                        <div className="flex items-start gap-2">
                          <input
                            value={field.key}
                            onChange={(event) =>
                              updateNode(selectedNode.id, (node) => ({
                                ...node,
                                fields: node.fields.map((candidate) =>
                                  candidate.id === field.id ? { ...candidate, key: event.target.value } : candidate,
                                ),
                              }))
                            }
                            placeholder="property"
                            className="flex-1 rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text outline-none focus:border-warroom-accent"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              updateNode(selectedNode.id, (node) => ({
                                ...node,
                                fields: node.fields.filter((candidate) => candidate.id !== field.id),
                              }))
                            }
                            className="rounded-lg border border-warroom-border px-2 py-2 text-warroom-muted transition hover:border-red-500/30 hover:text-red-200"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                        <textarea
                          value={field.value}
                          onChange={(event) =>
                            updateNode(selectedNode.id, (node) => ({
                              ...node,
                              fields: node.fields.map((candidate) =>
                                candidate.id === field.id ? { ...candidate, value: event.target.value } : candidate,
                              ),
                            }))
                          }
                          rows={2}
                          placeholder="value"
                          className="mt-2 w-full rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 font-mono text-xs text-warroom-text outline-none focus:border-warroom-accent"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-warroom-border px-4 py-8 text-center text-sm text-warroom-muted">
                Select a node to edit labels, edges, and step properties.
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}