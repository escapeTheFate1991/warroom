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
  delivery_channels: string[];
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
  const [platform, setPlatform] = useState(rule?.platform || "instagram");
  const [ruleType, setRuleType] = useState(rule?.rule_type || "comment");
  const [matchMode, setMatchMode] = useState(rule?.match_mode || "any");
  const [keywords, setKeywords] = useState<string[]>(rule?.keywords || []);
  const [keywordInput, setKeywordInput] = useState("");
  const [replies, setReplies] = useState<string[]>(rule?.replies?.length ? rule.replies : [""]);
  const [isActive, setIsActive] = useState(rule?.is_active ?? true);
  const [deliveryChannels, setDeliveryChannels] = useState<string[]>(rule?.delivery_channels || ["dm"]);
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
    const template = ruleType === "follow" ? "{{username}}" : "{{commenter_name}}";
    updateReply(idx, current + template);
  };

  /* ── Delivery channels ── */
  const toggleDeliveryChannel = (channel: string) => {
    if (ruleType === "follow") {
      // Follow rules must have DM delivery
      setDeliveryChannels(["dm"]);
      return;
    }
    
    if (deliveryChannels.includes(channel)) {
      const updated = deliveryChannels.filter(c => c !== channel);
      if (updated.length > 0) {
        setDeliveryChannels(updated);
      }
    } else {
      setDeliveryChannels([...deliveryChannels, channel]);
    }
  };

  /* ── Save ── */
  const handleSave = async () => {
    if (!name.trim()) { toast("error", "Name is required"); return; }
    
    // Follow rules don't need keywords, others do
    if (ruleType !== "follow" && keywords.length === 0) { 
      toast("error", "Add at least one keyword"); return; 
    }
    
    const validReplies = replies.filter((r) => r.trim());
    if (validReplies.length === 0) { toast("error", "Add at least one reply"); return; }

    if (deliveryChannels.length === 0) { 
      toast("error", "Select at least one delivery channel"); return; 
    }

    setSaving(true);
    try {
      const body = {
        name: name.trim(),
        platform,
        rule_type: ruleType,
        match_mode: ruleType === "follow" ? undefined : matchMode,
        keywords: ruleType === "follow" ? [] : keywords,
        replies: validReplies,
        is_active: isActive,
        delivery_channels: deliveryChannels,
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

          {/* Platform + Trigger Type */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="flex items-center gap-1 mb-1">
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Platform</label>
                <div className="group relative">
                  <Info size={10} className="text-warroom-muted cursor-help" />
                  <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text whitespace-nowrap z-10">
                    Which social platform to monitor
                  </div>
                </div>
              </div>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="instagram">Instagram</option>
              </select>
            </div>
            <div>
              <div className="flex items-center gap-1 mb-1">
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Trigger</label>
                <div className="group relative">
                  <Info size={10} className="text-warroom-muted cursor-help" />
                  <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text whitespace-nowrap z-10">
                    What event triggers this auto-reply
                  </div>
                </div>
              </div>
              <select
                value={ruleType}
                onChange={(e) => {
                  setRuleType(e.target.value);
                  // Auto-adjust delivery channels based on trigger type
                  if (e.target.value === "follow") {
                    setDeliveryChannels(["dm"]);
                    setKeywords([]);
                  } else if (e.target.value === "comment") {
                    setDeliveryChannels(["comment"]);
                  } else if (e.target.value === "dm") {
                    setDeliveryChannels(["dm"]);
                  }
                }}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="comment">Comment</option>
                <option value="dm">DM</option>
                <option value="follow">Follow</option>
              </select>
            </div>
          </div>

          {/* Delivery Channels */}
          <div>
            <div className="flex items-center gap-1 mb-2">
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Reply Via</label>
              <div className="group relative">
                <Info size={10} className="text-warroom-muted cursor-help" />
                <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text whitespace-nowrap z-10">
                  How to send the auto-reply message
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => toggleDeliveryChannel("comment")}
                disabled={ruleType === "follow" || ruleType === "dm"}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  deliveryChannels.includes("comment")
                    ? "bg-warroom-accent text-white"
                    : "bg-warroom-bg border border-warroom-border text-warroom-muted hover:text-warroom-text"
                } ${(ruleType === "follow" || ruleType === "dm") ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                Comment Reply
              </button>
              <button
                type="button"
                onClick={() => toggleDeliveryChannel("dm")}
                disabled={ruleType === "comment"}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  deliveryChannels.includes("dm")
                    ? "bg-warroom-accent text-white"
                    : "bg-warroom-bg border border-warroom-border text-warroom-muted hover:text-warroom-text"
                } ${ruleType === "comment" ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                Direct Message
              </button>
            </div>
            <p className="text-xs text-warroom-muted mt-1">
              {ruleType === "follow" 
                ? "Follow triggers can only send DMs"
                : ruleType === "comment"
                ? "Comment triggers can reply publicly or send DMs"
                : ruleType === "dm"
                ? "DM triggers can only send DMs"
                : "Select where to send the auto-reply"
              }
            </p>
          </div>

          {/* Keywords - Hidden for follow triggers */}
          {ruleType !== "follow" && (
            <>
              {/* Match Mode */}
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Match Mode</label>
                  <div className="group relative">
                    <Info size={10} className="text-warroom-muted cursor-help" />
                    <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text whitespace-nowrap z-10">
                      How keywords should match in text
                    </div>
                  </div>
                </div>
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

              {/* Keywords */}
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Keywords</label>
                  <div className="group relative">
                    <Info size={10} className="text-warroom-muted cursor-help" />
                    <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text whitespace-nowrap z-10">
                      Words/phrases that trigger this rule
                    </div>
                  </div>
                </div>
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
            </>
          )}

          {/* Replies */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1">
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Replies</label>
                <div className="group relative">
                  <Info size={10} className="text-warroom-muted cursor-help" />
                  <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text whitespace-nowrap z-10">
                    Auto-reply messages to send
                  </div>
                </div>
              </div>
              <span className="text-[10px] text-warroom-muted">Multiple = random selection</span>
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
                      title={`Insert ${ruleType === "follow" ? "{{username}}" : "{{commenter_name}}"}`}
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
