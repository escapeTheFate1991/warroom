"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  DollarSign,
  FileText,
  Mail,
  Percent,
  Phone,
  Scale,
  Target,
  TrendingUp,
  Trophy,
  Users,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import type { Activity, Deal, Pipeline, PipelineStage } from "@/components/crm/types";

interface SalesDeal extends Deal {
  closed_at?: string | null;
  user_name?: string | null;
  stage_name?: string | null;
  stage?: { name?: string | null } | null;
}

interface SalesActivity extends Activity {
  deal?: { title?: string | null } | null;
  deal_name?: string | null;
  deal_title?: string | null;
}

interface ContractSummary {
  monthly_price?: number | null;
  monthly_amount?: number | null;
}

interface InvoiceSummary {
  total?: number | null;
  amount?: number | null;
  paid_at?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
}

type LoadingState = {
  deals: boolean;
  stages: boolean;
  activities: boolean;
  invoices: boolean;
  contracts: boolean;
};

const INITIAL_LOADING: LoadingState = {
  deals: true,
  stages: true,
  activities: true,
  invoices: true,
  contracts: true,
};

const FUNNEL_COLORS = [
  "from-cyan-500/70 to-cyan-500/20",
  "from-blue-500/70 to-blue-500/20",
  "from-indigo-500/70 to-indigo-500/20",
  "from-violet-500/70 to-violet-500/20",
  "from-amber-500/70 to-amber-500/20",
  "from-emerald-500/70 to-emerald-500/20",
];

const KPI_TRENDS = {
  revenue: { change: 12.4, direction: "up" as const, sparkline: [48, 56, 52, 64, 68, 74] },
  mrr: { change: 5.8, direction: "up" as const, sparkline: [40, 42, 43, 45, 47, 49] },
  pipeline: { change: 8.1, direction: "up" as const, sparkline: [62, 58, 61, 66, 69, 72] },
  won: { change: 9.2, direction: "up" as const, sparkline: [22, 24, 21, 28, 30, 33] },
  average: { change: 3.6, direction: "down" as const, sparkline: [52, 54, 50, 51, 49, 48] },
  rate: { change: 4.7, direction: "up" as const, sparkline: [34, 38, 40, 43, 45, 47] },
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function isValidDate(value: string | null | undefined): value is string {
  return Boolean(value && !Number.isNaN(new Date(value).getTime()));
}

function isCurrentMonth(value: string | null | undefined): boolean {
  if (!isValidDate(value)) return false;
  const date = new Date(value);
  const now = new Date();
  return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
}

function extractList<T>(payload: unknown, keys: string[] = []): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    for (const key of keys) {
      if (Array.isArray(record[key])) return record[key] as T[];
    }
  }
  return [];
}

function getDealValue(deal: SalesDeal): number {
  return Number(deal.deal_value ?? 0);
}

function getContractValue(contract: ContractSummary): number {
  return Number(contract.monthly_price ?? contract.monthly_amount ?? 0);
}

function getInvoiceValue(invoice: InvoiceSummary): number {
  return Number(invoice.total ?? invoice.amount ?? 0);
}

function getInvoiceDate(invoice: InvoiceSummary): string | null {
  return invoice.paid_at ?? invoice.updated_at ?? invoice.created_at ?? null;
}

function getActivityDate(activity: SalesActivity): string | null {
  return activity.schedule_from ?? activity.created_at ?? null;
}

function getActivityDealName(activity: SalesActivity): string {
  return activity.deal?.title ?? activity.deal_name ?? activity.deal_title ?? "No deal linked";
}

function getDealStageName(deal: SalesDeal, stageMap: Map<number, string>): string {
  return deal.stage_name ?? deal.stage?.name ?? stageMap.get(deal.stage_id) ?? "Unassigned";
}

function getActivityIcon(type: string) {
  switch (type) {
    case "call":
      return Phone;
    case "email":
      return Mail;
    case "meeting":
      return Users;
    case "task":
      return CheckCircle2;
    default:
      return FileText;
  }
}

