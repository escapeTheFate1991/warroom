"use client";

import { useState, useEffect } from "react";
import { Search, Plus, X, Flame, Copy, Check, User, TrendingUp, Eye, Target, Zap, BookOpen, ExternalLink, Trash2, Loader2, RefreshCw, Play, Save, Edit3, ArrowLeft, Heart, MessageCircle, EyeIcon, BarChart3, Hash, Users, Sparkles, ShoppingBag, Film, FileText } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import PostDetailModal from "./PostDetailModal";


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
  id?: number;
  text: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  timestamp: string;
  url?: string;
  hook?: string;
  media_type?: string;
  has_transcript?: boolean;
  has_comments?: boolean;
}

interface TopContentPost {
  text: string;
  hook: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  virality_score: number;
  platform: string;
  competitor_handle: string;
  timestamp: string;
  url?: string;
  start_time?: number; // Video start time in seconds
  end_time?: number;   // Video end time in seconds
}

interface Hook {
  hook: string;
  engagement_score: number;
  virality_score: number;
  platform: string;
  competitor_handle: string;
  source_url?: string;
}

interface SimilarVideoReference {
  competitor_handle: string;
  platform: string;
  source_url?: string;
  hook: string;
  engagement_score: number;
}

interface ScriptScene {
  scene: string;
  direction: string;
  goal: string;
}

interface Script {
  id?: number;
  competitor_id?: number;
  platform: string;
  title: string;
  hook: string;
  body_outline: string;
  cta: string;
  topic?: string;
  source_post_url?: string;
  estimated_duration?: string;
  created_at?: string;
  predicted_views: number;
  predicted_engagement: number;
  predicted_engagement_rate: number;
  virality_score: number;
  business_alignment_score: number;
  business_alignment_label: string;
  business_alignment_reason: string;
  source_competitors: string[];
  similar_videos: SimilarVideoReference[];
  scene_map: ScriptScene[];
}

interface TopVideoItem {
  id?: number;
  post_url?: string;
  title: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  posted_at?: string;
  hook?: string;
  media_type?: string;
  has_transcript?: boolean;
  has_comments?: boolean;
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

interface ScrapeStatusResponse {
  sync_running: boolean;
}

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "bg-pink-500/20 text-pink-400",
  tiktok: "bg-cyan-500/20 text-cyan-400",
  youtube: "bg-red-500/20 text-red-400",
  x: "bg-gray-600/20 text-gray-300",
  facebook: "bg-blue-500/20 text-blue-400",
  threads: "bg-gray-500/20 text-gray-400",
};

const SCRIPT_SAVE_PLATFORMS = ["instagram", "youtube", "x", "facebook"] as const;

