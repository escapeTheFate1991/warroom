"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart3, Share2, Instagram, Youtube, Facebook, Twitter,
  RefreshCw,
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

// TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
const MOCK_ACCOUNTS: TrackedAccount[] = [
  { id: "ig_1", platform: "instagram", username: "yieldlabs", follower_count: 12400, post_count: 234, status: "connected" },
  { id: "yt_1", platform: "youtube", username: "YieldLabs", follower_count: 8900, post_count: 87, status: "connected" },
  { id: "fb_1", platform: "facebook", username: "YieldLabs", follower_count: 3200, post_count: 156, status: "connected" },
  { id: "x_1", platform: "x", username: "yieldlabs", follower_count: 5600, post_count: 412, status: "connected" },
];

// TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
const MOCK_SUMMARY: ContentSummary = {
  total_accounts: 4,
  total_followers: 30100,
  total_posts: 889,
  platforms: [
    { platform: "instagram", accounts: 1, followers: 12400, posts: 234 },
    { platform: "youtube", accounts: 1, followers: 8900, posts: 87 },
    { platform: "facebook", accounts: 1, followers: 3200, posts: 156 },
    { platform: "x", accounts: 1, followers: 5600, posts: 412 },
  ],
};

export default function ContentTracker() {
  const [summary, setSummary] = useState<ContentSummary | null>(null);
  const [accounts, setAccounts] = useState<TrackedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, accountsRes] = await Promise.all([
        authFetch(`${API}/api/content/tracker/summary`),
        authFetch(`${API}/api/content/tracker`),
      ]);

      if (summaryRes.ok) {
        setSummary(await summaryRes.json());
      }
      if (accountsRes.ok) {
        const data = await accountsRes.json();
        setAccounts(data.items || []);
      }
    } catch (err) {
      // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
      console.error("Failed to load content data:", err);
      setSummary(MOCK_SUMMARY);
      setAccounts(MOCK_ACCOUNTS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <LoadingState message="Loading content tracker..." />;

  if (!summary || accounts.length === 0) {
    return (
      <EmptyState
        icon={<Share2 size={48} />}
        title="No Connected Accounts"
        description="Connect your social media accounts to track content performance across platforms."
      />
    );
  }

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
        {/* Summary KPI cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
            <p className="text-xs text-warroom-muted mb-1">Connected Platforms</p>
            <p className="text-2xl font-bold">{summary.total_accounts}</p>
          </div>
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
            <p className="text-xs text-warroom-muted mb-1">Total Followers</p>
            <p className="text-2xl font-bold">{formatNum(summary.total_followers)}</p>
          </div>
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
            <p className="text-xs text-warroom-muted mb-1">Total Posts</p>
            <p className="text-2xl font-bold">{formatNum(summary.total_posts)}</p>
          </div>
        </div>

        {/* Platform breakdown */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
          <h3 className="text-base font-bold mb-4">Platform Performance</h3>
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
      </div>
    </div>
  );
}
