"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Bot, User, Loader2, Mic, MicOff, Phone, PhoneOff,
  Plus, Sparkles, X, StopCircle, ArrowDown,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

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

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [streamText, setStreamText] = useState<string | null>(null);

  // Voice states
  const [isRecording, setIsRecording] = useState(false);
  const [isCallMode, setIsCallMode] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);

  // UI states
  const [showScrollButton, setShowScrollButton] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const streamTextRef = useRef<string | null>(null);

  // Keep ref in sync with state
  useEffect(() => { streamTextRef.current = streamText; }, [streamText]);

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

  /* ── WebSocket ─────────────────────────────────────── */

  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;
    let destroyed = false;

    const connectWs = () => {
      if (destroyed) return;
      const wsUrl = `${API_URL.replace("http", "ws")}/api/chat/ws`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        // Wait for relay "connected" message
      };

      ws.onmessage = (event) => {
        let data: any;
        try { data = JSON.parse(event.data); } catch { return; }

        // Relay status messages
        if (data.type === "connected") { setWsConnected(true); return; }
        if (data.type === "status") return; // reconnecting notices
        if (data.type === "pong") return;
        if (data.type === "error") { setWsConnected(false); return; }
        if (data.type === "session_changed") {
          setMessages([]);
          setStreamText(null);
          streamTextRef.current = null;
          return;
        }

        // Gateway response frames
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

          if (res.ok && res.payload?.runId) {
            setIsLoading(true);
          }

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

        // Chat events
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

        // Skip other events
        if (data.type === "event") return;
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (!destroyed) {
          reconnectTimer = setTimeout(connectWs, 3000);
        }
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
  }, []); // No dependencies — stable connection

  /* ── Send ───────────────────────────────────────────── */

  const sendMessage = () => {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    }]);
    setInput("");
    setIsLoading(true);

    if (textareaRef.current) textareaRef.current.style.height = "auto";

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

  /* ── Voice ──────────────────────────────────────────── */

  const toggleRecording = async () => {
    if (isRecording) stopRecording();
    else startRecording();
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
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
    }
    setIsRecording(false);
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
  };

  const transcribeAudio = async (blob: Blob) => {
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    try {
      const resp = await fetch(`${API_URL}/api/voice/transcribe`, { method: "POST", body: formData });
      if (resp.ok) {
        const data = await resp.json();
        setInput(prev => prev + (prev ? " " : "") + data.text);
        textareaRef.current?.focus();
      }
    } catch {
      console.error("Transcription failed");
    }
  };

  const formatDuration = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  /* ── Render ─────────────────────────────────────────── */

  return (
    <div className="flex flex-col h-full">
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
                  <div className="prose prose-invert prose-sm max-w-none [&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>pre]:bg-black/40 [&>pre]:rounded-xl [&>pre]:p-4 [&>pre]:my-3 [&>h1]:text-lg [&>h2]:text-base [&>h3]:text-sm [&>code]:bg-black/30 [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded-md [&>code]:text-warroom-accent">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-warroom-border flex items-center justify-center flex-shrink-0 mt-1">
                  <User size={16} className="text-warroom-text" />
                </div>
              )}
            </div>
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

      {/* Voice recording overlay */}
      {isRecording && (
        <div className="mx-auto max-w-3xl w-full px-4 mb-2">
          <div className="bg-warroom-surface border border-warroom-accent/30 rounded-2xl p-4 flex items-center gap-4">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
            <span className="text-sm font-mono text-warroom-text">{formatDuration(recordingDuration)}</span>
            <div className="flex-1 flex items-center gap-0.5 h-8">
              {Array.from({ length: 40 }).map((_, i) => (
                <div key={i} className="flex-1 bg-warroom-accent/40 rounded-full" style={{ height: `${Math.random() * 100}%`, minHeight: "4px" }} />
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
                className="w-full bg-transparent text-sm text-warroom-text placeholder-warroom-muted resize-none outline-none min-h-[24px] max-h-[200px] leading-6"
                style={{ height: "auto", overflow: "hidden" }}
                onInput={(e) => {
                  const t = e.target as HTMLTextAreaElement;
                  t.style.height = "auto";
                  t.style.height = Math.min(t.scrollHeight, 200) + "px";
                }}
              />
            </div>

            <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded-full hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition">
                  <Plus size={18} />
                </button>
                <button className="p-1.5 rounded-full hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition">
                  <Sparkles size={18} />
                </button>
                <button
                  onClick={toggleRecording}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isRecording ? "text-red-400 bg-red-500/10" : "text-warroom-muted hover:text-warroom-text"}`}
                >
                  {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
                <button
                  onClick={() => setIsCallMode(!isCallMode)}
                  className={`p-1.5 rounded-full hover:bg-warroom-border/50 transition ${isCallMode ? "text-warroom-accent bg-warroom-accent/10" : "text-warroom-muted hover:text-warroom-text"}`}
                >
                  {isCallMode ? <PhoneOff size={18} /> : <Phone size={18} />}
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
                    onClick={sendMessage}
                    disabled={!input.trim() || !wsConnected}
                    className="p-2 rounded-full bg-warroom-accent text-white hover:bg-warroom-accent/80 disabled:opacity-20 disabled:hover:bg-warroom-accent transition"
                  >
                    <Send size={18} />
                  </button>
                )}
              </div>
            </div>
          </div>

          <p className="text-center text-[10px] text-warroom-muted/50 mt-2">
            WAR ROOM — yieldlabs
          </p>
        </div>
      </div>
    </div>
  );
}
