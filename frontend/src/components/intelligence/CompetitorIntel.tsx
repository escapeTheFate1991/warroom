"use client";

import { useState, useEffect } from "react";
import { Search, Plus, X, Flame, Copy, Check, User, TrendingUp, Eye, Target, Zap, BookOpen, ExternalLink, Trash2, Loader2, RefreshCw, Play, Save, Edit3 } from "lucide-react";

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
  id: string;
  content: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  created_at: string;
  url?: string;
}

interface TopContentPost {
  id: string;
  content: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  platform: string;
  competitor_handle: string;
  created_at: string;
  url?: string;
}

interface Hook {
  id: number;
  text: string;
  engagement_score: number;
  style?: string;
  platform: string;
  competitor_handle: string;
  post_id?: string;
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
        setTopContent(data.sort((a: any, b: any) => b.engagement_score - a.engagement_score));
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
        setHooks(data);
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
        setCompetitorPosts(data);
      } else {
        setCompetitorPosts([]);
      }
    } catch (error) {
      setCompetitorPosts([]);
    } finally {
      setLoadingPosts(false);
    }
  };

  // Load data based on active tab
  useEffect(() => {
    switch (activeTab) {
      case "competitors":
        fetchCompetitors();
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

  // Refresh all competitors
  const refreshAllCompetitors = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API}/api/competitors/sync`, {
        method: "POST",
      });

      if (response.ok) {
        fetchCompetitors(); // Refresh data
      } else {
        const error = await response.json();
        setError(`Failed to refresh data: ${error.detail || response.statusText}`);
      }
    } catch (error) {
      setError(`Error refreshing data: ${error}`);
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
  const copyHook = (hook: Hook) => {
    navigator.clipboard.writeText(hook.text);
    setCopiedHook(hook.id);
    setTimeout(() => setCopiedHook(null), 2000);
  };

  // Expand competitor to show posts
  const toggleCompetitorExpansion = (competitorId: number) => {
    if (expandedCompetitor === competitorId) {
      setExpandedCompetitor(null);
      setCompetitorPosts([]);
    } else {
      setExpandedCompetitor(competitorId);
      fetchCompetitorPosts(competitorId);
    }
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
              <div className="flex items-center justify-between">
                <p className="text-sm text-warroom-muted">Track competitors to learn their winning angles and posting strategies.</p>
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
                <div className="space-y-4">
                  {competitors.map(comp => (
                    <div key={comp.id}>
                      <div 
                        className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/30 transition cursor-pointer"
                        onClick={() => toggleCompetitorExpansion(comp.id)}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-warroom-accent/10 flex items-center justify-center">
                              {comp.profile_image_url ? (
                                <img src={comp.profile_image_url} alt="" className="w-10 h-10 rounded-full object-cover" />
                              ) : (
                                <User size={20} className="text-warroom-accent" />
                              )}
                            </div>
                            <div>
                              <h4 className="font-semibold text-sm">@{comp.handle}</h4>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[comp.platform] || "bg-gray-500/20 text-gray-400"}`}>{comp.platform}</span>
                                <span className="text-xs text-warroom-muted">{formatNum(comp.followers)} followers</span>
                                <span className="text-xs text-warroom-muted">{comp.avg_engagement_rate.toFixed(1)}% engagement</span>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button onClick={(e) => { e.stopPropagation(); deleteCompetitor(comp.id); }}
                              className="text-warroom-muted hover:text-red-400 transition">
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-2 text-xs text-warroom-muted mb-3">
                          <div>Following: {formatNum(comp.following)}</div>
                          <div>Posts: {formatNum(comp.post_count)}</div>
                          <div>Last sync: {comp.last_auto_sync ? timeAgo(comp.last_auto_sync) : "Never"}</div>
                        </div>

                        {comp.bio && (
                          <p className="text-xs text-warroom-text mb-2 line-clamp-2">{comp.bio}</p>
                        )}
                      </div>

                      {/* Expanded Posts */}
                      {expandedCompetitor === comp.id && (
                        <div className="mt-2 ml-4 space-y-2">
                          {loadingPosts ? (
                            <div className="text-center py-8">
                              <Loader2 size={20} className="mx-auto animate-spin text-warroom-accent" />
                            </div>
                          ) : competitorPosts.length === 0 ? (
                            <p className="text-xs text-warroom-muted py-4 text-center">No recent posts available</p>
                          ) : (
                            competitorPosts.slice(0, 3).map(post => (
                              <div key={post.id} className="bg-warroom-bg border border-warroom-border rounded-lg p-3">
                                <p className="text-xs text-warroom-text mb-2">{post.content.slice(0, 100)}...</p>
                                <div className="flex items-center justify-between text-xs text-warroom-muted">
                                  <div className="flex gap-3">
                                    <span>❤️ {formatNum(post.likes)}</span>
                                    <span>💬 {formatNum(post.comments)}</span>
                                    <span>🔄 {formatNum(post.shares)}</span>
                                  </div>
                                  <span>{timeAgo(post.created_at)}</span>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
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
                  {topContent.map(post => (
                    <div key={post.id} className="bg-warroom-surface border border-warroom-border rounded-2xl p-4 hover:border-warroom-accent/30 transition">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[post.platform] || "bg-gray-500/20 text-gray-400"}`}>{post.platform}</span>
                          <span className="text-xs text-warroom-muted">@{post.competitor_handle}</span>
                        </div>
                        {post.url && (
                          <a href={post.url} target="_blank" rel="noopener" className="text-warroom-muted hover:text-warroom-accent transition">
                            <ExternalLink size={14} />
                          </a>
                        )}
                      </div>
                      
                      <p className="text-sm text-warroom-text mb-3 line-clamp-3">{post.content.slice(0, 150)}...</p>
                      
                      <div className="flex items-center justify-between text-xs text-warroom-muted">
                        <div className="flex gap-3">
                          <span>❤️ {formatNum(post.likes)}</span>
                          <span>💬 {formatNum(post.comments)}</span>
                          <span>🔄 {formatNum(post.shares)}</span>
                        </div>
                        <span>{timeAgo(post.created_at)}</span>
                      </div>
                      
                      <div className="mt-2 bg-warroom-bg rounded px-2 py-1">
                        <span className="text-xs text-warroom-accent font-medium">Score: {post.engagement_score.toFixed(1)}</span>
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
                  {hooks.sort((a, b) => b.engagement_score - a.engagement_score).map(hook => (
                    <div key={hook.id} className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[hook.platform] || "bg-gray-500/20 text-gray-400"}`}>{hook.platform}</span>
                          <span className="text-xs text-warroom-muted">@{hook.competitor_handle}</span>
                          {hook.style && <span className="text-xs text-warroom-accent">{hook.style}</span>}
                        </div>
                        <button onClick={() => copyHook(hook)}
                          className="flex items-center gap-1 px-2 py-1 bg-warroom-accent/10 hover:bg-warroom-accent/20 text-warroom-accent rounded text-xs transition">
                          {copiedHook === hook.id ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
                        </button>
                      </div>
                      
                      <p className="text-sm text-warroom-text mb-2">{hook.text}</p>
                      
                      <div className="text-xs text-warroom-muted">
                        <span>Engagement Score: {hook.engagement_score.toFixed(1)}</span>
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