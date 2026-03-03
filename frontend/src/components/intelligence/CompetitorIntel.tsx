"use client";

import { useState, useEffect } from "react";
import { Search, Plus, X, Flame, Copy, Check, User, TrendingUp, Eye, Target, Zap, BookOpen, ExternalLink, Trash2 } from "lucide-react";

interface Competitor {
  id: string;
  handle: string;
  platform: string;
  followers: number;
  postingFrequency: string;
  topAngles: string[];
  signatureFormula: string;
  notes: string;
}

interface HookFormula {
  id: number;
  name: string;
  template: string;
  example: string;
  category: string;
}

interface TrendingTopic {
  id: number;
  title: string;
  heat: number; // 1-5
  source: string;
}

const LS_KEY_COMPETITORS = "warroom_competitors";
const LS_KEY_TOPICS = "warroom_trending_topics";

const DEFAULT_TOPICS: TrendingTopic[] = [
  { id: 1, title: "Claude Code builds entire app in 8 minutes", heat: 5, source: "TikTok" },
  { id: 2, title: "Why agency owners will replace 80% of staff with AI", heat: 4, source: "YouTube" },
  { id: 3, title: "I gave AI access to my business. Here's what happened.", heat: 5, source: "Instagram" },
  { id: 4, title: "Stop trading time for money — use AI agents instead", heat: 3, source: "TikTok" },
  { id: 5, title: "$0 to $10K creator playbook with AI tools", heat: 4, source: "YouTube" },
  { id: 6, title: "The AI tool stack that replaced my entire team", heat: 4, source: "Instagram" },
  { id: 7, title: "Why your marketing agency will be obsolete by 2027", heat: 3, source: "TikTok" },
  { id: 8, title: "I automated my entire content pipeline with AI", heat: 5, source: "YouTube" },
];

const HOOK_FORMULAS: HookFormula[] = [
  { id: 1, name: "The Comparison", template: "My [person] did [X] in [time]. AI did it in [Y].", example: "My designer took 3 days on the landing page. Claude did it in 8 minutes.", category: "shock" },
  { id: 2, name: "The Bold Claim", template: "[Category] is dead. Here's what replaced it.", example: "Freelancing is dead. Here's what replaced it.", category: "controversy" },
  { id: 3, name: "The Identity Challenge", template: "If you're still doing [task] manually, you're losing.", example: "If you're still writing emails manually, you're losing.", category: "urgency" },
  { id: 4, name: "The Confession", template: "I was wrong about [thing]. Here's what actually works.", example: "I was wrong about social media scheduling. Here's what actually works.", category: "authenticity" },
  { id: 5, name: "The Results", template: "I tried [thing] for [time]. Here are the real numbers.", example: "I tried AI content creation for 30 days. Here are the real numbers.", category: "proof" },
  { id: 6, name: "The Prediction", template: "In 12 months, [prediction]. Here's why.", example: "In 12 months, 90% of marketing will be AI-generated. Here's why.", category: "authority" },
];

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "bg-pink-500/20 text-pink-400",
  tiktok: "bg-cyan-500/20 text-cyan-400",
  youtube: "bg-red-500/20 text-red-400",
  x: "bg-gray-600/20 text-gray-300",
  facebook: "bg-blue-500/20 text-blue-400",
  threads: "bg-gray-500/20 text-gray-400",
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function genId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }

