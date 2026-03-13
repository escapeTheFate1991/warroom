"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Zap } from "lucide-react";

const ENTITY_LABELS: Record<string, string> = {
  deal: "Deal",
  person: "Contact",
  activity: "Activity",
  email: "Email",
  social_event: "Instagram",
  contact_submission: "Submission",
};

const EVENT_LABELS: Record<string, string> = {
  created: "is created",
  updated: "is updated",
  deleted: "is deleted",
  stage_changed: "changes stage",
  comment_received: "receives a comment",
  dm_received: "receives a DM",
  mention: "is mentioned",
  keyword_comment: "comment matches keyword",
};

function TriggerNode({ data, selected }: NodeProps) {
  const d = data as Record<string, unknown>;
  const entityLabel = ENTITY_LABELS[d.entity_type as string] || String(d.entity_type || "");
  const eventLabel = EVENT_LABELS[d.event as string] || String(d.event || "");

  return (
    <div className={`bg-warroom-surface border-2 rounded-2xl px-5 py-4 min-w-[220px] shadow-lg transition-all ${
      selected
        ? "border-indigo-400 shadow-indigo-500/25 ring-2 ring-indigo-400/30"
        : "border-emerald-500/50 shadow-emerald-500/10"
    }`}>
      <div className="flex items-center gap-2.5 mb-2">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
          <Zap size={16} className="text-emerald-400" />
        </div>
        <div>
          <p className="text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">Trigger</p>
          <p className="text-sm font-bold text-warroom-text">When {entityLabel}</p>
        </div>
      </div>
      <p className="text-xs text-warroom-muted pl-[42px]">{eventLabel}</p>
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-warroom-surface" />
    </div>
  );
}

export default memo(TriggerNode);
