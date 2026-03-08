"use client";

import { useEffect, useState } from "react";
import {
  X, ExternalLink, Heart, MessageCircle, Eye, Clock,
  Film, Image, Layers, Loader2, ChevronRight, User,
  ThumbsUp, FileText, MessageSquare,
} from "lucide-react";
import { API as _API, authFetch } from "@/lib/api";

// API imported from @/lib/api

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

interface Comment {
  username: string;
  text: string;
  likes: number;
  timestamp: string | null;
  is_reply: boolean;
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
  comments_data: Comment[] | null;
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
  const hasComments = post?.comments_data && post.comments_data.length > 0;

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
                { key: "comments" as const, label: `Comments${hasComments ? ` (${post.comments_data!.length})` : ""}`, icon: MessageSquare },
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

              {/* Comments Tab */}
              {activeTab === "comments" && (
                <div>
                  {hasComments ? (
                    <div className="space-y-3">
                      {post.comments_data!.map((c, i) => (
                        <div
                          key={i}
                          className={`flex gap-3 py-2.5 px-3 rounded-xl ${
                            c.is_reply ? "ml-8 bg-warroom-bg/30" : "bg-warroom-bg/50"
                          }`}
                        >
                          <div className="w-7 h-7 rounded-full bg-warroom-border flex items-center justify-center flex-shrink-0">
                            <User size={12} className="text-warroom-muted" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <a
                                href={`https://instagram.com/${c.username}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-semibold text-warroom-accent hover:underline"
                              >
                                @{c.username}
                              </a>
                              {c.timestamp && (
                                <span className="text-[10px] text-warroom-muted">{timeAgo(c.timestamp)}</span>
                              )}
                            </div>
                            <p className="text-sm text-warroom-text leading-relaxed">{c.text}</p>
                            {c.likes > 0 && (
                              <div className="flex items-center gap-1 mt-1">
                                <ThumbsUp size={10} className="text-warroom-muted" />
                                <span className="text-[10px] text-warroom-muted">{c.likes}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <MessageSquare size={32} className="text-warroom-muted mx-auto mb-3" />
                      <p className="text-sm text-warroom-muted">
                        No comments scraped yet — trigger from Competitor Intel
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
