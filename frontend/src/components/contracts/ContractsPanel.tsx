"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileSignature, Plus, Send, Eye, CheckCircle2, Edit, X, Save,
  Loader2, ChevronLeft, ChevronRight, Search, Filter,
  ExternalLink, FileText, DollarSign, Clock, AlertTriangle,
  ToggleLeft, ToggleRight, ArrowLeft, Bell, Mail, BookOpen,
  PenTool, UserCheck, PartyPopper, MailWarning,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";
import EmptyState from "@/components/ui/EmptyState";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type DealStage =
  | "draft" | "exported" | "sent" | "delivered"
  | "read" | "signing" | "signed" | "active"
  | "expired" | "cancelled";

// Keep legacy type for backward compat with existing status field
type ContractStatus = "draft" | "sent" | "viewed" | "signed" | "active" | "expired" | "cancelled";

interface ContractIncludes {
  hosting: boolean;
  maintenance: boolean;
  ssl: boolean;
  backups: boolean;
  seo_basic: boolean;
  seo_advanced: boolean;
  content_updates: boolean;
  analytics: boolean;
  priority_support: boolean;
  dedicated_manager: boolean;
}

interface DealHistoryEvent {
  id: number;
  stage: DealStage;
  timestamp: string;
  note?: string;
}

interface Contract {
  id: number;
  contract_number: string;
  client_name: string;
  client_email: string;
  client_company: string;
  client_address: string;
  plan_name: string;
  monthly_price: number;
  setup_fee: number;
  term_months: number;
  auto_renew: boolean;
  cancellation_notice_days: number;
  status: ContractStatus;
  deal_stage: DealStage;
  needs_followup: boolean;
  followup_count: number;
  start_date: string;
  includes: ContractIncludes;
  created_at: string;
  sent_at: string | null;
  viewed_at: string | null;
  signed_at: string | null;
  activated_at: string | null;
  expires_at: string | null;
  exported_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  signing_at: string | null;
}

interface ContractTemplate {
  id: number;
  name: string;
  plan_name: string;
  monthly_price: number;
  setup_fee: number;
  term_months: number;
  cancellation_notice_days: number;
  includes: ContractIncludes;
}

interface ContractsResponse {
  contracts: Contract[];
  total: number;
  page: number;
  limit: number;
}

