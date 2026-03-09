"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, Loader2 } from "lucide-react";

import { API, authFetch } from "@/lib/api";
import type { AgentAssignmentSummary, AssignableEntityType } from "@/lib/agentAssignments";

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-yellow-500/15 text-yellow-300 border-yellow-500/30",
  running: "bg-blue-500/15 text-blue-300 border-blue-500/30",
};

type Props = {
  title?: string;
  maxItems?: number;
  entityTypes?: AssignableEntityType[];
  className?: string;
};

function getScopeLabel(assignment: AgentAssignmentSummary) {
  return assignment.title || `${assignment.entity_type.replaceAll("_", " ")} #${assignment.entity_id}`;
}

export default function ActiveAssignmentsList({
  title = "Shared agents in progress",
  maxItems = 4,
  entityTypes,
  className = "",
}: Props) {
  const [assignments, setAssignments] = useState<AgentAssignmentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const response = await authFetch(`${API}/api/agents/assignments?limit=30`);
        if (!response.ok || cancelled) return;
        setAssignments(await response.json());
      } catch {
        if (!cancelled) setAssignments([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    const interval = window.setInterval(load, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const items = useMemo(() => {
    return assignments
      .filter((assignment) => assignment.status === "queued" || assignment.status === "running")
      .filter((assignment) => !entityTypes?.length || entityTypes.includes(assignment.entity_type))
      .slice(0, maxItems);
  }, [assignments, entityTypes, maxItems]);

  return (
    <div className={`rounded-xl border border-warroom-border bg-warroom-surface p-4 ${className}`.trim()}>
      <div className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
        <Bot size={15} className="text-warroom-accent" />
        <span>{title}</span>
        {loading && <Loader2 size={13} className="animate-spin text-warroom-muted" />}
      </div>

      <div className="mt-3 space-y-2">
        {!loading && items.length === 0 && <p className="text-xs text-warroom-muted">No shared agents are actively working right now.</p>}
        {items.map((assignment) => (
          <div key={assignment.id} className="flex items-start justify-between gap-3 rounded-xl border border-warroom-border bg-warroom-bg/60 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-warroom-text">
                {assignment.agent_emoji || "🤖"} {assignment.agent_name || assignment.agent_id}
              </p>
              <p className="truncate text-xs text-warroom-muted">{getScopeLabel(assignment)}</p>
            </div>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STATUS_STYLES[assignment.status] || STATUS_STYLES.queued}`}>
              {assignment.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}