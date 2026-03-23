"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Instagram, Settings, Calendar, BarChart3, RefreshCw, 
  Eye, Heart, MessageSquare, Share2, Play, Plus, 
  Clock3, Target, Zap, Bot
} from "lucide-react";
import { authFetch, API } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";
import { useSocialAccounts, PLATFORM_CONFIGS } from "@/hooks/useSocialAccounts";
import AutoReplyPanel from "@/components/auto-reply/AutoReplyPanel";

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

export default function InstagramPage() {
  const socialAccounts = useSocialAccounts();
  const [activeTab, setActiveTab] = useState<"feed" | "scheduled" | "published" | "auto-reply" | "recycle" | "analytics">("feed");
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [publishedPosts, setPublishedPosts] = useState<PublishedPost[]>([]);
  const [loading, setLoading] = useState(false);

  const instagramAccount = socialAccounts.getAccount('instagram');
  
  // Mock data for demo - replace with actual API calls
  const loadData = useCallback(async () => {
    if (!instagramAccount) return;
    
    setLoading(true);
    try {
      // Mock data for development
      setScheduledPosts(Array.from({ length: 5 }, (_, i) => ({
        id: `scheduled_${i}`,
        content: `Scheduled Instagram post ${i + 1}. This is sample content that will be posted soon.`,
        scheduled_for: new Date(Date.now() + (i * 24 * 60 * 60 * 1000)).toISOString(),
        status: "scheduled",
        media_url: i % 2 === 0 ? "/sample-image.jpg" : undefined
      })));

      setPublishedPosts(Array.from({ length: 10 }, (_, i) => ({
        id: `published_${i}`,
        content: `Published Instagram post ${i + 1}. This is sample content that was already posted.`,
        published_at: new Date(Date.now() - (i * 12 * 60 * 60 * 1000)).toISOString(),
        performance: {
          views: Math.floor(Math.random() * 10000) + 100,
          likes: Math.floor(Math.random() * 1000) + 10,
          comments: Math.floor(Math.random() * 100) + 1,
          shares: Math.floor(Math.random() * 50) + 1,
          saves: Math.floor(Math.random() * 200) + 5,
          engagement_rate: parseFloat((Math.random() * 10 + 1).toFixed(2))
        }
      })));
    } catch (error) {
      console.error("Failed to load Instagram data:", error);
    } finally {
      setLoading(false);
    }
  }, [instagramAccount]);

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

  if (socialAccounts.loading) {
    return <LoadingState message="Loading Instagram connection..." />;
  }

  // If not connected, show connection prompt
  if (!instagramAccount) {
    return (
      <div className="h-full flex flex-col">
        <div className="h-14 border-b border-warroom-border flex items-center px-6">
          <Instagram size={20} className="text-pink-400 mr-3" />
          <h2 className="text-lg font-bold">Instagram</h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <Instagram size={64} className="mx-auto text-pink-400 mb-6" />
            <h3 className="text-xl font-bold mb-3">Connect Your Instagram Account</h3>
            <p className="text-warroom-muted mb-6">
              Connect your Instagram Business account to manage posts, schedule content, 
              set up auto-replies, and track performance.
            </p>
            <button
              onClick={() => socialAccounts.connect('instagram')}
              className="px-6 py-3 bg-pink-500 hover:bg-pink-600 text-white font-medium rounded-lg transition"
            >
              Connect Instagram Account
            </button>
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { key: "feed", label: "Feed", icon: Instagram },
    { key: "scheduled", label: "Scheduled", icon: Calendar },
    { key: "published", label: "Published", icon: Play },
    { key: "auto-reply", label: "Auto-Reply", icon: Zap },
    { key: "recycle", label: "Recycle", icon: RefreshCw },
    { key: "analytics", label: "Analytics", icon: BarChart3 },
  ] as const;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Instagram size={20} className="text-pink-400" />
          <div>
            <h2 className="text-lg font-bold">Instagram</h2>
            <p className="text-[11px] text-warroom-muted -mt-0.5">
              @{instagramAccount.username} • {formatNumber(instagramAccount.follower_count)} followers
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => socialAccounts.disconnect('instagram')}
            className="text-xs px-3 py-1.5 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-muted hover:text-warroom-text transition"
          >
            Disconnect
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-pink-500 text-white text-sm font-medium hover:bg-pink-600 transition">
            <Plus size={14} />
            New Post
          </button>
        </div>
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
                    ? "border-b-2 border-pink-400 text-pink-400"
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
      <div className="flex-1 overflow-y-auto">
        {activeTab === "feed" && (
          <div className="p-6 space-y-6">
            {/* Account Stats */}
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "Followers", value: formatNumber(instagramAccount.follower_count), color: "text-pink-400" },
                { label: "Following", value: formatNumber(instagramAccount.following_count), color: "text-blue-400" },
                { label: "Scheduled", value: scheduledPosts.length.toString(), color: "text-orange-400" },
                { label: "Published", value: publishedPosts.length.toString(), color: "text-green-400" }
              ].map((stat, i) => (
                <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                  <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                  <p className="text-[10px] text-warroom-muted tracking-wider mt-1">{stat.label.toUpperCase()}</p>
                </div>
              ))}
            </div>

            {/* Recent Posts Grid */}
            <div>
              <h3 className="text-sm font-bold mb-4">Recent Posts</h3>
              <div className="grid grid-cols-3 gap-4">
                {publishedPosts.slice(0, 9).map((post) => (
                  <div
                    key={post.id}
                    className="bg-warroom-surface border border-warroom-border rounded-lg p-4 hover:border-pink-400/30 transition"
                  >
                    <div className="aspect-square bg-warroom-bg rounded-lg mb-3 flex items-center justify-center">
                      <Instagram size={24} className="text-warroom-muted" />
                    </div>
                    <p className="text-sm line-clamp-3 mb-3">{post.content}</p>
                    <div className="flex items-center gap-4 text-xs text-warroom-muted">
                      <span className="flex items-center gap-1">
                        <Eye size={12} />
                        {formatNumber(post.performance.views)}
                      </span>
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

            {/* Quick Actions removed - functionality available through main nav (Scheduler, Auto-Reply) */}
          </div>
        )}

        {activeTab === "scheduled" && (
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold">Scheduled Posts</h3>
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-pink-500 text-white text-sm font-medium">
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
          <div className="p-6 space-y-4">
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
                    <span className="flex items-center gap-1">
                      <Eye size={12} />
                      {formatNumber(post.performance.views)}
                    </span>
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
                    <button 
                      onClick={() => setActiveTab("recycle")}
                      className="text-xs px-2 py-1 rounded bg-warroom-bg hover:bg-warroom-border transition"
                    >
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

        {activeTab === "auto-reply" && (
          <div className="h-full">
            <AutoReplyPanel />
          </div>
        )}

        {activeTab === "recycle" && (
          <div className="p-6">
            <div className="text-center py-12">
              <RefreshCw size={48} className="mx-auto text-warroom-muted mb-4" />
              <h3 className="text-lg font-bold mb-2">Recycle High-Performing Content</h3>
              <p className="text-sm text-warroom-muted mb-6 max-w-md mx-auto">
                Automatically identify your top-performing Instagram posts and schedule them to be reposted
                at optimal times to maximize reach and engagement.
              </p>
              <button className="px-4 py-2 rounded-lg bg-pink-500 text-white font-medium hover:bg-pink-600 transition">
                Enable Auto-Recycling
              </button>
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="p-6">
            <div className="text-center py-12">
              <BarChart3 size={48} className="mx-auto text-warroom-muted mb-4" />
              <h3 className="text-lg font-bold mb-2">Instagram Analytics</h3>
              <p className="text-sm text-warroom-muted mb-6 max-w-md mx-auto">
                Detailed Instagram analytics dashboard coming soon. Track engagement trends, 
                optimal posting times, and audience insights.
              </p>
              <button className="px-4 py-2 rounded-lg bg-pink-500 text-white font-medium hover:bg-pink-600 transition">
                Request Beta Access
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}