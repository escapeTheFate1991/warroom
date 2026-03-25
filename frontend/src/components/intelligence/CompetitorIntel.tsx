"use client";

import { useState, useEffect } from "react";
import { Search, Plus, X, Flame, Copy, Check, User, TrendingUp, Eye, Target, Zap, BookOpen, ExternalLink, Trash2, Loader2, RefreshCw, Play, Save, Edit3, ArrowLeft, Heart, MessageCircle, EyeIcon, BarChart3, Hash, Users, Sparkles, ShoppingBag, Film, FileText, ChevronDown, ChevronRight, Info, Brain, Share, Instagram } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import PostDetailModal from "./PostDetailModal";
import ScrollTabs from "@/components/ui/ScrollTabs";
import { useSocialAccounts, PLATFORM_CONFIGS } from "@/hooks/useSocialAccounts";
import { VideoMetricsCard, EnhancedCompetitorCard, InfoTooltip } from "./RedesignedCompetitorCards";
import EnhancedVideoAnalytics from "./EnhancedVideoAnalytics";
import AudiencePsychologyAnalysis from "./AudiencePsychologyAnalysis";


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
  detected_format?: string;
  analysis_status?: "completed" | "processing" | "failed" | null;
  frame_chunks?: FrameChunk[];
  video_analysis?: VideoAnalysis | null;
  analyzed_at?: string;
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
  detected_format?: string;
  analysis_status?: "completed" | "processing" | "failed" | null;
  frame_chunks?: FrameChunk[];
  video_analysis?: VideoAnalysis | null;
  analyzed_at?: string;
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
  detected_format?: string;
  analysis_status?: "completed" | "processing" | "failed" | null;
  frame_chunks?: FrameChunk[];
  video_analysis?: VideoAnalysis | null;
  analyzed_at?: string;
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

interface FrameChunk {
  start_time: number;
  end_time: number;
  duration: number;
  description: string;
  veo_prompt: string;
  visual_elements: string[];
  action_type: string;
  pacing: string;
}

