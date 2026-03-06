"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  DollarSign, TrendingUp, TrendingDown, Clock, Mail, Users,
  FileSignature, AlertTriangle, Briefcase, Inbox, CalendarDays,
  Loader2, ArrowUpRight, ArrowDownRight, Minus,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────────── */

interface Invoice {
  id: number;
  invoice_number: string;
  client_name: string;
  client_company: string;
  status: string;
  total: number;
  due_date: string;
  created_at: string;
}

interface Contract {
  id: number;
  contract_number: string;
  client_name: string;
  client_company: string;
  plan_name: string;
  monthly_price: number;
  term_months: number;
  deal_stage: string;
  status: string;
  created_at: string;
  signed_at: string | null;
}

interface ContactSubmission {
  id: number;
  name: string;
  email: string;
  status: string;
  created_at: string;
}

interface ColdEmailDraft {
  id: number;
  status: string;
  created_at: string;
}

interface MetricData {
  value: number | string;
  trend: number | null;
  loading: boolean;
  error: boolean;
}

/* ── Helpers ───────────────────────────────────────────────────────── */

const formatCurrency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);

const formatDate = (d: string) =>
  d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";

const startOfWeek = (): Date => {
  const now = new Date();
  const day = now.getDay();
  const diff = now.getDate() - day + (day === 0 ? -6 : 1);
  const start = new Date(now);
  start.setDate(diff);
  start.setHours(0, 0, 0, 0);
  return start;
};

const daysBetween = (a: string, b: string): number => {
  const msPerDay = 86400000;
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / msPerDay);
};

const PIPELINE_STAGES = ["draft", "exported", "sent", "read", "signing"];

const REFRESH_INTERVAL_MS = 300000; // 5 minutes

/* ── Tile Config ───────────────────────────────────────────────────── */

interface TileConfig {
  key: string;
  label: string;
  icon: typeof DollarSign;
  color: string;
  bgColor: string;
  format: (v: number | string) => string;
  tab: string;
}

const TILES: TileConfig[] = [
  // Row 1
  { key: "totalRevenue", label: "Total Revenue", icon: DollarSign, color: "text-emerald-400", bgColor: "bg-emerald-500/15", format: (v) => formatCurrency(Number(v)), tab: "invoices" },
  { key: "mrr", label: "Monthly Recurring Revenue", icon: TrendingUp, color: "text-blue-400", bgColor: "bg-blue-500/15", format: (v) => formatCurrency(Number(v)), tab: "contracts" },
  { key: "avgTimeToClose", label: "Avg Time to Close", icon: Clock, color: "text-amber-400", bgColor: "bg-amber-500/15", format: (v) => `${v} days`, tab: "crm-deals" },
  { key: "pipelineValue", label: "Pipeline Value", icon: Briefcase, color: "text-purple-400", bgColor: "bg-purple-500/15", format: (v) => formatCurrency(Number(v)), tab: "crm-deals" },
  // Row 2
  { key: "coldEmailsSent", label: "Cold Emails Sent", icon: Mail, color: "text-sky-400", bgColor: "bg-sky-500/15", format: (v) => String(v), tab: "email" },
  { key: "newLeads", label: "New Leads (This Week)", icon: Users, color: "text-teal-400", bgColor: "bg-teal-500/15", format: (v) => String(v), tab: "crm-submissions" },
  { key: "activeContracts", label: "Active Contracts", icon: FileSignature, color: "text-indigo-400", bgColor: "bg-indigo-500/15", format: (v) => String(v), tab: "contracts" },
  { key: "overdueInvoices", label: "Overdue Invoices", icon: AlertTriangle, color: "text-red-400", bgColor: "bg-red-500/15", format: (v) => String(v), tab: "invoices" },
];

/* ── Skeleton ──────────────────────────────────────────────────────── */

