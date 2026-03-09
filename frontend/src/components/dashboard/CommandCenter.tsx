"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Zap, Users, Eye, BarChart3, TrendingUp, Activity, Share2, Film,
  Target, Clock, CheckCircle2, Loader2, AlertCircle, ArrowRight, ArrowUpRight,
  Flame, Calendar, DollarSign, FileText, Mail, UserPlus,
  AlertTriangle,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import ActiveAssignmentsList from "@/components/agents/ActiveAssignmentsList";
import AskAIButton from "@/components/agents/AskAIButton";
import type { GroundedAIContext } from "@/components/agents/SharedAIChatPanel";
import SalesDashboard from "@/components/dashboard/SalesDashboard";

type DashboardFocus = "sales" | "social" | "ai";

const TEAM_API = "/api/team";

interface SocialAccount {
  id: number; platform: string; username: string | null;
  follower_count: number; post_count: number; status: string;
}
interface SocialSummary {
  total_followers: number; total_engagement: number; total_impressions: number;
  total_reach: number; engagement_rate: number; accounts_connected: number;
}
interface SocialTrends {
  followers: string; engagement: string; impressions: string;
}
interface AgentEvent {
  event_type: string; from_agent: string; to_agent: string;
  summary: string; timestamp: string;
}

// Fallback agents — replaced by DB agents when available
const FALLBACK_AGENTS = [
  { id: "friday", emoji: "🖤", name: "Friday", role: "Orchestrator", model: "Opus" },
  { id: "copy", emoji: "✍️", name: "Copy", role: "Copywriter", model: "Sonnet" },
  { id: "design", emoji: "🎨", name: "Design", role: "UI/UX", model: "Sonnet" },
  { id: "dev", emoji: "⚡", name: "Dev", role: "Developer", model: "Sonnet" },
  { id: "docs", emoji: "📖", name: "Docs", role: "Documentation", model: "Haiku" },
  { id: "support", emoji: "🎧", name: "Support", role: "Support", model: "Haiku" },
  { id: "inbox", emoji: "📬", name: "Inbox", role: "Email", model: "Haiku" },
];

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "#E4405F", facebook: "#1877F2", youtube: "#FF0000",
  tiktok: "#00F2EA", x: "#000", threads: "#888",
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function getStoredPipelineCards(): any[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem("warroom_content_pipeline") || "[]";
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function normalizeTeamEvents(payload: any): AgentEvent[] {
  const rawEvents = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.events)
      ? payload.events
      : [];

  return rawEvents.map((event: any) => ({
    event_type: event?.event_type || "unknown",
    from_agent: event?.from_agent || "unknown",
    to_agent: event?.to_agent || "unknown",
    summary: event?.summary || "",
    timestamp: event?.timestamp || event?.created_at || new Date().toISOString(),
  }));
}