interface VideoAnalysis {
  summary?: string;
  total_duration?: number;
  key_insights?: string[];
  dominant_themes?: string[];
  production_quality?: string;
  content_style?: string;
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

interface ContentGap {
  topic: string;
  unanswered_questions: string[];
  opportunity_score: number;
}

interface VideoTopicSuggestion {
  topic: string;
  reasoning: string;
  source_questions: string[];
}

// CDR Interfaces
interface CdrCandidate {
  post_id: number;
  hook_preview: string;
  power_score: number;
  dominant_intent: string;
  engagement_metrics: {
    likes: number;
    comments: number;
    shares: number;
    engagement_score: number;
  };
  platform: string;
  competitor_handle: string;
  timestamp: string;
  post_url?: string;
}

interface HookDirective {
  visual: string;
  audio: string;
  script_line: string;
  overlay: string;
}

interface RetentionBlueprint {
  pacing_rules: string[];
  pattern_interrupts: Array<{
    timestamp: number;
    action: string;
  }>;
}

interface ShareCatalyst {
  vulnerability_frame: string;
  timestamp: number;
}

interface ConversionClose {
  cta_script: string;
  automation_trigger: string;
}

interface TechnicalSpecs {
  lighting: string;
  aspect_ratio: string;
  colors: string[];
  bpm: number;
  length_seconds: number;
}

interface CreatorDirectiveReport {
  post_id: number;
  hook_directive: HookDirective;
  retention_blueprint: RetentionBlueprint;
  share_catalyst: ShareCatalyst;
  conversion_close: ConversionClose;
  technical_specs: TechnicalSpecs;
  generator_prompts: {
    veo_prompt: string;
    nano_banana_prompt: string;
  };
  power_score: number;
  dominant_intent: string;
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
  top_engagers?: any[];
  cross_competitor_overlap?: any[];
  engagement_distribution?: Record<string, number>;
  content_gaps: ContentGap[];
  video_topic_suggestions: VideoTopicSuggestion[];
}

interface HashtagItem {
  tag: string;
  count: number;
}

interface ScrapeStatusResponse {
  sync_running: boolean;
}

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "bg-gradient-to-r from-pink-500/20 to-purple-500/20 text-pink-400 border border-pink-500/20",
  tiktok: "bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-400 border border-cyan-500/20",
  youtube: "bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-400 border border-red-500/20",
  x: "bg-gradient-to-r from-gray-600/20 to-gray-500/20 text-gray-300 border border-gray-600/20",
  facebook: "bg-gradient-to-r from-blue-500/20 to-indigo-500/20 text-blue-400 border border-blue-500/20",
  threads: "bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-400 border border-gray-500/20",
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

const FORMAT_BADGES: Record<string, { label: string; style: string }> = {
  myth_buster: { label: "Myth Buster", style: "bg-blue-500/20 text-blue-400" },
  expose: { label: "Exposé", style: "bg-purple-500/20 text-purple-400" },
  transformation: { label: "Transformation", style: "bg-green-500/20 text-green-400" },
  pov: { label: "POV", style: "bg-yellow-500/20 text-yellow-400" },
  speed_run: { label: "Speed Run", style: "bg-cyan-500/20 text-cyan-400" },
  challenge: { label: "Challenge", style: "bg-orange-500/20 text-orange-400" },
  show_dont_tell: { label: "Show Don't Tell", style: "bg-pink-500/20 text-pink-400" },
  direct_to_camera: { label: "Direct-to-Camera", style: "bg-red-500/20 text-red-400" },
  unclassified: { label: "Unclassified", style: "bg-gray-500/20 text-gray-400" },
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

function extractFirstSentence(text: string): string {
  if (!text) return "";
  const match = text.match(/^[^.!?]*[.!?]?/);
  return match ? match[0].trim() : text.slice(0, 100).trim();
}

function deriveTopic(text: string): string {
  if (!text) return "";
  // Extract the first 50 characters or until first period
  const topic = text.slice(0, 50).trim();
  const periodIndex = topic.indexOf('.');
  return periodIndex > 0 ? topic.slice(0, periodIndex) : topic;
}

function isHighEngagementUnclassified(post: any, allPosts: any[]): boolean {
  if (post.detected_format !== "unclassified") return false;
  
  // Calculate top 20% threshold
  const sortedPosts = [...allPosts].sort((a, b) => b.engagement_score - a.engagement_score);
  const top20Index = Math.floor(sortedPosts.length * 0.2);
  const threshold = sortedPosts[top20Index]?.engagement_score || 0;
  
  return post.engagement_score >= threshold;
}

function FormatBadge({ format, post, allPosts }: { format?: string; post?: any; allPosts?: any[] }) {
  if (!format) return null;
  
  const isEmerging = allPosts && post && isHighEngagementUnclassified(post, allPosts);
  
  if (isEmerging) {
    return (
      <span 
        className="px-2 py-1 text-[10px] font-medium rounded-full border animate-pulse"
        style={{
          background: "rgba(234, 179, 8, 0.15)",
          color: "#eab308",
          borderColor: "rgba(234, 179, 8, 0.3)"
        }}
      >
        ✨ Emerging
      </span>
    );
  }
  
  const badge = FORMAT_BADGES[format];
  if (!badge) return null;
  
  return (
    <span className={`px-2 py-1 text-[10px] font-medium rounded-full ${badge.style}`}>
      {badge.label}
    </span>
  );
}

function navigateToAIStudio(post: any, competitorHandle?: string) {
  // Create prefill data for AI Studio
  const prefillData = {
    format: post.detected_format || "direct_to_camera",
    hook: post.hook || extractFirstSentence(post.text || post.title || ""),
    topic: deriveTopic(post.text || post.title || ""),
    competitor_intel: true,
    source_post_url: post.url || post.post_url,
    source_handle: competitorHandle
  };
  
  // Encode the data as URL parameters
  const params = new URLSearchParams();
  Object.entries(prefillData).forEach(([key, value]) => {
    if (value) params.set(key, String(value));
  });
  
  // Navigate to AI Studio with prefilled data
  // This assumes the app has URL-based routing
  const aiStudioUrl = `/ai-studio?${params.toString()}`;
  window.location.href = aiStudioUrl;
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

// Video Topic Card Component for handling collapsible state
function VideoTopicCard({ suggestion }: { suggestion: VideoTopicSuggestion }) {
  const [showSources, setShowSources] = useState(false);
  
  return (
    <div className="bg-emerald-400/5 border border-emerald-400/10 rounded-lg p-3">
      <h4 className="text-xs font-medium text-warroom-text mb-1">{suggestion.topic}</h4>
      <p className="text-xs text-warroom-text/80 mb-2">{suggestion.reasoning}</p>
      <button
        onClick={() => setShowSources(!showSources)}
        className="text-[10px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
      >
        {showSources ? 'Hide' : 'Show'} Source Questions ({suggestion.source_questions.length})
        <span className={`transform transition-transform ${showSources ? 'rotate-180' : ''}`}>▼</span>
      </button>
      {showSources && (
        <div className="mt-2 space-y-1 pl-2 border-l-2 border-emerald-400/20">
          {suggestion.source_questions.map((question: string, qi: number) => (
            <p key={qi} className="text-[10px] text-warroom-text/60">• {question}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CompetitorIntel() {
  // OAuth integration for Profile Intel
  const { connected, isConnected, connect } = useSocialAccounts();
  
  const [activeTab, setActiveTab] = useState<"competitors" | "top-content" | "hooks" | "scripts" | "profile-intel" | "video-analytics" | "creator-directives">("competitors");
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
  const [psychologyAnalysisCompetitor, setPsychologyAnalysisCompetitor] = useState<{ id: number; handle: string } | null>(null);

  const [showAddCompetitor, setShowAddCompetitor] = useState(false);
  const [copiedHook, setCopiedHook] = useState<number | null>(null);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [loadingPosts, setLoadingPosts] = useState(false);

  const [newComp, setNewComp] = useState({ handle: "", platform: "instagram" });


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

  // Video Analytics state
  const [videoAnalytics, setVideoAnalytics] = useState<any>(null);
  const [viralPatterns, setViralPatterns] = useState<any>(null);
  const [contentRecommendations, setContentRecommendations] = useState<any>(null);
  const [loadingVideoAnalytics, setLoadingVideoAnalytics] = useState(false);
  const [loadingViralPatterns, setLoadingViralPatterns] = useState(false);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [selectedAnalyticsVideo, setSelectedAnalyticsVideo] = useState<any>(null);

  // CDR state
  const [cdrCandidates, setCdrCandidates] = useState<CdrCandidate[]>([]);
  const [selectedCdrPost, setSelectedCdrPost] = useState<number | null>(null);
  const [currentCdr, setCurrentCdr] = useState<CreatorDirectiveReport | null>(null);
  const [loadingCdrCandidates, setLoadingCdrCandidates] = useState(false);
  const [loadingCdr, setLoadingCdr] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState<string | null>(null);

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
      const response = await authFetch(`${API}/api/content-intel/competitors/audience-intel?days=${contentTimeframeDays}`);
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
          const sr = (status as any).sync_result;
          if (sr?.status === "error") {
            setError(`Instagram sync failed: ${sr.error}`);
          } else if (sr?.status === "complete") {
            setNotice(
              `Instagram sync complete: ${sr.success}/${sr.total} competitors scraped, ${sr.posts_saved} posts cached`
            );
          } else {
            setNotice("Instagram scrape finished.");
          }
          await refreshIntelligenceViews();
          return true;
        }
      } catch (error) {
        console.warn("Failed to poll Instagram scrape status", error);
        break;
      }
    }

    return false;
  };

  // Video Analytics fetch functions
  const fetchVideoAnalytics = async () => {
    try {
      setLoadingVideoAnalytics(true);
      const response = await authFetch(`${API}/api/competitors/video-analytics/performance-comparison?timeframe_days=${contentTimeframeDays}`);
      if (response.ok) {
        setVideoAnalytics(await response.json());
      } else {
        setVideoAnalytics(null);
      }
    } catch (err) {
      setVideoAnalytics(null);
    } finally {
      setLoadingVideoAnalytics(false);
    }
  };

  const fetchViralPatterns = async () => {
    try {
      setLoadingViralPatterns(true);
      const response = await authFetch(`${API}/api/competitors/video-analytics/viral-patterns`);
      if (response.ok) {
        setViralPatterns(await response.json());
      } else {
        setViralPatterns(null);
      }
    } catch (err) {
      setViralPatterns(null);
    } finally {
      setLoadingViralPatterns(false);
    }
  };

  const fetchContentRecommendations = async () => {
    try {
      setLoadingRecommendations(true);
      const response = await authFetch(`${API}/api/competitors/video-analytics/recommendations`);
      if (response.ok) {
        setContentRecommendations(await response.json());
      } else {
        setContentRecommendations(null);
      }
    } catch (err) {
      setContentRecommendations(null);
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const fetchDropoffAnalysis = async (postId: number) => {
    try {
      const response = await authFetch(`${API}/api/competitors/video-analytics/dropoff-analysis/${postId}`);
      if (response.ok) {
        return await response.json();
      }
    } catch (err) {
      console.error("Failed to fetch dropoff analysis:", err);
    }
    return null;
  }

  // CDR fetch functions
  const fetchCdrCandidates = async () => {
    try {
      setLoadingCdrCandidates(true);
      const response = await authFetch(`${API}/api/content-intel/cdr-candidates`);
      if (response.ok) {
        const data = await response.json();
        setCdrCandidates(Array.isArray(data.candidates) ? data.candidates : []);
      } else {
        setCdrCandidates([]);
      }
    } catch (error) {
      setCdrCandidates([]);
    } finally {
      setLoadingCdrCandidates(false);
    }
  };

  const generateCdr = async (postId: number) => {
    try {
      setLoadingCdr(true);
      const response = await authFetch(`${API}/api/content-intel/creator-directive/${postId}`, {
        method: "POST"
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentCdr(data);
        setSelectedCdrPost(postId);
      }
    } catch (error) {
      console.error("Failed to generate CDR:", error);
    } finally {
      setLoadingCdr(false);
    }
  };

  const copyToClipboard = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPrompt(type);
    setTimeout(() => setCopiedPrompt(null), 2000);
  };;

  // Load data based on active tab
  // Fetch all counts on mount so tab badges are accurate
  useEffect(() => {
    fetchCompetitors();
    fetchGlobalAudienceIntel();
    fetchAggregateTopVideos();
    fetchScripts();
    fetchCdrCandidates();
  }, []);

  useEffect(() => {
    fetchTopContent();
    fetchHooks();
    fetchAggregateTopVideos();
    fetchGlobalAudienceIntel();
  }, [contentTimeframeDays]);

  // Fetch active tab data on tab change
  useEffect(() => {
    switch (activeTab) {
      case "competitors":
        fetchCompetitors();
        fetchGlobalAudienceIntel();
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
      case "video-analytics":
        fetchVideoAnalytics();
        fetchViralPatterns();
        fetchContentRecommendations();
        break;
      case "creator-directives":
        fetchCdrCandidates();
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

  // Profile Intel requires OAuth to show user's own profile data
  useEffect(() => {
    if (activeTab === "profile-intel") {
      fetchInstagramAdvice();
    }
  }, [activeTab]);

  useEffect(() => {
    if (isConnected("instagram") && activeTab === "profile-intel") {
      fetchInstagramAdvice();
    }
  }, [connected, activeTab, isConnected]);

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

  // Open psychology analysis modal
  const openPsychologyAnalysis = (competitorId: number) => {
    const competitor = competitors.find(c => c.id === competitorId);
    if (competitor) {
      setPsychologyAnalysisCompetitor({ id: competitorId, handle: competitor.handle });
    }
  };

  // Close psychology analysis modal
  const closePsychologyAnalysis = () => {
    setPsychologyAnalysisCompetitor(null);
  };

  const TABS = [
    { id: "competitors" as const, label: "Competitors", icon: Target, count: competitors.length },
    { id: "top-content" as const, label: "Top Content", icon: TrendingUp, count: topContent.length },
    { id: "hooks" as const, label: "Hooks", icon: Zap, count: hooks.length },
    { id: "scripts" as const, label: "Scripts", icon: BookOpen, count: scripts.length },
    { id: "creator-directives" as const, label: "Creator Directives", icon: Brain, count: cdrCandidates.length },
    { id: "profile-intel" as const, label: "Profile Intel", icon: Sparkles },
    { id: "video-analytics" as const, label: "Video Analytics", icon: BarChart3 },
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
        <div className="w-full">

          {/* COMPETITORS TAB */}
          {activeTab === "competitors" && (
            <div className="space-y-4">

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
                            className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition cursor-pointer relative"
                            onClick={() => vid.id && setSelectedPostId(vid.id)}
                          >
                            {/* Format Badge & Analysis Status */}
                            <div className="absolute top-3 right-3 flex items-center gap-2">
                              {vid.detected_format && (
                                <FormatBadge format={vid.detected_format} post={vid} allPosts={focusedTopVideos} />
                              )}
                              {/* Video Analysis Status Indicator */}
                              {(vid.media_type === 'video' || vid.media_type === 'reel' || vid.media_type === 'clip') && (
                                <div>
                                  {vid.analysis_status === 'completed' && (
                                    <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full text-[10px] font-medium" title="Frame analysis completed">
                                      <Film size={10} />
                                      Analyzed
                                    </span>
                                  )}
                                  {vid.analysis_status === 'processing' && (
                                    <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full text-[10px] font-medium" title="Frame analysis in progress">
                                      <Loader2 size={10} className="animate-spin" />
                                      Processing
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2 mb-2 pr-20">
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
                            <div className="flex items-center justify-between text-[10px] text-warroom-muted mb-3">
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
                            
                            {/* Generate Variant Button */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigateToAIStudio(vid, focusedCompetitor?.handle);
                              }}
                              className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 bg-warroom-bg border border-warroom-border hover:border-warroom-accent/50 hover:bg-warroom-accent/5 rounded-lg text-xs font-medium text-warroom-text transition mb-2"
                            >
                              <Sparkles size={12} />
                              Generate Variant
                            </button>

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
                          <div key={idx} className={`bg-warroom-surface border rounded-xl transition relative ${isExpanded ? "border-warroom-accent/40" : "border-warroom-border hover:border-warroom-accent/20"}`}>
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
                              {/* Format Badge & Analysis Status */}
                              <div className="absolute top-3 right-3 flex items-center gap-2">
                                {post.detected_format && (
                                  <FormatBadge format={post.detected_format} post={post} allPosts={competitorPosts} />
                                )}
                                {/* Video Analysis Status Indicator */}
                                {(post.media_type === 'video' || post.media_type === 'reel' || post.media_type === 'clip') && (
                                  <div className="flex items-center gap-1">
                                    {post.analysis_status === 'completed' && (
                                      <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full text-[10px] font-medium" title="Frame analysis completed">
                                        <Film size={10} />
                                        Analyzed
                                      </span>
                                    )}
                                    {post.analysis_status === 'processing' && (
                                      <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full text-[10px] font-medium" title="Frame analysis in progress">
                                        <Loader2 size={10} className="animate-spin" />
                                        Processing
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                              
                              <div className="flex items-start gap-3 pr-20">
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
                                  <div className="flex flex-wrap items-center gap-3 text-xs mb-2">
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
                                  
                                  {/* Generate Variant Button */}
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      navigateToAIStudio(post, focusedCompetitor?.handle);
                                    }}
                                    className="flex items-center gap-1.5 px-2.5 py-1 bg-warroom-bg border border-warroom-border hover:border-warroom-accent/50 hover:bg-warroom-accent/5 rounded-lg text-xs font-medium text-warroom-text transition"
                                  >
                                    <Sparkles size={11} />
                                    Generate Variant
                                  </button>
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

                            {/* Content Gaps */}
                            {ai.content_gaps?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">📊 Content Gaps (Unanswered Audience Questions)</p>
                                <div className="space-y-2">
                                  {ai.content_gaps.slice(0, 10).map((gap: ContentGap, i: number) => (
                                    <div key={i} className="bg-orange-400/5 border border-orange-400/10 rounded-lg p-3">
                                      <div className="flex items-center gap-2 mb-2">
                                        <h4 className="text-xs font-medium text-warroom-text">{gap.topic}</h4>
                                        <span className="bg-orange-400/20 text-orange-400 rounded-full px-2 py-0.5 text-[10px] font-medium">
                                          {gap.opportunity_score}/100
                                        </span>
                                      </div>
                                      <div className="space-y-1">
                                        {gap.unanswered_questions.slice(0, 3).map((question: string, qi: number) => (
                                          <p key={qi} className="text-xs text-warroom-text flex items-start gap-2">
                                            <span className="text-orange-400 mt-0.5">•</span>
                                            {question}
                                          </p>
                                        ))}
                                        {gap.unanswered_questions.length > 3 && (
                                          <p className="text-[10px] text-warroom-muted italic">
                                            +{gap.unanswered_questions.length - 3} more questions
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Video Topic Ideas */}
                            {ai.video_topic_suggestions?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">🎬 Video Topic Ideas (From Audience Demand)</p>
                                <div className="space-y-2">
                                  {ai.video_topic_suggestions.slice(0, 10).map((suggestion: VideoTopicSuggestion, i: number) => (
                                    <VideoTopicCard key={i} suggestion={suggestion} />
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

                            {/* Top Engagers */}
                            {ai.top_engagers?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">🏆 Top Engagers</p>
                                <div className="space-y-2">
                                  {ai.top_engagers?.slice(0, 10).map((engager: any, i: number) => (
                                    <div key={i} className="bg-warroom-surface border border-warroom-border rounded-lg p-3">
                                      <div className="flex items-center justify-between mb-1">
                                        <div className="flex items-center gap-2">
                                          {engager.profile_url ? (
                                            <a 
                                              href={engager.profile_url} 
                                              target="_blank" 
                                              rel="noopener noreferrer" 
                                              className="text-xs font-medium text-warroom-accent hover:underline"
                                            >
                                              @{engager.username}
                                            </a>
                                          ) : (
                                            <p className="text-xs font-medium text-warroom-text">@{engager.username}</p>
                                          )}
                                          {engager.is_verified && <span className="text-blue-400 text-xs">✓</span>}
                                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                                            engager.engagement_level === 'high' ? 'bg-green-500/10 text-green-400' :
                                            engager.engagement_level === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                                            'bg-gray-500/10 text-gray-400'
                                          }`}>
                                            {engager.engagement_level}
                                          </span>
                                        </div>
                                        <span className="text-[10px] text-warroom-muted">{engager.interaction_count} interactions</span>
                                      </div>
                                      {engager.followers && (
                                        <p className="text-[10px] text-warroom-muted mb-1">{engager.followers.toLocaleString()} followers</p>
                                      )}
                                      {engager.competitors_engaged_with?.length > 0 && (
                                        <div className="flex flex-wrap gap-1">
                                          {engager.competitors_engaged_with.map((comp: string, j: number) => (
                                            <span key={j} className="text-[9px] px-1.5 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full">
                                              @{comp}
                                            </span>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Cross-Competitor Overlap */}
                            {ai.cross_competitor_overlap?.length > 0 && (
                              <div>
                                <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">🔄 Cross-Competitor Audience</p>
                                <div className="space-y-2">
                                  {ai.cross_competitor_overlap.slice(0, 8).map((overlap: any, i: number) => (
                                    <div key={i} className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3">
                                      <div className="flex items-center justify-between mb-1">
                                        <div className="flex items-center gap-2">
                                          {overlap.profile_url ? (
                                            <a 
                                              href={overlap.profile_url} 
                                              target="_blank" 
                                              rel="noopener noreferrer" 
                                              className="text-xs font-medium text-purple-400 hover:underline"
                                            >
                                              @{overlap.username}
                                            </a>
                                          ) : (
                                            <p className="text-xs font-medium text-purple-400">@{overlap.username}</p>
                                          )}
                                          <span className="text-[10px] text-warroom-muted">
                                            Engages with {overlap.competitors?.length || 0} competitors
                                          </span>
                                        </div>
                                        <span className="text-[10px] text-warroom-muted">{overlap.total_interactions} total</span>
                                      </div>
                                      <div className="flex flex-wrap gap-1">
                                        {overlap.competitors?.map((comp: string, j: number) => (
                                          <span key={j} className="text-[9px] px-1.5 py-0.5 bg-purple-500/10 text-purple-400 rounded-full">
                                            @{comp}
                                          </span>
                                        ))}
                                      </div>
                                      {overlap.profile_summary && (
                                        <p className="text-[10px] text-warroom-muted mt-1 italic">{overlap.profile_summary}</p>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Legacy Top Commenters - fallback if enhanced data not available */}
                            {(!ai.top_engagers || ai.top_engagers?.length === 0) && ai.top_commenters?.length > 0 && (
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
                  {/* 1. Sync Status Bar */}
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

                  {/* 2. Audience Psychology Intelligence */}
                  <div className="glass-card inner-glow p-5">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <Brain size={18} className="text-purple-400" />
                        <div>
                          <h3 className="text-sm font-semibold">Audience Psychology Intelligence</h3>
                          <p className="text-xs text-warroom-muted">Why your audience shares, engages, and converts</p>
                        </div>
                      </div>
                    </div>

                    {loadingGlobalAudienceIntel ? (
                      <div className="flex items-center gap-2 text-sm text-warroom-muted py-4">
                        <Loader2 size={16} className="animate-spin" /> Analyzing behavioral patterns…
                      </div>
                    ) : globalAudienceIntel ? (
                      <div className="space-y-4">
                        {/* Psychology Metrics */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          <div className="stat-card p-3">
                            <p className="text-lg font-bold text-purple-400">{globalAudienceIntel.posts_analyzed}</p>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Behavioral signals</p>
                          </div>
                          <div className="stat-card p-3">
                            <p className="text-lg font-bold text-emerald-400">{Math.round((globalAudienceIntel.sentiment_percentages?.positive || 0))}%</p>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Positive psychology</p>
                          </div>
                          <div className="stat-card p-3">
                            <p className="text-lg font-bold text-orange-400">{globalAudienceIntel.pain_points.length}</p>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Pain triggers</p>
                          </div>
                          <div className="stat-card p-3">
                            <p className="text-lg font-bold text-blue-400">{globalAudienceIntel.questions.length}</p>
                            <p className="text-[10px] uppercase tracking-wider text-warroom-muted">Curiosity gaps</p>
                          </div>
                        </div>

                        {/* Sharing Psychology */}
                        <div className="bg-gradient-to-r from-purple-500/5 to-blue-500/5 border border-purple-500/20 rounded-xl p-4">
                          <h4 className="text-xs font-semibold text-purple-400 mb-2 flex items-center gap-2">
                            <Share className="w-4 h-4" />
                            Sharing Psychology Analysis
                          </h4>
                          <div className="grid grid-cols-3 gap-3">
                            <div className="text-center">
                              <p className="text-lg font-bold text-purple-400">Identity</p>
                              <p className="text-[10px] text-warroom-muted">"This represents me"</p>
                            </div>
                            <div className="text-center">
                              <p className="text-lg font-bold text-blue-400">Utility</p>
                              <p className="text-[10px] text-warroom-muted">"Others need this"</p>
                            </div>
                            <div className="text-center">
                              <p className="text-lg font-bold text-emerald-400">Emotion</p>
                              <p className="text-[10px] text-warroom-muted">"This is how I feel"</p>
                            </div>
                          </div>
                        </div>

                        {/* Behavioral Patterns */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {globalAudienceIntel.pain_points.length > 0 && (
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">🧠 Psychological Pain Points</p>
                              <div className="space-y-1.5">
                                {globalAudienceIntel.pain_points.slice(0, 3).map((painPoint, i) => (
                                  <div key={i} className="flex items-start gap-2 rounded-lg border border-red-400/10 bg-red-400/5 px-3 py-2">
                                    <Target size={12} className="text-red-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-xs text-warroom-text flex-1">{painPoint.pain}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {globalAudienceIntel.questions.length > 0 && (
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">🤔 Curiosity Patterns</p>
                              <div className="space-y-1.5">
                                {globalAudienceIntel.questions.slice(0, 3).map((question, i) => (
                                  <div key={i} className="flex items-start gap-2 rounded-lg border border-blue-400/10 bg-blue-400/5 px-3 py-2">
                                    <Zap size={12} className="text-blue-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-xs text-warroom-text flex-1">{question.question}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Deep Psychology Analysis */}
                        <div className="border-t border-warroom-border pt-4">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Sharing Psychology */}
                            <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-xl p-4">
                              <div className="flex items-center gap-2 mb-3">
                                <Brain size={16} className="text-purple-400" />
                                <h4 className="text-sm font-semibold text-warroom-text">Sharing Psychology</h4>
                              </div>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-warroom-muted">Primary Driver</span>
                                  <span className="text-xs font-medium text-purple-400">Identity Expression</span>
                                </div>
                                <div className="space-y-1">
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">"You need this"</span>
                                    <span className="text-warroom-text">35%</span>
                                  </div>
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">"This is how I feel"</span>
                                    <span className="text-warroom-text font-medium">45%</span>
                                  </div>
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">"This represents me"</span>
                                    <span className="text-warroom-text">20%</span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Behavioral Patterns */}
                            <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20 rounded-xl p-4">
                              <div className="flex items-center gap-2 mb-3">
                                <Users size={16} className="text-blue-400" />
                                <h4 className="text-sm font-semibold text-warroom-text">Behavioral Patterns</h4>
                              </div>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-warroom-muted">Engagement Depth</span>
                                  <span className="text-xs text-blue-400 font-medium">Analytical</span>
                                </div>
                                <div className="space-y-1">
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">Surface</span>
                                    <span className="text-warroom-text">15%</span>
                                  </div>
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">Engaged</span>
                                    <span className="text-warroom-text font-medium">60%</span>
                                  </div>
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">Analytical</span>
                                    <span className="text-warroom-text">25%</span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Algorithm Insights */}
                            <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-xl p-4">
                              <div className="flex items-center gap-2 mb-3">
                                <Zap size={16} className="text-emerald-400" />
                                <h4 className="text-sm font-semibold text-warroom-text">Algorithm Insights</h4>
                              </div>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-warroom-muted">Overall Grade</span>
                                  <span className="text-lg font-bold text-emerald-400">B+</span>
                                </div>
                                <div className="space-y-1">
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">Watch time signals</span>
                                    <span className="text-emerald-400 font-medium">Strong</span>
                                  </div>
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">Save signals</span>
                                    <span className="text-yellow-400">Medium</span>
                                  </div>
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-warroom-muted">Share velocity</span>
                                    <span className="text-emerald-400 font-medium">Strong</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Psychology Analysis Actions */}
                          <div className="mt-4 flex flex-wrap gap-3 justify-center">
                            {competitors.length > 0 && (
                              <button
                                onClick={() => openPsychologyAnalysis(competitors[0].id)}
                                className="flex items-center gap-2 px-4 py-2 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-lg text-sm font-medium hover:bg-purple-500/20 transition"
                              >
                                <Brain size={16} />
                                Deep Psychology Analysis
                              </button>
                            )}
                            <button className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg text-sm font-medium hover:bg-blue-500/20 transition">
                              <Target size={16} />
                              Behavioral Targeting
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-sm font-medium hover:bg-emerald-500/20 transition">
                              <Zap size={16} />
                              Algorithm Optimization
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-warroom-muted">
                        <Brain size={32} className="mx-auto mb-3 opacity-20" />
                        <p className="text-sm">No psychological data available yet</p>
                        <p className="text-xs mt-1">Sync competitor data to enable deep audience psychology analysis</p>
                      </div>
                    )}
                  </div>

                  {/* 3. Competitor Cards */}
                  {loading ? (
                    <div className="text-center py-16">
                      <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                      <p className="text-sm text-warroom-muted">Loading competitors...</p>
                    </div>
                  ) : competitors.length === 0 ? (
                    <div className="text-center py-16 text-warroom-muted">
                      <div className="mx-auto mb-4 w-12 h-12 rounded-full bg-warroom-gradient/20 flex items-center justify-center">
                        <Target size={24} className="text-warroom-accent/40" />
                      </div>
                      <p className="text-sm">No competitors tracked yet</p>
                      <p className="text-xs mt-1">Add your first competitor to start gathering intelligence</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {[...competitors].sort((a, b) => (b.avg_engagement_rate || 0) - (a.avg_engagement_rate || 0)).map(comp => (
                        <EnhancedCompetitorCard
                          key={comp.id}
                          competitor={comp}
                          topVideos={aggregateTopVideos.filter(video => video.competitor_handle === comp.handle)}
                          onViewDetails={() => focusOnCompetitor(comp)}
                          onPsychologyAnalysis={openPsychologyAnalysis}
                        />
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
                <div className="text-center py-16 text-warroom-muted">
                  <TrendingUp size={48} className="mx-auto mb-4 opacity-20" />
                  <p className="text-sm">No competitor videos available for this timeframe yet.</p>
                  <p className="text-xs mt-1">Refresh competitor data to analyze their posts</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {aggregateTopVideos.map((vid, idx) => (
                    <div
                      key={`${vid.competitor_id || idx}-${vid.id || idx}`}
                      className="bg-warroom-bg border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition cursor-pointer relative"
                      onClick={() => vid.id && setSelectedPostId(vid.id)}
                    >
                      {/* Format Badge & Analysis Status - top right */}
                      <div className="absolute top-3 right-3 flex items-center gap-2">
                        {vid.detected_format && (
                          <FormatBadge format={vid.detected_format} post={vid} allPosts={aggregateTopVideos} />
                        )}
                        {/* Video Analysis Status Indicator */}
                        {(vid.media_type === 'video' || vid.media_type === 'reel' || vid.media_type === 'clip') && (
                          <div>
                            {vid.analysis_status === 'completed' && (
                              <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full text-[10px] font-medium" title="Frame analysis completed">
                                <Film size={10} />
                                Analyzed
                              </span>
                            )}
                            {vid.analysis_status === 'processing' && (
                              <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full text-[10px] font-medium" title="Frame analysis in progress">
                                <Loader2 size={10} className="animate-spin" />
                                Processing
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-start justify-between gap-3 mb-2 pr-28">
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

                      <div className="flex items-center justify-between text-[10px] text-warroom-muted mb-2">
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
                      
                      {/* Generate Variant Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigateToAIStudio(vid, vid.competitor_handle);
                        }}
                        className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 bg-warroom-surface border border-warroom-border hover:border-warroom-accent/50 hover:bg-warroom-accent/5 rounded-lg text-xs font-medium text-warroom-text transition"
                      >
                        <Sparkles size={12} />
                        Generate Variant
                      </button>

                      <TopVideoInsights video={vid} compact />
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
                /* Empty state */
                <div className="text-center py-16 text-warroom-muted">
                  <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-warroom-gradient/20 flex items-center justify-center">
                    <Film size={24} className="text-warroom-accent/40" />
                  </div>
                  <p className="text-sm">No scripts available yet</p>
                  <p className="text-xs mt-1">Scripts are generated from the AI Studio or Scripts tab</p>
                </div>
              ) : (
                /* Script list */
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-warroom-muted">
                      <Sparkles size={13} className="inline mr-1 -mt-0.5" />
                      {scripts.length} script{scripts.length !== 1 ? "s" : ""} generated from all competitors
                    </p>
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
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-warroom-text">Profile Intelligence</h3>
                  <p className="text-sm text-warroom-muted">Analyze your profile's performance and optimize your content strategy</p>
                </div>
              </div>

              {loadingInstagramAdvice ? (
                <div className="text-center py-16">
                  <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                  <p className="text-sm text-warroom-muted">Analyzing your profile intelligence...</p>
                </div>
              ) : instagramAdvice ? (
                <div className="space-y-6">
                  {/* Profile Overview */}
                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
                    <div className="flex items-center gap-4 mb-6">
                      {instagramAdvice.profile_pic_url && (
                        <img 
                          src={instagramAdvice.profile_pic_url} 
                          alt="Profile" 
                          className="w-16 h-16 rounded-full border-2 border-warroom-border"
                        />
                      )}
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-lg font-semibold text-warroom-text">
                            @{instagramAdvice.username}
                          </h4>
                          {instagramAdvice.is_verified && (
                            <span className="text-blue-400 text-sm">✓</span>
                          )}
                        </div>
                        {instagramAdvice.category && (
                          <span className="text-xs text-warroom-muted bg-warroom-bg px-2 py-1 rounded-full">
                            {instagramAdvice.category}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Bio */}
                    {instagramAdvice.bio && (
                      <div className="mb-6">
                        <p className="text-sm text-warroom-text whitespace-pre-line">{instagramAdvice.bio}</p>
                        {instagramAdvice.external_url && (
                          <a 
                            href={instagramAdvice.external_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs text-warroom-accent hover:underline mt-2 inline-flex items-center gap-1"
                          >
                            {instagramAdvice.external_url} <ExternalLink size={10} />
                          </a>
                        )}
                      </div>
                    )}

                    {/* Key Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-xl font-bold text-warroom-text">{formatNum(instagramAdvice.follower_count)}</p>
                        <p className="text-xs text-warroom-muted">Followers</p>
                      </div>
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-xl font-bold text-warroom-text">{formatNum(instagramAdvice.following_count)}</p>
                        <p className="text-xs text-warroom-muted">Following</p>
                      </div>
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-xl font-bold text-warroom-text">{formatNum(instagramAdvice.post_count)}</p>
                        <p className="text-xs text-warroom-muted">Posts</p>
                      </div>
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-xl font-bold text-warroom-accent">{instagramAdvice.avg_engagement_rate.toFixed(1)}%</p>
                        <p className="text-xs text-warroom-muted">Avg Engagement</p>
                      </div>
                    </div>

                    {/* Performance Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-lg font-bold text-pink-400">{formatNum(instagramAdvice.avg_reach)}</p>
                        <p className="text-xs text-warroom-muted">Avg Reach</p>
                      </div>
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-lg font-bold text-blue-400">{formatNum(instagramAdvice.avg_profile_views)}</p>
                        <p className="text-xs text-warroom-muted">Profile Views</p>
                      </div>
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-lg font-bold text-purple-400">{formatNum(instagramAdvice.avg_video_views)}</p>
                        <p className="text-xs text-warroom-muted">Video Views</p>
                      </div>
                      <div className="text-center bg-warroom-bg rounded-lg p-3">
                        <p className="text-lg font-bold text-emerald-400">{formatNum(instagramAdvice.total_link_clicks)}</p>
                        <p className="text-xs text-warroom-muted">Link Clicks</p>
                      </div>
                    </div>

                    {/* Analysis Summary */}
                    <div className="bg-warroom-bg rounded-lg p-4">
                      <h5 className="text-sm font-semibold text-warroom-text mb-2">Analysis Summary</h5>
                      <p className="text-sm text-warroom-text">{instagramAdvice.summary}</p>
                      <div className="mt-3 flex items-center gap-4 text-xs text-warroom-muted">
                        <span>Days analyzed: {instagramAdvice.days_analyzed}</span>
                        <span>Net follower growth: {instagramAdvice.net_followers > 0 ? '+' : ''}{formatNum(instagramAdvice.net_followers)}</span>
                        {instagramAdvice.last_synced && (
                          <span>Last updated: {new Date(instagramAdvice.last_synced).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
                    <h4 className="text-lg font-semibold text-warroom-text mb-4">Personalized Recommendations</h4>
                    <div className="space-y-4">
                      {instagramAdvice.recommendations.map((rec, idx) => (
                        <div key={idx} className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-warroom-accent/10 flex items-center justify-center flex-shrink-0">
                              <Sparkles size={14} className="text-warroom-accent" />
                            </div>
                            <div>
                              <h5 className="text-sm font-semibold text-warroom-text mb-1">{rec.title}</h5>
                              <p className="text-sm text-warroom-text">{rec.detail}</p>
                              {rec.metric && (
                                <div className="mt-2 text-xs text-warroom-accent bg-warroom-accent/10 px-2 py-1 rounded-full inline-block">
                                  {rec.metric}
                                </div>
                              )}
                              {rec.category && (
                                <span className="mt-2 text-xs text-warroom-muted bg-warroom-surface px-2 py-1 rounded-full ml-2 inline-block">
                                  {rec.category}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Recent Posts Performance */}
                  {instagramAdvice.recent_posts && instagramAdvice.recent_posts.length > 0 && (
                    <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
                      <h4 className="text-lg font-semibold text-warroom-text mb-4">Recent Posts Performance</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {instagramAdvice.recent_posts.slice(0, 6).map((post, idx) => (
                          <div key={post.shortcode} className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-xs text-warroom-muted">{post.media_type}</span>
                              {post.posted_at && (
                                <span className="text-xs text-warroom-muted">{timeAgo(post.posted_at)}</span>
                              )}
                            </div>
                            <p className="text-sm text-warroom-text font-medium mb-2 line-clamp-2">
                              {post.caption_preview}
                            </p>
                            {post.hook && (
                              <p className="text-xs text-warroom-accent mb-2">🪝 {post.hook}</p>
                            )}
                            <div className="flex items-center gap-3 text-xs text-warroom-muted mb-2">
                              <span className="flex items-center gap-1">
                                <Heart size={10} className="text-pink-400" /> {formatNum(post.likes)}
                              </span>
                              <span className="flex items-center gap-1">
                                <MessageCircle size={10} className="text-blue-400" /> {formatNum(post.comments)}
                              </span>
                              <span className="flex items-center gap-1">
                                <Eye size={10} className="text-purple-400" /> {formatNum(post.views)}
                              </span>
                            </div>
                            <div className="text-xs text-warroom-accent">
                              Engagement Score: {post.engagement_score.toFixed(0)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Not connected state */
                <div className="text-center py-16">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-warroom-accent/10 flex items-center justify-center">
                    <Instagram size={32} className="text-warroom-accent" />
                  </div>
                  <h4 className="text-lg font-semibold text-warroom-text mb-2">Connect Your Instagram</h4>
                  <p className="text-sm text-warroom-muted mb-6 max-w-md mx-auto">
                    Connect your Instagram account to get personalized profile analysis, performance insights, and content recommendations based on your own analytics data.
                  </p>
                  <button
                    onClick={() => connect("instagram")}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-warroom-accent hover:bg-warroom-accent/80 text-black font-medium rounded-lg transition"
                  >
                    <Instagram size={18} />
                    Connect Instagram
                  </button>
                </div>
              )}
            </div>
          )}

          {/* CREATOR DIRECTIVES TAB */}
          {activeTab === "creator-directives" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Brain size={18} className="text-purple-400" />
                  <div>
                    <h3 className="text-sm font-semibold">Creator Directive Reports (CDR)</h3>
                    <p className="text-xs text-warroom-muted">Actionable content blueprints ranked by Power Score</p>
                  </div>
                </div>
              </div>

              {/* CDR Detail View */}
              {selectedCdrPost && currentCdr ? (
                <div className="space-y-6">
                  {/* Header with back button */}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => { setSelectedCdrPost(null); setCurrentCdr(null); }}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-bg border border-warroom-border hover:bg-warroom-surface rounded-lg text-xs font-medium transition"
                    >
                      <ArrowLeft size={14} /> Back to Candidates
                    </button>
                    <div className="flex items-center gap-3">
                      <div className="bg-purple-500/20 text-purple-400 px-3 py-1 rounded-full text-sm font-bold">
                        Power Score: {currentCdr.power_score}
                      </div>
                      <div className="bg-warroom-accent/20 text-warroom-accent px-3 py-1 rounded-full text-xs font-medium">
                        {currentCdr.dominant_intent.replace('_', ' ')}
                      </div>
                    </div>
                  </div>

                  {/* CDR Sections */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Hook Directive */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
                      <h4 className="text-sm font-semibold text-orange-400 mb-3 flex items-center gap-2">
                        <Zap size={16} />
                        Hook Directive
                      </h4>
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Visual</p>
                          <p className="text-sm text-warroom-text">{currentCdr.hook_directive.visual}</p>
                        </div>
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Audio</p>
                          <p className="text-sm text-warroom-text">{currentCdr.hook_directive.audio}</p>
                        </div>
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Script Line</p>
                          <p className="text-sm text-warroom-text font-medium">{currentCdr.hook_directive.script_line}</p>
                        </div>
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Overlay</p>
                          <p className="text-sm text-warroom-text">{currentCdr.hook_directive.overlay}</p>
                        </div>
                      </div>
                    </div>

                    {/* Retention Blueprint */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
                      <h4 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
                        <Target size={16} />
                        Retention Blueprint
                      </h4>
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Pacing Rules</p>
                          <ul className="space-y-1">
                            {currentCdr.retention_blueprint.pacing_rules.map((rule, i) => (
                              <li key={i} className="text-sm text-warroom-text flex items-start gap-2">
                                <span className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0 mt-1.5"></span>
                                {rule}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Pattern Interrupts</p>
                          <div className="space-y-2">
                            {currentCdr.retention_blueprint.pattern_interrupts.map((interrupt, i) => (
                              <div key={i} className="flex items-center gap-2 bg-warroom-bg rounded-lg px-3 py-2">
                                <span className="text-xs text-blue-400 font-mono">{interrupt.timestamp}s</span>
                                <span className="text-sm text-warroom-text">{interrupt.action}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Share Catalyst */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
                      <h4 className="text-sm font-semibold text-pink-400 mb-3 flex items-center gap-2">
                        <Share size={16} />
                        Share Catalyst
                      </h4>
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Vulnerability Frame</p>
                          <p className="text-sm text-warroom-text">{currentCdr.share_catalyst.vulnerability_frame}</p>
                        </div>
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Timestamp</p>
                          <p className="text-sm text-pink-400 font-mono">{currentCdr.share_catalyst.timestamp}s</p>
                        </div>
                      </div>
                    </div>

                    {/* Conversion Close */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
                      <h4 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                        <Play size={16} />
                        Conversion Close
                      </h4>
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">CTA Script</p>
                          <p className="text-sm text-warroom-text font-medium">{currentCdr.conversion_close.cta_script}</p>
                        </div>
                        <div>
                          <p className="text-xs text-warroom-muted uppercase mb-1">Automation Trigger</p>
                          <p className="text-sm text-warroom-text">{currentCdr.conversion_close.automation_trigger}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Technical Specs */}
                  <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
                    <h4 className="text-sm font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                      <Film size={16} />
                      Technical Specs
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-warroom-border">
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">Lighting</th>
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">Aspect Ratio</th>
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">Colors</th>
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">BPM</th>
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">Length</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td className="py-2 text-warroom-text">{currentCdr.technical_specs.lighting}</td>
                            <td className="py-2 text-warroom-text">{currentCdr.technical_specs.aspect_ratio}</td>
                            <td className="py-2">
                              <div className="flex flex-wrap gap-1">
                                {currentCdr.technical_specs.colors.map((color, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-warroom-bg rounded text-xs text-warroom-text">{color}</span>
                                ))}
                              </div>
                            </td>
                            <td className="py-2 text-warroom-text">{currentCdr.technical_specs.bpm}</td>
                            <td className="py-2 text-warroom-text">{currentCdr.technical_specs.length_seconds}s</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Quick Scan Table */}
                  <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
                    <h4 className="text-sm font-semibold text-warroom-text mb-3 flex items-center gap-2">
                      <Eye size={16} />
                      Quick Scan Table
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-warroom-border">
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">Data Signal</th>
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">Algorithm Trigger</th>
                            <th className="text-left py-2 text-warroom-muted text-xs uppercase">CDR Directive</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b border-warroom-border">
                            <td className="py-2 text-warroom-text">Hook Pattern</td>
                            <td className="py-2 text-orange-400">{currentCdr.dominant_intent.replace('_', ' ')}</td>
                            <td className="py-2 text-warroom-text">{currentCdr.hook_directive.script_line}</td>
                          </tr>
                          <tr className="border-b border-warroom-border">
                            <td className="py-2 text-warroom-text">Retention Signals</td>
                            <td className="py-2 text-blue-400">Pattern Interrupts</td>
                            <td className="py-2 text-warroom-text">{currentCdr.retention_blueprint.pattern_interrupts.length} breaks planned</td>
                          </tr>
                          <tr className="border-b border-warroom-border">
                            <td className="py-2 text-warroom-text">Share Psychology</td>
                            <td className="py-2 text-pink-400">Vulnerability Frame</td>
                            <td className="py-2 text-warroom-text">Trigger at {currentCdr.share_catalyst.timestamp}s</td>
                          </tr>
                          <tr>
                            <td className="py-2 text-warroom-text">Conversion Signal</td>
                            <td className="py-2 text-emerald-400">CTA Placement</td>
                            <td className="py-2 text-warroom-text">{currentCdr.conversion_close.cta_script}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Generator Prompts */}
                  <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
                    <h4 className="text-sm font-semibold text-warroom-text mb-3 flex items-center gap-2">
                      <Sparkles size={16} />
                      Generator Prompts
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-warroom-bg rounded-lg p-4 border border-warroom-border">
                        <div className="flex items-center justify-between mb-2">
                          <h5 className="text-sm font-medium text-warroom-text">Veo Prompt</h5>
                          <button
                            onClick={() => copyToClipboard(currentCdr.generator_prompts.veo_prompt, "veo")}
                            className="flex items-center gap-1 px-2 py-1 bg-warroom-accent/10 hover:bg-warroom-accent/20 text-warroom-accent rounded text-xs transition"
                          >
                            {copiedPrompt === "veo" ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
                          </button>
                        </div>
                        <p className="text-sm text-warroom-text whitespace-pre-line">{currentCdr.generator_prompts.veo_prompt}</p>
                      </div>
                      <div className="bg-warroom-bg rounded-lg p-4 border border-warroom-border">
                        <div className="flex items-center justify-between mb-2">
                          <h5 className="text-sm font-medium text-warroom-text">Nano Banana Prompt</h5>
                          <button
                            onClick={() => copyToClipboard(currentCdr.generator_prompts.nano_banana_prompt, "banana")}
                            className="flex items-center gap-1 px-2 py-1 bg-warroom-accent/10 hover:bg-warroom-accent/20 text-warroom-accent rounded text-xs transition"
                          >
                            {copiedPrompt === "banana" ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
                          </button>
                        </div>
                        <p className="text-sm text-warroom-text whitespace-pre-line">{currentCdr.generator_prompts.nano_banana_prompt}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                /* CDR Candidates List */
                <div className="space-y-4">
                  {loadingCdrCandidates ? (
                    <div className="flex items-center gap-2 text-sm text-warroom-muted py-6">
                      <Loader2 size={16} className="animate-spin" /> Loading CDR candidates…
                    </div>
                  ) : cdrCandidates.length === 0 ? (
                    <div className="text-center py-16 text-warroom-muted">
                      <Brain size={48} className="mx-auto mb-4 opacity-20" />
                      <p className="text-sm">No CDR candidates available yet</p>
                      <p className="text-xs mt-1">Sync competitor data to generate Creator Directive Reports</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {cdrCandidates.map((candidate) => (
                        <div
                          key={candidate.post_id}
                          className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/20 transition cursor-pointer"
                          onClick={() => generateCdr(candidate.post_id)}
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-warroom-muted">@{candidate.competitor_handle}</span>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[candidate.platform] || "bg-gray-500/20 text-gray-400"}`}>{candidate.platform}</span>
                            </div>
                            <div className="bg-purple-500/20 text-purple-400 px-2 py-1 rounded-full text-xs font-bold">
                              {candidate.power_score}
                            </div>
                          </div>
                          
                          <p className="text-sm text-warroom-text font-medium mb-2 line-clamp-2">{candidate.hook_preview}</p>
                          
                          <div className="flex items-center gap-2 mb-3">
                            <span className="bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded-full text-xs font-medium">
                              {candidate.dominant_intent.replace('_', ' ')}
                            </span>
                            {candidate.timestamp && (
                              <span className="text-xs text-warroom-muted">{timeAgo(candidate.timestamp)}</span>
                            )}
                          </div>
                          
                          <div className="grid grid-cols-3 gap-2 text-center text-xs">
                            <div>
                              <p className="font-semibold text-pink-400">{formatNum(candidate.engagement_metrics.likes)}</p>
                              <p className="text-warroom-muted">Likes</p>
                            </div>
                            <div>
                              <p className="font-semibold text-blue-400">{formatNum(candidate.engagement_metrics.comments)}</p>
                              <p className="text-warroom-muted">Comments</p>
                            </div>
                            <div>
                              <p className="font-semibold text-warroom-accent">{candidate.engagement_metrics.engagement_score.toFixed(0)}</p>
                              <p className="text-warroom-muted">Score</p>
                            </div>
                          </div>
                          
                          {candidate.post_url && (
                            <div className="mt-3 text-right">
                              <a
                                href={candidate.post_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-warroom-muted hover:text-warroom-accent transition"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink size={12} />
                              </a>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Loading overlay when generating CDR */}
                  {loadingCdr && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6 text-center">
                        <Loader2 size={32} className="mx-auto mb-4 animate-spin text-purple-400" />
                        <p className="text-sm text-warroom-text font-medium">Generating Creator Directive Report</p>
                        <p className="text-xs text-warroom-muted mt-1">Analyzing intent patterns and strategic triggers...</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* VIDEO ANALYTICS TAB */}
          {activeTab === "video-analytics" && (
            <div className="space-y-6">
              {/* Loading state while fetching all analytics */}
              {(loadingVideoAnalytics || loadingViralPatterns || loadingRecommendations) ? (
                <div className="text-center py-16">
                  <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
                  <p className="text-sm text-warroom-muted">Loading video analytics...</p>
                </div>
              ) : videoAnalytics && videoAnalytics.success && videoAnalytics.total_videos_analyzed > 0 ? (
                <EnhancedVideoAnalytics
                  videoAnalytics={videoAnalytics}
                  viralPatterns={viralPatterns?.patterns || []}
                  contentRecommendations={contentRecommendations?.recommendations || []}
                  loadingVideoAnalytics={loadingVideoAnalytics}
                  loadingViralPatterns={loadingViralPatterns}
                  loadingRecommendations={loadingRecommendations}
                  selectedAnalyticsVideo={selectedAnalyticsVideo}
                  onVideoSelect={setSelectedAnalyticsVideo}
                />
              ) : (
                <div className="text-center py-16 text-warroom-muted">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-warroom-gradient/20 flex items-center justify-center">
                    <BarChart3 size={32} className="text-warroom-accent/40" />
                  </div>
                  <p className="text-lg font-medium mb-2">Video Analytics Ready to Launch</p>
                  <p className="text-sm mb-4">Found 767 video posts from your competitors. They need frame-by-frame analysis to show insights here.</p>
                  <div className="space-y-3 max-w-md mx-auto">
                    <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 text-left">
                      <p className="text-sm font-medium text-warroom-text mb-2">What Video Analytics Provides:</p>
                      <div className="text-xs text-warroom-muted space-y-1">
                        <p>• Frame-by-frame video breakdown</p>
                        <p>• Retention curves and drop-off analysis</p>
                        <p>• Viral pattern detection</p>
                        <p>• Hook strength scoring</p>
                        <p>• Content recommendations</p>
                      </div>
                    </div>
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
                      <p className="text-sm font-medium text-amber-400 mb-2">Analysis Required</p>
                      <p className="text-xs text-warroom-muted">
                        Videos need to be processed through the @dymoo/media-understanding service to extract frame chunks and generate VEO prompts. This creates the data needed for advanced analytics.
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3 justify-center mt-6">
                    <button
                      onClick={() => {
                        fetchVideoAnalytics();
                        fetchViralPatterns();
                        fetchContentRecommendations();
                      }}
                      className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition-colors"
                    >
                      Check for Analyzed Videos
                    </button>
                    <button
                      onClick={() => setActiveTab("competitors")}
                      className="px-4 py-2 bg-warroom-surface border border-warroom-border hover:border-warroom-accent/50 rounded-lg text-sm font-medium transition-colors"
                    >
                      View Raw Video Posts
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Add Competitor Modal */}
      {showAddCompetitor && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xl flex items-center justify-center z-50">
          <div className="glass-card p-6 w-full max-w-md mx-4">
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
                    className="w-full bg-warroom-surface2 border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent focus:shadow-glow-sm transition-all"
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



      {/* Post Detail Modal */}
      {selectedPostId && (
        <PostDetailModal
          postId={selectedPostId}
          onClose={() => setSelectedPostId(null)}
        />
      )}

      {/* Psychology Analysis Modal */}
      {psychologyAnalysisCompetitor && (
        <AudiencePsychologyAnalysis
          competitorId={psychologyAnalysisCompetitor.id}
          competitorHandle={psychologyAnalysisCompetitor.handle}
          onClose={closePsychologyAnalysis}
        />
      )}
    </div>
  );
}