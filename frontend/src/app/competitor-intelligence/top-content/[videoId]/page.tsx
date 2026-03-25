"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Film, FileText, BarChart3, Play, Loader2 } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import ScrollTabs from "@/components/ui/ScrollTabs";

interface VideoRecord {
  id: number;
  title: string;
  competitor_handle: string;
  platform: string;
  runtime_seconds?: number;
  likes: number;
  comments: number;
  shares?: number;
  engagement_score: number;
  posted_at?: string;
  url?: string;
}

// Format seconds to M:SS format
function formatRuntime(seconds?: number): string {
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function getPlatformIcon(platform: string) {
  switch (platform.toLowerCase()) {
    case "instagram":
      return "📷";
    case "tiktok":
      return "🎵";
    case "youtube":
      return "🎥";
    case "x":
      return "🐦";
    default:
      return "📱";
  }
}

export default function VideoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const videoId = params.videoId as string;

  const [activeTab, setActiveTab] = useState<"transcript" | "creator-directives" | "video-analytics">("transcript");
  const [videoRecord, setVideoRecord] = useState<VideoRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  // Load active tab from URL params
  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab && ["transcript", "creator-directives", "video-analytics"].includes(tab)) {
      setActiveTab(tab as typeof activeTab);
    }
  }, [searchParams]);

  // Update URL when tab changes
  const handleTabChange = (tab: string) => {
    setActiveTab(tab as typeof activeTab);
    const params = new URLSearchParams(searchParams);
    params.set("tab", tab);
    router.replace(`/competitor-intelligence/top-content/${videoId}?${params.toString()}`, { scroll: false });
  };

  // Fetch video record on mount
  useEffect(() => {
    const fetchVideoRecord = async () => {
      try {
        setLoading(true);
        setError("");
        
        const response = await authFetch(`${API}/api/content-intel/video/${videoId}`);
        
        if (response.ok) {
          const data = await response.json();
          setVideoRecord(data);
        } else {
          setError("Failed to load video details");
        }
      } catch (err) {
        setError("Error connecting to API");
      } finally {
        setLoading(false);
      }
    };

    fetchVideoRecord();
  }, [videoId]);

  const tabs = [
    { id: "transcript", label: "Transcript", icon: FileText },
    { id: "creator-directives", label: "Creator Directives", icon: Film },
    { id: "video-analytics", label: "Video Analytics", icon: BarChart3 },
  ];

  if (loading) {
    return (
      <div className="h-screen flex flex-col bg-warroom-bg text-warroom-text">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
            <p className="text-sm text-warroom-muted">Loading video details...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !videoRecord) {
    return (
      <div className="h-screen flex flex-col bg-warroom-bg text-warroom-text">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-sm text-red-400 mb-4">{error || "Video not found"}</p>
            <button
              onClick={() => router.push("/?tab=intelligence")}
              className="flex items-center gap-2 px-4 py-2 bg-warroom-surface border border-warroom-border rounded-lg text-sm font-medium hover:bg-warroom-border/50 transition"
            >
              <ArrowLeft size={16} />
              Back to Top Content
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-warroom-bg text-warroom-text overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-warroom-border p-6">
        <div className="flex items-start justify-between mb-4">
          <button
            onClick={() => router.push("/?tab=intelligence")}
            className="flex items-center gap-2 px-3 py-1.5 bg-warroom-surface border border-warroom-border rounded-lg text-sm font-medium hover:bg-warroom-border/50 transition"
          >
            <ArrowLeft size={16} />
            Back to Top Content
          </button>
        </div>

        {/* Video Title & Info */}
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 bg-warroom-gradient/20 rounded-xl flex items-center justify-center">
            <Play size={20} className="text-warroom-accent" />
          </div>
          
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-semibold text-warroom-text mb-2 line-clamp-2">
              {videoRecord.title}
            </h1>
            
            <div className="flex flex-wrap items-center gap-4 text-sm text-warroom-muted mb-4">
              <div className="flex items-center gap-2">
                <span className="text-base">{getPlatformIcon(videoRecord.platform)}</span>
                <span className="text-warroom-accent font-medium">@{videoRecord.competitor_handle}</span>
              </div>
              
              {videoRecord.runtime_seconds && (
                <div className="flex items-center gap-1">
                  <Film size={16} />
                  <span>{formatRuntime(videoRecord.runtime_seconds)}</span>
                </div>
              )}
              
              <div className="flex items-center gap-1">
                ❤️ <span>{formatNum(videoRecord.likes)}</span>
              </div>
              
              <div className="flex items-center gap-1">
                💬 <span>{formatNum(videoRecord.comments)}</span>
              </div>
              
              {videoRecord.shares && videoRecord.shares > 0 && (
                <div className="flex items-center gap-1">
                  🔄 <span>{formatNum(videoRecord.shares)}</span>
                </div>
              )}
            </div>
          </div>

          {videoRecord.url && (
            <a
              href={videoRecord.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 text-black rounded-lg text-sm font-medium transition"
            >
              View Original
            </a>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex-shrink-0">
        <ScrollTabs
          tabs={tabs}
          active={activeTab}
          onChange={handleTabChange}
        />
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "transcript" && (
          <div className="max-w-4xl mx-auto">
            <div className="text-center py-16 text-warroom-muted">
              <FileText size={48} className="mx-auto mb-4 opacity-20" />
              <p className="text-lg font-medium text-warroom-text">Transcript content will appear here</p>
              <p className="text-sm mt-2">Video transcript and analysis will be available in Wave 3</p>
            </div>
          </div>
        )}

        {activeTab === "creator-directives" && (
          <div className="max-w-4xl mx-auto">
            <div className="text-center py-16 text-warroom-muted">
              <Film size={48} className="mx-auto mb-4 opacity-20" />
              <p className="text-lg font-medium text-warroom-text">Creator directives will appear here</p>
              <p className="text-sm mt-2">Detailed creator directives and production specs will be available in Wave 3</p>
            </div>
          </div>
        )}

        {activeTab === "video-analytics" && (
          <div className="max-w-4xl mx-auto">
            <div className="text-center py-16 text-warroom-muted">
              <BarChart3 size={48} className="mx-auto mb-4 opacity-20" />
              <p className="text-lg font-medium text-warroom-text">Video analytics will appear here</p>
              <p className="text-sm mt-2">Performance metrics and analytical insights will be available in Wave 3</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}