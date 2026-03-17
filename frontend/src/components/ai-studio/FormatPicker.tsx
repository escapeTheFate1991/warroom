"use client";

import { useState, useEffect } from "react";
import {
  Zap, Eye, Repeat, UserCircle, FastForward, Trophy, Play, Camera, Info, ChevronRight, X
} from "lucide-react";
import { authFetch, API } from "@/lib/api";

interface VideoFormat {
  slug: string;
  name: string;
  description: string;
  why_it_works: string;
  post_count: number;
  avg_engagement_score: number;
  icon: string; // Lucide icon name
}

interface CompetitorPost {
  handle: string;
  platform: string;
  text_excerpt: string;
  engagement: {
    likes: number;
    comments: number;
    shares: number;
  };
  hook?: string;
}

interface FormatPickerProps {
  onSelect: (format: VideoFormat) => void;
  selectedFormat?: string;
}

export default function FormatPicker({ onSelect, selectedFormat }: FormatPickerProps) {
  const [formats, setFormats] = useState<VideoFormat[]>([]);
  const [loading, setLoading] = useState(true);
  const [examplesOpen, setExamplesOpen] = useState(false);
  const [selectedFormatExamples, setSelectedFormatExamples] = useState<CompetitorPost[]>([]);
  const [loadingExamples, setLoadingExamples] = useState(false);
  const [examplesFormatSlug, setExamplesFormatSlug] = useState<string>("");

  // Hardcoded fallback data
  const fallbackFormats: VideoFormat[] = [
    {
      slug: "myth-buster",
      name: "Myth Buster",
      description: "Debunk common misconceptions in your industry",
      why_it_works: "People love having their beliefs challenged. Creates engagement through controversy and discussion.",
      post_count: 1247,
      avg_engagement_score: 8.4,
      icon: "Zap"
    },
    {
      slug: "expose",
      name: "The Exposé",
      description: "Reveal hidden truths or behind-the-scenes secrets",
      why_it_works: "Satisfies curiosity and positions you as an insider with exclusive knowledge.",
      post_count: 892,
      avg_engagement_score: 7.8,
      icon: "Eye"
    },
    {
      slug: "transformation",
      name: "Transformation",
      description: "Show dramatic before/after results",
      why_it_works: "Visual proof creates instant credibility and aspirational desire.",
      post_count: 2156,
      avg_engagement_score: 9.1,
      icon: "Repeat"
    },
    {
      slug: "pov",
      name: "POV",
      description: "Share your unique perspective on trending topics",
      why_it_works: "Personal viewpoints create relatability and invite discussion.",
      post_count: 1653,
      avg_engagement_score: 7.2,
      icon: "UserCircle"
    },
    {
      slug: "speed-run",
      name: "Speed Run",
      description: "Quick tutorials or rapid-fire tips",
      why_it_works: "Fast pace keeps attention, perfect for short attention spans.",
      post_count: 981,
      avg_engagement_score: 8.0,
      icon: "FastForward"
    },
    {
      slug: "challenge",
      name: "Challenge",
      description: "Test yourself or challenge others",
      why_it_works: "Interactive format encourages participation and user-generated content.",
      post_count: 743,
      avg_engagement_score: 7.6,
      icon: "Trophy"
    },
    {
      slug: "show-dont-tell",
      name: "Show Don't Tell",
      description: "Demonstrate rather than explain",
      why_it_works: "Visual learning is more engaging and memorable than verbal explanations.",
      post_count: 1421,
      avg_engagement_score: 8.7,
      icon: "Play"
    },
    {
      slug: "direct-to-camera",
      name: "Direct-to-Camera",
      description: "Authentic talking head style content",
      why_it_works: "Creates personal connection and builds trust through eye contact.",
      post_count: 2834,
      avg_engagement_score: 6.9,
      icon: "Camera"
    }
  ];

  // Icon mapping
  const getIcon = (iconName: string) => {
    const icons = {
      Zap: Zap,
      Eye: Eye,
      Repeat: Repeat,
      UserCircle: UserCircle,
      FastForward: FastForward,
      Trophy: Trophy,
      Play: Play,
      Camera: Camera
    };
    return icons[iconName as keyof typeof icons] || Camera;
  };

  useEffect(() => {
    loadFormats();
  }, []);

  const loadFormats = async () => {
    try {
      const response = await authFetch(`${API}/api/video-formats`);
      if (response.ok) {
        const data = await response.json();
        if (data.formats && data.formats.length > 0) {
          setFormats(data.formats);
        } else {
          setFormats(fallbackFormats);
        }
      } else {
        setFormats(fallbackFormats);
      }
    } catch {
      setFormats(fallbackFormats);
    } finally {
      setLoading(false);
    }
  };

  const loadExamples = async (formatSlug: string) => {
    setLoadingExamples(true);
    setExamplesFormatSlug(formatSlug);
    try {
      const response = await authFetch(`${API}/api/video-formats/${formatSlug}/examples`);
      if (response.ok) {
        const data = await response.json();
        setSelectedFormatExamples(data.examples || []);
      } else {
        // Fallback examples
        setSelectedFormatExamples([
          {
            handle: "example_creator",
            platform: "instagram",
            text_excerpt: "Wait, you guys are still doing it the old way? Let me show you what I discovered...",
            engagement: { likes: 15420, comments: 347, shares: 892 }
          },
          {
            handle: "viral_tips",
            platform: "tiktok", 
            text_excerpt: "Nobody talks about this but here's the secret that changed everything for me...",
            engagement: { likes: 28750, comments: 612, shares: 1205 }
          }
        ]);
      }
    } catch {
      setSelectedFormatExamples([]);
    } finally {
      setLoadingExamples(false);
    }
  };

  const openExamples = (format: VideoFormat) => {
    setExamplesOpen(true);
    loadExamples(format.slug);
  };

  const closeExamples = () => {
    setExamplesOpen(false);
    setSelectedFormatExamples([]);
    setExamplesFormatSlug("");
  };

  const handleUseHook = (post: CompetitorPost) => {
    // Pass the hook back to parent - this would need to be connected to the parent component
    console.log("Use hook:", post.text_excerpt);
    // For now, just close the drawer
    closeExamples();
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-warroom-accent"></div>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {formats.map((format) => {
          const IconComponent = getIcon(format.icon);
          const isSelected = selectedFormat === format.slug;
          
          return (
            <div
              key={format.slug}
              onClick={() => onSelect(format)}
              className={`
                relative bg-warroom-surface border rounded-xl p-4 cursor-pointer transition-all duration-200
                hover:border-warroom-accent/50 hover:shadow-glow-sm
                ${isSelected 
                  ? "border-warroom-accent ring-1 ring-warroom-accent/30 shadow-glow-sm" 
                  : "border-warroom-border"
                }
              `}
            >
              {/* Icon and Title */}
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
                  <IconComponent size={20} className="text-warroom-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-warroom-text truncate">
                      {format.name}
                    </h3>
                    <div className="group relative">
                      <Info size={12} className="text-warroom-muted hover:text-warroom-accent transition-colors cursor-help" />
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-warroom-surface border border-warroom-border rounded-lg text-xs text-warroom-text w-64 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity z-10 shadow-xl">
                        <div className="font-medium text-warroom-accent mb-1">Why it works:</div>
                        {format.why_it_works}
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-warroom-border"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Description */}
              <p className="text-xs text-warroom-muted mb-3 leading-relaxed">
                {format.description}
              </p>

              {/* Stats */}
              <div className="flex items-center justify-between text-xs text-warroom-muted mb-3">
                <span>{format.post_count.toLocaleString()} posts</span>
                <span>·</span>
                <span>{format.avg_engagement_score} avg score</span>
              </div>

              {/* See Examples Link */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  openExamples(format);
                }}
                className="flex items-center gap-1 text-xs text-warroom-accent hover:text-warroom-accent/80 transition-colors"
              >
                See Examples
                <ChevronRight size={12} />
              </button>

              {/* Selected Indicator */}
              {isSelected && (
                <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-warroom-accent flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-white"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Examples Drawer */}
      {examplesOpen && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div 
            className="flex-1 bg-black/30" 
            onClick={closeExamples}
          />
          
          {/* Drawer */}
          <div className="w-96 bg-warroom-surface border-l border-warroom-border animate-slide-in-right overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-warroom-border">
              <div>
                <h3 className="text-sm font-bold text-warroom-text">
                  {formats.find(f => f.slug === examplesFormatSlug)?.name} Examples
                </h3>
                <p className="text-xs text-warroom-muted mt-0.5">
                  Top competitor posts using this format
                </p>
              </div>
              <button
                onClick={closeExamples}
                className="p-2 rounded-lg hover:bg-warroom-bg transition-colors"
              >
                <X size={16} className="text-warroom-muted" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {loadingExamples ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-warroom-accent"></div>
                </div>
              ) : selectedFormatExamples.length === 0 ? (
                <div className="text-center py-8 text-warroom-muted">
                  <p className="text-sm">No examples found</p>
                  <p className="text-xs mt-1">Check back later for competitor examples</p>
                </div>
              ) : (
                selectedFormatExamples.slice(0, 5).map((post, index) => (
                  <div 
                    key={index}
                    className="bg-warroom-bg border border-warroom-border rounded-xl p-4 space-y-3"
                  >
                    {/* Header */}
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-warroom-accent/10 flex items-center justify-center">
                        <span className="text-xs font-bold text-warroom-accent">
                          @{post.handle.slice(0, 2).toUpperCase()}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-warroom-text">
                          @{post.handle}
                        </div>
                        <div className="text-xs text-warroom-muted capitalize">
                          {post.platform}
                        </div>
                      </div>
                    </div>

                    {/* Post Text */}
                    <p className="text-sm text-warroom-text leading-relaxed">
                      {post.text_excerpt}
                    </p>

                    {/* Engagement Stats */}
                    <div className="flex items-center gap-4 text-xs text-warroom-muted">
                      <span>❤️ {post.engagement.likes.toLocaleString()}</span>
                      <span>💬 {post.engagement.comments.toLocaleString()}</span>
                      <span>🔄 {post.engagement.shares.toLocaleString()}</span>
                    </div>

                    {/* Use Hook Button */}
                    <button
                      onClick={() => handleUseHook(post)}
                      className="w-full py-2 px-3 bg-warroom-accent/20 text-warroom-accent text-xs font-medium rounded-lg hover:bg-warroom-accent/30 transition-colors"
                    >
                      Use This Hook
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}