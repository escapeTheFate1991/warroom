"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus, Power, Pencil, Trash2, MessageSquare, Zap,
  BarChart3, Clock, TrendingUp, Loader2, Instagram,
  AlertCircle, ExternalLink,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import ScrollTabs from "@/components/ui/ScrollTabs";
import LoadingState from "@/components/ui/LoadingState";
import EmptyState from "@/components/ui/EmptyState";
import RuleEditor from "./RuleEditor";
import ReplyLog from "./ReplyLog";
import { useSocialAccounts, PLATFORM_CONFIGS } from "@/hooks/useSocialAccounts";

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
  created_at: string;
}

interface Stats {
  total_replies: number;
  replies_today: number;
  replies_this_week: number;
  top_rules: { rule_id: string; rule_name: string; count: number }[];
  by_platform: Record<string, number>;
}

/* ── Constants ── */

const SUB_TABS = [
  { id: "rules", label: "Rules", icon: Zap },
  { id: "log", label: "Reply Log", icon: Clock },
  { id: "stats", label: "Stats", icon: BarChart3 },
];

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "bg-pink-500/15 text-pink-400 border-pink-500/30",
  all: "bg-blue-500/15 text-blue-400 border-blue-500/30",
};

const TYPE_COLORS: Record<string, string> = {
  comment: "bg-emerald-500/15 text-emerald-400",
  dm: "bg-violet-500/15 text-violet-400",
  follow: "bg-blue-500/15 text-blue-400",
};

/* ── Component ── */

