"use client";

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw, TrendingUp, Heart, MessageSquare, Share2, Eye, Instagram,
  Youtube, Facebook, Twitter, Settings, Clock, BarChart3, Zap, Target
} from "lucide-react";
import { authFetch, API } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";

interface RecyclableContent {
  id: string;
  content: string;
  platform: string;
  original_post_date: string;
  media_url?: string;
  account_username: string;
  performance: {
    views?: number;
    likes: number;
    comments: number;
    shares: number;
    saves?: number;
    engagement_rate: number;
    viral_score: number;
  };
  last_recycled?: string;
  recycle_count: number;
  optimal_cadence_days: number;
}

interface RecycleSettings {
  platform: string;
  account_username: string;
  auto_recycle_enabled: boolean;
  cadence_days: number;
  min_engagement_rate: number;
  max_recycles_per_post: number;
}

const PLATFORM_CONFIG = {
  instagram: { name: "Instagram", icon: Instagram, color: "#E4405F" },
  tiktok: { name: "TikTok", icon: TwitterIcon, color: "#000000" },
  youtube: { name: "YouTube", icon: Youtube, color: "#FF0000" },
  facebook: { name: "Facebook", icon: Facebook, color: "#1877F2" },
};

// Custom TikTok Icon
function TwitterIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.589 6.686a4.793 4.793 0 0 1-3.77-4.245V2h-3.445v13.672a2.896 2.896 0 0 1-5.201 1.743l-.002-.001.002.001a2.895 2.895 0 0 1 3.183-4.51v-3.5a6.329 6.329 0 0 0-1.183-.11C5.6 8.205 2.17 11.634 2.17 15.98c0 4.344 3.429 7.674 7.774 7.674 4.344 0 7.874-3.33 7.874-7.674V10.12a8.23 8.23 0 0 0 4.715 1.49V8.56a4.831 4.831 0 0 1-2.944-1.874z"/>
    </svg>
  );
}

