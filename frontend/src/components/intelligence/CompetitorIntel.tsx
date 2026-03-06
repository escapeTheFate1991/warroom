"use client";

import { useState, useEffect } from "react";
import { Search, Plus, X, Flame, Copy, Check, User, TrendingUp, Eye, Target, Zap, BookOpen, ExternalLink, Trash2, Loader2, RefreshCw, Play, Save, Edit3, ArrowLeft, Heart, MessageCircle, EyeIcon, BarChart3, Hash, Users, Sparkles } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Competitor {
  id: number;
  handle: string;
  platform: string;
  followers: number;
  following: number;
  post_count: number;
  bio?: string;
  profile_image_url?: string;
  posting_frequency?: string;
  avg_engagement_rate: number;
  top_angles?: string;
  signature_formula?: string;
  notes?: string;
  is_auto_populated: boolean;
  last_auto_sync?: string;
  auto_sync_enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface CompetitorPost {
  text: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  timestamp: string;
  url?: string;
  hook?: string;
}

interface TopContentPost {
  text: string;
  hook: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  platform: string;
  competitor_handle: string;
  timestamp: string;
  url?: string;
}

interface Hook {
  hook: string;
  engagement_score: number;
  platform: string;
  competitor_handle: string;
  source_url?: string;
}

interface Script {
  id: number;
  title: string;
  content: string;
  platform: string;
  hook_preview?: string;
  competitor_id?: number;
  created_at: string;
}

interface TopVideoItem {
  post_url?: string;
  title: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  posted_at?: string;
  hook?: string;
}

interface FollowerAnalysis {
  themes: string[];
  audience_type: string;
  engagement_style: string;
  key_interests: string[];
}

interface HashtagItem {
  tag: string;
  count: number;
}

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "bg-pink-500/20 text-pink-400",
  tiktok: "bg-cyan-500/20 text-cyan-400",
  youtube: "bg-red-500/20 text-red-400",
  x: "bg-gray-600/20 text-gray-300",
  facebook: "bg-blue-500/20 text-blue-400",
  threads: "bg-gray-500/20 text-gray-400",
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

export default function CompetitorIntel() {
  const [activeTab, setActiveTab] = useState<"competitors" | "top-content" | "hooks" | "scripts">("competitors");
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [topContent, setTopContent] = useState<TopContentPost[]>([]);
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [expandedCompetitor, setExpandedCompetitor] = useState<number | null>(null);
  const [focusedCompetitor, setFocusedCompetitor] = useState<Competitor | null>(null);
  const [competitorPosts, setCompetitorPosts] = useState<CompetitorPost[]>([]);
  
  const [showAddCompetitor, setShowAddCompetitor] = useState(false);
  const [showGenerateScript, setShowGenerateScript] = useState(false);
  const [copiedHook, setCopiedHook] = useState<number | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState<number | null>(null);
  const [loadingPosts, setLoadingPosts] = useState(false);
  
  const [newComp, setNewComp] = useState({ handle: "", platform: "instagram" });
  const [scriptForm, setScriptForm] = useState({
    competitor_id: 0,
    platform: "instagram",
    topic: "",
    hook_style: ""
  });
  
  const [error, setError] = useState<string>("");

  // New state for upgraded Reports features
  const [followerAnalysis, setFollowerAnalysis] = useState<FollowerAnalysis | null>(null);
  const [loadingFollowerAnalysis, setLoadingFollowerAnalysis] = useState(false);
  const [topVideos, setTopVideos] = useState<TopVideoItem[]>([]);
  const [loadingTopVideos, setLoadingTopVideos] = useState(false);
  const [hashtags, setHashtags] = useState<HashtagItem[]>([]);
  const [loadingHashtags, setLoadingHashtags] = useState(false);

  // Fetch competitors
  const fetchCompetitors = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API}/api/competitors`);
      if (response.ok) {
        const data = await response.json();
        setCompetitors(data);
      } else {
        setError("Failed to fetch competitors");
      }
    } catch (error) {
      setError("Error connecting to API");
    } finally {
      setLoading(false);
    }
  };

  // Fetch top content
  const fetchTopContent = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API}/api/content-intel/competitors/top-content`);
      if (response.ok) {
        const data = await response.json();
        const posts = Array.isArray(data) ? data : (data.posts || []);
        setTopContent(posts.sort((a: any, b: any) => b.engagement_score - a.engagement_score));
      } else if (response.status === 404) {
        setTopContent([]);
        setError("No content data available. Refresh competitor data first.");
      } else {
        setError("Failed to fetch top content");
      }
    } catch (error) {
      setError("Error connecting to API");
    } finally {
      setLoading(false);
    }
  };

  // Fetch hooks
  const fetchHooks = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API}/api/content-intel/competitors/hooks`);
      if (response.ok) {
        const data = await response.json();
        setHooks(Array.isArray(data) ? data : (data.hooks || []));
      } else if (response.status === 404) {
        setHooks([]);
        setError("No hooks available. Refresh competitor data first.");
      } else {
        setError("Failed to fetch hooks");
      }
    } catch (error) {
      setError("Error connecting to API");
    } finally {
      setLoading(false);
    }
  };

  // Fetch scripts
  const fetchScripts = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API}/api/content-intel/competitors/scripts`);
      if (response.ok) {
        const data = await response.json();
        setScripts(data);
      } else {
        setError("Failed to fetch scripts");
      }
    } catch (error) {
      setError("Error connecting to API");
    } finally {
      setLoading(false);
    }
  };

  // Fetch competitor posts
  const fetchCompetitorPosts = async (competitorId: number) => {
    try {
      setLoadingPosts(true);
      const response = await fetch(`${API}/api/content-intel/competitors/${competitorId}/content`);
      if (response.ok) {
        const data = await response.json();
        // API returns { posts: [...] }, extract the array
        setCompetitorPosts(Array.isArray(data) ? data : (data.posts || []));
      } else {
        setCompetitorPosts([]);
      }
    } catch (error) {
      setCompetitorPosts([]);
    } finally {
      setLoadingPosts(false);
    }
  };

  // Fetch follower analysis summary
  const fetchFollowerAnalysis = async () => {
    try {
      setLoadingFollowerAnalysis(true);
      const response = await fetch(`${API}/api/content-intel/competitors/follower-analysis`);
      if (response.ok) {
        setFollowerAnalysis(await response.json());
      }
    } catch (err) {
      console.error("Failed to fetch follower analysis", err);
    } finally {
      setLoadingFollowerAnalysis(false);
    }
  };

  // Fetch top videos for a competitor
  const fetchTopVideos = async (competitorId: number) => {
    try {
      setLoadingTopVideos(true);
      const response = await fetch(`${API}/api/content-intel/competitors/${competitorId}/top-videos?limit=5`);
      if (response.ok) {
        setTopVideos(await response.json());
      } else {
        setTopVideos([]);
      }
    } catch (err) {
      setTopVideos([]);
    } finally {
      setLoadingTopVideos(false);
    }
  };

  // Fetch hashtags for a competitor
  const fetchHashtags = async (competitorId: number) => {
    try {
      setLoadingHashtags(true);
      const response = await fetch(`${API}/api/content-intel/competitors/${competitorId}/hashtags`);
      if (response.ok) {
        setHashtags(await response.json());
      } else {
        setHashtags([]);
      }
    } catch (err) {
      setHashtags([]);
    } finally {
      setLoadingHashtags(false);
    }
  };

  // Load data based on active tab
  // Fetch all counts on mount so tab badges are accurate
  useEffect(() => {
    fetchCompetitors();
    fetchFollowerAnalysis();
    fetchTopContent();
    fetchHooks();
    fetchScripts();
  }, []);

  // Fetch active tab data on tab change
  useEffect(() => {
    switch (activeTab) {
      case "competitors":
        fetchCompetitors();
        fetchFollowerAnalysis();
        break;
      case "top-content":
        fetchTopContent();
        break;
      case "hooks":
        fetchHooks();
        break;
      case "scripts":
        fetchScripts();
        break;
    }
  }, [activeTab]);

  // Add competitor
  const addCompetitor = async () => {
    if (!newComp.handle.trim()) return;
    
    try {
      setSubmitting(true);
      setError("");
      
      // Create competitor
      const createResponse = await fetch(`${API}/api/competitors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          handle: newComp.handle.trim().replace('@', ''),
          platform: newComp.platform,
        }),
      });

      if (createResponse.ok) {
        const newCompetitor = await createResponse.json();
        
        // Auto-populate data
        try {
          await fetch(`${API}/api/competitors/${newCompetitor.id}/auto-populate`, {
            method: "POST",
          });
        } catch (error) {
          console.warn("Auto-populate failed, but competitor was created");
        }
        
        setCompetitors(prev => [newCompetitor, ...prev]);
        setNewComp({ handle: "", platform: "instagram" });
        setShowAddCompetitor(false);
        fetchCompetitors(); // Refresh to get updated data
      } else {
        const error = await createResponse.json();
        setError(`Failed to add competitor: ${error.detail || createResponse.statusText}`);
      }
    } catch (error) {
      setError(`Error adding competitor: ${error}`);
    } finally {
      setSubmitting(false);
    }
  };

  // Delete competitor
  const deleteCompetitor = async (id: number) => {
    try {
      const response = await fetch(`${API}/api/competitors/${id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setCompetitors(prev => prev.filter(c => c.id !== id));
      } else {
        setError("Failed to delete competitor");
      }
    } catch (error) {
      setError(`Error deleting competitor: ${error}`);
    }
  };

  // Refresh all competitors via our own scraper (Playwright, no third-party services)
  const refreshAllCompetitors = async () => {
    try {
      setLoading(true);
      setError("");
      // Use our scraper sync endpoint — scrapes all IG competitors via headless browser
      const response = await fetch(`${API}/api/scraper/instagram/sync`, {
        method: "POST",
      });

      if (response.ok) {
        const result = await response.json();
        const msg = `Scraped ${result.success}/${result.total} competitors, ${result.posts_saved} posts cached`;
        console.log(msg);
        fetchCompetitors(); // Refresh UI with new data
      } else {
        const errData = await response.json().catch(() => ({}));
        setError(`Scraper sync failed: ${errData.detail || response.statusText}`);
      }
    } catch (error) {
      setError(`Error running scraper: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Generate script
  const generateScript = async () => {
    if (!scriptForm.competitor_id || !scriptForm.topic.trim()) return;
    
    try {
      setSubmitting(true);
      setError("");
      const response = await fetch(`${API}/api/content-intel/competitors/${scriptForm.competitor_id}/generate-script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform: scriptForm.platform,
          topic: scriptForm.topic,
          hook_style: scriptForm.hook_style || undefined,
        }),
      });

      if (response.ok) {
        const newScript = await response.json();
        setScripts(prev => [newScript, ...prev]);
        setScriptForm({ competitor_id: 0, platform: "instagram", topic: "", hook_style: "" });
        setShowGenerateScript(false);
      } else {
        const error = await response.json();
        setError(`Failed to generate script: ${error.detail || response.statusText}`);
      }
    } catch (error) {
      setError(`Error generating script: ${error}`);
    } finally {
      setSubmitting(false);
    }
  };

  // Delete script
  const deleteScript = async (id: number) => {
    try {
      const response = await fetch(`${API}/api/content-intel/competitors/scripts/${id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setScripts(prev => prev.filter(s => s.id !== id));
      } else {
        setError("Failed to delete script");
      }
    } catch (error) {
      setError(`Error deleting script: ${error}`);
    }
  };

  // Save script to platform
  const saveScriptToPlatform = (script: Script, platform: string) => {
    const key = `warroom_content_${platform}`;
    const existing = JSON.parse(localStorage.getItem(key) || "[]");
    existing.push({
      id: Date.now(),
      title: script.title,
      content: script.content,
      created_at: new Date().toISOString(),
      source: "competitor_intel"
    });
    localStorage.setItem(key, JSON.stringify(existing));
    // Could show a toast notification here
  };

  // Copy hook
  const copyHook = (hookText: string, idx: number) => {
    navigator.clipboard.writeText(hookText);
    setCopiedHook(idx);
    setTimeout(() => setCopiedHook(null), 2000);
  };

  // Focus on a competitor — switches from grid to detail view
  const focusOnCompetitor = (comp: Competitor) => {
    setFocusedCompetitor(comp);
    setCompetitorPosts([]);
    setTopVideos([]);
    setHashtags([]);
    fetchCompetitorPosts(comp.id);
    fetchTopVideos(comp.id);
    fetchHashtags(comp.id);
  };

  // Back to grid
  const unfocusCompetitor = () => {
    setFocusedCompetitor(null);
    setCompetitorPosts([]);
    setTopVideos([]);
    setHashtags([]);
  };

  const TABS = [
    { id: "competitors" as const, label: "Competitors", icon: Target, count: competitors.length },
    { id: "top-content" as const, label: "Top Content", icon: TrendingUp, count: topContent.length },
    { id: "hooks" as const, label: "Hooks", icon: Zap, count: hooks.length },
    { id: "scripts" as const, label: "Scripts", icon: BookOpen, count: scripts.length },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Eye size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Competitor Intelligence</h2>
      </div>

      {/* Sub-tabs */}
      <div className="border-b border-warroom-border bg-warroom-surface flex-shrink-0">
        <div className="flex">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab.id
                  ? "text-warroom-accent border-warroom-accent bg-warroom-accent/5"
                  : "text-warroom-muted border-transparent hover:text-warroom-text"
              }`}>
              <tab.icon size={16} />
              {tab.label}
              <span className="text-xs bg-warroom-bg px-1.5 py-0.5 rounded-full">{tab.count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mx-6 mt-3 px-3 py-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg">
          {error}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">

          {/* COMPETITORS TAB */}
          {activeTab === "competitors" && (
            <div className="space-y-4">

              {/* ── Follower Analysis Summary ── */}
              {!focusedCompetitor && (
                <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Users size={18} className="text-warroom-accent" />
                    <h3 className="text-sm font-semibold">Audience Intelligence</h3>
                  </div>

                  {loadingFollowerAnalysis ? (
                    <div className="flex items-center gap-2 text-sm text-warroom-muted py-4">
                      <Loader2 size={16} className="animate-spin" /> Analyzing audience…
                    </div>
                  ) : followerAnalysis ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Audience type + engagement style */}
                      <div className="space-y-3">
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-1">Audience Type</p>
                          <p className="text-sm font-medium text-warroom-text">{followerAnalysis.audience_type}</p>
                        </div>
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-1">Engagement Style</p>
                          <p className="text-sm font-medium text-warroom-text">{followerAnalysis.engagement_style}</p>
                        </div>
                        {/* Key interests */}
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-1.5">Key Interests</p>
                          <ul className="space-y-1">
                            {followerAnalysis.key_interests.map((interest, i) => (
                              <li key={i} className="text-xs text-warroom-text flex items-center gap-1.5">
                                <Sparkles size={12} className="text-warroom-accent flex-shrink-0" />
                                {interest}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* Themes as badges */}
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">Content Themes</p>
                        <div className="flex flex-wrap gap-2">
                          {followerAnalysis.themes.map((theme, i) => (
                            <span key={i} className="px-2.5 py-1 bg-warroom-accent/10 text-warroom-accent text-xs rounded-full font-medium">
                              {theme}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted py-2">No audience data yet. Refresh competitor data to generate analysis.</p>
                  )}
                </div>
              )}

              {/* FOCUSED VIEW — single competitor detail */}
              {focusedCompetitor ? (
                <div className="space-y-6">
                  {/* Back button + competitor header */}
                  <div className="flex items-center gap-4">
                    <button onClick={unfocusCompetitor}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-bg border border-warroom-border hover:bg-warroom-surface rounded-lg text-xs font-medium transition">
                      <ArrowLeft size={14} /> Back
                    </button>
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-12 h-12 rounded-full bg-warroom-accent/10 flex items-center justify-center text-xl font-bold text-warroom-accent">
                        {focusedCompetitor.handle.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold">@{focusedCompetitor.handle}</h3>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[focusedCompetitor.platform] || "bg-gray-500/20 text-gray-400"}`}>{focusedCompetitor.platform}</span>
                          {focusedCompetitor.posting_frequency && (
                            <span className="text-xs text-warroom-muted">{focusedCompetitor.posting_frequency}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <a href={`https://instagram.com/${focusedCompetitor.handle}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-pink-500/10 text-pink-400 hover:bg-pink-500/20 rounded-lg text-xs font-medium transition">
                      <ExternalLink size={14} /> View Profile
                    </a>
                  </div>

                  {/* Stats bar */}
                  <div className="grid grid-cols-4 gap-3">
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold text-warroom-text">{formatNum(focusedCompetitor.followers)}</p>
                      <p className="text-xs text-warroom-muted mt-1">Followers</p>
                    </div>
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold text-warroom-text">{formatNum(focusedCompetitor.following)}</p>
                      <p className="text-xs text-warroom-muted mt-1">Following</p>
                    </div>
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold text-warroom-text">{formatNum(focusedCompetitor.post_count)}</p>
                      <p className="text-xs text-warroom-muted mt-1">Total Posts</p>
                    </div>
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold text-warroom-accent">{focusedCompetitor.avg_engagement_rate.toFixed(1)}%</p>
                      <p className="text-xs text-warroom-muted mt-1">Engagement</p>
                    </div>
                  </div>

                  {/* Bio */}
                  {focusedCompetitor.bio && (
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                      <p className="text-sm text-warroom-text whitespace-pre-line">{focusedCompetitor.bio}</p>
                    </div>
                  )}

                  {/* ── Top Videos / Posts ── */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Flame size={16} className="text-orange-400" />
                      <h4 className="text-sm font-semibold">Top Performing Posts</h4>
                    </div>

                    {loadingTopVideos ? (
                      <div className="flex items-center gap-2 text-sm text-warroom-muted py-6">
                        <Loader2 size={16} className="animate-spin" /> Loading top posts…
                      </div>
                    ) : topVideos.length === 0 ? (
                      <p className="text-xs text-warroom-muted py-4">No top posts data available.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {topVideos.map((vid, idx) => (
                          <div key={idx} className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition">
                            <p className="text-sm text-warroom-text font-medium line-clamp-2 mb-2">{vid.title || "Untitled"}</p>
                            {vid.hook && (
                              <p className="text-xs text-warroom-accent mb-2 line-clamp-1">🪝 {vid.hook}</p>
                            )}
                            <div className="flex items-center gap-3 text-xs text-warroom-muted mb-2">
                              <span className="flex items-center gap-1 text-pink-400"><Heart size={12} /> {formatNum(vid.likes)}</span>
                              <span className="flex items-center gap-1 text-blue-400"><MessageCircle size={12} /> {formatNum(vid.comments)}</span>
                              {vid.shares > 0 && (
                                <span className="flex items-center gap-1 text-purple-400">{formatNum(vid.shares)} shares</span>
                              )}
                            </div>
                            <div className="flex items-center justify-between text-[10px] text-warroom-muted">
                              <span>Score: <span className="text-warroom-accent font-medium">{vid.engagement_score.toFixed(0)}</span></span>
                              <div className="flex items-center gap-2">
                                {vid.posted_at && <span>{timeAgo(vid.posted_at)}</span>}
                                {vid.post_url && (
                                  <a href={vid.post_url} target="_blank" rel="noopener noreferrer"
                                    className="text-warroom-muted hover:text-warroom-accent transition">
                                    <ExternalLink size={12} />
                                  </a>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* ── Hashtag Cloud ── */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Hash size={16} className="text-cyan-400" />
                      <h4 className="text-sm font-semibold">Hashtag Cloud</h4>
                    </div>

                    {loadingHashtags ? (
                      <div className="flex items-center gap-2 text-sm text-warroom-muted py-4">
                        <Loader2 size={16} className="animate-spin" /> Loading hashtags…
                      </div>
                    ) : hashtags.length === 0 ? (
                      <p className="text-xs text-warroom-muted py-2">No hashtags found in posts.</p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {hashtags.slice(0, 20).map((ht, idx) => {
                          const colors = [
                            "bg-pink-500/15 text-pink-400",
                            "bg-blue-500/15 text-blue-400",
                            "bg-cyan-500/15 text-cyan-400",
                            "bg-purple-500/15 text-purple-400",
                            "bg-orange-500/15 text-orange-400",
                            "bg-green-500/15 text-green-400",
                            "bg-yellow-500/15 text-yellow-400",
                            "bg-red-500/15 text-red-400",
                          ];
                          const color = colors[idx % colors.length];
                          const maxCount = hashtags[0]?.count || 1;
                          const scale = 0.7 + 0.6 * (ht.count / maxCount);
                          return (
                            <span key={idx}
                              className={`px-2.5 py-1 rounded-full font-medium ${color}`}
                              style={{ fontSize: `${scale}rem` }}>
                              {ht.tag} <span className="opacity-60">({ht.count})</span>
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Content feed — scrollable post list */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold flex items-center gap-2">
                        <BarChart3 size={16} className="text-warroom-accent" />
                        Recent Content ({competitorPosts.length} posts)
                      </h4>
                      <span className="text-xs text-warroom-muted">Sorted by engagement</span>
                    </div>

                    {loadingPosts ? (
                      <div className="text-center py-16">
                        <Loader2 size={24} className="mx-auto animate-spin text-warroom-accent mb-3" />
                        <p className="text-sm text-warroom-muted">Loading posts...</p>
                      </div>
                    ) : competitorPosts.length === 0 ? (
                      <div className="text-center py-16 text-warroom-muted">
                        <Eye size={32} className="mx-auto mb-3 opacity-20" />
                        <p className="text-sm">No posts cached yet</p>
                        <p className="text-xs mt-1">Hit Refresh All to scrape their latest content</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {[...competitorPosts]
                          .sort((a, b) => b.engagement_score - a.engagement_score)
                          .map((post, idx) => (
                          <div key={idx} className="bg-warroom-surface border border-warroom-border rounded-xl p-5 hover:border-warroom-accent/20 transition">
                            {/* Rank badge */}
                            <div className="flex items-start gap-4">
                              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                                idx === 0 ? "bg-yellow-500/20 text-yellow-400" :
                                idx === 1 ? "bg-gray-400/20 text-gray-300" :
                                idx === 2 ? "bg-orange-500/20 text-orange-400" :
                                "bg-warroom-bg text-warroom-muted"
                              }`}>
                                #{idx + 1}
                              </div>

                              <div className="flex-1 min-w-0">
                                {/* Hook */}
                                {post.hook && (
                                  <p className="text-sm font-medium text-warroom-accent mb-1">🪝 {post.hook}</p>
                                )}

                                {/* Full caption */}
                                <p className="text-sm text-warroom-text whitespace-pre-line mb-3">{post.text}</p>

                                {/* Metrics bar */}
                                <div className="flex items-center gap-4 text-xs">
                                  <span className="flex items-center gap-1 text-pink-400">
                                    <Heart size={13} /> {formatNum(post.likes)}
                                  </span>
                                  <span className="flex items-center gap-1 text-blue-400">
                                    <MessageCircle size={13} /> {formatNum(post.comments)}
                                  </span>
                                  {post.shares > 0 && (
                                    <span className="flex items-center gap-1 text-purple-400">
                                      <EyeIcon size={13} /> {formatNum(post.shares)} views
                                    </span>
                                  )}
                                  <span className="ml-auto text-warroom-muted">
                                    Score: <span className="text-warroom-accent font-medium">{post.engagement_score.toFixed(0)}</span>
                                  </span>
                                  {post.timestamp && (
                                    <span className="text-warroom-muted">{timeAgo(post.timestamp)}</span>
                                  )}
                                  {post.url && (
                                    <a href={post.url} target="_blank" rel="noopener noreferrer"
                                      className="text-warroom-muted hover:text-warroom-accent transition">
                                      <ExternalLink size={13} />
                                    </a>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                </div>
              ) : (
                /* GRID VIEW — all competitors */
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-warroom-muted">Click a competitor to see their top content.</p>
                    <div className="flex gap-2">
                      <button onClick={refreshAllCompetitors} disabled={loading}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-bg border border-warroom-border hover:bg-warroom-surface rounded-lg text-xs font-medium transition disabled:opacity-50">
                        <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh All
                      </button>
                      <button onClick={() => setShowAddCompetitor(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition">
                        <Plus size={14} /> Add Competitor
                      </button>
                    </div>
                  </div>

                  {loading ? (
                    <div className="text-center py-16">
                      <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                      <p className="text-sm text-warroom-muted">Loading competitors...</p>
                    </div>
                  ) : competitors.length === 0 ? (
                    <div className="text-center py-16 text-warroom-muted">
                      <Target size={48} className="mx-auto mb-4 opacity-20" />
                      <p className="text-sm">No competitors tracked yet</p>
                      <p className="text-xs mt-1">Add your first competitor to start gathering intelligence</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {competitors.map(comp => (
                        <div key={comp.id}
                          className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/30 hover:shadow-lg hover:shadow-warroom-accent/5 transition cursor-pointer flex flex-col group"
                          onClick={() => focusOnCompetitor(comp)}
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-warroom-accent/10 flex items-center justify-center text-lg font-bold text-warroom-accent group-hover:bg-warroom-accent/20 transition">
                                {comp.handle.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <h4 className="font-semibold text-sm">@{comp.handle}</h4>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[comp.platform] || "bg-gray-500/20 text-gray-400"}`}>{comp.platform}</span>
                              </div>
                            </div>
                            <button onClick={(e) => { e.stopPropagation(); deleteCompetitor(comp.id); }}
                              className="text-warroom-muted hover:text-red-400 transition opacity-0 group-hover:opacity-100">
                              <Trash2 size={14} />
                            </button>
                          </div>

                          <div className="grid grid-cols-3 gap-1 text-center mb-3">
                            <div className="bg-warroom-bg rounded-lg py-2">
                              <p className="text-sm font-semibold text-warroom-text">{formatNum(comp.followers)}</p>
                              <p className="text-[10px] text-warroom-muted">Followers</p>
                            </div>
                            <div className="bg-warroom-bg rounded-lg py-2">
                              <p className="text-sm font-semibold text-warroom-text">{formatNum(comp.post_count)}</p>
                              <p className="text-[10px] text-warroom-muted">Posts</p>
                            </div>
                            <div className="bg-warroom-bg rounded-lg py-2">
                              <p className="text-sm font-semibold text-warroom-text">{comp.avg_engagement_rate.toFixed(1)}%</p>
                              <p className="text-[10px] text-warroom-muted">Eng Rate</p>
                            </div>
                          </div>

                          {comp.bio && (
                            <p className="text-xs text-warroom-muted line-clamp-2 mb-2 flex-1">{comp.bio}</p>
                          )}

                          <div className="flex items-center justify-between text-[10px] text-warroom-muted mt-auto pt-2 border-t border-warroom-border">
                            <span>{comp.posting_frequency || "—"}</span>
                            <span>{comp.last_auto_sync ? timeAgo(comp.last_auto_sync) : "Never synced"}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* TOP CONTENT TAB */}
          {activeTab === "top-content" && (
            <div className="space-y-4">
              <p className="text-sm text-warroom-muted">Top-performing posts across all tracked competitors.</p>
              
              {loading ? (
                <div className="text-center py-16">
                  <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                  <p className="text-sm text-warroom-muted">Loading top content...</p>
                </div>
              ) : topContent.length === 0 ? (
                <div className="text-center py-16 text-warroom-muted">
                  <TrendingUp size={48} className="mx-auto mb-4 opacity-20" />
                  <p className="text-sm">No top content available</p>
                  <p className="text-xs mt-1">Refresh competitor data to analyze their posts</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {topContent.map((post, idx) => (
                    <div key={idx} className="bg-warroom-surface border border-warroom-border rounded-2xl p-4 hover:border-warroom-accent/30 transition">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[post.platform] || "bg-gray-500/20 text-gray-400"}`}>{post.platform}</span>
                          <span className="text-xs text-warroom-muted">@{post.competitor_handle}</span>
                        </div>
                        {post.url && (
                          <a href={post.url} target="_blank" rel="noopener noreferrer" className="text-warroom-muted hover:text-warroom-accent transition">
                            <ExternalLink size={14} />
                          </a>
                        )}
                      </div>
                      
                      {post.hook && (
                        <p className="text-sm font-medium text-warroom-accent mb-1">🪝 {post.hook}</p>
                      )}
                      <p className="text-xs text-warroom-text mb-3 line-clamp-3">{(post.text || "").slice(0, 200)}</p>
                      
                      <div className="flex items-center justify-between text-xs text-warroom-muted">
                        <div className="flex gap-3">
                          <span>❤️ {formatNum(post.likes)}</span>
                          <span>💬 {formatNum(post.comments)}</span>
                          {post.shares > 0 && <span>👁 {formatNum(post.shares)}</span>}
                        </div>
                        {post.timestamp && <span>{timeAgo(post.timestamp)}</span>}
                      </div>
                      
                      <div className="mt-2 bg-warroom-bg rounded px-2 py-1 flex items-center justify-between">
                        <span className="text-xs text-warroom-accent font-medium">Score: {post.engagement_score.toFixed(0)}</span>
                        <span className="text-[10px] text-warroom-muted">#{idx + 1}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* HOOKS TAB */}
          {activeTab === "hooks" && (
            <div className="space-y-4">
              <p className="text-sm text-warroom-muted">Extracted hooks from top-performing competitor content.</p>
              
              {loading ? (
                <div className="text-center py-16">
                  <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                  <p className="text-sm text-warroom-muted">Loading hooks...</p>
                </div>
              ) : hooks.length === 0 ? (
                <div className="text-center py-16 text-warroom-muted">
                  <Zap size={48} className="mx-auto mb-4 opacity-20" />
                  <p className="text-sm">No hooks available yet</p>
                  <p className="text-xs mt-1">Refresh competitor data to extract hooks from their posts</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {hooks.sort((a, b) => b.engagement_score - a.engagement_score).map((hook, idx) => (
                    <div key={idx} className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[hook.platform] || "bg-gray-500/20 text-gray-400"}`}>{hook.platform}</span>
                          <span className="text-xs text-warroom-muted">@{hook.competitor_handle}</span>
                        </div>
                        <button onClick={() => { navigator.clipboard.writeText(hook.hook); setCopiedHook(idx); setTimeout(() => setCopiedHook(null), 2000); }}
                          className="flex items-center gap-1 px-2 py-1 bg-warroom-accent/10 hover:bg-warroom-accent/20 text-warroom-accent rounded text-xs transition">
                          {copiedHook === idx ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
                        </button>
                      </div>
                      
                      <p className="text-sm text-warroom-text mb-2">{hook.hook}</p>
                      
                      <div className="flex items-center justify-between text-xs text-warroom-muted">
                        <span>Score: {hook.engagement_score.toFixed(0)}</span>
                        {hook.source_url && (
                          <a href={hook.source_url} target="_blank" rel="noopener noreferrer" className="hover:text-warroom-accent transition">
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* SCRIPTS TAB */}
          {activeTab === "scripts" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-warroom-muted">Generated scripts based on competitor intelligence.</p>
                <button onClick={() => setShowGenerateScript(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition">
                  <Plus size={14} /> Generate New
                </button>
              </div>

              {loading ? (
                <div className="text-center py-16">
                  <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                  <p className="text-sm text-warroom-muted">Loading scripts...</p>
                </div>
              ) : scripts.length === 0 ? (
                <div className="text-center py-16 text-warroom-muted">
                  <BookOpen size={48} className="mx-auto mb-4 opacity-20" />
                  <p className="text-sm">No scripts generated yet</p>
                  <p className="text-xs mt-1">Generate your first script based on competitor insights</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {scripts.map(script => (
                    <div key={script.id} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/30 transition">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h4 className="font-semibold text-sm mb-1">{script.title}</h4>
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[script.platform] || "bg-gray-500/20 text-gray-400"}`}>{script.platform}</span>
                            <span className="text-xs text-warroom-muted">{timeAgo(script.created_at)}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button onClick={() => deleteScript(script.id)}
                            className="text-warroom-muted hover:text-red-400 transition">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>

                      {script.hook_preview && (
                        <div className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 mb-3">
                          <p className="text-xs text-warroom-muted font-medium mb-0.5">Hook Preview</p>
                          <p className="text-sm italic">{script.hook_preview}</p>
                        </div>
                      )}

                      <p className="text-sm text-warroom-text mb-3">{script.content.slice(0, 200)}...</p>

                      <div className="flex gap-2">
                        <button onClick={() => saveScriptToPlatform(script, "instagram")}
                          className="flex items-center gap-1 px-2 py-1 bg-pink-500/10 text-pink-400 rounded text-xs hover:bg-pink-500/20 transition">
                          <Save size={12} /> Save to Instagram
                        </button>
                        <button onClick={() => saveScriptToPlatform(script, "youtube")}
                          className="flex items-center gap-1 px-2 py-1 bg-red-500/10 text-red-400 rounded text-xs hover:bg-red-500/20 transition">
                          <Save size={12} /> Save to YouTube
                        </button>
                        <button onClick={() => saveScriptToPlatform(script, "tiktok")}
                          className="flex items-center gap-1 px-2 py-1 bg-cyan-500/10 text-cyan-400 rounded text-xs hover:bg-cyan-500/20 transition">
                          <Save size={12} /> Save to TikTok
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Add Competitor Modal */}
      {showAddCompetitor && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Add Competitor</h3>
              <button onClick={() => setShowAddCompetitor(false)} className="text-warroom-muted hover:text-warroom-text">
                <X size={20} />
              </button>
            </div>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">Handle</label>
                  <input 
                    type="text" 
                    value={newComp.handle} 
                    onChange={e => setNewComp({ ...newComp, handle: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" 
                    placeholder="handle" 
                    autoFocus 
                  />
                </div>
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">Platform</label>
                  <select 
                    value={newComp.platform} 
                    onChange={e => setNewComp({ ...newComp, platform: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent">
                    {Object.keys(PLATFORM_COLORS).map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowAddCompetitor(false)} 
                className="flex-1 px-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm hover:bg-warroom-surface transition">
                Cancel
              </button>
              <button onClick={addCompetitor} disabled={!newComp.handle.trim() || submitting}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2">
                {submitting ? <><Loader2 size={14} className="animate-spin" /> Adding...</> : "Add Competitor"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Generate Script Modal */}
      {showGenerateScript && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Generate Script</h3>
              <button onClick={() => setShowGenerateScript(false)} className="text-warroom-muted hover:text-warroom-text">
                <X size={20} />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Competitor</label>
                <select 
                  value={scriptForm.competitor_id} 
                  onChange={e => setScriptForm({ ...scriptForm, competitor_id: parseInt(e.target.value) })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent">
                  <option value={0}>Select a competitor</option>
                  {competitors.map(comp => (
                    <option key={comp.id} value={comp.id}>@{comp.handle} ({comp.platform})</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Platform</label>
                <select 
                  value={scriptForm.platform} 
                  onChange={e => setScriptForm({ ...scriptForm, platform: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent">
                  {Object.keys(PLATFORM_COLORS).map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Topic</label>
                <input 
                  type="text" 
                  value={scriptForm.topic} 
                  onChange={e => setScriptForm({ ...scriptForm, topic: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" 
                  placeholder="What should this script be about?" 
                />
              </div>
              
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Hook Style (optional)</label>
                <input 
                  type="text" 
                  value={scriptForm.hook_style} 
                  onChange={e => setScriptForm({ ...scriptForm, hook_style: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" 
                  placeholder="e.g. question, bold claim, shocking stat" 
                />
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowGenerateScript(false)} 
                className="flex-1 px-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm hover:bg-warroom-surface transition">
                Cancel
              </button>
              <button onClick={generateScript} disabled={!scriptForm.competitor_id || !scriptForm.topic.trim() || submitting}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2">
                {submitting ? <><Loader2 size={14} className="animate-spin" /> Generating...</> : "Generate Script"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}