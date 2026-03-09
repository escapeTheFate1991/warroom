"use client";

import { useState, useEffect, useCallback } from "react";
import {
  X, DollarSign, Calendar, User, Building2, Clock, AlertTriangle,
  CheckCircle, ChevronRight, ArrowRight, Loader2, Edit, Phone, Mail,
  FileText, MessageSquare,
} from "lucide-react";
import { Deal, DealFull, Activity, PipelineStage } from "./types";
import { API, authFetch } from "@/lib/api";
import AgentAssignmentCard from "@/components/agents/AgentAssignmentCard";
import CallEvidence, { getCallEvidence } from "./CallEvidence";
import QuickActions from "@/components/communications/QuickActions";

interface DealDetailDrawerProps {
  deal: Deal;
  stages: PipelineStage[];
  onClose: () => void;
  onAdvance: (deal: Deal, fromStage: PipelineStage, toStage: PipelineStage) => void;
}

const STAGE_COLORS: Record<number, string> = {
  0: "bg-red-500/20 text-red-400 border-red-500/30",
  10: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  20: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  40: "bg-blue-600/20 text-blue-300 border-blue-600/30",
  60: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  80: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  100: "bg-green-500/20 text-green-400 border-green-500/30",
};

const ACTIVITY_ICONS: Record<string, typeof FileText> = {
  call: Phone, meeting: User, email: Mail, note: FileText, task: CheckCircle,
};