function TileSkeleton() {
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5 animate-pulse">
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-full bg-warroom-border/40" />
        <div className="w-16 h-4 rounded bg-warroom-border/40" />
      </div>
      <div className="w-24 h-8 rounded bg-warroom-border/40 mb-2" />
      <div className="w-32 h-4 rounded bg-warroom-border/30" />
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5 animate-pulse">
      <div className="w-32 h-5 rounded bg-warroom-border/40 mb-4" />
      {[...Array(3)].map((_, i) => (
        <div key={i} className="flex items-center gap-3 py-3 border-t border-warroom-border/30">
          <div className="w-full h-4 rounded bg-warroom-border/30" />
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────────── */

export default function ReportsOverview() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<Record<string, MetricData>>({});
  const [recentDeals, setRecentDeals] = useState<Contract[]>([]);
  const [recentSubmissions, setRecentSubmissions] = useState<ContactSubmission[]>([]);
  const [upcomingInvoices, setUpcomingInvoices] = useState<Invoice[]>([]);

  const navigateTo = useCallback((tab: string) => {
    router.push(`/?tab=${tab}`, { scroll: false });
  }, [router]);

  const fetchData = useCallback(async () => {
    const weekStart = startOfWeek();
    const newMetrics: Record<string, MetricData> = {};

    const safe = async <T,>(fn: () => Promise<T>, fallback: T): Promise<T> => {
      try { return await fn(); } catch { return fallback; }
    };

    const [
      paidInvoicesRes,
      activeContractsRes,
      allContractsRes,
      overdueInvoicesRes,
      coldEmailsRes,
      submissionsRes,
      upcomingInvoicesRes,
    ] = await Promise.all([
      safe(() => authFetch(`${API}/api/invoices?status=paid&limit=1000`).then(r => r.json()), null),
      safe(() => authFetch(`${API}/api/contracts?status=active&limit=1000`).then(r => r.json()), null),
      safe(() => authFetch(`${API}/api/contracts?limit=1000`).then(r => r.json()), null),
      safe(() => authFetch(`${API}/api/invoices?status=overdue&limit=1000`).then(r => r.json()), null),
      safe(() => authFetch(`${API}/api/cold-emails/drafts?status=sent&limit=1000`).then(r => r.json()), null),
      safe(() => authFetch(`${API}/api/contact-submissions?limit=1000`).then(r => r.json()), null),
      safe(() => authFetch(`${API}/api/invoices?status=sent&limit=1000`).then(r => r.json()), null),
    ]);

    // Total Revenue
    const paidInvoices: Invoice[] = paidInvoicesRes?.invoices ?? [];
    const totalRevenue = paidInvoices.reduce((sum, inv) => sum + (inv.total || 0), 0);
    newMetrics.totalRevenue = { value: totalRevenue, trend: null, loading: false, error: !paidInvoicesRes };

    // MRR
    const activeContracts: Contract[] = activeContractsRes?.contracts ?? [];
    const mrr = activeContracts.reduce((sum, c) => sum + (c.monthly_price || 0), 0);
    newMetrics.mrr = { value: mrr, trend: null, loading: false, error: !activeContractsRes };

    // Avg Time to Close
    const allContracts: Contract[] = allContractsRes?.contracts ?? [];
    const closedContracts = allContracts.filter(c => c.signed_at && c.created_at);
    const avgDays = closedContracts.length > 0
      ? Math.round(closedContracts.reduce((sum, c) => sum + daysBetween(c.created_at, c.signed_at!), 0) / closedContracts.length)
      : 0;
    newMetrics.avgTimeToClose = { value: avgDays || "—", trend: null, loading: false, error: !allContractsRes };

    // Pipeline Value
    const pipelineContracts = allContracts.filter(c => PIPELINE_STAGES.includes(c.deal_stage));
    const pipelineValue = pipelineContracts.reduce((sum, c) => sum + ((c.monthly_price || 0) * (c.term_months || 1)), 0);
    newMetrics.pipelineValue = { value: pipelineValue, trend: null, loading: false, error: !allContractsRes };

    // Cold Emails Sent (This Week)
    const coldEmails: ColdEmailDraft[] = coldEmailsRes?.drafts ?? coldEmailsRes?.cold_emails ?? [];
    const thisWeekEmails = coldEmails.filter(e => new Date(e.created_at) >= weekStart);
    newMetrics.coldEmailsSent = { value: thisWeekEmails.length, trend: null, loading: false, error: !coldEmailsRes };

    // New Leads (This Week)
    const submissions: ContactSubmission[] = submissionsRes?.submissions ?? submissionsRes?.contact_submissions ?? [];
    const thisWeekLeads = submissions.filter(s => new Date(s.created_at) >= weekStart);
    newMetrics.newLeads = { value: thisWeekLeads.length, trend: null, loading: false, error: !submissionsRes };

    // Active Contracts count
    newMetrics.activeContracts = { value: activeContracts.length, trend: null, loading: false, error: !activeContractsRes };

    // Overdue Invoices count
    const overdueInvoices: Invoice[] = overdueInvoicesRes?.invoices ?? [];
    newMetrics.overdueInvoices = { value: overdueInvoices.length, trend: null, loading: false, error: !overdueInvoicesRes };

    setMetrics(newMetrics);

    // Recent Deals — last 5 sorted by created_at desc
    const sortedDeals = [...allContracts].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);
    setRecentDeals(sortedDeals);

    // Recent Submissions — last 5
    const sortedSubs = [...submissions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);
    setRecentSubmissions(sortedSubs);

    // Upcoming Invoice Due Dates — next 5 future unpaid invoices
    const allSentInvoices: Invoice[] = upcomingInvoicesRes?.invoices ?? [];
    const allUnpaid = [...allSentInvoices, ...overdueInvoices];
    const upcoming = allUnpaid
      .filter(inv => inv.due_date)
      .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
      .slice(0, 5);
    setUpcomingInvoices(upcoming);

    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchData]);

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-warroom-text">Business Overview</h1>
          <p className="text-sm text-warroom-muted mt-0.5">Key performance metrics at a glance</p>
        </div>
        {!loading && (
          <button
            onClick={fetchData}
            className="text-xs text-warroom-muted hover:text-warroom-text bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 transition-colors"
          >
            Refresh
          </button>
        )}
      </div>

      {/* Metric Tiles — 2 rows of 4 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {TILES.map((tile) => {
          const data = metrics[tile.key];
          const isLoading = loading || !data;

          if (isLoading) return <TileSkeleton key={tile.key} />;

          const Icon = tile.icon;
          const displayValue = data.error ? "—" : tile.format(data.value);
          const hasTrend = data.trend !== null && data.trend !== undefined;
          const isPositive = hasTrend && data.trend! > 0;
          const isNegative = hasTrend && data.trend! < 0;

          return (
            <button
              key={tile.key}
              onClick={() => navigateTo(tile.tab)}
              className="bg-warroom-surface border border-warroom-border rounded-xl p-5 text-left hover:border-warroom-accent/40 hover:bg-warroom-surface/80 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className={`w-10 h-10 rounded-full ${tile.bgColor} flex items-center justify-center`}>
                  <Icon size={20} className={tile.color} />
                </div>
                {hasTrend ? (
                  <span className={`flex items-center gap-0.5 text-xs font-medium ${isPositive ? "text-emerald-400" : isNegative ? "text-red-400" : "text-warroom-muted"}`}>
                    {isPositive ? <ArrowUpRight size={14} /> : isNegative ? <ArrowDownRight size={14} /> : <Minus size={14} />}
                    {Math.abs(data.trend!).toFixed(1)}%
                  </span>
                ) : (
                  <span className="text-xs text-warroom-muted">—</span>
                )}
              </div>
              <p className="text-2xl font-bold text-warroom-text mb-1 group-hover:text-warroom-accent transition-colors">
                {displayValue}
              </p>
              <p className="text-sm text-warroom-muted">{tile.label}</p>
            </button>
          );
        })}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent Deals */}
        {loading ? <CardSkeleton /> : (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-warroom-text flex items-center gap-2">
                <Briefcase size={16} className="text-purple-400" />
                Recent Deals
              </h3>
              <button onClick={() => navigateTo("crm-deals")} className="text-xs text-warroom-accent hover:underline">View all</button>
            </div>
            {recentDeals.length === 0 ? (
              <p className="text-sm text-warroom-muted py-4 text-center">No deals yet</p>
            ) : (
              <div className="space-y-0">
                {recentDeals.map((deal) => (
                  <div key={deal.id} className="flex items-center justify-between py-2.5 border-t border-warroom-border/30 first:border-t-0">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-warroom-text truncate">{deal.client_name || deal.client_company || "Unknown"}</p>
                      <p className="text-xs text-warroom-muted truncate">{deal.plan_name || "—"}</p>
                    </div>
                    <div className="text-right ml-3 flex-shrink-0">
                      <StageBadge stage={deal.deal_stage} />
                      <p className="text-[11px] text-warroom-muted mt-0.5">{formatDate(deal.created_at)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Recent Submissions */}
        {loading ? <CardSkeleton /> : (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-warroom-text flex items-center gap-2">
                <Inbox size={16} className="text-teal-400" />
                Recent Submissions
              </h3>
              <button onClick={() => navigateTo("crm-submissions")} className="text-xs text-warroom-accent hover:underline">View all</button>
            </div>
            {recentSubmissions.length === 0 ? (
              <p className="text-sm text-warroom-muted py-4 text-center">No submissions yet</p>
            ) : (
              <div className="space-y-0">
                {recentSubmissions.map((sub) => (
                  <div key={sub.id} className="flex items-center justify-between py-2.5 border-t border-warroom-border/30 first:border-t-0">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-warroom-text truncate">{sub.name || "Unknown"}</p>
                      <p className="text-xs text-warroom-muted truncate">{sub.email}</p>
                    </div>
                    <div className="text-right ml-3 flex-shrink-0">
                      <StatusBadge status={sub.status} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Upcoming Invoice Due Dates */}
        {loading ? <CardSkeleton /> : (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-warroom-text flex items-center gap-2">
                <CalendarDays size={16} className="text-amber-400" />
                Upcoming Invoices
              </h3>
              <button onClick={() => navigateTo("invoices")} className="text-xs text-warroom-accent hover:underline">View all</button>
            </div>
            {upcomingInvoices.length === 0 ? (
              <p className="text-sm text-warroom-muted py-4 text-center">No upcoming invoices</p>
            ) : (
              <div className="space-y-0">
                {upcomingInvoices.map((inv) => (
                  <div key={inv.id} className="flex items-center justify-between py-2.5 border-t border-warroom-border/30 first:border-t-0">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-warroom-text truncate">{inv.client_name || inv.client_company || "Unknown"}</p>
                      <p className="text-xs text-warroom-muted">{inv.invoice_number}</p>
                    </div>
                    <div className="text-right ml-3 flex-shrink-0">
                      <p className="text-sm font-semibold text-warroom-text">{formatCurrency(inv.total)}</p>
                      <p className={`text-[11px] ${isOverdue(inv.due_date) ? "text-red-400" : "text-warroom-muted"}`}>
                        {formatDate(inv.due_date)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Sub-components ────────────────────────────────────────────────── */

const STAGE_COLORS: Record<string, { bg: string; text: string }> = {
  draft:    { bg: "bg-gray-500/20",   text: "text-gray-400" },
  exported: { bg: "bg-slate-500/20",  text: "text-slate-400" },
  sent:     { bg: "bg-blue-500/20",   text: "text-blue-400" },
  delivered:{ bg: "bg-cyan-500/20",   text: "text-cyan-400" },
  read:     { bg: "bg-amber-500/20",  text: "text-amber-400" },
  signing:  { bg: "bg-purple-500/20", text: "text-purple-400" },
  signed:   { bg: "bg-emerald-500/20",text: "text-emerald-400" },
  active:   { bg: "bg-green-500/20",  text: "text-green-400" },
  expired:  { bg: "bg-orange-500/20", text: "text-orange-400" },
  cancelled:{ bg: "bg-red-500/20",    text: "text-red-400" },
};

function StageBadge({ stage }: { stage: string }) {
  const colors = STAGE_COLORS[stage] ?? { bg: "bg-gray-500/20", text: "text-gray-400" };
  return (
    <span className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded-full ${colors.bg} ${colors.text} capitalize`}>
      {stage}
    </span>
  );
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  new:       { bg: "bg-blue-500/20",   text: "text-blue-400" },
  contacted: { bg: "bg-amber-500/20",  text: "text-amber-400" },
  qualified: { bg: "bg-green-500/20",  text: "text-green-400" },
  closed:    { bg: "bg-gray-500/20",   text: "text-gray-400" },
  spam:      { bg: "bg-red-500/20",    text: "text-red-400" },
};

function StatusBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] ?? { bg: "bg-gray-500/20", text: "text-gray-400" };
  return (
    <span className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded-full ${colors.bg} ${colors.text} capitalize`}>
      {status}
    </span>
  );
}

function isOverdue(dueDate: string): boolean {
  return new Date(dueDate) < new Date();
}