export default function RecyclePanel() {
  const [recyclableContent, setRecyclableContent] = useState<RecyclableContent[]>([]);
  const [recycleSettings, setRecycleSettings] = useState<RecycleSettings[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"engagement_rate" | "viral_score" | "likes">("engagement_rate");
  const [filterPlatform, setFilterPlatform] = useState<string>("all");
  const [showSettings, setShowSettings] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // TODO: Replace with actual API calls
      // const contentRes = await authFetch(`${API}/api/scheduler/recycle/candidates`);
      // const contentData = await contentRes.json();
      // setRecyclableContent(contentData.candidates || []);
      
      // const settingsRes = await authFetch(`${API}/api/scheduler/recycle/settings`);
      // const settingsData = await settingsRes.json();
      // setRecycleSettings(settingsData.settings || []);

      // Mock data for development
      const platforms = ["instagram", "tiktok", "youtube", "facebook"];
      const mockContent: RecyclableContent[] = Array.from({ length: 12 }, (_, i) => {
        const platform = platforms[i % platforms.length];
        const pastDate = new Date();
        pastDate.setDate(pastDate.getDate() - (7 + i * 3));
        
        return {
          id: `recyclable_${i}`,
          content: `Top performing ${PLATFORM_CONFIG[platform as keyof typeof PLATFORM_CONFIG].name} post ${i + 1}. This content performed exceptionally well and is perfect for recycling to reach new audiences.`,
          platform,
          original_post_date: pastDate.toISOString(),
          account_username: `@${platform}_account`,
          performance: {
            views: Math.floor(Math.random() * 50000) + 5000,
            likes: Math.floor(Math.random() * 2000) + 100,
            comments: Math.floor(Math.random() * 200) + 10,
            shares: Math.floor(Math.random() * 100) + 5,
            saves: platform === "instagram" ? Math.floor(Math.random() * 300) + 20 : undefined,
            engagement_rate: parseFloat((Math.random() * 8 + 2).toFixed(1)),
            viral_score: Math.floor(Math.random() * 40) + 60
          },
          recycle_count: Math.floor(Math.random() * 3),
          optimal_cadence_days: 30 + Math.floor(Math.random() * 30),
          last_recycled: i < 3 ? undefined : pastDate.toISOString()
        };
      });

      const mockSettings: RecycleSettings[] = platforms.map(platform => ({
        platform,
        account_username: `@${platform}_account`,
        auto_recycle_enabled: Math.random() > 0.5,
        cadence_days: 30,
        min_engagement_rate: 3.0,
        max_recycles_per_post: 3
      }));

      setRecyclableContent(mockContent);
      setRecycleSettings(mockSettings);
    } catch (error) {
      console.error("Failed to load recycle data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

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
      year: "numeric"
    });
  };

  const getViralScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-400";
    if (score >= 60) return "text-yellow-400";
    return "text-orange-400";
  };

  const handleRecyclePost = async (postId: string) => {
    try {
      // TODO: Implement actual recycling API
      // const response = await authFetch(`${API}/api/scheduler/recycle`, {
      //   method: "POST",
      //   body: JSON.stringify({ post_id: postId })
      // });
      
      // if (response.ok) {
      //   await loadData(); // Refresh data
      // }
      
      console.log("Recycling post:", postId);
      // Mock update
      setRecyclableContent(prev => 
        prev.map(content => 
          content.id === postId 
            ? { ...content, recycle_count: content.recycle_count + 1, last_recycled: new Date().toISOString() }
            : content
        )
      );
    } catch (error) {
      console.error("Failed to recycle post:", error);
    }
  };

  const updateSettings = async (platform: string, updates: Partial<RecycleSettings>) => {
    try {
      // TODO: Implement actual settings update API
      // const response = await authFetch(`${API}/api/scheduler/recycle/settings`, {
      //   method: "PUT",
      //   body: JSON.stringify({ platform, ...updates })
      // });
      
      // if (response.ok) {
      //   await loadData(); // Refresh data
      // }
      
      console.log("Updating settings for", platform, updates);
      // Mock update
      setRecycleSettings(prev =>
        prev.map(setting =>
          setting.platform === platform ? { ...setting, ...updates } : setting
        )
      );
    } catch (error) {
      console.error("Failed to update settings:", error);
    }
  };

  // Sort and filter content
  const sortedAndFilteredContent = recyclableContent
    .filter(content => filterPlatform === "all" || content.platform === filterPlatform)
    .sort((a, b) => {
      switch (sortBy) {
        case "engagement_rate":
          return b.performance.engagement_rate - a.performance.engagement_rate;
        case "viral_score":
          return b.performance.viral_score - a.performance.viral_score;
        case "likes":
          return b.performance.likes - a.performance.likes;
        default:
          return 0;
      }
    });

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <RefreshCw size={20} className="text-warroom-accent" />
          <div>
            <h2 className="text-lg font-bold">Content Recycling</h2>
            <p className="text-[11px] text-warroom-muted -mt-0.5">
              Recycle high-performing content to maximize reach
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warroom-surface border border-warroom-border text-sm hover:border-warroom-accent/30 transition"
          >
            <Settings size={14} />
            Auto-Recycle Settings
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: "RECYCLABLE POSTS", value: recyclableContent.length.toString(), color: "text-warroom-accent" },
            { label: "AVG ENGAGEMENT", value: `${(recyclableContent.reduce((acc, c) => acc + c.performance.engagement_rate, 0) / recyclableContent.length || 0).toFixed(1)}%`, color: "text-green-400" },
            { label: "AUTO-ENABLED", value: recycleSettings.filter(s => s.auto_recycle_enabled).length.toString(), color: "text-blue-400" },
            { label: "TOTAL RECYCLES", value: recyclableContent.reduce((acc, c) => acc + c.recycle_count, 0).toString(), color: "text-purple-400" },
          ].map((stat, i) => (
            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
              <p className="text-[10px] text-warroom-muted tracking-wider mt-1">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm"
            >
              <option value="engagement_rate">Engagement Rate</option>
              <option value="viral_score">Viral Score</option>
              <option value="likes">Likes</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Platform:</span>
            <select
              value={filterPlatform}
              onChange={(e) => setFilterPlatform(e.target.value)}
              className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm"
            >
              <option value="all">All Platforms</option>
              {Object.entries(PLATFORM_CONFIG).map(([key, config]) => (
                <option key={key} value={key}>{config.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedAndFilteredContent.map((content) => {
            const config = PLATFORM_CONFIG[content.platform as keyof typeof PLATFORM_CONFIG];
            const Icon = config.icon;
            const daysSincePost = Math.floor((Date.now() - new Date(content.original_post_date).getTime()) / (1000 * 60 * 60 * 24));
            const canRecycle = daysSincePost >= content.optimal_cadence_days;

            return (
              <div
                key={content.id}
                className="bg-warroom-surface border border-warroom-border rounded-lg p-4 hover:border-warroom-accent/30 transition"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Icon size={16} style={{ color: config.color }} />
                    <span className="text-xs text-warroom-muted">{content.account_username}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`flex items-center gap-1 text-xs ${getViralScoreColor(content.performance.viral_score)}`}>
                      <Zap size={12} />
                      {content.performance.viral_score}
                    </div>
                    {content.recycle_count > 0 && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-warroom-accent/20 text-warroom-accent">
                        {content.recycle_count}x recycled
                      </span>
                    )}
                  </div>
                </div>

                {/* Content Preview */}
                <p className="text-sm line-clamp-3 mb-3">{content.content}</p>

                {/* Performance Metrics */}
                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="flex items-center gap-1 text-xs text-warroom-muted">
                    <Heart size={12} />
                    {formatNumber(content.performance.likes)}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-warroom-muted">
                    <MessageSquare size={12} />
                    {formatNumber(content.performance.comments)}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-warroom-muted">
                    <Share2 size={12} />
                    {formatNumber(content.performance.shares)}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-warroom-muted">
                    <Target size={12} />
                    {content.performance.engagement_rate}% ER
                  </div>
                </div>

                {/* Original Post Date */}
                <div className="flex items-center gap-1 text-xs text-warroom-muted mb-4">
                  <Clock size={12} />
                  Original: {formatDate(content.original_post_date)}
                </div>

                {/* Action Button */}
                <button
                  onClick={() => handleRecyclePost(content.id)}
                  disabled={!canRecycle}
                  className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition ${
                    canRecycle
                      ? "bg-warroom-accent text-white hover:bg-warroom-accent/80"
                      : "bg-warroom-bg text-warroom-muted cursor-not-allowed"
                  }`}
                  title={canRecycle ? "Ready to recycle" : `Ready in ${content.optimal_cadence_days - daysSincePost} days`}
                >
                  <RefreshCw size={14} />
                  {canRecycle ? "Recycle Now" : `${content.optimal_cadence_days - daysSincePost} days left`}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center" onClick={() => setShowSettings(false)}>
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">Auto-Recycle Settings</h3>
            <div className="flex-1 overflow-y-auto space-y-4">
              {recycleSettings.map((setting) => {
                const config = PLATFORM_CONFIG[setting.platform as keyof typeof PLATFORM_CONFIG];
                const Icon = config.icon;
                return (
                  <div key={setting.platform} className="p-4 bg-warroom-bg border border-warroom-border rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <Icon size={16} style={{ color: config.color }} />
                      <span className="font-medium">{config.name}</span>
                      <span className="text-sm text-warroom-muted">({setting.account_username})</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={setting.auto_recycle_enabled}
                            onChange={(e) => updateSettings(setting.platform, { auto_recycle_enabled: e.target.checked })}
                            className="rounded"
                          />
                          Enable Auto-Recycling
                        </label>
                      </div>
                      <div>
                        <label className="text-xs text-warroom-muted block mb-1">Cadence (days)</label>
                        <input
                          type="number"
                          value={setting.cadence_days}
                          onChange={(e) => updateSettings(setting.platform, { cadence_days: Number(e.target.value) })}
                          className="w-full bg-warroom-surface border border-warroom-border rounded px-2 py-1 text-sm"
                          min="7"
                          max="365"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-warroom-muted block mb-1">Min Engagement Rate (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={setting.min_engagement_rate}
                          onChange={(e) => updateSettings(setting.platform, { min_engagement_rate: Number(e.target.value) })}
                          className="w-full bg-warroom-surface border border-warroom-border rounded px-2 py-1 text-sm"
                          min="0"
                          max="20"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-warroom-muted block mb-1">Max Recycles</label>
                        <input
                          type="number"
                          value={setting.max_recycles_per_post}
                          onChange={(e) => updateSettings(setting.platform, { max_recycles_per_post: Number(e.target.value) })}
                          className="w-full bg-warroom-surface border border-warroom-border rounded px-2 py-1 text-sm"
                          min="1"
                          max="10"
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-warroom-border">
              <button 
                onClick={() => setShowSettings(false)}
                className="px-4 py-2 text-sm rounded-lg text-warroom-muted hover:text-warroom-text transition"
              >
                Cancel
              </button>
              <button 
                onClick={() => setShowSettings(false)}
                className="px-4 py-2 text-sm rounded-lg bg-warroom-accent text-white hover:bg-warroom-accent/80 transition"
              >
                Save Settings
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}