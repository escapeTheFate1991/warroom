"use client";

import { useState, useEffect } from "react";
import { X, Filter, ChevronDown } from "lucide-react";
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

interface CompetitorScriptDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyScript: (script: string, preview: string) => void; // keep for backward compat
  onUseHook?: (hook: string) => void; // NEW - copies hook to parent
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

export default function CompetitorScriptDrawer({
  isOpen,
  onClose,
  onApplyScript,
  onUseHook,
  brandName = "",
  productName = "",
  targetAudience = "",
  keyMessage = ""
}: CompetitorScriptDrawerProps) {
  const [posts, setPosts] = useState<CompetitorPost[]>([]);
  const [topHooks, setTopHooks] = useState<{hook_text: string; handle: string; engagement_score: number; format: string}[]>([]);
  const [audienceDemands, setAudienceDemands] = useState<{theme: string; frequency: number}[]>([]);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Filters
  const [formatFilter, setFormatFilter] = useState("all");
  const [showFilters, setShowFilters] = useState(false);

  const fetchAggregateIntel = async () => {
    setLoading(true);
    try {
      const [scriptsResp, hooksResp] = await Promise.all([
        authFetch(`${API}/api/ai-studio/ugc/competitor-scripts?limit=30`),
        authFetch(`${API}/api/ai-studio/ugc/competitor-hooks`),
      ]);
      if (scriptsResp.ok) {
        const d = await scriptsResp.json();
        setPosts(d.scripts || []);
      }
      if (hooksResp.ok) {
        const d = await hooksResp.json();
        setTopHooks(d.hooks || []);
        setAudienceDemands(d.audience_demands || []);
      }
    } catch {}
    setLoading(false);
  };

  const copyHook = (hookText: string, idx: number) => {
    navigator.clipboard.writeText(hookText);
    setCopiedIdx(idx);
    if (onUseHook) onUseHook(hookText);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  // Filter posts by format
  const filteredPosts = formatFilter === "all" 
    ? posts 
    : posts.filter(post => post.format === formatFilter);

  useEffect(() => {
    if (isOpen) {
      fetchAggregateIntel();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[500px] bg-warroom-surface border-l border-warroom-border z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-warroom-border">
          <h2 className="text-sm font-semibold text-warroom-text">Competitor Intelligence</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-warroom-bg rounded transition"
          >
            <X size={16} className="text-warroom-muted" />
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-warroom-accent"></div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {/* Winning Hooks */}
            <div className="p-4 border-b border-warroom-border">
              <h3 className="text-xs font-semibold text-warroom-text mb-3">🏆 Top Performing Hooks</h3>
              <div className="space-y-2">
                {topHooks.slice(0, 5).map((h, i) => (
                  <button key={i} onClick={() => copyHook(h.hook_text, i)}
                    className="w-full text-left p-2 rounded-lg hover:bg-warroom-bg transition group">
                    <div className="flex items-start gap-2">
                      <span className="text-xs text-warroom-accent font-bold mt-0.5">{i + 1}.</span>
                      <div className="flex-1">
                        <p className="text-sm text-warroom-text leading-relaxed">"{h.hook_text}"</p>
                        <span className="text-[10px] text-warroom-muted">
                          @{h.handle} · {h.engagement_score?.toLocaleString()} engagement
                        </span>
                      </div>
                      {copiedIdx === i && (
                        <span className="text-[10px] text-emerald-400 font-medium">Copied!</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Audience Demands */}
            {audienceDemands.length > 0 && (
              <div className="p-4 border-b border-warroom-border">
                <h3 className="text-xs font-semibold text-warroom-text mb-2">📊 Audience Demand Signals</h3>
                <div className="flex flex-wrap gap-2">
                  {audienceDemands.map((d, i) => (
                    <span key={i} className="px-2 py-1 bg-warroom-bg rounded text-[10px] text-warroom-muted">
                      {d.theme} ({d.frequency}x)
                    </span>
                  ))}
                </div>
              </div>
            )}

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
              )}
            </div>

            {/* All Scripts as scrollable text */}
            <div className="p-4">
              <h3 className="text-xs font-semibold text-warroom-text mb-3">📝 All Scripts</h3>
              <div className="space-y-3">
                {filteredPosts.map((post, idx) => (
                  <button
                    key={post.post_id}
                    onClick={() => copyHook(post.hook, filteredPosts.length + idx)}
                    className="w-full text-left p-3 rounded-lg bg-warroom-bg hover:bg-warroom-surface transition group"
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-1">
                        <p className="text-sm text-warroom-text leading-relaxed mb-1">"{post.hook}"</p>
                        <div className="flex items-center gap-2 text-[10px] text-warroom-muted">
                          <span className={`px-1.5 py-0.5 rounded font-medium ${
                            post.format === "transformation" ? "bg-blue-500/10 text-blue-400" :
                            post.format === "myth_buster" ? "bg-red-500/10 text-red-400" :
                            post.format === "speed_run" ? "bg-yellow-500/10 text-yellow-400" :
                            post.format === "pov" ? "bg-purple-500/10 text-purple-400" :
                            post.format === "expose" ? "bg-orange-500/10 text-orange-400" :
                            post.format === "challenge" ? "bg-green-500/10 text-green-400" :
                            "bg-gray-500/10 text-gray-400"
                          }`}>
                            {post.format.replace("_", " ")}
                          </span>
                          <span>{post.engagement?.toLocaleString()} engagement</span>
                          {post.handle && <span>@{post.handle}</span>}
                        </div>
                      </div>
                      {copiedIdx === filteredPosts.length + idx && (
                        <span className="text-[10px] text-emerald-400 font-medium">Copied!</span>
                      )}
                    </div>
                  </button>
                ))}
                {filteredPosts.length === 0 && (
                  <p className="text-xs text-warroom-muted text-center py-8">
                    No scripts found for selected format
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}