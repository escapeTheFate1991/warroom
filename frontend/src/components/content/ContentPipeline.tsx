"use client";

import { useState, useEffect } from "react";
import { Plus, X, GripVertical, Instagram, Youtube, Clock, User, Lightbulb, PenTool, Film, Scissors, Calendar, CheckCircle2, MoreVertical, Trash2, Edit2 } from "lucide-react";

interface ContentCard {
  id: string;
  title: string;
  platforms: string[];
  notes: string;
  assignedAgent?: string;
  dueDate?: string;
  stage: Stage;
  createdAt: string;
}

type Stage = "idea" | "script" | "filming" | "editing" | "scheduled" | "posted";

const STAGES: { id: Stage; label: string; icon: typeof Lightbulb; color: string }[] = [
  { id: "idea", label: "Idea", icon: Lightbulb, color: "text-yellow-400" },
  { id: "script", label: "Script", icon: PenTool, color: "text-blue-400" },
  { id: "filming", label: "Filming", icon: Film, color: "text-purple-400" },
  { id: "editing", label: "Editing", icon: Scissors, color: "text-pink-400" },
  { id: "scheduled", label: "Scheduled", icon: Calendar, color: "text-orange-400" },
  { id: "posted", label: "Posted", icon: CheckCircle2, color: "text-green-400" },
];

const PLATFORM_OPTIONS = [
  { id: "instagram", label: "Instagram", color: "bg-pink-500/20 text-pink-400" },
  { id: "tiktok", label: "TikTok", color: "bg-cyan-500/20 text-cyan-400" },
  { id: "youtube", label: "YouTube", color: "bg-red-500/20 text-red-400" },
  { id: "facebook", label: "Facebook", color: "bg-blue-500/20 text-blue-400" },
  { id: "threads", label: "Threads", color: "bg-gray-500/20 text-gray-400" },
  { id: "x", label: "X", color: "bg-gray-600/20 text-gray-300" },
];

const LS_KEY = "warroom_content_pipeline";

function loadCards(): ContentCard[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch { return []; }
}

function saveCards(cards: ContentCard[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(cards));
}

function genId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }

export default function ContentPipeline() {
  const [cards, setCards] = useState<ContentCard[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editCard, setEditCard] = useState<ContentCard | null>(null);
  const [newCard, setNewCard] = useState({ title: "", platforms: [] as string[], notes: "", dueDate: "" });
  const [dragCard, setDragCard] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<Stage | null>(null);

  useEffect(() => { setCards(loadCards()); }, []);
  useEffect(() => { if (cards.length > 0 || localStorage.getItem(LS_KEY)) saveCards(cards); }, [cards]);

  const addCard = () => {
    if (!newCard.title.trim()) return;
    const card: ContentCard = {
      id: genId(),
      title: newCard.title.trim(),
      platforms: newCard.platforms,
      notes: newCard.notes,
      dueDate: newCard.dueDate || undefined,
      stage: "idea",
      createdAt: new Date().toISOString(),
    };
    setCards(prev => [...prev, card]);
    setNewCard({ title: "", platforms: [], notes: "", dueDate: "" });
    setShowAddForm(false);
  };

  const moveCard = (cardId: string, newStage: Stage) => {
    setCards(prev => prev.map(c => c.id === cardId ? { ...c, stage: newStage } : c));
  };

  const deleteCard = (cardId: string) => {
    setCards(prev => prev.filter(c => c.id !== cardId));
  };

  const togglePlatform = (pid: string) => {
    setNewCard(prev => ({
      ...prev,
      platforms: prev.platforms.includes(pid) ? prev.platforms.filter(p => p !== pid) : [...prev.platforms, pid],
    }));
  };

  const handleDragStart = (cardId: string) => setDragCard(cardId);
  const handleDragOver = (e: React.DragEvent, stage: Stage) => { e.preventDefault(); setDragOverStage(stage); };
  const handleDragLeave = () => setDragOverStage(null);
  const handleDrop = (stage: Stage) => {
    if (dragCard) { moveCard(dragCard, stage); setDragCard(null); setDragOverStage(null); }
  };

  const getStageCards = (stage: Stage) => cards.filter(c => c.stage === stage);
  const totalCards = cards.length;
  const ideasCount = getStageCards("idea").length;
  const inProduction = cards.filter(c => ["script", "filming", "editing"].includes(c.stage)).length;
  const postedCount = getStageCards("posted").length;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Film size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Content Pipeline</h2>
        <div className="ml-auto flex items-center gap-4 text-xs text-warroom-muted">
          <span>{totalCards} total</span>
          <span className="text-yellow-400">{ideasCount} ideas</span>
          <span className="text-purple-400">{inProduction} in production</span>
          <span className="text-green-400">{postedCount} posted</span>
          <button onClick={() => setShowAddForm(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs text-white font-medium transition">
            <Plus size={14} /> New Idea
          </button>
        </div>
      </div>

      {/* Pipeline Columns */}
      <div className="flex-1 overflow-x-auto">
        <div className="flex h-full min-w-max p-4 gap-3">
          {STAGES.map(stage => {
            const stageCards = getStageCards(stage.id);
            const Icon = stage.icon;
            const isDragOver = dragOverStage === stage.id;

            return (
              <div key={stage.id}
                className={`w-72 flex-shrink-0 flex flex-col rounded-2xl border transition-all ${
                  isDragOver ? "border-warroom-accent bg-warroom-accent/5" : "border-warroom-border bg-warroom-surface/50"
                }`}
                onDragOver={e => handleDragOver(e, stage.id)}
                onDragLeave={handleDragLeave}
                onDrop={() => handleDrop(stage.id)}>
                {/* Column header */}
                <div className="flex items-center gap-2 px-4 py-3 border-b border-warroom-border/50">
                  <Icon size={16} className={stage.color} />
                  <span className="text-sm font-medium">{stage.label}</span>
                  <span className="ml-auto text-xs text-warroom-muted bg-warroom-bg px-2 py-0.5 rounded-full">{stageCards.length}</span>
                </div>

                {/* Cards */}
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                  {stageCards.map(card => (
                    <div key={card.id} draggable
                      onDragStart={() => handleDragStart(card.id)}
                      className="bg-warroom-bg border border-warroom-border rounded-xl p-3 cursor-grab active:cursor-grabbing hover:border-warroom-accent/30 transition group">
                      {/* Card content */}
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-1.5 opacity-30 group-hover:opacity-60 transition">
                          <GripVertical size={14} />
                        </div>
                        <div className="flex items-center gap-1">
                          {/* Move to next stage */}
                          {stage.id !== "posted" && (
                            <button onClick={() => {
                              const idx = STAGES.findIndex(s => s.id === stage.id);
                              if (idx < STAGES.length - 1) moveCard(card.id, STAGES[idx + 1].id);
                            }} className="opacity-0 group-hover:opacity-100 text-warroom-muted hover:text-warroom-accent transition p-0.5" title="Move to next stage">
                              <CheckCircle2 size={14} />
                            </button>
                          )}
                          <button onClick={() => deleteCard(card.id)}
                            className="opacity-0 group-hover:opacity-100 text-warroom-muted hover:text-red-400 transition p-0.5" title="Delete">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>

                      <h4 className="text-sm font-medium mb-2 leading-snug">{card.title}</h4>

                      {/* Platform tags */}
                      {card.platforms.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {card.platforms.map(pid => {
                            const po = PLATFORM_OPTIONS.find(p => p.id === pid);
                            return po ? (
                              <span key={pid} className={`text-[10px] px-1.5 py-0.5 rounded-md ${po.color}`}>{po.label}</span>
                            ) : null;
                          })}
                        </div>
                      )}

                      {/* Notes preview */}
                      {card.notes && (
                        <p className="text-xs text-warroom-muted line-clamp-2 mb-2">{card.notes}</p>
                      )}

                      {/* Footer */}
                      <div className="flex items-center gap-2 text-[10px] text-warroom-muted">
                        {card.dueDate && (
                          <span className="flex items-center gap-1"><Clock size={10} /> {new Date(card.dueDate).toLocaleDateString()}</span>
                        )}
                        {card.assignedAgent && (
                          <span className="flex items-center gap-1"><User size={10} /> {card.assignedAgent}</span>
                        )}
                      </div>
                    </div>
                  ))}

                  {stageCards.length === 0 && (
                    <div className="text-center py-8 text-warroom-muted/40">
                      <Icon size={24} className="mx-auto mb-2 opacity-30" />
                      <p className="text-xs">No content here</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Add Idea Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Lightbulb size={20} className="text-yellow-400" /> New Content Idea
              </h3>
              <button onClick={() => setShowAddForm(false)} className="text-warroom-muted hover:text-warroom-text"><X size={20} /></button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Title / Hook</label>
                <input type="text" value={newCard.title} onChange={e => setNewCard({ ...newCard, title: e.target.value })}
                  onKeyDown={e => e.key === "Enter" && addCard()}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                  placeholder="e.g., 'I gave AI access to my business. Here's what happened.'" autoFocus />
              </div>

              <div>
                <label className="text-xs text-warroom-muted block mb-2">Platforms</label>
                <div className="flex flex-wrap gap-2">
                  {PLATFORM_OPTIONS.map(po => (
                    <button key={po.id} onClick={() => togglePlatform(po.id)}
                      className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                        newCard.platforms.includes(po.id)
                          ? `${po.color} border-current`
                          : "text-warroom-muted border-warroom-border hover:border-warroom-muted"
                      }`}>
                      {po.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-warroom-muted block mb-1">Notes</label>
                <textarea value={newCard.notes} onChange={e => setNewCard({ ...newCard, notes: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent h-20 resize-none"
                  placeholder="Angle, talking points, reference content..." />
              </div>

              <div>
                <label className="text-xs text-warroom-muted block mb-1">Due Date (optional)</label>
                <input type="date" value={newCard.dueDate} onChange={e => setNewCard({ ...newCard, dueDate: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" />
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowAddForm(false)} className="flex-1 px-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm hover:bg-warroom-surface transition">Cancel</button>
              <button onClick={addCard} disabled={!newCard.title.trim()}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition">Add to Pipeline</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
