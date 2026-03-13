"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Sparkles, Settings2, Loader2, Copy, Check, RotateCcw, Trash2 } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface Message {
  role: "user" | "model";
  text: string;
}

interface ModelOption {
  id: string;
  name: string;
  description: string;
}

const DEFAULT_MODELS: ModelOption[] = [
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", description: "Fast, versatile model" },
  { id: "gemini-2.5-pro-preview-05-06", name: "Gemini 2.5 Pro", description: "Complex reasoning" },
  { id: "gemini-2.5-flash-preview-05-20", name: "Gemini 2.5 Flash", description: "Speed + intelligence" },
];

export default function AIStudioPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [model, setModel] = useState("gemini-2.0-flash");
  const [systemInstruction, setSystemInstruction] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [showSettings, setShowSettings] = useState(false);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [copied, setCopied] = useState<number | null>(null);
  const [models, setModels] = useState<ModelOption[]>(DEFAULT_MODELS);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    authFetch(`${API}/api/ai-studio/status`).then(r => r.json()).then(d => setConfigured(d.configured)).catch(() => setConfigured(false));
    authFetch(`${API}/api/ai-studio/models`).then(r => r.json()).then(d => { if (d.models?.length) setModels(d.models); }).catch(() => {});
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    const newMessages: Message[] = [...messages, { role: "user", text }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    try {
      const resp = await authFetch(`${API}/api/ai-studio/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, text: m.text })),
          model,
          temperature,
          system_instruction: systemInstruction || undefined,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setMessages([...newMessages, { role: "model", text: data.response }]);
      } else {
        setMessages([...newMessages, { role: "model", text: `⚠️ Error: ${data.detail || "Unknown error"}` }]);
      }
    } catch (err) {
      setMessages([...newMessages, { role: "model", text: `⚠️ Network error` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, model, temperature, systemInstruction]);

  const copyText = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopied(idx);
    setTimeout(() => setCopied(null), 1500);
  };

  if (configured === false) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-warroom-muted gap-3 p-8">
        <Sparkles size={40} className="text-warroom-accent/50" />
        <h2 className="text-lg font-semibold text-warroom-text">Google AI Studio</h2>
        <p className="text-sm text-center max-w-md">Add your Google AI Studio (Gemini) API key in <strong>Settings → API Keys → Google</strong> to start using AI Studio.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-warroom-border bg-warroom-surface/50">
          <div className="flex items-center gap-2.5">
            <Sparkles size={18} className="text-warroom-accent" />
            <h1 className="text-base font-bold text-warroom-text">AI Studio</h1>
            <select value={model} onChange={e => setModel(e.target.value)} className="ml-3 text-xs bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-warroom-text">
              {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => { setMessages([]); }} className="p-1.5 rounded-lg hover:bg-warroom-border/50 text-warroom-muted" title="Clear chat"><Trash2 size={15} /></button>
            <button onClick={() => setShowSettings(!showSettings)} className={`p-1.5 rounded-lg hover:bg-warroom-border/50 ${showSettings ? "text-warroom-accent" : "text-warroom-muted"}`} title="Settings"><Settings2 size={15} /></button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-warroom-muted gap-3">
              <Sparkles size={32} className="text-warroom-accent/30" />
              <p className="text-sm">Start a conversation with Gemini</p>
              <p className="text-xs max-w-sm text-center">Ask questions, generate content, brainstorm ideas, or analyze data using Google&apos;s most capable AI models.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${m.role === "user" ? "bg-warroom-accent/20 text-warroom-text" : "bg-warroom-surface border border-warroom-border text-warroom-text"}`}>
                <pre className="whitespace-pre-wrap font-sans">{m.text}</pre>
                {m.role === "model" && (
                  <button onClick={() => copyText(m.text, i)} className="mt-2 text-[10px] text-warroom-muted hover:text-warroom-text flex items-center gap-1">
                    {copied === i ? <><Check size={10} /> Copied</> : <><Copy size={10} /> Copy</>}
                  </button>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl px-4 py-3">
                <Loader2 size={16} className="animate-spin text-warroom-accent" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-5 py-3 border-t border-warroom-border bg-warroom-surface/50">
          <div className="flex items-end gap-2">
            <textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Message Gemini..." rows={1} className="flex-1 bg-warroom-bg border border-warroom-border rounded-xl px-4 py-2.5 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent min-h-[40px] max-h-[120px]" style={{ height: "auto", overflow: "auto" }}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()} className="p-2.5 rounded-xl bg-warroom-accent text-white disabled:opacity-40 hover:bg-warroom-accent/80 transition-colors">
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>


      {/* Settings sidebar */}
      {showSettings && (
        <div className="w-72 border-l border-warroom-border bg-warroom-surface/50 p-4 space-y-4 overflow-y-auto">
          <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider">Generation Settings</h3>
          <div>
            <label className="text-xs text-warroom-muted block mb-1">System Instruction</label>
            <textarea value={systemInstruction} onChange={e => setSystemInstruction(e.target.value)} placeholder="e.g. You are a helpful marketing assistant..." rows={4}
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text resize-none focus:outline-none focus:border-warroom-accent"
            />
          </div>
          <div>
            <label className="text-xs text-warroom-muted block mb-1">Temperature: {temperature.toFixed(1)}</label>
            <input type="range" min="0" max="2" step="0.1" value={temperature} onChange={e => setTemperature(parseFloat(e.target.value))} className="w-full accent-warroom-accent" />
            <div className="flex justify-between text-[10px] text-warroom-muted"><span>Precise</span><span>Creative</span></div>
          </div>
          <div>
            <label className="text-xs text-warroom-muted block mb-1">Model</label>
            {models.map(m => (
              <button key={m.id} onClick={() => setModel(m.id)} className={`w-full text-left px-3 py-2 rounded-lg text-xs mb-1 transition-colors ${model === m.id ? "bg-warroom-accent/20 text-warroom-accent border border-warroom-accent/30" : "bg-warroom-bg border border-warroom-border text-warroom-text hover:border-warroom-accent/30"}`}>
                <p className="font-medium">{m.name}</p>
                <p className="text-[10px] text-warroom-muted mt-0.5">{m.description}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}