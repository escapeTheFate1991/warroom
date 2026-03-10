"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { GitBranch } from "lucide-react";

const OPERATOR_LABELS: Record<string, string> = {
  equals: "is",
  not_equals: "is not",
  contains: "contains",
  not_contains: "doesn't contain",
  gte: "is at least",
  lte: "is at most",
  gt: "is greater than",
  lt: "is less than",
  not_empty: "has a value",
  is_empty: "is empty",
};

function ConditionNode({ data, selected }: NodeProps) {
  const d = data as Record<string, unknown>;
  const conditions = (d.conditions || []) as { field?: string; operator?: string; value?: unknown }[];

  return (
    <div className={`bg-warroom-surface border-2 rounded-2xl px-5 py-4 min-w-[220px] shadow-lg transition-all ${
      selected
        ? "border-indigo-400 shadow-indigo-500/25 ring-2 ring-indigo-400/30"
        : "border-violet-500/50 shadow-violet-500/10"
    }`}>
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-violet-500 !border-2 !border-warroom-surface" />
      <div className="flex items-center gap-2.5 mb-2">
        <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center rotate-45">
          <GitBranch size={16} className="text-violet-400 -rotate-45" />
        </div>
        <div>
          <p className="text-[10px] text-violet-400 font-semibold uppercase tracking-wider">Condition</p>
          <p className="text-sm font-bold text-warroom-text">
            {d.conditionType === "or" ? "If any match" : "If all match"}
          </p>
        </div>
      </div>
      <div className="pl-[42px] space-y-1">
        {conditions.length > 0 ? conditions.map((c, i) => (
          <p key={i} className="text-xs text-warroom-muted">
            <span className="text-warroom-text font-medium">{(c.field || "").replace(/_/g, " ")}</span>{" "}
            {OPERATOR_LABELS[c.operator || ""] || c.operator}{" "}
            {c.value != null && <span className="text-violet-400">{String(c.value)}</span>}
          </p>
        )) : (
          <p className="text-xs text-warroom-muted italic">No conditions set</p>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} id="yes" className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-warroom-surface !left-[35%]" />
      <Handle type="source" position={Position.Bottom} id="no" className="!w-3 !h-3 !bg-red-500 !border-2 !border-warroom-surface !left-[65%]" />
    </div>
  );
}

export default memo(ConditionNode);
