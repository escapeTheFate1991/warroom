"use client";

import { useState, useEffect, useCallback } from "react";
import {
  GraduationCap, Link, Send, Loader2, CheckCircle, AlertCircle,
  Clock, User, Hash, Calendar, ExternalLink, Eye, Trash2, RefreshCw,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";
const ML_API = API + "/api/ml"; // Mental Library via WAR ROOM backend

interface Video {
  id: number;
  url: string;
  title: string;
  author: string;
  duration: number;
  processed_at: string;
  topic_tags: string[];
  chunk_count: number;
}

interface ProcessingTask {
  taskId: string;
  status: string;
  progress: number;
  message: string;
}

const PLATFORMS = [
  { name: "YouTube", icon: "📺" },
  { name: "Instagram", icon: "📷" },
  { name: "TikTok", icon: "🎵" },
  { name: "X/Twitter", icon: "🐦" },
];

const formatDuration = (seconds: number): string => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
};

const timeAgo = (date: string): string => {
  const diff = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

const getPlatformIcon = (url: string): string => {
  if (url.includes("youtube.com") || url.includes("youtu.be")) return "📺";
  if (url.includes("instagram.com")) return "📷";
  if (url.includes("tiktok.com")) return "🎵";
  if (url.includes("twitter.com") || url.includes("x.com")) return "🐦";
  return "🎬";
};

const getThumbnail = (url: string): string | null => {
  if (url.includes("youtube.com/watch?v=")) {
    const id = url.split("v=")[1]?.split("&")[0];
    return id ? `https://img.youtube.com/vi/${id}/mqdefault.jpg` : null;
  }
  if (url.includes("youtu.be/")) {
    const id = url.split("youtu.be/")[1]?.split("?")[0];
    return id ? `https://img.youtube.com/vi/${id}/mqdefault.jpg` : null;
  }
  return null;
};

export default function EducatePanel() {
  const [url, setUrl] = useState("");
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(false);
  const [task, setTask] = useState<ProcessingTask | null>(null);
  const [error, setError] = useState("");

  const loadVideos = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await fetch(`${ML_API}/videos`);
      if (resp.ok) setVideos(await resp.json());
    } catch {
      console.error("Failed to load videos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadVideos(); }, [loadVideos]);

  // Poll task status
  useEffect(() => {
    if (!task || task.status === "completed" || task.status === "error") return;
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`${ML_API}/videos/status/${task.taskId}`);
        if (resp.ok) {
          const data = await resp.json();
          setTask({ taskId: data.task_id, status: data.status, progress: data.progress, message: data.message });
          if (data.status === "completed" || data.status === "error") {
            setTimeout(() => { setTask(null); loadVideos(); }, 2000);
          }
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [task, loadVideos]);

  const submitVideo = async () => {
    const trimmed = url.trim();
    if (!trimmed) return;
    setError("");
    try {
      const resp = await fetch(`${ML_API}/videos/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: trimmed }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setTask({ taskId: data.task_id, status: data.status, progress: 0, message: data.message });
        setUrl("");
      } else {
        const err = await resp.json();
        setError(err.detail || "Failed to start processing");
      }
    } catch {
      setError("Network error — is the mental library backend running?");
    }
  };

  const deleteVideo = async (id: number) => {
    if (!confirm("Delete this video from the library?")) return;
    try {
      await fetch(`${ML_API}/videos/${id}`, { method: "DELETE" });
      setVideos((prev) => prev.filter((v) => v.id !== id));
    } catch {}
  };

  const totalChunks = videos.reduce((s, v) => s + (v.chunk_count || 0), 0);
  const totalMinutes = Math.round(videos.reduce((s, v) => s + (v.duration || 0), 0) / 60);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <div className="flex items-center gap-2">
          <GraduationCap size={20} className="text-warroom-accent" />
          <h2 className="text-sm font-semibold">Educate</h2>
        </div>
        <button onClick={loadVideos} disabled={loading} className="text-warroom-muted hover:text-warroom-text transition">
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Video URL Input */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5">
          <p className="text-sm text-warroom-muted mb-3">
            Paste a video URL to download, transcribe, and add to your knowledge base.
          </p>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Link size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
              <input
                value={url}
                onChange={(e) => { setUrl(e.target.value); setError(""); }}
                onKeyDown={(e) => e.key === "Enter" && submitVideo()}
                placeholder="https://www.youtube.com/watch?v=..."
                disabled={!!task}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent disabled:opacity-50"
              />
            </div>
            <button
              onClick={submitVideo}
              disabled={!url.trim() || !!task}
              className="px-5 py-2.5 bg-warroom-accent rounded-lg text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-30 flex items-center gap-2 transition"
            >
              {task ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              Process
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 mt-3 text-warroom-danger text-xs">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          {/* Platform badges */}
          <div className="flex gap-2 mt-3">
            {PLATFORMS.map((p) => (
              <span key={p.name} className="text-[10px] bg-warroom-border/50 text-warroom-muted px-2 py-1 rounded-full">
                {p.icon} {p.name}
              </span>
            ))}
          </div>
        </div>

        {/* Progress bar */}
        {task && (
          <div className={`rounded-xl p-4 border ${
            task.status === "completed" ? "bg-green-900/10 border-green-800/50" :
            task.status === "error" ? "bg-red-900/10 border-red-800/50" :
            "bg-warroom-accent/5 border-warroom-accent/20"
          }`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm">
                {task.status === "completed" ? <CheckCircle size={16} className="text-warroom-success" /> :
                 task.status === "error" ? <AlertCircle size={16} className="text-warroom-danger" /> :
                 <Loader2 size={16} className="animate-spin text-warroom-accent" />}
                <span className="capitalize">{task.status}</span>
              </div>
              <span className="text-xs text-warroom-muted">{Math.round(task.progress)}%</span>
            </div>
            <div className="w-full bg-warroom-border rounded-full h-1.5 mb-2">
              <div
                className={`h-1.5 rounded-full transition-all duration-500 ${
                  task.status === "completed" ? "bg-warroom-success" :
                  task.status === "error" ? "bg-warroom-danger" :
                  "bg-warroom-accent"
                }`}
                style={{ width: `${task.progress}%` }}
              />
            </div>
            <p className="text-xs text-warroom-muted">{task.message}</p>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Videos", value: videos.length, color: "text-warroom-accent" },
            { label: "Chunks", value: totalChunks, color: "text-warroom-success" },
            { label: "Duration", value: `${totalMinutes}m`, color: "text-purple-400" },
          ].map((stat) => (
            <div key={stat.label} className="bg-warroom-surface border border-warroom-border rounded-lg p-3 text-center">
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
              <p className="text-[10px] text-warroom-muted uppercase tracking-wider">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Video Grid */}
        {videos.length === 0 && !loading ? (
          <div className="text-center py-16 text-warroom-muted">
            <GraduationCap size={48} className="mx-auto mb-4 opacity-20" />
            <p className="text-sm">No videos yet. Paste a URL above to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {videos.map((video) => {
              const thumb = (video as any).thumbnail_url || getThumbnail(video.url);
              return (
                <div key={video.id} className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden hover:border-warroom-accent/30 transition group">
                  {/* Thumbnail */}
                  <div className="relative h-36 bg-warroom-bg">
                    {thumb ? (
                      <img src={thumb} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-3xl opacity-30">
                        {getPlatformIcon(video.url)}
                      </div>
                    )}
                    <span className="absolute top-2 left-2 bg-black/70 px-1.5 py-0.5 rounded text-xs">
                      {getPlatformIcon(video.url)}
                    </span>
                    <span className="absolute bottom-2 right-2 bg-black/70 px-1.5 py-0.5 rounded text-xs flex items-center gap-1">
                      <Clock size={10} /> {formatDuration(video.duration)}
                    </span>
                  </div>

                  {/* Content */}
                  <div className="p-3">
                    <h3 className="text-sm font-medium line-clamp-2 leading-tight mb-1">{video.title}</h3>
                    <div className="flex items-center gap-1 text-xs text-warroom-muted mb-2">
                      <User size={10} /> <span className="truncate">{video.author}</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-warroom-muted mb-3">
                      <span className="flex items-center gap-1"><Hash size={10} /> {video.chunk_count} chunks</span>
                      <span className="flex items-center gap-1"><Calendar size={10} /> {timeAgo(video.processed_at)}</span>
                    </div>

                    {/* Tags */}
                    {video.topic_tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-3">
                        {video.topic_tags.slice(0, 3).map((tag, i) => (
                          <span key={i} className="text-[10px] bg-warroom-accent/10 text-warroom-accent px-1.5 py-0.5 rounded-full">{tag}</span>
                        ))}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2">
                      <a href={video.url} target="_blank" rel="noopener noreferrer"
                        className="flex-1 text-center bg-warroom-border/50 hover:bg-warroom-border py-1.5 rounded text-xs font-medium transition flex items-center justify-center gap-1">
                        <ExternalLink size={10} /> Original
                      </a>
                      <button onClick={() => deleteVideo(video.id)}
                        className="bg-warroom-danger/10 hover:bg-warroom-danger/20 text-warroom-danger py-1.5 px-3 rounded text-xs transition">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
