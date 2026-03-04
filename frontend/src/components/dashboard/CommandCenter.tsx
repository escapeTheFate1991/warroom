"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Zap, Users, Eye, BarChart3, TrendingUp, Activity, Share2, Film,
  Target, Clock, CheckCircle2, Loader2, AlertCircle, ArrowRight, ArrowUpRight,
  Flame, Calendar, MessageSquare,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";
const TEAM_API = "http://10.0.0.11:18795";

interface SocialAccount {
  id: number; platform: string; username: string | null;
  follower_count: number; post_count: number; status: string;
}
interface SocialSummary {
  total_followers: number; total_engagement: number; total_impressions: number;
  total_reach: number; engagement_rate: number; accounts_connected: number;
}
interface AgentEvent {
  event_type: string; from_agent: string; to_agent: string;
  summary: string; timestamp: string;
}

const AGENTS = [
  { id: "friday", emoji: "🖤", name: "Friday", role: "Orchestrator", model: "Opus" },
  { id: "copy", emoji: "📝", name: "Copy", role: "Copywriter", model: "Sonnet" },
  { id: "design", emoji: "🎨", name: "Design", role: "UI/UX", model: "Sonnet" },
  { id: "dev", emoji: "💻", name: "Dev", role: "Developer", model: "Sonnet" },
  { id: "docs", emoji: "📚", name: "Docs", role: "Documentation", model: "Haiku" },
  { id: "support", emoji: "📞", name: "Support", role: "Call Center", model: "Haiku" },
  { id: "inbox", emoji: "📧", name: "Inbox", role: "Email", model: "Haiku" },
];

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "#E4405F", facebook: "#1877F2", youtube: "#FF0000",
  tiktok: "#00F2EA", x: "#000", threads: "#888",
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function MiniSparkline({ color }: { color: string }) {
  const data = Array.from({ length: 12 }, () => Math.random() * 80 + 20);
  const max = Math.max(...data);
  const w = 100, h = 30;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / max) * h}`).join(" ");
  return (
    <svg width={w} height={h} className="opacity-40">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Content pipeline data from localStorage
function getPipelineStats() {
  if (typeof window === "undefined") return { total: 0, ideas: 0, inProduction: 0, posted: 0 };
  try {
    const cards = JSON.parse(localStorage.getItem("warroom_content_pipeline") || "[]");
    return {
      total: cards.length,
      ideas: cards.filter((c: any) => c.stage === "idea").length,
      inProduction: cards.filter((c: any) => ["script", "filming", "editing"].includes(c.stage)).length,
      posted: cards.filter((c: any) => c.stage === "posted").length,
      scheduled: cards.filter((c: any) => c.stage === "scheduled").length,
    };
  } catch { return { total: 0, ideas: 0, inProduction: 0, posted: 0, scheduled: 0 }; }
}

export default function CommandCenter() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [summary, setSummary] = useState<SocialSummary | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [pipelineStats, setPipelineStats] = useState(getPipelineStats());
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());

  const fetchData = useCallback(async () => {
    try {
      const [accResp, sumResp] = await Promise.all([
        fetch(`${API}/api/social/accounts`).catch(() => null),
        fetch(`${API}/api/social/analytics`).catch(() => null),
      ]);
      if (accResp?.ok) setAccounts(await accResp.json());
      if (sumResp?.ok) setSummary(await sumResp.json());

      // Team events
      try {
        const evResp = await fetch(`${TEAM_API}/events?limit=8`);
        if (evResp.ok) {
          const data = await evResp.json();
          if (Array.isArray(data)) setEvents(data);
        }
      } catch {}
    } catch {} finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { setPipelineStats(getPipelineStats()); }, []);
  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  // Demo events if none from API
  const displayEvents = events.length > 0 ? events : [
    { event_type: "complete", from_agent: "dev", to_agent: "friday", summary: "War Room UI rebuild deployed — 5 new components", timestamp: new Date(Date.now() - 300000).toISOString() },
    { event_type: "spawn", from_agent: "friday", to_agent: "dev", summary: "Building Command Center dashboard", timestamp: new Date(Date.now() - 120000).toISOString() },
    { event_type: "complete", from_agent: "copy", to_agent: "friday", summary: "6 hook formula templates created", timestamp: new Date(Date.now() - 60000).toISOString() },
  ];

  const greeting = currentTime.getHours() < 12 ? "Good morning" : currentTime.getHours() < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-16 border-b border-warroom-border flex items-center px-8 gap-3 flex-shrink-0">
        <Zap size={22} className="text-warroom-accent" />
        <h2 className="text-lg font-bold">Command Center</h2>
        <span className="ml-auto text-sm text-warroom-muted">
          {currentTime.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })} · {currentTime.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-8 space-y-8">

          {/* Welcome + Quick Stats */}
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-3xl font-bold">{greeting}, Eddy</h1>
              <p className="text-base text-warroom-muted mt-1">Here's your operations overview</p>
            </div>
          </div>

          {/* Top Metrics Row */}
          <div className="grid grid-cols-5 gap-5">
            {[
              { label: "Total Reach", value: summary?.total_reach || 0, icon: Eye, color: "text-purple-400", bgColor: "bg-purple-400/10", trend: "+22%", sparkColor: "#a78bfa" },
              { label: "Followers", value: summary?.total_followers || accounts.reduce((s, a) => s + a.follower_count, 0), icon: Users, color: "text-blue-400", bgColor: "bg-blue-400/10", trend: "+12%", sparkColor: "#60a5fa" },
              { label: "Engagement", value: summary?.engagement_rate || 0, icon: TrendingUp, color: "text-green-400", bgColor: "bg-green-400/10", trend: "+3.2%", sparkColor: "#4ade80", isRate: true },
              { label: "Content Pipeline", value: pipelineStats.total, icon: Film, color: "text-orange-400", bgColor: "bg-orange-400/10", trend: null, sparkColor: "#fb923c" },
              { label: "Agents Active", value: AGENTS.length, icon: Activity, color: "text-warroom-accent", bgColor: "bg-warroom-accent/10", trend: null, sparkColor: "#6366f1" },
            ].map((stat, i) => (
              <div key={i} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/20 transition group relative overflow-hidden">
                <div className="absolute bottom-0 right-0 opacity-30">
                  <MiniSparkline color={stat.sparkColor} />
                </div>
                <div className="flex items-center justify-between mb-3 relative z-10">
                  <div className={`w-10 h-10 rounded-xl ${stat.bgColor} flex items-center justify-center`}>
                    <stat.icon size={20} className={stat.color} />
                  </div>
                  {stat.trend && (
                    <span className="flex items-center gap-0.5 text-xs text-green-400 font-medium">
                      <ArrowUpRight size={12} /> {stat.trend}
                    </span>
                  )}
                </div>
                <p className={`text-2xl font-bold ${stat.color} relative z-10`}>
                  {stat.isRate ? `${(typeof stat.value === "number" ? stat.value : 0).toFixed(1)}%` : formatNum(typeof stat.value === "number" ? stat.value : 0)}
                </p>
                <p className="text-xs text-warroom-muted mt-1 relative z-10">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-3 gap-6">

            {/* Left Column (2/3) */}
            <div className="col-span-2 space-y-6">

              {/* AI Team Status */}
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-base font-bold flex items-center gap-2.5">
                    <Activity size={18} className="text-warroom-accent" /> AI Team
                  </h3>
                  <span className="text-sm text-warroom-muted">{AGENTS.length} agents</span>
                </div>
                <div className="grid grid-cols-4 gap-4">
                  {AGENTS.slice(0, 4).map(agent => {
                    const isRunning = agent.id === "friday";
                    return (
                      <div key={agent.id} className="bg-warroom-bg border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition">
                        <div className="flex items-center gap-2.5 mb-3">
                          <span className="text-2xl">{agent.emoji}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold truncate">{agent.name}</p>
                            <p className="text-xs text-warroom-muted">{agent.role}</p>
                          </div>
                          <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${isRunning ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] px-2 py-0.5 rounded bg-warroom-accent/10 text-warroom-accent font-medium">{agent.model}</span>
                          <span className={`text-[11px] ${isRunning ? "text-green-400" : "text-warroom-muted"}`}>
                            {isRunning ? "Running" : "Idle"}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="grid grid-cols-3 gap-4 mt-4">
                  {AGENTS.slice(4).map(agent => (
                    <div key={agent.id} className="flex items-center gap-2.5 bg-warroom-bg border border-warroom-border rounded-xl px-4 py-3">
                      <span className="text-xl">{agent.emoji}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{agent.name}</p>
                        <p className="text-xs text-warroom-muted">{agent.role}</p>
                      </div>
                      <div className="w-2 h-2 rounded-full bg-gray-500" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Social Performance Cards */}
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-base font-bold flex items-center gap-2.5">
                    <Share2 size={18} className="text-warroom-accent" /> Social Performance
                  </h3>
                  <span className="text-sm text-warroom-muted">{accounts.length} platforms</span>
                </div>
                {accounts.length > 0 ? (
                  <div className="grid grid-cols-3 gap-4">
                    {accounts.map(acc => (
                      <div key={acc.id} className="bg-warroom-bg border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: PLATFORM_COLORS[acc.platform] || "#666" }} />
                            <span className="text-sm font-semibold capitalize">{acc.platform}</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                            <span className="text-[11px] text-green-400 font-medium">LIVE</span>
                          </div>
                        </div>
                        {acc.username && <p className="text-xs text-warroom-muted mb-2">@{acc.username}</p>}
                        <div className="flex items-end justify-between">
                          <div>
                            <p className="text-2xl font-bold">{formatNum(acc.follower_count)}</p>
                            <p className="text-xs text-warroom-muted">followers</p>
                          </div>
                          <MiniSparkline color={PLATFORM_COLORS[acc.platform] || "#6366f1"} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-warroom-muted">
                    <Share2 size={24} className="mx-auto mb-2 opacity-20" />
                    <p className="text-xs">No social accounts connected</p>
                    <p className="text-[10px] mt-1">Go to Social → Connect your platforms</p>
                  </div>
                )}
              </div>

              {/* Content Pipeline Summary */}
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Film size={16} className="text-warroom-accent" /> Content Pipeline
                  </h3>
                </div>
                <div className="grid grid-cols-6 gap-2">
                  {[
                    { label: "Ideas", count: pipelineStats.ideas || 0, color: "text-yellow-400", bg: "bg-yellow-400/10" },
                    { label: "Script", count: 0, color: "text-blue-400", bg: "bg-blue-400/10" },
                    { label: "Filming", count: 0, color: "text-purple-400", bg: "bg-purple-400/10" },
                    { label: "Editing", count: pipelineStats.inProduction || 0, color: "text-pink-400", bg: "bg-pink-400/10" },
                    { label: "Scheduled", count: pipelineStats.scheduled || 0, color: "text-orange-400", bg: "bg-orange-400/10" },
                    { label: "Posted", count: pipelineStats.posted || 0, color: "text-green-400", bg: "bg-green-400/10" },
                  ].map((stage, i) => (
                    <div key={i} className="text-center">
                      <div className={`${stage.bg} rounded-xl py-3 mb-1`}>
                        <p className={`text-xl font-bold ${stage.color}`}>{stage.count}</p>
                      </div>
                      <p className="text-[10px] text-warroom-muted">{stage.label}</p>
                    </div>
                  ))}
                </div>
                {pipelineStats.total === 0 && (
                  <p className="text-xs text-warroom-muted text-center mt-3">No content in pipeline yet. Go to Pipeline → New Idea</p>
                )}
              </div>
            </div>

            {/* Right Column (1/3) — Activity Feed */}
            <div className="space-y-6">

              {/* Scheduled Today */}
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                  <Calendar size={16} className="text-warroom-accent" /> Scheduled Today
                </h3>
                <div className="space-y-2">
                  {pipelineStats.scheduled ? (
                    <div className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2">
                      <p className="text-xs font-medium">{pipelineStats.scheduled} posts queued</p>
                      <p className="text-[10px] text-warroom-muted">Check Pipeline for details</p>
                    </div>
                  ) : (
                    <div className="text-center py-4 text-warroom-muted">
                      <Calendar size={20} className="mx-auto mb-1 opacity-20" />
                      <p className="text-xs">Nothing scheduled</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Quick Capture */}
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                  <MessageSquare size={16} className="text-warroom-accent" /> Quick Capture
                </h3>
                <QuickCapture />
              </div>

              {/* Activity Feed */}
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                  <Activity size={16} className="text-warroom-accent" /> Recent Activity
                </h3>
                <div className="space-y-2">
                  {displayEvents.slice(0, 6).map((ev, i) => {
                    const isSpawn = ev.event_type === "spawn";
                    return (
                      <div key={i} className="flex items-start gap-2 py-1.5">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                          isSpawn ? "bg-warroom-accent/20" : "bg-green-500/20"
                        }`}>
                          {isSpawn ? <Zap size={10} className="text-warroom-accent" /> : <CheckCircle2 size={10} className="text-green-400" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs leading-snug line-clamp-2">{ev.summary}</p>
                          <p className="text-[10px] text-warroom-muted mt-0.5 flex items-center gap-1">
                            <Clock size={9} /> {timeAgo(ev.timestamp)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Trending */}
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                  <Flame size={16} className="text-orange-400" /> Trending Now
                </h3>
                <div className="space-y-2">
                  {[
                    "Claude Code builds entire app in 8 min",
                    "AI replaced 80% of my team",
                    "$0 to $10K creator playbook",
                  ].map((topic, i) => (
                    <div key={i} className="flex items-center gap-2 py-1">
                      <div className="flex gap-0.5">
                        {Array.from({ length: 5 - i }).map((_, j) => (
                          <Flame key={j} size={10} className="text-orange-400" />
                        ))}
                      </div>
                      <p className="text-xs text-warroom-text truncate flex-1">{topic}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Quick Capture sub-component
function QuickCapture() {
  const [text, setText] = useState("");
  const [platform, setPlatform] = useState("all");
  const [saved, setSaved] = useState(false);

  const capture = () => {
    if (!text.trim()) return;
    // Save to content pipeline localStorage
    try {
      const cards = JSON.parse(localStorage.getItem("warroom_content_pipeline") || "[]");
      cards.push({
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
        title: text.trim(),
        platforms: platform === "all" ? ["instagram", "tiktok"] : [platform],
        notes: "",
        stage: "idea",
        createdAt: new Date().toISOString(),
      });
      localStorage.setItem("warroom_content_pipeline", JSON.stringify(cards));
      setText("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };

  return (
    <div>
      <textarea value={text} onChange={e => setText(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); capture(); } }}
        placeholder="Drop an idea, topic, or rough hook here..."
        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-warroom-accent h-16 resize-none" />
      <div className="flex items-center justify-between mt-2">
        <div className="flex gap-1">
          {["all", "instagram", "tiktok", "youtube"].map(p => (
            <button key={p} onClick={() => setPlatform(p)}
              className={`text-[10px] px-2 py-1 rounded-md transition ${
                platform === p ? "bg-warroom-accent/20 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text"
              }`}>
              {p === "all" ? "All" : p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
        <button onClick={capture} disabled={!text.trim()}
          className={`text-xs px-3 py-1 rounded-lg font-medium transition ${
            saved ? "bg-green-500/20 text-green-400" : "bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-30"
          }`}>
          {saved ? "✓ Saved" : "Capture"}
        </button>
      </div>
    </div>
  );
}
