"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Bot, User, Loader2, Mic, MicOff,
  Plus, Sparkles, X, StopCircle, ArrowDown,
  PanelRightOpen, Copy, Check,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import ArtifactPanel, { Artifact } from "./ArtifactPanel";

/* ── Types ─────────────────────────────────────────────── */

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  thinking?: string;
}

interface GatewayRes {
  type: "res";
  id: string;
  ok: boolean;
  payload?: any;
  error?: { code: string; message: string };
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

/* ── Waveform Icon ─────────────────────────────────────── */

function WaveformIcon({ size = 18, animated = false }: { size?: number; animated?: boolean }) {
  const bars = [
    { x: 3, h: 8 },
    { x: 7, h: 14 },
    { x: 11, h: 10 },
    { x: 15, h: 16 },
    { x: 19, h: 6 },
  ];
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      {bars.map((bar, i) => {
        const y1 = (24 - bar.h) / 2;
        const y2 = y1 + bar.h;
        return animated ? (
          <line key={i} x1={bar.x} x2={bar.x} y1={12} y2={12}>
            <animate attributeName="y1" values={`12;${y1};12`} dur={`${0.4 + i * 0.1}s`} repeatCount="indefinite" />
            <animate attributeName="y2" values={`12;${y2};12`} dur={`${0.4 + i * 0.1}s`} repeatCount="indefinite" />
          </line>
        ) : (
          <line key={i} x1={bar.x} x2={bar.x} y1={y1} y2={y2} />
        );
      })}
    </svg>
  );
}

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

function CodeCopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-warroom-surface border border-warroom-border/50 text-xs text-warroom-muted hover:text-warroom-text transition"
      title="Copy code"
    >
      {copied ? <Check size={13} className="text-green-400" /> : <Copy size={13} />}
      <span>{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [streamText, setStreamText] = useState<string | null>(null);

  // Voice states
  const [isRecording, setIsRecording] = useState(false);
  const [isConversationMode, setIsConversationMode] = useState(false);
  const [hasVoiceActivity, setHasVoiceActivity] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);

  // Magic prompt states
  const [isPolishing, setIsPolishing] = useState(false);

  // Token usage
  const [tokenUsage, setTokenUsage] = useState<{ totalTokens: number; contextWindow: number; percentage: number; compactionCount: number } | null>(null);
  const lastCompactionRef = useRef<number>(-1);

  // Artifact panel
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [activeArtifactIndex, setActiveArtifactIndex] = useState(0);
  const [showArtifacts, setShowArtifacts] = useState(false);

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
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioQueueRef = useRef<(() => Promise<void>)[]>([]);
  const audioPlayingRef = useRef<boolean>(false);
  const lastSpokenTextRef = useRef<string>("");
  const lastSpokenTimeRef = useRef<number>(0);

  // Keep ref in sync with state
  useEffect(() => { streamTextRef.current = streamText; }, [streamText]);

  // Fetch token usage
  const fetchTokenUsage = useCallback(async () => {
    try {
      const resp = await fetch(`${API_URL}/api/chat/session-status`);
      if (resp.ok) {
        const data = await resp.json();
        setTokenUsage(data);
        // Detect compaction
        if (lastCompactionRef.current === -1) {
          lastCompactionRef.current = data.compactionCount;
        } else if (data.compactionCount > lastCompactionRef.current) {
          lastCompactionRef.current = data.compactionCount;
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

  // Split message content into text segments and code blocks with metadata
  type ContentSegment = { type: "text"; content: string } | { type: "code"; code: string; language: string; title: string; content?: never };

  const splitContentWithCodeBlocks = useCallback((content: string): ContentSegment[] => {
    const segments: ContentSegment[] = [];
    const regex = /```(\w+)?\n([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(content)) !== null) {
      // Text before this code block
      const textBefore = content.slice(lastIndex, match.index).trim();
      if (textBefore) {
        segments.push({ type: "text", content: textBefore });
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

    // Remaining text after last code block
    const remaining = content.slice(lastIndex).trim();
    if (remaining) {
      segments.push({ type: "text", content: remaining });
    }

    // If no code blocks found, return the whole thing as text
    if (segments.length === 0) {
      segments.push({ type: "text", content });
    }

    return segments;
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, streamText, scrollToBottom]);

  // Scroll detection
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      setShowScrollButton(scrollHeight - scrollTop - clientHeight > 100);
    };
    container.addEventListener("scroll", handleScroll);
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
        if (data.type === "error") { setWsConnected(false); return; }
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
              }));
            setMessages(history);
          }
          if (res.ok && res.payload?.runId) setIsLoading(true);
          if (!res.ok) {
            setIsLoading(false);
            setMessages(prev => [...prev, {
              id: crypto.randomUUID(),
              role: "system",
              content: `Error: ${res.error?.message || "request failed"}`,
              timestamp: new Date(),
            }]);
          }
          return;
        }

        if (data.type === "event" && data.event === "chat") {
          const p = data.payload || {};
          const state = p.state;
          const message = p.message;


          if (state === "delta") {
            const text = extractText(message);
            if (text) {
              setStreamText(text);
              streamTextRef.current = text;
              setIsLoading(false);
            }
          } else if (state === "final") {
            const text = extractText(message);
            if (text) {
              setMessages(prev => [...prev, {
                id: crypto.randomUUID(),
                role: "assistant",
                content: text,
                timestamp: new Date(message?.timestamp || Date.now()),
              }]);
            }
            setStreamText(null);
            streamTextRef.current = null;
            setIsLoading(false);

            // If in conversation mode, speak the response
            if (text && conversationActiveRef.current) {
              speakText(text);
            }
          } else if (state === "aborted") {
            const partial = streamTextRef.current;
            if (partial) {
              setMessages(prev => [...prev, {
                id: crypto.randomUUID(),
                role: "assistant",
                content: partial + "\n\n*[aborted]*",
                timestamp: new Date(),
              }]);
            }
            setStreamText(null);
            streamTextRef.current = null;
            setIsLoading(false);
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

  /* ── Send ───────────────────────────────────────────── */

  const sendMessage = (overrideText?: string) => {
    const text = (overrideText || input).trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    }]);
    if (!overrideText) setInput("");
    setIsLoading(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.overflow = "hidden";
    }

    wsRef.current.send(JSON.stringify({ action: "send", message: text }));
  };

  const abortResponse = () => {
    wsRef.current?.send(JSON.stringify({ action: "abort" }));
    setIsLoading(false);
    setStreamText(null);
    streamTextRef.current = null;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
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
    // Play next in queue if any
    if (conversationActiveRef.current && audioQueueRef.current.length > 0) {
      processAudioQueue();
    }
  };

  const speakText = async (text: string) => {
    if (!conversationActiveRef.current) return;
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

    const playTask = async () => {
      if (!conversationActiveRef.current) return;
      try {
        const resp = await fetch(`${API_URL}/api/voice/tts?text=${encodeURIComponent(text.slice(0, 500))}`, {
          method: "POST",
        });
        if (resp.ok && conversationActiveRef.current) {
          const blob = await resp.blob();
          const audio = new Audio(URL.createObjectURL(blob));
          currentAudioRef.current = audio;
          await new Promise<void>((resolve) => {
            audio.onended = () => { currentAudioRef.current = null; resolve(); };
            audio.onerror = () => { currentAudioRef.current = null; resolve(); };
            audio.play().catch(() => resolve());
          });
        }
      } catch (err) {
        console.error("TTS failed:", err);
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
      const resp = await fetch(`${API_URL}/api/voice/transcribe`, { method: "POST", body: formData });
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
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });

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
          chunks = [];
          recorder = new MediaRecorder(stream);
          recorder.ondataavailable = (e) => chunks.push(e.data);
          recorder.onstop = async () => {
            const blob = new Blob(chunks, { type: "audio/webm" });
            // Transcribe and send as message
            const formData = new FormData();
            formData.append("file", blob, "conversation.webm");
            try {
              const resp = await fetch(`${API_URL}/api/voice/transcribe`, { method: "POST", body: formData });
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

  /* ── Magic Prompt Polish ────────────────────────────── */

  const polishPrompt = async () => {
    const text = input.trim();
    if (!text || isPolishing) return;

    setIsPolishing(true);
    try {
      const resp = await fetch(`${API_URL}/api/chat/polish`, {
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
    <div className="flex h-full">
    <div className={`flex flex-col ${showArtifacts ? "w-1/2" : "w-full"} transition-all duration-300 h-full`}>
      {/* Messages area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto">
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

          {messages.map((msg) => (
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
              <div className={`max-w-[80%] ${msg.role === "user" ? "order-first" : ""}`}>
                {msg.role === "user" ? (
                  <div className="bg-warroom-surface border border-warroom-border rounded-2xl px-4 py-2.5 text-sm">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                ) : (
                  <div>
                    {splitContentWithCodeBlocks(msg.content).map((segment, idx) => (
                      segment.type === "text" ? (
                        <div key={idx} className="prose prose-invert prose-sm max-w-none overflow-hidden [&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>pre]:bg-black/40 [&>pre]:rounded-xl [&>pre]:p-4 [&>pre]:my-3 [&>pre]:overflow-x-auto [&>pre]:max-w-full [&>h1]:text-lg [&>h2]:text-base [&>h3]:text-sm [&>code]:bg-black/30 [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded-md [&>code]:text-warroom-accent [&>pre>code]:whitespace-pre [&>pre>code]:break-normal">
                          <ReactMarkdown>{segment.content}</ReactMarkdown>
                        </div>
                      ) : (
                        <div key={idx} className="my-3">
                          <div className="bg-black/40 rounded-xl p-4 overflow-x-auto max-w-full">
                            <pre className="text-sm text-slate-300 font-mono whitespace-pre overflow-x-auto"><code>{segment.code}</code></pre>
                          </div>
                          <div className="flex items-center gap-2 mt-1.5">
                            <CodeCopyButton text={segment.code || ""} />
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

          {/* Streaming response */}
          {streamText && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-warroom-accent/10 flex items-center justify-center flex-shrink-0 mt-1">
                <Bot size={16} className="text-warroom-accent" />
              </div>
              <div className="max-w-[80%] prose prose-invert prose-sm max-w-none [&>p]:mb-3 [&>code]:bg-black/30 [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded-md [&>code]:text-warroom-accent">
                <ReactMarkdown>{streamText}</ReactMarkdown>
                <span className="inline-block w-2 h-4 bg-warroom-accent/60 animate-pulse ml-0.5" />
              </div>
            </div>
          )}

          {/* Loading dots */}
          {isLoading && !streamText && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-warroom-accent/10 flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="text-warroom-accent" />
              </div>
              <div className="flex items-center gap-1 py-2">
                <span className="w-2 h-2 bg-warroom-muted rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-warroom-muted rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-warroom-muted rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Scroll to bottom */}
      {showScrollButton && (
        <div className="absolute bottom-32 left-1/2 -translate-x-1/2 z-10">
          <button onClick={scrollToBottom} className="bg-warroom-surface border border-warroom-border rounded-full p-2 shadow-lg hover:bg-warroom-border transition">
            <ArrowDown size={16} />
          </button>
        </div>
      )}

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

      {/* Conversation mode banner */}
      {isConversationMode && !isRecording && (
        <div className="mx-auto max-w-3xl w-full px-4 mb-2">
          <div className="bg-warroom-surface border border-green-500/30 rounded-2xl p-4 flex items-center gap-4">
            <div className={`w-3 h-3 rounded-full ${hasVoiceActivity ? "bg-green-500 animate-pulse" : "bg-green-500/40"}`} />
            <span className="text-sm text-warroom-text">
              {hasVoiceActivity ? "Listening..." : "Conversation mode — speak to chat"}
            </span>
            <div className="flex-1 flex items-center gap-0.5 h-6">
              {Array.from({ length: 30 }).map((_, i) => (
                <div
                  key={i}
                  className="flex-1 bg-green-500/40 rounded-full transition-all duration-75"
                  style={{
                    height: hasVoiceActivity ? `${Math.random() * 100}%` : "4px",
                    minHeight: "4px",
                  }}
                />
              ))}
            </div>
            <button onClick={stopConversationMode} className="bg-red-500/20 text-red-400 rounded-full px-3 py-1.5 text-sm hover:bg-red-500/30 transition flex items-center gap-1.5">
              <StopCircle size={14} />
              End
            </button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="pb-4 pt-2 px-4">
        <div className="max-w-3xl mx-auto">
          <div className={`bg-warroom-surface border rounded-3xl shadow-lg transition-colors ${wsConnected ? "border-warroom-border" : "border-warroom-danger/30"}`}>
            <div className="px-4 pt-3">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message Friday..."
                rows={1}
                className="w-full bg-transparent text-sm text-warroom-text placeholder-warroom-muted resize-none outline-none min-h-[24px] max-h-[200px] leading-6 scrollbar-thin scrollbar-thumb-warroom-border scrollbar-track-transparent"
                style={{ overflow: input.split("\n").length > 8 || input.length > 400 ? "auto" : "hidden" }}
                onInput={resizeTextarea}
              />
            </div>

            <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded-full hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition" title="Attach file">
                  <Plus size={18} />
                </button>
                <button
                  onClick={polishPrompt}
                  disabled={!input.trim() || isPolishing}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isPolishing ? "text-warroom-accent animate-spin" : "text-warroom-muted hover:text-warroom-text"} disabled:opacity-30`}
                  title="Polish prompt with AI"
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
                  onClick={toggleConversationMode}
                  disabled={isRecording}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isConversationMode ? "text-green-400 bg-green-500/10" : "text-warroom-muted hover:text-warroom-text"} disabled:opacity-30`}
                  title="Voice conversation"
                >
                  <WaveformIcon size={18} animated={isConversationMode && hasVoiceActivity} />
                </button>
                <div className="w-px h-4 bg-warroom-border mx-1" />
                <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-warroom-success" : "bg-warroom-danger animate-pulse"}`} />
                {!wsConnected && <span className="text-[10px] text-warroom-danger ml-1">disconnected</span>}
              </div>

              <div className="flex items-center gap-1.5">
                {(isLoading || streamText) ? (
                  <button onClick={abortResponse} className="p-2 rounded-full bg-warroom-danger/20 text-warroom-danger hover:bg-warroom-danger/30 transition">
                    <StopCircle size={18} />
                  </button>
                ) : (
                  <button
                    onClick={() => sendMessage()}
                    disabled={!input.trim() || !wsConnected}
                    className="p-2 rounded-full bg-warroom-accent text-white hover:bg-warroom-accent/80 disabled:opacity-20 disabled:hover:bg-warroom-accent transition"
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
    </div>
  );
}