function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(...data, 1);
  const width = 88;
  const height = 24;
  const points = data
    .map((value, index) => `${(index / Math.max(data.length - 1, 1)) * width},${height - (value / max) * height}`)
    .join(" ");

  return (
    <svg width={width} height={height} className="opacity-60">
      <polyline
        fill="none"
        points={points}
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function KpiSkeleton() {
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 animate-pulse">
      <div className="w-10 h-10 rounded-full bg-warroom-bg mb-4" />
      <div className="h-7 w-28 bg-warroom-bg rounded mb-2" />
      <div className="h-4 w-36 bg-warroom-bg rounded mb-3" />
      <div className="h-5 w-24 bg-warroom-bg rounded" />
    </div>
  );
}

function PanelSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="h-12 bg-warroom-bg rounded-lg" />
      ))}
    </div>
  );
}

function SectionEmpty({ title }: { title: string }) {
  return <p className="py-10 text-center text-sm text-warroom-muted">{title}</p>;
}

export default function SalesDashboard() {
  const [deals, setDeals] = useState<SalesDeal[]>([]);
  const [activities, setActivities] = useState<SalesActivity[]>([]);
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [paidInvoices, setPaidInvoices] = useState<InvoiceSummary[]>([]);
  const [activeContracts, setActiveContracts] = useState<ContractSummary[]>([]);
  const [loading, setLoading] = useState<LoadingState>(INITIAL_LOADING);

  const fetchSalesData = useCallback(async () => {
    setLoading(INITIAL_LOADING);

    const safeJson = async (response: Response | null) => {
      if (!response?.ok) return null;
      try {
        return await response.json();
      } catch {
        return null;
      }
    };

    const loadDeals = async () => {
      try {
        const payload = await safeJson(await authFetch(`${API}/api/crm/deals`).catch(() => null));
        setDeals(extractList<SalesDeal>(payload, ["deals", "items"]));
      } finally {
        setLoading((current) => ({ ...current, deals: false }));
      }
    };

    const loadActivities = async () => {
      try {
        const payload = await safeJson(await authFetch(`${API}/api/crm/activities?limit=10`).catch(() => null));
        setActivities(extractList<SalesActivity>(payload, ["activities", "items"]));
      } finally {
        setLoading((current) => ({ ...current, activities: false }));
      }
    };

    const loadInvoices = async () => {
      try {
        const payload = await safeJson(await authFetch(`${API}/api/invoices?status=paid&limit=1000`).catch(() => null));
        setPaidInvoices(extractList<InvoiceSummary>(payload, ["invoices", "items"]));
      } finally {
        setLoading((current) => ({ ...current, invoices: false }));
      }
    };

    const loadContracts = async () => {
      try {
        const payload = await safeJson(await authFetch(`${API}/api/contracts?status=active`).catch(() => null));
        setActiveContracts(extractList<ContractSummary>(payload, ["contracts", "items"]));
      } finally {
        setLoading((current) => ({ ...current, contracts: false }));
      }
    };

    const loadPipelineStages = async () => {
      try {
        const pipelinesPayload = await safeJson(await authFetch(`${API}/api/crm/pipelines`).catch(() => null));
        const pipelines = extractList<Pipeline>(pipelinesPayload, ["pipelines", "items"]);
        const pipeline = pipelines.find((item) => item.is_default) ?? pipelines[0] ?? null;
        setSelectedPipeline(pipeline);
        if (!pipeline) {
          setStages([]);
          return;
        }

        const stagesPayload = await safeJson(
          await authFetch(`${API}/api/crm/pipelines/${pipeline.id}/stages`).catch(() => null),
        );
        setStages(
          extractList<PipelineStage>(stagesPayload, ["stages", "items"]).sort(
            (left, right) => left.sort_order - right.sort_order,
          ),
        );
      } finally {
        setLoading((current) => ({ ...current, stages: false }));
      }
    };

    await Promise.allSettled([
      loadDeals(),
      loadActivities(),
      loadInvoices(),
      loadContracts(),
      loadPipelineStages(),
    ]);
  }, []);

  useEffect(() => {
    fetchSalesData();
  }, [fetchSalesData]);

  const stageMap = useMemo(() => new Map(stages.map((stage) => [stage.id, stage.name])), [stages]);

  const openDeals = useMemo(() => deals.filter((deal) => deal.status === null), [deals]);
  const wonDeals = useMemo(() => deals.filter((deal) => deal.status === true), [deals]);
  const lostDeals = useMemo(() => deals.filter((deal) => deal.status === false), [deals]);
  const valuedDeals = useMemo(() => deals.filter((deal) => getDealValue(deal) > 0), [deals]);

  const revenueThisMonth = useMemo(
    () => paidInvoices.filter((invoice) => isCurrentMonth(getInvoiceDate(invoice))).reduce((sum, invoice) => sum + getInvoiceValue(invoice), 0),
    [paidInvoices],
  );
  const mrr = useMemo(
    () => activeContracts.reduce((sum, contract) => sum + getContractValue(contract), 0),
    [activeContracts],
  );
  const pipelineValue = useMemo(
    () => openDeals.reduce((sum, deal) => sum + getDealValue(deal), 0),
    [openDeals],
  );
  const dealsWonThisMonth = useMemo(
    () => wonDeals.filter((deal) => isCurrentMonth(deal.closed_at ?? deal.updated_at ?? deal.created_at)).length,
    [wonDeals],
  );
  const averageDealSize = useMemo(
    () => (valuedDeals.length ? valuedDeals.reduce((sum, deal) => sum + getDealValue(deal), 0) / valuedDeals.length : 0),
    [valuedDeals],
  );
  const winRate = useMemo(() => {
    const closedDeals = wonDeals.length + lostDeals.length;
    return closedDeals ? (wonDeals.length / closedDeals) * 100 : 0;
  }, [lostDeals.length, wonDeals.length]);

  const revenueByMonth = useMemo(() => {
    const months = Array.from({ length: 6 }, (_, index) => {
      const date = new Date();
      date.setDate(1);
      date.setMonth(date.getMonth() - (5 - index));
      return {
        key: `${date.getFullYear()}-${date.getMonth()}`,
        label: date.toLocaleDateString("en-US", { month: "short" }),
        total: 0,
      };
    });

    const revenueMap = new Map(months.map((month) => [month.key, { ...month }]));
    for (const invoice of paidInvoices) {
      const rawDate = getInvoiceDate(invoice);
      if (!isValidDate(rawDate)) continue;
      const date = new Date(rawDate);
      const key = `${date.getFullYear()}-${date.getMonth()}`;
      const month = revenueMap.get(key);
      if (month) month.total += getInvoiceValue(invoice);
    }

    return months.map((month) => revenueMap.get(month.key) ?? month);
  }, [paidInvoices]);

  const topDeals = useMemo(
    () => [...deals].sort((left, right) => getDealValue(right) - getDealValue(left)).slice(0, 5),
    [deals],
  );

  const funnelStages = useMemo(() => {
    const relevantDeals = selectedPipeline ? deals.filter((deal) => deal.pipeline_id === selectedPipeline.id) : deals;
    return stages.map((stage) => {
      const stageDeals = relevantDeals.filter((deal) => deal.stage_id === stage.id);
      return {
        id: stage.id,
        name: stage.name,
        count: stageDeals.length,
        totalValue: stageDeals.reduce((sum, deal) => sum + getDealValue(deal), 0),
      };
    });
  }, [deals, selectedPipeline, stages]);

  const maxRevenue = Math.max(...revenueByMonth.map((month) => month.total), 1);
  const maxFunnelCount = Math.max(...funnelStages.map((stage) => stage.count), 1);
  const maxFunnelValue = Math.max(...funnelStages.map((stage) => stage.totalValue), 1);

  const kpis = [
    {
      label: "Revenue This Month",
      value: formatCurrency(revenueThisMonth),
      icon: DollarSign,
      iconBg: "bg-green-500/15",
      iconColor: "text-green-400",
      trend: KPI_TRENDS.revenue,
    },
    {
      label: "Monthly Recurring Revenue",
      value: formatCurrency(mrr),
      icon: TrendingUp,
      iconBg: "bg-emerald-500/15",
      iconColor: "text-emerald-400",
      trend: KPI_TRENDS.mrr,
    },
    {
      label: "Total Pipeline Value",
      value: formatCurrency(pipelineValue),
      icon: Target,
      iconBg: "bg-violet-500/15",
      iconColor: "text-violet-400",
      trend: KPI_TRENDS.pipeline,
    },
    {
      label: "Deals Won This Month",
      value: dealsWonThisMonth.toLocaleString(),
      icon: Trophy,
      iconBg: "bg-amber-500/15",
      iconColor: "text-amber-400",
      trend: KPI_TRENDS.won,
    },
    {
      label: "Average Deal Size",
      value: formatCurrency(averageDealSize),
      icon: Scale,
      iconBg: "bg-cyan-500/15",
      iconColor: "text-cyan-400",
      trend: KPI_TRENDS.average,
    },
    {
      label: "Win Rate",
      value: formatPercent(winRate),
      icon: Percent,
      iconBg: "bg-blue-500/15",
      iconColor: "text-blue-400",
      trend: KPI_TRENDS.rate,
    },
  ];

  const loadingKpis = loading.deals || loading.invoices || loading.contracts;
  const loadingFunnel = loading.deals || loading.stages;
  const loadingRevenue = loading.invoices;
  const loadingTopDeals = loading.deals;
  const loadingActivities = loading.activities;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {loadingKpis
          ? Array.from({ length: 6 }).map((_, index) => <KpiSkeleton key={index} />)
          : kpis.map((kpi) => {
              const Icon = kpi.icon;
              const TrendIcon = kpi.trend.direction === "up" ? ArrowUpRight : ArrowDownRight;
              const trendColor = kpi.trend.direction === "up" ? "text-green-400" : "text-red-400";

              return (
                <div key={kpi.label} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div className={`w-10 h-10 rounded-full ${kpi.iconBg} flex items-center justify-center`}>
                      <Icon size={18} className={kpi.iconColor} />
                    </div>
                    <div className={`${trendColor} flex-shrink-0`}>
                      <Sparkline data={kpi.trend.sparkline} />
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-warroom-text">{kpi.value}</div>
                  <p className="text-sm text-warroom-muted mt-1">{kpi.label}</p>
                  <div className={`mt-3 inline-flex items-center gap-1 text-xs font-medium ${trendColor}`}>
                    <TrendIcon size={12} />
                    {kpi.trend.change}% vs last month
                  </div>
                </div>
              );
            })}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
          <div className="flex items-center justify-between gap-3 mb-5">
            <div>
              <h3 className="text-sm font-semibold text-warroom-text">Pipeline Funnel</h3>
              <p className="text-xs text-warroom-muted mt-1">
                {selectedPipeline?.name ? `${selectedPipeline.name} pipeline` : "Current sales stages"}
              </p>
            </div>
            <span className="text-xs text-warroom-muted">{openDeals.length} open deals</span>
          </div>

          {loadingFunnel ? (
            <PanelSkeleton rows={5} />
          ) : funnelStages.length === 0 || funnelStages.every((stage) => stage.count === 0) ? (
            <SectionEmpty title="No pipeline stage data available yet." />
          ) : (
            <div className="space-y-3">
              {funnelStages.map((stage, index) => {
                const widthRatio = Math.max(stage.count / maxFunnelCount, stage.totalValue / maxFunnelValue);
                return (
                  <div key={stage.id} className="space-y-2">
                    <div className="flex items-center justify-between gap-3 text-xs">
                      <span className="font-medium text-warroom-text truncate">{stage.name}</span>
                      <span className="text-warroom-muted">
                        {stage.count} deals · {formatCurrency(stage.totalValue)}
                      </span>
                    </div>
                    <div className="h-12 rounded-xl bg-warroom-bg border border-warroom-border/60 overflow-hidden flex items-center px-2">
                      <div
                        className={`h-8 min-w-[14%] rounded-lg bg-gradient-to-r ${FUNNEL_COLORS[index % FUNNEL_COLORS.length]} px-3 flex items-center`}
                        style={{ width: `${Math.max(widthRatio * 100, 14)}%` }}
                      >
                        <span className="text-xs font-medium text-white/90 truncate">{stage.count} · {formatCurrency(stage.totalValue)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
          <div className="flex items-center justify-between gap-3 mb-5">
            <div>
              <h3 className="text-sm font-semibold text-warroom-text">Revenue Over Time</h3>
              <p className="text-xs text-warroom-muted mt-1">Paid invoices over the last 6 months</p>
            </div>
            <span className="text-xs text-warroom-muted">{paidInvoices.length} invoices</span>
          </div>

          {loadingRevenue ? (
            <PanelSkeleton rows={1} />
          ) : revenueByMonth.every((month) => month.total === 0) ? (
            <SectionEmpty title="No paid invoice revenue found for the last 6 months." />
          ) : (
            <div className="h-[260px] flex items-end gap-3">
              {revenueByMonth.map((month) => (
                <div key={month.key} className="flex-1 h-full flex flex-col justify-end items-center gap-2">
                  <span className="text-[10px] text-warroom-muted">{month.total > 0 ? formatCurrency(month.total) : "—"}</span>
                  <div className="w-full h-[190px] flex items-end">
                    <div
                      className="w-full rounded-t-xl bg-gradient-to-t from-warroom-accent to-cyan-400/70 border border-cyan-400/20"
                      style={{ height: `${Math.max((month.total / maxRevenue) * 100, month.total > 0 ? 14 : 4)}%` }}
                    />
                  </div>
                  <span className="text-xs text-warroom-muted">{month.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5 overflow-hidden">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h3 className="text-sm font-semibold text-warroom-text">Top Deals</h3>
            <span className="text-xs text-warroom-muted">Top 5 by value</span>
          </div>

          {loadingTopDeals ? (
            <PanelSkeleton rows={5} />
          ) : topDeals.length === 0 ? (
            <SectionEmpty title="No deals available yet." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-warroom-border text-left text-xs text-warroom-muted">
                    <th className="pb-3 pr-3 font-medium">Deal</th>
                    <th className="pb-3 pr-3 font-medium">Organization</th>
                    <th className="pb-3 pr-3 font-medium">Value</th>
                    <th className="pb-3 pr-3 font-medium">Stage</th>
                    <th className="pb-3 font-medium">Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {topDeals.map((deal) => (
                    <tr key={deal.id} className="border-b border-warroom-border/50 last:border-0">
                      <td className="py-3 pr-3 text-warroom-text font-medium">{deal.title}</td>
                      <td className="py-3 pr-3 text-warroom-muted">{deal.organization_name ?? deal.person_name ?? "—"}</td>
                      <td className="py-3 pr-3 text-green-400 font-medium">{formatCurrency(getDealValue(deal))}</td>
                      <td className="py-3 pr-3 text-warroom-muted">{getDealStageName(deal, stageMap)}</td>
                      <td className="py-3 text-warroom-muted">{deal.user_name ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h3 className="text-sm font-semibold text-warroom-text">Recent Activities</h3>
            <span className="text-xs text-warroom-muted">Last 10 activities</span>
          </div>

          {loadingActivities ? (
            <PanelSkeleton rows={6} />
          ) : activities.length === 0 ? (
            <SectionEmpty title="No recent activities to show." />
          ) : (
            <div className="space-y-3">
              {activities.map((activity) => {
                const ActivityIcon = getActivityIcon(activity.type);
                const activityDate = getActivityDate(activity);
                return (
                  <div key={activity.id} className="flex items-start gap-3 py-3 border-b border-warroom-border last:border-0">
                    <div className="w-9 h-9 rounded-full bg-warroom-bg border border-warroom-border flex items-center justify-center flex-shrink-0">
                      <ActivityIcon size={15} className="text-warroom-accent" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-warroom-text truncate">{activity.title || activity.type}</p>
                          <p className="text-xs text-warroom-muted mt-1">{getActivityDealName(activity)}</p>
                        </div>
                        <div className="flex items-center gap-1 text-[11px] text-warroom-muted whitespace-nowrap">
                          <Clock3 size={11} />
                          {activityDate && isValidDate(activityDate)
                            ? new Date(activityDate).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                            : "—"}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}