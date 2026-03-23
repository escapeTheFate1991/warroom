"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Instagram, Youtube, Facebook, 
  Zap, TrendingUp, BarChart3, Calendar, PlusCircle,
  CheckCircle2, Clock, Activity, Users, Eye, Share2,
  Loader2, AlertCircle, ArrowUpRight, Target, Sparkles
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────

interface SocialAccount {
  id: number;
  platform: string;
  username: string | null;
  follower_count: number;
  post_count: number;
  status: string;
  is_connected: boolean;
}

interface ContentStats {
  posts_scheduled_this_week: number;
  posts_published_today: number;
  total_engagement: number;
  engagement_rate: number;
}

interface CompetitorPulse {
  latest_activity: string;
  trending_topics: string[];
  last_updated: string;
}

interface SocialMetrics {
  total_followers: number;
  total_engagement: number;
  weekly_reach: number;
  engagement_trend: string; // "+12%" or "-5%"
}

// ── Main Component ───────────────────────────────────────────────

export default function SocialDashboard() {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [contentStats, setContentStats] = useState<ContentStats | null>(null);
  const [socialMetrics, setSocialMetrics] = useState<SocialMetrics | null>(null);
  const [competitorPulse, setCompetitorPulse] = useState<CompetitorPulse | null>(null);

  // ── Data Loading ──────────────────────────────────────────────

  const loadSocialAccounts = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/social/accounts`);
      if (res.ok) {
        const data = await res.json();
        setAccounts(data || []);
      }
    } catch (error) {
      console.error("Failed to load social accounts:", error);
    }
  }, []);

  const loadContentStats = useCallback(async () => {
    try {
      // Mock data for now - replace with actual API calls
      setContentStats({
        posts_scheduled_this_week: 12,
        posts_published_today: 3,
        total_engagement: 2847,
        engagement_rate: 4.2
      });
    } catch (error) {
      console.error("Failed to load content stats:", error);
    }
  }, []);

  const loadSocialMetrics = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/social/summary`);
      if (res.ok) {
        const data = await res.json();
        setSocialMetrics({
          total_followers: data.total_followers || 0,
          total_engagement: data.total_engagement || 0,
          weekly_reach: data.total_reach || 0,
          engagement_trend: "+12%" // Mock trend
        });
      }
    } catch (error) {
      console.error("Failed to load social metrics:", error);
      setSocialMetrics({
        total_followers: 0,
        total_engagement: 0,
        weekly_reach: 0,
        engagement_trend: "0%"
      });
    }
  }, []);

  const loadCompetitorPulse = useCallback(async () => {
    try {
      // Mock data for now
      setCompetitorPulse({
        latest_activity: "Competitor posted viral reel about trending topic",
        trending_topics: ["social media tips", "business growth", "AI tools"],
        last_updated: new Date().toISOString()
      });
    } catch (error) {
      console.error("Failed to load competitor pulse:", error);
    }
  }, []);

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([
        loadSocialAccounts(),
        loadContentStats(), 
        loadSocialMetrics(),
        loadCompetitorPulse()
      ]);
      setLoading(false);
    };
    loadAll();
  }, [loadSocialAccounts, loadContentStats, loadSocialMetrics, loadCompetitorPulse]);

  // ── Helpers ──────────────────────────────────────────────────

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'instagram': return <Instagram size={20} className="text-pink-500" />;
      case 'youtube': return <Youtube size={20} className="text-red-500" />;
      case 'facebook': return <Facebook size={20} className="text-blue-500" />;
      case 'tiktok': return <div className="w-5 h-5 bg-white rounded-sm flex items-center justify-center"><span className="text-[10px] font-bold text-black">TT</span></div>;
      default: return <Share2 size={20} className="text-gray-400" />;
    }
  };

  const getPlatformColor = (platform: string): string => {
    switch (platform.toLowerCase()) {
      case 'instagram': return 'border-pink-500/30 bg-pink-500/10';
      case 'youtube': return 'border-red-500/30 bg-red-500/10';
      case 'facebook': return 'border-blue-500/30 bg-blue-500/10';
      case 'tiktok': return 'border-white/30 bg-white/10';
      default: return 'border-gray-500/30 bg-gray-500/10';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="animate-spin text-warroom-muted" />
        <span className="ml-3 text-warroom-muted">Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-warroom-text">Social Command</h1>
          <p className="text-warroom-muted mt-1">Manage your social presence across platforms</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-warroom-muted">Last updated</p>
          <p className="text-sm font-medium text-warroom-text">{new Date().toLocaleDateString()}</p>
        </div>
      </div>

      {/* Quick Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warroom-muted">Total Followers</p>
              <p className="text-2xl font-bold text-warroom-text">{formatNumber(socialMetrics?.total_followers || 0)}</p>
            </div>
            <Users className="text-blue-400" size={24} />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs">
            <TrendingUp size={12} className="text-green-400" />
            <span className="text-green-400">{socialMetrics?.engagement_trend}</span>
            <span className="text-warroom-muted">this week</span>
          </div>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warroom-muted">Weekly Engagement</p>
              <p className="text-2xl font-bold text-warroom-text">{formatNumber(socialMetrics?.total_engagement || 0)}</p>
            </div>
            <Eye className="text-purple-400" size={24} />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs">
            <span className="text-warroom-muted">Across all platforms</span>
          </div>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warroom-muted">Scheduled Posts</p>
              <p className="text-2xl font-bold text-warroom-text">{contentStats?.posts_scheduled_this_week || 0}</p>
            </div>
            <Calendar className="text-orange-400" size={24} />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs">
            <span className="text-warroom-muted">This week</span>
          </div>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warroom-muted">Today's Posts</p>
              <p className="text-2xl font-bold text-warroom-text">{contentStats?.posts_published_today || 0}</p>
            </div>
            <CheckCircle2 className="text-green-400" size={24} />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs">
            <span className="text-warroom-muted">Published successfully</span>
          </div>
        </div>
      </div>

      {/* Connected Platforms */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-warroom-text">Connected Platforms</h2>
            <p className="text-sm text-warroom-muted">Manage your social media accounts</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-warroom-accent rounded-lg hover:bg-warroom-accent/80 transition-colors">
            <PlusCircle size={16} />
            Connect Platform
          </button>
        </div>

        {accounts.length === 0 ? (
          <div className="text-center py-8">
            <Share2 size={48} className="mx-auto text-warroom-muted mb-4" />
            <h3 className="text-lg font-medium text-warroom-text mb-2">No platforms connected</h3>
            <p className="text-warroom-muted mb-4">Connect your social media accounts to get started</p>
            <button className="px-4 py-2 bg-warroom-accent rounded-lg hover:bg-warroom-accent/80 transition-colors">
              Connect Your First Platform
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {accounts.map((account) => (
              <div key={account.id} className={`border rounded-xl p-4 ${getPlatformColor(account.platform)}`}>
                <div className="flex items-center gap-3 mb-3">
                  {getPlatformIcon(account.platform)}
                  <div>
                    <p className="font-medium text-warroom-text capitalize">{account.platform}</p>
                    <p className="text-sm text-warroom-muted">@{account.username || 'Not connected'}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-warroom-muted">Followers</span>
                  <span className="font-medium text-warroom-text">{formatNumber(account.follower_count)}</span>
                </div>
                <div className="flex items-center justify-between text-sm mt-1">
                  <span className="text-warroom-muted">Posts</span>
                  <span className="font-medium text-warroom-text">{account.post_count}</span>
                </div>
                <div className="mt-3 flex items-center gap-1">
                  {account.status === 'active' ? (
                    <>
                      <CheckCircle2 size={12} className="text-green-400" />
                      <span className="text-xs text-green-400">Connected</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle size={12} className="text-red-400" />
                      <span className="text-xs text-red-400">Disconnected</span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions & Recent Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
          <h2 className="text-lg font-semibold text-warroom-text mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            <button className="flex items-center gap-3 p-4 bg-warroom-bg border border-warroom-border rounded-lg hover:bg-warroom-border/10 transition-colors text-left">
              <Sparkles className="text-purple-400" size={20} />
              <div>
                <p className="font-medium text-warroom-text">Create Post</p>
                <p className="text-xs text-warroom-muted">AI Studio</p>
              </div>
            </button>
            
            <button className="flex items-center gap-3 p-4 bg-warroom-bg border border-warroom-border rounded-lg hover:bg-warroom-border/10 transition-colors text-left">
              <Calendar className="text-blue-400" size={20} />
              <div>
                <p className="font-medium text-warroom-text">Schedule Content</p>
                <p className="text-xs text-warroom-muted">Content Pipeline</p>
              </div>
            </button>
            
            <button className="flex items-center gap-3 p-4 bg-warroom-bg border border-warroom-border rounded-lg hover:bg-warroom-border/10 transition-colors text-left">
              <BarChart3 className="text-green-400" size={20} />
              <div>
                <p className="font-medium text-warroom-text">View Analytics</p>
                <p className="text-xs text-warroom-muted">Performance</p>
              </div>
            </button>
            
            <button className="flex items-center gap-3 p-4 bg-warroom-bg border border-warroom-border rounded-lg hover:bg-warroom-border/10 transition-colors text-left">
              <Zap className="text-orange-400" size={20} />
              <div>
                <p className="font-medium text-warroom-text">Run Mirofish</p>
                <p className="text-xs text-warroom-muted">Content Scoring</p>
              </div>
            </button>
          </div>
        </div>

        {/* Recent Performance */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-warroom-text">Recent Performance</h2>
            <ArrowUpRight size={16} className="text-warroom-muted" />
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <Instagram size={16} className="text-pink-500" />
                <span className="text-sm text-warroom-text">Instagram Reel</span>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-warroom-text">2.4K</p>
                <p className="text-xs text-green-400">+15%</p>
              </div>
            </div>
            
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <Youtube size={16} className="text-red-500" />
                <span className="text-sm text-warroom-text">YouTube Short</span>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-warroom-text">890</p>
                <p className="text-xs text-green-400">+8%</p>
              </div>
            </div>
            
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 bg-white rounded flex items-center justify-center">
                  <span className="text-[8px] font-bold text-black">TT</span>
                </div>
                <span className="text-sm text-warroom-text">TikTok Video</span>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-warroom-text">5.1K</p>
                <p className="text-xs text-green-400">+23%</p>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-warroom-border">
            <div className="flex items-center justify-between text-sm">
              <span className="text-warroom-muted">Avg. Engagement Rate</span>
              <span className="font-medium text-warroom-text">{contentStats?.engagement_rate?.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Competitor Pulse */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-warroom-text">Competitor Pulse</h2>
          <span className="text-xs text-warroom-muted">Updated {timeAgo(competitorPulse?.last_updated || new Date().toISOString())}</span>
        </div>
        
        {competitorPulse ? (
          <div className="space-y-4">
            <div className="p-4 bg-warroom-bg border border-warroom-border rounded-lg">
              <div className="flex items-start gap-3">
                <Target className="text-orange-400 mt-0.5" size={16} />
                <div>
                  <p className="text-sm font-medium text-warroom-text mb-1">Latest Activity</p>
                  <p className="text-sm text-warroom-muted">{competitorPulse.latest_activity}</p>
                </div>
              </div>
            </div>
            
            <div>
              <p className="text-sm font-medium text-warroom-text mb-2">Trending Topics</p>
              <div className="flex flex-wrap gap-2">
                {competitorPulse.trending_topics.map((topic, index) => (
                  <span 
                    key={index}
                    className="px-2 py-1 bg-warroom-accent/20 text-warroom-accent rounded text-xs"
                  >
                    #{topic}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <Activity className="mx-auto text-warroom-muted mb-2" size={24} />
            <p className="text-sm text-warroom-muted">No competitor data available</p>
          </div>
        )}
      </div>
    </div>
  );
}

function timeAgo(timestamp: string): string {
  const now = new Date();
  const past = new Date(timestamp);
  const diffMs = now.getTime() - past.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}