export default function CompetitorIntel() {
  const [activeTab, setActiveTab] = useState<"competitors" | "trending" | "hooks">("competitors");
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [topics, setTopics] = useState<TrendingTopic[]>(DEFAULT_TOPICS);
  const [showAddCompetitor, setShowAddCompetitor] = useState(false);
  const [copiedHook, setCopiedHook] = useState<number | null>(null);
  const [newComp, setNewComp] = useState({ handle: "", platform: "instagram", followers: 0, postingFrequency: "", topAngles: "", signatureFormula: "", notes: "" });

  useEffect(() => {
    try {
      const saved = localStorage.getItem(LS_KEY_COMPETITORS);
      if (saved) setCompetitors(JSON.parse(saved));
    } catch {}
  }, []);

  useEffect(() => {
    if (competitors.length > 0 || localStorage.getItem(LS_KEY_COMPETITORS)) {
      localStorage.setItem(LS_KEY_COMPETITORS, JSON.stringify(competitors));
    }
  }, [competitors]);

  const addCompetitor = () => {
    if (!newComp.handle.trim()) return;
    const comp: Competitor = {
      id: genId(),
      handle: newComp.handle.trim(),
      platform: newComp.platform,
      followers: newComp.followers,
      postingFrequency: newComp.postingFrequency,
      topAngles: newComp.topAngles.split("\n").filter(Boolean),
      signatureFormula: newComp.signatureFormula,
      notes: newComp.notes,
    };
    setCompetitors(prev => [...prev, comp]);
    setNewComp({ handle: "", platform: "instagram", followers: 0, postingFrequency: "", topAngles: "", signatureFormula: "", notes: "" });
    setShowAddCompetitor(false);
  };

  const deleteCompetitor = (id: string) => setCompetitors(prev => prev.filter(c => c.id !== id));

  const copyHook = (formula: HookFormula) => {
    navigator.clipboard.writeText(formula.template);
    setCopiedHook(formula.id);
    setTimeout(() => setCopiedHook(null), 2000);
  };

  const TABS = [
    { id: "competitors" as const, label: "Competitor Pulse", icon: Target, count: competitors.length },
    { id: "trending" as const, label: "Trending Topics", icon: TrendingUp, count: topics.length },
    { id: "hooks" as const, label: "Hook Formulas", icon: Zap, count: HOOK_FORMULAS.length },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Eye size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Intelligence</h2>
      </div>

      {/* Sub-tabs */}
      <div className="border-b border-warroom-border bg-warroom-surface flex-shrink-0">
        <div className="flex">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab.id
                  ? "text-warroom-accent border-warroom-accent bg-warroom-accent/5"
                  : "text-warroom-muted border-transparent hover:text-warroom-text"
              }`}>
              <tab.icon size={16} />
              {tab.label}
              <span className="text-xs bg-warroom-bg px-1.5 py-0.5 rounded-full">{tab.count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">

          {/* COMPETITORS TAB */}
          {activeTab === "competitors" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-warroom-muted">Track competitors to learn their winning angles and posting strategies.</p>
                <button onClick={() => setShowAddCompetitor(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition">
                  <Plus size={14} /> Add Competitor
                </button>
              </div>

              {competitors.length === 0 ? (
                <div className="text-center py-16 text-warroom-muted">
                  <Target size={48} className="mx-auto mb-4 opacity-20" />
                  <p className="text-sm">No competitors tracked yet</p>
                  <p className="text-xs mt-1">Add your first competitor to start gathering intelligence</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {competitors.map(comp => (
                    <div key={comp.id} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/30 transition group">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-warroom-accent/10 flex items-center justify-center">
                            <User size={20} className="text-warroom-accent" />
                          </div>
                          <div>
                            <h4 className="font-semibold text-sm">@{comp.handle}</h4>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${PLATFORM_COLORS[comp.platform] || "bg-gray-500/20 text-gray-400"}`}>{comp.platform}</span>
                              <span className="text-xs text-warroom-muted">{formatNum(comp.followers)} followers</span>
                            </div>
                          </div>
                        </div>
                        <button onClick={() => deleteCompetitor(comp.id)}
                          className="opacity-0 group-hover:opacity-100 text-warroom-muted hover:text-red-400 transition">
                          <Trash2 size={14} />
                        </button>
                      </div>

                      {comp.postingFrequency && (
                        <p className="text-xs text-warroom-muted mb-2">📅 {comp.postingFrequency}</p>
                      )}

                      {comp.topAngles.length > 0 && (
                        <div className="mb-2">
                          <p className="text-[10px] text-warroom-muted font-medium mb-1">Top Angles</p>
                          <div className="space-y-1">
                            {comp.topAngles.map((angle, i) => (
                              <p key={i} className="text-xs text-warroom-text">• {angle}</p>
                            ))}
                          </div>
                        </div>
                      )}

                      {comp.signatureFormula && (
                        <div className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 mt-2">
                          <p className="text-[10px] text-warroom-muted font-medium mb-0.5">Signature Formula</p>
                          <p className="text-xs italic">{comp.signatureFormula}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TRENDING TAB */}
          {activeTab === "trending" && (
            <div className="space-y-3">
              <p className="text-sm text-warroom-muted mb-4">Hot topics in your niche based on engagement signals.</p>
              {topics.sort((a, b) => b.heat - a.heat).map(topic => (
                <div key={topic.id} className="bg-warroom-surface border border-warroom-border rounded-xl px-5 py-4 flex items-center gap-4 hover:border-warroom-accent/30 transition group">
                  <div className="flex items-center gap-1 w-16 flex-shrink-0">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Flame key={i} size={14} className={i < topic.heat ? "text-orange-400" : "text-warroom-border"} />
                    ))}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{topic.title}</p>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 ${
                    PLATFORM_COLORS[topic.source.toLowerCase()] || "bg-gray-500/20 text-gray-400"
                  }`}>{topic.source}</span>
                  <button className="opacity-0 group-hover:opacity-100 text-xs text-warroom-accent hover:underline flex-shrink-0 transition">
                    Use as Hook →
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* HOOKS TAB */}
          {activeTab === "hooks" && (
            <div className="space-y-4">
              <p className="text-sm text-warroom-muted mb-4">Proven hook formulas with fill-in-the-blank templates.</p>
              <div className="grid grid-cols-1 gap-4">
                {HOOK_FORMULAS.map((formula, i) => (
                  <div key={formula.id} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/30 transition">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-warroom-accent/30">{String(i + 1).padStart(2, "0")}</span>
                        <div>
                          <h4 className="font-semibold text-sm">{formula.name}</h4>
                          <span className="text-[10px] text-warroom-muted px-2 py-0.5 bg-warroom-bg rounded-full">{formula.category}</span>
                        </div>
                      </div>
                      <button onClick={() => copyHook(formula)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent/10 hover:bg-warroom-accent/20 text-warroom-accent rounded-lg text-xs font-medium transition">
                        {copiedHook === formula.id ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Use This</>}
                      </button>
                    </div>

                    <div className="bg-warroom-bg border border-warroom-border rounded-xl px-4 py-3 mb-2">
                      <p className="text-sm font-mono">{formula.template}</p>
                    </div>

                    <p className="text-xs text-warroom-muted italic">
                      💡 Example: "{formula.example}"
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Competitor Modal */}
      {showAddCompetitor && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Add Competitor</h3>
              <button onClick={() => setShowAddCompetitor(false)} className="text-warroom-muted hover:text-warroom-text"><X size={20} /></button>
            </div>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">Handle</label>
                  <input type="text" value={newComp.handle} onChange={e => setNewComp({ ...newComp, handle: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" placeholder="@handle" autoFocus />
                </div>
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">Platform</label>
                  <select value={newComp.platform} onChange={e => setNewComp({ ...newComp, platform: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent">
                    {Object.keys(PLATFORM_COLORS).map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">Followers</label>
                  <input type="number" value={newComp.followers} onChange={e => setNewComp({ ...newComp, followers: parseInt(e.target.value) || 0 })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" />
                </div>
                <div>
                  <label className="text-xs text-warroom-muted block mb-1">Posting Frequency</label>
                  <input type="text" value={newComp.postingFrequency} onChange={e => setNewComp({ ...newComp, postingFrequency: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" placeholder="e.g., 5-6x/week" />
                </div>
              </div>
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Top Angles (one per line)</label>
                <textarea value={newComp.topAngles} onChange={e => setNewComp({ ...newComp, topAngles: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent h-20 resize-none"
                  placeholder="AI replaces entire teams&#10;Behind the scenes content&#10;Income reveals" />
              </div>
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Signature Formula</label>
                <input type="text" value={newComp.signatureFormula} onChange={e => setNewComp({ ...newComp, signatureFormula: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent"
                  placeholder="e.g., Hook + AI demo + results + CTA" />
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowAddCompetitor(false)} className="flex-1 px-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm hover:bg-warroom-surface transition">Cancel</button>
              <button onClick={addCompetitor} disabled={!newComp.handle.trim()}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition">Add Competitor</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
