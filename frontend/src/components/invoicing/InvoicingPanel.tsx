"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileText, Plus, Send, CheckCircle, Eye, Edit, XCircle, Printer,
  Trash2, X, Save, Loader2, ChevronLeft, ChevronRight, Search,
  DollarSign, AlertTriangle, Clock,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";
import EmptyState from "@/components/ui/EmptyState";

/* ── Types ─────────────────────────────────────────────────────────── */

type InvoiceStatus = "draft" | "sent" | "viewed" | "paid" | "overdue" | "cancelled";

interface LineItem {
  id?: number;
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
}

interface Invoice {
  id: number;
  invoice_number: string;
  client_name: string;
  client_email: string;
  client_company: string;
  status: InvoiceStatus;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  notes: string;
  due_date: string;
  created_at: string;
  updated_at: string;
  line_items: LineItem[];
}

interface InvoiceTemplate {
  id: number;
  name: string;
  line_items: Omit<LineItem, "id" | "amount">[];
}

interface InvoiceListResponse {
  invoices: Invoice[];
  total: number;
  page: number;
  limit: number;
}

interface StatsData {
  total_outstanding: number;
  total_paid_this_month: number;
  overdue_count: number;
}

/* ── Constants ─────────────────────────────────────────────────────── */

const STATUS_CONFIG: Record<InvoiceStatus, { label: string; bg: string; text: string }> = {
  draft:     { label: "Draft",     bg: "bg-gray-500/20",    text: "text-gray-400" },
  sent:      { label: "Sent",      bg: "bg-blue-500/20",    text: "text-blue-400" },
  viewed:    { label: "Viewed",    bg: "bg-amber-500/20",   text: "text-amber-400" },
  paid:      { label: "Paid",      bg: "bg-green-500/20",   text: "text-green-400" },
  overdue:   { label: "Overdue",   bg: "bg-red-500/20",     text: "text-red-400" },
  cancelled: { label: "Cancelled", bg: "bg-slate-500/20",   text: "text-slate-400" },
};

const ALL_STATUSES: InvoiceStatus[] = ["draft", "sent", "viewed", "paid", "overdue", "cancelled"];
const ITEMS_PER_PAGE = 25;

const emptyLineItem = (): LineItem => ({ description: "", quantity: 1, unit_price: 0, amount: 0 });

const formatCurrency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

const formatDate = (d: string) =>
  d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";

/* ── Component ─────────────────────────────────────────────────────── */

type View = "list" | "detail" | "form";

