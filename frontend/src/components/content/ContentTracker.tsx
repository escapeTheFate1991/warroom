"use client";

import { useState, useEffect } from "react";
import {
  BarChart3, Eye, Heart, MessageSquare, Share2, ExternalLink,
  TrendingUp, Film, CheckCircle2, Lightbulb,
} from "lucide-react";

interface TrackedContent {
  id: string;
  title: string;
  platform: string;
  stage: string;
  views?: number;
  likes?: number;
  comments?: number;
  engagement?: number;
  thumbnail?: string;
  postedAt?: string;
  url?: string;
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

export default function ContentTracker() {
  const [allContent, setAllContent] = useState<TrackedContent[]>([]);

  useEffect(() => {
    // Aggregate from all platform pipelines
    const platforms = ["instagram", "youtube"];
    const all: TrackedContent[] = [];
    
    for (const p of platforms) {
      try {
        const stored = localStorage.getItem(`warroom_content_${p}`);
        if (stored) {
          const cards = JSON.parse(stored);
          all.push(...cards.map((c: any) => ({ ...c, platform: p })));
        }
      } catch {}
    }

    // Also check the shared pipeline
    try {
      const shared = localStorage.getItem("warroom_content_pipeline");
      if (shared) {
        const cards = JSON.parse(shared);
        all.push(...cards);
      }
    } catch {}

    setAllContent(all);
  }, []);

  const posted = allContent.filter(c => c.stage === "posted");
  const inProduction = allContent.filter(c => ["scripted", "filming", "editing", "scheduled"].includes(c.stage));
  const ideas = allContent.filter(c => c.stage === "idea");

  // Top performing (sort by views, fake data for now if none)
  const topPerforming = posted.length > 0 ? posted : [
    { id: "1", title: "My client went from $2K to $18K/month...", platform: "instagram", stage: "posted", views: 7200, likes: 340, comments: 28 },
    { id: "2", title: "The Content System I Used to...", platform: "instagram", stage: "posted", views: 5100, likes: 220, comments: 15 },
    { id: "3", title: "Bro this is a SCAM 😂", platform: "youtube", stage: "posted", views: 4800, likes: 190, comments: 42 },
    { id: "4", title: "I shut down my $80K/yr agency...", platform: "youtube", stage: "posted", views: 3200, likes: 150, comments: 12 },
    { id: "5", title: "The exact offer I changed...", platform: "instagram", stage: "posted", views: 2800, likes: 130, comments: 9 },
  ] as TrackedContent[];

  const maxViews = Math.max(...topPerforming.map(c => c.views || 0), 1);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <BarChart3 size={18} className="text-warroom-accent" />
        <h2 className="text-lg font-bold">Content Tracker</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "TOTAL PIECES", value: allContent.length, color: "text-warroom-accent" },
            { label: "PUBLISHED", value: posted.length, color: "text-green-400" },
            { label: "IN PRODUCTION", value: inProduction.length, color: "text-purple-400" },
            { label: "IDEAS", value: ideas.length, color: "text-orange-400" },
          ].map((s, i) => (
            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-[10px] text-warroom-muted tracking-wider mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Top Performing Content — Bar Chart */}
        <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
          <h3 className="text-xs text-warroom-muted font-bold tracking-widest mb-4">TOP PERFORMING CONTENT</h3>
          <div className="flex items-end gap-3 h-[200px]">
            {topPerforming.slice(0, 6).map((content, i) => {
              const height = ((content.views || 0) / maxViews) * 100;
              return (
                <div key={content.id} className="flex-1 flex flex-col items-center justify-end h-full group">
                  <p className="text-[10px] text-warroom-muted mb-1 opacity-0 group-hover:opacity-100 transition">
                    {formatNum(content.views || 0)} views
                  </p>
                  <div
                    className="w-full rounded-t-lg bg-warroom-accent hover:bg-warroom-accent/80 transition cursor-pointer relative"
                    style={{ height: `${Math.max(height, 5)}%` }}
                    title={content.title}
                  />
                  <p className="text-[9px] text-warroom-muted mt-2 text-center line-clamp-2 h-8">
                    {content.title.slice(0, 30)}...
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Metrics Summary */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "VIDEOS", value: posted.length || topPerforming.length, icon: Film, color: "text-blue-400" },
            { label: "TOTAL VIEWS", value: topPerforming.reduce((s, c) => s + (c.views || 0), 0), icon: Eye, color: "text-purple-400" },
            { label: "AVG VIEWS", value: Math.round(topPerforming.reduce((s, c) => s + (c.views || 0), 0) / (topPerforming.length || 1)), icon: TrendingUp, color: "text-green-400" },
            { label: "TOTAL LIKES", value: topPerforming.reduce((s, c) => s + (c.likes || 0), 0), icon: Heart, color: "text-red-400" },
          ].map((s, i) => (
            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
              <p className={`text-2xl font-bold ${s.color}`}>{formatNum(s.value)}</p>
              <p className="text-[10px] text-warroom-muted tracking-wider mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Published Videos List */}
        <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
          <h3 className="text-xs text-warroom-muted font-bold tracking-widest mb-4">
            PUBLISHED VIDEOS ({topPerforming.length})
          </h3>
          <div className="space-y-3">
            {topPerforming.map(content => (
              <div key={content.id}
                className="flex items-center gap-4 py-3 border-b border-warroom-border/50 last:border-0 hover:bg-warroom-bg/30 transition px-2 rounded-lg">
                {/* Thumbnail placeholder */}
                <div className="w-24 h-14 rounded-lg bg-warroom-bg border border-warroom-border flex items-center justify-center flex-shrink-0">
                  <Film size={16} className="text-warroom-muted/30" />
                </div>
                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{content.title}</p>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="flex items-center gap-1 text-[11px] text-warroom-muted">
                      <Eye size={11} /> {formatNum(content.views || 0)} views
                    </span>
                    <span className="flex items-center gap-1 text-[11px] text-warroom-muted">
                      <Heart size={11} /> {formatNum(content.likes || 0)} likes
                    </span>
                    <span className="flex items-center gap-1 text-[11px] text-warroom-muted">
                      <MessageSquare size={11} /> {content.comments || 0} comments
                    </span>
                    <span className="text-[11px] text-warroom-muted">
                      {content.engagement ? `${content.engagement.toFixed(1)}% engagement` : "0.0% engagement"}
                    </span>
                  </div>
                </div>
                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-warroom-accent/10 text-warroom-accent capitalize">
                    {content.platform}
                  </span>
                  {content.url && (
                    <a href={content.url} target="_blank" rel="noopener noreferrer"
                      className="text-warroom-accent text-xs flex items-center gap-1 hover:underline">
                      View <ExternalLink size={10} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
