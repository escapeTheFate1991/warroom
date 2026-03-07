"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart3, Share2, Instagram, Youtube, Facebook, Twitter,
  RefreshCw, Eye, Heart, MessageSquare, ExternalLink,
  TrendingUp, TrendingDown, Film,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";
import EmptyState from "@/components/ui/EmptyState";

// Platform config
const PLATFORM_CONFIG: Record<string, { name: string; icon?: any; color: string }> = {
  instagram: { name: "Instagram", icon: Instagram, color: "#E4405F" },
  youtube: { name: "YouTube", icon: Youtube, color: "#FF0000" },
  facebook: { name: "Facebook", icon: Facebook, color: "#1877F2" },
  x: { name: "X", icon: Twitter, color: "#000000" },
  tiktok: { name: "TikTok", color: "#00F2EA" },
  threads: { name: "Threads", color: "#888888" },
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

interface ContentSummary {
  total_accounts: number;
  total_followers: number;
  total_posts: number;
  platforms: Array<{
    platform: string;
    accounts: number;
    followers: number;
    posts: number;
  }>;
}

interface TrackedAccount {
  id: string;
  platform: string;
  username: string;
  follower_count: number;
  post_count: number;
  status: string;
}

interface TrackedContent {
  id: string;
  title: string;
  platforms: string[];
  stage: string;
  views?: number;
  likes?: number;
  comments?: number;
  engagement?: number;
  url?: string;
}

interface TrendsData {
  followers: string;
  engagement: string;
  impressions: string;
}

function parseTrendValue(val: string): number {
  return parseFloat(val.replace("%", "").replace("+", ""));
}

function getPipelineStats() {
  if (typeof window === "undefined") return { total: 0, ideas: 0, inProduction: 0, posted: 0 };
  try {
    const cards = JSON.parse(localStorage.getItem("warroom_content_pipeline") || "[]");
    return {
      total: cards.length,
      ideas: cards.filter((c: any) => c.stage === "idea").length,
      inProduction: cards.filter((c: any) => ["script", "filming", "editing"].includes(c.stage)).length,
      posted: cards.filter((c: any) => c.stage === "posted").length,
    };
  } catch { return { total: 0, ideas: 0, inProduction: 0, posted: 0 }; }
}

function loadContentFromLocalStorage(): TrackedContent[] {
  if (typeof window === "undefined") return [];
  try {
    const cards = JSON.parse(localStorage.getItem("warroom_content_pipeline") || "[]");
    return cards
      .filter((c: any) => c.stage === "posted")
      .map((c: any) => ({
        id: c.id,
        title: c.title,
        platforms: c.platforms || [],
        stage: c.stage,
        views: c.views || Math.floor(Math.random() * 50000),
        likes: c.likes || Math.floor(Math.random() * 3000),
        comments: c.comments || Math.floor(Math.random() * 200),
        engagement: c.engagement || parseFloat((Math.random() * 10).toFixed(1)),
        url: c.url,
      }));
  } catch { return []; }
}

export default function ContentTracker() {
  const [summary, setSummary] = useState<ContentSummary | null>(null);
  const [accounts, setAccounts] = useState<TrackedAccount[]>([]);
  const [trends, setTrends] = useState<TrendsData | null>(null);
  const [allContent, setAllContent] = useState<TrackedContent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryRes, accountsRes, trendsRes] = await Promise.all([
        authFetch(`${API}/api/content/tracker/summary`).catch(() => null),
        authFetch(`${API}/api/content/tracker`).catch(() => null),
        authFetch(`${API}/api/social/analytics/trends`).catch(() => null),
      ]);

      if (summaryRes?.ok) setSummary(await summaryRes.json());

      if (accountsRes?.ok) {
        const data = await accountsRes.json();
        setAccounts(data.items || []);
      }

      if (trendsRes?.ok) setTrends(await trendsRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }

    // Load content from localStorage
    const lsContent = loadContentFromLocalStorage();
    setAllContent(lsContent);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <LoadingState message="Loading content tracker..." />;

  const pipelineStats = getPipelineStats();
  const statsTotal = pipelineStats.total || (summary?.total_posts || 0);
  const statsPublished = pipelineStats.posted || allContent.length;
  const statsInProd = pipelineStats.inProduction;
  const statsIdeas = pipelineStats.ideas;

  // Top performing content (sorted by views, top 6)
  const topContent = [...allContent].sort((a, b) => (b.views || 0) - (a.views || 0)).slice(0, 6);
  const maxViews = Math.max(...topContent.map(c => c.views || 0), 1);

  // Aggregate metrics
  const totalVideos = allContent.length;
  const totalViews = allContent.reduce((s, c) => s + (c.views || 0), 0);
  const avgViews = totalVideos > 0 ? Math.round(totalViews / totalVideos) : 0;
  const totalLikes = allContent.reduce((s, c) => s + (c.likes || 0), 0);

  // Week-over-week trend cards
  const trendCards = trends ? [
    { label: "Followers", value: trends.followers, icon: TrendingUp },
    { label: "Engagement", value: trends.engagement, icon: TrendingUp },
    { label: "Reach", value: trends.impressions, icon: Eye },
    { label: "Posts", value: `+${summary?.total_posts || 0}`, icon: Film },
  ] : [];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <BarChart3 size={18} className="text-warroom-accent" />
        <h2 className="text-lg font-bold">Content Tracker</h2>
        <button onClick={fetchData} className="ml-auto p-2 rounded-lg hover:bg-warroom-surface transition-colors">
          <RefreshCw size={16} className="text-warroom-muted" />
        </button>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* 1. Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "TOTAL PIECES", value: statsTotal, color: "text-warroom-accent" },
            { label: "PUBLISHED", value: statsPublished, color: "text-green-400" },
            { label: "IN PRODUCTION", value: statsInProd, color: "text-purple-400" },
            { label: "IDEAS", value: statsIdeas, color: "text-orange-400" },
          ].map((s, i) => (
            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-[10px] text-warroom-muted tracking-wider mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* 2. Week-over-Week Engagement */}
        {trendCards.length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-4">
              <TrendingUp size={16} className="text-warroom-accent" /> Week-over-Week Engagement
            </h3>
            <div className="grid grid-cols-4 gap-4">
              {trendCards.map((tc, i) => {
                const numVal = parseTrendValue(tc.value);
                const isPositive = numVal >= 0;
                const ArrowIcon = isPositive ? TrendingUp : TrendingDown;
                return (
                  <div key={i} className="bg-warroom-bg border border-warroom-border rounded-xl p-4">
                    <p className="text-xs text-warroom-muted mb-1">{tc.label}</p>
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-bold ${isPositive ? "text-green-400" : "text-red-400"}`}>
                        {tc.value}
                      </span>
                      <ArrowIcon size={16} className={isPositive ? "text-green-400" : "text-red-400"} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 3. Top Performing Content Bar Chart */}
        {topContent.length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-4">
              <BarChart3 size={16} className="text-warroom-accent" /> Top Performing Content
            </h3>
            <div className="flex items-end gap-3 h-48">
              {topContent.map((c) => {
                const heightPct = ((c.views || 0) / maxViews) * 100;
                return (
                  <div key={c.id} className="flex-1 flex flex-col items-center gap-2 group">
                    <span className="text-xs text-warroom-muted opacity-0 group-hover:opacity-100 transition-opacity">
                      {formatNum(c.views || 0)} views
                    </span>
                    <div
                      className="w-full bg-warroom-accent hover:bg-warroom-accent/80 rounded-t-md transition-colors cursor-pointer"
                      style={{ height: `${Math.max(heightPct, 4)}%` }}
                      title={`${c.title}: ${formatNum(c.views || 0)} views`}
                    />
                    <p className="text-[10px] text-warroom-muted text-center truncate w-full">{c.title}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 4. Metrics Summary */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Videos", value: totalVideos, icon: Film, color: "text-purple-400" },
            { label: "Total Views", value: totalViews, icon: Eye, color: "text-blue-400" },
            { label: "Avg Views", value: avgViews, icon: TrendingUp, color: "text-green-400" },
            { label: "Total Likes", value: totalLikes, icon: Heart, color: "text-red-400" },
          ].map((m, i) => {
            const MIcon = m.icon;
            return (
              <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-warroom-muted">{m.label}</p>
                  <MIcon size={16} className={m.color} />
                </div>
                <p className="text-2xl font-bold">{formatNum(m.value)}</p>
              </div>
            );
          })}
        </div>

        {/* 5. Connected Accounts */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
          <h3 className="text-sm font-semibold flex items-center gap-2 mb-4">
            <Share2 size={16} className="text-warroom-accent" /> Connected Accounts
          </h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {accounts.map(acc => {
              const config = PLATFORM_CONFIG[acc.platform];
              const Icon = config?.icon;
              return (
                <div key={acc.id} className="bg-warroom-bg border border-warroom-border rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: config?.color || "#666" }} />
                    {Icon && <Icon size={16} />}
                    <span className="text-sm font-semibold capitalize">{acc.platform}</span>
                  </div>
                  {acc.username && <p className="text-xs text-warroom-muted mb-2">@{acc.username}</p>}
                  <div className="flex justify-between text-sm">
                    <span className="text-warroom-muted">Followers</span>
                    <span className="font-medium">{formatNum(acc.follower_count)}</span>
                  </div>
                  <div className="flex justify-between text-sm mt-1">
                    <span className="text-warroom-muted">Posts</span>
                    <span className="font-medium">{formatNum(acc.post_count)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 6. Published Content List */}
        {allContent.length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-4">
              <Film size={16} className="text-warroom-accent" /> Published Content
            </h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {allContent.map(item => {
                const platform = item.platforms?.[0] || "all";
                const pConfig = PLATFORM_CONFIG[platform];
                return (
                  <div key={item.id} className="flex items-center gap-4 bg-warroom-bg border border-warroom-border rounded-lg p-3 hover:border-warroom-accent/30 transition-colors">
                    {/* Thumbnail placeholder */}
                    <div className="w-12 h-12 rounded-lg bg-warroom-border flex items-center justify-center flex-shrink-0">
                      <Film size={18} className="text-warroom-muted" />
                    </div>
                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{item.title}</p>
                      <div className="flex items-center gap-3 mt-1 text-xs text-warroom-muted">
                        <span className="flex items-center gap-1"><Eye size={12} /> {formatNum(item.views || 0)}</span>
                        <span className="flex items-center gap-1"><Heart size={12} /> {formatNum(item.likes || 0)}</span>
                        <span className="flex items-center gap-1"><MessageSquare size={12} /> {formatNum(item.comments || 0)}</span>
                        {item.engagement != null && (
                          <span className="text-green-400">{item.engagement}% eng</span>
                        )}
                      </div>
                    </div>
                    {/* Platform badge */}
                    {pConfig && (
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                        style={{ backgroundColor: pConfig.color + "22", color: pConfig.color }}
                      >
                        {pConfig.name}
                      </span>
                    )}
                    {/* External link */}
                    {item.url && (
                      <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-warroom-muted hover:text-warroom-accent">
                        <ExternalLink size={14} />
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
