"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Sparkles, Plus, Search, Filter, Instagram, Youtube,
  ChevronRight, Clock, Eye, Heart, MessageSquare, Share2,
} from "lucide-react";

interface ContentCard {
  id: string;
  title: string;
  description?: string;
  stage: string;
  platform: string;
  createdAt: string;
  hook?: string;
  views?: number;
  likes?: number;
  comments?: number;
}

const STAGES = [
  { key: "idea", label: "IDEA", color: "text-orange-400", bg: "bg-orange-400/10", border: "border-orange-400/30" },
  { key: "scripted", label: "SCRIPTED", color: "text-blue-400", bg: "bg-blue-400/10", border: "border-blue-400/30" },
  { key: "filming", label: "FILMING", color: "text-purple-400", bg: "bg-purple-400/10", border: "border-purple-400/30" },
  { key: "editing", label: "EDITING", color: "text-pink-400", bg: "bg-pink-400/10", border: "border-pink-400/30" },
  { key: "scheduled", label: "SCHEDULED", color: "text-yellow-400", bg: "bg-yellow-400/10", border: "border-yellow-400/30" },
  { key: "posted", label: "POSTED", color: "text-green-400", bg: "bg-green-400/10", border: "border-green-400/30" },
];

const PLATFORM_CONFIG: Record<string, { name: string; icon: any; color: string }> = {
  instagram: { name: "Instagram", icon: Instagram, color: "#E4405F" },
  youtube: { name: "YouTube", icon: Youtube, color: "#FF0000" },
};

interface PlatformContentProps {
  platform: "instagram" | "youtube";
}

export default function PlatformContent({ platform }: PlatformContentProps) {
  const [cards, setCards] = useState<ContentCard[]>([]);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  const config = PLATFORM_CONFIG[platform];
  const Icon = config.icon;

  const storageKey = `warroom_content_${platform}`;

  const loadCards = useCallback(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) setCards(JSON.parse(stored));
    } catch {}
  }, [storageKey]);

  useEffect(() => { loadCards(); }, [loadCards]);

  const saveCards = (updated: ContentCard[]) => {
    setCards(updated);
    localStorage.setItem(storageKey, JSON.stringify(updated));
  };

  const addCard = () => {
    if (!newTitle.trim()) return;
    const card: ContentCard = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
      title: newTitle.trim(),
      stage: "idea",
      platform,
      createdAt: new Date().toISOString(),
    };
    saveCards([card, ...cards]);
    setNewTitle("");
    setShowAdd(false);
  };

  const moveCard = (id: string, newStage: string) => {
    saveCards(cards.map(c => c.id === id ? { ...c, stage: newStage } : c));
  };

  const deleteCard = (id: string) => {
    saveCards(cards.filter(c => c.id !== id));
  };

  const filtered = cards.filter(c => {
    if (stageFilter !== "all" && c.stage !== stageFilter) return false;
    if (search && !c.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const stats = {
    total: cards.length,
    ideas: cards.filter(c => c.stage === "idea").length,
    inProduction: cards.filter(c => ["scripted", "filming", "editing"].includes(c.stage)).length,
    posted: cards.filter(c => c.stage === "posted").length,
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Icon size={20} style={{ color: config.color }} />
          <div>
            <h2 className="text-lg font-bold">{config.name}</h2>
            <p className="text-[11px] text-warroom-muted -mt-0.5">Content ideas, scripts, and publishing pipeline</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-surface border border-warroom-border text-xs hover:border-warroom-accent/30 transition">
            <Sparkles size={14} className="text-warroom-accent" /> Generate Ideas
          </button>
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-accent text-white text-xs font-medium hover:bg-warroom-accent/80 transition">
            <Plus size={14} /> Add Manual
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "TOTAL CONTENT", value: stats.total, color: "text-warroom-accent" },
            { label: "IDEAS", value: stats.ideas, color: "text-orange-400" },
            { label: "IN PRODUCTION", value: stats.inProduction, color: "text-purple-400" },
            { label: "POSTED", value: stats.posted, color: "text-green-400" },
          ].map((s, i) => (
            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-[10px] text-warroom-muted tracking-wider mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Search + Filter */}
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search content..."
              className="w-full bg-warroom-surface border border-warroom-border rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-warroom-accent/30" />
          </div>
          <select value={stageFilter} onChange={e => setStageFilter(e.target.value)}
            className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none">
            <option value="all">All Stages</option>
            {STAGES.map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>

        {/* Pipeline Columns */}
        <div>
          <h3 className="text-xs text-warroom-muted font-bold tracking-widest mb-3">PIPELINE</h3>
          <div className="grid grid-cols-6 gap-3">
            {STAGES.map(stage => {
              const stageCards = filtered.filter(c => c.stage === stage.key);
              return (
                <div key={stage.key} className="min-h-[200px]">
                  {/* Stage Header */}
                  <div className={`flex items-center justify-between px-3 py-2 rounded-t-lg border ${stage.border} ${stage.bg}`}>
                    <span className={`text-[10px] font-bold tracking-wider ${stage.color}`}>{stage.label}</span>
                    <span className={`text-[10px] font-bold ${stage.color}`}>{stageCards.length}</span>
                  </div>
                  {/* Cards */}
                  <div className="space-y-2 mt-2">
                    {stageCards.map(card => (
                      <div key={card.id}
                        className="bg-warroom-surface border border-warroom-border rounded-lg p-3 hover:border-warroom-accent/20 transition group">
                        <p className="text-xs font-medium leading-snug line-clamp-3 mb-2">{card.title}</p>
                        {card.description && (
                          <p className="text-[10px] text-warroom-muted line-clamp-2 mb-2">{card.description}</p>
                        )}
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] text-warroom-muted">
                            {new Date(card.createdAt).toLocaleDateString()}
                          </span>
                          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                            {/* Move to next stage */}
                            {stage.key !== "posted" && (
                              <button
                                onClick={() => {
                                  const idx = STAGES.findIndex(s => s.key === stage.key);
                                  if (idx < STAGES.length - 1) moveCard(card.id, STAGES[idx + 1].key);
                                }}
                                className="text-[9px] px-1.5 py-0.5 rounded bg-warroom-accent/20 text-warroom-accent hover:bg-warroom-accent/30"
                                title="Move to next stage">
                                <ChevronRight size={10} />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                    {stageCards.length === 0 && (
                      <p className="text-[10px] text-warroom-muted/40 text-center py-6">No items</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Add Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center" onClick={() => setShowAdd(false)}>
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-[480px]" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-bold mb-4">Add Content Idea — {config.name}</h3>
            <input value={newTitle} onChange={e => setNewTitle(e.target.value)}
              onKeyDown={e => e.key === "Enter" && addCard()}
              placeholder="Hook or title..."
              autoFocus
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:border-warroom-accent" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowAdd(false)}
                className="px-3 py-1.5 text-xs rounded-lg text-warroom-muted hover:text-warroom-text transition">Cancel</button>
              <button onClick={addCard} disabled={!newTitle.trim()}
                className="px-4 py-1.5 text-xs rounded-lg bg-warroom-accent text-white font-medium disabled:opacity-30 hover:bg-warroom-accent/80 transition">Add Idea</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