const ALIGNMENT_STYLES: Record<string, string> = {
  High: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  Medium: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  Low: "bg-slate-500/15 text-slate-300 border-slate-500/20",
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

// Format time in MM:SS format for video chunks
function formatTime(seconds?: number): string | null {
  if (seconds === undefined || seconds === null) return null;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatPercent(n: number, digits = 1): string {
  return `${n.toFixed(digits)}%`;
}

function formatPlatformLabel(platform: string): string {
  return platform === "x" ? "X" : platform.charAt(0).toUpperCase() + platform.slice(1);
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

/* ── Dossier Panel ─────────────────────────────────────── */

interface DossierData {
  bio: string;
  full_name: string;
  is_verified: boolean;
  category: string;
  followers: number;
  following: number;
  post_count: number;
  linked_handles: string[];
  links: string[];
  bio_links: { url: string; title: string }[];
  affiliate_links: string[];
  product_mentions: string[];
  business_intel: {
    positions?: { title: string; company: string }[];
    roles?: string[];
    experience?: string;
    offering?: string;
    accepts_inquiries?: boolean;
    full_name?: string;
  };
  audience: {
    themes: string[];
    audience_type: string;
    engagement_style: string;
    key_interests: string[];
  } | null;
  content_summary: {
    total_posts: number;
    avg_engagement: number;
    top_hashtags: { tag: string; count: number }[];
    post_frequency: string;
  };
}

function DossierPanel({ competitorId, bio }: { competitorId: number; bio?: string }) {
  const [dossier, setDossier] = useState<DossierData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    authFetch(`${API}/api/content-intel/competitors/${competitorId}/dossier`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setDossier(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="animate-spin text-warroom-accent" size={24} />
      </div>
    );
  }

  if (!dossier) {
    return <p className="text-sm text-warroom-muted text-center py-8">Failed to load dossier data.</p>;
  }

  return (
    <div className="space-y-6">
      {/* Bio */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <User size={16} className="text-warroom-accent" />
          <h4 className="text-sm font-semibold">Bio Information</h4>
        </div>
        {(dossier.full_name || dossier.is_verified || dossier.category) && (
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {dossier.full_name && <span className="text-sm font-semibold text-warroom-text">{dossier.full_name}</span>}
            {dossier.is_verified && <span className="text-blue-400 text-xs">✓ Verified</span>}
            {dossier.category && <span className="text-xs text-warroom-muted bg-warroom-bg px-2 py-0.5 rounded-full">{dossier.category}</span>}
          </div>
        )}
        {dossier.bio ? (
          <p className="text-sm text-warroom-text whitespace-pre-line">{dossier.bio}</p>
        ) : (
          <p className="text-sm text-warroom-muted italic">No bio available</p>
        )}
        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="text-center bg-warroom-bg rounded-lg p-2">
            <p className="text-lg font-bold text-warroom-text">{(dossier.followers || 0).toLocaleString()}</p>
            <p className="text-[10px] text-warroom-muted uppercase">Followers</p>
          </div>
          <div className="text-center bg-warroom-bg rounded-lg p-2">
            <p className="text-lg font-bold text-warroom-text">{(dossier.following || 0).toLocaleString()}</p>
            <p className="text-[10px] text-warroom-muted uppercase">Following</p>
          </div>
          <div className="text-center bg-warroom-bg rounded-lg p-2">
            <p className="text-lg font-bold text-warroom-text">{dossier.content_summary.post_frequency}</p>
            <p className="text-[10px] text-warroom-muted uppercase">Post Freq</p>
          </div>
        </div>
      </div>

      {/* Audience Intelligence */}
      {dossier.audience && (
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Target size={16} className="text-warroom-accent" />
            <h4 className="text-sm font-semibold">Audience Intelligence</h4>
          </div>
          <div className="space-y-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Audience Type</p>
              <p className="text-sm text-warroom-text font-medium">{dossier.audience.audience_type}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Engagement Style</p>
              <p className="text-sm text-warroom-text">{dossier.audience.engagement_style}</p>
            </div>
            {dossier.audience.themes.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Content Themes</p>
                <div className="flex flex-wrap gap-1.5">
                  {dossier.audience.themes.map((t, i) => (
                    <span key={i} className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full text-[10px]">{t}</span>
                  ))}
                </div>
              </div>
            )}
            {dossier.audience.key_interests.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Key Interests</p>
                <div className="flex flex-wrap gap-1.5">
                  {dossier.audience.key_interests.map((k, i) => (
                    <span key={i} className="px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded-full text-[10px]">{k}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Products & Business */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <ShoppingBag size={16} className="text-warroom-accent" />
          <h4 className="text-sm font-semibold">Products & Business</h4>
        </div>
        {(dossier.business_intel && Object.keys(dossier.business_intel).length > 0) || dossier.product_mentions.length > 0 ? (
          <div className="space-y-3">
            {/* Positions / Roles */}
            {dossier.business_intel?.positions && dossier.business_intel.positions.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Background</p>
                <div className="space-y-1">
                  {dossier.business_intel.positions.map((p, i) => (
                    <div key={i} className="bg-warroom-bg rounded-lg px-3 py-2 text-xs text-warroom-text">
                      <span className="font-medium">{p.title}</span>
                      {p.company && <span className="text-warroom-muted"> at {p.company}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {/* Experience */}
            {dossier.business_intel?.experience && (
              <div>
                <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Experience</p>
                <p className="text-sm text-warroom-text">{dossier.business_intel.experience}</p>
              </div>
            )}
            {/* What they offer */}
            {dossier.business_intel?.offering && (
              <div>
                <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Offering</p>
                <p className="text-sm text-warroom-text">{dossier.business_intel.offering}</p>
              </div>
            )}
            {/* Accepts inquiries */}
            {dossier.business_intel?.accepts_inquiries && (
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-400"></span>
                <span className="text-xs text-green-400">Open to inquiries / bookings</span>
              </div>
            )}
            {/* Product mentions from captions */}
            {dossier.product_mentions.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Product Mentions</p>
                {dossier.product_mentions.map((p, i) => (
                  <div key={i} className="bg-warroom-bg rounded-lg px-3 py-2 text-xs text-warroom-text">{p}</div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-warroom-muted italic">No business intel detected</p>
        )}
      </div>

      {/* Links & Affiliate */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <ExternalLink size={16} className="text-warroom-accent" />
          <h4 className="text-sm font-semibold">Links & References</h4>
        </div>
        <div className="space-y-3">
          {/* Profile bio links (from Instagram multi-link feature) */}
          {dossier.bio_links && dossier.bio_links.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Profile Links ({dossier.bio_links.length})</p>
              <div className="space-y-1">
                {dossier.bio_links.map((l, i) => (
                  <a key={i} href={l.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 bg-warroom-bg rounded-lg px-3 py-2 text-xs text-warroom-accent hover:border-warroom-accent/50 border border-warroom-border transition">
                    <ExternalLink size={10} className="flex-shrink-0" />
                    <span className="truncate">{l.title || l.url}</span>
                  </a>
                ))}
              </div>
            </div>
          )}
          {/* Links found in captions */}
          {dossier.links.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-warroom-muted mb-1">Links in Content ({dossier.links.length})</p>
              <div className="space-y-1">
                {dossier.links.slice(0, 10).map((l, i) => (
                  <a key={i} href={l} target="_blank" rel="noopener noreferrer" className="block text-xs text-warroom-accent hover:underline truncate">{l}</a>
                ))}
              </div>
            </div>
          )}
          {dossier.affiliate_links.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-red-400 mb-1">Affiliate Links ({dossier.affiliate_links.length})</p>
              <div className="space-y-1">
                {dossier.affiliate_links.map((l, i) => (
                  <a key={i} href={l} target="_blank" rel="noopener noreferrer" className="block text-xs text-red-400 hover:underline truncate">{l}</a>
                ))}
              </div>
            </div>
          )}
          {(!dossier.bio_links || dossier.bio_links.length === 0) && dossier.links.length === 0 && dossier.affiliate_links.length === 0 && (
            <p className="text-sm text-warroom-muted italic">No links found in content</p>
          )}
        </div>
      </div>

      {/* Network / Linked Accounts */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <Users size={16} className="text-warroom-accent" />
          <h4 className="text-sm font-semibold">Network Intelligence</h4>
        </div>
        {dossier.linked_handles.length > 0 ? (
          <div>
            <p className="text-xs uppercase tracking-wide text-warroom-muted mb-2">Linked Accounts ({dossier.linked_handles.length})</p>
            <div className="flex flex-wrap gap-2">
              {dossier.linked_handles.map((h, i) => {
                const isThreads = h.startsWith('threads:');
                const displayHandle = isThreads ? h.replace('threads:', '') : `@${h}`;
                const href = isThreads
                  ? `https://threads.net/${h.replace('threads:@', '')}`
                  : `https://instagram.com/${h}`;
                const platform = isThreads ? '🧵' : '📷';
                return (
                  <a
                    key={i}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 px-2.5 py-1 bg-warroom-bg border border-warroom-border rounded-lg text-xs text-warroom-text hover:border-warroom-accent/50 transition"
                  >
                    <span>{platform}</span>
                    {displayHandle}
                    <ExternalLink size={10} className="text-warroom-muted" />
                  </a>
                );
              })}
            </div>
          </div>
        ) : (
          <p className="text-sm text-warroom-muted italic">No linked accounts detected</p>
        )}

        {/* Top Hashtags */}
        {dossier.content_summary.top_hashtags.length > 0 && (
          <div className="mt-4">
            <p className="text-xs uppercase tracking-wide text-warroom-muted mb-2">Top Hashtags</p>
            <div className="flex flex-wrap gap-1.5">
              {dossier.content_summary.top_hashtags.map((h, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-full text-[10px]">
                  #{h.tag} <span className="text-blue-400/50">({h.count})</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CompetitorIntel() {
  const [activeTab, setActiveTab] = useState<"competitors" | "top-content" | "hooks" | "scripts">("competitors");
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [topContent, setTopContent] = useState<TopContentPost[]>([]);
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedScriptId, setSelectedScriptId] = useState<number | null>(null);
  const [expandedCompetitor, setExpandedCompetitor] = useState<number | null>(null);
  const [focusedCompetitor, setFocusedCompetitor] = useState<Competitor | null>(null);
  const [competitorPosts, setCompetitorPosts] = useState<CompetitorPost[]>([]);
  const [competitorDetailTab, setCompetitorDetailTab] = useState<"overview" | "dossier">("overview");
  
  const [showAddCompetitor, setShowAddCompetitor] = useState(false);
  const [showGenerateScript, setShowGenerateScript] = useState(false);
  const [copiedHook, setCopiedHook] = useState<number | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [loadingPosts, setLoadingPosts] = useState(false);
  
  const [newComp, setNewComp] = useState({ handle: "", platform: "instagram" });
  const [scriptForm, setScriptForm] = useState({
    competitor_id: 0,
    platform: "instagram",
    topic: "",
    hook_style: "",
    count: 6,
  });
  
  const [error, setError] = useState<string>("");
  const [notice, setNotice] = useState<string>("");

  // New state for upgraded Reports features
  const [followerAnalysis, setFollowerAnalysis] = useState<FollowerAnalysis | null>(null);
  const [loadingFollowerAnalysis, setLoadingFollowerAnalysis] = useState(false);
  const [topVideos, setTopVideos] = useState<TopVideoItem[]>([]);
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null);
  const [loadingTopVideos, setLoadingTopVideos] = useState(false);
  const [hashtags, setHashtags] = useState<HashtagItem[]>([]);
  const [loadingHashtags, setLoadingHashtags] = useState(false);

  // Fetch competitors
  const fetchCompetitors = async (): Promise<Competitor[]> => {
    try {
      setLoading(true);
      setError("");
      const response = await authFetch(`${API}/api/competitors`);
      if (response.ok) {
        const data = await response.json();
        const nextCompetitors = Array.isArray(data) ? data : [];
        setCompetitors(nextCompetitors);
        setFocusedCompetitor((prev) => {
          if (!prev) return prev;
          return nextCompetitors.find((competitor) => competitor.id === prev.id) || null;
        });
        return nextCompetitors;
      } else {
        setError("Failed to fetch competitors");
        return [];
      }
    } catch (error) {
      setError("Error connecting to API");
      return [];
    } finally {
      setLoading(false);
    }
  };

  // Fetch top content
  const fetchTopContent = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await authFetch(`${API}/api/content-intel/competitors/top-content`);
      if (response.ok) {
        const data = await response.json();
        const posts = Array.isArray(data) ? data : (data.posts || []);
        setTopContent(
          posts.sort((a: TopContentPost, b: TopContentPost) => (
            (b.virality_score || 0) - (a.virality_score || 0) || b.engagement_score - a.engagement_score
          ))
        );
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
      const response = await authFetch(`${API}/api/content-intel/competitors/hooks`);
      if (response.ok) {
        const data = await response.json();
        const nextHooks = Array.isArray(data) ? data : (data.hooks || []);
        setHooks(
          nextHooks.sort((a: Hook, b: Hook) => (
            (b.virality_score || 0) - (a.virality_score || 0) || b.engagement_score - a.engagement_score
          ))
        );
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
      const response = await authFetch(`${API}/api/content-intel/competitors/scripts`);
      if (response.ok) {
        const data = await response.json();
        const nextScripts = Array.isArray(data) ? data : [];
        setScripts(nextScripts);
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
      const response = await authFetch(`${API}/api/content-intel/competitors/${competitorId}/content`);
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
      const response = await authFetch(`${API}/api/content-intel/competitors/follower-analysis`);
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
      const response = await authFetch(`${API}/api/content-intel/competitors/${competitorId}/top-videos?limit=5`);
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
      const response = await authFetch(`${API}/api/content-intel/competitors/${competitorId}/hashtags`);
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

  const refreshFocusedCompetitorDetail = async (competitorId: number) => {
    await Promise.all([
      fetchCompetitorPosts(competitorId),
      fetchTopVideos(competitorId),
      fetchHashtags(competitorId),
    ]);
  };

  const refreshIntelligenceViews = async () => {
    const nextCompetitors = await fetchCompetitors();
    await Promise.all([
      fetchFollowerAnalysis(),
      fetchTopContent(),
      fetchHooks(),
      focusedCompetitor ? refreshFocusedCompetitorDetail(focusedCompetitor.id) : Promise.resolve(),
    ]);
    return nextCompetitors;
  };

  const waitForInstagramSyncCompletion = async () => {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000));

      try {
        const response = await authFetch(`${API}/api/scraper/status`);
        if (!response.ok) {
          break;
        }

        const status: ScrapeStatusResponse = await response.json();
        if (!status.sync_running) {
          await refreshIntelligenceViews();
          setNotice("Instagram scrape finished. Competitor intelligence updated.");
          return true;
        }
      } catch (error) {
        console.warn("Failed to poll Instagram scrape status", error);
        break;
      }
    }

    return false;
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

  useEffect(() => {
    if (!notice) return;

    const timeoutId = window.setTimeout(() => {
      setNotice("");
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  useEffect(() => {
    if (scripts.length === 0) {
      setSelectedScriptId(null);
      return;
    }

    setSelectedScriptId((prev) => {
      if (prev != null && scripts.some((script) => script.id === prev)) {
        return prev;
      }
      return scripts[0].id ?? null;
    });
  }, [scripts]);

  // Add competitor
  const addCompetitor = async () => {
    if (!newComp.handle.trim()) return;
    
    try {
      setSubmitting(true);
      setError("");
      
      // Create competitor
      const createResponse = await authFetch(`${API}/api/competitors`, {
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
          await authFetch(`${API}/api/competitors/${newCompetitor.id}/auto-populate`, {
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
      const response = await authFetch(`${API}/api/competitors/${id}`, {
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

  const getResponseMessage = async (response: Response): Promise<string> => {
    const payload = await response.json().catch(() => ({}));
    return payload.detail || payload.message || response.statusText;
  };

  // Refresh all tracked competitors across the routes that actually back this UI
  const refreshAllCompetitors = async () => {
    try {
      setRefreshing(true);
      setError("");
      setNotice("");

      const messages: string[] = [];
      let refreshedAnySource = false;
      let waitForInstagramCompletion = false;

      const hasInstagramCompetitors = competitors.some(
        (competitor) => competitor.auto_sync_enabled && competitor.platform.toLowerCase() === "instagram"
      );

      if (hasInstagramCompetitors) {
        const instagramResponse = await authFetch(`${API}/api/scraper/instagram/sync?background=1`, {
          method: "POST",
        });

        if (instagramResponse.ok) {
          const result = await instagramResponse.json();
          if (result.accepted) {
            messages.push(
              result.message || `Instagram scrape started in the background for ${result.total} competitors`
            );
            waitForInstagramCompletion = true;
          } else {
            messages.push(
              `Instagram scraped: ${result.success}/${result.total} competitors, ${result.posts_saved} posts cached`
            );
          }
          refreshedAnySource = true;
        } else {
          messages.push(`Instagram scrape failed: ${await getResponseMessage(instagramResponse)}`);
        }
      }

      const hasXCompetitors = competitors.some(
        (competitor) => competitor.auto_sync_enabled && competitor.platform.toLowerCase() === "x"
      );

      if (hasXCompetitors) {
        const xContentRefreshResponse = await authFetch(
          `${API}/api/content-intel/competitors/refresh?platform=x`,
          { method: "POST" }
        );

        if (xContentRefreshResponse.ok) {
          const result = await xContentRefreshResponse.json();
          messages.push(
            `X content refreshed: ${result.refreshed_competitors || 0}/${result.total_competitors || 0}`
          );
          refreshedAnySource = true;
        } else {
          messages.push(`X content refresh failed: ${await getResponseMessage(xContentRefreshResponse)}`);
        }
      }

      if (!refreshedAnySource) {
        setError(messages.join(" • ") || "No supported competitor refresh sources are available");
        return;
      }

      setNotice(messages.join(" • "));

      if (waitForInstagramCompletion) {
        const syncCompleted = await waitForInstagramSyncCompletion();
        if (!syncCompleted) {
          await refreshIntelligenceViews();
        }
      } else {
        await refreshIntelligenceViews();
      }
    } catch (error) {
      setError(`Error refreshing competitors: ${error}`);
    } finally {
      setRefreshing(false);
    }
  };

  const mergeScriptsById = (incoming: Script[], existing: Script[]) => {
    const merged = [...incoming, ...existing];
    const seen = new Set<number>();

    return merged.filter((script) => {
      if (script.id == null) return true;
      if (seen.has(script.id)) return false;
      seen.add(script.id);
      return true;
    });
  };

  const openGenerateScriptModal = (competitor?: Competitor | null) => {
    if (competitor) {
      setScriptForm((prev) => ({
        ...prev,
        competitor_id: competitor.id,
        platform: competitor.platform || prev.platform,
      }));
    }
    setShowGenerateScript(true);
  };

  const handleScriptCompetitorChange = (value: string) => {
    const competitorId = parseInt(value, 10) || 0;
    const selectedCompetitor = competitors.find((comp) => comp.id === competitorId);

    setScriptForm((prev) => ({
      ...prev,
      competitor_id: competitorId,
      platform: selectedCompetitor?.platform || prev.platform,
    }));
  };

  // Generate script
  const generateScript = async () => {
    if (!scriptForm.competitor_id) return;
    
    try {
      setSubmitting(true);
      setError("");
      const response = await authFetch(`${API}/api/content-intel/competitors/${scriptForm.competitor_id}/generate-script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform: scriptForm.platform,
          topic: scriptForm.topic.trim() || undefined,
          hook_style: scriptForm.hook_style || undefined,
          count: scriptForm.count,
        }),
      });

      if (response.ok) {
        const payload = await response.json();
        const generatedScripts = Array.isArray(payload) ? payload : [payload];
        setScripts((prev) => mergeScriptsById(generatedScripts, prev));
        setSelectedScriptId(generatedScripts[0]?.id ?? null);
        setScriptForm({ competitor_id: 0, platform: "instagram", topic: "", hook_style: "", count: 6 });
        setShowGenerateScript(false);
        setNotice(`Generated ${generatedScripts.length} competitor-driven script ideas.`);
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
      const response = await authFetch(`${API}/api/content-intel/competitors/scripts/${id}`, {
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
    existing.unshift({
      id: `competitor-script-${script.id || Date.now()}`,
      title: script.title,
      description: script.body_outline,
      stage: "scripted",
      platform,
      createdAt: script.created_at || new Date().toISOString(),
      hook: script.hook,
      views: script.predicted_views,
      source: "competitor_intel",
    });
    localStorage.setItem(key, JSON.stringify(existing));
    setNotice(`Saved script to ${formatPlatformLabel(platform)} content pipeline.`);
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

  const selectedScript = scripts.find((script) => script.id === selectedScriptId) || scripts[0] || null;

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

      {/* Status messages */}
      {notice && (
        <div className="mx-6 mt-3 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg">
          {notice}
        </div>
      )}

      {error && (
        <div className="mx-6 mt-3 px-3 py-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg">
          {error}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-6xl mx-auto">

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

                  {/* Competitor Detail Tabs */}
                  <div className="flex border-b border-warroom-border">
                    <button 
                      onClick={() => setCompetitorDetailTab("overview")}
                      className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                        competitorDetailTab === "overview" 
                          ? "border-warroom-accent text-warroom-accent" 
                          : "border-transparent text-warroom-muted hover:text-warroom-text"
                      }`}
                    >
                      Content Overview
                    </button>
                    <button 
                      onClick={() => setCompetitorDetailTab("dossier")}
                      className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                        competitorDetailTab === "dossier" 
                          ? "border-warroom-accent text-warroom-accent" 
                          : "border-transparent text-warroom-muted hover:text-warroom-text"
                      }`}
                    >
                      Dossier
                    </button>
                  </div>

                  {/* Content Overview Tab */}
                  {competitorDetailTab === "overview" && (
                    <>
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
                          <div
                            key={idx}
                            className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition cursor-pointer"
                            onClick={() => vid.id && setSelectedPostId(vid.id)}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <p className="text-sm text-warroom-text font-medium line-clamp-2 flex-1">{vid.title || "Untitled"}</p>
                              {vid.media_type && (vid.media_type === "reel" || vid.media_type === "video") && (
                                <Film size={12} className="text-pink-400 flex-shrink-0" />
                              )}
                              {vid.has_transcript && <span title="Has transcript"><FileText size={10} className="text-green-400 flex-shrink-0" /></span>}
                            </div>
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
                          <div
                            key={idx}
                            className="bg-warroom-surface border border-warroom-border rounded-xl p-5 hover:border-warroom-accent/20 transition cursor-pointer"
                            onClick={() => post.id && setSelectedPostId(post.id)}
                          >
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
                    </>
                  )}

                  {/* Dossier Tab */}
                  {competitorDetailTab === "dossier" && (
                    <DossierPanel competitorId={focusedCompetitor.id} bio={focusedCompetitor.bio} />
                  )}

                </div>
              ) : (
                /* GRID VIEW — all competitors */
                <>
                  {/* Sync Status Bar */}
                  <div className="flex items-center justify-between bg-warroom-surface border border-warroom-border rounded-xl px-4 py-2.5">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${syncing ? "bg-warroom-accent animate-pulse" : "bg-emerald-500"}`} />
                      <div>
                        <p className="text-xs text-warroom-text font-medium">
                          {syncing ? "Syncing competitors..." : "Competitor Intelligence"}
                        </p>
                        <p className="text-[10px] text-warroom-muted">
                          {syncResult ? syncResult : lastSyncTime ? `Last synced: ${lastSyncTime}` : "Not synced yet"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={async () => {
                          setSyncing(true);
                          setSyncResult(null);
                          try {
                            const resp = await authFetch(`${API}/api/content-intel/sync-all`, { method: "POST" });
                            if (resp.ok) {
                              setSyncResult("Sync started...");
                              // Poll for completion
                              const pollInterval = setInterval(async () => {
                                try {
                                  const statusResp = await authFetch(`${API}/api/content-intel/sync-all/status`);
                                  if (statusResp.ok) {
                                    const status = await statusResp.json();
                                    setSyncResult(status.message || "Syncing...");
                                    if (!status.running) {
                                      clearInterval(pollInterval);
                                      setSyncing(false);
                                      setLastSyncTime(new Date().toLocaleTimeString());
                                      await refreshIntelligenceViews();
                                    }
                                  }
                                } catch { /* ignore poll errors */ }
                              }, 3000);
                              // Safety timeout: stop polling after 5 minutes
                              setTimeout(() => { clearInterval(pollInterval); setSyncing(false); }, 300000);
                            } else {
                              setSyncResult("Sync failed to start");
                              setSyncing(false);
                            }
                          } catch {
                            setSyncResult("Sync error");
                            setSyncing(false);
                          }
                        }}
                        disabled={syncing}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-bg border border-warroom-border hover:bg-warroom-border/50 rounded-lg text-xs font-medium transition disabled:opacity-50"
                      >
                        <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
                        Sync All
                      </button>
                      <button onClick={() => setShowAddCompetitor(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition">
                        <Plus size={14} /> Add
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
                                <div className="flex items-center gap-2">
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[comp.platform] || "bg-gray-500/20 text-gray-400"}`}>{comp.platform}</span>
                                  {comp.last_auto_sync && (
                                    <span className="text-[9px] text-warroom-muted">
                                      Last synced: {timeAgo(comp.last_auto_sync)}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <button onClick={(e) => { e.stopPropagation(); deleteCompetitor(comp.id); }}
                              className="text-warroom-muted hover:text-red-400 transition">
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
              <p className="text-sm text-warroom-muted">Top-performing posts across all tracked competitors, re-ranked by live virality and engagement on every refresh.</p>
              
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
                        <div className="flex items-center gap-2">
                          {/* Video chunk timestamps */}
                          {(post.start_time !== undefined && post.end_time !== undefined) && (
                            <span className="text-warroom-accent bg-warroom-bg px-1.5 py-0.5 rounded text-[10px] font-mono">
                              {formatTime(post.start_time)}-{formatTime(post.end_time)}
                            </span>
                          )}
                          {post.timestamp && <span>{timeAgo(post.timestamp)}</span>}
                        </div>
                      </div>
                      
                      <div className="mt-2 bg-warroom-bg rounded px-2 py-1 flex items-center justify-between gap-2">
                        <span className="text-xs text-warroom-accent font-medium">Score: {post.engagement_score.toFixed(0)}</span>
                        <span className="text-[10px] text-orange-300">Virality: {post.virality_score.toFixed(1)}</span>
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
              <p className="text-sm text-warroom-muted">Opening hook language pulled from the current top-performing competitor posts.</p>
              
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
                  {hooks.map((hook, idx) => (
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
                        <span className="text-orange-300">Virality: {hook.virality_score.toFixed(1)}</span>
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
                <p className="text-sm text-warroom-muted">Generate hook-first script ideas from real competitor winners, then click any card to drill into the full script, metrics, and source evidence.</p>
                <button onClick={() => openGenerateScriptModal(focusedCompetitor)}
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
                <div className="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.9fr)] lg:items-start">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {scripts.map((script, idx) => {
                      const isSelected = script.id != null && script.id === selectedScriptId;
                      return (
                        <button
                          key={script.id ?? `${script.title}-${idx}`}
                          onClick={() => setSelectedScriptId(script.id ?? null)}
                          className={`text-left bg-warroom-surface border rounded-2xl p-4 transition hover:border-warroom-accent/40 ${
                            isSelected ? "border-warroom-accent shadow-lg shadow-warroom-accent/10" : "border-warroom-border"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3 mb-3">
                            <div>
                              <div className="flex items-center gap-2 mb-2">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[script.platform] || "bg-gray-500/20 text-gray-400"}`}>{script.platform}</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${ALIGNMENT_STYLES[script.business_alignment_label] || ALIGNMENT_STYLES.Low}`}>{script.business_alignment_label} alignment</span>
                              </div>
                              <h4 className="font-semibold text-sm leading-snug mb-1">{script.title}</h4>
                              <p className="text-xs text-warroom-accent line-clamp-2">🪝 {script.hook}</p>
                            </div>
                            {script.id != null && (
                              <button
                                onClick={(event) => {
                                  event.stopPropagation();
                                  deleteScript(script.id!);
                                }}
                                className="text-warroom-muted hover:text-red-400 transition"
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>

                          <p className="text-xs text-warroom-muted line-clamp-3 mb-4">{script.body_outline}</p>

                          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                            <div className="bg-warroom-bg rounded-lg px-3 py-2">
                              <p className="text-[10px] text-warroom-muted mb-1">Potential Views</p>
                              <p className="font-semibold text-warroom-text">{formatNum(script.predicted_views)}</p>
                            </div>
                            <div className="bg-warroom-bg rounded-lg px-3 py-2">
                              <p className="text-[10px] text-warroom-muted mb-1">Pred. Engagement</p>
                              <p className="font-semibold text-warroom-text">{formatNum(Math.round(script.predicted_engagement))}</p>
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-warroom-muted gap-2">
                            <span>ER {formatPercent(script.predicted_engagement_rate, 2)}</span>
                            <span>Virality {script.virality_score.toFixed(1)}</span>
                            <span>{script.created_at ? timeAgo(script.created_at) : "Just now"}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 lg:sticky lg:top-6">
                    {selectedScript ? (
                      <div className="space-y-5">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2 mb-2">
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[selectedScript.platform] || "bg-gray-500/20 text-gray-400"}`}>{selectedScript.platform}</span>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded border ${ALIGNMENT_STYLES[selectedScript.business_alignment_label] || ALIGNMENT_STYLES.Low}`}>{selectedScript.business_alignment_label} alignment</span>
                              {selectedScript.estimated_duration && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-warroom-bg text-warroom-muted">{selectedScript.estimated_duration}</span>
                              )}
                            </div>
                            <h3 className="text-base font-semibold leading-snug">{selectedScript.title}</h3>
                            <p className="text-sm text-warroom-accent mt-2">🪝 {selectedScript.hook}</p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div className="bg-warroom-bg rounded-xl p-3">
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1">Potential Views</p>
                            <p className="font-semibold">{formatNum(selectedScript.predicted_views)}</p>
                          </div>
                          <div className="bg-warroom-bg rounded-xl p-3">
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1">Engagement Rate</p>
                            <p className="font-semibold">{formatPercent(selectedScript.predicted_engagement_rate, 2)}</p>
                          </div>
                          <div className="bg-warroom-bg rounded-xl p-3">
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1">Pred. Engagement</p>
                            <p className="font-semibold">{formatNum(Math.round(selectedScript.predicted_engagement))}</p>
                          </div>
                          <div className="bg-warroom-bg rounded-xl p-3">
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1">Virality Score</p>
                            <p className="font-semibold">{selectedScript.virality_score.toFixed(1)}</p>
                          </div>
                        </div>

                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Business Message Alignment</p>
                          <div className="bg-warroom-bg rounded-xl p-3 border border-warroom-border">
                            <p className="text-sm font-medium mb-1">{selectedScript.business_alignment_label} • {selectedScript.business_alignment_score.toFixed(1)}/100</p>
                            <p className="text-xs text-warroom-muted">{selectedScript.business_alignment_reason}</p>
                          </div>
                        </div>

                        {selectedScript.source_competitors.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Source Competitors</p>
                            <div className="flex flex-wrap gap-2">
                              {selectedScript.source_competitors.map((sourceCompetitor) => (
                                <span key={sourceCompetitor} className="px-2.5 py-1 rounded-full bg-warroom-bg text-xs text-warroom-text border border-warroom-border">
                                  @{sourceCompetitor}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Script</p>
                          <div className="bg-warroom-bg rounded-xl p-4 border border-warroom-border space-y-3">
                            <p className="text-sm whitespace-pre-line">{selectedScript.body_outline}</p>
                            <div className="pt-3 border-t border-warroom-border">
                              <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1">CTA</p>
                              <p className="text-sm">{selectedScript.cta}</p>
                            </div>
                          </div>
                        </div>

                        {selectedScript.scene_map.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Scene Map</p>
                            <div className="space-y-2">
                              {selectedScript.scene_map.map((scene, idx) => (
                                <div key={`${scene.scene}-${idx}`} className="bg-warroom-bg rounded-xl p-3 border border-warroom-border">
                                  <p className="text-xs font-semibold mb-1">{scene.scene}</p>
                                  <p className="text-xs text-warroom-text mb-1">{scene.direction}</p>
                                  <p className="text-[11px] text-warroom-muted">Goal: {scene.goal}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedScript.similar_videos.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Similar Competitor Videos</p>
                            <div className="space-y-2">
                              {selectedScript.similar_videos.map((video, idx) => (
                                <div key={`${video.source_url || video.hook}-${idx}`} className="bg-warroom-bg rounded-xl p-3 border border-warroom-border">
                                  <div className="flex items-center justify-between gap-2 mb-1">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[video.platform] || "bg-gray-500/20 text-gray-400"}`}>{video.platform}</span>
                                      <span className="text-xs text-warroom-muted truncate">@{video.competitor_handle}</span>
                                    </div>
                                    <span className="text-[11px] text-warroom-accent">Score {video.engagement_score.toFixed(0)}</span>
                                  </div>
                                  <p className="text-xs text-warroom-text">{video.hook || "Reference post"}</p>
                                  {video.source_url && (
                                    <a href={video.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-[11px] text-warroom-muted hover:text-warroom-accent transition">
                                      <ExternalLink size={11} /> View source
                                    </a>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="flex flex-wrap gap-2 pt-1">
                          <button
                            onClick={() => saveScriptToPlatform(selectedScript, selectedScript.platform)}
                            className="flex items-center gap-1.5 px-3 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition"
                          >
                            <Save size={12} /> Save to {formatPlatformLabel(selectedScript.platform)}
                          </button>
                          {SCRIPT_SAVE_PLATFORMS.filter((platform) => platform !== selectedScript.platform).slice(0, 2).map((platform) => (
                            <button
                              key={platform}
                              onClick={() => saveScriptToPlatform(selectedScript, platform)}
                              className="flex items-center gap-1 px-2.5 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-xs hover:border-warroom-accent/30 transition"
                            >
                              <Save size={12} /> Save to {formatPlatformLabel(platform)}
                            </button>
                          ))}
                        </div>

                        {selectedScript.source_post_url && (
                          <a href={selectedScript.source_post_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs text-warroom-muted hover:text-warroom-accent transition">
                            <ExternalLink size={12} /> View source post
                          </a>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-12 text-warroom-muted">
                        <BookOpen size={32} className="mx-auto mb-3 opacity-20" />
                        <p className="text-sm">Select a script idea to inspect the full detail.</p>
                      </div>
                    )}
                  </div>
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
              <h3 className="text-lg font-semibold">Generate Competitor-Driven Scripts</h3>
              <button onClick={() => setShowGenerateScript(false)} className="text-warroom-muted hover:text-warroom-text">
                <X size={20} />
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-xs text-warroom-muted">We’ll use the competitor’s latest winning posts, hook language, and engagement patterns to generate multiple script ideas. Topic is optional if you want to steer the angle.</p>
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Competitor</label>
                <select 
                  value={scriptForm.competitor_id} 
                  onChange={e => handleScriptCompetitorChange(e.target.value)}
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
                <label className="text-xs text-warroom-muted block mb-1">Topic Override (optional)</label>
                <input 
                  type="text" 
                  value={scriptForm.topic} 
                  onChange={e => setScriptForm({ ...scriptForm, topic: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" 
                  placeholder="Leave blank to let current competitor trends drive the angle" 
                />
              </div>

              <div>
                <label className="text-xs text-warroom-muted block mb-1">How many ideas?</label>
                <select
                  value={scriptForm.count}
                  onChange={e => setScriptForm({ ...scriptForm, count: parseInt(e.target.value, 10) || 6 })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                >
                  {[3, 6, 9].map((count) => <option key={count} value={count}>{count} ideas</option>)}
                </select>
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
              <button onClick={generateScript} disabled={!scriptForm.competitor_id || submitting}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2">
                {submitting ? <><Loader2 size={14} className="animate-spin" /> Generating...</> : "Generate Ideas"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Post Detail Modal */}
      {selectedPostId && (
        <PostDetailModal
          postId={selectedPostId}
          onClose={() => setSelectedPostId(null)}
        />
      )}
    </div>
  );
}