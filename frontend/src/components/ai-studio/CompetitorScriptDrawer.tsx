"use client";

import { useState, useEffect } from "react";
import { X, Filter, Search, ChevronDown, Target, ExternalLink, Eye } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface CompetitorPost {
  post_id: string;
  hook: string;
  body_preview: string;
  cta: string;
  format: string;
  likes: number;
  engagement: number;
  thumbnail_url?: string;
  media_url?: string;
  platform?: string;
  handle?: string;
}

interface CompetitorPostDetail {
  post_id: string;
  hook: string;
  body: string;
  cta: string;
  format: string;
  likes: number;
  engagement: number;
  thumbnail_url?: string;
  media_url?: string;
  platform?: string;
  handle?: string;
  transcript?: string;
  content_analysis?: {
    value?: string;
  };
}

interface GeneratedScript {
  hook: string;
  body: string;
  cta: string;
  visual_directions: string;
  total_duration: number;
}

interface CompetitorScriptDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyScript: (script: string, preview: string) => void;
  brandName?: string;
  productName?: string;
  targetAudience?: string;
  keyMessage?: string;
}

const FORMAT_OPTIONS = [
  { value: "all", label: "All Formats" },
  { value: "transformation", label: "Transformation" },
  { value: "speed_run", label: "Speed Run" },
  { value: "myth_buster", label: "Myth Buster" },
  { value: "pov", label: "POV" },
  { value: "expose", label: "The Exposé" },
  { value: "challenge", label: "Challenge" },
  { value: "show_dont_tell", label: "Show Don't Tell" },
  { value: "direct_to_camera", label: "Direct to Camera" },
];

const SORT_OPTIONS = [
  { value: "engagement", label: "Engagement" },
  { value: "likes", label: "Likes" },
  { value: "recent", label: "Recent" },
];

