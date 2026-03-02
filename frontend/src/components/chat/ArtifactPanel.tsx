"use client";

import { useState, useCallback } from "react";
import { X, Copy, ExternalLink, Check, FileCode, FileText, File, ChevronLeft, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";

export interface Artifact {
  id: string;
  type: "code" | "text" | "file";
  title: string;
  content: string;
  language?: string;
  filename?: string;
  timestamp: Date;
}

interface ArtifactPanelProps {
  artifacts: Artifact[];
  activeIndex: number;
  onClose: () => void;
  onSelect: (index: number) => void;
  onRemove: (id: string) => void;
}

function getIcon(type: string) {
  switch (type) {
    case "code": return <FileCode size={14} />;
    case "text": return <FileText size={14} />;
    default: return <File size={14} />;
  }
}

function getLanguageLabel(lang?: string): string {
  const labels: Record<string, string> = {
    typescript: "TypeScript", tsx: "TSX", javascript: "JavaScript", jsx: "JSX",
    python: "Python", bash: "Bash", sh: "Shell", json: "JSON", yaml: "YAML",
    html: "HTML", css: "CSS", sql: "SQL", markdown: "Markdown", md: "Markdown",
    rust: "Rust", go: "Go", java: "Java", cpp: "C++", c: "C",
  };
  return lang ? (labels[lang.toLowerCase()] || lang.toUpperCase()) : "Text";
}

export default function ArtifactPanel({ artifacts, activeIndex, onClose, onSelect, onRemove }: ArtifactPanelProps) {
  const [copied, setCopied] = useState(false);

  const active = artifacts[activeIndex];
  if (!active) return null;

  const copyToClipboard = useCallback(async () => {
    await navigator.clipboard.writeText(active.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [active]);

  const openFile = useCallback(async () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";
    const ext = active.language === "typescript" || active.language === "tsx" ? ".tsx"
      : active.language === "javascript" || active.language === "jsx" ? ".js"
      : active.language === "python" ? ".py"
      : active.language === "json" ? ".json"
      : active.language === "html" ? ".html"
      : active.language === "css" ? ".css"
      : active.language === "bash" || active.language === "sh" ? ".sh"
      : active.language === "sql" ? ".sql"
      : active.language === "yaml" ? ".yml"
      : active.language === "markdown" || active.language === "md" ? ".md"
      : ".txt";

    const filename = active.filename || `${active.title.toLowerCase().replace(/\s+/g, "-")}${ext}`;
    try {
      await fetch(`${API_URL}/api/files/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: active.content, filename }),
      });
    } catch (err) {
      console.error("Failed to open file:", err);
    }
  }, [active]);

  return (
    <div className="h-full flex flex-col bg-warroom-bg border-l border-warroom-border">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-warroom-border bg-warroom-surface">
        <div className="flex items-center gap-2 min-w-0">
          {getIcon(active.type)}
          <span className="text-sm font-medium text-warroom-text truncate">{active.title}</span>
          <span className="text-[10px] text-warroom-muted bg-warroom-border/50 px-1.5 py-0.5 rounded">
            {getLanguageLabel(active.language)}
          </span>
        </div>
        <div className="flex items-center gap-1 ml-2">
          <button
            onClick={copyToClipboard}
            className="p-1.5 rounded-md hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition"
            title="Copy to clipboard"
          >
            {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
          </button>
          <button
            onClick={openFile}
            className="p-1.5 rounded-md hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition"
            title="Open file"
          >
            <ExternalLink size={14} />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition"
            title="Close panel"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Tab bar (when multiple artifacts) */}
      {artifacts.length > 1 && (
        <div className="flex items-center gap-1 px-3 py-2 border-b border-warroom-border bg-warroom-surface/50 overflow-x-auto scrollbar-none">
          <button
            onClick={() => onSelect(Math.max(0, activeIndex - 1))}
            disabled={activeIndex === 0}
            className="p-1 rounded text-warroom-muted hover:text-warroom-text disabled:opacity-20 transition flex-shrink-0"
          >
            <ChevronLeft size={14} />
          </button>
          {artifacts.map((art, i) => (
            <button
              key={art.id}
              onClick={() => onSelect(i)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs whitespace-nowrap transition flex-shrink-0 ${
                i === activeIndex
                  ? "bg-warroom-accent/20 text-warroom-accent"
                  : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/30"
              }`}
            >
              {getIcon(art.type)}
              <span className="max-w-[100px] truncate">{art.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); onRemove(art.id); }}
                className="ml-1 hover:text-red-400 transition"
              >
                <X size={10} />
              </button>
            </button>
          ))}
          <button
            onClick={() => onSelect(Math.min(artifacts.length - 1, activeIndex + 1))}
            disabled={activeIndex === artifacts.length - 1}
            className="p-1 rounded text-warroom-muted hover:text-warroom-text disabled:opacity-20 transition flex-shrink-0"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {active.type === "code" ? (
          <div className="relative">
            <pre className="p-4 text-sm font-mono leading-relaxed text-slate-300 overflow-x-auto">
              <code>{active.content}</code>
            </pre>
          </div>
        ) : active.type === "text" ? (
          <div className="p-4 prose prose-invert prose-sm max-w-none [&>p]:mb-3 [&>h1]:text-lg [&>h2]:text-base [&>h3]:text-sm [&>code]:bg-black/30 [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded-md [&>code]:text-warroom-accent [&>pre]:bg-black/40 [&>pre]:rounded-xl [&>pre]:p-4">
            <ReactMarkdown>{active.content}</ReactMarkdown>
          </div>
        ) : (
          <div className="p-4">
            <pre className="text-sm font-mono text-slate-300 whitespace-pre-wrap">{active.content}</pre>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-warroom-border bg-warroom-surface/50 flex items-center justify-between">
        <span className="text-[10px] text-warroom-muted">
          {active.content.split("\n").length} lines · {(active.content.length / 1024).toFixed(1)}KB
        </span>
        <span className="text-[10px] text-warroom-muted">
          {artifacts.length > 1 ? `${activeIndex + 1} of ${artifacts.length}` : ""}
        </span>
      </div>
    </div>
  );
}