function MiniSparkline({ color, data }: { color: string; data?: number[] }) {
  const sparkData = data?.length ? data : Array.from({ length: 12 }, () => Math.random() * 80 + 20);
  const max = Math.max(...sparkData, 1);
  const w = 100, h = 30;
  const points = sparkData.map((v, i) => `${(i / (sparkData.length - 1)) * w},${h - (v / max) * h}`).join(" ");
  return (
    <svg width={w} height={h} className="opacity-40">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function getPipelineStats() {
  const cards = getStoredPipelineCards();
  return {
    total: cards.length,
    ideas: cards.filter((c: any) => c.stage === "idea").length,
    inProduction: cards.filter((c: any) => ["script", "filming", "editing"].includes(c.stage)).length,
    posted: cards.filter((c: any) => c.stage === "posted").length,
    scheduled: cards.filter((c: any) => c.stage === "scheduled").length,
  };
}

interface BusinessMetrics {
  revenueThisMonth: number | null;
  activeContracts: number | null;
  mrr: number | null;
  coldEmailsSent: number | null;
  newLeads: number | null;
  avgCloseTime: number | null;
  pipelineValue: number | null;
  overdueInvoices: number | null;
}

const INITIAL_METRICS: BusinessMetrics = {
  revenueThisMonth: null,
  activeContracts: null,
  mrr: null,
  coldEmailsSent: null,
  newLeads: null,
  avgCloseTime: null,
  pipelineValue: null,
  overdueInvoices: null,
};

function isCurrentMonth(dateStr: string): boolean {
  const d = new Date(dateStr);
  const now = new Date();
  return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
}

function isCurrentWeek(dateStr: string): boolean {
  const d = new Date(dateStr);
  const now = new Date();
  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - now.getDay());
  startOfWeek.setHours(0, 0, 0, 0);
  return d >= startOfWeek;
}

interface CRMDeal {
  id: number; title: string; value: number; stage: string; created_at: string;
  contact_name?: string;
}
interface CRMActivity {
  id: number; title: string; type: string; due_date: string; is_done: boolean;
  contact_name?: string;
}
interface PipelineStage {
  stage: string; count: number; total_value: number;
}

export default function CommandCenter() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [summary, setSummary] = useState<SocialSummary | null>(null);
  const [trends, setTrends] = useState<SocialTrends | null>(null);
  const [sparklineData, setSparklineData] = useState<Record<string, number[]>>({});
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [pipelineStats, setPipelineStats] = useState(getPipelineStats());
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [metrics, setMetrics] = useState<BusinessMetrics>(INITIAL_METRICS);
  const [focus, setFocus] = useState<DashboardFocus>("sales");
  const [recentDeals, setRecentDeals] = useState<CRMDeal[]>([]);
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([]);
  const [upcomingActivities, setUpcomingActivities] = useState<CRMActivity[]>([]);
  const [dbAgents, setDbAgents] = useState<{ id: string; emoji: string; name: string; role: string; model: string; status: string }[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [accResp, sumResp, trendsResp, sparkResp] = await Promise.all([
        authFetch(`${API}/api/social/accounts`).catch(() => null),
        authFetch(`${API}/api/social/analytics`).catch(() => null),
        authFetch(`${API}/api/social/analytics/trends`).catch(() => null),
        authFetch(`${API}/api/social/analytics/sparkline?days=12`).catch(() => null),
      ]);
      if (accResp?.ok) setAccounts(await accResp.json());
      if (sumResp?.ok) setSummary(await sumResp.json());
      if (trendsResp?.ok) setTrends(await trendsResp.json());
      if (sparkResp?.ok) setSparklineData(await sparkResp.json());

      // Agents from DB
      try {
        const agentResp = await authFetch(`${API}/api/agents`).catch(() => null);
        if (agentResp?.ok) {
          const agentData = await agentResp.json();
          if (Array.isArray(agentData) && agentData.length > 0) {
            setDbAgents(agentData.map((a: any) => ({
              id: a.id,
              emoji: a.emoji || "🤖",
              name: a.name,
              role: a.role,
              model: (a.model || "").split("/").pop()?.replace("claude-", "") || "Sonnet",
              status: a.status || "idle",
            })));
          }
        }
      } catch {}

      // Team events
      try {
        const evResp = await authFetch(`${API}${TEAM_API}/events?limit=8`).catch(() => null);
        if (evResp?.ok) {
          const data = await evResp.json();
          setEvents(normalizeTeamEvents(data));
        }
      } catch {}
    } catch {} finally { setLoading(false); }
  }, []);

  const fetchMetrics = useCallback(async () => {
    const safeJson = async (resp: Response | null) => {
      if (!resp?.ok) return null;
      try { return await resp.json(); } catch { return null; }
    };

    const [invoicesResp, contractsResp, allContractsResp, coldEmailsResp, leadsResp, overdueResp] = await Promise.all([
      authFetch(`${API}/api/invoices`).catch(() => null),
      authFetch(`${API}/api/contracts?status=active`).catch(() => null),
      authFetch(`${API}/api/contracts`).catch(() => null),
      authFetch(`${API}/api/cold-emails/drafts?status=sent`).catch(() => null),
      authFetch(`${API}/api/contact-submissions`).catch(() => null),
      authFetch(`${API}/api/invoices?status=overdue`).catch(() => null),
    ]);

    const invoices: any[] = (await safeJson(invoicesResp)) || [];
    const activeContracts: any[] = (await safeJson(contractsResp)) || [];
    const allContracts: any[] = (await safeJson(allContractsResp)) || [];
    const coldEmails: any[] = (await safeJson(coldEmailsResp)) || [];
    const leads: any[] = (await safeJson(leadsResp)) || [];
    const overdueInvoices: any[] = (await safeJson(overdueResp)) || [];

    // Revenue this month: sum of paid invoices in current month
    const paidThisMonth = invoices
      .filter((inv: any) => inv.status === "paid" && inv.paid_at && isCurrentMonth(inv.paid_at))
      .reduce((sum: number, inv: any) => sum + (Number(inv.total) || Number(inv.amount) || 0), 0);

    // MRR from active contracts
    const mrr = activeContracts.reduce(
      (sum: number, c: any) => sum + (Number(c.monthly_price) || Number(c.monthly_amount) || 0), 0
    );

    // Cold emails sent this week
    const emailsThisWeek = coldEmails.filter(
      (e: any) => e.sent_at && isCurrentWeek(e.sent_at)
    ).length || coldEmails.length;

    // New leads this week
    const leadsThisWeek = leads.filter(
      (l: any) => l.created_at && isCurrentWeek(l.created_at)
    ).length || leads.length;

    // Average close time: days from created to signed for signed contracts
    const signedContracts = allContracts.filter((c: any) => c.status === "signed" && c.created_at && c.signed_at);
    const avgClose = signedContracts.length > 0
      ? signedContracts.reduce((sum: number, c: any) => {
          const days = (new Date(c.signed_at).getTime() - new Date(c.created_at).getTime()) / 86400000;
          return sum + days;
        }, 0) / signedContracts.length
      : null;

    // Pipeline value: total of unsigned contracts
    const unsignedValue = allContracts
      .filter((c: any) => c.status !== "signed" && c.status !== "cancelled")
      .reduce((sum: number, c: any) => sum + (Number(c.total) || Number(c.value) || Number(c.monthly_price) || 0), 0);

    setMetrics({
      revenueThisMonth: paidThisMonth,
      activeContracts: activeContracts.length,
      mrr,
      coldEmailsSent: emailsThisWeek,
      newLeads: leadsThisWeek,
      avgCloseTime: avgClose !== null ? Math.round(avgClose) : null,
      pipelineValue: unsignedValue,
      overdueInvoices: overdueInvoices.length,
    });
  }, []);

  const fetchCRMData = useCallback(async () => {
    try {
      const [dealsResp, activitiesResp, pipelinesResp] = await Promise.all([
        authFetch(`${API}/api/crm/deals?limit=5`).catch(() => null),
        authFetch(`${API}/api/crm/activities?is_done=false&limit=5`).catch(() => null),
        authFetch(`${API}/api/crm/pipelines`).catch(() => null),
      ]);
      if (dealsResp?.ok) setRecentDeals(await dealsResp.json());
      if (activitiesResp?.ok) setUpcomingActivities(await activitiesResp.json());
      if (pipelinesResp?.ok) {
        const pipelines = await pipelinesResp.json();
        if (Array.isArray(pipelines) && pipelines.length > 0) {
          const forecastResp = await authFetch(`${API}/api/crm/deals/forecast?pipeline_id=${pipelines[0].id}`).catch(() => null);
          if (forecastResp?.ok) {
            const forecast = await forecastResp.json();
            if (Array.isArray(forecast)) setPipelineStages(forecast);
          }
        }
      }
    } catch {}
  }, []);

  useEffect(() => { fetchData(); fetchMetrics(); fetchCRMData(); }, [fetchData, fetchMetrics, fetchCRMData]);
  useEffect(() => { setPipelineStats(getPipelineStats()); }, []);

  // Loading timeout: prevent infinite spinner — show zero-value KPIs after 10s
  useEffect(() => {
    const timeout = setTimeout(() => setLoading(false), 10000);
    return () => clearTimeout(timeout);
  }, []);
  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 60000);
    const metricsInterval = setInterval(fetchMetrics, 300000);
    return () => { clearInterval(t); clearInterval(metricsInterval); };
  }, [fetchMetrics]);

  // Demo events if none from API
  const displayEvents = events.length > 0 ? events : [
    { event_type: "complete", from_agent: "dev", to_agent: "friday", summary: "War Room UI rebuild deployed — 5 new components", timestamp: new Date(Date.now() - 300000).toISOString() },
    { event_type: "spawn", from_agent: "friday", to_agent: "dev", summary: "Building Command Center dashboard", timestamp: new Date(Date.now() - 120000).toISOString() },
    { event_type: "complete", from_agent: "copy", to_agent: "friday", summary: "6 hook formula templates created", timestamp: new Date(Date.now() - 60000).toISOString() },
  ];

  const greeting = currentTime.getHours() < 12 ? "Good morning" : currentTime.getHours() < 18 ? "Good afternoon" : "Good evening";
  const chatContext: GroundedAIContext = focus === "sales"
    ? {
        surface: "sales",
        entityType: "dashboard_view",
        entityId: "command-center:sales",
        entityName: "Command Center sales view",
        title: "Command Center sales view",
        summary: `${metrics.activeContracts || 0} active contracts and ${formatNum(metrics.pipelineValue || 0)} in open pipeline value.`,
        facts: [
          { label: "Revenue this month", value: metrics.revenueThisMonth || 0 },
          { label: "MRR", value: metrics.mrr || 0 },
          { label: "New leads", value: metrics.newLeads || 0 },
        ],
      }
    : focus === "social"
      ? {
          surface: "social",
          entityType: "dashboard_view",
          entityId: "command-center:social",
          entityName: "Command Center social view",
          title: "Command Center social view",
          summary: `${accounts.length} connected account(s) with ${formatNum(summary?.total_engagement || 0)} engagements tracked.`,
          facts: [
            { label: "Followers", value: summary?.total_followers || 0 },
            { label: "Reach", value: summary?.total_reach || 0 },
            { label: "Pipeline content", value: pipelineStats.total },
          ],
        }
      : {
          surface: "agents",
          entityType: "dashboard_view",
          entityId: "command-center:agents",
          entityName: "Command Center AI Agents",
          title: "Command Center AI Agents",
          summary: `${(dbAgents.length || FALLBACK_AGENTS.length)} agents configured, ${displayEvents.length} recent events.`,
          facts: [
            { label: "Active agents", value: dbAgents.length || FALLBACK_AGENTS.length },
            { label: "Recent events", value: displayEvents.length },
          ],
        };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header with greeting + focus tabs */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between flex-shrink-0">
        <div>
          <h2 className="text-lg font-bold">Command Center</h2>
          <p className="text-xs text-warroom-muted">{currentTime.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })} · {currentTime.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}</p>
        </div>
        <div className="flex gap-1 bg-warroom-bg rounded-lg p-1">
          {(["sales", "social", "ai"] as const).map(f => (
            <button
              key={f}
              onClick={() => setFocus(f)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                focus === f ? "bg-warroom-accent text-white" : "text-warroom-muted hover:text-warroom-text"
              }`}
            >
              {f === "sales" ? "💰 Sales" : f === "social" ? "📱 Social" : "🤖 Agents"}
            </button>
          ))}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto p-6">
        {focus === "sales" && (
          <SalesFocus metrics={metrics} recentDeals={recentDeals} pipelineStages={pipelineStages} upcomingActivities={upcomingActivities} />
        )}
        {focus === "social" && (
          <SocialFocus accounts={accounts} summary={summary} trends={trends} sparklineData={sparklineData} pipelineStats={pipelineStats} />
        )}
        {focus === "ai" && (
          <AIFocus agents={dbAgents.length > 0 ? dbAgents : FALLBACK_AGENTS} events={displayEvents} />
        )}
      </div>

      <AskAIButton
        context={chatContext}
        buttonLabel={`Ask AI about ${focus === "ai" ? "Agents" : focus === "sales" ? "Sales" : "Social"}`}
        emptyHint="Ask for a diagnosis, next action, or summary of this dashboard view..."
        className="fixed bottom-6 right-6 z-40"
        buttonClassName="h-12 rounded-full px-5 shadow-lg"
      />
    </div>
  );
}

// ── Sales Focus View ──────────────────────────────────────
function SalesFocus({ metrics, recentDeals, pipelineStages, upcomingActivities }: {
  metrics: BusinessMetrics;
  recentDeals: CRMDeal[];
  pipelineStages: PipelineStage[];
  upcomingActivities: CRMActivity[];
}) {
  void metrics;
  void recentDeals;
  void pipelineStages;
  void upcomingActivities;
  return <SalesDashboard />;
}

// ── Social Focus View ──────────────────────────────────────
function SocialFocus({ accounts, summary, trends, sparklineData, pipelineStats }: {
  accounts: SocialAccount[];
  summary: SocialSummary | null;
  trends: SocialTrends | null;
  sparklineData: Record<string, number[]>;
  pipelineStats: ReturnType<typeof getPipelineStats>;
}) {
  const socialKpis = [
    { label: "Total Followers", value: summary?.total_followers || accounts.reduce((s, a) => s + a.follower_count, 0), icon: Users, color: "text-blue-400", bg: "bg-blue-400/10", trend: trends?.followers },
    { label: "Engagement Rate", value: summary?.engagement_rate || 0, icon: TrendingUp, color: "text-green-400", bg: "bg-green-400/10", isRate: true, trend: trends?.engagement },
    { label: "Total Reach", value: summary?.total_reach || 0, icon: Eye, color: "text-purple-400", bg: "bg-purple-400/10", trend: trends?.impressions },
    { label: "Content Pipeline", value: pipelineStats.total, icon: Film, color: "text-orange-400", bg: "bg-orange-400/10" },
  ];

  // Top performing content from localStorage
  const topPerforming: { title: string; platform: string; stage: string }[] = [];
  if (typeof window !== "undefined") {
    try {
      const cards = getStoredPipelineCards();
      cards.filter((c: any) => c.stage === "posted").slice(0, 5).forEach((c: any) => {
        topPerforming.push({ title: c.title, platform: c.platforms?.[0] || "all", stage: c.stage });
      });
    } catch {}
  }

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        {socialKpis.map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4 relative overflow-hidden">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-8 h-8 rounded-lg ${kpi.bg} flex items-center justify-center`}>
                  <Icon size={16} className={kpi.color} />
                </div>
                {kpi.trend && (
                  <span className="flex items-center gap-0.5 text-xs text-green-400 font-medium">
                    <ArrowUpRight size={12} /> {kpi.trend}
                  </span>
                )}
              </div>
              <p className={`text-xl font-bold ${kpi.color}`}>
                {kpi.isRate ? `${(typeof kpi.value === "number" ? kpi.value : 0).toFixed(1)}%` : formatNum(typeof kpi.value === "number" ? kpi.value : 0)}
              </p>
              <p className="text-xs text-warroom-muted mt-1">{kpi.label}</p>
            </div>
          );
        })}
      </div>

      {/* Platform Performance Grid */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <h3 className="text-sm font-semibold flex items-center gap-2 mb-4">
          <Share2 size={16} className="text-warroom-accent" /> Platform Performance
        </h3>
        {accounts.length > 0 ? (
          <div className="grid grid-cols-3 gap-4">
            {accounts.map(acc => (
              <div key={acc.id} className="bg-warroom-bg border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: PLATFORM_COLORS[acc.platform] || "#666" }} />
                    <span className="text-sm font-semibold capitalize">{acc.platform}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                    <span className="text-[11px] text-green-400 font-medium">LIVE</span>
                  </div>
                </div>
                {acc.username && <p className="text-xs text-warroom-muted mb-2">@{acc.username}</p>}
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-2xl font-bold">{formatNum(acc.follower_count)}</p>
                    <p className="text-xs text-warroom-muted">followers</p>
                  </div>
                  <MiniSparkline color={PLATFORM_COLORS[acc.platform] || "#6366f1"} data={sparklineData[acc.platform]} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <Share2 size={24} className="mx-auto mb-2 opacity-20" />
            <p className="text-xs">No social accounts connected</p>
            <p className="text-[10px] mt-1">Go to Social → Connect your platforms</p>
          </div>
        )}
      </div>

      {/* Top Performing Content */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
          <Flame size={16} className="text-orange-400" /> Top Performing Content
        </h3>
        {topPerforming.length > 0 ? (
          <div className="space-y-2">
            {topPerforming.map((item, i) => (
              <div key={i} className="flex items-center gap-3 py-1.5 border-b border-warroom-border last:border-0">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: PLATFORM_COLORS[item.platform] || "#666" }} />
                <p className="text-xs font-medium flex-1 truncate">{item.title}</p>
                <span className="text-[10px] text-warroom-muted capitalize">{item.platform}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-warroom-muted text-center py-4">No posted content yet</p>
        )}
      </div>
    </div>
  );
}

// ── AI Agents Focus View ──────────────────────────────────────
function AIFocus({ agents, events }: {
  agents: { id: string; emoji: string; name: string; role: string; model: string; status?: string }[];
  events: AgentEvent[];
}) {
  return (
    <div className="space-y-6">
      {/* Agent Status Grid */}
      <div className="grid grid-cols-4 gap-4">
        {agents.map(agent => {
          const isRunning = agent.status === "working" || agent.id === "friday";
          return (
            <div key={agent.id} className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition">
              <div className="flex items-center gap-2.5 mb-3">
                <span className="text-2xl">{agent.emoji}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate">{agent.name}</p>
                  <p className="text-xs text-warroom-muted">{agent.role}</p>
                </div>
                <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${isRunning ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] px-2 py-0.5 rounded bg-warroom-accent/10 text-warroom-accent font-medium">{agent.model}</span>
                <span className={`text-[11px] ${isRunning ? "text-green-400" : "text-warroom-muted"}`}>
                  {isRunning ? "Running" : "Idle"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <ActiveAssignmentsList />

      {/* Event Feed Timeline */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <h3 className="text-sm font-semibold flex items-center gap-2 mb-4">
          <Activity size={16} className="text-warroom-accent" /> Event Feed
        </h3>
        <div className="space-y-3">
          {events.map((ev, i) => {
            const isSpawn = ev.event_type === "spawn";
            return (
              <div key={i} className="flex items-start gap-3 py-2 border-b border-warroom-border last:border-0">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  isSpawn ? "bg-warroom-accent/20" : "bg-green-500/20"
                }`}>
                  {isSpawn ? <Zap size={12} className="text-warroom-accent" /> : <CheckCircle2 size={12} className="text-green-400" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs leading-snug">{ev.summary}</p>
                  <p className="text-[10px] text-warroom-muted mt-1 flex items-center gap-1">
                    <Clock size={9} /> {timeAgo(ev.timestamp)} · {ev.from_agent} → {ev.to_agent}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
