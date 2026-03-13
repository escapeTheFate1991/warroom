"use client";

import { useState, useEffect } from "react";
import { Search, Plus, X, Flame, Copy, Check, User, TrendingUp, Eye, Target, Zap, BookOpen, ExternalLink, Trash2, Loader2, RefreshCw, Play, Save, Edit3, ArrowLeft, Heart, MessageCircle, EyeIcon, BarChart3, Hash, Users, Sparkles, ShoppingBag, Film, FileText, ChevronDown, ChevronRight } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import PostDetailModal from "./PostDetailModal";
import ScrollTabs from "@/components/ui/ScrollTabs";


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
  id?: number;
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
  competitor_id?: number;
  competitor_handle?: string;
  platform?: string;
  post_url?: string;
  title: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  virality_score: number;
  posted_at?: string;
  hook?: string;
  media_type?: string;
  has_transcript?: boolean;
  has_comments?: boolean;
  analysis?: TopVideoAnalysis | null;
}

interface TopVideoSection {
  text?: string;
  start?: number;
  end?: number;
}

interface TopVideoStoryboardScene {
  scene: string;
  direction: string;
  goal: string;
  timing?: string | null;
}

interface TopVideoProductionSpec {
  creative_angle: string;
  pacing_label: string;
  pacing_notes: string;
  scene_pattern: string[];
  production_notes: string[];
  cta_strategy: string;
}

interface TopVideoAnalysis {
  content_format?: string | null;
  duration_seconds: number;
  structure_score: number;
  hook_type?: string | null;
  hook_strength: number;
  cta_type?: string | null;
  cta_phrase?: string | null;
  pacing_label: string;
  pacing_reason: string;
  key_points: string[];
  scene_pattern: string[];
  hook_window?: TopVideoSection;
  value_window?: TopVideoSection;
  cta_window?: TopVideoSection;
  storyboard: TopVideoStoryboardScene[];
  production_spec: TopVideoProductionSpec;
}

interface InstagramAdviceItem {
  title: string;
  detail: string;
  metric?: string | null;
  category?: string | null;
}

interface ProfilePostSummary {
  shortcode: string;
  caption_preview: string;
  hook: string;
  likes: number;
  comments: number;
  views: number;
  media_type: string;
  posted_at?: string | null;
  engagement_score: number;
}

interface InstagramProfileAdvice {
  connected: boolean;
  platform: string;
  username?: string | null;
  status: string;
  summary: string;
  follower_count: number;
  following_count: number;
  post_count: number;
  last_synced?: string | null;
  days_analyzed: number;
  avg_engagement_rate: number;
  avg_reach: number;
  avg_profile_views: number;
  avg_video_views: number;
  total_link_clicks: number;
  net_followers: number;
  bio?: string | null;
  external_url?: string | null;
  bio_links?: { url: string; title?: string }[];
  profile_pic_url?: string | null;
  is_verified?: boolean;
  category?: string | null;
  posting_frequency?: string | null;
  recent_posts?: ProfilePostSummary[];
  recommendations: InstagramAdviceItem[];
}

interface AudienceQuestion {
  question: string;
  likes: number;
}

interface AudiencePainPoint {
  pain: string;
  likes: number;
}

interface AudienceTheme {
  theme: string;
  count: number;
}

interface AudienceProductMention {
  product: string;
  count: number;
}

interface AudienceCommenter {
  username: string;
  count: number;
}

