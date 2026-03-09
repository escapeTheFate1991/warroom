"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { X, Send, Loader2, Sparkles, MessageSquare } from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */

export interface GroundedAIContext {
  surface?: string;
  entityType?: string;
  entityId?: string;
  entityName?: string;
  title?: string;
  summary?: string;
  facts?: { label: string; value: string | number }[];
  contextData?: Record<string, unknown>;
}

interface SharedAIChatPanelProps {
  context: GroundedAIContext;
  panelTitle?: string;
  emptyHint?: string;
  onClose?: () => void;
  className?: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/* ── Pre-baked Questions ───────────────────────────────── */

const TOPIC_QUESTIONS: Record<string, string[]> = {
  sales: [
    "What should I focus on to close more deals this month?",
    "Which leads are most likely to convert right now?",
    "Summarize my pipeline health and any risks",
    "What's my revenue trend looking like?",
    "Any overdue invoices I should follow up on?",
  ],
  social: [
    "Which platform is performing best right now?",
    "What content type gets the most engagement?",
    "Suggest 3 post ideas based on my analytics",
    "Are there any engagement drops I should know about?",
    "What's the best time to post this week?",
  ],
  agents: [
    "Which agents are currently active and what are they doing?",
    "Show me recent agent completions and their results",
    "Which agent should I assign this task to?",
    "Are there any failed or stalled agent tasks?",
    "How can I optimize my agent workflow?",
  ],
  ai: [
    "Which agents are currently active and what are they doing?",
    "Show me recent agent completions and their results",
    "Which agent should I assign this task to?",
    "Are there any failed or stalled agent tasks?",
    "How can I optimize my agent workflow?",
  ],
};

function getQuestionsForContext(context: GroundedAIContext): string[] {
  const surface = context.surface?.toLowerCase() || "";
  return TOPIC_QUESTIONS[surface] || TOPIC_QUESTIONS.agents;
}

/* ── Component ─────────────────────────────────────────── */

export default function SharedAIChatPanel({
  context,
  panelTitle,
  emptyHint,
  onClose,
  className = "",
}: SharedAIChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const buildSystemPrompt = (): string => {
    const surface = context.surface || "general";
    const factsStr = context.facts?.map(f => `- ${f.label}: ${f.value}`).join("\n") || "No metrics available.";

    return `You are an AI assistant embedded in the War Room Command Center, currently scoped to the "${surface}" dashboard view.

CONTEXT:
- View: ${context.title || context.entityName || surface}
- Summary: ${context.summary || "No summary available."}
- Key Metrics:
${factsStr}

RULES:
- Only answer questions about ${surface}. If the user asks about something outside this scope, politely redirect them.
- Keep answers concise and actionable.
- Reference the metrics above when relevant.
- Suggest specific next steps when possible.
- Format with bullet points for readability.`;
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: "user", content: content.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const systemPrompt = buildSystemPrompt();
      const chatMessages = [...messages, userMsg].map(m => ({
        role: m.role,
        content: m.content,
      }));

      const res = await authFetch(`${API}/api/chat/ask-ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          system: systemPrompt,
          messages: chatMessages,
          context: {
            surface: context.surface,
            entityType: context.entityType,
            entityId: context.entityId,
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          role: "assistant",
          content: data.response || data.message || data.content || "I couldn't generate a response. Try rephrasing your question.",
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: "Sorry, I couldn't process that request right now. The backend may not have the `/api/chat/ask-ai` endpoint configured yet.",
        }]);
      }
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Connection error. Please try again.",
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const questions = getQuestionsForContext(context);

  return (
    <div className={`bg-warroom-surface border border-warroom-border rounded-2xl flex flex-col overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-warroom-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-warroom-accent" />
          <h3 className="text-sm font-semibold text-warroom-text">
            {panelTitle || `Ask AI about ${context.surface || "this view"}`}
          </h3>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1 text-warroom-muted hover:text-warroom-text transition">
            <X size={16} />
          </button>
        )}
      </div>

      {/* Context Banner */}
      <div className="px-4 py-2 bg-warroom-accent/5 border-b border-warroom-border text-[11px] text-warroom-muted flex-shrink-0">
        <span className="text-warroom-accent font-medium">Scope:</span>{" "}
        {context.title || context.surface} — {context.summary?.slice(0, 80) || "Ready to help"}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8">
            <MessageSquare size={28} className="text-warroom-muted/30 mb-3" />
            <p className="text-xs text-warroom-muted mb-4">
              {emptyHint || `Ask about ${context.surface || "this dashboard"}`}
            </p>
            {/* Pre-baked Questions */}
            <div className="w-full space-y-1.5">
              <p className="text-[10px] text-warroom-muted/60 uppercase tracking-wide text-center mb-2">
                Quick questions
              </p>
              {questions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  className="w-full text-left px-3 py-2 rounded-xl bg-warroom-bg border border-warroom-border text-xs text-warroom-text hover:border-warroom-accent/30 hover:bg-warroom-accent/5 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] px-3 py-2 rounded-2xl text-xs leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-warroom-accent text-white rounded-tr-sm"
                    : "bg-warroom-bg border border-warroom-border text-warroom-text rounded-tl-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-warroom-bg border border-warroom-border rounded-2xl rounded-tl-sm px-3 py-2">
              <Loader2 size={14} className="animate-spin text-warroom-accent" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-warroom-border flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask about ${context.surface || "this view"}...`}
            rows={1}
            className="flex-1 bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-xs text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50 resize-none max-h-20"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading}
            className="p-2 bg-warroom-accent text-white rounded-xl hover:bg-warroom-accent/80 disabled:opacity-30 transition flex-shrink-0"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