interface StatsData {
  active_count: number;
  total_mrr: number;
  pending_signatures: number;
  expiring_30_days: number;
  awaiting_signature: number;
  needs_followup: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const DEAL_STAGE_CONFIG: Record<DealStage, { label: string; bg: string; text: string; dot: string }> = {
  draft:     { label: "Draft",     bg: "bg-gray-500/20",    text: "text-gray-400",    dot: "bg-gray-400" },
  exported:  { label: "Exported",  bg: "bg-blue-500/20",    text: "text-blue-400",    dot: "bg-blue-400" },
  sent:      { label: "Sent",      bg: "bg-indigo-500/20",  text: "text-indigo-400",  dot: "bg-indigo-400" },
  delivered: { label: "Delivered", bg: "bg-purple-500/20",  text: "text-purple-400",  dot: "bg-purple-400" },
  read:      { label: "Read",      bg: "bg-amber-500/20",   text: "text-amber-400",   dot: "bg-amber-400" },
  signing:   { label: "Signing",   bg: "bg-orange-500/20",  text: "text-orange-400",  dot: "bg-orange-400" },
  signed:    { label: "Signed",    bg: "bg-green-500/20",   text: "text-green-400",   dot: "bg-green-400" },
  active:    { label: "Active",    bg: "bg-emerald-500/20", text: "text-emerald-400", dot: "bg-emerald-400" },
  expired:   { label: "Expired",   bg: "bg-slate-500/20",   text: "text-slate-400",   dot: "bg-slate-400" },
  cancelled: { label: "Cancelled", bg: "bg-red-500/20",     text: "text-red-400",     dot: "bg-red-400" },
};

/** Linear pipeline stages (excludes terminal expired/cancelled) */
const PIPELINE_STAGES: DealStage[] = [
  "draft", "exported", "sent", "read", "signing", "signed", "active",
];

const ALL_DEAL_STAGES: DealStage[] = [
  "draft", "exported", "sent", "delivered", "read", "signing", "signed", "active", "expired", "cancelled",
];

const INCLUDES_LABELS: Record<keyof ContractIncludes, string> = {
  hosting: "Hosting",
  maintenance: "Maintenance",
  ssl: "SSL Certificate",
  backups: "Backups",
  seo_basic: "Basic SEO",
  seo_advanced: "Advanced SEO",
  content_updates: "Content Updates",
  analytics: "Analytics",
  priority_support: "Priority Support",
  dedicated_manager: "Dedicated Manager",
};

const DEFAULT_INCLUDES: ContractIncludes = {
  hosting: false,
  maintenance: false,
  ssl: false,
  backups: false,
  seo_basic: false,
  seo_advanced: false,
  content_updates: false,
  analytics: false,
  priority_support: false,
  dedicated_manager: false,
};

const PER_PAGE = 25;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function DealStageBadge({ stage }: { stage: DealStage }) {
  const cfg = DEAL_STAGE_CONFIG[stage];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

/** Get the index of a stage in the pipeline, or -1 if terminal */
function pipelineIndex(stage: DealStage): number {
  return PIPELINE_STAGES.indexOf(stage);
}

/** Get the timestamp for a given pipeline stage from contract data */
function stageTimestamp(c: Contract, stage: DealStage): string | null {
  const map: Partial<Record<DealStage, string | null>> = {
    draft: c.created_at,
    exported: c.exported_at,
    sent: c.sent_at,
    read: c.read_at ?? c.viewed_at,
    signing: c.signing_at,
    signed: c.signed_at,
    active: c.activated_at,
  };
  return map[stage] ?? null;
}

/* ------------------------------------------------------------------ */
/*  Sub-Components                                                     */
/* ------------------------------------------------------------------ */

/** Horizontal deal pipeline stepper */
function DealPipeline({ contract }: { contract: Contract }) {
  const currentIdx = pipelineIndex(contract.deal_stage);
  const isTerminal = currentIdx === -1; // expired or cancelled

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-warroom-text mb-4">Deal Pipeline</h3>
      <div className="flex items-start">
        {PIPELINE_STAGES.map((stage, i) => {
          const isCompleted = !isTerminal && i < currentIdx;
          const isCurrent = !isTerminal && i === currentIdx;
          const isFuture = isTerminal || i > currentIdx;
          const ts = stageTimestamp(contract, stage);
          const cfg = DEAL_STAGE_CONFIG[stage];

          return (
            <div key={stage} className="flex items-start flex-1">
              <div className="flex flex-col items-center min-w-0">
                {/* Circle */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
                    isCompleted
                      ? "bg-green-500/20 text-green-400 border-green-500"
                      : isCurrent
                        ? "bg-warroom-accent/20 text-warroom-accent border-warroom-accent animate-pulse"
                        : "bg-warroom-bg text-warroom-muted border-warroom-border"
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 size={16} />
                  ) : (
                    <span className={`w-2.5 h-2.5 rounded-full ${isCurrent ? cfg.dot : "bg-warroom-border"}`} />
                  )}
                </div>
                {/* Label */}
                <p className={`text-xs mt-1.5 text-center ${
                  isCompleted || isCurrent ? "text-warroom-text font-medium" : "text-warroom-muted"
                }`}>
                  {cfg.label}
                </p>
                {/* Timestamp */}
                {(isCompleted || isCurrent) && ts && (
                  <p className="text-[10px] text-warroom-muted text-center">{formatDate(ts)}</p>
                )}
                {isFuture && <p className="text-[10px] text-warroom-muted/40 text-center">—</p>}
              </div>
              {/* Connector line */}
              {i < PIPELINE_STAGES.length - 1 && (
                <div className={`flex-1 h-0.5 mt-4 mx-1 ${
                  isCompleted ? "bg-green-500/60" : "bg-warroom-border"
                }`} />
              )}
            </div>
          );
        })}
      </div>
      {/* Terminal state banner */}
      {isTerminal && (
        <div className={`mt-4 px-3 py-2 rounded-lg text-sm font-medium ${DEAL_STAGE_CONFIG[contract.deal_stage].bg} ${DEAL_STAGE_CONFIG[contract.deal_stage].text}`}>
          Contract is {DEAL_STAGE_CONFIG[contract.deal_stage].label.toLowerCase()}
        </div>
      )}
    </div>
  );
}

