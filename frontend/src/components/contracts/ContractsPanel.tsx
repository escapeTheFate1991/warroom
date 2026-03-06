"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileSignature, Plus, Send, Eye, CheckCircle2, Edit, X, Save,
  Loader2, ChevronLeft, ChevronRight, Search, Filter,
  ExternalLink, FileText, DollarSign, Clock, AlertTriangle,
  ToggleLeft, ToggleRight, ArrowLeft,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

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
  start_date: string;
  includes: ContractIncludes;
  created_at: string;
  sent_at: string | null;
  viewed_at: string | null;
  signed_at: string | null;
  activated_at: string | null;
  expires_at: string | null;
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
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const STATUS_CONFIG: Record<ContractStatus, { label: string; bg: string; text: string }> = {
  draft:     { label: "Draft",     bg: "bg-gray-500/20",    text: "text-gray-400" },
  sent:      { label: "Sent",      bg: "bg-blue-500/20",    text: "text-blue-400" },
  viewed:    { label: "Viewed",    bg: "bg-amber-500/20",   text: "text-amber-400" },
  signed:    { label: "Signed",    bg: "bg-green-500/20",   text: "text-green-400" },
  active:    { label: "Active",    bg: "bg-emerald-500/20", text: "text-emerald-400" },
  expired:   { label: "Expired",   bg: "bg-orange-500/20",  text: "text-orange-400" },
  cancelled: { label: "Cancelled", bg: "bg-red-500/20",     text: "text-red-400" },
};

const ALL_STATUSES: ContractStatus[] = ["draft", "sent", "viewed", "signed", "active", "expired", "cancelled"];

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

