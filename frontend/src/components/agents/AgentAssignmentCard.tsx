"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, Loader2, Plus, X } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import type { AgentAssignmentSummary, AgentSummary, AssignableEntityType } from "@/lib/agentAssignments";
import AskAIButton from "@/components/agents/AskAIButton";

function getAISurface(entityType: AssignableEntityType) {
  if (entityType.startsWith("crm_")) return "crm";
  if (entityType.startsWith("marketing_")) return "marketing";
  if (entityType === "social_account") return "social";
  return entityType === "kanban_task" || entityType === "calendar_event" ? "tasks" : "operations";
}

type Props = {
  entityType: AssignableEntityType;
  entityId: number | string;
  title: string;
  initialAssignments?: AgentAssignmentSummary[];
  className?: string;
};

export default function AgentAssignmentCard({ entityType, entityId, title, initialAssignments = [], className = "" }: Props) {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [assignments, setAssignments] = useState<AgentAssignmentSummary[]>(initialAssignments);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => setAssignments(initialAssignments), [entityType, entityId, initialAssignments]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const [agentsRes, assignmentsRes] = await Promise.all([
          authFetch(`${API}/api/agents`),
          authFetch(`${API}/api/agents/assignments?entity_type=${entityType}&entity_id=${encodeURIComponent(String(entityId))}`),
        ]);
        if (cancelled) return;
        if (agentsRes.ok) setAgents(await agentsRes.json());
        if (assignmentsRes.ok) setAssignments(await assignmentsRes.json());
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [entityId, entityType]);

  const assignedAgentIds = useMemo(() => new Set(assignments.map((item) => item.agent_id)), [assignments]);
  const availableAgents = useMemo(() => agents.filter((agent) => !assignedAgentIds.has(agent.id)), [agents, assignedAgentIds]);

  const refreshAssignments = async () => {
    const response = await authFetch(`${API}/api/agents/assignments?entity_type=${entityType}&entity_id=${encodeURIComponent(String(entityId))}`);
    if (response.ok) setAssignments(await response.json());
  };

  const handleAssign = async () => {
    if (!selectedAgentId) return;
    setSaving(true);
    try {
      const response = await authFetch(`${API}/api/agents/${selectedAgentId}/assignments`, {
        method: "POST",
        body: JSON.stringify({ entity_type: entityType, entity_id: String(entityId), title }),
      });
      if (response.ok) {
        setSelectedAgentId("");
        await refreshAssignments();
      }
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (assignment: AgentAssignmentSummary) => {
    setSaving(true);
    try {
      const response = await authFetch(`${API}/api/agents/${assignment.agent_id}/assignments/${assignment.id}`, { method: "DELETE" });
      if (response.ok) await refreshAssignments();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`rounded-xl border border-warroom-border bg-warroom-surface p-4 ${className}`.trim()}>
      <div className="flex items-center gap-2 text-warroom-text">
        <Bot size={16} className="text-warroom-accent" />
        <h3 className="text-sm font-semibold">AI Actions</h3>
      </div>
      <p className="mt-1 text-xs text-warroom-muted">Assign AI agents to work this record.</p>
      <AskAIButton
        context={{
          surface: getAISurface(entityType),
          entityType,
          entityId: String(entityId),
          title,
          summary: assignments.length > 0 ? `${assignments.length} shared AI agent(s) assigned.` : "No AI actions assigned.",
          facts: [{ label: "Assigned agents", value: assignments.length }],
        }}
        emptyHint={`Ask AI about ${title}...`}
        className="mt-3"
      />

      <div className="mt-3 space-y-2">
        {loading ? <div className="flex items-center gap-2 text-sm text-warroom-muted"><Loader2 size={14} className="animate-spin" />Loading AI assignments…</div> : null}
        {!loading && assignments.length === 0 ? <div className="rounded-lg border border-dashed border-warroom-border px-3 py-2 text-sm text-warroom-muted">No AI actions assigned.</div> : null}
        {assignments.map((assignment) => (
          <div key={assignment.id} className="flex items-center justify-between gap-3 rounded-lg border border-warroom-border bg-warroom-bg/60 px-3 py-2">
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-warroom-text">{assignment.agent_emoji || "🤖"} {assignment.agent_name || assignment.agent_id}</div>
              <div className="text-xs text-warroom-muted capitalize">{assignment.status.replaceAll("_", " ")}</div>
            </div>
            <button type="button" onClick={() => void handleRemove(assignment)} disabled={saving} className="text-warroom-muted transition hover:text-red-400 disabled:opacity-50">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>

      <div className="mt-3 flex gap-2">
        <select value={selectedAgentId} onChange={(event) => setSelectedAgentId(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text focus:border-warroom-accent/60 focus:outline-none">
          <option value="">Assign an AI agent…</option>
          {availableAgents.map((agent) => <option key={agent.id} value={agent.id}>{agent.emoji} {agent.name}</option>)}
        </select>
        <button type="button" onClick={() => void handleAssign()} disabled={!selectedAgentId || saving} className="inline-flex items-center gap-1 rounded-lg bg-warroom-accent px-3 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:opacity-50">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          Assign
        </button>
      </div>
    </div>
  );
}