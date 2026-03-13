"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  ExternalLink,
  Eye,
  Facebook,
  Film,
  Heart,
  Instagram,
  Loader2,
  MessageSquare,
  Plus,
  Share2,
  TrendingUp,
  Twitter,
  Users,
  X,
  Youtube,
  Zap,
} from "lucide-react";
import AskAIButton from "@/components/agents/AskAIButton";
import EntityAssignmentControl from "@/components/agents/EntityAssignmentControl";
import { API, authFetch } from "@/lib/api";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import LoadingState from "@/components/ui/LoadingState";

interface SocialAccount {
  id: number;
  platform: string;
  username: string | null;
  profile_url: string | null;
  follower_count: number;
  following_count: number;
  post_count: number;
  connected_at: string;
  last_synced: string | null;
  status: string;
  agent_assignments: AgentAssignmentSummary[];
}

interface SocialSummary {
  total_followers: number;
  total_engagement: number;
  total_impressions: number;
  total_reach: number;
  engagement_rate: number;
  accounts_connected: number;
  total_link_clicks: number;
  total_shares: number;
  total_saves: number;
  total_video_views: number;
  total_views: number;
  total_interactions: number;
  avg_watch_time_ms: number;
  total_watch_time_ms: number;
}

interface SocialAnalyticsSeriesPoint {
  bucket: string;
  label: string;
  engagement: number;
  impressions: number;
  reach: number;
  shares: number;
  saves: number;
  link_clicks: number;
  video_views: number;
  likes: number;
  comments: number;
}

interface ConnectAccountData {
  platform: string;
  username: string;
  profile_url: string;
  follower_count: number;
  following_count: number;
  post_count: number;
}

interface PublishedContentItem {
  id: string;
  title: string;
  platforms: string[];
  createdAt: string;
  source: "pipeline" | "platform";
  description?: string;
  notes?: string;
  url?: string;
  views?: number;
  likes?: number;
  comments?: number;
}

type Granularity = "hourly" | "daily" | "weekly" | "monthly";

interface PlatformConfig {
  id: string;
  name: string;
  color: string;
  icon?: typeof Instagram;
}

const EMPTY_SUMMARY: SocialSummary = {
  total_followers: 0,
  total_engagement: 0,
  total_impressions: 0,
  total_reach: 0,
  engagement_rate: 0,
  accounts_connected: 0,
  total_link_clicks: 0,
  total_shares: 0,
  total_saves: 0,
  total_video_views: 0,
  total_views: 0,
  total_interactions: 0,
  avg_watch_time_ms: 0,
  total_watch_time_ms: 0,
};

const PLATFORMS: PlatformConfig[] = [
  { id: "instagram", name: "Instagram", icon: Instagram, color: "#E4405F" },
  { id: "facebook", name: "Facebook", icon: Facebook, color: "#1877F2" },
  { id: "threads", name: "Threads", color: "#888888" },
  { id: "youtube", name: "YouTube", icon: Youtube, color: "#FF0000" },
  { id: "x", name: "X", icon: Twitter, color: "#9CA3AF" },
  { id: "tiktok", name: "TikTok", color: "#00F2EA" },
];

const GRANULARITY_OPTIONS: { id: Granularity; label: string }[] = [
  { id: "hourly", label: "Hourly" },
  { id: "daily", label: "Daily" },
  { id: "weekly", label: "Weekly" },
  { id: "monthly", label: "Monthly" },
];

const OAUTH_PLATFORMS: Record<string, { provider: string; params?: Record<string, string> }> = {
  instagram: { provider: "meta", params: { platform: "instagram" } },
  facebook: { provider: "meta", params: { platform: "facebook" } },
  threads: { provider: "meta", params: { platform: "threads" } },
  x: { provider: "x" },
  tiktok: { provider: "tiktok" },
  youtube: { provider: "google" },
};