export default function DealDetailDrawer({ deal, stages, onClose, onAdvance }: DealDetailDrawerProps) {
  const [fullDeal, setFullDeal] = useState<DealFull | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loadingFull, setLoadingFull] = useState(true);
  const [loadingActivities, setLoadingActivities] = useState(true);

  // Escape key handler
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Fetch full deal + activities
  useEffect(() => {
    const fetchData = async () => {
      setLoadingFull(true);
      setLoadingActivities(true);
      try {
        const res = await authFetch(`${API}/api/crm/deals/${deal.id}`);
        if (res.ok) setFullDeal(await res.json());
      } catch { /* fallback to basic deal data */ }
      finally { setLoadingFull(false); }

      try {
        const res = await authFetch(`${API}/api/crm/activities?deal_id=${deal.id}`);
        if (res.ok) setActivities(await res.json());
      } catch { /* show empty state */ }
      finally { setLoadingActivities(false); }
    };
    fetchData();
  }, [deal.id]);

  const fmt = (n: number | null) => {
    if (!n) return "$0";
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
  };
  const fmtDate = (d: string | null) => d ? new Date(d).toLocaleDateString() : "—";

  const currentStage = stages.find((s) => s.id === deal.stage_id);
  const currentStageIdx = stages.findIndex((s) => s.id === deal.stage_id);
  const stageColor = STAGE_COLORS[currentStage?.probability ?? 0] || STAGE_COLORS[0];

  // Next stage for advance button
  const nextStage = currentStageIdx >= 0 && currentStageIdx < stages.length - 1
    ? stages[currentStageIdx + 1] : null;

  const d = fullDeal; // shorthand for full data (may be null)

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 transition-opacity" onClick={onClose} />

      {/* Drawer */}
      <div className="absolute right-0 top-0 h-full w-[480px] max-w-full bg-warroom-surface border-l border-warroom-border shadow-2xl flex flex-col animate-slide-in-right">

        {/* ── Header ── */}
        <div className="flex-shrink-0 p-5 border-b border-warroom-border">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0 mr-3">
              <h2 className="text-lg font-semibold text-warroom-text truncate">{deal.title}</h2>
              {(deal.organization_name || deal.person_name) && (
                <p className="text-sm text-warroom-muted mt-0.5 truncate">
                  {deal.organization_name}{deal.organization_name && deal.person_name ? " · " : ""}{deal.person_name}
                </p>
              )}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {deal.deal_value != null && (
                  <span className="text-sm font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">{fmt(deal.deal_value)}</span>
                )}
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${stageColor}`}>
                  {currentStage?.name || "Unknown"}
                </span>
                {deal.is_rotten && (
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-1">
                    <AlertTriangle size={10} />Rotten
                  </span>
                )}
              </div>
            </div>
            <button onClick={onClose} className="text-warroom-muted hover:text-warroom-text transition p-1"><X size={20} /></button>
          </div>
        </div>

        {/* ── Scrollable Content ── */}
        <div className="flex-1 overflow-y-auto">

          {/* Contact Info */}
          <div className="p-5 border-b border-warroom-border space-y-2">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider">Contact</h3>
              <QuickActions
                phone={d?.person_phone as string | undefined}
                email={d?.person_email as string | undefined}
                name={deal.person_name || undefined}
                size="md"
              />
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {deal.person_name && (
                <div className="flex items-center gap-2 text-warroom-text"><User size={13} className="text-warroom-muted" />{deal.person_name}</div>
              )}
              {deal.organization_name && (
                <div className="flex items-center gap-2 text-warroom-text"><Building2 size={13} className="text-warroom-muted" />{deal.organization_name}</div>
              )}
              {d?.user_name && (
                <div className="col-span-2 flex items-center gap-2 text-warroom-text text-xs"><User size={12} className="text-warroom-muted" /><span className="text-warroom-muted">Assigned to:</span> {d.user_name}</div>
              )}
            </div>
          </div>

          {/* Deal Info */}
          <div className="p-5 border-b border-warroom-border">
            <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-2">Deal Info</h3>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between"><span className="text-warroom-muted">Expected Close</span><span className="text-warroom-text">{fmtDate(deal.expected_close_date)}</span></div>
              <div className="flex justify-between">
                <span className="text-warroom-muted">Days in Stage</span>
                <span className={deal.is_rotten || deal.days_in_stage > 14 ? "text-red-400 font-medium" : "text-warroom-text"}>{deal.days_in_stage} {deal.days_in_stage === 1 ? "day" : "days"}</span>
              </div>
              <div className="flex justify-between"><span className="text-warroom-muted">Created</span><span className="text-warroom-text">{fmtDate(deal.created_at)}</span></div>
              {d?.source_name && <div className="flex justify-between"><span className="text-warroom-muted">Source</span><span className="text-warroom-text">{d.source_name}</span></div>}
              {d?.type_name && <div className="flex justify-between"><span className="text-warroom-muted">Type</span><span className="text-warroom-text">{d.type_name}</span></div>}
              {(d?.description || deal.description) && (
                <div className="mt-2 p-2 bg-warroom-bg rounded text-xs text-warroom-text">{d?.description || deal.description}</div>
              )}
            </div>
          </div>

          <div className="p-5 border-b border-warroom-border">
            <AgentAssignmentCard
              entityType="crm_deal"
              entityId={deal.id}
              initialAssignments={d?.agent_assignments || deal.agent_assignments}
              title={`Work deal: ${deal.title}`}
            />
          </div>

          {/* Stage Timeline */}
          <div className="p-5 border-b border-warroom-border">
            <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-3">Stage Progress</h3>
            <div className="flex items-center gap-1">
              {stages.map((stage, idx) => {
                const isCurrent = stage.id === deal.stage_id;
                const isCompleted = idx < currentStageIdx;
                const color = STAGE_COLORS[stage.probability] || STAGE_COLORS[0];
                return (
                  <div key={stage.id} className="flex items-center gap-1 flex-1 min-w-0">
                    <div className={`flex flex-col items-center flex-1 min-w-0`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border ${
                        isCompleted ? "bg-green-500/30 border-green-500 text-green-400"
                        : isCurrent ? `${color} ring-2 ring-offset-1 ring-offset-warroom-surface ring-warroom-accent`
                        : "bg-warroom-bg border-warroom-border text-warroom-muted"
                      }`}>
                        {isCompleted ? <CheckCircle size={12} /> : idx + 1}
                      </div>
                      <span className={`text-[9px] mt-1 text-center truncate w-full ${isCurrent ? "text-warroom-text font-medium" : "text-warroom-muted"}`}>
                        {stage.name}
                      </span>
                      {isCurrent && (
                        <span className="text-[9px] text-warroom-accent">{deal.days_in_stage}d</span>
                      )}
                    </div>
                    {idx < stages.length - 1 && (
                      <div className={`h-px flex-shrink-0 w-2 ${isCompleted ? "bg-green-500/50" : "bg-warroom-border"}`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Activity History */}
          <div className="p-5">
            <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-3">Activity History</h3>
            {loadingActivities ? (
              <div className="flex items-center justify-center py-6 text-warroom-muted text-sm">
                <Loader2 size={14} className="animate-spin mr-2" />Loading…
              </div>
            ) : activities.length > 0 ? (
              <div className="space-y-2">
                {activities.map((act) => {
                  const Icon = ACTIVITY_ICONS[act.type] || FileText;
                  const evidence = act.type === "call" ? getCallEvidence(act) : null;
                  return (
                    <div key={act.id} className={`p-3 rounded-lg border ${act.is_done ? "bg-green-500/5 border-green-500/20" : "bg-warroom-bg border-warroom-border"}`}>
                      <div className="flex items-start gap-2">
                        <Icon size={14} className="text-warroom-muted mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-warroom-text truncate">{act.title}</span>
                            <span className="text-[10px] px-1.5 py-0.5 bg-warroom-border/50 rounded-full text-warroom-muted flex-shrink-0">{act.type}</span>
                          </div>
                          {act.comment && <p className="text-xs text-warroom-muted mt-0.5 line-clamp-2">{act.comment}</p>}
                          {evidence && <CallEvidence recordingUrl={evidence.recordingUrl} transcript={evidence.transcript} className="mt-2" />}
                          <span className="text-[10px] text-warroom-muted mt-1 block">{fmtDate(act.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6 text-warroom-muted">
                <MessageSquare size={24} className="mx-auto mb-1 opacity-20" />
                <p className="text-xs">No activities recorded</p>
              </div>
            )}
          </div>
        </div>

        {/* ── Quick Actions (bottom) ── */}
        <div className="flex-shrink-0 p-4 border-t border-warroom-border flex gap-2">
          {nextStage && currentStage && (
            <button
              onClick={() => onAdvance(deal, currentStage, nextStage)}
              className="flex-1 px-4 py-2.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
            >
              <ArrowRight size={14} />Advance to {nextStage.name}
            </button>
          )}
          <button
            className="flex-1 px-4 py-2.5 bg-warroom-bg border border-warroom-border hover:bg-warroom-border/30 rounded-lg text-sm font-medium text-warroom-muted transition flex items-center justify-center gap-2"
            onClick={() => {/* placeholder */}}
          >
            <Edit size={14} />Edit Deal
          </button>
        </div>
      </div>
    </div>
  );
}
