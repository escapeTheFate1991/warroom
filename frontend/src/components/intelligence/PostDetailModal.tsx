"use client";

import { useEffect, useState } from "react";
import {
  X, ExternalLink, Heart, MessageCircle, Eye, Clock,
  Film, Image, Layers, Loader2, FileText, MessageSquare,
} from "lucide-react";
import { API as _API, authFetch } from "@/lib/api";

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
  const [activeTab, setActiveTab] = useState<"overview" | "transcript" | "comments">("overview");

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
            <div className="flex border-b border-warroom-border px-5">
              {[
                { key: "overview" as const, label: "Overview", icon: FileText },
                { key: "transcript" as const, label: `Transcript${hasTranscript ? ` (${post.transcript!.length})` : ""}`, icon: Film },
                { key: "comments" as const, label: `Audience Intel${hasComments ? ` (${post.comments_data!.analyzed})` : ""}`, icon: MessageSquare },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition ${
                    activeTab === tab.key
                      ? "border-warroom-accent text-warroom-accent"
                      : "border-transparent text-warroom-muted hover:text-warroom-text"
                  }`}
                >
                  <tab.icon size={12} />
                  {tab.label}
                </button>
              ))}
            </div>

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

              {/* Transcript Tab */}
              {activeTab === "transcript" && (
                <div>
                  {hasTranscript ? (
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