/** Deal action buttons based on current stage */
function DealActions({
  contract,
  actionLoading,
  onAction,
}: {
  contract: Contract;
  actionLoading: string | null;
  onAction: (action: string, id: number) => void;
}) {
  const stage = contract.deal_stage;
  const id = contract.id;

  const isLoading = (key: string) => actionLoading === `${key}-${id}`;

  const ActionButton = ({
    actionKey, label, icon: Icon, color, badge,
  }: {
    actionKey: string;
    label: string;
    icon: React.ComponentType<{ size?: number | string; className?: string }>;
    color: string;
    badge?: number;
  }) => (
    <button
      onClick={() => onAction(actionKey, id)}
      disabled={isLoading(actionKey)}
      className={`relative flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${color}`}
    >
      {isLoading(actionKey) ? <Loader2 size={16} className="animate-spin" /> : <Icon size={16} />}
      {label}
      {badge !== undefined && badge > 0 && (
        <span className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-orange-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
          {badge}
        </span>
      )}
    </button>
  );

  const buttons: React.ReactNode[] = [];

  if (stage === "draft") {
    buttons.push(
      <ActionButton key="export" actionKey="export-gdoc" label="Export to Google Docs" icon={FileText} color="bg-blue-500/20 text-blue-400 hover:bg-blue-500/30" />
    );
  }

  if (stage === "exported") {
    buttons.push(
      <ActionButton key="send-sig" actionKey="send-for-signature" label="Send for Signature" icon={PenTool} color="bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30" />
    );
  }

  if (stage === "sent") {
    buttons.push(
      <ActionButton key="mark-read" actionKey="mark-read" label="Mark as Read" icon={BookOpen} color="bg-amber-500/20 text-amber-400 hover:bg-amber-500/30" />,
      <ActionButton key="followup" actionKey="send-followup" label="Send Follow-up" icon={MailWarning} color="bg-orange-500/20 text-orange-400 hover:bg-orange-500/30" badge={contract.followup_count} />
    );
  }

  if (stage === "read") {
    buttons.push(
      <ActionButton key="mark-signing" actionKey="mark-signing" label="Mark as Signing" icon={PenTool} color="bg-orange-500/20 text-orange-400 hover:bg-orange-500/30" />,
      <ActionButton key="followup" actionKey="send-followup" label="Send Follow-up" icon={MailWarning} color="bg-orange-500/20 text-orange-400 hover:bg-orange-500/30" badge={contract.followup_count} />
    );
  }

  if (stage === "signing") {
    buttons.push(
      <ActionButton key="mark-signed" actionKey="mark-signed" label="Mark as Signed" icon={CheckCircle2} color="bg-green-500/20 text-green-400 hover:bg-green-500/30" />
    );
  }

  if (stage === "signed") {
    buttons.push(
      <ActionButton key="welcome" actionKey="send-congratulation" label="Send Welcome Email" icon={PartyPopper} color="bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30" />
    );
  }

  if (buttons.length === 0) return null;

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-warroom-text mb-3">Deal Actions</h3>
      <div className="flex flex-wrap gap-3">
        {buttons}
      </div>
    </div>
  );
}

