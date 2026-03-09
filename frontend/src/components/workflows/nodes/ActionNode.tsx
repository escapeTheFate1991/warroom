"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Mail, Phone, Bell, ClipboardList, Bot, Send, MessageSquare } from "lucide-react";

const ACTION_CONFIG: Record<string, { icon: typeof Mail; color: string; label: string }> = {
  send_email: { icon: Mail, color: "blue", label: "Send Email" },
  create_activity: { icon: ClipboardList, color: "amber", label: "Create Task" },
  notify_owner: { icon: Bell, color: "orange", label: "Notify Owner" },
  make_call: { icon: Phone, color: "green", label: "Make Call" },
  send_sms: { icon: MessageSquare, color: "cyan", label: "Send SMS" },
  ai_extract_details: { icon: Bot, color: "purple", label: "AI Analysis" },
  ai_generate: { icon: Bot, color: "purple", label: "AI Generate" },
  webhook: { icon: Send, color: "slate", label: "Webhook" },
};

const COLOR_MAP: Record<string, { border: string; bg: string; text: string; shadow: string }> = {
  blue: { border: "border-blue-500/50", bg: "bg-blue-500/20", text: "text-blue-400", shadow: "shadow-blue-500/10" },
  amber: { border: "border-amber-500/50", bg: "bg-amber-500/20", text: "text-amber-400", shadow: "shadow-amber-500/10" },
  orange: { border: "border-orange-500/50", bg: "bg-orange-500/20", text: "text-orange-400", shadow: "shadow-orange-500/10" },
  green: { border: "border-green-500/50", bg: "bg-green-500/20", text: "text-green-400", shadow: "shadow-green-500/10" },
  cyan: { border: "border-cyan-500/50", bg: "bg-cyan-500/20", text: "text-cyan-400", shadow: "shadow-cyan-500/10" },
  purple: { border: "border-purple-500/50", bg: "bg-purple-500/20", text: "text-purple-400", shadow: "shadow-purple-500/10" },
  slate: { border: "border-slate-500/50", bg: "bg-slate-500/20", text: "text-slate-400", shadow: "shadow-slate-500/10" },
};

function ActionNode({ data }: NodeProps) {
  const d = data as Record<string, unknown>;
  const actionType = (d.actionType as string) || "create_activity";
  const config = ACTION_CONFIG[actionType] || ACTION_CONFIG.create_activity;
  const colors = COLOR_MAP[config.color] || COLOR_MAP.blue;
  const Icon = config.icon;

  const title = String(d.title || d.subject || config.label);
  const detail = String(d.detail || d.body || d.message || "");

  return (
    <div className={`bg-warroom-surface border-2 ${colors.border} rounded-2xl px-5 py-4 min-w-[220px] shadow-lg ${colors.shadow}`}>
      <Handle type="target" position={Position.Top} className={`!w-3 !h-3 !bg-warroom-accent !border-2 !border-warroom-surface`} />
      <div className="flex items-center gap-2.5 mb-1">
        <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center`}>
          <Icon size={16} className={colors.text} />
        </div>
        <div className="min-w-0 flex-1">
          <p className={`text-[10px] ${colors.text} font-semibold uppercase tracking-wider`}>Action</p>
          <p className="text-sm font-bold text-warroom-text truncate">{title}</p>
        </div>
      </div>
      {detail && (
        <p className="text-xs text-warroom-muted pl-[42px] line-clamp-2">{detail}</p>
      )}
      <Handle type="source" position={Position.Bottom} className={`!w-3 !h-3 !bg-warroom-accent !border-2 !border-warroom-surface`} />
    </div>
  );
}

export default memo(ActionNode);
