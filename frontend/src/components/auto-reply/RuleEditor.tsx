"use client";

import { useState } from "react";
import { X, Plus, Trash2, Loader2, Info } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

/* ── Types ── */

interface Rule {
  id: string;
  name: string;
  platform: string;
  rule_type: string;
  keywords: string[];
  replies: string[];
  match_mode: string;
  is_active: boolean;
}

interface RuleEditorProps {
  rule: Rule | null; // null = create mode
  onSave: () => void;
  onClose: () => void;
}

/* ── Component ── */

export default function RuleEditor({ rule, onSave, onClose }: RuleEditorProps) {
  const { toast } = useToast();
  const isEdit = !!rule;

  const [name, setName] = useState(rule?.name || "");
  const [platform, setPlatform] = useState(rule?.platform || "all");
  const [ruleType, setRuleType] = useState(rule?.rule_type || "comment");
  const [matchMode, setMatchMode] = useState(rule?.match_mode || "any");
  const [keywords, setKeywords] = useState<string[]>(rule?.keywords || []);
  const [keywordInput, setKeywordInput] = useState("");
  const [replies, setReplies] = useState<string[]>(rule?.replies?.length ? rule.replies : [""]);
  const [isActive, setIsActive] = useState(rule?.is_active ?? true);
  const [saving, setSaving] = useState(false);

  /* ── Keyword management ── */
  const addKeyword = () => {
    const trimmed = keywordInput.trim();
    if (trimmed && !keywords.includes(trimmed)) {
      setKeywords([...keywords, trimmed]);
    }
    setKeywordInput("");
  };

  const removeKeyword = (idx: number) => {
    setKeywords(keywords.filter((_, i) => i !== idx));
  };

  const handleKeywordKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addKeyword();
    }
  };

  /* ── Replies management ── */
  const updateReply = (idx: number, value: string) => {
    setReplies(replies.map((r, i) => (i === idx ? value : r)));
  };

  const addReply = () => {
    setReplies([...replies, ""]);
  };

  const removeReply = (idx: number) => {
    if (replies.length <= 1) return;
    setReplies(replies.filter((_, i) => i !== idx));
  };

  const insertTemplate = (idx: number) => {
    const current = replies[idx];
    updateReply(idx, current + "{{commenter_name}}");
  };

  /* ── Save ── */
  const handleSave = async () => {
    if (!name.trim()) { toast("error", "Name is required"); return; }
    if (keywords.length === 0) { toast("error", "Add at least one keyword"); return; }
    const validReplies = replies.filter((r) => r.trim());
    if (validReplies.length === 0) { toast("error", "Add at least one reply"); return; }

    setSaving(true);
    try {
      const body = {
        name: name.trim(),
        platform,
        rule_type: ruleType,
        match_mode: matchMode,
        keywords,
        replies: validReplies,
        is_active: isActive,
      };
      const url = isEdit
        ? `${API}/api/auto-reply/rules/${rule!.id}`
        : `${API}/api/auto-reply/rules`;
      const r = await authFetch(url, {
        method: isEdit ? "PUT" : "POST",
        body: JSON.stringify(body),
      });
      if (r.ok) {
        toast("success", isEdit ? "Rule updated" : "Rule created");
        onSave();
      } else {
        const err = await r.json().catch(() => ({}));
        toast("error", err.detail || "Failed to save rule");
      }
    } catch {
      toast("error", "Network error");
    }
    setSaving(false);
  };

  return (
    /* Backdrop */
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      {/* Modal */}
      <div className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-warroom-border">
          <h2 className="text-sm font-semibold text-warroom-text">
            {isEdit ? "Edit Rule" : "Create Rule"}
          </h2>
          <button onClick={onClose} className="p-1 text-warroom-muted hover:text-warroom-text transition">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Name */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Welcome new commenters"
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
            />
          </div>

          {/* Platform + Type + Match row */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="all">All</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Type</label>
              <select
                value={ruleType}
                onChange={(e) => setRuleType(e.target.value)}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="comment">Comment</option>
                <option value="dm">DM</option>
                <option value="both">Both</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Match Mode</label>
              <select
                value={matchMode}
                onChange={(e) => setMatchMode(e.target.value)}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="any">Any keyword</option>
                <option value="all">All keywords</option>
                <option value="exact">Exact phrase</option>
              </select>
            </div>
          </div>

          {/* Keywords */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Keywords</label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {keywords.map((kw, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-warroom-accent/15 text-warroom-accent rounded text-xs font-medium"
                >
                  {kw}
                  <button onClick={() => removeKeyword(i)} className="hover:text-red-400 transition">
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={handleKeywordKeyDown}
                placeholder="Type keyword and press Enter"
                className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              />
              <button
                onClick={addKeyword}
                className="px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-xs text-warroom-muted hover:text-warroom-text transition"
              >
                Add
              </button>
            </div>
          </div>

          {/* Replies */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Replies</label>
              <span className="text-[10px] text-warroom-muted">Multiple replies = random selection</span>
            </div>
            <div className="space-y-2">
              {replies.map((reply, i) => (
                <div key={i} className="flex gap-2">
                  <div className="flex-1 relative">
                    <textarea
                      value={reply}
                      onChange={(e) => updateReply(i, e.target.value)}
                      placeholder={`Reply variation ${i + 1}...`}
                      rows={2}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                    />
                    <button
                      onClick={() => insertTemplate(i)}
                      title="Insert {{commenter_name}}"
                      className="absolute top-1 right-1 p-1 text-warroom-muted hover:text-warroom-accent transition"
                    >
                      <Info size={12} />
                    </button>
                  </div>
                  <button
                    onClick={() => removeReply(i)}
                    disabled={replies.length <= 1}
                    className="p-2 text-warroom-muted hover:text-red-400 disabled:opacity-30 transition self-start"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <button
              onClick={addReply}
              className="mt-2 px-3 py-1.5 bg-warroom-bg border border-warroom-border rounded-lg text-xs text-warroom-muted hover:text-warroom-text transition flex items-center gap-1"
            >
              <Plus size={12} />
              Add Reply Variation
            </button>
          </div>

          {/* Active toggle */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-warroom-text">Active</span>
            <button
              onClick={() => setIsActive(!isActive)}
              className={`w-10 h-5 rounded-full relative transition-colors ${
                isActive ? "bg-emerald-500" : "bg-warroom-border"
              }`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  isActive ? "translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-warroom-border">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg hover:text-warroom-text transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-warroom-accent text-white text-xs font-medium rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition flex items-center gap-1.5"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            {isEdit ? "Update Rule" : "Create Rule"}
          </button>
        </div>
      </div>
    </div>
  );
}
