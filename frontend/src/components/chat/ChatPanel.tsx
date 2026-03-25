"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Bot, User, Loader2, Mic, MicOff, ChevronDown,
  Plus, Sparkles, X, StopCircle, ArrowDown,
  PanelRightOpen, Copy, Check, Volume2,
  Brain, Wrench, FileText, Search, Terminal, Globe, CheckCircle2, AlertCircle, ChevronRight,
} from "lucide-react";
import SafeMarkdown from "../SafeMarkdown";
import remarkGfm from "remark-gfm";

const MARKDOWN_PROSE = [
  "prose prose-invert prose-sm max-w-none overflow-hidden break-words [overflow-wrap:anywhere]",
  // Spacing
  "[&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>blockquote]:mb-3",
  // Headers
  "[&>h1]:text-lg [&>h1]:font-bold [&>h1]:mb-2 [&>h1]:mt-4",
  "[&>h2]:text-base [&>h2]:font-semibold [&>h2]:mb-2 [&>h2]:mt-3",
  "[&>h3]:text-sm [&>h3]:font-semibold [&>h3]:mb-1.5 [&>h3]:mt-2",
  // Code
  "[&>pre]:bg-black/40 [&>pre]:rounded-xl [&>pre]:p-4 [&>pre]:my-3 [&>pre]:overflow-x-auto [&>pre]:max-w-full",
  "[&>code]:bg-black/30 [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded-md [&>code]:text-warroom-accent [&>code]:break-all",
  "[&>pre>code]:whitespace-pre [&>pre>code]:break-normal",
  // Links
  "[&_a]:break-all [&_a]:text-warroom-accent [&_a]:underline",
  // Lists
  "[&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5",
  "[&_li]:mb-1 [&_li]:leading-relaxed",
  // Task lists (GFM)
  "[&_li.task-list-item]:list-none [&_li.task-list-item]:ml-[-1.25rem]",
  "[&_input[type=checkbox]]:mr-2 [&_input[type=checkbox]]:accent-warroom-accent",
  // Tables (GFM)
  "[&_table]:w-full [&_table]:border-collapse [&_table]:my-3 [&_table]:text-xs",
  "[&_th]:bg-warroom-surface [&_th]:border [&_th]:border-warroom-border [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-semibold [&_th]:text-warroom-text",
  "[&_td]:border [&_td]:border-warroom-border/50 [&_td]:px-3 [&_td]:py-1.5 [&_td]:text-warroom-text/80",
  "[&_tr:nth-child(even)]:bg-warroom-surface/30",
  // Blockquotes
  "[&_blockquote]:border-l-2 [&_blockquote]:border-warroom-accent/40 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-warroom-muted",
  // Horizontal rules
  "[&_hr]:border-warroom-border [&_hr]:my-4",
  // Strikethrough
  "[&_del]:text-warroom-muted [&_del]:line-through",
  // Strong/em
  "[&_strong]:text-warroom-text [&_strong]:font-semibold",
].join(" ");
import ArtifactPanel, { Artifact } from "./ArtifactPanel";
import PromptImproverModal from "./PromptImproverModal";
import { EnhancedWaveformIcon } from "./WaveformAnimation";
import VoiceOrb from "./VoiceOrb";
import type { AgentSummary } from "@/lib/agentAssignments";

/* ── Types ─────────────────────────────────────────────── */

interface ImageAttachment {
  id: string;
  dataUrl: string;  // base64 data URL
  name: string;
}

interface ToolCall {
  id: string;
  name: string;
  input: string;
  status: "running" | "done" | "error";
}

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  thinking?: string;
  images?: ImageAttachment[];
  toolCalls?: ToolCall[];
}

interface GatewayRes {
  type: "res";
  id: string;
  ok: boolean;
  payload?: any;
  error?: { code: string; message: string };
}

import { API as API_URL, authFetch } from "@/lib/api";

/* ── Usage Indicator (replaces connection dot) ─────────── */

interface UsageTier { label: string; percent: number; resetsIn: string; tokens: number; cost: number; }
interface UsageData {
  model: string;
  tiers: UsageTier[];
  details: { today: { tokens: number; cost: number; sessions: number }; week: { tokens: number; cost: number; sessions: number }; month: { tokens: number; cost: number; sessions: number } };
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toString();
}

type AgentOption = Pick<AgentSummary, "id" | "name" | "emoji" | "role" | "model">;

