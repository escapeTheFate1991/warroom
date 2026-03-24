"use client";

import { useEffect, useState } from "react";
import {
  X, ExternalLink, Heart, MessageCircle, Eye, Clock,
  Film, Image, Layers, Loader2, FileText, MessageSquare,
  Zap, Target, Megaphone, BarChart3,
} from "lucide-react";
import { API as _API, authFetch } from "@/lib/api";
import ScrollTabs from "@/components/ui/ScrollTabs";

// API imported from @/lib/api

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

interface CommentAnalysis {
  analyzed: number;
  sentiment: string;
  sentiment_breakdown: { positive: number; negative: number; neutral: number };
  avg_comment_likes: number;
  reply_rate: number;
  questions: { question: string; likes: number }[];
  pain_points: { pain: string; likes: number }[];
  product_mentions: { product: string; count: number }[];
  themes: { theme: string; count: number }[];
  top_commenters: { username: string; count: number }[];
  engagement_quality: string;
}

interface ContentAnalysis {
  is_clip?: boolean;
  hook: { text: string; start: number; end: number; type: string; strength: number };
  value: { text: string; start: number; end: number; key_points: string[] };
  cta: { text: string; start: number; end: number; type: string; phrase: string };
  total_duration: number;
  structure_score: number;
  full_script: string;
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

interface FrameAnalysisData {
  frame_chunks: FrameChunk[];
  video_analysis: VideoAnalysis;
  analyzed_at: string;
  total_chunks: number;
}

interface PostDetail {
  id: number;
  competitor_id: number;
  handle: string;
  shortcode: string;
  platform: string;
  post_text: string;
  hook: string;
  likes: number;
  comments: number;
  shares: number;
  engagement_score: number;
  media_type: string;
  media_url: string | null;
  thumbnail_url: string | null;
  post_url: string;
  posted_at: string | null;
  transcript: TranscriptSegment[] | null;
  comments_data: CommentAnalysis | null;
  content_analysis: ContentAnalysis | null;
  analysis_status?: "completed" | "processing" | "failed" | null;
  frame_chunks?: FrameChunk[];
  video_analysis?: VideoAnalysis | null;
  analyzed_at?: string;
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function timeAgo(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = (now.getTime() - d.getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 2592000) return `${Math.floor(diff / 86400)}d ago`;
    return `${Math.floor(diff / 2592000)}mo ago`;
  } catch {
    return "";
  }
}

function MediaTypeBadge({ type }: { type: string }) {
  const config: Record<string, { icon: typeof Film; label: string; color: string }> = {
    reel: { icon: Film, label: "Reel", color: "text-pink-400 bg-pink-400/10" },
    video: { icon: Film, label: "Video", color: "text-blue-400 bg-blue-400/10" },
    carousel: { icon: Layers, label: "Carousel", color: "text-purple-400 bg-purple-400/10" },
    image: { icon: Image, label: "Image", color: "text-green-400 bg-green-400/10" },
  };
  const c = config[type] || config.image;
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${c.color}`}>
      <Icon size={10} /> {c.label}
    </span>
  );
}

export default function PostDetailModal({
  postId,
  onClose,
}: {
  postId: number;
  onClose: () => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "transcript" | "comments" | "frames">("overview");
  const [frameAnalysisData, setFrameAnalysisData] = useState<FrameAnalysisData | null>(null);
  const [loadingFrames, setLoadingFrames] = useState(false);

  useEffect(() => {
    setLoading(true);
    authFetch(`${_API}/api/scraper/posts/${postId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setPost(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [postId]);

  // Function to fetch frame analysis data
  const fetchFrameAnalysis = async () => {
    if (!post || loadingFrames) return;
    
    setLoadingFrames(true);
    try {
      const response = await authFetch(`${_API}/api/competitors/videos/${post.id}/frames`);
      if (response.ok) {
        const data = await response.json();
        setFrameAnalysisData(data);
      }
    } catch (error) {
      console.error('Failed to load frame analysis:', error);
    } finally {
      setLoadingFrames(false);
    }
  };

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const hasTranscript = post?.transcript && post.transcript.length > 0;
  const hasComments = post?.comments_data && post.comments_data.analyzed > 0;
  const hasAnalysis = post?.content_analysis && post.content_analysis.structure_score > 0;
  const hasFrameAnalysis = post?.analysis_status === 'completed';
  const isVideoContent = post?.media_type === 'video' || post?.media_type === 'reel' || post?.media_type === 'clip';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative w-full max-w-2xl max-h-[85vh] bg-warroom-surface border border-warroom-border rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-warroom-border">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-warroom-text">Post Detail</h3>
            {post && <MediaTypeBadge type={post.media_type} />}
            {post && (
              <span className="text-xs text-warroom-muted">@{post.handle}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {post?.post_url && (
              <a
                href={post.post_url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg hover:bg-warroom-bg text-warroom-muted hover:text-warroom-accent transition"
                title="View on Instagram"
              >
                <ExternalLink size={14} />
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-warroom-bg text-warroom-muted hover:text-warroom-text transition"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="animate-spin text-warroom-accent" size={24} />
          </div>
        )}

        {/* Content */}
        {!loading && post && (
          <>
            {/* Tabs */}
            <ScrollTabs
              tabs={[
                { id: "overview", label: "Overview", icon: FileText },
                { id: "transcript", label: hasAnalysis ? "Script Analysis" : `Transcript${hasTranscript ? ` (${post.transcript!.length})` : ""}`, icon: hasAnalysis ? Zap : Film },
                { id: "comments", label: `Audience Intel${hasComments ? ` (${post.comments_data!.analyzed})` : ""}`, icon: MessageSquare },
                ...(hasFrameAnalysis && isVideoContent ? [{ id: "frames" as const, label: "Frame Analysis", icon: Film }] : []),
              ]}
              active={activeTab}
              onChange={(id) => {
                setActiveTab(id as any);
                if (id === "frames" && !frameAnalysisData && hasFrameAnalysis) {
                  fetchFrameAnalysis();
                }
              }}
              size="sm"
            />

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-5">
              {/* Overview Tab */}
              {activeTab === "overview" && (
                <div className="space-y-4">
                  {/* Stats row */}
                  <div className="flex items-center gap-4 text-xs text-warroom-muted">
                    <span className="flex items-center gap-1"><Heart size={12} className="text-red-400" /> {post.likes.toLocaleString()}</span>
                    <span className="flex items-center gap-1"><MessageCircle size={12} className="text-blue-400" /> {post.comments.toLocaleString()}</span>
                    {post.shares > 0 && <span className="flex items-center gap-1"><Eye size={12} className="text-green-400" /> {post.shares.toLocaleString()} views</span>}
                    <span className="flex items-center gap-1 ml-auto"><Clock size={12} /> {post.posted_at ? timeAgo(post.posted_at) : "Unknown"}</span>
                  </div>

                  {/* Hook */}
                  {post.hook && (
                    <div className="bg-warroom-accent/5 border border-warroom-accent/20 rounded-xl px-4 py-3">
                      <p className="text-[10px] uppercase tracking-wide text-warroom-accent mb-1">Hook</p>
                      <p className="text-sm text-warroom-text font-medium">{post.hook}</p>
                    </div>
                  )}

                  {/* Full caption */}
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1">Caption</p>
                    <p className="text-sm text-warroom-text whitespace-pre-line leading-relaxed">
                      {post.post_text || "No caption"}
                    </p>
                  </div>

                  {/* Engagement score */}
                  <div className="bg-warroom-bg rounded-xl px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-warroom-muted">Engagement Score</span>
                      <span className="text-lg font-bold text-warroom-accent">{Math.round(post.engagement_score).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Transcript / Script Analysis Tab */}
              {activeTab === "transcript" && (
                <div>
                  {hasAnalysis ? (() => {
                    const a = post.content_analysis!;
                    const scoreColor = a.structure_score >= 0.7 ? "text-green-400" : a.structure_score >= 0.4 ? "text-yellow-400" : "text-red-400";
                    const hookTypeColors: Record<string, string> = {
                      question: "bg-blue-400/10 text-blue-400",
                      curiosity_gap: "bg-purple-400/10 text-purple-400",
                      bold_claim: "bg-orange-400/10 text-orange-400",
                      shock_stat: "bg-red-400/10 text-red-400",
                      story: "bg-green-400/10 text-green-400",
                      direct_address: "bg-yellow-400/10 text-yellow-400",
                      controversy: "bg-pink-400/10 text-pink-400",
                      statement: "bg-warroom-border/30 text-warroom-muted",
                    };
                    const ctaTypeColors: Record<string, string> = {
                      engagement: "text-blue-400",
                      conversion: "text-green-400",
                      growth: "text-purple-400",
                      amplification: "text-orange-400",
                      none: "text-warroom-muted",
                    };
                    return (
                      <div className="space-y-4">
                        {/* Score bar */}
                        <div className="flex items-center justify-between bg-warroom-bg rounded-xl px-4 py-3">
                          <div className="flex items-center gap-2">
                            <BarChart3 size={14} className="text-warroom-muted" />
                            <span className="text-xs text-warroom-muted">Script Structure Score</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-24 h-2 bg-warroom-border rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${a.structure_score >= 0.7 ? "bg-green-400" : a.structure_score >= 0.4 ? "bg-yellow-400" : "bg-red-400"}`} style={{ width: `${a.structure_score * 100}%` }} />
                            </div>
                            <span className={`text-sm font-bold ${scoreColor}`}>{Math.round(a.structure_score * 100)}%</span>
                          </div>
                        </div>

                        {/* Clip Warning */}
                        {a.is_clip && (
                          <div className="flex items-center gap-2 bg-yellow-400/10 border border-yellow-400/20 rounded-xl px-4 py-2.5">
                            <span className="text-yellow-400 text-sm">⚠️</span>
                            <p className="text-xs text-yellow-300">
                              <span className="font-medium">Partial transcript</span> — Instagram served a short clip preview ({formatTimestamp(a.total_duration)}) instead of the full reel. Script analysis may be incomplete.
                            </p>
                          </div>
                        )}

                        {/* HOOK Section */}
                        <div className="border border-orange-400/20 bg-orange-400/5 rounded-xl px-4 py-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Zap size={14} className="text-orange-400" />
                              <span className="text-[10px] uppercase tracking-widest text-orange-400 font-bold">Hook</span>
                              <span className="text-[10px] text-warroom-muted">{formatTimestamp(a.hook.start)} – {formatTimestamp(a.hook.end)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${hookTypeColors[a.hook.type] || hookTypeColors.statement}`}>
                                {a.hook.type.replace("_", " ")}
                              </span>
                              <span className="text-[10px] text-warroom-muted">{Math.round(a.hook.strength * 100)}% str</span>
                            </div>
                          </div>
                          <p className="text-sm text-warroom-text font-medium leading-relaxed">"{a.hook.text}"</p>
                        </div>

                        {/* VALUE Section */}
                        <div className="border border-blue-400/20 bg-blue-400/5 rounded-xl px-4 py-3 space-y-2">
                          <div className="flex items-center gap-2">
                            <Target size={14} className="text-blue-400" />
                            <span className="text-[10px] uppercase tracking-widest text-blue-400 font-bold">Value / Message</span>
                            <span className="text-[10px] text-warroom-muted">{formatTimestamp(a.value.start)} – {formatTimestamp(a.value.end)}</span>
                          </div>
                          <p className="text-sm text-warroom-text leading-relaxed">{a.value.text}</p>
                          {a.value.key_points.length > 0 && (
                            <div className="mt-2 pt-2 border-t border-blue-400/10">
                              <p className="text-[10px] uppercase text-blue-400/70 mb-1">Key Points</p>
                              <ul className="space-y-1">
                                {a.value.key_points.map((kp, i) => (
                                  <li key={i} className="text-xs text-warroom-text flex items-start gap-2">
                                    <span className="text-blue-400 mt-0.5">•</span>
                                    <span>{kp}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>

                        {/* CTA Section */}
                        <div className={`border rounded-xl px-4 py-3 space-y-2 ${a.cta.type !== "none" ? "border-green-400/20 bg-green-400/5" : "border-warroom-border/30 bg-warroom-bg/50"}`}>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Megaphone size={14} className={a.cta.type !== "none" ? "text-green-400" : "text-warroom-muted"} />
                              <span className={`text-[10px] uppercase tracking-widest font-bold ${a.cta.type !== "none" ? "text-green-400" : "text-warroom-muted"}`}>
                                Call to Action
                              </span>
                              <span className="text-[10px] text-warroom-muted">{formatTimestamp(a.cta.start)} – {formatTimestamp(a.cta.end)}</span>
                            </div>
                            <span className={`text-[10px] capitalize ${ctaTypeColors[a.cta.type] || "text-warroom-muted"}`}>
                              {a.cta.type}
                            </span>
                          </div>
                          {a.cta.text ? (
                            <p className="text-sm text-warroom-text leading-relaxed">"{a.cta.text}"</p>
                          ) : (
                            <p className="text-xs text-warroom-muted italic">No clear CTA detected</p>
                          )}
                          {a.cta.phrase && (
                            <p className="text-[10px] text-green-400/70 italic">Trigger: "{a.cta.phrase}"</p>
                          )}
                        </div>

                        {/* Duration + raw transcript toggle */}
                        <div className="flex items-center justify-between text-[10px] text-warroom-muted pt-1">
                          <span>Duration: {formatTimestamp(a.total_duration)}</span>
                          {hasTranscript && (
                            <button
                              onClick={() => {
                                const el = document.getElementById("raw-transcript");
                                if (el) el.classList.toggle("hidden");
                              }}
                              className="text-warroom-accent hover:underline"
                            >
                              Toggle raw transcript
                            </button>
                          )}
                        </div>

                        {/* Raw transcript (hidden by default) */}
                        {hasTranscript && (
                          <div id="raw-transcript" className="hidden space-y-1 pt-2 border-t border-warroom-border">
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Raw Transcript</p>
                            {post.transcript!.map((seg, i) => (
                              <div key={i} className="flex gap-3 py-1 px-3 rounded-lg hover:bg-warroom-bg/50 transition">
                                <span className="text-[10px] font-mono text-warroom-accent w-12 flex-shrink-0 pt-0.5">
                                  {formatTimestamp(seg.start)}
                                </span>
                                <p className="text-xs text-warroom-text leading-relaxed">{seg.text}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })() : hasTranscript ? (
                    <div className="space-y-1">
                      {post.transcript!.map((seg, i) => (
                        <div
                          key={i}
                          className="flex gap-3 py-2 px-3 rounded-lg hover:bg-warroom-bg/50 transition group"
                        >
                          <span className="text-[10px] font-mono text-warroom-accent w-12 flex-shrink-0 pt-0.5">
                            {formatTimestamp(seg.start)}
                          </span>
                          <p className="text-sm text-warroom-text leading-relaxed">{seg.text}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <Film size={32} className="text-warroom-muted mx-auto mb-3" />
                      <p className="text-sm text-warroom-muted">
                        {post.media_type === "image" || post.media_type === "carousel"
                          ? "No transcript — this is not a video post"
                          : "No transcript yet — trigger transcription from Competitor Intel"}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Audience Intelligence Tab */}
              {activeTab === "comments" && (
                <div>
                  {hasComments ? (() => {
                    const data = post.comments_data!;
                    const sentimentColors: Record<string, string> = {
                      very_positive: "text-green-400", positive: "text-green-300",
                      neutral: "text-warroom-muted", negative: "text-orange-400", very_negative: "text-red-400",
                    };
                    return (
                      <div className="space-y-5">
                        {/* Sentiment + Stats Row */}
                        <div className="grid grid-cols-3 gap-3">
                          <div className="bg-warroom-bg rounded-xl p-3 text-center">
                            <p className={`text-lg font-bold capitalize ${sentimentColors[data.sentiment] || "text-warroom-text"}`}>
                              {data.sentiment.replace("_", " ")}
                            </p>
                            <p className="text-[10px] text-warroom-muted uppercase">Sentiment</p>
                          </div>
                          <div className="bg-warroom-bg rounded-xl p-3 text-center">
                            <p className="text-lg font-bold text-warroom-text">{data.analyzed}</p>
                            <p className="text-[10px] text-warroom-muted uppercase">Analyzed</p>
                          </div>
                          <div className="bg-warroom-bg rounded-xl p-3 text-center">
                            <p className="text-lg font-bold text-warroom-text capitalize">{data.engagement_quality}</p>
                            <p className="text-[10px] text-warroom-muted uppercase">Quality</p>
                          </div>
                        </div>

                        {/* Sentiment Breakdown Bar */}
                        {data.sentiment_breakdown && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1.5">Sentiment Breakdown</p>
                            <div className="flex h-2.5 rounded-full overflow-hidden bg-warroom-bg">
                              {data.sentiment_breakdown.positive > 0 && (
                                <div className="bg-green-400" style={{ width: `${(data.sentiment_breakdown.positive / data.analyzed) * 100}%` }} />
                              )}
                              {data.sentiment_breakdown.neutral > 0 && (
                                <div className="bg-warroom-border" style={{ width: `${(data.sentiment_breakdown.neutral / data.analyzed) * 100}%` }} />
                              )}
                              {data.sentiment_breakdown.negative > 0 && (
                                <div className="bg-red-400" style={{ width: `${(data.sentiment_breakdown.negative / data.analyzed) * 100}%` }} />
                              )}
                            </div>
                            <div className="flex justify-between text-[10px] text-warroom-muted mt-1">
                              <span className="text-green-400">👍 {data.sentiment_breakdown.positive}</span>
                              <span>😐 {data.sentiment_breakdown.neutral}</span>
                              <span className="text-red-400">👎 {data.sentiment_breakdown.negative}</span>
                            </div>
                          </div>
                        )}

                        {/* Questions from Audience */}
                        {data.questions && data.questions.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Questions from Audience</p>
                            <div className="space-y-1.5">
                              {data.questions.map((q, i) => (
                                <div key={i} className="flex items-start gap-2 bg-warroom-bg/50 rounded-lg px-3 py-2">
                                  <span className="text-blue-400 text-xs mt-0.5">❓</span>
                                  <p className="text-xs text-warroom-text flex-1">{q.question}</p>
                                  {q.likes > 0 && <span className="text-[10px] text-warroom-muted flex-shrink-0">👍 {q.likes}</span>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Pain Points */}
                        {data.pain_points && data.pain_points.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Pain Points</p>
                            <div className="space-y-1.5">
                              {data.pain_points.map((p, i) => (
                                <div key={i} className="flex items-start gap-2 bg-red-400/5 border border-red-400/10 rounded-lg px-3 py-2">
                                  <span className="text-red-400 text-xs mt-0.5">🎯</span>
                                  <p className="text-xs text-warroom-text flex-1">{p.pain}</p>
                                  {p.likes > 0 && <span className="text-[10px] text-warroom-muted flex-shrink-0">👍 {p.likes}</span>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Product Mentions */}
                        {data.product_mentions && data.product_mentions.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Product / Tool Mentions</p>
                            <div className="flex flex-wrap gap-1.5">
                              {data.product_mentions.map((p, i) => (
                                <span key={i} className="px-2.5 py-1 bg-purple-400/10 text-purple-400 rounded-full text-[10px]">
                                  {p.product} ({p.count})
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Themes */}
                        {data.themes && data.themes.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Comment Themes</p>
                            <div className="flex flex-wrap gap-1.5">
                              {data.themes.map((t, i) => (
                                <span key={i} className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full text-[10px]">
                                  {t.theme} ({t.count})
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Top Commenters */}
                        {data.top_commenters && data.top_commenters.length > 0 && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-2">Top Commenters</p>
                            <div className="flex flex-wrap gap-1.5">
                              {data.top_commenters.map((u, i) => (
                                <a key={i} href={`https://instagram.com/${u.username}`} target="_blank" rel="noopener noreferrer"
                                  className="px-2.5 py-1 bg-warroom-bg border border-warroom-border rounded-full text-[10px] text-warroom-text hover:border-warroom-accent/50 transition">
                                  @{u.username} ({u.count})
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })() : (
                    <div className="text-center py-12">
                      <MessageSquare size={32} className="text-warroom-muted mx-auto mb-3" />
                      <p className="text-sm text-warroom-muted">
                        No audience intel yet — trigger comment analysis from Competitor Intel
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Frame Analysis Tab */}
              {activeTab === "frames" && hasFrameAnalysis && isVideoContent && (
                <div>
                  {loadingFrames ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="animate-spin text-warroom-accent mr-2" size={20} />
                      <span className="text-sm text-warroom-muted">Loading frame analysis...</span>
                    </div>
                  ) : frameAnalysisData ? (
                    <div className="space-y-5">
                      {/* Overall Video Analysis Summary */}
                      {frameAnalysisData.video_analysis && (
                        <div className="bg-warroom-bg rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <Film size={16} className="text-warroom-accent" />
                            <h4 className="text-sm font-semibold">Video Analysis Summary</h4>
                          </div>
                          
                          {frameAnalysisData.video_analysis.summary && (
                            <p className="text-sm text-warroom-text mb-3">{frameAnalysisData.video_analysis.summary}</p>
                          )}
                          
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            {frameAnalysisData.video_analysis.total_duration && (
                              <div>
                                <p className="text-warroom-muted mb-1">Duration</p>
                                <p className="text-warroom-text font-medium">{formatTimestamp(frameAnalysisData.video_analysis.total_duration)}</p>
                              </div>
                            )}
                            {frameAnalysisData.video_analysis.content_style && (
                              <div>
                                <p className="text-warroom-muted mb-1">Content Style</p>
                                <p className="text-warroom-text font-medium capitalize">{frameAnalysisData.video_analysis.content_style}</p>
                              </div>
                            )}
                            {frameAnalysisData.video_analysis.production_quality && (
                              <div>
                                <p className="text-warroom-muted mb-1">Production Quality</p>
                                <p className="text-warroom-text font-medium capitalize">{frameAnalysisData.video_analysis.production_quality}</p>
                              </div>
                            )}
                          </div>

                          {frameAnalysisData.video_analysis.key_insights && frameAnalysisData.video_analysis.key_insights.length > 0 && (
                            <div className="mt-3">
                              <p className="text-warroom-muted text-xs mb-2">Key Insights</p>
                              <ul className="space-y-1">
                                {frameAnalysisData.video_analysis.key_insights.map((insight, i) => (
                                  <li key={i} className="text-xs text-warroom-text flex items-start gap-2">
                                    <span className="text-warroom-accent mt-0.5">•</span>
                                    <span>{insight}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {frameAnalysisData.video_analysis.dominant_themes && frameAnalysisData.video_analysis.dominant_themes.length > 0 && (
                            <div className="mt-3">
                              <p className="text-warroom-muted text-xs mb-2">Dominant Themes</p>
                              <div className="flex flex-wrap gap-1.5">
                                {frameAnalysisData.video_analysis.dominant_themes.map((theme, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded-full text-[10px]">
                                    {theme}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Frame Chunks Timeline */}
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Clock size={16} className="text-orange-400" />
                            <h4 className="text-sm font-semibold">Frame-by-Frame Timeline</h4>
                          </div>
                          <span className="text-xs text-warroom-muted">{frameAnalysisData.total_chunks} chunks</span>
                        </div>

                        <div className="space-y-3">
                          {frameAnalysisData.frame_chunks.map((chunk, i) => (
                            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                              <div className="flex items-start justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono text-warroom-accent bg-warroom-bg px-2 py-1 rounded">
                                    {formatTimestamp(chunk.start_time)} - {formatTimestamp(chunk.end_time)}
                                  </span>
                                  <span className="text-[10px] text-warroom-muted">
                                    ({chunk.duration}s)
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-full">
                                    {chunk.action_type}
                                  </span>
                                  <span className="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded-full">
                                    {chunk.pacing}
                                  </span>
                                </div>
                              </div>

                              <p className="text-sm text-warroom-text mb-3">{chunk.description}</p>

                              {chunk.visual_elements.length > 0 && (
                                <div className="mb-3">
                                  <p className="text-[10px] uppercase tracking-wide text-warroom-muted mb-1">Visual Elements</p>
                                  <div className="flex flex-wrap gap-1">
                                    {chunk.visual_elements.map((element, j) => (
                                      <span key={j} className="text-[10px] px-1.5 py-0.5 bg-green-500/10 text-green-400 rounded">
                                        {element}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* VEO Prompt - Collapsible */}
                              {chunk.veo_prompt && (
                                <details className="group">
                                  <summary className="cursor-pointer text-[10px] text-warroom-accent hover:text-warroom-accent/80 transition">
                                    <span className="group-open:hidden">Show VEO Prompt</span>
                                    <span className="hidden group-open:inline">Hide VEO Prompt</span>
                                  </summary>
                                  <div className="mt-2 p-3 bg-warroom-bg border border-warroom-border/50 rounded-lg">
                                    <p className="text-xs text-warroom-text font-mono leading-relaxed">{chunk.veo_prompt}</p>
                                  </div>
                                </details>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Analyzed At Timestamp */}
                      <div className="text-center pt-2 border-t border-warroom-border">
                        <p className="text-[10px] text-warroom-muted">
                          Analyzed at {new Date(frameAnalysisData.analyzed_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <Film size={32} className="text-warroom-muted mx-auto mb-3" />
                      <p className="text-sm text-warroom-muted">
                        Failed to load frame analysis data
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {/* Error state */}
        {!loading && !post && (
          <div className="flex items-center justify-center py-20">
            <p className="text-sm text-warroom-muted">Failed to load post detail</p>
          </div>
        )}
      </div>
    </div>
  );
}
