"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Settings, Calendar, BarChart3, RefreshCw, Clock, Eye, Heart,
  MessageSquare, Share2, Play, Plus, User, Clock3, Target
} from "lucide-react";
import { authFetch, API } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";

interface ConnectedAccount {
  id: number;
  username: string | null;
  profile_url: string | null;
  follower_count: number;
  following_count: number;
  status: string;
  last_synced: string | null;
  avatar_url?: string;
}

interface ScheduledPost {
  id: string;
  content: string;
  media_url?: string;
  scheduled_for: string;
  status: string;
  platform_specific?: any;
}

interface PublishedPost {
  id: string;
  content: string;
  media_url?: string;
  published_at: string;
  performance: {
    views?: number;
    likes?: number;
    comments?: number;
    shares?: number;
    saves?: number;
    engagement_rate?: number;
  };
}

interface PlatformPageProps {
  platform: "instagram" | "tiktok" | "youtube" | "facebook";
  platformConfig: {
    name: string;
    icon: any;
    color: string;
    bgColor: string;
  };
}

export default function PlatformPage({ platform, platformConfig }: PlatformPageProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "scheduled" | "published" | "recycled" | "analytics">("overview");
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [publishedPosts, setPublishedPosts] = useState<PublishedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);

  const Icon = platformConfig.icon;

  // Mock data for demo - replace with actual API calls
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // TODO: Replace with actual API endpoints
      // const accountsRes = await authFetch(`${API}/api/social/accounts?platform=${platform}`);
      // const accountsData = await accountsRes.json();
      // setAccounts(accountsData.accounts || []);

      // const scheduledRes = await authFetch(`${API}/api/scheduler/posts?platform=${platform}`);
      // const scheduledData = await scheduledRes.json();
      // setScheduledPosts(scheduledData.posts || []);

      // const publishedRes = await authFetch(`${API}/api/scheduler/posts?platform=${platform}&status=published`);
      // const publishedData = await publishedRes.json();
      // setPublishedPosts(publishedData.posts || []);

      // Mock data for development
      setAccounts([
        {
          id: 1,
          username: `@${platform}_account`,
          profile_url: `https://${platform}.com/account`,
          follower_count: Math.floor(Math.random() * 50000) + 1000,
          following_count: Math.floor(Math.random() * 1000) + 100,
          status: "active",
          last_synced: new Date().toISOString(),
          avatar_url: undefined
        }
      ]);

      setScheduledPosts(Array.from({ length: 5 }, (_, i) => ({
        id: `scheduled_${i}`,
        content: `Scheduled ${platform} post ${i + 1}. This is sample content that will be posted soon.`,
        scheduled_for: new Date(Date.now() + (i * 24 * 60 * 60 * 1000)).toISOString(),
        status: "scheduled",
        media_url: i % 2 === 0 ? "/sample-image.jpg" : undefined
      })));

      setPublishedPosts(Array.from({ length: 10 }, (_, i) => ({
        id: `published_${i}`,
        content: `Published ${platform} post ${i + 1}. This is sample content that was already posted.`,
        published_at: new Date(Date.now() - (i * 12 * 60 * 60 * 1000)).toISOString(),
        performance: {
          views: Math.floor(Math.random() * 10000) + 100,
          likes: Math.floor(Math.random() * 1000) + 10,
          comments: Math.floor(Math.random() * 100) + 1,
          shares: Math.floor(Math.random() * 50) + 1,
          saves: platform === "instagram" ? Math.floor(Math.random() * 200) + 5 : undefined,
          engagement_rate: parseFloat((Math.random() * 10 + 1).toFixed(2))
        }
      })));

      if (accounts.length > 0) {
        setSelectedAccountId(accounts[0].id);
      }
    } catch (error) {
      console.error(`Failed to load ${platform} data:`, error);
    } finally {
      setLoading(false);
    }
  }, [platform, accounts.length]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatNumber = (num?: number) => {
    if (!num) return "0";
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  if (loading) {
    return <LoadingState />;
  }

  const tabs = [
    { key: "overview", label: "Overview", icon: BarChart3 },
    { key: "scheduled", label: "Scheduled", icon: Calendar },
    { key: "published", label: "Published", icon: Play },
    { key: "recycled", label: "Recycled", icon: RefreshCw },
    { key: "analytics", label: "Analytics", icon: BarChart3 },
  ] as const;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Icon size={20} style={{ color: platformConfig.color }} />
          <div>
            <h2 className="text-lg font-bold">{platformConfig.name}</h2>
            <p className="text-[11px] text-warroom-muted -mt-0.5">
              Content management for {platformConfig.name}
            </p>
          </div>
        </div>

        {/* Account Selector */}
        {accounts.length > 0 && (
          <div className="flex items-center gap-3">
            <select
              value={selectedAccountId || ""}
              onChange={(e) => setSelectedAccountId(Number(e.target.value))}
              className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm"
            >
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.username} ({formatNumber(account.follower_count)} followers)
                </option>
              ))}
            </select>
            <button
              onClick={() => {/* TODO: Add new account */}}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warroom-accent text-white text-sm font-medium hover:bg-warroom-accent/80 transition"
            >
              <Plus size={14} />
              Connect Account
            </button>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-warroom-border px-6">
        <div className="flex gap-1">
          {tabs.map((tab) => {
            const TabIcon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition ${
                  activeTab === tab.key
                    ? "border-b-2 border-warroom-accent text-warroom-accent"
                    : "text-warroom-muted hover:text-warroom-text"
                }`}
              >
                <TabIcon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Account Stats */}
            {accounts.length > 0 && selectedAccountId && (
              <div className="grid grid-cols-4 gap-4">
                {(() => {
                  const account = accounts.find(a => a.id === selectedAccountId)!;
                  const stats = [
                    { label: "Followers", value: formatNumber(account.follower_count), color: "text-warroom-accent" },
                    { label: "Following", value: formatNumber(account.following_count), color: "text-blue-400" },
                    { label: "Scheduled", value: scheduledPosts.length.toString(), color: "text-orange-400" },
                    { label: "Published", value: publishedPosts.length.toString(), color: "text-green-400" }
                  ];
                  return stats.map((stat, i) => (
                    <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                      <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                      <p className="text-[10px] text-warroom-muted tracking-wider mt-1">{stat.label.toUpperCase()}</p>
                    </div>
                  ));
                })()}
              </div>
            )}

            {/* Recent Posts Grid */}
            <div>
              <h3 className="text-sm font-bold mb-4">Recent Posts</h3>
              <div className={`grid gap-4 ${
                platform === "instagram" ? "grid-cols-3" : "grid-cols-1"
              }`}>
                {publishedPosts.slice(0, platform === "instagram" ? 9 : 5).map((post) => (
                  <div
                    key={post.id}
                    className="bg-warroom-surface border border-warroom-border rounded-lg p-4 hover:border-warroom-accent/30 transition"
                  >
                    {platform === "instagram" && (
                      <div className="aspect-square bg-warroom-bg rounded-lg mb-3 flex items-center justify-center">
                        <Icon size={24} className="text-warroom-muted" />
                      </div>
                    )}
                    <p className="text-sm line-clamp-3 mb-3">{post.content}</p>
                    <div className="flex items-center gap-4 text-xs text-warroom-muted">
                      {post.performance.views && (
                        <span className="flex items-center gap-1">
                          <Eye size={12} />
                          {formatNumber(post.performance.views)}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Heart size={12} />
                        {formatNumber(post.performance.likes)}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare size={12} />
                        {formatNumber(post.performance.comments)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-3">
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-warroom-accent text-white font-medium hover:bg-warroom-accent/80 transition">
                <Plus size={16} />
                Schedule Post
              </button>
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-text hover:border-warroom-accent/30 transition">
                <RefreshCw size={16} />
                Recycle Top Content
              </button>
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-text hover:border-warroom-accent/30 transition">
                <Settings size={16} />
                Platform Settings
              </button>
            </div>
          </div>
        )}

        {activeTab === "scheduled" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold">Scheduled Posts</h3>
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warroom-accent text-white text-sm font-medium">
                <Plus size={14} />
                New Post
              </button>
            </div>
            {scheduledPosts.map((post) => (
              <div
                key={post.id}
                className="bg-warroom-surface border border-warroom-border rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <p className="text-sm flex-1 line-clamp-3">{post.content}</p>
                  <div className="flex items-center gap-2 text-xs text-warroom-muted ml-4">
                    <Clock3 size={12} />
                    {formatDate(post.scheduled_for)}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2 py-1 rounded bg-orange-400/20 text-orange-400">
                    Scheduled
                  </span>
                  <div className="flex gap-2">
                    <button className="text-xs px-2 py-1 rounded bg-warroom-bg hover:bg-warroom-border transition">
                      Edit
                    </button>
                    <button className="text-xs px-2 py-1 rounded bg-warroom-bg hover:bg-warroom-border transition">
                      Reschedule
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "published" && (
          <div className="space-y-4">
            <h3 className="text-sm font-bold">Published Posts</h3>
            {publishedPosts.map((post) => (
              <div
                key={post.id}
                className="bg-warroom-surface border border-warroom-border rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <p className="text-sm flex-1 line-clamp-3">{post.content}</p>
                  <div className="flex items-center gap-2 text-xs text-warroom-muted ml-4">
                    <Clock3 size={12} />
                    {formatDate(post.published_at)}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 text-xs text-warroom-muted">
                    {post.performance.views && (
                      <span className="flex items-center gap-1">
                        <Eye size={12} />
                        {formatNumber(post.performance.views)}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Heart size={12} />
                      {formatNumber(post.performance.likes)}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare size={12} />
                      {formatNumber(post.performance.comments)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Target size={12} />
                      {post.performance.engagement_rate}% ER
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button className="text-xs px-2 py-1 rounded bg-warroom-bg hover:bg-warroom-border transition">
                      Recycle
                    </button>
                    <button className="text-xs px-2 py-1 rounded bg-warroom-bg hover:bg-warroom-border transition">
                      View Post
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "recycled" && (
          <div className="text-center py-12">
            <RefreshCw size={48} className="mx-auto text-warroom-muted mb-4" />
            <h3 className="text-lg font-bold mb-2">Recycle High-Performing Content</h3>
            <p className="text-sm text-warroom-muted mb-6 max-w-md mx-auto">
              Automatically identify your top-performing posts and schedule them to be reposted
              at optimal times to maximize reach and engagement.
            </p>
            <button className="px-4 py-2 rounded-lg bg-warroom-accent text-white font-medium hover:bg-warroom-accent/80 transition">
              Enable Auto-Recycling
            </button>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="text-center py-12">
            <BarChart3 size={48} className="mx-auto text-warroom-muted mb-4" />
            <h3 className="text-lg font-bold mb-2">Advanced Analytics</h3>
            <p className="text-sm text-warroom-muted mb-6 max-w-md mx-auto">
              Detailed analytics dashboard coming soon. Track engagement trends, 
              optimal posting times, and audience insights.
            </p>
            <button className="px-4 py-2 rounded-lg bg-warroom-accent text-white font-medium hover:bg-warroom-accent/80 transition">
              Request Beta Access
            </button>
          </div>
        )}
      </div>
    </div>
  );
}