interface AudienceIntel {
  posts_analyzed: number;
  comments_analyzed: number;
  sentiment: string;
  sentiment_breakdown: Record<string, number>;
  sentiment_percentages: Record<string, number>;
  questions: AudienceQuestion[];
  pain_points: AudiencePainPoint[];
  themes: AudienceTheme[];
  product_mentions: AudienceProductMention[];
  top_commenters: AudienceCommenter[];
  engagement_quality: Record<string, number>;
  content_formats: Record<string, number>;
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

const CONTENT_TIMEFRAME_OPTIONS = [
  { label: "Day", days: 1 },
  { label: "Week", days: 7 },
  { label: "Month", days: 30 },
] as const;

const AUDIENCE_SENTIMENT_COLORS: Record<string, string> = {
  very_positive: "text-green-400",
  positive: "text-green-300",
  neutral: "text-warroom-muted",
  negative: "text-orange-400",
  very_negative: "text-red-400",
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

function titleizeToken(value?: string | null): string {
  if (!value) return "Unknown";
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTimeWindow(section?: TopVideoSection | null): string | null {
  if (!section) return null;
  const start = formatTime(section.start);
  const end = formatTime(section.end);
  if (!start || !end) return null;
  return start === end ? start : `${start}-${end}`;
}

function TopVideoInsights({ video, compact = false }: { video: TopVideoItem; compact?: boolean }) {
  const analysis = video.analysis;
  if (!analysis) return null;

  const hasInsights = Boolean(
    analysis.scene_pattern?.length ||
    analysis.key_points?.length ||
    analysis.storyboard?.length ||
    analysis.pacing_reason ||
    analysis.cta_phrase ||
    analysis.production_spec?.production_notes?.length
  );

  if (!hasInsights) return null;

  const keyPoints = (analysis.key_points || []).slice(0, compact ? 2 : 4);
  const storyboard = (analysis.storyboard || []).slice(0, compact ? 3 : analysis.storyboard.length);
  const structurePct = analysis.structure_score > 0 ? formatPercent(analysis.structure_score * 100, 0) : null;
  const hookTiming = formatTimeWindow(analysis.hook_window);
  const ctaText = analysis.cta_phrase || analysis.cta_window?.text;

  return (
    <div className="mt-3 space-y-3 border-t border-warroom-border/70 pt-3">
      <div className="flex flex-wrap gap-1.5 text-[10px]">
        <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-1 text-amber-300">
          {titleizeToken(analysis.pacing_label)} pace
        </span>
        {analysis.content_format && (
          <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-2 py-1 text-sky-300">
            {titleizeToken(analysis.content_format)}
          </span>
        )}
        {analysis.duration_seconds > 0 && (
          <span className="rounded-full border border-warroom-border bg-warroom-surface px-2 py-1 text-warroom-muted">
            {formatTime(analysis.duration_seconds)} runtime
          </span>
        )}
        {structurePct && (
          <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-emerald-300">
            {structurePct} structure
          </span>
        )}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-warroom-text">
            <Zap size={12} className="text-amber-400" />
            Pacing + pattern
          </div>
          <p className="text-[11px] leading-5 text-warroom-muted">{analysis.pacing_reason}</p>
          <div className="flex flex-wrap gap-1.5">
            {(analysis.scene_pattern || []).map((pattern, idx) => (
              <span key={`${pattern}-${idx}`} className="rounded-full bg-warroom-bg px-2 py-1 text-[10px] text-warroom-text border border-warroom-border">
                {pattern}
              </span>
            ))}
          </div>
          {hookTiming && analysis.hook_type && (
            <p className="text-[10px] text-warroom-muted">
              Hook: <span className="text-warroom-text">{titleizeToken(analysis.hook_type)}</span> · {hookTiming}
            </p>
          )}
        </div>

        {(keyPoints.length > 0 || ctaText) && (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-warroom-text">
              <Target size={12} className="text-warroom-accent" />
              Core beats
            </div>
            {keyPoints.length > 0 && (
              <ul className="space-y-1.5 text-[11px] text-warroom-muted">
                {keyPoints.map((point, idx) => (
                  <li key={`${idx}-${point.slice(0, 16)}`} className="flex gap-2">
                    <span className="mt-[3px] h-1.5 w-1.5 rounded-full bg-warroom-accent flex-shrink-0" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            )}
            {ctaText && (
              <p className="text-[11px] leading-5 text-warroom-muted">
                CTA: <span className="text-warroom-text">{ctaText}</span>
              </p>
            )}
          </div>
        )}
      </div>

      {storyboard.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-warroom-text">
            <BookOpen size={12} className="text-pink-400" />
            Storyboard groundwork
          </div>
          <div className={`grid gap-2 ${compact ? "grid-cols-1" : "grid-cols-1 xl:grid-cols-2"}`}>
            {storyboard.map((scene, idx) => (
              <div key={`${scene.scene}-${idx}`} className="rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <p className="text-[11px] font-medium text-warroom-text">{scene.scene}</p>
                  {scene.timing && <span className="text-[10px] text-warroom-muted">{scene.timing}</span>}
                </div>
                <p className="text-[10px] text-warroom-muted leading-5">{scene.direction}</p>
                {!compact && <p className="mt-1 text-[10px] text-pink-300">Goal: {scene.goal}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {!compact && analysis.production_spec && (
        <div className="rounded-xl border border-warroom-border bg-warroom-bg/60 p-3 space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-warroom-text">
            <Sparkles size={12} className="text-emerald-400" />
            Generation-ready spec
          </div>
          {analysis.production_spec.creative_angle && (
            <p className="text-[11px] text-warroom-muted leading-5">
              Angle: <span className="text-warroom-text">{analysis.production_spec.creative_angle}</span>
            </p>
          )}
          <p className="text-[11px] text-warroom-muted leading-5">
            CTA strategy: <span className="text-warroom-text">{analysis.production_spec.cta_strategy}</span>
          </p>
          {analysis.production_spec.production_notes?.length > 0 && (
            <ul className="space-y-1.5 text-[11px] text-warroom-muted">
              {analysis.production_spec.production_notes.map((note, idx) => (
                <li key={`${idx}-${note.slice(0, 16)}`} className="flex gap-2">
                  <span className="mt-[3px] h-1.5 w-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
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
  const [activeTab, setActiveTab] = useState<"competitors" | "top-content" | "hooks" | "scripts" | "profile-intel">("competitors");
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [topContent, setTopContent] = useState<TopContentPost[]>([]);
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedScriptId, setSelectedScriptId] = useState<number | null>(null);
  const [expandedScriptIdx, setExpandedScriptIdx] = useState<number | null>(null);
  const [expandedCompetitor, setExpandedCompetitor] = useState<number | null>(null);
  const [focusedCompetitor, setFocusedCompetitor] = useState<Competitor | null>(null);
  const [competitorPosts, setCompetitorPosts] = useState<CompetitorPost[]>([]);
  const [competitorDetailTab, setCompetitorDetailTab] = useState<"overview" | "dossier" | "audience">("overview");
  const [audienceIntel, setAudienceIntel] = useState<any>(null);
  const [loadingAudienceIntel, setLoadingAudienceIntel] = useState(false);

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
  const [globalAudienceIntel, setGlobalAudienceIntel] = useState<AudienceIntel | null>(null);
  const [loadingGlobalAudienceIntel, setLoadingGlobalAudienceIntel] = useState(false);
  const [focusedTopVideos, setFocusedTopVideos] = useState<TopVideoItem[]>([]);
  const [aggregateTopVideos, setAggregateTopVideos] = useState<TopVideoItem[]>([]);
  const [instagramAdvice, setInstagramAdvice] = useState<InstagramProfileAdvice | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null);
  const [expandedPostId, setExpandedPostId] = useState<number | null>(null);
  const [expandedPostData, setExpandedPostData] = useState<any>(null);
  const [expandedPostTab, setExpandedPostTab] = useState<"overview" | "transcript" | "audience">("overview");
  const [loadingFocusedTopVideos, setLoadingFocusedTopVideos] = useState(false);
  const [loadingAggregateTopVideos, setLoadingAggregateTopVideos] = useState(false);
  const [loadingInstagramAdvice, setLoadingInstagramAdvice] = useState(false);
  const [hashtags, setHashtags] = useState<HashtagItem[]>([]);
  const [loadingHashtags, setLoadingHashtags] = useState(false);
  const [contentTimeframeDays, setContentTimeframeDays] = useState<number>(30);

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
      const response = await authFetch(`${API}/api/content-intel/competitors/top-content?days=${contentTimeframeDays}`);
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
      const response = await authFetch(`${API}/api/content-intel/competitors/hooks?days=${contentTimeframeDays}`);
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

  // Fetch aggregated audience intelligence across all competitors
  const fetchGlobalAudienceIntel = async () => {
    try {
      setLoadingGlobalAudienceIntel(true);
      const response = await authFetch(`${API}/api/content-intel/competitors/audience-intel`);
      if (response.ok) {
        setGlobalAudienceIntel(await response.json());
      }
    } catch (err) {
      console.error("Failed to fetch global audience intelligence", err);
    } finally {
      setLoadingGlobalAudienceIntel(false);
    }
  };

  const fetchInstagramAdvice = async () => {
    try {
      setLoadingInstagramAdvice(true);
      const response = await authFetch(`${API}/api/content-intel/instagram/account-advice`);
      if (response.ok) {
        setInstagramAdvice(await response.json());
      } else {
        setInstagramAdvice(null);
      }
    } catch (err) {
      setInstagramAdvice(null);
    } finally {
      setLoadingInstagramAdvice(false);
    }
  };

  const fetchAggregateTopVideos = async () => {
    try {
      setLoadingAggregateTopVideos(true);
      const response = await authFetch(`${API}/api/content-intel/competitors/top-videos?days=${contentTimeframeDays}&limit=5`);
      if (response.ok) {
        setAggregateTopVideos(await response.json());
      } else {
        setAggregateTopVideos([]);
      }
    } catch (err) {
      setAggregateTopVideos([]);
    } finally {
      setLoadingAggregateTopVideos(false);
    }
  };

  // Fetch top videos for a focused competitor
  const fetchFocusedTopVideos = async (competitorId: number) => {
    try {
      setLoadingFocusedTopVideos(true);
      const response = await authFetch(`${API}/api/content-intel/competitors/${competitorId}/top-videos?limit=5`);
      if (response.ok) {
        setFocusedTopVideos(await response.json());
      } else {
        setFocusedTopVideos([]);
      }
    } catch (err) {
      setFocusedTopVideos([]);
    } finally {
      setLoadingFocusedTopVideos(false);
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
      fetchFocusedTopVideos(competitorId),
      fetchHashtags(competitorId),
    ]);
  };

  const refreshIntelligenceViews = async () => {
    const nextCompetitors = await fetchCompetitors();
    await Promise.all([
      fetchGlobalAudienceIntel(),
      fetchInstagramAdvice(),
      fetchAggregateTopVideos(),
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
    fetchGlobalAudienceIntel();
    fetchInstagramAdvice();
    fetchAggregateTopVideos();
    fetchScripts();
  }, []);

  useEffect(() => {
    fetchTopContent();
    fetchHooks();
    fetchAggregateTopVideos();
  }, [contentTimeframeDays]);

  // Fetch active tab data on tab change
  useEffect(() => {
    switch (activeTab) {
      case "competitors":
        fetchCompetitors();
        fetchGlobalAudienceIntel();
        fetchInstagramAdvice();
        fetchAggregateTopVideos();
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
      case "profile-intel":
        fetchInstagramAdvice();
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

  // Generate script (aggregated from all competitors)
  const generateScript = async () => {
    try {
      setSubmitting(true);
      setError("");
      const response = await authFetch(`${API}/api/content-intel/generate-scripts`, {
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
        setExpandedScriptIdx(null);
        setScriptForm({ competitor_id: 0, platform: "instagram", topic: "", hook_style: "", count: 6 });
        setShowGenerateScript(false);
        setNotice(`Generated ${generatedScripts.length} script ideas from all competitors.`);
      } else {
        const error = await response.json();
        setError(`Failed to generate scripts: ${error.detail || response.statusText}`);
      }
    } catch (error) {
      setError(`Error generating scripts: ${error}`);
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

  // Focus on a competitor - switches from grid to detail view
  const focusOnCompetitor = (comp: Competitor) => {
    setFocusedCompetitor(comp);
    setCompetitorPosts([]);
    setFocusedTopVideos([]);
    setHashtags([]);
    setAudienceIntel(null);
    fetchCompetitorPosts(comp.id);
    fetchFocusedTopVideos(comp.id);
    fetchHashtags(comp.id);
  };

  // Back to grid
  const unfocusCompetitor = () => {
    setFocusedCompetitor(null);
    setCompetitorPosts([]);
    setFocusedTopVideos([]);
    setHashtags([]);
  };

  const TABS = [
    { id: "competitors" as const, label: "Competitors", icon: Target, count: competitors.length },
    { id: "top-content" as const, label: "Top Content", icon: TrendingUp, count: topContent.length },
    { id: "hooks" as const, label: "Hooks", icon: Zap, count: hooks.length },
    { id: "scripts" as const, label: "Scripts", icon: BookOpen, count: scripts.length },
    { id: "profile-intel" as const, label: "Profile Intel", icon: Sparkles },
  ];

  const selectedScript = scripts.find((script) => script.id === selectedScriptId) || scripts[0] || null;
  const selectedTimeframeLabel = CONTENT_TIMEFRAME_OPTIONS.find((option) => option.days === contentTimeframeDays)?.label || `${contentTimeframeDays}d`;

  const renderTimeframeControls = () => (
    <div className="inline-flex items-center gap-1 rounded-xl border border-warroom-border bg-warroom-surface p-1">
      {CONTENT_TIMEFRAME_OPTIONS.map((option) => {
        const active = option.days === contentTimeframeDays;
        return (
          <button
            key={option.days}
            type="button"
            onClick={() => setContentTimeframeDays(option.days)}
            className={`px-3 py-1.5 text-xs rounded-lg transition ${active ? "bg-warroom-accent text-black font-medium" : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg"}`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Eye size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Competitor Intelligence</h2>
      </div>

      {/* Sub-tabs */}
      <ScrollTabs
        tabs={TABS.map(t => ({ id: t.id, label: t.label, icon: t.icon, count: t.count }))}
        active={activeTab}
        onChange={(id) => setActiveTab(id as typeof activeTab)}
      />

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

                  {loadingGlobalAudienceIntel ? (
                    <div className="flex items-center gap-2 text-sm text-warroom-muted py-4">
                      <Loader2 size={16} className="animate-spin" /> Analyzing audience…
                    </div>
                  ) : globalAudienceIntel ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="bg-warroom-bg border border-warroom-border rounded-xl p-3">
                          <p className="text-lg font-bold text-warroom-text">{globalAudienceIntel.posts_analyzed}</p>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Posts analyzed</p>
                        </div>
                        <div className="bg-warroom-bg border border-warroom-border rounded-xl p-3">
                          <p className="text-lg font-bold text-warroom-text">{globalAudienceIntel.comments_analyzed.toLocaleString()}</p>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Comments</p>
                        </div>
                        <div className="bg-warroom-bg border border-warroom-border rounded-xl p-3">
                          <p className={`text-lg font-bold capitalize ${AUDIENCE_SENTIMENT_COLORS[globalAudienceIntel.sentiment] || "text-warroom-text"}`}>
                            {globalAudienceIntel.sentiment.replace(/_/g, " ")}
                          </p>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Sentiment</p>
                        </div>
                        <div className="bg-warroom-bg border border-warroom-border rounded-xl p-3">
                          <p className="text-lg font-bold text-warroom-accent">{globalAudienceIntel.sentiment_percentages.positive || 0}%</p>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Positive</p>
                        </div>
                      </div>

                      {Object.keys(globalAudienceIntel.content_formats || {}).length > 0 && (
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">Content Formats</p>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(globalAudienceIntel.content_formats).map(([format, count]) => (
                              <span key={format} className="px-2.5 py-1 bg-warroom-bg border border-warroom-border text-xs rounded-full text-warroom-text">
                                {format.replace(/_/g, " ")} <span className="text-warroom-muted">({count})</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {globalAudienceIntel.themes.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">Discussion Themes</p>
                            <div className="flex flex-wrap gap-2">
                              {globalAudienceIntel.themes.slice(0, 12).map((theme, i) => (
                                <span key={i} className="px-2.5 py-1 bg-warroom-accent/10 text-warroom-accent text-xs rounded-full font-medium">
                                  {theme.theme} ({theme.count})
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {globalAudienceIntel.product_mentions.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">Products Mentioned</p>
                            <div className="flex flex-wrap gap-2">
                              {globalAudienceIntel.product_mentions.slice(0, 10).map((product, i) => (
                                <span key={i} className="px-2.5 py-1 bg-purple-400/10 text-purple-400 text-xs rounded-full font-medium">
                                  {product.product} ({product.count})
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {globalAudienceIntel.questions.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">Top Questions</p>
                            <div className="space-y-1.5">
                              {globalAudienceIntel.questions.slice(0, 4).map((question, i) => (
                                <div key={i} className="flex items-start gap-2 rounded-lg border border-blue-400/10 bg-blue-400/5 px-3 py-2">
                                  <Sparkles size={12} className="text-blue-400 flex-shrink-0 mt-0.5" />
                                  <p className="text-xs text-warroom-text flex-1">{question.question}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {globalAudienceIntel.pain_points.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">Pain Points</p>
                            <div className="space-y-1.5">
                              {globalAudienceIntel.pain_points.slice(0, 4).map((painPoint, i) => (
                                <div key={i} className="flex items-start gap-2 rounded-lg border border-red-400/10 bg-red-400/5 px-3 py-2">
                                  <Sparkles size={12} className="text-red-400 flex-shrink-0 mt-0.5" />
                                  <p className="text-xs text-warroom-text flex-1">{painPoint.pain}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted py-2">No audience data yet. Refresh competitor data to generate analysis.</p>
                  )}
                </div>
              )}

              {!focusedCompetitor && (
                <div>
                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                      <div className="flex items-center gap-2">
                        <Film size={18} className="text-pink-400" />
                        <div>
                          <h3 className="text-sm font-semibold">Top Competitor Videos</h3>
                          <p className="text-xs text-warroom-muted">One top video-style post per leading competitor for the selected window.</p>
                        </div>
                      </div>
                      {renderTimeframeControls()}
                    </div>

                    {loadingAggregateTopVideos ? (
                      <div className="flex items-center gap-2 text-sm text-warroom-muted py-6">
                        <Loader2 size={16} className="animate-spin" /> Ranking top competitor videos…
                      </div>
                    ) : aggregateTopVideos.length === 0 ? (
                      <p className="text-xs text-warroom-muted py-4">No competitor videos available for this timeframe yet.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {aggregateTopVideos.map((vid, idx) => (
                          <div
                            key={`${vid.competitor_id || idx}-${vid.id || idx}`}
                            className="bg-warroom-bg border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition cursor-pointer"
                            onClick={() => vid.id && setSelectedPostId(vid.id)}
                          >
                            <div className="flex items-start justify-between gap-3 mb-2">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-[10px] uppercase tracking-wider text-warroom-muted">{vid.competitor_handle ? `@${vid.competitor_handle}` : "Competitor"}</span>
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-pink-500/10 text-pink-400">{formatPlatformLabel(vid.platform || "instagram")}</span>
                                </div>
                                <p className="text-sm text-warroom-text font-medium line-clamp-2">{vid.title || "Untitled"}</p>
                              </div>
                              {(vid.media_type === "reel" || vid.media_type === "video") && <Film size={12} className="text-pink-400 flex-shrink-0" />}
                            </div>

                            {vid.hook && <p className="text-xs text-warroom-accent mb-2 line-clamp-2">🪝 {vid.hook}</p>}

                            <div className="grid grid-cols-4 gap-2 text-center mb-3">
                              <div className="rounded-lg border border-warroom-border bg-warroom-surface px-2 py-2">
                                <p className="text-xs font-semibold text-warroom-text">{formatNum(vid.likes)}</p>
                                <p className="text-[10px] text-warroom-muted">Likes</p>
                              </div>
                              <div className="rounded-lg border border-warroom-border bg-warroom-surface px-2 py-2">
                                <p className="text-xs font-semibold text-warroom-text">{formatNum(vid.comments)}</p>
                                <p className="text-[10px] text-warroom-muted">Comments</p>
                              </div>
                              <div className="rounded-lg border border-warroom-border bg-warroom-surface px-2 py-2">
                                <p className="text-xs font-semibold text-warroom-accent">{vid.engagement_score.toFixed(0)}</p>
                                <p className="text-[10px] text-warroom-muted">Engage</p>
                              </div>
                              <div className="rounded-lg border border-warroom-border bg-warroom-surface px-2 py-2">
                                <p className="text-xs font-semibold text-pink-400">{vid.virality_score.toFixed(0)}</p>
                                <p className="text-[10px] text-warroom-muted">Virality</p>
                              </div>
                            </div>

                            <div className="flex items-center justify-between text-[10px] text-warroom-muted">
                              <div className="flex items-center gap-2">
                                {vid.posted_at && <span>{timeAgo(vid.posted_at)}</span>}
                                {vid.has_transcript && <span className="text-emerald-400">Transcript</span>}
                              </div>
                              {vid.post_url && (
                                <a
                                  href={vid.post_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-warroom-muted hover:text-warroom-accent transition"
                                  onClick={(event) => event.stopPropagation()}
                                >
                                  <ExternalLink size={12} />
                                </a>
                              )}
                            </div>

                            <TopVideoInsights video={vid} compact />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* FOCUSED VIEW - single competitor detail */}
              {focusedCompetitor ? (
                <div className="space-y-4">
                  {/* Back button + competitor header */}
                  <div className="flex flex-wrap items-center gap-2">
                    <button onClick={unfocusCompetitor}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-bg border border-warroom-border hover:bg-warroom-surface rounded-lg text-xs font-medium transition">
                      <ArrowLeft size={14} /> Back
                    </button>
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <div className="w-9 h-9 rounded-full bg-warroom-accent/10 flex items-center justify-center text-base font-bold text-warroom-accent flex-shrink-0">
                        {focusedCompetitor.handle.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-base font-semibold truncate">@{focusedCompetitor.handle}</h3>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[focusedCompetitor.platform] || "bg-gray-500/20 text-gray-400"}`}>{focusedCompetitor.platform}</span>
                          {focusedCompetitor.posting_frequency && (
                            <span className="text-[11px] text-warroom-muted">{focusedCompetitor.posting_frequency}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <a href={`https://instagram.com/${focusedCompetitor.handle}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 px-2.5 py-1.5 bg-pink-500/10 text-pink-400 hover:bg-pink-500/20 rounded-lg text-[11px] font-medium transition flex-shrink-0">
                      <ExternalLink size={12} /> Profile
                    </a>
                  </div>

                  {/* Stats bar - responsive grid */}
                  <div className="grid grid-cols-4 gap-2">
                    <div className="bg-warroom-surface border border-warroom-border rounded-lg p-2.5 text-center">
                      <p className="text-lg sm:text-xl font-bold text-warroom-text">{formatNum(focusedCompetitor.followers)}</p>
                      <p className="text-[10px] text-warroom-muted mt-0.5">Followers</p>
                    </div>
                    <div className="bg-warroom-surface border border-warroom-border rounded-lg p-2.5 text-center">
                      <p className="text-lg sm:text-xl font-bold text-warroom-text">{formatNum(focusedCompetitor.following)}</p>
                      <p className="text-[10px] text-warroom-muted mt-0.5">Following</p>
                    </div>
                    <div className="bg-warroom-surface border border-warroom-border rounded-lg p-2.5 text-center">
                      <p className="text-lg sm:text-xl font-bold text-warroom-text">{formatNum(focusedCompetitor.post_count)}</p>
                      <p className="text-[10px] text-warroom-muted mt-0.5">Posts</p>
                    </div>
                    <div className="bg-warroom-surface border border-warroom-border rounded-lg p-2.5 text-center">
                      <p className="text-lg sm:text-xl font-bold text-warroom-accent">{focusedCompetitor.avg_engagement_rate.toFixed(1)}%</p>
                      <p className="text-[10px] text-warroom-muted mt-0.5">Engage</p>
                    </div>
                  </div>

                  {/* Competitor Detail Tabs */}
                  <ScrollTabs
                    tabs={[
                      { id: "overview", label: "Content Overview" },
                      { id: "dossier", label: "Dossier" },
                      { id: "audience", label: "Audience Intel" },
                    ]}
                    active={competitorDetailTab}
                    onChange={(id) => {
                      setCompetitorDetailTab(id as any);
                      if (id === "audience" && !audienceIntel && focusedCompetitor) {
                        setLoadingAudienceIntel(true);
                        authFetch(`${API}/api/content-intel/competitors/${focusedCompetitor.id}/audience-intel`)
                          .then(r => r.ok ? r.json() : null)
                          .then(data => { if (data) setAudienceIntel(data); })
                          .catch(() => {})
                          .finally(() => setLoadingAudienceIntel(false));
                      }
                    }}
                    size="sm"
                  />

                  {/* Content Overview Tab */}
                  {competitorDetailTab === "overview" && (
                    <>
                      {/* ── Top Videos / Posts ── */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Flame size={16} className="text-orange-400" />
                      <h4 className="text-sm font-semibold">Top Performing Posts</h4>
                    </div>

                    {loadingFocusedTopVideos ? (
                      <div className="flex items-center gap-2 text-sm text-warroom-muted py-6">
                        <Loader2 size={16} className="animate-spin" /> Loading top posts…
                      </div>
                    ) : focusedTopVideos.length === 0 ? (
                      <p className="text-xs text-warroom-muted py-4">No top posts data available.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {focusedTopVideos.map((vid, idx) => (
                          <div
                            key={vid.id ?? idx}
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
                                    className="text-warroom-muted hover:text-warroom-accent transition"
                                    onClick={(event) => event.stopPropagation()}>
                                    <ExternalLink size={12} />
                                  </a>
                                )}
                              </div>
                            </div>

                            <TopVideoInsights video={vid} />
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

                  {/* Content feed - scrollable post list */}
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
                          .map((post, idx) => {
                          const isExpanded = expandedPostId === post.id;
                          return (
                          <div key={idx} className={`bg-warroom-surface border rounded-xl transition ${isExpanded ? "border-warroom-accent/40" : "border-warroom-border hover:border-warroom-accent/20"}`}>
                            <div
                              className="p-4 cursor-pointer"
                              onClick={() => {
                                if (isExpanded) {
                                  setExpandedPostId(null);
                                  setExpandedPostData(null);
                                } else if (post.id) {
                                  setExpandedPostId(post.id);
                                  setExpandedPostTab("overview");
                                  authFetch(`${API}/api/scraper/posts/${post.id}`)
                                    .then(r => r.ok ? r.json() : null)
                                    .then(data => { if (data) setExpandedPostData(data); })
                                    .catch(() => {});
                                }
                              }}
                            >
                              <div className="flex items-start gap-3">
                                <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold ${
                                  idx === 0 ? "bg-yellow-500/20 text-yellow-400" :
                                  idx === 1 ? "bg-gray-400/20 text-gray-300" :
                                  idx === 2 ? "bg-orange-500/20 text-orange-400" :
                                  "bg-warroom-bg text-warroom-muted"
                                }`}>
                                  #{idx + 1}
                                </div>

                                <div className="flex-1 min-w-0">
                                  {post.hook && (
                                    <p className="text-sm font-medium text-warroom-accent mb-1 line-clamp-1">🪝 {post.hook}</p>
                                  )}
                                  <p className="text-sm text-warroom-text line-clamp-2 mb-2">{post.text}</p>
                                  <div className="flex flex-wrap items-center gap-3 text-xs">
                                    <span className="flex items-center gap-1 text-pink-400"><Heart size={12} /> {formatNum(post.likes)}</span>
                                    <span className="flex items-center gap-1 text-blue-400"><MessageCircle size={12} /> {formatNum(post.comments)}</span>
                                    <span className="text-warroom-muted">Score: <span className="text-warroom-accent font-medium">{post.engagement_score.toFixed(0)}</span></span>
                                    {post.timestamp && <span className="text-warroom-muted">{timeAgo(post.timestamp)}</span>}
                                    {post.url && (
                                      <a href={post.url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                                        className="text-warroom-muted hover:text-warroom-accent transition">
                                        <ExternalLink size={12} />
                                      </a>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Inline expanded detail */}
                            {isExpanded && expandedPostData && (
                              <div className="border-t border-warroom-border">
                                <ScrollTabs
                                  tabs={[
                                    { id: "overview", label: "Overview" },
                                    { id: "transcript", label: expandedPostData.content_analysis ? "Script Analysis" : "Transcript" },
                                    { id: "audience", label: `Audience${expandedPostData.comments_data?.analyzed ? ` (${expandedPostData.comments_data.analyzed})` : ""}` },
                                  ]}
                                  active={expandedPostTab}
                                  onChange={(id) => setExpandedPostTab(id as any)}
                                  size="sm"
                                />
                                <div className="p-4 max-h-80 overflow-y-auto">
                                  {expandedPostTab === "overview" && (
                                    <div className="space-y-3">
                                      {expandedPostData.hook && (
                                        <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3">
                                          <p className="text-[10px] uppercase tracking-wider text-orange-400 mb-1">Hook</p>
                                          <p className="text-sm text-warroom-text">{expandedPostData.hook}</p>
                                        </div>
                                      )}
                                      <p className="text-sm text-warroom-text whitespace-pre-line">{expandedPostData.caption || expandedPostData.text}</p>
                                    </div>
                                  )}
                                  {expandedPostTab === "transcript" && (
                                    <div>
                                      {expandedPostData.content_analysis ? (
                                        <div className="space-y-3">
                                          {expandedPostData.content_analysis.hook?.text && (
                                            <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3">
                                              <p className="text-[10px] uppercase tracking-wider text-orange-400 mb-1">Hook ({expandedPostData.content_analysis.hook.type})</p>
                                              <p className="text-sm">{expandedPostData.content_analysis.hook.text}</p>
                                            </div>
                                          )}
                                          {expandedPostData.content_analysis.value?.text && (
                                            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                                              <p className="text-[10px] uppercase tracking-wider text-blue-400 mb-1">Value</p>
                                              <p className="text-sm whitespace-pre-line">{expandedPostData.content_analysis.value.text}</p>
                                            </div>
                                          )}
                                          {expandedPostData.content_analysis.cta?.text && (
                                            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                                              <p className="text-[10px] uppercase tracking-wider text-green-400 mb-1">CTA ({expandedPostData.content_analysis.cta.type})</p>
                                              <p className="text-sm">{expandedPostData.content_analysis.cta.text}</p>
                                            </div>
                                          )}
                                        </div>
                                      ) : expandedPostData.transcript?.length ? (
                                        <div className="space-y-1">
                                          {expandedPostData.transcript.map((seg: any, i: number) => (
                                            <div key={i} className="flex gap-2 text-sm">
                                              <span className="text-[10px] text-warroom-muted font-mono w-10 flex-shrink-0 pt-0.5">{seg.start?.toFixed(1)}s</span>
                                              <span className="text-warroom-text">{seg.text}</span>
                                            </div>
                                          ))}
                                        </div>
                                      ) : (
                                        <p className="text-sm text-warroom-muted text-center py-6">No transcript available</p>
                                      )}
                                    </div>
                                  )}
                                  {expandedPostTab === "audience" && (
                                    <div>
                                      {expandedPostData.comments_data?.analyzed > 0 ? (
                                        <div className="space-y-3">
                                          <div className="flex items-center gap-3 text-sm">
                                            <span className="text-warroom-muted">Sentiment:</span>
                                            <span className="font-medium capitalize">{expandedPostData.comments_data.sentiment}</span>
                                          </div>
                                          {expandedPostData.comments_data.questions?.length > 0 && (
                                            <div>
                                              <p className="text-xs text-warroom-muted mb-1">Questions Asked</p>
                                              {expandedPostData.comments_data.questions.map((q: any, i: number) => (
                                                <p key={i} className="text-sm text-warroom-text">• {q.question}</p>
                                              ))}
                                            </div>
                                          )}
                                          {expandedPostData.comments_data.themes?.length > 0 && (
                                            <div className="flex flex-wrap gap-1">
                                              {expandedPostData.comments_data.themes.map((t: string, i: number) => (
                                                <span key={i} className="text-[10px] px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full">{t}</span>
                                              ))}
                                            </div>
                                          )}
                                        </div>
                                      ) : (
                                        <p className="text-sm text-warroom-muted text-center py-6">No audience intel available</p>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                    </>
                  )}

                  {/* Dossier Tab */}
                  {competitorDetailTab === "dossier" && (
                    <DossierPanel competitorId={focusedCompetitor.id} bio={focusedCompetitor.bio} />
                  )}

                  {/* Audience Intelligence Tab */}
                  {competitorDetailTab === "audience" && (
                    <div className="space-y-5 py-2">
                      {loadingAudienceIntel ? (
                        <div className="flex items-center gap-2 text-sm text-warroom-muted py-8 justify-center">
                          <Loader2 size={16} className="animate-spin" /> Loading audience intelligence…
                        </div>
                      ) : audienceIntel ? (() => {
                        const ai = audienceIntel;
                        const sentimentColors: Record<string, string> = {
                          very_positive: "text-green-400", positive: "text-green-300",
                          neutral: "text-warroom-muted", negative: "text-orange-400", very_negative: "text-red-400",
                        };
                        return (
                          <>
                            {/* Summary Stats */}
                            <div className="grid grid-cols-4 gap-3">
                              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-3 text-center">
                                <p className="text-lg font-bold text-warroom-text">{ai.posts_analyzed}</p>
                                <p className="text-[10px] text-warroom-muted uppercase">Posts Analyzed</p>
                              </div>
                              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-3 text-center">
                                <p className="text-lg font-bold text-warroom-text">{ai.comments_analyzed?.toLocaleString()}</p>
                                <p className="text-[10px] text-warroom-muted uppercase">Comments</p>
                              </div>
                              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-3 text-center">
                                <p className={`text-lg font-bold capitalize ${sentimentColors[ai.sentiment] || "text-warroom-text"}`}>
                                  {ai.sentiment?.replace("_", " ")}
                                </p>
                                <p className="text-[10px] text-warroom-muted uppercase">Sentiment</p>
                              </div>
                              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-3 text-center">
                                <p className="text-lg font-bold text-warroom-accent">
                                  {ai.sentiment_percentages?.positive || 0}%
                                </p>
                                <p className="text-[10px] text-warroom-muted uppercase">Positive</p>
                              </div>
                            </div>

                            {/* Sentiment Bar */}
                            {ai.sentiment_breakdown && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1.5">Sentiment Distribution</p>
                                <div className="flex h-3 rounded-full overflow-hidden bg-warroom-bg">
                                  {ai.sentiment_breakdown.positive > 0 && (
                                    <div className="bg-green-400" style={{ width: `${ai.sentiment_percentages?.positive || 0}%` }} />
                                  )}
                                  {ai.sentiment_breakdown.neutral > 0 && (
                                    <div className="bg-warroom-border" style={{ width: `${ai.sentiment_percentages?.neutral || 0}%` }} />
                                  )}
                                  {ai.sentiment_breakdown.negative > 0 && (
                                    <div className="bg-red-400" style={{ width: `${ai.sentiment_percentages?.negative || 0}%` }} />
                                  )}
                                </div>
                                <div className="flex justify-between text-[10px] text-warroom-muted mt-1">
                                  <span className="text-green-400">👍 {ai.sentiment_breakdown.positive}</span>
                                  <span>😐 {ai.sentiment_breakdown.neutral}</span>
                                  <span className="text-red-400">👎 {ai.sentiment_breakdown.negative}</span>
                                </div>
                              </div>
                            )}

                            {/* Content Formats */}
                            {ai.content_formats && Object.keys(ai.content_formats).length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Content Format Breakdown</p>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(ai.content_formats).map(([fmt, count]) => (
                                    <span key={fmt} className="px-2.5 py-1 bg-warroom-surface border border-warroom-border rounded-full text-[11px] text-warroom-text">
                                      {fmt === "text_overlay" ? "📝 Text/Tip" : fmt === "short_form" ? "⚡ Short-form" : fmt === "mid_form" ? "📹 Mid-form" : fmt === "long_form" ? "🎬 Long-form" : fmt}
                                      <span className="ml-1 text-warroom-muted">({String(count)})</span>
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Questions */}
                            {ai.questions?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">🔍 Top Questions from Audience</p>
                                <div className="space-y-1.5">
                                  {ai.questions.slice(0, 10).map((q: any, i: number) => (
                                    <div key={i} className="flex items-start gap-2 bg-blue-400/5 border border-blue-400/10 rounded-lg px-3 py-2">
                                      <span className="text-blue-400 text-xs mt-0.5">❓</span>
                                      <p className="text-xs text-warroom-text flex-1">{q.question}</p>
                                      {q.likes > 0 && <span className="text-[10px] text-warroom-muted">👍 {q.likes}</span>}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Pain Points */}
                            {ai.pain_points?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">🎯 Audience Pain Points</p>
                                <div className="space-y-1.5">
                                  {ai.pain_points.slice(0, 10).map((p: any, i: number) => (
                                    <div key={i} className="flex items-start gap-2 bg-red-400/5 border border-red-400/10 rounded-lg px-3 py-2">
                                      <span className="text-red-400 text-xs mt-0.5">💢</span>
                                      <p className="text-xs text-warroom-text flex-1">{p.pain}</p>
                                      {p.likes > 0 && <span className="text-[10px] text-warroom-muted">👍 {p.likes}</span>}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Themes */}
                            {ai.themes?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">💬 Discussion Themes</p>
                                <div className="flex flex-wrap gap-1.5">
                                  {ai.themes.slice(0, 20).map((t: any, i: number) => (
                                    <span key={i} className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full text-[10px]">
                                      {t.theme} ({t.count})
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Product Mentions */}
                            {ai.product_mentions?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">🔧 Tools & Products Mentioned</p>
                                <div className="flex flex-wrap gap-1.5">
                                  {ai.product_mentions.map((p: any, i: number) => (
                                    <span key={i} className="px-2.5 py-1 bg-purple-400/10 text-purple-400 rounded-full text-[10px]">
                                      {p.product} ({p.count})
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Top Commenters */}
                            {ai.top_commenters?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">👥 Most Active Commenters</p>
                                <div className="flex flex-wrap gap-1.5">
                                  {ai.top_commenters.slice(0, 10).map((c: any, i: number) => (
                                    <a key={i} href={`https://instagram.com/${c.username}`} target="_blank" rel="noopener noreferrer"
                                      className="px-2.5 py-1 bg-warroom-bg border border-warroom-border rounded-full text-[10px] text-warroom-text hover:border-warroom-accent/50 transition">
                                      @{c.username} ({c.count})
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        );
                      })() : (
                        <div className="text-center py-12">
                          <p className="text-sm text-warroom-muted">No audience intelligence data yet. Run a sync to populate.</p>
                        </div>
                      )}
                    </div>
                  )}

                </div>
              ) : (
                /* GRID VIEW - all competitors */
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
                      {[...competitors].sort((a, b) => (b.avg_engagement_rate || 0) - (a.avg_engagement_rate || 0)).map(comp => (
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
                            <button onClick={async (e) => {
                                e.stopPropagation();
                                const btn = e.currentTarget;
                                btn.classList.add("animate-spin");
                                try {
                                  const resp = await authFetch(`${API}/api/scraper/instagram/${comp.handle}`, { method: "POST" });
                                  if (resp.ok) {
                                    await fetchCompetitors();
                                  }
                                } catch { /* ignore */ } finally {
                                  btn.classList.remove("animate-spin");
                                }
                              }}
                              className="text-warroom-muted hover:text-warroom-accent transition"
                              title="Sync this competitor">
                              <RefreshCw size={14} />
                            </button>
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
                            <span>{comp.posting_frequency || "-"}</span>
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
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-warroom-muted">Top-performing posts across all tracked competitors for the selected {selectedTimeframeLabel.toLowerCase()} window, re-ranked by live virality and engagement on every refresh.</p>
                {renderTimeframeControls()}
              </div>

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
                    <div
                      key={idx}
                      className={`bg-warroom-surface border border-warroom-border rounded-2xl p-4 transition ${post.id ? "cursor-pointer hover:border-warroom-accent/30" : ""}`}
                      onClick={() => post.id && setSelectedPostId(post.id)}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[post.platform] || "bg-gray-500/20 text-gray-400"}`}>{post.platform}</span>
                          <span className="text-xs text-warroom-muted">@{post.competitor_handle}</span>
                        </div>
                        {post.url && (
                          <a
                            href={post.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(event) => event.stopPropagation()}
                            className="text-warroom-muted hover:text-warroom-accent transition"
                          >
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
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-warroom-muted">Opening hook language pulled from the current top-performing competitor posts in the selected {selectedTimeframeLabel.toLowerCase()} window.</p>
                {renderTimeframeControls()}
              </div>

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
              {loading ? (
                <div className="text-center py-16">
                  <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                  <p className="text-sm text-warroom-muted">Loading scripts...</p>
                </div>
              ) : scripts.length === 0 ? (
                /* Empty state - centered generate form */
                <div className="flex flex-col items-center justify-center py-16 max-w-md mx-auto">
                  <Film size={48} className="text-warroom-muted/20 mb-4" />
                  <h3 className="text-base font-semibold mb-1">No scripts yet</h3>
                  <p className="text-sm text-warroom-muted mb-6 text-center">Generate winning scripts aggregated from all your competitors' top-performing content.</p>

                  <div className="w-full space-y-3 bg-warroom-surface border border-warroom-border rounded-xl p-5">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-warroom-muted block mb-1">Platform</label>
                        <select
                          value={scriptForm.platform}
                          onChange={(e) => setScriptForm({ ...scriptForm, platform: e.target.value })}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                        >
                          <option value="instagram">Instagram</option>
                          <option value="tiktok">TikTok</option>
                          <option value="youtube">YouTube</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-warroom-muted block mb-1">How many</label>
                        <input
                          type="number"
                          min={1}
                          max={12}
                          value={scriptForm.count}
                          onChange={(e) => setScriptForm({ ...scriptForm, count: parseInt(e.target.value, 10) || 6 })}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-warroom-muted block mb-1">Topic / angle (optional)</label>
                      <input
                        type="text"
                        value={scriptForm.topic}
                        onChange={(e) => setScriptForm({ ...scriptForm, topic: e.target.value })}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                        placeholder="Leave blank to auto-detect from competitor trends"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-warroom-muted block mb-1">Hook style (optional)</label>
                      <select
                        value={scriptForm.hook_style}
                        onChange={(e) => setScriptForm({ ...scriptForm, hook_style: e.target.value })}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                      >
                        <option value="">Auto</option>
                        <option value="question">Question</option>
                        <option value="bold_claim">Bold Claim</option>
                        <option value="confession">Confession</option>
                        <option value="shocking_stat">Shocking Stat</option>
                        <option value="comparison">Comparison</option>
                      </select>
                    </div>
                    <button
                      onClick={generateScript}
                      disabled={submitting}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition"
                    >
                      {submitting ? <><Loader2 size={14} className="animate-spin" /> Generating...</> : <><Sparkles size={14} /> Generate Scripts</>}
                    </button>
                  </div>
                </div>
              ) : (
                /* Script list */
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-warroom-muted">
                      <Sparkles size={13} className="inline mr-1 -mt-0.5" />
                      {scripts.length} script{scripts.length !== 1 ? "s" : ""} generated from all competitors
                    </p>
                    <button
                      onClick={() => setShowGenerateScript(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition"
                    >
                      <Plus size={14} /> Generate More
                    </button>
                  </div>

                  <div className="space-y-2">
                    {scripts.map((script, idx) => {
                      const isExpanded = expandedScriptIdx === idx;
                      return (
                        <div
                          key={script.id ?? `${script.title}-${idx}`}
                          className="bg-warroom-surface border border-warroom-border rounded-xl transition hover:border-warroom-accent/30"
                        >
                          {/* Collapsed row */}
                          <button
                            onClick={() => setExpandedScriptIdx(isExpanded ? null : idx)}
                            className="w-full text-left px-5 py-4 flex items-start gap-3"
                          >
                            <span className="mt-0.5 text-warroom-muted">
                              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                            </span>
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-sm leading-snug text-warroom-text">{script.hook}</p>
                              <div className="flex flex-wrap items-center gap-2 mt-1.5">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[script.platform] || "bg-gray-500/20 text-gray-400"}`}>{script.platform}</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${ALIGNMENT_STYLES[script.business_alignment_label] || ALIGNMENT_STYLES.Low}`}>{script.business_alignment_label}</span>
                                <span className="text-[11px] text-warroom-muted flex items-center gap-1"><Eye size={11} /> {formatNum(script.predicted_views)}</span>
                                <span className="text-[11px] text-warroom-muted flex items-center gap-1"><TrendingUp size={11} /> {formatPercent(script.predicted_engagement_rate, 2)}</span>
                                <span className="text-[11px] text-warroom-muted flex items-center gap-1"><Zap size={11} /> {script.virality_score.toFixed(1)}</span>
                                {script.source_competitors.length > 0 && (
                                  <span className="text-[11px] text-warroom-muted ml-1">
                                    {script.source_competitors.slice(0, 3).map((h) => (
                                      <span key={h} className="inline-block px-1.5 py-0.5 mr-1 rounded bg-warroom-bg border border-warroom-border text-[10px]">@{h}</span>
                                    ))}
                                    {script.source_competitors.length > 3 && <span className="text-[10px]">+{script.source_competitors.length - 3}</span>}
                                  </span>
                                )}
                              </div>
                            </div>
                            {script.id != null && (
                              <button
                                onClick={(e) => { e.stopPropagation(); deleteScript(script.id!); }}
                                className="text-warroom-muted hover:text-red-400 transition mt-0.5"
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </button>

                          {/* Expanded accordion */}
                          {isExpanded && (
                            <div className="px-5 pb-5 pt-0 border-t border-warroom-border space-y-5">
                              {/* Title + body */}
                              <div className="pt-4">
                                <h4 className="text-sm font-semibold mb-1">{script.title}</h4>
                                <p className="text-sm text-warroom-text whitespace-pre-line leading-relaxed">{script.body_outline}</p>
                              </div>

                              {/* Scene breakdown */}
                              {script.scene_map.length > 0 && (
                                <div>
                                  <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2 flex items-center gap-1"><Film size={12} /> Scene Breakdown</p>
                                  <div className="space-y-2">
                                    {script.scene_map.map((scene, sIdx) => (
                                      <div key={`${scene.scene}-${sIdx}`} className="bg-warroom-bg rounded-lg p-3 border border-warroom-border">
                                        <p className="text-xs font-semibold mb-0.5">{scene.scene}</p>
                                        <p className="text-xs text-warroom-text">{scene.direction}</p>
                                        <p className="text-[11px] text-warroom-muted mt-1">Goal: {scene.goal}</p>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Business alignment */}
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2 flex items-center gap-1"><Target size={12} /> Business Alignment</p>
                                <div className="bg-warroom-bg rounded-lg p-3 border border-warroom-border">
                                  <p className="text-sm font-medium">{script.business_alignment_label} • {script.business_alignment_score.toFixed(1)}/100</p>
                                  <p className="text-xs text-warroom-muted mt-1">{script.business_alignment_reason}</p>
                                </div>
                              </div>

                              {/* CTA */}
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2 flex items-center gap-1"><Play size={12} /> Call to Action</p>
                                <p className="text-sm bg-warroom-bg rounded-lg p-3 border border-warroom-border">{script.cta}</p>
                              </div>

                              {/* Source evidence */}
                              {script.similar_videos.length > 0 && (
                                <div>
                                  <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2 flex items-center gap-1"><ExternalLink size={12} /> Source Evidence</p>
                                  <div className="space-y-1.5">
                                    {script.similar_videos.map((video, vIdx) => (
                                      <div key={`${video.source_url || video.hook}-${vIdx}`} className="flex items-center gap-2 text-xs bg-warroom-bg rounded-lg px-3 py-2 border border-warroom-border">
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[video.platform] || "bg-gray-500/20 text-gray-400"}`}>{video.platform}</span>
                                        <span className="text-warroom-muted">@{video.competitor_handle}</span>
                                        <span className="flex-1 truncate text-warroom-text">{video.hook || "Reference post"}</span>
                                        <span className="text-warroom-accent text-[11px]">Score {video.engagement_score.toFixed(0)}</span>
                                        {video.source_url && (
                                          <a href={video.source_url} target="_blank" rel="noopener noreferrer" className="text-warroom-muted hover:text-warroom-accent transition" onClick={(e) => e.stopPropagation()}>
                                            <ExternalLink size={11} />
                                          </a>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Actions */}
                              <div className="flex flex-wrap items-center gap-2 pt-1">
                                <button
                                  onClick={() => saveScriptToPlatform(script, script.platform)}
                                  className="flex items-center gap-1.5 px-3 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition"
                                >
                                  <Save size={12} /> Save to {formatPlatformLabel(script.platform)}
                                </button>
                                {SCRIPT_SAVE_PLATFORMS.filter((p) => p !== script.platform).slice(0, 2).map((p) => (
                                  <button
                                    key={p}
                                    onClick={() => saveScriptToPlatform(script, p)}
                                    className="flex items-center gap-1 px-2.5 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-xs hover:border-warroom-accent/30 transition"
                                  >
                                    <Save size={12} /> {formatPlatformLabel(p)}
                                  </button>
                                ))}
                                {script.source_post_url && (
                                  <a href={script.source_post_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-warroom-muted hover:text-warroom-accent transition ml-2">
                                    <ExternalLink size={12} /> Source
                                  </a>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* PROFILE INTEL TAB */}
          {activeTab === "profile-intel" && (
            <div className="space-y-6">
              {loadingInstagramAdvice ? (
                <div className="text-center py-16">
                  <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                  <p className="text-sm text-warroom-muted">Analyzing your profile…</p>
                </div>
              ) : !instagramAdvice || !instagramAdvice.connected ? (
                <div className="text-center py-16 text-warroom-muted">
                  <User size={48} className="mx-auto mb-4 opacity-20" />
                  <p className="text-sm font-medium">Connect your Instagram account</p>
                  <p className="text-xs mt-1">Once connected and synced, War Room will analyze your profile and give you actionable advice.</p>
                </div>
              ) : (
                <>
                  {/* Profile header with scraped data */}
                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                    <div className="flex items-start justify-between gap-4 mb-3">
                      <div className="flex items-start gap-3">
                        {instagramAdvice.profile_pic_url ? (
                          <img src={instagramAdvice.profile_pic_url} alt="" className="w-12 h-12 rounded-full object-cover flex-shrink-0" />
                        ) : (
                          <div className="w-12 h-12 rounded-full bg-warroom-accent/10 flex items-center justify-center text-lg font-bold text-warroom-accent flex-shrink-0">
                            {(instagramAdvice.username || "?").charAt(0).toUpperCase()}
                          </div>
                        )}
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-base font-semibold text-warroom-text">{instagramAdvice.username ? `@${instagramAdvice.username}` : "Your Instagram"}</p>
                            {instagramAdvice.is_verified && <span className="text-blue-400" title="Verified">✓</span>}
                            {instagramAdvice.category && <span className="text-[10px] text-warroom-muted bg-warroom-bg px-1.5 py-0.5 rounded">{instagramAdvice.category}</span>}
                          </div>
                          <p className="text-xs text-warroom-muted mt-0.5">{instagramAdvice.summary}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {instagramAdvice.posting_frequency && (
                          <span className="text-[10px] text-warroom-muted bg-warroom-bg border border-warroom-border px-2 py-1 rounded-lg">{instagramAdvice.posting_frequency}</span>
                        )}
                        <span className={`px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider ${instagramAdvice.connected ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
                          {instagramAdvice.status.replace(/_/g, " ")}
                        </span>
                      </div>
                    </div>

                    {/* Bio + Links snapshot */}
                    {instagramAdvice.bio && (
                      <div className="bg-warroom-bg border border-warroom-border rounded-xl p-3 mb-3">
                        <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-1">Current bio</p>
                        <p className="text-sm text-warroom-text whitespace-pre-line">{instagramAdvice.bio}</p>
                      </div>
                    )}
                    <div className="flex flex-wrap items-center gap-3 text-xs">
                      {instagramAdvice.external_url && (
                        <a href={instagramAdvice.external_url} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-1 text-warroom-accent hover:underline">
                          <ExternalLink size={12} /> {instagramAdvice.external_url.replace(/^https?:\/\//, "").slice(0, 40)}
                        </a>
                      )}
                      {(instagramAdvice.bio_links || []).map((link: any, i: number) => (
                        <a key={i} href={link.url} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-1 text-warroom-accent hover:underline">
                          <ExternalLink size={12} /> {link.title || link.url?.replace(/^https?:\/\//, "").slice(0, 30)}
                        </a>
                      ))}
                      {!instagramAdvice.external_url && !(instagramAdvice.bio_links || []).length && (
                        <span className="text-warroom-muted italic">No links in profile</span>
                      )}
                    </div>
                    {instagramAdvice.last_synced && (
                      <p className="text-[11px] text-warroom-muted mt-3">Last synced {timeAgo(instagramAdvice.last_synced)} · {instagramAdvice.days_analyzed} days analyzed</p>
                    )}
                  </div>

                  {/* Actionable Intelligence Cards */}
                  <div>
                    <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-3">Actionable intelligence</h3>
                    <div className="space-y-3">
                      {instagramAdvice.recommendations.length > 0 ? instagramAdvice.recommendations.map((item: any, idx: number) => {
                        const categoryColors: Record<string, string> = {
                          bio: "bg-purple-500/10 text-purple-400",
                          content: "bg-blue-500/10 text-blue-400",
                          growth: "bg-emerald-500/10 text-emerald-400",
                          profile: "bg-amber-500/10 text-amber-400",
                          engagement: "bg-pink-500/10 text-pink-400",
                        };
                        const catClass = categoryColors[item.category] || "bg-warroom-accent/10 text-warroom-accent";
                        return (
                          <div key={idx} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/20 transition">
                            <div className="flex items-start gap-3">
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${catClass}`}>
                                <Sparkles size={16} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <p className="text-sm font-semibold text-warroom-text">{item.title}</p>
                                  {item.category && <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded ${catClass}`}>{item.category}</span>}
                                </div>
                                <p className="text-sm text-warroom-muted leading-relaxed whitespace-pre-line">{item.detail}</p>
                                {item.metric && (
                                  <p className="text-xs text-warroom-accent mt-3 px-2.5 py-1 bg-warroom-accent/10 rounded-lg inline-block">{item.metric}</p>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      }) : (
                        <div className="text-center py-10 text-warroom-muted">
                          <Sparkles size={32} className="mx-auto mb-3 opacity-20" />
                          <p className="text-sm">Sync your Instagram data to unlock profile intelligence</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Recent Posts from scrape */}
                  {(instagramAdvice.recent_posts || []).length > 0 && (
                    <div>
                      <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-3">Your recent posts</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {(instagramAdvice.recent_posts || []).map((post: any, idx: number) => (
                          <div key={idx} className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition">
                            <div className="flex items-center gap-2 mb-2">
                              {post.media_type === "reel" || post.media_type === "video" ? (
                                <Film size={12} className="text-pink-400" />
                              ) : (
                                <EyeIcon size={12} className="text-warroom-muted" />
                              )}
                              <span className="text-[10px] text-warroom-muted uppercase">{post.media_type}</span>
                              {post.posted_at && <span className="text-[10px] text-warroom-muted ml-auto">{timeAgo(post.posted_at)}</span>}
                            </div>
                            {post.hook && (
                              <p className="text-xs font-medium text-warroom-accent mb-1 line-clamp-1">🪝 {post.hook}</p>
                            )}
                            <p className="text-xs text-warroom-text line-clamp-2 mb-2">{post.caption_preview}</p>
                            <div className="flex items-center gap-3 text-[11px] text-warroom-muted">
                              <span className="flex items-center gap-1"><Heart size={10} className="text-pink-400" /> {formatNum(post.likes)}</span>
                              <span className="flex items-center gap-1"><MessageCircle size={10} className="text-blue-400" /> {formatNum(post.comments)}</span>
                              {post.views > 0 && <span className="flex items-center gap-1"><Play size={10} className="text-purple-400" /> {formatNum(post.views)}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Quick Stats - compact row at bottom */}
                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                    <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-3">Metrics snapshot</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                      <div className="text-center">
                        <p className="text-lg font-bold text-warroom-text">{formatNum(instagramAdvice.follower_count)}</p>
                        <p className="text-[10px] text-warroom-muted">Followers</p>
                      </div>
                      <div className="text-center">
                        <p className={`text-lg font-bold ${instagramAdvice.net_followers >= 0 ? "text-emerald-400" : "text-red-400"}`}>{instagramAdvice.net_followers >= 0 ? "+" : ""}{formatNum(instagramAdvice.net_followers)}</p>
                        <p className="text-[10px] text-warroom-muted">Net followers</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-warroom-accent">{formatPercent(instagramAdvice.avg_engagement_rate, 2)}</p>
                        <p className="text-[10px] text-warroom-muted">Engagement</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-warroom-text">{formatNum(instagramAdvice.avg_reach)}</p>
                        <p className="text-[10px] text-warroom-muted">Avg reach</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-warroom-text">{formatNum(instagramAdvice.avg_video_views)}</p>
                        <p className="text-[10px] text-warroom-muted">Avg views</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-warroom-text">{formatNum(instagramAdvice.avg_profile_views)}</p>
                        <p className="text-[10px] text-warroom-muted">Profile views</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-warroom-text">{formatNum(instagramAdvice.total_link_clicks)}</p>
                        <p className="text-[10px] text-warroom-muted">Link clicks</p>
                      </div>
                    </div>
                  </div>
                </>
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
              <h3 className="text-lg font-semibold">Generate Scripts</h3>
              <button onClick={() => setShowGenerateScript(false)} className="text-warroom-muted hover:text-warroom-text">
                <X size={20} />
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-xs text-warroom-muted">Aggregates top-performing posts from all your competitors to generate winning script ideas.</p>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">Platform</label>
                  <select
                    value={scriptForm.platform}
                    onChange={(e) => setScriptForm({ ...scriptForm, platform: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                  >
                    <option value="instagram">Instagram</option>
                    <option value="tiktok">TikTok</option>
                    <option value="youtube">YouTube</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">How many</label>
                  <input
                    type="number"
                    min={1}
                    max={12}
                    value={scriptForm.count}
                    onChange={(e) => setScriptForm({ ...scriptForm, count: parseInt(e.target.value, 10) || 6 })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-warroom-muted block mb-1">Topic / angle (optional)</label>
                <input
                  type="text"
                  value={scriptForm.topic}
                  onChange={(e) => setScriptForm({ ...scriptForm, topic: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                  placeholder="Leave blank to auto-detect from competitor trends"
                />
              </div>

              <div>
                <label className="text-xs text-warroom-muted block mb-1">Hook style (optional)</label>
                <select
                  value={scriptForm.hook_style}
                  onChange={(e) => setScriptForm({ ...scriptForm, hook_style: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                >
                  <option value="">Auto</option>
                  <option value="question">Question</option>
                  <option value="bold_claim">Bold Claim</option>
                  <option value="confession">Confession</option>
                  <option value="shocking_stat">Shocking Stat</option>
                  <option value="comparison">Comparison</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowGenerateScript(false)}
                className="flex-1 px-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm hover:bg-warroom-surface transition">
                Cancel
              </button>
              <button onClick={generateScript} disabled={submitting}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2">
                {submitting ? <><Loader2 size={14} className="animate-spin" /> Generating...</> : <><Sparkles size={14} /> Generate Scripts</>}
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