export default function InvoicingPanel() {
  /* State */
  const [view, setView] = useState<View>("list");
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "">("");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [stats, setStats] = useState<StatsData>({ total_outstanding: 0, total_paid_this_month: 0, overdue_count: 0 });
  const [templates, setTemplates] = useState<InvoiceTemplate[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);

  /* Form state */
  const [formClientName, setFormClientName] = useState("");
  const [formClientEmail, setFormClientEmail] = useState("");
  const [formClientCompany, setFormClientCompany] = useState("");
  const [formLineItems, setFormLineItems] = useState<LineItem[]>([emptyLineItem()]);
  const [formTaxRate, setFormTaxRate] = useState(0);
  const [formNotes, setFormNotes] = useState("");
  const [formDueDate, setFormDueDate] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);

  /* Derived */
  const subtotal = formLineItems.reduce((s, li) => s + li.quantity * li.unit_price, 0);
  const taxAmount = subtotal * (formTaxRate / 100);
  const formTotal = subtotal + taxAmount;
  const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE));

  /* ── Data fetching ─────────────────────────────────────────────── */

  const loadInvoices = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), limit: String(ITEMS_PER_PAGE) });
      if (statusFilter) params.set("status", statusFilter);
      if (searchQuery.trim()) params.set("search", searchQuery.trim());
      const res = await authFetch(`${API}/api/invoices?${params}`);
      if (res.ok) {
        const data: InvoiceListResponse = await res.json();
        setInvoices(data.invoices);
        setTotal(data.total);
      }
    } catch (e) {
      console.error("Failed to load invoices:", e);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, searchQuery]);

  const loadStats = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/invoices?limit=1000`);
      if (!res.ok) return;
      const data: InvoiceListResponse = await res.json();
      const all = data.invoices;
      const outstanding = all
        .filter((i) => ["sent", "viewed", "overdue"].includes(i.status))
        .reduce((s, i) => s + i.total, 0);
      const now = new Date();
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
      const paidThisMonth = all
        .filter((i) => i.status === "paid" && new Date(i.updated_at) >= monthStart)
        .reduce((s, i) => s + i.total, 0);
      const overdueCount = all.filter((i) => i.status === "overdue").length;
      setStats({ total_outstanding: outstanding, total_paid_this_month: paidThisMonth, overdue_count: overdueCount });
    } catch {
      /* silent */
    }
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/invoices/templates`);
      if (res.ok) setTemplates(await res.json());
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => { loadInvoices(); }, [loadInvoices]);
  useEffect(() => { loadStats(); loadTemplates(); }, [loadStats, loadTemplates]);

  /* ── Actions ───────────────────────────────────────────────────── */

  const sendInvoice = async (id: number) => {
    await authFetch(`${API}/api/invoices/${id}/send`, { method: "POST" });
    loadInvoices();
    loadStats();
    if (selectedInvoice?.id === id) loadDetail(id);
  };

  const markPaid = async (id: number) => {
    await authFetch(`${API}/api/invoices/${id}/mark-paid`, { method: "POST" });
    loadInvoices();
    loadStats();
    if (selectedInvoice?.id === id) loadDetail(id);
  };

  const cancelInvoice = async (id: number) => {
    await authFetch(`${API}/api/invoices/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "cancelled" }),
    });
    loadInvoices();
    loadStats();
  };

  const loadDetail = async (id: number) => {
    try {
      const res = await authFetch(`${API}/api/invoices/${id}`);
      if (res.ok) {
        setSelectedInvoice(await res.json());
        setView("detail");
      }
    } catch (e) {
      console.error("Failed to load invoice detail:", e);
    }
  };

  const openPdf = (id: number) => {
    const token = localStorage.getItem("warroom_token");
    window.open(`${API}/api/invoices/${id}/pdf?token=${token}`, "_blank");
  };

  /* ── Form helpers ──────────────────────────────────────────────── */

  const resetForm = () => {
    setFormClientName("");
    setFormClientEmail("");
    setFormClientCompany("");
    setFormLineItems([emptyLineItem()]);
    setFormTaxRate(0);
    setFormNotes("");
    setFormDueDate("");
    setEditingId(null);
  };

  const openCreateForm = () => {
    resetForm();
    setView("form");
  };

  const openEditForm = (inv: Invoice) => {
    setEditingId(inv.id);
    setFormClientName(inv.client_name);
    setFormClientEmail(inv.client_email);
    setFormClientCompany(inv.client_company);
    setFormLineItems(
      inv.line_items.length > 0
        ? inv.line_items.map((li) => ({ ...li, amount: li.quantity * li.unit_price }))
        : [emptyLineItem()],
    );
    setFormTaxRate(inv.tax_rate);
    setFormNotes(inv.notes || "");
    setFormDueDate(inv.due_date ? inv.due_date.slice(0, 10) : "");
    setView("form");
  };

  const applyTemplate = (templateId: number) => {
    const tpl = templates.find((t) => t.id === templateId);
    if (!tpl) return;
    setFormLineItems(
      tpl.line_items.map((li) => ({ ...li, amount: li.quantity * li.unit_price })),
    );
  };

  const updateLineItem = (idx: number, field: keyof LineItem, value: string | number) => {
    setFormLineItems((prev) => {
      const updated = [...prev];
      const item = { ...updated[idx], [field]: value };
      item.amount = item.quantity * item.unit_price;
      updated[idx] = item;
      return updated;
    });
  };

  const addLineItem = () => setFormLineItems((p) => [...p, emptyLineItem()]);

  const removeLineItem = (idx: number) => {
    setFormLineItems((p) => (p.length <= 1 ? p : p.filter((_, i) => i !== idx)));
  };

  const saveInvoice = async (andSend: boolean) => {
    setSaving(true);
    const body = {
      client_name: formClientName,
      client_email: formClientEmail,
      client_company: formClientCompany,
      line_items: formLineItems.map(({ description, quantity, unit_price }) => ({
        description,
        quantity,
        unit_price,
      })),
      tax_rate: formTaxRate,
      notes: formNotes,
      due_date: formDueDate || null,
      status: andSend ? "sent" : "draft",
    };

    try {
      const url = editingId ? `${API}/api/invoices/${editingId}` : `${API}/api/invoices`;
      const method = editingId ? "PATCH" : "POST";
      const res = await authFetch(url, { method, body: JSON.stringify(body) });
      if (res.ok) {
        const saved: Invoice = await res.json();
        if (andSend && !editingId) {
          await authFetch(`${API}/api/invoices/${saved.id}/send`, { method: "POST" });
        }
        resetForm();
        setView("list");
        loadInvoices();
        loadStats();
      }
    } catch (e) {
      console.error("Failed to save invoice:", e);
    } finally {
      setSaving(false);
    }
  };

  /* ── Render: Stats bar ─────────────────────────────────────────── */

  const StatsBar = () => (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-amber-500/15 flex items-center justify-center">
          <Clock size={20} className="text-amber-400" />
        </div>
        <div>
          <p className="text-xs text-warroom-muted">Outstanding</p>
          <p className="text-lg font-semibold text-warroom-text">{formatCurrency(stats.total_outstanding)}</p>
        </div>
      </div>
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-green-500/15 flex items-center justify-center">
          <DollarSign size={20} className="text-green-400" />
        </div>
        <div>
          <p className="text-xs text-warroom-muted">Paid This Month</p>
          <p className="text-lg font-semibold text-warroom-text">{formatCurrency(stats.total_paid_this_month)}</p>
        </div>
      </div>
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-red-500/15 flex items-center justify-center">
          <AlertTriangle size={20} className="text-red-400" />
        </div>
        <div className="flex items-center gap-2">
          <div>
            <p className="text-xs text-warroom-muted">Overdue</p>
            <p className="text-lg font-semibold text-warroom-text">{stats.overdue_count}</p>
          </div>
          {stats.overdue_count > 0 && (
            <span className="ml-1 px-2 py-0.5 text-xs font-bold rounded-full bg-red-500/20 text-red-400">
              {stats.overdue_count}
            </span>
          )}
        </div>
      </div>
    </div>
  );

  /* ── Render: Status badge ──────────────────────────────────────── */

  const StatusBadge = ({ status }: { status: InvoiceStatus }) => {
    const cfg = STATUS_CONFIG[status];
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>
        {cfg.label}
      </span>
    );
  };

  /* ── Render: List view ─────────────────────────────────────────── */

  if (view === "list") {
    return (
      <div className="h-full overflow-y-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <FileText size={24} className="text-warroom-accent" />
            <h1 className="text-xl font-bold text-warroom-text">Invoices</h1>
          </div>
          <button
            onClick={openCreateForm}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-warroom-accent text-white text-sm font-medium hover:bg-warroom-accent/80 transition-colors"
          >
            <Plus size={16} /> New Invoice
          </button>
        </div>

        <StatsBar />

        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1 max-w-xs">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
            <input
              type="text"
              placeholder="Search by client…"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-text text-sm placeholder:text-warroom-muted focus:outline-none focus:border-warroom-accent/50"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value as InvoiceStatus | ""); setPage(1); }}
            className="px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50"
          >
            <option value="">All Statuses</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
            ))}
          </select>
        </div>

        {/* Table */}
        {loading ? (
          <LoadingState message="Loading invoices..." />
        ) : invoices.length === 0 ? (
          <EmptyState
            icon={<FileText size={40} />}
            title="No invoices yet"
            description="Create your first invoice to start billing clients."
            action={{ label: "New Invoice", onClick: openCreateForm }}
          />
        ) : (
          <>
            <div className="bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-warroom-border text-warroom-muted text-left">
                    <th className="px-4 py-3 font-medium">Invoice #</th>
                    <th className="px-4 py-3 font-medium">Client</th>
                    <th className="px-4 py-3 font-medium text-right">Amount</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Due Date</th>
                    <th className="px-4 py-3 font-medium">Created</th>
                    <th className="px-4 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr
                      key={inv.id}
                      onClick={() => loadDetail(inv.id)}
                      className="border-b border-warroom-border/50 hover:bg-warroom-border/20 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-warroom-accent">{inv.invoice_number}</td>
                      <td className="px-4 py-3">
                        <div className="text-warroom-text">{inv.client_name}</div>
                        {inv.client_company && (
                          <div className="text-xs text-warroom-muted">{inv.client_company}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-medium">{formatCurrency(inv.total)}</td>
                      <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                      <td className="px-4 py-3 text-warroom-muted">{formatDate(inv.due_date)}</td>
                      <td className="px-4 py-3 text-warroom-muted">{formatDate(inv.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                          {inv.status === "draft" && (
                            <button
                              onClick={() => sendInvoice(inv.id)}
                              className="p-1.5 rounded-md hover:bg-blue-500/15 text-blue-400 transition-colors"
                              title="Send"
                            >
                              <Send size={14} />
                            </button>
                          )}
                          {["sent", "viewed", "overdue"].includes(inv.status) && (
                            <button
                              onClick={() => markPaid(inv.id)}
                              className="p-1.5 rounded-md hover:bg-green-500/15 text-green-400 transition-colors"
                              title="Mark Paid"
                            >
                              <CheckCircle size={14} />
                            </button>
                          )}
                          <button
                            onClick={() => loadDetail(inv.id)}
                            className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted transition-colors"
                            title="View"
                          >
                            <Eye size={14} />
                          </button>
                          {["draft", "sent"].includes(inv.status) && (
                            <button
                              onClick={() => openEditForm(inv)}
                              className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted transition-colors"
                              title="Edit"
                            >
                              <Edit size={14} />
                            </button>
                          )}
                          {inv.status !== "cancelled" && inv.status !== "paid" && (
                            <button
                              onClick={() => cancelInvoice(inv.id)}
                              className="p-1.5 rounded-md hover:bg-red-500/15 text-red-400 transition-colors"
                              title="Cancel"
                            >
                              <XCircle size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-warroom-muted">
                  Showing {(page - 1) * ITEMS_PER_PAGE + 1}–{Math.min(page * ITEMS_PER_PAGE, total)} of {total}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted disabled:opacity-30 transition-colors"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="text-sm text-warroom-muted px-2">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="p-1.5 rounded-md hover:bg-warroom-border/40 text-warroom-muted disabled:opacity-30 transition-colors"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  /* ── Render: Detail view ───────────────────────────────────────── */

  if (view === "detail" && selectedInvoice) {
    const inv = selectedInvoice;
    return (
      <div className="h-full overflow-y-auto p-6">
        {/* Back + actions */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => { setView("list"); setSelectedInvoice(null); }}
            className="flex items-center gap-2 text-warroom-muted hover:text-warroom-text transition-colors"
          >
            <ChevronLeft size={18} /> Back to Invoices
          </button>
          <div className="flex items-center gap-2">
            {inv.status === "draft" && (
              <button
                onClick={() => sendInvoice(inv.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-400 text-sm font-medium hover:bg-blue-500/25 transition-colors"
              >
                <Send size={14} /> Send
              </button>
            )}
            {["sent", "viewed", "overdue"].includes(inv.status) && (
              <button
                onClick={() => markPaid(inv.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/15 text-green-400 text-sm font-medium hover:bg-green-500/25 transition-colors"
              >
                <CheckCircle size={14} /> Mark Paid
              </button>
            )}
            {["draft", "sent"].includes(inv.status) && (
              <button
                onClick={() => openEditForm(inv)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-border/40 text-warroom-text text-sm font-medium hover:bg-warroom-border/60 transition-colors"
              >
                <Edit size={14} /> Edit
              </button>
            )}
            <button
              onClick={() => openPdf(inv.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-border/40 text-warroom-text text-sm font-medium hover:bg-warroom-border/60 transition-colors"
            >
              <Printer size={14} /> Print
            </button>
          </div>
        </div>

        {/* Invoice card */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-8 max-w-3xl">
          <div className="flex items-start justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-warroom-text">Invoice {inv.invoice_number}</h2>
              <p className="text-sm text-warroom-muted mt-1">Created {formatDate(inv.created_at)}</p>
            </div>
            <StatusBadge status={inv.status} />
          </div>

          {/* Client info */}
          <div className="mb-8 p-4 rounded-lg bg-warroom-bg/50 border border-warroom-border/50">
            <p className="text-xs text-warroom-muted mb-1">Bill To</p>
            <p className="font-medium text-warroom-text">{inv.client_name}</p>
            {inv.client_company && <p className="text-sm text-warroom-muted">{inv.client_company}</p>}
            {inv.client_email && <p className="text-sm text-warroom-muted">{inv.client_email}</p>}
          </div>

          {/* Line items table */}
          <table className="w-full text-sm mb-6">
            <thead>
              <tr className="border-b border-warroom-border text-warroom-muted">
                <th className="text-left py-2 font-medium">Description</th>
                <th className="text-right py-2 font-medium w-20">Qty</th>
                <th className="text-right py-2 font-medium w-28">Unit Price</th>
                <th className="text-right py-2 font-medium w-28">Amount</th>
              </tr>
            </thead>
            <tbody>
              {(inv.line_items || []).map((li, i) => (
                <tr key={i} className="border-b border-warroom-border/30">
                  <td className="py-2.5 text-warroom-text">{li.description}</td>
                  <td className="py-2.5 text-right text-warroom-muted">{li.quantity}</td>
                  <td className="py-2.5 text-right text-warroom-muted">{formatCurrency(li.unit_price)}</td>
                  <td className="py-2.5 text-right text-warroom-text font-medium">{formatCurrency(li.quantity * li.unit_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Totals */}
          <div className="flex justify-end">
            <div className="w-64 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-warroom-muted">Subtotal</span>
                <span className="text-warroom-text">{formatCurrency(inv.subtotal)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-warroom-muted">Tax ({inv.tax_rate}%)</span>
                <span className="text-warroom-text">{formatCurrency(inv.tax_amount)}</span>
              </div>
              <div className="flex justify-between text-base font-bold pt-2 border-t border-warroom-border">
                <span className="text-warroom-text">Total</span>
                <span className="text-warroom-accent">{formatCurrency(inv.total)}</span>
              </div>
            </div>
          </div>

          {/* Due date + notes */}
          <div className="mt-8 grid grid-cols-2 gap-6">
            <div>
              <p className="text-xs text-warroom-muted mb-1">Due Date</p>
              <p className="text-sm text-warroom-text">{formatDate(inv.due_date)}</p>
            </div>
            {inv.notes && (
              <div>
                <p className="text-xs text-warroom-muted mb-1">Notes</p>
                <p className="text-sm text-warroom-text whitespace-pre-wrap">{inv.notes}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ── Render: Create/Edit form ──────────────────────────────────── */

  if (view === "form") {
    return (
      <div className="h-full overflow-y-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => { setView("list"); resetForm(); }}
            className="flex items-center gap-2 text-warroom-muted hover:text-warroom-text transition-colors"
          >
            <ChevronLeft size={18} /> Back
          </button>
          <h1 className="text-xl font-bold text-warroom-text">
            {editingId ? "Edit Invoice" : "New Invoice"}
          </h1>
          <div className="w-20" /> {/* spacer */}
        </div>

        <div className="max-w-3xl space-y-6">
          {/* Template selector */}
          {templates.length > 0 && !editingId && (
            <div>
              <label className="block text-xs text-warroom-muted mb-1">Load Template</label>
              <select
                onChange={(e) => { if (e.target.value) applyTemplate(Number(e.target.value)); }}
                defaultValue=""
                className="px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-text text-sm w-full focus:outline-none focus:border-warroom-accent/50"
              >
                <option value="">Select a template…</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Client info */}
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-warroom-text mb-4">Client Information</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-warroom-muted mb-1">Name *</label>
                <input
                  type="text"
                  value={formClientName}
                  onChange={(e) => setFormClientName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50"
                  placeholder="Client name"
                />
              </div>
              <div>
                <label className="block text-xs text-warroom-muted mb-1">Email</label>
                <input
                  type="email"
                  value={formClientEmail}
                  onChange={(e) => setFormClientEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50"
                  placeholder="email@example.com"
                />
              </div>
              <div>
                <label className="block text-xs text-warroom-muted mb-1">Company</label>
                <input
                  type="text"
                  value={formClientCompany}
                  onChange={(e) => setFormClientCompany(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50"
                  placeholder="Company name"
                />
              </div>
            </div>
          </div>

          {/* Line items */}
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-warroom-text">Line Items</h3>
              <button
                onClick={addLineItem}
                className="flex items-center gap-1 text-xs text-warroom-accent hover:text-warroom-accent/80 transition-colors"
              >
                <Plus size={14} /> Add Item
              </button>
            </div>

            <div className="space-y-2">
              {/* Header */}
              <div className="grid grid-cols-[1fr_80px_110px_110px_36px] gap-2 text-xs text-warroom-muted px-1">
                <span>Description</span>
                <span className="text-right">Qty</span>
                <span className="text-right">Unit Price</span>
                <span className="text-right">Amount</span>
                <span />
              </div>

              {formLineItems.map((li, idx) => (
                <div key={idx} className="grid grid-cols-[1fr_80px_110px_110px_36px] gap-2 items-center">
                  <input
                    type="text"
                    value={li.description}
                    onChange={(e) => updateLineItem(idx, "description", e.target.value)}
                    className="px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50"
                    placeholder="Description"
                  />
                  <input
                    type="number"
                    min={0}
                    value={li.quantity}
                    onChange={(e) => updateLineItem(idx, "quantity", Number(e.target.value))}
                    className="px-2 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-warroom-text text-sm text-right focus:outline-none focus:border-warroom-accent/50"
                  />
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={li.unit_price}
                    onChange={(e) => updateLineItem(idx, "unit_price", Number(e.target.value))}
                    className="px-2 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-warroom-text text-sm text-right focus:outline-none focus:border-warroom-accent/50"
                  />
                  <div className="px-2 py-2 text-sm text-right text-warroom-muted">
                    {formatCurrency(li.quantity * li.unit_price)}
                  </div>
                  <button
                    onClick={() => removeLineItem(idx)}
                    disabled={formLineItems.length <= 1}
                    className="p-1.5 rounded-md hover:bg-red-500/15 text-red-400 disabled:opacity-20 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>

            {/* Totals */}
            <div className="flex justify-end mt-4 pt-4 border-t border-warroom-border/50">
              <div className="w-64 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-warroom-muted">Subtotal</span>
                  <span className="text-warroom-text">{formatCurrency(subtotal)}</span>
                </div>
                <div className="flex items-center justify-between text-sm gap-3">
                  <span className="text-warroom-muted">Tax</span>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      value={formTaxRate}
                      onChange={(e) => setFormTaxRate(Number(e.target.value))}
                      className="w-16 px-2 py-1 rounded-md bg-warroom-bg border border-warroom-border text-warroom-text text-sm text-right focus:outline-none focus:border-warroom-accent/50"
                    />
                    <span className="text-warroom-muted text-xs">%</span>
                    <span className="text-warroom-text ml-2">{formatCurrency(taxAmount)}</span>
                  </div>
                </div>
                <div className="flex justify-between text-base font-bold pt-2 border-t border-warroom-border">
                  <span className="text-warroom-text">Total</span>
                  <span className="text-warroom-accent">{formatCurrency(formTotal)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Due date + notes */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-warroom-muted mb-1">Due Date</label>
              <input
                type="date"
                value={formDueDate}
                onChange={(e) => setFormDueDate(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50"
              />
            </div>
            <div>
              <label className="block text-xs text-warroom-muted mb-1">Notes</label>
              <textarea
                value={formNotes}
                onChange={(e) => setFormNotes(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-text text-sm resize-none focus:outline-none focus:border-warroom-accent/50"
                placeholder="Payment terms, thank you note, etc."
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pb-8">
            <button
              onClick={() => { setView("list"); resetForm(); }}
              className="px-4 py-2 rounded-lg border border-warroom-border text-warroom-muted text-sm font-medium hover:bg-warroom-border/30 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => saveInvoice(false)}
              disabled={saving || !formClientName.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-warroom-border/40 text-warroom-text text-sm font-medium hover:bg-warroom-border/60 disabled:opacity-40 transition-colors"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save as Draft
            </button>
            <button
              onClick={() => saveInvoice(true)}
              disabled={saving || !formClientName.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-warroom-accent text-white text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-40 transition-colors"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              Save & Send
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