export default function CompetitorScriptDrawer({
  isOpen,
  onClose,
  onApplyScript,
  brandName = "",
  productName = "",
  targetAudience = "",
  keyMessage = ""
}: CompetitorScriptDrawerProps) {
  const [posts, setPosts] = useState<CompetitorPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedPost, setSelectedPost] = useState<CompetitorPostDetail | null>(null);
  const [expandedPost, setExpandedPost] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  
  // Filters
  const [formatFilter, setFormatFilter] = useState("all");
  const [sortBy, setSortBy] = useState("engagement");
  const [showFilters, setShowFilters] = useState(false);

  // Fetch competitor posts
  const fetchPosts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (formatFilter !== "all") {
        params.set("format", formatFilter);
      }
      params.set("limit", "20");
      
      const response = await authFetch(`${API}/api/ugc-studio/competitor-scripts?${params}`);
      if (response.ok) {
        const data = await response.json();
        const postsData = Array.isArray(data) ? data : data.posts || [];
        setPosts(postsData);
      } else {
        console.error("Failed to fetch competitor posts");
        // Fallback data for development
        setPosts([
          {
            post_id: "demo_1",
            hook: "Wait, you guys are still doing it the old way?",
            body_preview: "I just found this AI tool that's completely changing how agencies handle client reporting...",
            cta: "Link in bio, trust me on this one.",
            format: "transformation",
            likes: 15420,
            engagement: 8.2,
            thumbnail_url: "https://via.placeholder.com/400x400",
          },
          {
            post_id: "demo_2", 
            hook: "Nobody talks about this but...",
            body_preview: "The biggest mistake I see agencies making is manually creating reports for every client...",
            cta: "Check the link in my bio if you want to automate this.",
            format: "myth_buster",
            likes: 12340,
            engagement: 7.8,
            thumbnail_url: "https://via.placeholder.com/400x400",
          }
        ]);
      }
    } catch (error) {
      console.error("Error fetching posts:", error);
      setPosts([]);
    }
    setLoading(false);
  };

  // Fetch post detail
  const fetchPostDetail = async (postId: string) => {
    try {
      const response = await authFetch(`${API}/api/ugc-studio/competitor-scripts/${postId}/detail`);
      if (response.ok) {
        const data = await response.json();
        setSelectedPost(data);
      } else {
        // Fallback for demo
        setSelectedPost({
          post_id: postId,
          hook: "Wait, you guys are still doing it the old way?",
          body: "I just found this AI tool that's completely changing how agencies handle client reporting. Like, I used to spend 3 hours every week just pulling data from different platforms, formatting everything, making it look pretty for clients. Now this thing does it all automatically. The reports actually look better than what I was making by hand, and it takes 30 seconds instead of 3 hours.",
          cta: "Link in bio, trust me on this one.",
          format: "transformation",
          likes: 15420,
          engagement: 8.2,
          thumbnail_url: "https://via.placeholder.com/400x400",
          transcript: "Full transcript would appear here...",
          content_analysis: {
            value: "Analysis of the content structure and key messaging points..."
          }
        });
      }
    } catch (error) {
      console.error("Error fetching post detail:", error);
    }
  };

  // Generate script from competitor post
  const generateScript = async (postId: string) => {
    setGenerating(true);
    try {
      const response = await authFetch(`${API}/api/ugc-studio/generate-script`, {
        method: "POST",
        body: JSON.stringify({
          reference_post_id: postId,
          brand_name: brandName,
          product_name: productName,
          target_audience: targetAudience,
          key_message: keyMessage
        })
      });

      if (response.ok) {
        const data: GeneratedScript = await response.json();
        const fullScript = `${data.hook}\n\n${data.body}\n\n${data.cta}`;
        const preview = data.hook.substring(0, 50) + "...";
        onApplyScript(fullScript, preview);
        onClose();
      } else {
        // Fallback for demo
        const post = posts.find(p => p.post_id === postId);
        if (post) {
          const demoScript = `${post.hook}\n\nAdapted for ${productName || "your product"} - ${post.body_preview}\n\n${post.cta}`;
          onApplyScript(demoScript, post.hook.substring(0, 50) + "...");
          onClose();
        }
      }
    } catch (error) {
      console.error("Error generating script:", error);
    }
    setGenerating(false);
  };

  useEffect(() => {
    if (isOpen) {
      fetchPosts();
    }
  }, [isOpen, formatFilter, sortBy]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[400px] bg-warroom-surface border-l border-warroom-border z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-warroom-border">
          <h2 className="text-sm font-semibold text-warroom-text">Competitor Intel Library</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-warroom-bg rounded transition"
          >
            <X size={16} className="text-warroom-muted" />
          </button>
        </div>

        {/* Filters */}
        <div className="p-4 border-b border-warroom-border">
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-1 px-2 py-1 bg-warroom-bg border border-warroom-border rounded text-xs text-warroom-muted hover:text-warroom-text transition"
            >
              <Filter size={12} />
              Filters
              <ChevronDown size={12} className={`transition-transform ${showFilters ? "rotate-180" : ""}`} />
            </button>
          </div>

          {showFilters && (
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Format</label>
                <select
                  value={formatFilter}
                  onChange={(e) => setFormatFilter(e.target.value)}
                  className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                >
                  {FORMAT_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Sort By</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                >
                  {SORT_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Posts List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-warroom-accent"></div>
            </div>
          ) : posts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-warroom-muted">
              <Search size={24} className="mb-2" />
              <p className="text-xs">No competitor posts found</p>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {posts.map((post) => (
                <div
                  key={post.post_id}
                  className="bg-warroom-bg border border-warroom-border rounded-lg p-3 hover:border-warroom-accent/30 transition cursor-pointer"
                  onClick={() => {
                    if (expandedPost === post.post_id) {
                      setExpandedPost(null);
                      setSelectedPost(null);
                    } else {
                      setExpandedPost(post.post_id);
                      fetchPostDetail(post.post_id);
                    }
                  }}
                >
                  {/* Card Header */}
                  <div className="flex gap-3 mb-2">
                    {post.thumbnail_url && (
                      <div className="w-12 h-12 rounded bg-warroom-surface border border-warroom-border overflow-hidden flex-shrink-0">
                        <img 
                          src={post.thumbnail_url} 
                          alt="Thumbnail" 
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-warroom-text font-medium line-clamp-2 mb-1">
                        "{post.hook}"
                      </p>
                      <div className="flex items-center gap-2 text-[10px] text-warroom-muted">
                        <span className={`px-1.5 py-0.5 rounded font-medium ${
                          post.format === "transformation" ? "bg-blue-500/10 text-blue-400" :
                          post.format === "myth_buster" ? "bg-red-500/10 text-red-400" :
                          post.format === "speed_run" ? "bg-yellow-500/10 text-yellow-400" :
                          "bg-gray-500/10 text-gray-400"
                        }`}>
                          {post.format.replace("_", " ")}
                        </span>
                        <span>❤️ {post.likes?.toLocaleString()}</span>
                        <span>📊 {post.engagement?.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Action Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      generateScript(post.post_id);
                    }}
                    disabled={generating}
                    className="w-full py-2 bg-warroom-accent/10 border border-warroom-accent/30 text-warroom-accent text-xs rounded hover:bg-warroom-accent/20 transition flex items-center justify-center gap-1 disabled:opacity-50"
                  >
                    <Target size={12} />
                    {generating ? "Applying..." : "Apply Structure"}
                  </button>

                  {/* Expanded Preview */}
                  {expandedPost === post.post_id && selectedPost && (
                    <div className="mt-3 pt-3 border-t border-warroom-border space-y-3">
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-1">Full Hook</p>
                        <p className="text-xs text-warroom-text">{selectedPost.hook}</p>
                      </div>
                      
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-1">Body Preview</p>
                        <p className="text-xs text-warroom-muted">{selectedPost.body || post.body_preview}</p>
                      </div>
                      
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-1">CTA</p>
                        <p className="text-xs text-warroom-text">{selectedPost.cta}</p>
                      </div>

                      {selectedPost.transcript && (
                        <div>
                          <details>
                            <summary className="text-[10px] uppercase tracking-wider text-warroom-muted cursor-pointer hover:text-warroom-accent transition">
                              See Full Transcript
                            </summary>
                            <p className="text-xs text-warroom-muted mt-2">{selectedPost.transcript}</p>
                          </details>
                        </div>
                      )}

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          generateScript(post.post_id);
                        }}
                        disabled={generating}
                        className="w-full py-2 bg-warroom-accent text-white text-xs rounded hover:bg-warroom-accent/80 transition flex items-center justify-center gap-1 disabled:opacity-50"
                      >
                        🎯 Apply to Script
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}