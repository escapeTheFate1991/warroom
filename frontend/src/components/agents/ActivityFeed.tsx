"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Activity, Clock, ArrowRight, Zap } from "lucide-react";

const TEAM_API = "http://10.0.0.11:18795";

interface AgentEvent {
  id?: string;
  event_type: string;
  from_agent: string;
  to_agent: string;
  summary: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

const AGENT_META: Record<string, { emoji: string; color: string }> = {
  friday: { emoji: "🖤", color: "text-indigo-400" },
  copy: { emoji: "📝", color: "text-yellow-400" },
  design: { emoji: "🎨", color: "text-pink-400" },
  dev: { emoji: "💻", color: "text-green-400" },
  docs: { emoji: "📚", color: "text-blue-400" },
  support: { emoji: "📞", color: "text-orange-400" },
  inbox: { emoji: "📧", color: "text-cyan-400" },
};

const DEMO_EVENTS: AgentEvent[] = [
  { event_type: "spawn", from_agent: "friday", to_agent: "dev", summary: "Building Social Performance Dashboard", timestamp: new Date(Date.now() - 120000).toISOString() },
  { event_type: "complete", from_agent: "dev", to_agent: "friday", summary: "Social Dashboard component deployed", timestamp: new Date(Date.now() - 60000).toISOString() },
  { event_type: "spawn", from_agent: "friday", to_agent: "design", summary: "Design review for Agent Service Map", timestamp: new Date(Date.now() - 45000).toISOString() },
  { event_type: "spawn", from_agent: "friday", to_agent: "copy", summary: "Write hook formulas for Content Pipeline", timestamp: new Date(Date.now() - 30000).toISOString() },
  { event_type: "complete", from_agent: "copy", to_agent: "friday", summary: "6 hook formula templates created", timestamp: new Date(Date.now() - 15000).toISOString() },
  { event_type: "complete", from_agent: "design", to_agent: "friday", summary: "Agent Service Map layout approved", timestamp: new Date(Date.now() - 5000).toISOString() },
];

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function getAgentInfo(id: string) {
  return AGENT_META[id] || { emoji: "🤖", color: "text-gray-400" };
}

export default function ActivityFeed() {
  const [events, setEvents] = useState<AgentEvent[]>(DEMO_EVENTS);
  const [demoMode, setDemoMode] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchEvents = useCallback(async () => {
    try {
      const resp = await fetch(`${TEAM_API}/events?limit=50`);
      if (resp.ok) {
        const data = await resp.json();
        if (Array.isArray(data) && data.length > 0) {
          setEvents(data);
          setDemoMode(false);
        }
      }
    } catch { /* demo mode stays */ }
  }, []);

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 15000);
    return () => clearInterval(interval);
  }, [fetchEvents]);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Activity size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Activity Feed</h2>
        {demoMode && (
          <span className="ml-2 px-2 py-0.5 bg-warroom-accent/10 text-warroom-accent text-[10px] font-medium rounded-full">DEMO</span>
        )}
        <span className="ml-auto text-xs text-warroom-muted">{events.length} events</span>
      </div>

      {/* Timeline */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-5 top-0 bottom-0 w-px bg-warroom-border" />

          <div className="space-y-1">
            {events.map((event, i) => {
              const from = getAgentInfo(event.from_agent);
              const to = getAgentInfo(event.to_agent);
              const isSpawn = event.event_type === "spawn";

              return (
                <div key={event.id || i} className="flex items-start gap-3 pl-2 py-2 hover:bg-warroom-surface/50 rounded-lg transition group">
                  {/* Timeline dot */}
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 z-10 text-xs ${
                    isSpawn ? "bg-warroom-accent/20" : "bg-green-500/20"
                  }`}>
                    {isSpawn ? <Zap size={12} className="text-warroom-accent" /> : <Activity size={12} className="text-green-400" />}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 text-xs mb-0.5">
                      <span>{from.emoji}</span>
                      <span className={`font-medium ${from.color}`}>{event.from_agent}</span>
                      <ArrowRight size={10} className="text-warroom-muted" />
                      <span>{to.emoji}</span>
                      <span className={`font-medium ${to.color}`}>{event.to_agent}</span>
                      <span className={`ml-1 px-1.5 py-0.5 rounded text-[9px] ${
                        isSpawn ? "bg-warroom-accent/10 text-warroom-accent" : "bg-green-500/10 text-green-400"
                      }`}>
                        {event.event_type}
                      </span>
                    </div>
                    <p className="text-sm text-warroom-text truncate">{event.summary}</p>
                  </div>

                  {/* Timestamp */}
                  <span className="text-[10px] text-warroom-muted flex-shrink-0 flex items-center gap-1 opacity-60 group-hover:opacity-100 transition">
                    <Clock size={10} /> {timeAgo(event.timestamp)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