function StatusBadge({ status }: { status: ContractStatus }) {
  const cfg = STATUS_CONFIG[status];
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

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ContractsPanel() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<ContractStatus | "">("");
  const [searchQuery, setSearchQuery] = useState("");
  const [stats, setStats] = useState<StatsData>({ active_count: 0, total_mrr: 0, pending_signatures: 0, expiring_30_days: 0 });

  // Detail view
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

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
      const active = all.filter((c) => c.status === "active");
      const pending = all.filter((c) => c.status === "sent" || c.status === "viewed");
      const now = Date.now();
      const thirtyDays = 30 * 24 * 60 * 60 * 1000;
      const expiring = all.filter((c) => c.expires_at && new Date(c.expires_at).getTime() - now < thirtyDays && new Date(c.expires_at).getTime() > now);
      setStats({
        active_count: active.length,
        total_mrr: active.reduce((sum, c) => sum + c.monthly_price, 0),
        pending_signatures: pending.length,
        expiring_30_days: expiring.length,
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

  /* ---- Actions ---- */

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
        setShowModal(false);
        loadContracts();
        loadStats();
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
    const timelineSteps = [
      { label: "Created", date: c.created_at, done: true },
      { label: "Sent", date: c.sent_at, done: !!c.sent_at },
      { label: "Viewed", date: c.viewed_at, done: !!c.viewed_at },
      { label: "Signed", date: c.signed_at, done: !!c.signed_at },
      { label: "Active", date: c.activated_at, done: c.status === "active" },
    ];

    return (
      <div className="h-full overflow-y-auto p-6">
        {/* Back button */}
        <button
          onClick={() => setSelectedContract(null)}
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
                  {c.contract_number} <StatusBadge status={c.status} />
                </h2>
                <p className="text-warroom-muted mt-1">{c.client_name} — {c.client_company}</p>
              </div>
              <div className="flex items-center gap-2">
                {(c.status === "draft" || c.status === "viewed") && (
                  <button
                    onClick={() => handleSend(c.id)}
                    disabled={actionLoading === `send-${c.id}`}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 text-sm transition-colors"
                  >
                    {actionLoading === `send-${c.id}` ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                    Send to Client
                  </button>
                )}
                <button
                  onClick={() => handleViewHtml(c.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-border/40 text-warroom-text hover:bg-warroom-border/60 text-sm transition-colors"
                >
                  <ExternalLink size={14} /> View / Print
                </button>
                <button
                  onClick={async () => {
                    setActionLoading(`gdoc-${c.id}`);
                    try {
                      const res = await authFetch(`${API}/api/contracts/${c.id}/export-google-doc`, { method: "POST" });
                      if (res.ok) {
                        const data = await res.json();
                        window.open(data.doc_url, "_blank");
                      } else {
                        const err = await res.json().catch(() => null);
                        alert(err?.detail || "Failed to export");
                      }
                    } catch { alert("Export failed"); }
                    setActionLoading(null);
                  }}
                  disabled={actionLoading === `gdoc-${c.id}`}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 text-sm transition-colors"
                >
                  {actionLoading === `gdoc-${c.id}` ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
                  Export to Google Docs
                </button>
                {(c.status === "sent" || c.status === "viewed") && (
                  <button
                    onClick={() => handleMarkSigned(c.id)}
                    disabled={actionLoading === `sign-${c.id}`}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 text-sm transition-colors"
                  >
                    {actionLoading === `sign-${c.id}` ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                    Mark Signed
                  </button>
                )}
                <button
                  onClick={() => openEditModal(c)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-border/40 text-warroom-text hover:bg-warroom-border/60 text-sm transition-colors"
                >
                  <Edit size={14} /> Edit
                </button>
              </div>
            </div>

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

            {/* Timeline */}
            <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-warroom-text mb-4">Timeline</h3>
              <div className="flex items-center gap-0">
                {timelineSteps.map((step, i) => (
                  <div key={step.label} className="flex items-center flex-1">
                    <div className="flex flex-col items-center">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                          step.done
                            ? "bg-warroom-accent/20 text-warroom-accent border-2 border-warroom-accent"
                            : "bg-warroom-bg text-warroom-muted border-2 border-warroom-border"
                        }`}
                      >
                        {i + 1}
                      </div>
                      <p className={`text-xs mt-1.5 ${step.done ? "text-warroom-text" : "text-warroom-muted"}`}>{step.label}</p>
                      <p className="text-[10px] text-warroom-muted">{formatDate(step.date)}</p>
                    </div>
                    {i < timelineSteps.length - 1 && (
                      <div className={`flex-1 h-0.5 mx-1 ${step.done ? "bg-warroom-accent/40" : "bg-warroom-border"}`} />
                    )}
                  </div>
                ))}
              </div>
            </div>
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
          <div className="w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center">
            <Clock size={16} className="text-blue-400" />
          </div>
          <div>
            <p className="text-xs text-warroom-muted">Pending Signatures</p>
            <p className="text-sm font-bold text-warroom-text">{stats.pending_signatures}</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-orange-500/15 flex items-center justify-center">
            <AlertTriangle size={16} className="text-orange-400" />
          </div>
          <div>
            <p className="text-xs text-warroom-muted">Expiring (30d)</p>
            <p className="text-sm font-bold text-warroom-text">{stats.expiring_30_days}</p>
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
            onChange={(e) => { setStatusFilter(e.target.value as ContractStatus | ""); setPage(1); }}
            className="bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text px-2 py-1.5 focus:outline-none focus:border-warroom-accent/50"
          >
            <option value="">All Statuses</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-warroom-accent" />
          </div>
        ) : contracts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
            <FileText size={40} className="mb-3 opacity-40" />
            <p className="text-sm">No contracts found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="sticky top-0 bg-warroom-surface/90 backdrop-blur-sm">
              <tr className="border-b border-warroom-border text-xs text-warroom-muted">
                <th className="text-left py-2.5 px-6 font-medium">Contract #</th>
                <th className="text-left py-2.5 px-3 font-medium">Client</th>
                <th className="text-left py-2.5 px-3 font-medium">Plan</th>
                <th className="text-right py-2.5 px-3 font-medium">Monthly</th>
                <th className="text-center py-2.5 px-3 font-medium">Status</th>
                <th className="text-left py-2.5 px-3 font-medium">Start Date</th>
                <th className="text-right py-2.5 px-6 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => { setSelectedContract(c); loadContractDetail(c.id); }}
                  className="border-b border-warroom-border/50 hover:bg-warroom-border/20 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-6 text-sm font-mono text-warroom-accent">{c.contract_number}</td>
                  <td className="py-3 px-3">
                    <p className="text-sm text-warroom-text">{c.client_name}</p>
                    <p className="text-xs text-warroom-muted">{c.client_company}</p>
                  </td>
                  <td className="py-3 px-3 text-sm text-warroom-text">{c.plan_name}</td>
                  <td className="py-3 px-3 text-sm text-warroom-text text-right font-medium">{formatCurrency(c.monthly_price)}</td>
                  <td className="py-3 px-3 text-center"><StatusBadge status={c.status} /></td>
                  <td className="py-3 px-3 text-sm text-warroom-muted">{formatDate(c.start_date)}</td>
                  <td className="py-3 px-6 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      {(c.status === "draft" || c.status === "viewed") && (
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
                      {(c.status === "sent" || c.status === "viewed") && (
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
              ))}
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