function UsageIndicator({ wsConnected }: { wsConnected: boolean }) {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [models, setModels] = useState<string[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [activeAgent, setActiveAgent] = useState<string>("main");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const resp = await authFetch(`${API_URL}/api/usage`);
        if (resp.ok) setUsage(await resp.json());
      } catch {}
    };
    fetchUsage();
    const interval = setInterval(fetchUsage, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!expanded) return;
    authFetch(`${API_URL}/api/usage/models`).then(r => r.ok ? r.json() : []).then(setModels).catch(() => {});
    authFetch(`${API_URL}/api/agents`).then(r => r.ok ? r.json() : []).then((data: AgentOption[]) => {
      if (Array.isArray(data) && data.length > 0) setAgents(data);
    }).catch(() => {});
  }, [expanded]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setExpanded(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const switchModel = async (model: string) => {
    try {
      await authFetch(`${API_URL}/api/usage/model`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model }) });
      const resp = await authFetch(`${API_URL}/api/usage`);
      if (resp.ok) setUsage(await resp.json());
    } catch {}
  };

  const switchAgent = async (agentId: string) => {
    setActiveAgent(agentId);
    const agent = agents.find(a => a.id === agentId);
    if (agent?.model) {
      await switchModel(agent.model);
    }
    // Notify the chat WS to switch session to this agent
    // This is handled by the parent via a custom event
    window.dispatchEvent(new CustomEvent("warroom:switch-agent", { detail: { agentId, model: agent?.model } }));
  };

  const sessionPct = usage?.tiers?.[0]?.percent ?? 0;
  const dotColor = !wsConnected ? "bg-warroom-danger animate-pulse" : sessionPct > 80 ? "bg-red-500" : sessionPct > 60 ? "bg-amber-500" : "bg-emerald-500";
  const displayModel = (usage?.model || "unknown").replace("anthropic/", "").replace("google/", "");
  const activeAgentData = agents.find(a => a.id === activeAgent);
  const displayLabel = activeAgentData && activeAgent !== "main"
    ? `${activeAgentData.name} · ${displayModel}`
    : displayModel;

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-1.5 hover:bg-warroom-border/30 rounded-full px-1.5 py-0.5 transition" title={`${displayLabel} · ${sessionPct}% session`}>
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotColor}`} />
        <span className="text-[10px] text-warroom-muted truncate max-w-[160px]">{displayLabel}</span>
        <span className="text-[10px] text-warroom-muted/60">·</span>
        <span className="text-[10px] text-warroom-muted">{sessionPct}%</span>
        <ChevronDown size={10} className={`text-warroom-muted flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`} />
      </button>

      {expanded && (
        <div className="absolute bottom-full right-0 mb-2 w-80 bg-warroom-surface border border-warroom-border rounded-lg shadow-xl z-50 p-3 space-y-3">
          {/* Agent Switcher */}
          {agents.length > 0 && (
            <div>
              <label className="text-[9px] text-warroom-muted uppercase tracking-wide font-medium">Agent</label>
              <div className="mt-1 space-y-0.5 max-h-40 overflow-y-auto">
                {/* Main agent (Friday) */}
                <button
                  onClick={() => switchAgent("main")}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition ${
                    activeAgent === "main" ? "bg-warroom-accent/10 border border-warroom-accent/30" : "hover:bg-warroom-border/30"
                  }`}
                >
                  <span className="text-sm">🖤</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-warroom-text">Friday</p>
                    <p className="text-[9px] text-warroom-muted truncate">{usage?.model || "claude-opus-4-6"}</p>
                  </div>
                  {activeAgent === "main" && <span className="w-1.5 h-1.5 rounded-full bg-warroom-accent flex-shrink-0" />}
                </button>
                {/* Created agents */}
                {agents.map(agent => (
                  <button
                    key={agent.id}
                    onClick={() => switchAgent(agent.id)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition ${
                      activeAgent === agent.id ? "bg-warroom-accent/10 border border-warroom-accent/30" : "hover:bg-warroom-border/30"
                    }`}
                  >
                    <span className="text-sm">{agent.emoji}</span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-warroom-text">{agent.name}</p>
                      <p className="text-[9px] text-warroom-muted truncate">{(agent.model || "").replace("anthropic/", "").replace("google/", "")}</p>
                    </div>
                    {activeAgent === agent.id && <span className="w-1.5 h-1.5 rounded-full bg-warroom-accent flex-shrink-0" />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Model Override */}
          <div>
            <label className="text-[9px] text-warroom-muted uppercase tracking-wide font-medium">
              {activeAgent !== "main" ? `Model (${activeAgentData?.name || "Agent"})` : "Model Override"}
            </label>
            {activeAgent !== "main" && activeAgentData ? (
              <div className="mt-1 bg-warroom-bg border border-warroom-border rounded px-2 py-1.5 text-xs text-warroom-muted">
                {(activeAgentData.model || "").replace("anthropic/", "").replace("google/", "")}
                <span className="text-[9px] text-warroom-muted/50 ml-1">(set in agent config)</span>
              </div>
            ) : models.length > 0 ? (
              <select value={usage?.model ? "anthropic/" + usage.model : ""} onChange={(e) => switchModel(e.target.value)}
                className="w-full mt-1 bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent">
                {models.map(m => <option key={m} value={m}>{m.replace("anthropic/", "").replace("google/", "")}</option>)}
              </select>
            ) : (
              <p className="text-xs text-warroom-text mt-0.5">{displayModel}</p>
            )}
          </div>

          {/* Progress bars */}
          {usage?.tiers?.map((tier, i) => {
            const barColor = tier.percent > 80 ? "bg-red-500" : tier.percent > 60 ? "bg-amber-500" : "bg-emerald-500";
            return (
              <div key={i} className="space-y-1">
                <div className="flex justify-between text-[9px] text-warroom-muted">
                  <span>{tier.label}</span>
                  <span>Resets {tier.resetsIn}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-warroom-bg rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${Math.max(1, tier.percent)}%` }} />
                  </div>
                  <span className="text-[10px] font-medium text-warroom-text w-8 text-right">{tier.percent}%</span>
                </div>
                <div className="flex gap-3 text-[9px] text-warroom-muted">
                  <span>{formatTokens(tier.tokens)} tokens</span>
                  <span>${tier.cost.toFixed(2)}</span>
                </div>
              </div>
            );
          })}

          {/* Cost summary */}
          {usage?.details && (
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-warroom-border">
              {(["today", "week", "month"] as const).map(period => (
                <div key={period} className="text-center">
                  <p className="text-xs font-medium text-warroom-text">${usage.details[period].cost.toFixed(2)}</p>
                  <p className="text-[9px] text-warroom-muted capitalize">{period}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Waveform Icon (now using enhanced version from WaveformAnimation.tsx) ─────────────────────────────────────── */

/* ── Helpers ───────────────────────────────────────────── */

function extractText(msg: any): string {
  if (typeof msg === "string") return msg;
  if (!msg) return "";
  if (msg.content) {
    if (typeof msg.content === "string") return msg.content;
    if (Array.isArray(msg.content)) {
      return msg.content
        .filter((c: any) => c.type === "text")
        .map((c: any) => c.text)
        .join("\n");
    }
  }
  if (msg.text) return msg.text;
  return JSON.stringify(msg);
}

function extractRole(msg: any): "user" | "assistant" | "system" {
  if (msg.role === "user") return "user";
  if (msg.role === "assistant") return "assistant";
  return "system";
}

function getLanguageLabel(lang?: string): string {
  const labels: Record<string, string> = {
    typescript: "TypeScript", tsx: "TSX", javascript: "JavaScript", jsx: "JSX",
    python: "Python", bash: "Bash", sh: "Shell", json: "JSON", yaml: "YAML",
    html: "HTML", css: "CSS", sql: "SQL", markdown: "Markdown", md: "Markdown",
  };
  return lang ? (labels[lang.toLowerCase()] || lang.toUpperCase()) : "Text";
}

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-warroom-surface border border-warroom-border/50 text-xs text-warroom-muted hover:text-warroom-text transition flex-shrink-0"
      title={`Copy ${label.toLowerCase()}`}
    >
      {copied ? <Check size={13} className="text-green-400" /> : <Copy size={13} />}
      <span>{copied ? "Copied" : label}</span>
    </button>
  );
}

function UrlBox({ url }: { url: string }) {
  return (
    <div className="my-2">
      <div className="bg-black/30 border border-warroom-border/50 rounded-xl px-4 py-2.5 flex items-center gap-3 min-w-0">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-warroom-accent hover:underline truncate min-w-0 flex-1 font-mono"
          title={url}
        >
          {url}
        </a>
        <CopyButton text={url} label="Copy" />
      </div>
    </div>
  );
}

export default function ChatPanel() {
  const [messages, setMessagesRaw] = useState<Message[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const cached = localStorage.getItem("warroom-chat-messages");
        if (cached) {
          const parsed = JSON.parse(cached);
          return parsed.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) }));
        }
      } catch {}
    }
    return [];
  });
  const setMessages = useCallback((val: Message[] | ((prev: Message[]) => Message[])) => {
    setMessagesRaw(prev => {
      const next = typeof val === "function" ? val(prev) : val;
      if (typeof window !== "undefined") {
        try {
          // Keep last 100 messages in cache to avoid storage limits
          const toCache = next.slice(-100).map(m => ({
            ...m,
            timestamp: m.timestamp.toISOString(),
            images: undefined, // Don't cache base64 images
            toolCalls: m.toolCalls, // Preserve tool history
          }));
          localStorage.setItem("warroom-chat-messages", JSON.stringify(toCache));
        } catch {}
      }
      return next;
    });
  }, []);
  const [input, setInputRaw] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("warroom-chat-input") || "";
    }
    return "";
  });
  const setInput = useCallback((val: string | ((prev: string) => string)) => {
    setInputRaw(prev => {
      const next = typeof val === "function" ? val(prev) : val;
      if (typeof window !== "undefined") {
        if (next) {
          localStorage.setItem("warroom-chat-input", next);
        } else {
          localStorage.removeItem("warroom-chat-input");
        }
      }
      return next;
    });
  }, []);
  const [pendingImages, setPendingImages] = useState<ImageAttachment[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("warroom-chat-images");
        if (saved) {
          const parsed = JSON.parse(saved) as ImageAttachment[];
          // Check staleness (24h)
          const savedAt = localStorage.getItem("warroom-chat-images-ts");
          if (savedAt && Date.now() - Number(savedAt) > 24 * 60 * 60 * 1000) {
            localStorage.removeItem("warroom-chat-images");
            localStorage.removeItem("warroom-chat-images-ts");
            return [];
          }
          return parsed;
        }
      } catch {}
    }
    return [];
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [streamText, setStreamText] = useState<string | null>(null);

  // Voice states
  const [isRecording, setIsRecording] = useState(false);
  const [isConversationMode, setIsConversationMode] = useState(false);
  const [isTTSEnabled, setIsTTSEnabled] = useState(false);
  const [hasVoiceActivity, setHasVoiceActivity] = useState(false);
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);
  const [spokenText, setSpokenText] = useState<string | undefined>();
  const [ttsDurationMs, setTtsDurationMs] = useState<number | undefined>();
  const [recordingDuration, setRecordingDuration] = useState(0);

  // Generation state — single source of truth for stop/send button
  const isGeneratingRef = useRef(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const updateGenerating = useCallback((val: boolean) => {
    isGeneratingRef.current = val;
    setIsGenerating(val);
  }, []);

  // Magic prompt states
  const [isPolishing, setIsPolishing] = useState(false);

  // Alert banners
  const [rateLimitAlert, setRateLimitAlert] = useState<string | null>(null);
  const [compactionAlert, setCompactionAlert] = useState<false | "start" | "end">(false);

  // Prompt improver
  const [improverState, setImproverState] = useState<{
    show: boolean;
    originalPrompt: string;
    questions: string[];
    contextSummary?: string;
    isImproving: boolean;
  }>({ show: false, originalPrompt: "", questions: [], isImproving: false });

  // Token usage
  const [tokenUsage, setTokenUsage] = useState<{ totalTokens: number; contextWindow: number; percentage: number; compactionCount: number } | null>(null);
  const lastCompactionRef = useRef<number>(-1);

  // Artifact panel
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [activeArtifactIndex, setActiveArtifactIndex] = useState(0);
  const [showArtifacts, setShowArtifacts] = useState(false);

  // Streaming progress (tool calls + thinking)
  const [activeTools, setActiveTools] = useState<ToolCall[]>([]);
  const [thinkingText, setThinkingText] = useState<string | null>(null);
  const [thinkingCollapsed, setThinkingCollapsed] = useState(false);
  const activeToolsRef = useRef<ToolCall[]>([]);

  // Task completion review — holds stop button until summary renders
  const [taskReview, setTaskReview] = useState<{ tools: ToolCall[]; show: boolean } | null>(null);
  const taskReviewTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Persist pending images to localStorage (max 5MB check)
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (pendingImages.length === 0) {
      localStorage.removeItem("warroom-chat-images");
      localStorage.removeItem("warroom-chat-images-ts");
    } else {
      try {
        const json = JSON.stringify(pendingImages);
        if (json.length < 5 * 1024 * 1024) { // 5MB cap
          localStorage.setItem("warroom-chat-images", json);
          localStorage.setItem("warroom-chat-images-ts", String(Date.now()));
        }
      } catch {} // quota exceeded — skip silently
    }
  }, [pendingImages]);

  // UI states
  const [showScrollButton, setShowScrollButton] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const streamTextRef = useRef<string | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadFrameRef = useRef<number>(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const conversationStreamRef = useRef<MediaStream | null>(null);
  const conversationRecorderRef = useRef<MediaRecorder | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const conversationActiveRef = useRef<boolean>(false);
  const deviceChangeHandlerRef = useRef<(() => void) | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioQueueRef = useRef<(() => Promise<void>)[]>([]);
  const audioPlayingRef = useRef<boolean>(false);
  const lastSpokenTextRef = useRef<string>("");
  const spokenLengthRef = useRef<number>(0); // Track how much streaming text has been sent to TTS
  const lastSpokenTimeRef = useRef<number>(0);
  // Accumulates assistant text across tool cycles within a single response
  const partialContentRef = useRef<string>("");
  const [partialContent, setPartialContent] = useState<string>("");
  const updatePartial = useCallback((val: string) => {
    partialContentRef.current = val;
    setPartialContent(val);
  }, []);

  // Keep ref in sync with state
  useEffect(() => { streamTextRef.current = streamText; }, [streamText]);

  // Fetch token usage
  const fetchTokenUsage = useCallback(async () => {
    try {
      const resp = await authFetch(`${API_URL}/api/chat/session-status`);
      if (resp.ok) {
        const data = await resp.json();
        setTokenUsage(data);
        // Detect compaction
        if (lastCompactionRef.current === -1) {
          lastCompactionRef.current = data.compactionCount;
        } else if (data.compactionCount > lastCompactionRef.current) {
          lastCompactionRef.current = data.compactionCount;
          // Show persistent banner (fallback for polling-based detection)
          setCompactionAlert("end");
          setTimeout(() => setCompactionAlert(false), 30000);
          setMessages(prev => [...prev, {
            id: crypto.randomUUID(),
            role: "system",
            content: "🧹 Context compressed — older messages summarized to free up space.",
            timestamp: new Date(),
          }]);
        }
      }
    } catch {}
  }, []);

  // Poll token usage on mount + after each response
  useEffect(() => { fetchTokenUsage(); }, [fetchTokenUsage]);
  useEffect(() => { if (!isLoading && !streamText) fetchTokenUsage(); }, [isLoading, streamText, fetchTokenUsage]);

  // Artifact helpers
  const openArtifact = useCallback((artifact: Artifact) => {
    setArtifacts(prev => {
      const exists = prev.find(a => a.id === artifact.id);
      if (exists) return prev;
      return [...prev, artifact];
    });
    setActiveArtifactIndex(prev => artifacts.length); // select new one
    setShowArtifacts(true);
  }, [artifacts.length]);

  const removeArtifact = useCallback((id: string) => {
    setArtifacts(prev => {
      const next = prev.filter(a => a.id !== id);
      if (next.length === 0) setShowArtifacts(false);
      return next;
    });
    setActiveArtifactIndex(prev => Math.max(0, prev - 1));
  }, []);

  // Split message content into text segments, code blocks, and URL boxes
  type ContentSegment =
    | { type: "text"; content: string }
    | { type: "code"; code: string; language: string; title: string; content?: never }
    | { type: "url"; url: string };

  // Split text into text + url segments (for non-code parts)
  const splitTextWithUrls = useCallback((text: string): ContentSegment[] => {
    // Match URLs that are NOT inside markdown link syntax [text](url)
    // We capture any https?:// URL that isn't preceded by ]( 
    const urlRegex = /(https?:\/\/[^\s<>)"'\]]+)/g;
    const segments: ContentSegment[] = [];
    let lastIndex = 0;
    let match;

    while ((match = urlRegex.exec(text)) !== null) {
      const url = match[1];
      const before = text.slice(Math.max(0, match.index - 2), match.index);
      // Skip URLs inside markdown links like [text](url)
      if (before.endsWith("](")) continue;
      // Skip URLs inside inline code `url`
      const textBefore = text.slice(lastIndex, match.index);
      const backticksBefore = (textBefore.match(/`/g) || []).length;
      if (backticksBefore % 2 === 1) continue; // Inside backticks

      const trimmedBefore = text.slice(lastIndex, match.index).trim();
      if (trimmedBefore) {
        segments.push({ type: "text", content: trimmedBefore });
      }
      segments.push({ type: "url", url: url.replace(/[.,;:!?)]+$/, "") }); // Strip trailing punctuation
      lastIndex = match.index + match[0].length;
    }

    const remaining = text.slice(lastIndex).trim();
    if (remaining) {
      segments.push({ type: "text", content: remaining });
    }

    if (segments.length === 0 && text.trim()) {
      segments.push({ type: "text", content: text });
    }

    return segments;
  }, []);

  const splitContentWithCodeBlocks = useCallback((content: string): ContentSegment[] => {
    const segments: ContentSegment[] = [];
    const regex = /```(\w+)?[\r\n]+([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(content)) !== null) {
      // Text before this code block — split for URLs too
      const textBefore = content.slice(lastIndex, match.index).trim();
      if (textBefore) {
        segments.push(...splitTextWithUrls(textBefore));
      }

      const lang = match[1] || "text";
      const code = match[2].trim();
      const lines = code.split("\n").length;

      if (lines >= 4) {
        // Look for a title in the text before
        const preceding = content.slice(Math.max(0, match.index - 150), match.index);
        const filenameMatch = preceding.match(/[`"]([^`"]+\.\w+)[`"]/);
        const headerMatch = preceding.match(/\*\*(.+?)\*\*\s*$/);
        const title = filenameMatch ? filenameMatch[1] : headerMatch ? headerMatch[1] : `${lang} snippet`;
        segments.push({ type: "code", code, language: lang, title });
      } else {
        // Short code block — render as inline markdown
        segments.push({ type: "text", content: match[0] });
      }

      lastIndex = match.index + match[0].length;
    }

    // Remaining text after last code block — split for URLs too
    const remaining = content.slice(lastIndex).trim();
    if (remaining) {
      segments.push(...splitTextWithUrls(remaining));
    }

    // If no segments found, return the whole thing as text
    if (segments.length === 0) {
      segments.push({ type: "text", content });
    }

    return segments;
  }, [splitTextWithUrls]);

  const scrollToBottom = useCallback((force = false) => {
    if (force) {
      showScrollBtnRef.current = false;
      setShowScrollButton(false);
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Auto-scroll only when user is already at the bottom
  useEffect(() => {
    if (!showScrollBtnRef.current) scrollToBottom();
  }, [messages, streamText, partialContent, scrollToBottom]);

  // Scroll to bottom on initial load (after messages populate)
  const initialScrollDone = useRef(false);
  useEffect(() => {
    if (messages.length > 0 && !initialScrollDone.current) {
      initialScrollDone.current = true;
      // Use instant scroll (not smooth) so user doesn't see the scroll animation
      requestAnimationFrame(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "instant" });
      });
    }
  }, [messages]);

  // Scroll to bottom when panel becomes visible again (tab switch back)
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    let wasHidden = false;
    const observer = new ResizeObserver(() => {
      const visible = container.offsetHeight > 0;
      if (visible && wasHidden && messages.length > 0) {
        requestAnimationFrame(() => {
          messagesEndRef.current?.scrollIntoView({ behavior: "instant" });
          showScrollBtnRef.current = false;
          setShowScrollButton(false);
        });
      }
      wasHidden = !visible;
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [messages.length]);

  // Scroll detection (throttled)
  const showScrollBtnRef = useRef(false);
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    let ticking = false;
    const handleScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const { scrollTop, scrollHeight, clientHeight } = container;
        const isScrolledUp = scrollHeight - scrollTop - clientHeight > 100;
        if (isScrolledUp !== showScrollBtnRef.current) {
          showScrollBtnRef.current = isScrolledUp;
          setShowScrollButton(isScrolledUp);
        }
        ticking = false;
      });
    };
    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-resize textarea
  const resizeTextarea = useCallback(() => {
    const t = textareaRef.current;
    if (!t) return;
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 200) + "px";
    t.style.overflow = t.scrollHeight > 200 ? "auto" : "hidden";
  }, []);

  useEffect(() => { resizeTextarea(); }, [input, resizeTextarea]);

  /* ── WebSocket ─────────────────────────────────────── */

  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;
    let destroyed = false;

    const connectWs = () => {
      if (destroyed) return;
      const wsUrl = `${API_URL.replace("http", "ws")}/api/chat/ws`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {};

      ws.onmessage = (event) => {
        let data: any;
        try { data = JSON.parse(event.data); } catch { return; }

        if (data.type === "connected") { setWsConnected(true); return; }
        if (data.type === "status" || data.type === "pong") return;
        if (data.type === "error") {
          const errMsg = data.message || data.error?.message || "";
          const errCode = data.code || data.error?.code || "";
          // Detect rate limit errors
          if (errCode === "rate_limited" || errMsg.toLowerCase().includes("rate limit") || errMsg.includes("429") || errMsg.toLowerCase().includes("too many")) {
            setRateLimitAlert(errMsg || "Rate limit reached. Please wait before sending another message.");
            setTimeout(() => setRateLimitAlert(null), 15000);
            updateGenerating(false);
            // Don't mark WS as disconnected for rate limits — connection is fine
            return;
          }
          setWsConnected(false);
          return;
        }
        if (data.type === "compaction") {
          if (data.phase === "start") {
            setCompactionAlert("start");
          } else if (data.phase === "end") {
            setCompactionAlert("end");
            // Keep banner visible for 30s after completion
            setTimeout(() => setCompactionAlert(false), 30000);
            setMessages(prev => [...prev, {
              id: crypto.randomUUID(),
              role: "system" as const,
              content: "🧹 " + (data.message || "Context compressed — older messages summarized to free up space."),
              timestamp: new Date(),
            }]);
            // Refresh token usage
            fetchTokenUsage();
          }
          return;
        }
        if (data.type === "session_changed") {
          setMessages([]);
          setStreamText(null);
          streamTextRef.current = null;
          return;
        }

        if (data.type === "res") {
          const res = data as GatewayRes;
          if (res.ok && res.payload?.messages) {
            const history: Message[] = res.payload.messages
              .filter((m: any) => m.role === "user" || m.role === "assistant")
              .map((m: any) => ({
                id: crypto.randomUUID(),
                role: extractRole(m),
                content: extractText(m),
                timestamp: new Date(m.timestamp || Date.now()),
              }))
              .filter((m: Message) => m.content.trim().length > 0);
            setMessages(history);
          }
          if (res.ok && res.payload?.runId) {
            setIsLoading(true);
            updateGenerating(true);
          }
          if (!res.ok) {
            setIsLoading(false);
            updateGenerating(false);
            const errMsg = res.error?.message || "request failed";
            // Detect rate limit in error responses
            if (res.error?.code === "rate_limited" || errMsg.toLowerCase().includes("rate limit") || errMsg.includes("429")) {
              setRateLimitAlert(errMsg);
              setTimeout(() => setRateLimitAlert(null), 15000);
            }
            setMessages(prev => [...prev, {
              id: crypto.randomUUID(),
              role: "system",
              content: `Error: ${errMsg}`,
              timestamp: new Date(),
            }]);
          }
          return;
        }

        if (data.type === "event" && data.event === "chat") {
          const p = data.payload || {};
          const state = p.state;
          const message = p.message;


          // --- Thinking blocks ---
          if (state === "thinking") {
            const thinking = message?.content?.[0]?.thinking || message?.thinking || extractText(message) || "";
            if (thinking) {
              setThinkingText(thinking);
              setThinkingCollapsed(false);
              setIsLoading(false);
            }
            return;
          }

          // --- Tool use (agent calling a tool) ---
          if (state === "tool_use") {
            const blocks = Array.isArray(message?.content) ? message.content : [];
            const toolBlock = blocks.find((b: any) => b.type === "tool_use") || message;
            const toolName = toolBlock?.name || toolBlock?.tool_name || "tool";
            const toolInput = toolBlock?.input ? JSON.stringify(toolBlock.input).slice(0, 120) : "";
            const toolId = toolBlock?.id || crypto.randomUUID();
            const newTool: ToolCall = { id: toolId, name: toolName, input: toolInput, status: "running" };
            // Snapshot any streaming text before tool call so it stays visible
            if (streamTextRef.current) {
              updatePartial(streamTextRef.current);
            }
            setActiveTools(prev => {
              const updated = [...prev, newTool];
              activeToolsRef.current = updated;
              return updated;
            });
            setThinkingText(null);
            setIsLoading(false);
            return;
          }

          // --- Tool result ---
          if (state === "tool_result") {
            const toolId = message?.tool_use_id || message?.id || "";
            const isError = message?.is_error === true || message?.status === "error";
            setActiveTools(prev => {
              const updated = prev.map(t =>
                t.id === toolId ? { ...t, status: (isError ? "error" : "done") as ToolCall["status"] } : t
              );
              // If no matching ID, mark the last running tool as done
              if (!prev.some(t => t.id === toolId)) {
                const lastRunning = [...updated].reverse().findIndex(t => t.status === "running");
                if (lastRunning >= 0) {
                  const idx = updated.length - 1 - lastRunning;
                  updated[idx] = { ...updated[idx], status: isError ? "error" : "done" };
                }
              }
              activeToolsRef.current = updated;
              return updated;
            });
            return;
          }

          if (state === "delta") {
            const text = extractText(message);
            if (text) {
              // Gateway sends cumulative text per assistant turn, but resets between tool cycles.
              // If new delta is shorter than what we had (new turn after tool), preserve partial.
              const prev = streamTextRef.current || "";
              if (text.length < prev.length * 0.5 && prev.length > 20) {
                // Looks like a new turn — snapshot previous text into partial buffer
                updatePartial(prev);
                spokenLengthRef.current = 0; // Reset sentence tracking
              }
              setStreamText(text);
              streamTextRef.current = text;
              setIsLoading(false);

              // Streaming TTS: extract complete sentences and speak them as they arrive
              if (conversationActiveRef.current || isTTSEnabled) {
                const unspoken = text.slice(spokenLengthRef.current);
                // Match sentences ending with . ! ? followed by space, newline, or another sentence
                const sentenceEnd = unspoken.search(/[.!?][\s\n]/);
                if (sentenceEnd > 0) {
                  const sentence = unspoken.slice(0, sentenceEnd + 1).trim();
                  if (sentence.length > 5) {
                    spokenLengthRef.current += sentenceEnd + 2;
                    console.log("[voice] Streaming sentence to TTS:", sentence.slice(0, 50));
                    speakText(sentence);
                  }
                }
              }
            }
          } else if (state === "final") {
            const text = extractText(message);
            const completedTools = activeToolsRef.current.length > 0
              ? activeToolsRef.current.map(t => ({ ...t, status: "done" as ToolCall["status"] }))
              : undefined;
            if (text && text.trim().length > 0) {
              setMessages(prev => [...prev, {
                id: crypto.randomUUID(),
                role: "assistant",
                content: text,
                timestamp: new Date(message?.timestamp || Date.now()),
                toolCalls: completedTools,
              }]);
            }
            setStreamText(null);
            streamTextRef.current = null;
            updatePartial("");
            setIsLoading(false);
            setThinkingText(null);

            // If tools were used, show task completion review before releasing send button
            if (completedTools && completedTools.length > 0) {
              // Clear any previous timer
              if (taskReviewTimerRef.current) clearTimeout(taskReviewTimerRef.current);
              setTaskReview({ tools: completedTools, show: true });
              // Hold for 2.5s so user sees completion, then release
              taskReviewTimerRef.current = setTimeout(() => {
                setTaskReview(null);
                updateGenerating(false);
                setActiveTools([]);
                activeToolsRef.current = [];
              }, 2500);
            } else {
              // No tools — release immediately
              updateGenerating(false);
              setActiveTools([]);
              activeToolsRef.current = [];
            }

            // If in conversation mode or TTS enabled, speak any remaining unspoken text
            if (text && (conversationActiveRef.current || isTTSEnabled)) {
              const remaining = text.slice(spokenLengthRef.current).trim();
              console.log("[voice] Final handler - remaining:", remaining.length, "chars, spokenSoFar:", spokenLengthRef.current);
              if (remaining.length > 3) {
                speakText(remaining);
              }
              spokenLengthRef.current = 0;
            }
          } else if (state === "aborted") {
            const partial = streamTextRef.current || partialContentRef.current;
            if (partial && partial.trim().length > 0) {
              setMessages(prev => [...prev, {
                id: crypto.randomUUID(),
                role: "assistant",
                content: partial + "\n\n*[aborted]*",
                timestamp: new Date(),
              }]);
            }
            setStreamText(null);
            streamTextRef.current = null;
            updatePartial("");
            setIsLoading(false);
            updateGenerating(false);
          } else if (state === "error") {
            // Catch rate limit and other errors from the stream
            const errText = extractText(message) || p.error || "";
            if (errText.toLowerCase().includes("rate limit") || errText.includes("429")) {
              setRateLimitAlert(errText || "API rate limit reached. Please wait.");
              setTimeout(() => setRateLimitAlert(null), 15000);
            }
            setStreamText(null);
            streamTextRef.current = null;
            updatePartial("");
            setIsLoading(false);
            updateGenerating(false);
          }
          return;
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (!destroyed) reconnectTimer = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => ws.close();
      wsRef.current = ws;
    };

    connectWs();
    return () => {
      destroyed = true;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  /* ── Agent switching ──────────────────────────────────── */

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (!detail?.agentId) return;
      const agentId = detail.agentId;
      // Build session key: agent:{agentId}:warroom for sub-agents, warroom for main
      const sessionKey = agentId === "main" ? "warroom" : `agent:${agentId}:warroom`;
      // Send set_session to switch the WS to this agent's session
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "set_session", sessionKey }));
      }
    };
    window.addEventListener("warroom:switch-agent", handler);
    return () => window.removeEventListener("warroom:switch-agent", handler);
  }, []);

  /* ── Image handling ──────────────────────────────────── */

  const addImagesFromFiles = useCallback((files: FileList | File[]) => {
    Array.from(files).forEach(file => {
      if (!file.type.startsWith("image/")) return;
      if (file.size > 10 * 1024 * 1024) return; // 10MB max
      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUrl = e.target?.result as string;
        setPendingImages(prev => [...prev, {
          id: crypto.randomUUID(),
          dataUrl,
          name: file.name,
        }]);
      };
      reader.readAsDataURL(file);
    });
  }, []);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const imageFiles: File[] = [];
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith("image/")) {
        const file = items[i].getAsFile();
        if (file) imageFiles.push(file);
      }
    }
    if (imageFiles.length > 0) {
      e.preventDefault();
      addImagesFromFiles(imageFiles);
    }
  }, [addImagesFromFiles]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      addImagesFromFiles(e.dataTransfer.files);
    }
  }, [addImagesFromFiles]);

  const removeImage = useCallback((id: string) => {
    setPendingImages(prev => prev.filter(img => img.id !== id));
  }, []);

  /* ── Send ───────────────────────────────────────────── */

  const sendMessage = (overrideText?: string) => {
    const text = (overrideText || input).trim();
    const images = pendingImages;
    if (isGeneratingRef.current) return; // Block sends while generating
    if ((!text && images.length === 0) || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: "user",
      content: text || "(image)",
      timestamp: new Date(),
      images: images.length > 0 ? images : undefined,
    }]);
    if (!overrideText) setInput("");
    setPendingImages([]);
    setIsLoading(true);
    updateGenerating(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.overflow = "hidden";
    }

    const payload: any = { action: "send", message: text || "What do you see in this image?" };
    if (images.length > 0) {
      payload.images = images.map(img => img.dataUrl);
    }
    wsRef.current.send(JSON.stringify(payload));
  };

  const abortResponse = () => {
    wsRef.current?.send(JSON.stringify({ action: "abort" }));
    setIsLoading(false);
    setStreamText(null);
    streamTextRef.current = null;
    updateGenerating(false);
    // Clear task review if aborting during review period
    if (taskReviewTimerRef.current) clearTimeout(taskReviewTimerRef.current);
    setTaskReview(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      // On touch devices (mobile), Enter = newline. Send only via button.
      const isTouchDevice =
        "ontouchstart" in window || navigator.maxTouchPoints > 0;
      if (isTouchDevice) return; // let Enter insert a newline naturally
      if (!e.shiftKey) {
        e.preventDefault();
        if (!isGeneratingRef.current) sendMessage();
      }
    }
  };

  /* ── TTS (for conversation mode) ────────────────────── */

  const processAudioQueue = async () => {
    if (audioPlayingRef.current) return;
    const next = audioQueueRef.current.shift();
    if (!next) return;
    audioPlayingRef.current = true;
    await next();
    audioPlayingRef.current = false;
    setIsTTSPlaying(false);
    setSpokenText(undefined);
    // Play next in queue if any
    if ((conversationActiveRef.current || isTTSEnabled) && audioQueueRef.current.length > 0) {
      processAudioQueue();
    }
  };

  const speakText = async (text: string) => {
    if (!conversationActiveRef.current && !isTTSEnabled) return;
    // Skip TTS for code-heavy responses
    const codeBlockCount = (text.match(/```/g) || []).length / 2;
    const codeRatio = text.replace(/```[\s\S]*?```/g, '').length / text.length;
    if (codeBlockCount >= 1 && codeRatio < 0.3) return; // Mostly code, don't speak
    // Deduplicate — don't speak the same text twice within 10s window
    const now = Date.now();
    const textHash = text.slice(0, 100);
    if (textHash === lastSpokenTextRef.current && now - lastSpokenTimeRef.current < 10000) return;
    lastSpokenTextRef.current = textHash;
    lastSpokenTimeRef.current = now;

    // Strip markdown for clean spoken text
    const cleanText = text.replace(/```[\s\S]*?```/g, "").replace(/[*_~`#>]/g, "").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").trim();
    const spokenSlice = cleanText.slice(0, 500);
    // Estimate duration: ~150ms per word for edge-tts
    const wordCount = spokenSlice.split(/\s+/).length;
    const estimatedMs = wordCount * 150;

    const playTask = async () => {
      if (!conversationActiveRef.current && !isTTSEnabled) return;
      try {
        const resp = await authFetch(`${API_URL}/api/voice/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: spokenSlice }),
        });
        if (resp.ok && (conversationActiveRef.current || isTTSEnabled)) {
          const blob = await resp.blob();
          const audio = new Audio(URL.createObjectURL(blob));
          currentAudioRef.current = audio;
          // Update duration estimate from actual audio if possible
          audio.onloadedmetadata = () => {
            if (audio.duration && isFinite(audio.duration)) {
              setTtsDurationMs(audio.duration * 1000);
            }
          };
          await new Promise<void>((resolve) => {
            audio.onended = () => { currentAudioRef.current = null; setSpokenText(undefined); setIsTTSPlaying(false); resolve(); };
            audio.onerror = (e) => { console.error("TTS audio error:", e); currentAudioRef.current = null; setSpokenText(undefined); setIsTTSPlaying(false); resolve(); };
            audio.play().then(() => {
              console.log("TTS playing, duration:", audio.duration);
              // Only show captions + mark speaking AFTER play succeeds
              setIsTTSPlaying(true);
              setSpokenText(spokenSlice);
              setTtsDurationMs(audio.duration && isFinite(audio.duration) ? audio.duration * 1000 : estimatedMs);
            }).catch((err) => { console.error("TTS play() rejected:", err); setSpokenText(undefined); setIsTTSPlaying(false); resolve(); });
          });
        }
      } catch (err) {
        console.error("TTS failed:", err);
        setSpokenText(undefined);
      }
    };

    audioQueueRef.current.push(playTask);
    processAudioQueue();
  };

  /* ── Voice Recording (STT — mic button) ─────────────── */

  const toggleRecording = async () => {
    if (isRecording) stopRecording();
    else startRecording();
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });

      // Set up audio analyser for VAD visualization
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      audioContextRef.current = audioCtx;

      // Monitor for voice activity
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const checkVAD = () => {
        if (!analyserRef.current) return;
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        setHasVoiceActivity(avg > 15); // Threshold for voice detection
        vadFrameRef.current = requestAnimationFrame(checkVAD);
      };
      checkVAD();

      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        cancelAnimationFrame(vadFrameRef.current);
        analyserRef.current = null;
        audioCtx.close();
        setHasVoiceActivity(false);
        const blob = new Blob(chunks, { type: "audio/webm" });
        await transcribeAudio(blob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setRecordingDuration(0);
      recordingTimerRef.current = setInterval(() => setRecordingDuration(d => d + 1), 1000);
    } catch (err) {
      console.error("Microphone access denied:", err);
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.ondataavailable = null;
      mediaRecorderRef.current.onstop = null;
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
    }
    cancelAnimationFrame(vadFrameRef.current);
    analyserRef.current = null;
    audioContextRef.current?.close();
    setIsRecording(false);
    setHasVoiceActivity(false);
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
  };

  const transcribeAudio = async (blob: Blob) => {
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    try {
      const resp = await authFetch(`${API_URL}/api/voice/transcribe`, { method: "POST", body: formData });
      if (resp.ok) {
        const data = await resp.json();
        if (data.text) {
          setInput(prev => prev + (prev ? " " : "") + data.text);
          textareaRef.current?.focus();
        }
      }
    } catch {
      console.error("Transcription failed");
    }
  };

  /* ── Conversation Mode (waveform button) ────────────── */

  const toggleConversationMode = async () => {
    if (isConversationMode) {
      stopConversationMode();
    } else {
      startConversationMode();
    }
  };

  const startConversationMode = async () => {
    try {
      // Switch BT to HFP (mic mode) via host-side server before acquiring mic
      try {
        await fetch("http://127.0.0.1:18797/hfp", { method: "POST" });
        await new Promise(r => setTimeout(r, 500));
      } catch {}

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
      } catch (firstErr) {
        // BT device might still be switching — wait and retry
        console.warn("[voice] First mic attempt failed, retrying in 2s...", firstErr);
        await new Promise(r => setTimeout(r, 2000));
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
      }

      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      audioContextRef.current = audioCtx;
      conversationStreamRef.current = stream;

      setIsConversationMode(true);
      conversationActiveRef.current = true;
      // Conversation mode always enables TTS
      setIsTTSEnabled(true);

      // Continuous VAD loop — detect speech, record, transcribe, send, speak response
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      let recording = false;
      let recorder: MediaRecorder | null = null;
      let chunks: Blob[] = [];
      let silenceStart = 0;
      const SILENCE_THRESHOLD = 15;
      const SILENCE_DURATION = 1500; // 1.5s of silence = end of utterance

      const vadLoop = () => {
        if (!conversationActiveRef.current || !analyserRef.current) return;
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        const isSpeaking = avg > SILENCE_THRESHOLD;

        setHasVoiceActivity(isSpeaking);

        if (isSpeaking && !recording) {
          // Start recording
          recording = true;
          setIsRecording(true);
          chunks = [];
          recorder = new MediaRecorder(stream);
          recorder.ondataavailable = (e) => chunks.push(e.data);
          recorder.onstop = async () => {
            const blob = new Blob(chunks, { type: "audio/webm" });
            // Transcribe and send as message
            const formData = new FormData();
            formData.append("file", blob, "conversation.webm");
            try {
              const resp = await authFetch(`${API_URL}/api/voice/transcribe`, { method: "POST", body: formData });
              if (resp.ok) {
                const data = await resp.json();
                if (data.text && data.text.trim().length > 1) {
                  // Voice command: "Stop Friday" — kill all audio, stay listening
                  if (data.text.toLowerCase().includes("stop friday")) {
                    // Kill any playing TTS
                    if (currentAudioRef.current) {
                      currentAudioRef.current.pause();
                      currentAudioRef.current.src = "";
                      currentAudioRef.current = null;
                    }
                    // Flush the queue
                    audioQueueRef.current = [];
                    audioPlayingRef.current = false;
                    lastSpokenTextRef.current = "";
                    // Don't send "stop friday" as a message — just resume listening
                    return;
                  }
                  sendMessage(data.text);
                }
              }
            } catch (err) {
              console.error("Conversation transcription failed:", err);
            }
          };
          recorder.start();
          silenceStart = 0;
        } else if (!isSpeaking && recording) {
          if (!silenceStart) silenceStart = Date.now();
          if (Date.now() - silenceStart > SILENCE_DURATION) {
            // End of utterance
            recording = false;
            setIsRecording(false);
            recorder?.stop();
            recorder = null;
            silenceStart = 0;
          }
        } else if (isSpeaking && recording) {
          silenceStart = 0; // Reset silence timer
        }

        vadFrameRef.current = requestAnimationFrame(vadLoop);
      };

      vadLoop();
    } catch (err) {
      console.error("Microphone access denied:", err);
    }
  };

  const stopConversationMode = () => {
    // Hard kill — stop everything immediately
    conversationActiveRef.current = false;
    audioQueueRef.current = [];
    audioPlayingRef.current = false;
    lastSpokenTextRef.current = "";
    setIsConversationMode(false);
    setHasVoiceActivity(false);
    // Keep TTS enabled separately if user had it on

    // Kill VAD loop
    cancelAnimationFrame(vadFrameRef.current);

    // Kill any playing TTS audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.src = "";
      currentAudioRef.current = null;
    }

    // Kill mic stream
    conversationStreamRef.current?.getTracks().forEach(t => t.stop());
    conversationStreamRef.current = null;
    conversationRecorderRef.current = null;

    // Kill audio context
    analyserRef.current = null;
    audioContextRef.current?.close();
    audioContextRef.current = null;
  };

  /* ── Prompt Improver (evaluate → clarify → improve) ── */

  const evaluatePrompt = async () => {
    const text = input.trim();
    if (!text || isPolishing) return;

    setIsPolishing(true);
    try {
      // Build recent context for grounding
      const recentContext = messages
        .filter(m => m.role !== "system")
        .slice(-6)
        .map(m => `${m.role}: ${m.content.slice(0, 150)}`);

      const resp = await authFetch(`${API_URL}/api/chat/evaluate-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, context: recentContext }),
      });

      if (resp.ok) {
        const data = await resp.json();
        if (data.clear) {
          // Prompt is clear — send directly
          sendMessage();
        } else if (data.questions && data.questions.length > 0) {
          // Prompt is vague — show clarifying questions
          setImproverState({
            show: true,
            originalPrompt: text,
            questions: data.questions,
            contextSummary: data.context_summary,
            isImproving: false,
          });
        } else {
          // Fallback — send as-is
          sendMessage();
        }
      } else {
        // API error — fall back to sending as-is
        sendMessage();
      }
    } catch (err) {
      console.error("Prompt evaluation failed:", err);
      sendMessage();
    } finally {
      setIsPolishing(false);
    }
  };

  const handleImproverSubmit = async (answers: string[]) => {
    setImproverState(prev => ({ ...prev, isImproving: true }));
    try {
      const resp = await authFetch(`${API_URL}/api/chat/improve-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original: improverState.originalPrompt,
          questions: improverState.questions,
          answers,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        if (data.improved) {
          setInput(data.improved);
          setImproverState({ show: false, originalPrompt: "", questions: [], isImproving: false });
          // Auto-send the improved prompt
          setTimeout(() => sendMessage(data.improved), 100);
        }
      }
    } catch (err) {
      console.error("Prompt improvement failed:", err);
    } finally {
      setImproverState(prev => ({ ...prev, isImproving: false }));
    }
  };

  const handleImproverSkip = () => {
    setImproverState({ show: false, originalPrompt: "", questions: [], isImproving: false });
    sendMessage();
  };

  const handleImproverCancel = () => {
    setImproverState({ show: false, originalPrompt: "", questions: [], isImproving: false });
  };

  // Legacy polish (simple cleanup, no questions)
  const polishPrompt = async () => {
    const text = input.trim();
    if (!text || isPolishing) return;

    setIsPolishing(true);
    try {
      const resp = await authFetch(`${API_URL}/api/chat/polish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.polished) {
          setInput(data.polished);
        }
      }
    } catch (err) {
      console.error("Prompt polish failed:", err);
    } finally {
      setIsPolishing(false);
    }
  };

  const formatDuration = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  /* ── Render ─────────────────────────────────────────── */

  return (
    <div className="flex h-full overflow-hidden" style={{ maxHeight: '100%' }}>
    <div className={`flex flex-col ${showArtifacts ? "w-1/2" : "w-full"} transition-all duration-300 min-h-0`} style={{ height: '100%', maxHeight: '100%' }}>
      {/* Alert Banners */}
      {rateLimitAlert && (
        <div className="mx-4 mt-2 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex items-center gap-3 flex-shrink-0">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-red-400">API Rate Limit</p>
            <p className="text-xs text-red-400/70 truncate">{rateLimitAlert}</p>
          </div>
          <button onClick={() => setRateLimitAlert(null)} className="text-red-400/50 hover:text-red-400 transition flex-shrink-0">
            <X size={16} />
          </button>
        </div>
      )}
      {compactionAlert && (
        <div className="mx-4 mt-2 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3 flex items-center gap-3 flex-shrink-0">
          {compactionAlert === "start" ? (
            <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse flex-shrink-0" />
          ) : (
            <div className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
          )}
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-400">
              {compactionAlert === "start" ? "Compressing Context..." : "Context Compressed"}
            </p>
            <p className="text-xs text-amber-400/70">
              {compactionAlert === "start"
                ? "Summarizing older messages to free up space. This may take a moment..."
                : "Older messages were summarized to free up space. Recent context is preserved."}
            </p>
          </div>
          {compactionAlert === "end" && (
            <button onClick={() => setCompactionAlert(false)} className="text-amber-400/50 hover:text-amber-400 transition flex-shrink-0">
              <X size={16} />
            </button>
          )}
        </div>
      )}

      {/* Messages area wrapper (relative for orb overlay) */}
      <div className="flex-1 min-h-0 relative">
      <div ref={messagesContainerRef} className="absolute inset-0 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages.length === 0 && !streamText && (
            <div className="flex flex-col items-center justify-center pt-[20vh] text-warroom-muted">
              <div className="w-16 h-16 rounded-2xl bg-warroom-accent/10 flex items-center justify-center mb-4">
                <Bot size={32} className="text-warroom-accent" />
              </div>
              <p className="text-xl font-medium text-warroom-text mb-1">WAR ROOM</p>
              <p className="text-sm">How can I help you today?</p>
            </div>
          )}

          {messages.filter(msg => msg.role === "system" || msg.content.trim().length > 0).map((msg) => (
            msg.role === "system" ? (
              <div key={msg.id} className="flex justify-center">
                <div className="bg-warroom-surface/50 border border-warroom-border/50 rounded-full px-4 py-1.5 text-xs text-warroom-muted flex items-center gap-2">
                  <span>{msg.content}</span>
                </div>
              </div>
            ) : (
            <div key={msg.id} className={`flex gap-4 ${msg.role === "user" ? "justify-end" : ""}`}>
              {msg.role !== "user" && (
                <div className="w-8 h-8 rounded-full bg-warroom-accent/10 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot size={16} className="text-warroom-accent" />
                </div>
              )}
              <div className={`max-w-[80%] min-w-0 ${msg.role === "user" ? "order-first" : ""}`}>
                {msg.role === "user" ? (
                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl px-4 py-2.5 text-sm overflow-hidden">
                    {msg.images && msg.images.length > 0 && (
                      <div className="flex gap-2 mb-2 flex-wrap">
                        {msg.images.map(img => (
                          <img key={img.id} src={img.dataUrl} alt={img.name} className="max-h-48 rounded-lg border border-warroom-border/50 cursor-pointer hover:opacity-90 transition" onClick={() => window.open(img.dataUrl, "_blank")} />
                        ))}
                      </div>
                    )}
                    <p className="whitespace-pre-wrap break-words" style={{ overflowWrap: 'anywhere' }}>{msg.content !== "(image)" ? msg.content : ""}</p>
                  </div>
                ) : (
                  <div className="overflow-hidden">
                    {/* Tool call history (collapsed) */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <details className="mb-2 border border-zinc-700/30 rounded-lg bg-zinc-900/40">
                        <summary className="flex items-center gap-2 px-3 py-1.5 text-xs text-zinc-400 cursor-pointer hover:text-zinc-300 transition select-none">
                          <Wrench size={12} />
                          <span>{msg.toolCalls.length} tool{msg.toolCalls.length > 1 ? "s" : ""} used</span>
                        </summary>
                        <div className="px-3 pb-2 space-y-1">
                          {msg.toolCalls.map((tool) => (
                            <div key={tool.id} className="flex items-center gap-2 text-xs">
                              {tool.status === "error" ? (
                                <AlertCircle size={10} className="text-red-400" />
                              ) : (
                                <CheckCircle2 size={10} className="text-green-400/60" />
                              )}
                              <span className="text-zinc-400 font-mono">{tool.name}</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                    {splitContentWithCodeBlocks(msg.content).map((segment, idx) => (
                      segment.type === "url" ? (
                        <UrlBox key={idx} url={segment.url} />
                      ) : segment.type === "text" ? (
                        <div key={idx} className={MARKDOWN_PROSE}>
                          <SafeMarkdown>{segment.content}</SafeMarkdown>
                        </div>
                      ) : (
                        <div key={idx} className="my-3">
                          <div className="bg-black/40 rounded-xl p-4 overflow-x-auto max-w-full">
                            <pre className="text-sm text-slate-300 font-mono whitespace-pre overflow-x-auto"><code>{segment.code}</code></pre>
                          </div>
                          <div className="flex items-center gap-2 mt-1.5">
                            <CopyButton text={segment.code || ""} label="Copy" />
                            <button
                              onClick={() => openArtifact({
                                id: crypto.randomUUID(),
                                type: "code",
                                title: segment.title || "snippet",
                                content: segment.code || "",
                                language: segment.language || "text",
                                timestamp: new Date(),
                              })}
                              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-warroom-surface border border-warroom-border/50 text-xs text-warroom-muted hover:text-warroom-accent transition"
                              title="Open in side panel"
                            >
                              <PanelRightOpen size={13} />
                              <span>Open</span>
                            </button>
                            <span className="text-[10px] text-warroom-muted/50 ml-auto">
                              {getLanguageLabel(segment.language)} · {(segment.code || "").split("\n").length} lines
                            </span>
                          </div>
                        </div>
                      )
                    ))}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-warroom-border flex items-center justify-center flex-shrink-0 mt-1">
                  <User size={16} className="text-warroom-text" />
                </div>
              )}
            </div>
            )
          ))}

          {/* Live progress: thinking + tool calls */}
          {(thinkingText || activeTools.length > 0 || streamText) && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-warroom-accent/10 flex items-center justify-center flex-shrink-0 mt-1">
                <Bot size={16} className="text-warroom-accent" />
              </div>
              <div className="max-w-[80%] min-w-0 space-y-2 w-full">
                {/* Partial content from before tool calls — keeps text visible during tool execution */}
                {!streamText && partialContent && activeTools.length > 0 && (
                  <div className={`${MARKDOWN_PROSE} opacity-70`}>
                    <SafeMarkdown>{partialContent}</SafeMarkdown>
                  </div>
                )}

                {/* Thinking block */}
                {thinkingText && (
                  <div className="border border-zinc-700/50 rounded-lg overflow-hidden bg-zinc-900/60">
                    <button
                      onClick={() => setThinkingCollapsed(!thinkingCollapsed)}
                      className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-amber-400/80 hover:text-amber-300 transition"
                    >
                      <Brain size={12} className="animate-pulse" />
                      <span className="font-medium">Thinking...</span>
                      <ChevronRight size={12} className={`ml-auto transition-transform ${thinkingCollapsed ? "" : "rotate-90"}`} />
                    </button>
                    {!thinkingCollapsed && (
                      <div className="px-3 pb-2 text-xs text-zinc-400 max-h-32 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                        {thinkingText.length > 500 ? thinkingText.slice(-500) + "..." : thinkingText}
                      </div>
                    )}
                  </div>
                )}

                {/* Tool calls */}
                {activeTools.length > 0 && (
                  <div className="space-y-1">
                    {activeTools.map((tool) => (
                      <div key={tool.id} className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-zinc-800/80 border border-zinc-700/40 text-xs">
                        {tool.status === "running" ? (
                          <Loader2 size={12} className="text-blue-400 animate-spin flex-shrink-0" />
                        ) : tool.status === "error" ? (
                          <AlertCircle size={12} className="text-red-400 flex-shrink-0" />
                        ) : (
                          <CheckCircle2 size={12} className="text-green-400 flex-shrink-0" />
                        )}
                        <span className="text-zinc-300 font-mono">{tool.name}</span>
                        {tool.input && (
                          <span className="text-zinc-500 truncate max-w-[300px]">{tool.input}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Streaming text */}
                {streamText && (
                  <div className={MARKDOWN_PROSE}>
                    <SafeMarkdown>{streamText}</SafeMarkdown>
                    <span className="inline-block w-2 h-4 bg-warroom-accent/60 animate-pulse ml-0.5" />
                  </div>
                )}

                {/* Loading dots when no text yet but tools are active */}
                {!streamText && !partialContent && !thinkingText && activeTools.length > 0 && activeTools.some(t => t.status === "running") && (
                  <div className="flex items-center gap-1 py-1">
                    <span className="w-1.5 h-1.5 bg-warroom-muted rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-warroom-muted rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-warroom-muted rounded-full animate-bounce [animation-delay:300ms]" />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Task completion review card */}
          {taskReview?.show && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center flex-shrink-0">
                <CheckCircle2 size={16} className="text-green-400" />
              </div>
              <div className="bg-green-500/5 border border-green-500/20 rounded-xl px-4 py-3 flex-1">
                <p className="text-xs font-semibold text-green-400 mb-1.5">Task Complete</p>
                <div className="space-y-1">
                  {taskReview.tools.map((tool, i) => (
                    <div key={tool.id || i} className="flex items-center gap-2 text-xs text-warroom-text/70">
                      <CheckCircle2 size={10} className="text-green-400/60 shrink-0" />
                      <span className="truncate">{tool.name}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-2 flex items-center gap-1.5">
                  <div className="w-full bg-green-500/10 rounded-full h-1">
                    <div className="bg-green-400 h-1 rounded-full animate-shrink" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Response skeleton (no blocking dots) */}
          {isLoading && !streamText && activeTools.length === 0 && !thinkingText && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-warroom-accent/10 flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="text-warroom-accent" />
              </div>
              <div className="flex-1 min-w-0 space-y-2">
                <div className="h-4 bg-warroom-border rounded w-3/4 animate-pulse" />
                <div className="h-4 bg-warroom-border rounded w-1/2 animate-pulse" />
                <div className="text-xs text-warroom-muted">Preparing response...</div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Voice orb overlay — covers messages area during conversation mode */}
      <VoiceOrb
        isActive={isConversationMode}
        isSpeaking={isTTSPlaying}
        isListening={isRecording}
        isProcessing={isLoading || isGenerating}
        spokenText={spokenText}
        ttsDurationMs={ttsDurationMs}
      />

      {/* Scroll to bottom */}
      <div className={`absolute bottom-4 left-1/2 -translate-x-1/2 z-10 transition-all duration-200 ${showScrollButton ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 translate-y-2 pointer-events-none"}`}>
        <button
          onClick={() => scrollToBottom(true)}
          className="bg-warroom-surface/90 border border-warroom-border rounded-full p-2 shadow-lg hover:bg-warroom-accent/20 transition-colors backdrop-blur-sm"
          title="Scroll to bottom"
        >
          <ArrowDown size={16} className="text-warroom-text" />
        </button>
      </div>
      </div>

      {/* Voice recording overlay (STT) */}
      {isRecording && (
        <div className="mx-auto max-w-3xl w-full px-4 mb-2">
          <div className="bg-warroom-surface border border-warroom-accent/30 rounded-2xl p-4 flex items-center gap-4">
            <div className={`w-3 h-3 rounded-full ${hasVoiceActivity ? "bg-green-500" : "bg-red-500"} ${hasVoiceActivity ? "animate-pulse" : ""}`} />
            <span className="text-sm font-mono text-warroom-text">{formatDuration(recordingDuration)}</span>
            <div className="flex-1 flex items-center gap-0.5 h-8">
              {Array.from({ length: 40 }).map((_, i) => (
                <div
                  key={i}
                  className="flex-1 bg-warroom-accent/40 rounded-full transition-all duration-75"
                  style={{
                    height: hasVoiceActivity ? `${Math.random() * 100}%` : "4px",
                    minHeight: "4px",
                  }}
                />
              ))}
            </div>
            <button onClick={cancelRecording} className="text-warroom-muted hover:text-warroom-danger transition p-1">
              <X size={18} />
            </button>
            <button onClick={stopRecording} className="bg-warroom-accent rounded-full p-2 hover:bg-warroom-accent/80 transition">
              <StopCircle size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="pb-4 pt-2 px-4 flex-shrink-0">
        <div className="max-w-4xl mx-auto">
          <div
            className={`bg-warroom-surface border rounded-3xl shadow-lg transition-colors ${wsConnected ? "border-warroom-border" : "border-warroom-danger/30"}`}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            {/* Image preview strip */}
            {pendingImages.length > 0 && (
              <div className="flex gap-2 px-4 pt-3 pb-1 overflow-x-auto">
                {pendingImages.map(img => (
                  <div key={img.id} className="relative group flex-shrink-0">
                    <img src={img.dataUrl} alt={img.name} className="h-20 w-20 object-cover rounded-xl border border-warroom-border" />
                    <button
                      onClick={() => removeImage(img.id)}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-warroom-danger rounded-full flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition"
                    >
                      <X size={12} />
                    </button>
                    <span className="absolute bottom-1 left-1 right-1 text-[8px] text-white bg-black/60 rounded px-1 truncate">{img.name}</span>
                  </div>
                ))}
              </div>
            )}
            <div className={`px-4 ${pendingImages.length > 0 ? "pt-1" : "pt-3"}`}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                disabled={isGenerating}
                placeholder={isGenerating ? "Generating response..." : pendingImages.length > 0 ? "Add a message about these images..." : "Message Friday..."}
                rows={1}
                className={`w-full bg-transparent text-sm placeholder-warroom-muted resize-none outline-none min-h-[24px] max-h-[200px] leading-6 scrollbar-thin scrollbar-thumb-warroom-border scrollbar-track-transparent ${isGenerating ? "text-warroom-muted/50 cursor-not-allowed" : "text-warroom-text"}`}
                style={{ overflow: input.split("\n").length > 8 || input.length > 400 ? "auto" : "hidden" }}
                onInput={resizeTextarea}
              />
            </div>
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => { if (e.target.files) addImagesFromFiles(e.target.files); e.target.value = ""; }}
            />

            <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-1.5 rounded-full hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition"
                  title="Attach image"
                >
                  <Plus size={18} />
                </button>
                <button
                  onClick={evaluatePrompt}
                  onDoubleClick={(e) => { e.stopPropagation(); polishPrompt(); }}
                  disabled={!input.trim() || isPolishing}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isPolishing ? "text-warroom-accent animate-spin" : "text-warroom-muted hover:text-warroom-text"} disabled:opacity-30`}
                  title="Evaluate & improve prompt (double-click to just polish)"
                >
                  <Sparkles size={18} />
                </button>
                <button
                  onClick={toggleRecording}
                  disabled={isConversationMode}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isRecording ? "text-red-400 bg-red-500/10" : "text-warroom-muted hover:text-warroom-text"} disabled:opacity-30`}
                  title="Speech to text"
                >
                  {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
                <button
                  onClick={() => setIsTTSEnabled(!isTTSEnabled)}
                  disabled={isConversationMode}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isTTSEnabled ? "text-warroom-accent bg-warroom-accent/15" : "text-warroom-muted hover:text-warroom-text"} disabled:opacity-30`}
                  title="Text to speech"
                >
                  <Volume2 size={18} />
                </button>
                <button
                  onClick={toggleConversationMode}
                  disabled={isRecording}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isConversationMode ? "text-warroom-accent bg-warroom-accent/15" : "text-warroom-muted hover:text-warroom-text"} disabled:opacity-30`}
                  title="Voice conversation (TTS + STT)"
                >
                  <EnhancedWaveformIcon 
                    size={18} 
                    animated={isConversationMode && hasVoiceActivity}
                    isActive={isConversationMode}
                    hasActivity={hasVoiceActivity}
                  />
                </button>
                <div className="w-px h-4 bg-warroom-border mx-1" />
                <UsageIndicator wsConnected={wsConnected} />
              </div>

              <div className="flex items-center gap-1.5">
                {isConversationMode ? (
                  <button onClick={stopConversationMode} className="p-2 rounded-full bg-warroom-danger/20 text-warroom-danger hover:bg-warroom-danger/30 transition" title="End conversation">
                    <StopCircle size={18} />
                  </button>
                ) : isGenerating ? (
                  <button onClick={abortResponse} className="p-2 rounded-full bg-warroom-danger/20 text-warroom-danger hover:bg-warroom-danger/30 transition" title="Stop generating">
                    <StopCircle size={18} />
                  </button>
                ) : (
                  <button
                    onClick={() => sendMessage()}
                    disabled={!input.trim() || !wsConnected}
                    className="p-2 rounded-full bg-warroom-accent text-white hover:bg-warroom-accent/80 disabled:opacity-20 disabled:hover:bg-warroom-accent transition"
                    title="Send message"
                  >
                    <Send size={18} />
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between mt-2 px-1">
            <p className="text-[10px] text-warroom-muted/50">
              WAR ROOM — stuffnthings
            </p>
            {tokenUsage && (
              <p className="text-[10px] text-warroom-muted/50 font-mono">
                {tokenUsage.totalTokens >= 1000
                  ? `${Math.round(tokenUsage.totalTokens / 1000)}K`
                  : tokenUsage.totalTokens}
                {" / "}
                {Math.round(tokenUsage.contextWindow / 1000)}K
                {" · "}
                <span className={
                  tokenUsage.percentage > 80 ? "text-red-400" :
                  tokenUsage.percentage > 60 ? "text-yellow-400" :
                  "text-warroom-muted/50"
                }>
                  {tokenUsage.percentage}%
                </span>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>

    {/* Artifact Panel */}
    {showArtifacts && artifacts.length > 0 && (
      <div className="w-1/2 h-full">
        <ArtifactPanel
          artifacts={artifacts}
          activeIndex={activeArtifactIndex}
          onClose={() => setShowArtifacts(false)}
          onSelect={setActiveArtifactIndex}
          onRemove={removeArtifact}
        />
      </div>
    )}

    {/* Prompt Improver Modal */}
    {improverState.show && (
      <PromptImproverModal
        originalPrompt={improverState.originalPrompt}
        questions={improverState.questions}
        contextSummary={improverState.contextSummary}
        onSubmit={handleImproverSubmit}
        onSkip={handleImproverSkip}
        onCancel={handleImproverCancel}
        isImproving={improverState.isImproving}
      />
    )}
    </div>
  );
}
