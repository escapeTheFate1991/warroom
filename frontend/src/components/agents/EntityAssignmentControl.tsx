"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Bot, Loader2, Plus, X } from "lucide-react";

import type {
  AgentAssignmentSummary,
  AgentSummary,
  AssignableEntityType,
} from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";
import AskAIButton from "@/components/agents/AskAIButton";

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-yellow-500/15 text-yellow-300 border-yellow-500/30",
  running: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  completed: "bg-green-500/15 text-green-300 border-green-500/30",
  failed: "bg-red-500/15 text-red-300 border-red-500/30",
  cancelled: "bg-warroom-border/40 text-warroom-muted border-warroom-border",
};

type Props = {
  entityType: AssignableEntityType;
  entityId: string | number | null | undefined;
  title?: string;
  initialAssignments?: AgentAssignmentSummary[];
  onAssignmentsChange?: (assignments: AgentAssignmentSummary[]) => void;
  emptyLabel?: string;
  className?: string;
};

function getErrorMessage(response: Response, fallback: string) {
  return response.json().then((payload) => payload?.detail || payload?.message || fallback).catch(() => fallback);
}

function getAISurface(entityType: AssignableEntityType) {
  if (entityType.startsWith("crm_")) return "crm";
  if (entityType.startsWith("marketing_")) return "marketing";
  if (entityType === "social_account") return "social";
  return entityType === "kanban_task" || entityType === "calendar_event" ? "tasks" : "operations";
}

export default function EntityAssignmentControl({
  entityType,
  entityId,
  title,
  initialAssignments = [],
  onAssignmentsChange,
  emptyLabel = "Assign an AI agent",
  className = "",
}: Props) {
  const entityKey = entityId == null ? "" : String(entityId);
  const [assignments, setAssignments] = useState<AgentAssignmentSummary[]>(initialAssignments);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [loadingAssignments, setLoadingAssignments] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const updateAssignments = useCallback((next: AgentAssignmentSummary[]) => {
    setAssignments(next);
    onAssignmentsChange?.(next);
  }, [onAssignmentsChange]);

  const loadAssignments = useCallback(async () => {
    if (!entityKey) {
      updateAssignments([]);
      return;
    }
    setLoadingAssignments(true);
    setError("");
    try {
      const response = await authFetch(
        `${API}/api/agents/assignments?entity_type=${entityType}&entity_id=${encodeURIComponent(entityKey)}`,
      );
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to load assignments."));
      }
      updateAssignments((await response.json()) as AgentAssignmentSummary[]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load assignments.");
    } finally {
      setLoadingAssignments(false);
    }
  }, [entityKey, entityType, updateAssignments]);

  const loadAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      const response = await authFetch(`${API}/api/agents`);
      if (!response.ok) return;
      setAgents((await response.json()) as AgentSummary[]);
    } catch {
      setAgents([]);
    } finally {
      setLoadingAgents(false);
    }
  }, []);

  useEffect(() => {
    setAssignments(initialAssignments);
  }, [entityKey, initialAssignments]);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    loadAssignments();
  }, [loadAssignments]);

  const assignedAgentIds = useMemo(() => new Set(assignments.map((assignment) => assignment.agent_id)), [assignments]);
  const agentLookup = useMemo(() => Object.fromEntries(agents.map((agent) => [agent.id, agent])), [agents]);
  const availableAgents = agents.filter((agent) => !assignedAgentIds.has(agent.id));

  const assignAgent = useCallback(async () => {
    if (!entityKey || !selectedAgentId) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await authFetch(`${API}/api/agents/${selectedAgentId}/assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_type: entityType,
          entity_id: entityKey,
          title,
        }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to assign agent."));
      }
      setSelectedAgentId("");
      await loadAssignments();
    } catch (assignError) {
      setError(assignError instanceof Error ? assignError.message : "Failed to assign agent.");
    } finally {
      setSubmitting(false);
    }
  }, [entityKey, entityType, loadAssignments, selectedAgentId, title]);

  const removeAssignment = useCallback(async (assignment: AgentAssignmentSummary) => {
    setSubmitting(true);
    setError("");
    try {
      const response = await authFetch(`${API}/api/agents/${assignment.agent_id}/assignments/${assignment.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to remove assignment."));
      }
      await loadAssignments();
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Failed to remove assignment.");
    } finally {
      setSubmitting(false);
    }
  }, [loadAssignments]);

  return (
    <div className={`rounded-xl border border-warroom-border bg-warroom-bg/60 p-3 ${className}`.trim()}>
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-warroom-muted">
        <Bot size={13} className="text-warroom-accent" />
        <span>AI Agents</span>
        {(loadingAssignments || loadingAgents) && <Loader2 size={12} className="animate-spin" />}
      </div>

      <div className="mt-2 space-y-2">
        {assignments.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {assignments.map((assignment) => {
              const agent = agentLookup[assignment.agent_id];
              const name = assignment.agent_name || agent?.name || assignment.agent_id;
              const emoji = assignment.agent_emoji || agent?.emoji || "🤖";
              return (
                <div
                  key={assignment.id}
                  className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs ${STATUS_STYLES[assignment.status] || STATUS_STYLES.cancelled}`}
                >
                  <span>{emoji}</span>
                  <span className="font-medium">{name}</span>
                  <span className="capitalize opacity-80">{assignment.status}</span>
                  <button
                    type="button"
                    onClick={() => removeAssignment(assignment)}
                    disabled={submitting}
                    className="rounded-full opacity-70 transition hover:opacity-100 disabled:cursor-not-allowed"
                    title="Remove assignment"
                  >
                    <X size={12} />
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-warroom-muted">{entityKey ? emptyLabel : "Save this item first to assign an AI agent."}</p>
        )}

        <div className="flex flex-col gap-2 sm:flex-row">
          <select
            value={selectedAgentId}
            onChange={(event) => setSelectedAgentId(event.target.value)}
            disabled={!entityKey || submitting || loadingAgents || availableAgents.length === 0}
            className="flex-1 rounded-lg border border-warroom-border bg-warroom-surface px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent disabled:opacity-50"
          >
            <option value="">{availableAgents.length === 0 ? "No available agents" : "Select an agent"}</option>
            {availableAgents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.emoji ? `${agent.emoji} ` : ""}{agent.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={assignAgent}
            disabled={!entityKey || !selectedAgentId || submitting}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-warroom-accent px-3 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/85 disabled:opacity-50"
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Assign
          </button>
        </div>

        <AskAIButton
          context={{
            surface: getAISurface(entityType),
            entityType,
            entityId: entityKey,
            title,
            summary: assignments.length > 0 ? `${assignments.length} shared AI agent(s) assigned.` : emptyLabel,
            facts: [{ label: "Assigned agents", value: assignments.length }],
          }}
          disabled={!entityKey}
          emptyHint={`Ask AI about ${title || entityType.replaceAll("_", " ")}...`}
          buttonClassName="w-full sm:w-auto"
        />

        {error && <p className="text-xs text-red-300">{error}</p>}
      </div>
    </div>
  );
}