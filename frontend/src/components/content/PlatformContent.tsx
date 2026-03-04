"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Sparkles, Plus, Search, Instagram, Youtube, RefreshCw,
  ChevronRight, Eye, Heart, MessageSquare, ExternalLink, Film, Image as ImageIcon, Grid3X3,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface MediaItem {
  id: string;
  caption: string;
  type: string;
  url: string;
  thumbnail: string;
  permalink: string;
  timestamp: string;
  likes: number;
  comments: number;
}

interface YouTubeVideo {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  published: string;
  views: number;
  likes: number;
  comments: number;
  url: string;
}

interface Profile {
  username: string;
  followers: number;
  following: number;
  posts: number;
  account_type?: string;
}

interface YouTubeChannel {
  title: string;
  subscribers: number;
  views: number;
  videos: number;
  thumbnail: string;
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const days = Math.floor(diff / 86400000);
  if (days < 1) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

const PLATFORM_CONFIG: Record<string, { name: string; icon: any; color: string; gradient: string }> = {
  instagram: { name: "Instagram", icon: Instagram, color: "#E4405F", gradient: "from-pink-500 to-purple-600" },
  youtube: { name: "YouTube", icon: Youtube, color: "#FF0000", gradient: "from-red-500 to-red-700" },
};

interface PlatformContentProps {
  platform: "instagram" | "youtube";
}

export default function PlatformContent({ platform }: PlatformContentProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  // Instagram state
  const [igProfile, setIgProfile] = useState<Profile | null>(null);
  const [igMedia, setIgMedia] = useState<MediaItem[]>([]);

  // YouTube state
  const [ytChannel, setYtChannel] = useState<YouTubeChannel | null>(null);
  const [ytVideos, setYtVideos] = useState<YouTubeVideo[]>([]);

  const [search, setSearch] = useState("");
  const [view, setView] = useState<"grid" | "list">("grid");

  const config = PLATFORM_CONFIG[platform];
  const Icon = config.icon;

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (platform === "instagram") {
        const resp = await fetch(`${API}/api/social/content/instagram/media?limit=50`);
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || "Failed to fetch Instagram data");
        }
        const data = await resp.json();
        setIgProfile(data.profile);
        setIgMedia(data.media || []);
      } else if (platform === "youtube") {
        const resp = await fetch(`${API}/api/social/content/youtube/videos?limit=50`);
        if (!resp.ok) throw new Error("Failed to fetch YouTube data");
        const data = await resp.json();
        setYtChannel(data.channel);
        setYtVideos(data.videos || []);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [platform]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  // Compute stats
  const totalPosts = platform === "instagram" ? igMedia.length : ytVideos.length;
  const totalLikes = platform === "instagram"
    ? igMedia.reduce((s, m) => s + m.likes, 0)
    : ytVideos.reduce((s, v) => s + v.likes, 0);
  const totalComments = platform === "instagram"
    ? igMedia.reduce((s, m) => s + m.comments, 0)
    : ytVideos.reduce((s, v) => s + v.comments, 0);
  const totalViews = platform === "youtube"
    ? ytVideos.reduce((s, v) => s + v.views, 0) : 0;
  const followers = platform === "instagram"
    ? (igProfile?.followers || 0)
    : (ytChannel?.subscribers || 0);
  const avgEngagement = totalPosts > 0
    ? ((totalLikes + totalComments) / totalPosts / Math.max(followers, 1) * 100)
    : 0;

  // Filter
  const filteredIG = igMedia.filter(m =>
    !search || m.caption.toLowerCase().includes(search.toLowerCase())
  );
  const filteredYT = ytVideos.filter(v =>
    !search || v.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-16 border-b border-warroom-border flex items-center justify-between px-8 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Icon size={22} style={{ color: config.color }} />
          <div>
            <h2 className="text-lg font-bold">{config.name}</h2>
            <p className="text-xs text-warroom-muted -mt-0.5">
              {platform === "instagram" ? `@${igProfile?.username || "..."}` : ytChannel?.title || "Loading..."}
              {" · "}{followers > 0 ? formatNum(followers) + " followers" : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleRefresh} disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-surface border border-warroom-border text-xs hover:border-warroom-accent/30 transition disabled:opacity-50">
            <RefreshCw size={14} className={`text-warroom-accent ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-warroom-accent border-t-transparent" />
        </div>
      ) : error ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-400 mb-2">{error}</p>
            <button onClick={fetchData} className="text-sm text-warroom-accent hover:underline">Try again</button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-8 space-y-8">
          {/* Stats Row */}
          <div className="grid grid-cols-5 gap-5">
            {[
              { label: "FOLLOWERS", value: formatNum(followers), color: "text-blue-400" },
              { label: "POSTS", value: formatNum(totalPosts), color: "text-warroom-accent" },
              { label: "TOTAL LIKES", value: formatNum(totalLikes), color: "text-pink-400" },
              { label: "TOTAL COMMENTS", value: formatNum(totalComments), color: "text-orange-400" },
              ...(platform === "youtube"
                ? [{ label: "TOTAL VIEWS", value: formatNum(totalViews), color: "text-purple-400" }]
                : [{ label: "AVG ENGAGEMENT", value: `${avgEngagement.toFixed(1)}%`, color: "text-green-400" }]),
            ].map((s, i) => (
              <div key={i} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-warroom-muted tracking-wider mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Search + View Toggle */}
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder={`Search ${platform === "instagram" ? "captions" : "video titles"}...`}
                className="w-full bg-warroom-surface border border-warroom-border rounded-lg pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:border-warroom-accent/30" />
            </div>
            <div className="flex rounded-lg border border-warroom-border overflow-hidden">
              <button onClick={() => setView("grid")}
                className={`px-3 py-2 ${view === "grid" ? "bg-warroom-accent/15 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text"}`}>
                <Grid3X3 size={16} />
              </button>
              <button onClick={() => setView("list")}
                className={`px-3 py-2 ${view === "list" ? "bg-warroom-accent/15 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text"}`}>
                <Film size={16} />
              </button>
            </div>
          </div>

          {/* Content Grid/List */}
          {platform === "instagram" && (
            view === "grid" ? (
              <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {filteredIG.map(m => (
                  <a key={m.id} href={m.permalink} target="_blank" rel="noopener noreferrer"
                    className="group relative aspect-square rounded-xl overflow-hidden border border-warroom-border hover:border-warroom-accent/30 transition bg-warroom-surface">
                    {m.thumbnail || m.url ? (
                      <img src={m.thumbnail || m.url} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        {m.type === "VIDEO" ? <Film size={24} className="text-warroom-muted/30" /> : <ImageIcon size={24} className="text-warroom-muted/30" />}
                      </div>
                    )}
                    {/* Overlay on hover */}
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
                      <span className="flex items-center gap-1 text-white text-sm font-semibold">
                        <Heart size={16} fill="white" /> {formatNum(m.likes)}
                      </span>
                      <span className="flex items-center gap-1 text-white text-sm font-semibold">
                        <MessageSquare size={16} fill="white" /> {formatNum(m.comments)}
                      </span>
                    </div>
                    {m.type === "VIDEO" && (
                      <div className="absolute top-2 right-2 bg-black/50 rounded px-1.5 py-0.5">
                        <Film size={12} className="text-white" />
                      </div>
                    )}
                  </a>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredIG.map(m => (
                  <a key={m.id} href={m.permalink} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-4 bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition">
                    <div className="w-20 h-20 rounded-lg overflow-hidden flex-shrink-0 bg-warroom-bg">
                      {m.thumbnail || m.url ? (
                        <img src={m.thumbnail || m.url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Film size={16} className="text-warroom-muted/30" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium line-clamp-2">{m.caption || "(no caption)"}</p>
                      <div className="flex items-center gap-4 mt-2">
                        <span className="flex items-center gap-1 text-xs text-warroom-muted"><Heart size={12} /> {formatNum(m.likes)}</span>
                        <span className="flex items-center gap-1 text-xs text-warroom-muted"><MessageSquare size={12} /> {m.comments}</span>
                        <span className="text-xs text-warroom-muted">{timeAgo(m.timestamp)}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-warroom-accent/10 text-warroom-accent">{m.type}</span>
                      </div>
                    </div>
                    <ExternalLink size={14} className="text-warroom-muted flex-shrink-0" />
                  </a>
                ))}
              </div>
            )
          )}

          {platform === "youtube" && (
            ytVideos.length === 0 ? (
              <div className="text-center py-16">
                <Youtube size={48} className="text-warroom-muted/20 mx-auto mb-4" />
                <p className="text-warroom-muted">No videos found on this channel</p>
                <p className="text-xs text-warroom-muted/60 mt-1">Upload videos to YouTube and they&apos;ll appear here</p>
              </div>
            ) : (
              <div className={view === "grid" ? "grid grid-cols-2 lg:grid-cols-3 gap-4" : "space-y-3"}>
                {filteredYT.map(v => (
                  view === "grid" ? (
                    <a key={v.id} href={v.url} target="_blank" rel="noopener noreferrer"
                      className="group bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden hover:border-warroom-accent/20 transition">
                      <div className="aspect-video relative">
                        {v.thumbnail ? (
                          <img src={v.thumbnail} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full bg-warroom-bg flex items-center justify-center">
                            <Film size={24} className="text-warroom-muted/30" />
                          </div>
                        )}
                        <div className="absolute bottom-2 right-2 bg-black/70 rounded px-2 py-0.5 text-xs text-white">
                          {formatNum(v.views)} views
                        </div>
                      </div>
                      <div className="p-4">
                        <p className="text-sm font-semibold line-clamp-2 mb-2">{v.title}</p>
                        <div className="flex items-center gap-3 text-xs text-warroom-muted">
                          <span className="flex items-center gap-1"><Eye size={12} /> {formatNum(v.views)}</span>
                          <span className="flex items-center gap-1"><Heart size={12} /> {formatNum(v.likes)}</span>
                          <span className="flex items-center gap-1"><MessageSquare size={12} /> {v.comments}</span>
                          <span className="ml-auto">{timeAgo(v.published)}</span>
                        </div>
                      </div>
                    </a>
                  ) : (
                    <a key={v.id} href={v.url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-4 bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition">
                      <div className="w-40 h-24 rounded-lg overflow-hidden flex-shrink-0 bg-warroom-bg">
                        {v.thumbnail ? <img src={v.thumbnail} alt="" className="w-full h-full object-cover" /> : null}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold line-clamp-2">{v.title}</p>
                        <div className="flex items-center gap-4 mt-2">
                          <span className="flex items-center gap-1 text-xs text-warroom-muted"><Eye size={12} /> {formatNum(v.views)}</span>
                          <span className="flex items-center gap-1 text-xs text-warroom-muted"><Heart size={12} /> {formatNum(v.likes)}</span>
                          <span className="flex items-center gap-1 text-xs text-warroom-muted"><MessageSquare size={12} /> {v.comments}</span>
                          <span className="text-xs text-warroom-muted">{timeAgo(v.published)}</span>
                        </div>
                      </div>
                      <ExternalLink size={14} className="text-warroom-muted flex-shrink-0" />
                    </a>
                  )
                ))}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