/** Vertical timeline of deal history events */
function DealTimeline({ events }: { events: DealHistoryEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-warroom-text mb-3">Deal Timeline</h3>
        <p className="text-sm text-warroom-muted">No history events yet.</p>
      </div>
    );
  }

  // Most recent first
  const sorted = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-warroom-text mb-4">Deal Timeline</h3>
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[9px] top-2 bottom-2 w-0.5 bg-warroom-border" />
        <div className="space-y-4">
          {sorted.map((event) => {
            const cfg = DEAL_STAGE_CONFIG[event.stage];
            return (
              <div key={event.id} className="relative flex items-start gap-3 pl-0">
                {/* Dot */}
                <div className={`relative z-10 w-[18px] h-[18px] rounded-full border-2 border-warroom-surface flex items-center justify-center flex-shrink-0 ${cfg.dot}`}>
                  <div className="w-2 h-2 rounded-full bg-warroom-surface" />
                </div>
                {/* Content */}
                <div className="min-w-0 flex-1 -mt-0.5">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${cfg.text}`}>{cfg.label}</span>
                    <span className="text-xs text-warroom-muted">{formatDateTime(event.timestamp)}</span>
                  </div>
                  {event.note && (
                    <p className="text-xs text-warroom-muted mt-0.5">{event.note}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function ContractsPanel() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<DealStage | "">("");
  const [searchQuery, setSearchQuery] = useState("");
  const [stats, setStats] = useState<StatsData>({
    active_count: 0, total_mrr: 0, pending_signatures: 0,
    expiring_30_days: 0, awaiting_signature: 0, needs_followup: 0,
  });

  // Detail view
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [dealTimeline, setDealTimeline] = useState<DealHistoryEvent[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Create / Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editingContract, setEditingContract] = useState<Contract | null>(null);
  const [templates, setTemplates] = useState<ContractTemplate[]>([]);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    template_id: "",
    client_name: "",
    client_email: "",
    client_company: "",
    client_address: "",
    plan_name: "",
    monthly_price: "",
    setup_fee: "",
    term_months: "12",
    auto_renew: true,
    cancellation_notice_days: "30",
    start_date: new Date().toISOString().split("T")[0],
    includes: { ...DEFAULT_INCLUDES },
  });

  /* ---- Data Loading ---- */

  const loadContracts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), limit: String(PER_PAGE) });
      if (statusFilter) params.set("status", statusFilter);
      if (searchQuery) params.set("search", searchQuery);
      const res = await authFetch(`${API}/api/contracts?${params}`);
      if (res.ok) {
        const data: ContractsResponse = await res.json();
        setContracts(data.contracts);
        setTotal(data.total);
      }
    } catch (err) {
      console.error("Failed to load contracts:", err);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, searchQuery]);

  const loadStats = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/contracts?limit=999`);
      if (!res.ok) return;
      const data: ContractsResponse = await res.json();
      const all = data.contracts;
      const active = all.filter((c) => (c.deal_stage ?? c.status) === "active");
      const awaitingSig = all.filter((c) => {
        const s = c.deal_stage ?? c.status;
        return s === "sent" || s === "delivered" || s === "read";
      });
      const followup = all.filter((c) => c.needs_followup);
      const now = Date.now();
      const thirtyDays = 30 * 24 * 60 * 60 * 1000;
      const expiring = all.filter(
        (c) => c.expires_at && new Date(c.expires_at).getTime() - now < thirtyDays && new Date(c.expires_at).getTime() > now
      );
      setStats({
        active_count: active.length,
        total_mrr: active.reduce((sum, c) => sum + c.monthly_price, 0),
        pending_signatures: awaitingSig.length,
        expiring_30_days: expiring.length,
        awaiting_signature: awaitingSig.length,
        needs_followup: followup.length,
      });
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => { loadContracts(); }, [loadContracts]);
  useEffect(() => { loadStats(); }, [loadStats]);

  const loadTemplates = async () => {
    try {
      const res = await authFetch(`${API}/api/contracts/templates`);
      if (res.ok) setTemplates(await res.json());
    } catch {
      /* silent */
    }
  };

  const loadContractDetail = async (id: number) => {
    setDetailLoading(true);
    try {
      const res = await authFetch(`${API}/api/contracts/${id}`);
      if (res.ok) setSelectedContract(await res.json());
    } catch (err) {
      console.error("Failed to load contract:", err);
    } finally {
      setDetailLoading(false);
    }
  };

  const loadDealTimeline = async (id: number) => {
    setTimelineLoading(true);
    try {
      const res = await authFetch(`${API}/api/contracts/${id}/deal-timeline`);
      if (res.ok) {
        const data = await res.json();
        setDealTimeline(Array.isArray(data) ? data : data.events ?? []);
      } else {
        setDealTimeline([]);
      }
    } catch {
      setDealTimeline([]);
    } finally {
      setTimelineLoading(false);
    }
  };

  const openDetail = (contract: Contract) => {
    setSelectedContract(contract);
    loadContractDetail(contract.id);
    loadDealTimeline(contract.id);
  };

  /* ---- Deal Actions ---- */

  const handleDealAction = async (action: string, id: number) => {
    setActionLoading(`${action}-${id}`);
    try {
      let url = "";
      let method = "POST";

      switch (action) {
        case "export-gdoc":
          url = `${API}/api/contracts/${id}/export-google-doc`;
          break;
        case "send-for-signature":
          url = `${API}/api/contracts/${id}/send-for-signature`;
          break;
        case "mark-read":
          url = `${API}/api/contracts/${id}/mark-read`;
          break;
        case "send-followup":
          url = `${API}/api/contracts/${id}/send-followup`;
          break;
        case "mark-signing":
          url = `${API}/api/contracts/${id}/mark-signing`;
          break;
        case "mark-signed":
          url = `${API}/api/contracts/${id}/mark-signed`;
          break;
        case "send-congratulation":
          url = `${API}/api/contracts/${id}/send-congratulation`;
          break;
        default:
          return;
      }

      const res = await authFetch(url, { method });
      if (res.ok) {
        // For export, open the doc URL
        if (action === "export-gdoc") {
          const data = await res.json();
          if (data.doc_url) window.open(data.doc_url, "_blank");
        }
        loadContracts();
        loadStats();
        loadContractDetail(id);
        loadDealTimeline(id);
      } else {
        const err = await res.json().catch(() => null);
        console.error(`Action ${action} failed:`, err?.detail || "Unknown error");
      }
    } catch (err) {
      console.error(`Failed to execute ${action}:`, err);
    } finally {
      setActionLoading(null);
    }
  };

  /* ---- Legacy actions (kept for compatibility) ---- */

  const handleSend = async (id: number) => {
    setActionLoading(`send-${id}`);
    try {
      const res = await authFetch(`${API}/api/contracts/${id}/send`, { method: "POST" });
      if (res.ok) { loadContracts(); loadStats(); if (selectedContract?.id === id) loadContractDetail(id); }
    } catch (err) {
      console.error("Failed to send contract:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkSigned = async (id: number) => {
    setActionLoading(`sign-${id}`);
    try {
      const res = await authFetch(`${API}/api/contracts/${id}/mark-signed`, { method: "POST" });
      if (res.ok) { loadContracts(); loadStats(); if (selectedContract?.id === id) loadContractDetail(id); }
    } catch (err) {
      console.error("Failed to mark signed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleViewHtml = (id: number) => {
    window.open(`${API}/api/contracts/${id}/html`, "_blank");
  };

  const openCreateModal = () => {
    setEditingContract(null);
    setForm({
      template_id: "",
      client_name: "",
      client_email: "",
      client_company: "",
      client_address: "",
      plan_name: "",
      monthly_price: "",
      setup_fee: "",
      term_months: "12",
      auto_renew: true,
      cancellation_notice_days: "30",
      start_date: new Date().toISOString().split("T")[0],
      includes: { ...DEFAULT_INCLUDES },
    });
    loadTemplates();
    setShowModal(true);
  };

  const openEditModal = (contract: Contract) => {
    setEditingContract(contract);
    setForm({
      template_id: "",
      client_name: contract.client_name,
      client_email: contract.client_email,
      client_company: contract.client_company,
      client_address: contract.client_address,
      plan_name: contract.plan_name,
      monthly_price: String(contract.monthly_price),
      setup_fee: String(contract.setup_fee),
      term_months: String(contract.term_months),
      auto_renew: contract.auto_renew,
      cancellation_notice_days: String(contract.cancellation_notice_days),
      start_date: contract.start_date?.split("T")[0] ?? new Date().toISOString().split("T")[0],
      includes: { ...contract.includes },
    });
    loadTemplates();
    setShowModal(true);
  };

  const handleTemplateChange = (templateId: string) => {
    setForm((prev) => ({ ...prev, template_id: templateId }));
    const tpl = templates.find((t) => String(t.id) === templateId);
    if (tpl) {
      setForm((prev) => ({
        ...prev,
        plan_name: tpl.plan_name,
        monthly_price: String(tpl.monthly_price),
        setup_fee: String(tpl.setup_fee),
        term_months: String(tpl.term_months),
        cancellation_notice_days: String(tpl.cancellation_notice_days),
        includes: { ...tpl.includes },
      }));
    }
  };

  const handleSave = async (andSend: boolean) => {
    setSaving(true);
    try {
      const body = {
        client_name: form.client_name,
        client_email: form.client_email,
        client_company: form.client_company,
        client_address: form.client_address,
        plan_name: form.plan_name,
        monthly_price: parseFloat(form.monthly_price) || 0,
        setup_fee: parseFloat(form.setup_fee) || 0,
        term_months: parseInt(form.term_months) || 12,
        auto_renew: form.auto_renew,
        cancellation_notice_days: parseInt(form.cancellation_notice_days) || 30,
        start_date: form.start_date,
        includes: form.includes,
        send: andSend,
      };

      const url = editingContract
        ? `${API}/api/contracts/${editingContract.id}`
        : `${API}/api/contracts`;
      const method = editingContract ? "PATCH" : "POST";

      const res = await authFetch(url, { method, body: JSON.stringify(body) });
      if (res.ok) {
        const savedContract: Contract = await res.json();
        setShowModal(false);
        loadContracts();
        loadStats();
        // Auto-open detail view for new contracts
        if (!editingContract && savedContract?.id) {
          openDetail(savedContract);
        }
      }
    } catch (err) {
      console.error("Failed to save contract:", err);
    } finally {
      setSaving(false);
    }
  };

  /* ---- Pagination ---- */

  const totalPages = Math.ceil(total / PER_PAGE);

  /* ---- Render: Detail View ---- */

  if (selectedContract) {
    const c = selectedContract;
    const stage = c.deal_stage ?? c.status;

    return (
      <div className="h-full overflow-y-auto p-6">
        {/* Back button */}
        <button
          onClick={() => { setSelectedContract(null); setDealTimeline([]); }}
          className="flex items-center gap-1.5 text-sm text-warroom-muted hover:text-warroom-text mb-4 transition-colors"
        >
          <ArrowLeft size={16} /> Back to Contracts
        </button>

        {detailLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-warroom-accent" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-bold text-warroom-text flex items-center gap-2">
                  {c.contract_number} <DealStageBadge stage={stage as DealStage} />
                  {c.needs_followup && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-500/20 text-orange-400" title="Follow-up needed">
                      <Bell size={12} /> Follow-up
                    </span>
                  )}
                </h2>
                <p className="text-warroom-muted mt-1">{c.client_name} — {c.client_company}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleViewHtml(c.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-border/40 text-warroom-text hover:bg-warroom-border/60 text-sm transition-colors"
                >
                  <ExternalLink size={14} /> View / Print
                </button>
                <button
                  onClick={() => openEditModal(c)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-border/40 text-warroom-text hover:bg-warroom-border/60 text-sm transition-colors"
                >
                  <Edit size={14} /> Edit
                </button>
              </div>
            </div>

            {/* Deal Pipeline */}
            <DealPipeline contract={c} />

            {/* Deal Actions */}
            <DealActions
              contract={c}
              actionLoading={actionLoading}
              onAction={handleDealAction}
            />

            {/* Summary Card */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                <p className="text-xs text-warroom-muted mb-1">Plan</p>
                <p className="text-sm font-semibold text-warroom-text">{c.plan_name}</p>
              </div>
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                <p className="text-xs text-warroom-muted mb-1">Monthly Price</p>
                <p className="text-sm font-semibold text-warroom-text">{formatCurrency(c.monthly_price)}</p>
              </div>
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                <p className="text-xs text-warroom-muted mb-1">Setup Fee</p>
                <p className="text-sm font-semibold text-warroom-text">{formatCurrency(c.setup_fee)}</p>
              </div>
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                <p className="text-xs text-warroom-muted mb-1">Term</p>
                <p className="text-sm font-semibold text-warroom-text">{c.term_months} months {c.auto_renew && "(auto-renew)"}</p>
              </div>
            </div>

            {/* Client Details */}
            <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-warroom-text mb-3">Client Details</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-warroom-muted">Email:</span> <span className="text-warroom-text ml-2">{c.client_email}</span></div>
                <div><span className="text-warroom-muted">Company:</span> <span className="text-warroom-text ml-2">{c.client_company}</span></div>
                <div className="col-span-2"><span className="text-warroom-muted">Address:</span> <span className="text-warroom-text ml-2">{c.client_address}</span></div>
              </div>
            </div>

            {/* Includes */}
            <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-warroom-text mb-3">Included Services</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
                {(Object.entries(INCLUDES_LABELS) as [keyof ContractIncludes, string][]).map(([key, label]) => (
                  <div
                    key={key}
                    className={`text-xs px-2.5 py-1.5 rounded-lg text-center ${
                      c.includes[key]
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        : "bg-warroom-bg text-warroom-muted border border-warroom-border"
                    }`}
                  >
                    {label}
                  </div>
                ))}
              </div>
            </div>

            {/* Deal Timeline */}
            {timelineLoading ? (
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5 flex items-center justify-center py-10">
                <Loader2 size={20} className="animate-spin text-warroom-accent" />
              </div>
            ) : (
              <DealTimeline events={dealTimeline} />
            )}
          </div>
        )}
      </div>
    );
  }

  /* ---- Render: List View ---- */

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border">
        <div className="flex items-center gap-2.5">
          <FileSignature size={20} className="text-warroom-accent" />
          <h1 className="text-lg font-bold text-warroom-text">Contracts</h1>
          <span className="text-xs text-warroom-muted bg-warroom-bg px-2 py-0.5 rounded-full">{total}</span>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent text-white rounded-lg text-sm font-medium hover:bg-warroom-accent/80 transition-colors"
        >
          <Plus size={15} /> New Contract
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 px-6 py-3 border-b border-warroom-border bg-warroom-surface/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center">
            <CheckCircle2 size={16} className="text-emerald-400" />
          </div>
          <div>
            <p className="text-xs text-warroom-muted">Active</p>
            <p className="text-sm font-bold text-warroom-text">{stats.active_count}</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-warroom-accent/15 flex items-center justify-center">
            <DollarSign size={16} className="text-warroom-accent" />
          </div>
          <div>
            <p className="text-xs text-warroom-muted">Total MRR</p>
            <p className="text-sm font-bold text-warroom-text">{formatCurrency(stats.total_mrr)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center">
            <PenTool size={16} className="text-indigo-400" />
          </div>
          <div>
            <p className="text-xs text-warroom-muted">Awaiting Signature</p>
            <p className="text-sm font-bold text-warroom-text">{stats.awaiting_signature}</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-orange-500/15 flex items-center justify-center">
            <Bell size={16} className="text-orange-400" />
          </div>
          <div>
            <p className="text-xs text-warroom-muted">Needs Follow-up</p>
            <p className="text-sm font-bold text-warroom-text">{stats.needs_followup}</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-warroom-border">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
          <input
            type="text"
            placeholder="Search by client…"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-1.5 bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text placeholder:text-warroom-muted focus:outline-none focus:border-warroom-accent/50"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter size={14} className="text-warroom-muted" />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value as DealStage | ""); setPage(1); }}
            className="bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-2 py-1.5 focus:outline-none focus:border-warroom-accent/50"
          >
            <option value="">All Stages</option>
            {ALL_DEAL_STAGES.map((s) => (
              <option key={s} value={s}>{DEAL_STAGE_CONFIG[s].label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <LoadingState message="Loading contracts..." />
        ) : contracts.length === 0 ? (
          <EmptyState
            icon={<FileText size={40} />}
            title="No contracts yet"
            description="Create your first contract to start managing client agreements."
            action={{ label: "New Contract", onClick: openCreateModal }}
          />
        ) : (
          <table className="w-full">
            <thead className="sticky top-0 bg-warroom-surface/90 backdrop-blur-sm">
              <tr className="border-b border-warroom-border text-xs text-warroom-muted">
                <th className="text-left py-2.5 px-6 font-medium">Contract #</th>
                <th className="text-left py-2.5 px-3 font-medium">Client</th>
                <th className="text-left py-2.5 px-3 font-medium">Plan</th>
                <th className="text-right py-2.5 px-3 font-medium">Monthly</th>
                <th className="text-center py-2.5 px-3 font-medium">Deal Stage</th>
                <th className="text-left py-2.5 px-3 font-medium">Start Date</th>
                <th className="text-right py-2.5 px-6 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => {
                const stage = (c.deal_stage ?? c.status) as DealStage;
                return (
                  <tr
                    key={c.id}
                    onClick={() => openDetail(c)}
                    className="border-b border-warroom-border/50 hover:bg-warroom-border/20 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono text-warroom-accent">{c.contract_number}</span>
                        {c.needs_followup && (
                          <span
                            className="w-2.5 h-2.5 rounded-full bg-orange-400 flex-shrink-0 animate-pulse"
                            title="Follow-up needed"
                          />
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <p className="text-sm text-warroom-text">{c.client_name}</p>
                      <p className="text-xs text-warroom-muted">{c.client_company}</p>
                    </td>
                    <td className="py-3 px-3 text-sm text-warroom-text">{c.plan_name}</td>
                    <td className="py-3 px-3 text-sm text-warroom-text text-right font-medium">{formatCurrency(c.monthly_price)}</td>
                    <td className="py-3 px-3 text-center"><DealStageBadge stage={stage} /></td>
                    <td className="py-3 px-3 text-sm text-warroom-muted">{formatDate(c.start_date)}</td>
                    <td className="py-3 px-6 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        {(stage === "draft" || stage === "exported") && (
                          <button
                            onClick={() => handleSend(c.id)}
                            disabled={actionLoading === `send-${c.id}`}
                            className="p-1.5 rounded-md hover:bg-blue-500/20 text-blue-400 transition-colors"
                            title="Send"
                          >
                            {actionLoading === `send-${c.id}` ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                          </button>
                        )}
                        <button
                          onClick={() => handleViewHtml(c.id)}
                          className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted hover:text-warroom-text transition-colors"
                          title="View HTML"
                        >
                          <Eye size={14} />
                        </button>
                        {(stage === "sent" || stage === "read" || stage === "signing") && (
                          <button
                            onClick={() => handleMarkSigned(c.id)}
                            disabled={actionLoading === `sign-${c.id}`}
                            className="p-1.5 rounded-md hover:bg-green-500/20 text-green-400 transition-colors"
                            title="Mark Signed"
                          >
                            {actionLoading === `sign-${c.id}` ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                          </button>
                        )}
                        <button
                          onClick={() => openEditModal(c)}
                          className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted hover:text-warroom-text transition-colors"
                          title="Edit"
                        >
                          <Edit size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-3 border-t border-warroom-border">
          <p className="text-xs text-warroom-muted">
            Showing {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} of {total}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted disabled:opacity-30 transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="text-xs text-warroom-muted px-2">{page} / {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted disabled:opacity-30 transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border">
              <h2 className="text-lg font-bold text-warroom-text">
                {editingContract ? "Edit Contract" : "New Contract"}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-warroom-muted hover:text-warroom-text transition-colors">
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-6 py-5 space-y-5">
              {/* Template Selector */}
              {!editingContract && (
                <div>
                  <label className="block text-xs text-warroom-muted mb-1.5">Template</label>
                  <select
                    value={form.template_id}
                    onChange={(e) => handleTemplateChange(e.target.value)}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                  >
                    <option value="">Select a template…</option>
                    {templates.map((t) => (
                      <option key={t.id} value={String(t.id)}>{t.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Client Info */}
              <div>
                <p className="text-xs text-warroom-muted mb-2 font-semibold uppercase tracking-wider">Client Information</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Name *</label>
                    <input
                      type="text"
                      value={form.client_name}
                      onChange={(e) => setForm((p) => ({ ...p, client_name: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Email *</label>
                    <input
                      type="email"
                      value={form.client_email}
                      onChange={(e) => setForm((p) => ({ ...p, client_email: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Company</label>
                    <input
                      type="text"
                      value={form.client_company}
                      onChange={(e) => setForm((p) => ({ ...p, client_company: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Address</label>
                    <input
                      type="text"
                      value={form.client_address}
                      onChange={(e) => setForm((p) => ({ ...p, client_address: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                </div>
              </div>

              {/* Plan Override */}
              <div>
                <p className="text-xs text-warroom-muted mb-2 font-semibold uppercase tracking-wider">Plan Details</p>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Plan Name</label>
                    <input
                      type="text"
                      value={form.plan_name}
                      onChange={(e) => setForm((p) => ({ ...p, plan_name: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Monthly Price</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.monthly_price}
                      onChange={(e) => setForm((p) => ({ ...p, monthly_price: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Setup Fee</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.setup_fee}
                      onChange={(e) => setForm((p) => ({ ...p, setup_fee: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                </div>
              </div>

              {/* Contract Terms */}
              <div>
                <p className="text-xs text-warroom-muted mb-2 font-semibold uppercase tracking-wider">Contract Terms</p>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Term (months)</label>
                    <input
                      type="number"
                      value={form.term_months}
                      onChange={(e) => setForm((p) => ({ ...p, term_months: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-warroom-muted mb-1">Cancellation Notice (days)</label>
                    <input
                      type="number"
                      value={form.cancellation_notice_days}
                      onChange={(e) => setForm((p) => ({ ...p, cancellation_notice_days: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div className="flex items-end">
                    <button
                      type="button"
                      onClick={() => setForm((p) => ({ ...p, auto_renew: !p.auto_renew }))}
                      className="flex items-center gap-2 text-sm text-warroom-text px-3 py-2"
                    >
                      {form.auto_renew ? (
                        <ToggleRight size={22} className="text-warroom-accent" />
                      ) : (
                        <ToggleLeft size={22} className="text-warroom-muted" />
                      )}
                      Auto-Renew
                    </button>
                  </div>
                </div>
              </div>

              {/* Start Date */}
              <div>
                <label className="block text-xs text-warroom-muted mb-1">Start Date</label>
                <input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))}
                  className="bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-3 py-2 focus:outline-none focus:border-warroom-accent/50"
                />
              </div>

              {/* Includes Checklist */}
              <div>
                <p className="text-xs text-warroom-muted mb-2 font-semibold uppercase tracking-wider">Included Services</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {(Object.entries(INCLUDES_LABELS) as [keyof ContractIncludes, string][]).map(([key, label]) => (
                    <label key={key} className="flex items-center gap-2 cursor-pointer text-sm text-warroom-text">
                      <input
                        type="checkbox"
                        checked={form.includes[key]}
                        onChange={() =>
                          setForm((p) => ({
                            ...p,
                            includes: { ...p.includes, [key]: !p.includes[key] },
                          }))
                        }
                        className="rounded border-warroom-border bg-warroom-bg text-warroom-accent focus:ring-warroom-accent/50"
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-warroom-border">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded-lg text-sm text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/30 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleSave(false)}
                disabled={saving || !form.client_name || !form.client_email}
                className="flex items-center gap-1.5 px-4 py-2 bg-warroom-border/50 text-warroom-text rounded-lg text-sm font-medium hover:bg-warroom-border/70 disabled:opacity-40 transition-colors"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Save as Draft
              </button>
              <button
                onClick={() => handleSave(true)}
                disabled={saving || !form.client_name || !form.client_email}
                className="flex items-center gap-1.5 px-4 py-2 bg-warroom-accent text-white rounded-lg text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-40 transition-colors"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                Save & Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