function safeParseArray(raw: string | null): any[] {
  try {
    const parsed = JSON.parse(raw || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function toOptionalNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function normalizePlatforms(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === "string" && item.length > 0);
  }
  if (typeof value === "string" && value.length > 0) {
    return [value];
  }
  return [];
}

function loadPublishedContent(): PublishedContentItem[] {
  if (typeof window === "undefined") return [];

  const collected: PublishedContentItem[] = [];
  const pipelineCards = safeParseArray(localStorage.getItem("warroom_content_pipeline"));

  pipelineCards
    .filter((card) => card?.stage === "posted")
    .forEach((card) => {
      collected.push({
        id: String(card.id || `${card.title || "content"}-${card.createdAt || Date.now()}`),
        title: typeof card.title === "string" ? card.title : "Untitled content",
        platforms: normalizePlatforms(card.platforms),
        createdAt: typeof card.createdAt === "string" ? card.createdAt : new Date(0).toISOString(),
        source: "pipeline",
        notes: typeof card.notes === "string" ? card.notes : undefined,
        url: typeof card.url === "string" ? card.url : undefined,
        views: toOptionalNumber(card.views),
        likes: toOptionalNumber(card.likes),
        comments: toOptionalNumber(card.comments),
      });
    });

  PLATFORMS.forEach((platform) => {
    const platformCards = safeParseArray(localStorage.getItem(`warroom_content_${platform.id}`));
    platformCards
      .filter((card) => card?.stage === "posted")
      .forEach((card) => {
        collected.push({
          id: String(card.id || `${platform.id}-${card.title || "content"}-${card.createdAt || Date.now()}`),
          title: typeof card.title === "string" ? card.title : "Untitled content",
          platforms: [platform.id],
          createdAt: typeof card.createdAt === "string" ? card.createdAt : new Date(0).toISOString(),
          source: "platform",
          description: typeof card.description === "string" ? card.description : undefined,
          notes: typeof card.hook === "string" ? card.hook : undefined,
          views: toOptionalNumber(card.views),
          likes: toOptionalNumber(card.likes),
          comments: toOptionalNumber(card.comments),
        });
      });
  });

  const deduped = new Map<string, PublishedContentItem>();
  collected.forEach((item) => {
    const dedupeKey = `${item.title.toLowerCase()}::${item.platforms.slice().sort().join(",")}::${item.createdAt}`;
    const existing = deduped.get(dedupeKey);

    if (!existing) {
      deduped.set(dedupeKey, item);
      return;
    }

    deduped.set(dedupeKey, {
      ...existing,
      description: existing.description || item.description,
      notes: existing.notes || item.notes,
      url: existing.url || item.url,
      views: existing.views ?? item.views,
      likes: existing.likes ?? item.likes,
      comments: existing.comments ?? item.comments,
      source: existing.source === "platform" ? existing.source : item.source,
    });
  });

  return Array.from(deduped.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );
}

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  if (!data.length) return null;

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const width = 120;
  const height = 40;
  const denominator = Math.max(data.length - 1, 1);
  const points = data
    .map((value, index) => `${(index / denominator) * width},${height - ((value - min) / range) * height}`)
    .join(" ");

  return (
    <svg width={width} height={height} className="opacity-70">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function formatNum(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function formatRecordedDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return date.toLocaleDateString();
}

function summarizeAssignedAgents(assignments: AgentAssignmentSummary[] = []) {
  if (assignments.length === 0) return "No shared AI agents assigned yet.";
  return assignments
    .slice(0, 2)
    .map((assignment) => `${assignment.agent_emoji || "🤖"} ${assignment.agent_name || assignment.agent_id}`)
    .join(" · ");
}

function PlatformIcon({ platform, size = 20 }: { platform: string; size?: number }) {
  const item = PLATFORMS.find((entry) => entry.id === platform);
  const Icon = item?.icon;

  if (Icon) {
    return <Icon size={size} style={{ color: item.color }} />;
  }

  return (
    <div
      className="rounded-full flex items-center justify-center text-white font-bold text-xs"
      style={{ backgroundColor: item?.color || "#666", width: size, height: size }}
    >
      {platform.charAt(0).toUpperCase()}
    </div>
  );
}

export default function SocialDashboard() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [summary, setSummary] = useState<SocialSummary>(EMPTY_SUMMARY);
  const [sparklineData, setSparklineData] = useState<Record<string, number[]>>({});
  const [timeSeries, setTimeSeries] = useState<SocialAnalyticsSeriesPoint[]>([]);
  const [publishedContent, setPublishedContent] = useState<PublishedContentItem[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const [granularity, setGranularity] = useState<Granularity>("daily");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [velocityData, setVelocityData] = useState<any[]>([]);
  const [showManualModal, setShowManualModal] = useState(false);
  const [connectPlatform, setConnectPlatform] = useState("");
  const [connectForm, setConnectForm] = useState<ConnectAccountData>({
    platform: "",
    username: "",
    profile_url: "",
    follower_count: 0,
    following_count: 0,
    post_count: 0,
  });

  const selectedPlatformLabel =
    selectedPlatform === "all"
      ? "All platforms"
      : PLATFORMS.find((platform) => platform.id === selectedPlatform)?.name || selectedPlatform;

  const loadLocalContent = useCallback(() => {
    setPublishedContent(loadPublishedContent());
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);

    try {
      const summaryParams = new URLSearchParams();
      if (selectedPlatform !== "all") {
        summaryParams.set("platform", selectedPlatform);
      }

      const timeSeriesParams = new URLSearchParams();
      if (selectedPlatform !== "all") {
        timeSeriesParams.set("platform", selectedPlatform);
      }
      if (granularity !== "hourly") {
        timeSeriesParams.set("granularity", granularity);
      }

      const [accResp, sumResp, sparkResp, seriesResp, velocityResp] = await Promise.all([
        authFetch(`${API}/api/social/accounts`).catch(() => null),
        authFetch(`${API}/api/social/analytics${summaryParams.toString() ? `?${summaryParams.toString()}` : ""}`).catch(() => null),
        authFetch(`${API}/api/social/analytics/sparkline`).catch(() => null),
        granularity === "hourly"
          ? Promise.resolve(null)
          : authFetch(`${API}/api/social/analytics/timeseries?${timeSeriesParams.toString()}`).catch(() => null),
        authFetch(`${API}/api/social/analytics/engagement-velocity`).catch(() => null),
      ]);

      if (accResp?.ok) {
        setAccounts(await accResp.json());
      }

      if (sumResp?.ok) {
        setSummary(await sumResp.json());
      } else {
        setSummary(EMPTY_SUMMARY);
      }

      if (sparkResp?.ok) {
        setSparklineData(await sparkResp.json());
      } else {
        setSparklineData({});
      }

      if (granularity === "hourly") {
        setTimeSeries([]);
      } else if (seriesResp?.ok) {
        setTimeSeries(await seriesResp.json());
      } else {
        setTimeSeries([]);
      }

      if (velocityResp?.ok) {
        const vData = await velocityResp.json();
        setVelocityData(vData.points || []);
      } else {
        setVelocityData([]);
      }
    } catch (error) {
      console.error("Failed to fetch social dashboard data:", error);
      setSummary(EMPTY_SUMMARY);
      setTimeSeries([]);
    } finally {
      setLoading(false);
    }
  }, [granularity, selectedPlatform]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    loadLocalContent();

    const onStorage = () => loadLocalContent();
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [loadLocalContent]);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === "oauth_complete") {
        fetchData();
        if (event.data.status === "error" && event.data.error) {
          alert(event.data.error);
        }
      }
    };

    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [fetchData]);

  const startOAuth = async (platform: string) => {
    const oauth = OAUTH_PLATFORMS[platform];
    if (!oauth) {
      openManual(platform);
      return;
    }

    try {
      const params = new URLSearchParams(oauth.params || {});
      const url = `${API}/api/social/oauth/${oauth.provider}/authorize${params.toString() ? `?${params.toString()}` : ""}`;
      const res = await authFetch(url);

      if (res.ok) {
        const data = await res.json();
        if (data.auth_url) {
          window.open(data.auth_url, "_blank", "width=600,height=700");
          return;
        }
      }

      if (res.status === 400) {
        alert(`OAuth not configured for ${platform}. Add credentials in Settings → API Keys.`);
      }
    } catch {
      // Fall back to manual connect.
    }

    openManual(platform);
  };

  const openManual = (platform: string) => {
    setConnectPlatform(platform);
    setConnectForm({
      platform,
      username: "",
      profile_url: "",
      follower_count: 0,
      following_count: 0,
      post_count: 0,
    });
    setShowManualModal(true);
  };

  const handleManualConnect = async () => {
    try {
      const res = await authFetch(`${API}/api/social/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(connectForm),
      });

      if (res.ok) {
        await fetchData();
        setShowManualModal(false);
      }
    } catch (error) {
      console.error(error);
    }
  };

  const handleDisconnect = async (id: number) => {
    try {
      const res = await authFetch(`${API}/api/social/accounts/${id}`, { method: "DELETE" });
      if (res.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error(error);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await authFetch(`${API}/api/social/sync`, { method: "POST" });
      if (res.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error("Failed to sync:", error);
    } finally {
      setSyncing(false);
    }
  };

  const getAccount = (platformId: string) => accounts.find((account) => account.platform === platformId);
  const getSparklineData = (platformId: string) => sparklineData[platformId] || Array(7).fill(0);
  const scopedAccounts = selectedPlatform === "all"
    ? accounts
    : accounts.filter((account) => account.platform === selectedPlatform);

  const filteredPublishedContent = useMemo(() => {
    return publishedContent
      .filter((item) => selectedPlatform === "all" || item.platforms.includes(selectedPlatform))
      .slice(0, 8);
  }, [publishedContent, selectedPlatform]);

  const savesAndShares = summary.total_saves + summary.total_shares;
  const avgWatchSec = summary.avg_watch_time_ms > 0 ? (summary.avg_watch_time_ms / 1000).toFixed(1) + "s" : "—";
  const totalWatchMin = summary.total_watch_time_ms > 0
    ? Math.floor(summary.total_watch_time_ms / 60000) + "m " + Math.floor((summary.total_watch_time_ms % 60000) / 1000) + "s"
    : "—";
  const chartMax = Math.max(...timeSeries.map((point) => point.engagement), 1);
  const chartPeak = timeSeries.reduce<SocialAnalyticsSeriesPoint | null>((current, point) => {
    if (!current || point.engagement > current.engagement) return point;
    return current;
  }, null);
  const chartTotal = timeSeries.reduce((sum, point) => sum + point.engagement, 0);

  const metricCards = [
    { label: "Followers", value: formatNum(summary.total_followers), icon: Users, tone: "text-blue-400" },
    { label: "Views", value: formatNum(summary.total_views || summary.total_video_views), icon: Eye, tone: "text-purple-400" },
    { label: "Reach", value: formatNum(summary.total_reach), icon: BarChart3, tone: "text-indigo-400" },
    { label: "Interactions", value: formatNum(summary.total_interactions || summary.total_engagement), icon: Zap, tone: "text-green-400" },
    { label: "Avg Watch Time", value: avgWatchSec, icon: Film, tone: "text-rose-400" },
    { label: "Total Watch Time", value: totalWatchMin, icon: Film, tone: "text-pink-400" },
    { label: "Saves + Shares", value: formatNum(savesAndShares), icon: Share2, tone: "text-orange-400" },
    { label: "Engagement Rate", value: formatPercent(summary.engagement_rate), icon: TrendingUp, tone: "text-emerald-400" },
  ];

  if (loading) {
    return <LoadingState message="Loading analytics..." />;
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="border-b border-warroom-border px-6 py-4 flex-shrink-0">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <Share2 size={18} className="text-warroom-accent mt-0.5" />
            <div>
              <h2 className="text-base font-semibold">Social Analytics</h2>
              <p className="text-xs text-warroom-muted mt-1">
                Aggregate engagement performance across supported platforms with real content records at the bottom.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="flex items-center gap-2 text-xs text-warroom-muted">
              <span>Scope</span>
              <select
                value={selectedPlatform}
                onChange={(event) => setSelectedPlatform(event.target.value)}
                className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="all">All platforms</option>
                {PLATFORMS.map((platform) => (
                  <option key={platform.id} value={platform.id}>
                    {platform.name}
                  </option>
                ))}
              </select>
            </label>

            <button
              onClick={handleSync}
              disabled={syncing || accounts.length === 0}
              className="flex items-center justify-center gap-2 px-3 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition"
            >
              {syncing ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />}
              {syncing ? "Syncing..." : "Sync now"}
            </button>

            <AskAIButton
              context={{
                surface: "social",
                entityType: "dashboard_view",
                entityId: `social-dashboard:${selectedPlatform}`,
                entityName: `${selectedPlatformLabel} social dashboard`,
                title: `${selectedPlatformLabel} social coverage`,
                summary: `${scopedAccounts.length} connected account(s) in view with ${formatNum(summary.total_engagement)} engagements tracked.`,
                facts: [
                  { label: "Accounts in view", value: scopedAccounts.length },
                  { label: "Followers", value: summary.total_followers },
                  { label: "Engagement rate", value: formatPercent(summary.engagement_rate) },
                  { label: "Reach", value: summary.total_reach },
                ],
              }}
              buttonLabel="Ask AI about social"
              emptyHint="Ask for a channel diagnosis, content angle, or next experiment..."
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5 gap-4">
            {metricCards.map((card) => {
              const Icon = card.icon;
              return (
                <div key={card.label} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-warroom-muted font-medium">{card.label}</span>
                    <Icon size={16} className={card.tone} />
                  </div>
                  <div className={`text-2xl font-bold ${card.tone}`}>{card.value}</div>
                  <p className="text-[11px] text-warroom-muted mt-2">{selectedPlatformLabel}</p>
                </div>
              );
            })}
          </div>

          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between mb-5">
              <div>
                <h3 className="text-sm font-semibold">Engagement performance</h3>
                <p className="text-xs text-warroom-muted mt-1">
                  {selectedPlatformLabel} · real stored social analytics only
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                {GRANULARITY_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => setGranularity(option.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      granularity === option.id
                        ? "bg-warroom-accent text-white"
                        : "bg-warroom-bg border border-warroom-border text-warroom-muted hover:text-warroom-text"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {granularity === "hourly" ? (
              <div className="rounded-xl border border-dashed border-warroom-border bg-warroom-bg/50 px-5 py-10 text-center">
                <BarChart3 size={28} className="mx-auto mb-3 text-warroom-muted" />
                <p className="text-sm font-medium">Hourly analytics are not available yet</p>
                <p className="text-xs text-warroom-muted mt-2">
                  The current backend stores social analytics as daily snapshots, so the hourly toggle is shown honestly but cannot render real data yet.
                </p>
              </div>
            ) : timeSeries.length === 0 ? (
              <div className="rounded-xl border border-dashed border-warroom-border bg-warroom-bg/50 px-5 py-10 text-center">
                <BarChart3 size={28} className="mx-auto mb-3 text-warroom-muted" />
                <p className="text-sm font-medium">No analytics data yet</p>
                <p className="text-xs text-warroom-muted mt-2">
                  Connect and sync a platform to populate the engagement chart.
                </p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
                  <div className="rounded-xl bg-warroom-bg border border-warroom-border px-4 py-3">
                    <p className="text-[11px] text-warroom-muted">Total engagement in view</p>
                    <p className="text-lg font-semibold mt-1">{formatNum(chartTotal)}</p>
                  </div>
                  <div className="rounded-xl bg-warroom-bg border border-warroom-border px-4 py-3">
                    <p className="text-[11px] text-warroom-muted">Peak bucket</p>
                    <p className="text-lg font-semibold mt-1">{chartPeak ? `${chartPeak.label} · ${formatNum(chartPeak.engagement)}` : "—"}</p>
                  </div>
                  <div className="rounded-xl bg-warroom-bg border border-warroom-border px-4 py-3">
                    <p className="text-[11px] text-warroom-muted">Saves + shares in view</p>
                    <p className="text-lg font-semibold mt-1">
                      {formatNum(timeSeries.reduce((sum, point) => sum + point.saves + point.shares, 0))}
                    </p>
                  </div>
                </div>

                <div className="h-72 flex gap-2 rounded-xl bg-warroom-bg border border-warroom-border p-4 overflow-x-auto">
                  {timeSeries.map((point) => {
                    const height = point.engagement > 0 ? Math.max((point.engagement / chartMax) * 100, 8) : 4;

                    return (
                      <div key={`${point.bucket}-${point.label}`} className="min-w-[44px] flex-1 h-full flex flex-col items-center justify-end gap-2">
                        <div className="text-[10px] text-warroom-muted">{formatNum(point.engagement)}</div>
                        <div
                          className="w-full rounded-t-lg bg-gradient-to-t from-warroom-accent/30 to-warroom-accent"
                          style={{ height: `${height}%` }}
                          title={`${point.label}: ${point.engagement} engagement`}
                        />
                        <div className="text-[10px] text-warroom-muted text-center leading-tight">{point.label}</div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>

          {/* Engagement Velocity Chart */}
          {velocityData.length > 1 && (
            <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <TrendingUp size={16} className="text-warroom-accent" />
                    Engagement Velocity
                  </h3>
                  <p className="text-xs text-warroom-muted mt-0.5">How engagement grows over time — helps find best posting times</p>
                </div>
              </div>
              <div className="h-48 flex items-end gap-px">
                {(() => {
                  const maxViews = Math.max(...velocityData.map(p => p.views || 0), 1);
                  const maxLikes = Math.max(...velocityData.map(p => p.likes || 0), 1);
                  return velocityData.map((point, i) => {
                    const viewH = Math.max(((point.views || 0) / maxViews) * 100, 2);
                    const likeH = Math.max(((point.likes || 0) / maxLikes) * 100, 2);
                    const time = new Date(point.time);
                    const label = `${time.getMonth()+1}/${time.getDate()} ${time.getHours()}:${String(time.getMinutes()).padStart(2,'0')}`;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-0.5 group relative min-w-0">
                        <div className="w-full flex gap-px items-end" style={{ height: '160px' }}>
                          <div className="flex-1 rounded-t bg-purple-500/60 transition-all" style={{ height: `${viewH}%` }} title={`Views: ${point.views}`} />
                          <div className="flex-1 rounded-t bg-pink-500/60 transition-all" style={{ height: `${likeH}%` }} title={`Likes: ${point.likes}`} />
                        </div>
                        {(i === 0 || i === velocityData.length - 1 || i % Math.max(1, Math.floor(velocityData.length / 6)) === 0) && (
                          <span className="text-[8px] text-warroom-muted truncate max-w-full">{label}</span>
                        )}
                        <div className="absolute bottom-full mb-2 hidden group-hover:block bg-warroom-bg border border-warroom-border rounded-lg px-2.5 py-1.5 text-[10px] z-10 whitespace-nowrap shadow-lg">
                          <p className="text-warroom-text font-medium">{label}</p>
                          <p className="text-purple-400">Views: {(point.views || 0).toLocaleString()}</p>
                          <p className="text-pink-400">Likes: {point.likes || 0}</p>
                          <p className="text-blue-400">Reach: {(point.reach || 0).toLocaleString()}</p>
                          <p className="text-green-400">Interactions: {point.interactions || 0}</p>
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
              <div className="flex items-center gap-4 mt-3 text-[10px] text-warroom-muted">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500/60" /> Views</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-pink-500/60" /> Likes</span>
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Platforms</h3>
              <span className="text-xs text-warroom-muted">{accounts.length} connected</span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {PLATFORMS.map((platform) => {
                const account = getAccount(platform.id);
                const isFocused = selectedPlatform === platform.id;

                return (
                  <div
                    key={platform.id}
                    className={`bg-warroom-surface border rounded-2xl p-5 transition-all ${
                      isFocused
                        ? "border-warroom-accent shadow-lg shadow-warroom-accent/10"
                        : "border-warroom-border"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-4">
                      <div className="flex items-center gap-3">
                        <PlatformIcon platform={platform.id} size={24} />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{platform.name}</span>
                            {isFocused && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-warroom-accent/15 text-warroom-accent font-medium">
                                Focused
                              </span>
                            )}
                          </div>
                          {account?.username ? (
                            <p className="text-xs text-warroom-muted mt-1">@{account.username}</p>
                          ) : (
                            <p className="text-xs text-warroom-muted mt-1">Not connected yet</p>
                          )}
                        </div>
                      </div>

                      {account ? (
                        <button
                          onClick={() => setSelectedPlatform(selectedPlatform === platform.id ? "all" : platform.id)}
                          className="text-xs px-3 py-1.5 rounded-lg border border-warroom-border bg-warroom-bg hover:border-warroom-accent/40 transition"
                        >
                          {isFocused ? "Show all" : "Focus"}
                        </button>
                      ) : (
                        <button
                          onClick={() => startOAuth(platform.id)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition"
                        >
                          <Plus size={12} /> Connect
                        </button>
                      )}
                    </div>

                    {account ? (
                      <>
                        <div className="grid grid-cols-3 gap-3 mb-4">
                          <div>
                            <p className="text-lg font-bold">{formatNum(account.follower_count)}</p>
                            <p className="text-[10px] text-warroom-muted">Followers</p>
                          </div>
                          <div>
                            <p className="text-lg font-bold">{formatNum(account.post_count)}</p>
                            <p className="text-[10px] text-warroom-muted">Posts</p>
                          </div>
                          <div>
                            <p className="text-lg font-bold">{formatNum(account.following_count)}</p>
                            <p className="text-[10px] text-warroom-muted">Following</p>
                          </div>
                        </div>

                        <div className="mb-3">
                          <MiniSparkline data={getSparklineData(platform.id)} color={platform.color} />
                          <p className="text-[10px] text-warroom-muted mt-1">Daily engagement · last 7 days</p>
                        </div>

                        {account.last_synced && (
                          <p className="text-[10px] text-warroom-muted mb-3">
                            Last synced {new Date(account.last_synced).toLocaleString()}
                          </p>
                        )}

                        <p className="mb-3 text-xs text-warroom-muted">{summarizeAssignedAgents(account.agent_assignments)}</p>

                        <div className="flex items-center justify-between pt-3 border-t border-warroom-border/50">
                          {account.profile_url ? (
                            <a
                              href={account.profile_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-warroom-accent hover:underline flex items-center gap-1"
                            >
                              <ExternalLink size={12} /> View profile
                            </a>
                          ) : (
                            <span className="text-xs text-warroom-muted">Connected account</span>
                          )}

                          <button
                            onClick={() => handleDisconnect(account.id)}
                            className="text-xs text-warroom-muted hover:text-red-400 transition"
                          >
                            Disconnect
                          </button>
                        </div>

                        <EntityAssignmentControl
                          className="mt-4 border-0 bg-transparent p-0"
                          entityType="social_account"
                          entityId={account.id}
                          title={`Own ${platform.name} account: @${account.username || platform.name}`}
                          initialAssignments={account.agent_assignments || []}
                          emptyLabel={`No AI agents assigned to this ${platform.name} account yet.`}
                        />
                      </>
                    ) : (
                      <div className="rounded-xl border border-dashed border-warroom-border bg-warroom-bg/40 px-4 py-6 text-center">
                        <p className="text-xs text-warroom-muted">
                          Connect {platform.name} to include it in the aggregate analytics view.
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <h3 className="text-sm font-semibold">Recent published content</h3>
                <p className="text-xs text-warroom-muted mt-1">
                  Sourced from current local content records. Metrics appear only when those records actually store them.
                </p>
              </div>
              <span className="text-xs text-warroom-muted">{selectedPlatformLabel}</span>
            </div>

            <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
              {filteredPublishedContent.length === 0 ? (
                <div className="text-center py-10 text-warroom-muted">
                  <Film size={28} className="mx-auto mb-3 opacity-40" />
                  <p className="text-sm">No published content found for this scope yet</p>
                  <p className="text-xs mt-2">Move items to the posted stage in the content pipeline to surface them here.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredPublishedContent.map((item) => {
                    const hasMetrics = item.views != null || item.likes != null || item.comments != null;

                    return (
                      <div
                        key={`${item.source}-${item.id}`}
                        className="flex flex-col gap-4 rounded-xl border border-warroom-border bg-warroom-bg/60 p-4 lg:flex-row lg:items-center"
                      >
                        <div className="w-12 h-12 rounded-xl bg-warroom-surface border border-warroom-border flex items-center justify-center flex-shrink-0">
                          <Film size={18} className="text-warroom-muted" />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <p className="text-sm font-medium truncate">{item.title}</p>
                            {item.platforms.map((platform) => (
                              <span
                                key={`${item.id}-${platform}`}
                                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium bg-warroom-surface border border-warroom-border"
                              >
                                <PlatformIcon platform={platform} size={12} />
                                {PLATFORMS.find((entry) => entry.id === platform)?.name || platform}
                              </span>
                            ))}
                          </div>

                          {(item.description || item.notes) && (
                            <p className="text-xs text-warroom-muted line-clamp-2 mb-2">
                              {item.description || item.notes}
                            </p>
                          )}

                          <div className="flex flex-wrap items-center gap-3 text-[11px] text-warroom-muted">
                            <span>Recorded {formatRecordedDate(item.createdAt)}</span>
                            <span className="capitalize">Source: {item.source}</span>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-warroom-muted lg:justify-end">
                          {hasMetrics ? (
                            <>
                              <span className="inline-flex items-center gap-1"><Eye size={12} /> {formatNum(item.views || 0)}</span>
                              <span className="inline-flex items-center gap-1"><Heart size={12} /> {formatNum(item.likes || 0)}</span>
                              <span className="inline-flex items-center gap-1"><MessageSquare size={12} /> {formatNum(item.comments || 0)}</span>
                            </>
                          ) : (
                            <span>Metrics pending</span>
                          )}

                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-warroom-accent hover:underline"
                            >
                              <ExternalLink size={12} /> Open
                            </a>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showManualModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <PlatformIcon platform={connectPlatform} size={20} />
                Connect {PLATFORMS.find((platform) => platform.id === connectPlatform)?.name}
              </h3>
              <button onClick={() => setShowManualModal(false)} className="text-warroom-muted hover:text-warroom-text">
                <X size={20} />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Username</label>
                <input
                  type="text"
                  value={connectForm.username}
                  onChange={(event) => setConnectForm({ ...connectForm, username: event.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent font-mono"
                  placeholder="@username"
                />
              </div>

              <div>
                <label className="text-xs text-warroom-muted block mb-1">Profile URL</label>
                <input
                  type="url"
                  value={connectForm.profile_url}
                  onChange={(event) => setConnectForm({ ...connectForm, profile_url: event.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent font-mono"
                  placeholder="https://..."
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "Followers", key: "follower_count" as const },
                  { label: "Following", key: "following_count" as const },
                  { label: "Posts", key: "post_count" as const },
                ].map((field) => (
                  <div key={field.key}>
                    <label className="text-xs text-warroom-muted block mb-1">{field.label}</label>
                    <input
                      type="number"
                      value={connectForm[field.key]}
                      onChange={(event) =>
                        setConnectForm({
                          ...connectForm,
                          [field.key]: parseInt(event.target.value, 10) || 0,
                        })
                      }
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button
                onClick={() => setShowManualModal(false)}
                className="flex-1 px-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm hover:bg-warroom-surface transition"
              >
                Cancel
              </button>
              <button
                onClick={handleManualConnect}
                disabled={!connectForm.username}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition"
              >
                Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