export default function AutoReplyPanel() {
  const { toast } = useToast();
  const socialAccounts = useSocialAccounts();
  const [subTab, setSubTab] = useState("rules");
  const [rules, setRules] = useState<Rule[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);

  /* Filters */
  const [filterPlatform, setFilterPlatform] = useState("all");
  const [filterType, setFilterType] = useState("all");
  const [filterActive, setFilterActive] = useState("all");

  /* ── Fetch rules ── */
  const fetchRules = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterPlatform !== "all") params.set("platform", filterPlatform);
      if (filterType !== "all") params.set("rule_type", filterType);
      if (filterActive !== "all") params.set("is_active", filterActive === "active" ? "true" : "false");
      const qs = params.toString();
      const r = await authFetch(`${API}/api/auto-reply/rules${qs ? `?${qs}` : ""}`);
      if (r.ok) {
        const d = await r.json();
        setRules(Array.isArray(d) ? d : d.rules || []);
      } else {
        toast("error", "Failed to load rules");
      }
    } catch {
      toast("error", "Network error loading rules");
    }
    setLoading(false);
  }, [filterPlatform, filterType, filterActive, toast]);

  /* ── Fetch stats ── */
  const fetchStats = useCallback(async () => {
    try {
      const r = await authFetch(`${API}/api/auto-reply/stats`);
      if (r.ok) {
        setStats(await r.json());
      }
    } catch {
      /* silently fail stats */
    }
  }, []);

  useEffect(() => { fetchRules(); }, [fetchRules]);
  useEffect(() => { if (subTab === "stats") fetchStats(); }, [subTab, fetchStats]);

  /* ── Toggle rule ── */
  const toggleRule = async (rule: Rule) => {
    try {
      const r = await authFetch(`${API}/api/auto-reply/rules/${rule.id}/toggle`, { method: "POST" });
      if (r.ok) {
        setRules((prev) => prev.map((ru) => (ru.id === rule.id ? { ...ru, is_active: !ru.is_active } : ru)));
        toast("success", `Rule "${rule.name}" ${rule.is_active ? "disabled" : "enabled"}`);
      } else {
        toast("error", "Failed to toggle rule");
      }
    } catch {
      toast("error", "Network error");
    }
  };

  /* ── Delete rule ── */
  const deleteRule = async (rule: Rule) => {
    if (!confirm(`Delete rule "${rule.name}"?`)) return;
    try {
      const r = await authFetch(`${API}/api/auto-reply/rules/${rule.id}`, { method: "DELETE" });
      if (r.ok) {
        setRules((prev) => prev.filter((ru) => ru.id !== rule.id));
        toast("success", "Rule deleted");
      } else {
        toast("error", "Failed to delete rule");
      }
    } catch {
      toast("error", "Network error");
    }
  };

  /* ── Editor callbacks ── */
  const openCreate = () => { setEditingRule(null); setEditorOpen(true); };
  const openEdit = (rule: Rule) => { setEditingRule(rule); setEditorOpen(true); };
  const onEditorSave = () => { setEditorOpen(false); setEditingRule(null); fetchRules(); };
  const onEditorClose = () => { setEditorOpen(false); setEditingRule(null); };

  /* ── Render connection status ── */
  const renderConnectionStatus = () => {
    const connectedPlatforms = Object.keys(socialAccounts.connected);
    const supportedPlatforms = ['instagram']; // Auto-reply currently supports Instagram
    const missingConnections = supportedPlatforms.filter(p => !socialAccounts.isConnected(p));

    if (socialAccounts.loading) {
      return (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2 text-blue-400 text-sm">
            <Loader2 size={14} className="animate-spin" />
            Checking social media connections...
          </div>
        </div>
      );
    }

    if (missingConnections.length > 0) {
      return (
        <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2 text-orange-400 text-sm mb-2">
            <AlertCircle size={14} />
            Connect your social accounts to use auto-reply
          </div>
          <div className="flex flex-wrap gap-2">
            {missingConnections.map(platform => {
              const config = PLATFORM_CONFIGS[platform as keyof typeof PLATFORM_CONFIGS];
              return (
                <button
                  key={platform}
                  onClick={() => socialAccounts.connect(platform)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500/20 hover:bg-orange-500/30 rounded-lg text-xs text-orange-300 transition"
                >
                  <Instagram size={12} />
                  Connect {config.name}
                  <ExternalLink size={10} />
                </button>
              );
            })}
          </div>
        </div>
      );
    }

    return (
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 mb-4">
        <div className="flex items-center gap-2 text-emerald-400 text-sm">
          <MessageSquare size={14} />
          Connected to {connectedPlatforms.map(p => PLATFORM_CONFIGS[p as keyof typeof PLATFORM_CONFIGS]?.name || p).join(', ')}
        </div>
      </div>
    );
  };

  /* ── Render rules list ── */
  const renderRules = () => {
    if (loading) return <LoadingState message="Loading rules..." />;
    if (rules.length === 0) {
      return (
        <EmptyState
          icon={<Zap size={40} />}
          title="No auto-reply rules"
          description="Create your first rule to automatically respond to comments and DMs."
          action={{ label: "Create Rule", onClick: openCreate }}
        />
      );
    }
    return (
      <div className="space-y-3">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition"
          >
            <div className="flex items-start justify-between gap-3">
              {/* Left */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className="text-sm font-semibold text-warroom-text">{rule.name}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${PLATFORM_COLORS[rule.platform] || PLATFORM_COLORS.all}`}>
                    {rule.platform}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${TYPE_COLORS[rule.rule_type] || TYPE_COLORS.comment}`}>
                    {rule.rule_type === "follow" ? "Follow" : rule.rule_type.toUpperCase()}
                  </span>
                  {/* Delivery channels */}
                  <div className="flex items-center gap-1">
                    {(rule.delivery_channels || ["dm"]).map(channel => (
                      <span 
                        key={channel}
                        className="px-1.5 py-0.5 bg-warroom-accent/10 text-warroom-accent rounded text-[9px] font-medium"
                      >
                        {channel === "dm" ? "DM" : "Comment"}
                      </span>
                    ))}
                  </div>
                </div>
                
                {/* Keywords - only show for non-follow rules */}
                {rule.rule_type !== "follow" && rule.keywords && rule.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {rule.keywords.slice(0, 5).map((kw, i) => (
                      <span key={i} className="px-2 py-0.5 bg-warroom-bg rounded text-[10px] text-warroom-muted font-medium">
                        {kw}
                      </span>
                    ))}
                    {rule.keywords.length > 5 && (
                      <span className="px-2 py-0.5 text-[10px] text-warroom-muted">+{rule.keywords.length - 5} more</span>
                    )}
                  </div>
                )}
                
                {/* Follow rule description */}
                {rule.rule_type === "follow" && (
                  <div className="mb-2">
                    <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-[10px] font-medium">
                      Triggers on new followers
                    </span>
                  </div>
                )}
                
                <div className="flex items-center gap-3 text-xs text-warroom-muted">
                  <span className="flex items-center gap-1">
                    <MessageSquare size={12} />
                    {rule.replies.length} {rule.replies.length === 1 ? "reply" : "replies"}
                  </span>
                  {rule.rule_type !== "follow" && rule.match_mode && (
                    <span className="capitalize">{rule.match_mode.replace(/_/g, " ")}</span>
                  )}
                </div>
              </div>
              {/* Right – actions */}
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => toggleRule(rule)}
                  title={rule.is_active ? "Disable" : "Enable"}
                  className={`p-1.5 rounded-lg transition ${
                    rule.is_active
                      ? "bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25"
                      : "bg-warroom-bg text-warroom-muted hover:text-warroom-text"
                  }`}
                >
                  <Power size={14} />
                </button>
                <button
                  onClick={() => openEdit(rule)}
                  className="p-1.5 rounded-lg bg-warroom-bg text-warroom-muted hover:text-warroom-text transition"
                  title="Edit"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={() => deleteRule(rule)}
                  className="p-1.5 rounded-lg bg-warroom-bg text-warroom-muted hover:text-red-400 transition"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  /* ── Render stats ── */
  const renderStats = () => {
    if (!stats) return <LoadingState message="Loading stats..." />;
    return (
      <div className="space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { label: "Total Replies", value: stats.total_replies, icon: MessageSquare },
            { label: "Today", value: stats.replies_today, icon: TrendingUp },
            { label: "This Week", value: stats.replies_this_week, icon: BarChart3 },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-1">
                <Icon size={14} className="text-warroom-accent" />
                <span className="text-[10px] uppercase tracking-wider text-warroom-muted">{label}</span>
              </div>
              <div className="text-2xl font-bold text-warroom-text">{value}</div>
            </div>
          ))}
        </div>

        {/* Top rules */}
        {stats.top_rules.length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
            <h3 className="text-sm font-semibold text-warroom-text mb-3">Top Performing Rules</h3>
            <div className="space-y-2">
              {stats.top_rules.map((tr, i) => (
                <div key={tr.rule_id} className="flex items-center justify-between text-sm">
                  <span className="text-warroom-muted">
                    <span className="text-warroom-text font-medium mr-2">#{i + 1}</span>
                    {tr.rule_name}
                  </span>
                  <span className="text-warroom-accent font-medium">{tr.count} replies</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* By platform */}
        {Object.keys(stats.by_platform).length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
            <h3 className="text-sm font-semibold text-warroom-text mb-3">Replies by Platform</h3>
            <div className="space-y-2">
              {Object.entries(stats.by_platform).map(([platform, count]) => (
                <div key={platform} className="flex items-center justify-between text-sm">
                  <span className="text-warroom-muted capitalize">{platform}</span>
                  <span className="text-warroom-text font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-warroom-border bg-warroom-surface/50">
        <div className="flex items-center gap-2">
          <Zap size={18} className="text-warroom-accent" />
          <h1 className="text-sm font-semibold text-warroom-text">Auto-Reply</h1>
        </div>
        {subTab === "rules" && (
          <button
            onClick={openCreate}
            className="px-3 py-1.5 bg-warroom-accent text-white text-xs font-medium rounded-lg hover:bg-warroom-accent/80 transition flex items-center gap-1.5"
          >
            <Plus size={14} />
            New Rule
          </button>
        )}
      </div>

      {/* Sub-tabs */}
      <ScrollTabs tabs={SUB_TABS} active={subTab} onChange={setSubTab} size="sm" />

      {/* Filters (rules tab only) */}
      {subTab === "rules" && (
        <div className="flex items-center gap-2 px-5 py-2 border-b border-warroom-border">
          <select
            value={filterPlatform}
            onChange={(e) => setFilterPlatform(e.target.value)}
            className="bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
          >
            <option value="all">All Platforms</option>
            <option value="instagram">Instagram</option>
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
          >
            <option value="all">All Types</option>
            <option value="comment">Comment</option>
            <option value="dm">DM</option>
            <option value="follow">Follow</option>
          </select>
          <select
            value={filterActive}
            onChange={(e) => setFilterActive(e.target.value)}
            className="bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {subTab === "rules" && (
          <>
            {renderConnectionStatus()}
            {renderRules()}
          </>
        )}
        {subTab === "log" && <ReplyLog />}
        {subTab === "stats" && renderStats()}
      </div>

      {/* Rule editor modal */}
      {editorOpen && (
        <RuleEditor rule={editingRule} onSave={onEditorSave} onClose={onEditorClose} />
      )}
    </div>
  );
}
