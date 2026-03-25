"use client";

import { useState, useEffect, useCallback } from "react";
import { Clock, Loader2, ChevronDown } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import EmptyState from "@/components/ui/EmptyState";

/* ── Types ── */

interface LogEntry {
  id: string;
  rule_id: string;
  rule_name: string;
  platform: string;
  reply_type: string;
  keyword_matched: string;
  original_text: string;
  reply_sent: string;
  status: string;
  created_at: string;
}

const PAGE_SIZE = 20;

/* ── Component ── */

export default function ReplyLog() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [filterRule, setFilterRule] = useState("");
  const [filterPlatform, setFilterPlatform] = useState("");

  const fetchLogs = useCallback(async (offset = 0, append = false) => {
    if (offset === 0) setLoading(true);
    else setLoadingMore(true);

    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
      if (filterRule) params.set("rule_id", filterRule);
      if (filterPlatform) params.set("platform", filterPlatform);

      const r = await authFetch(`${API}/api/auto-reply/log?${params}`);
      if (r.ok) {
        const d = await r.json();
        const entries: LogEntry[] = Array.isArray(d) ? d : d.logs || [];
        if (append) {
          setLogs((prev) => [...prev, ...entries]);
        } else {
          setLogs(entries);
        }
        setHasMore(entries.length >= PAGE_SIZE);
      }
    } catch {
      /* network error - keep existing data */
    }
    setLoading(false);
    setLoadingMore(false);
  }, [filterRule, filterPlatform]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const loadMore = () => {
    if (!loadingMore && hasMore) {
      fetchLogs(logs.length, true);
    }
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const truncate = (s: string, max: number) => (s.length > max ? s.slice(0, max) + "…" : s);

  if (loading) {
    return (
      <div className="space-y-4">
        {[1,2,3,4].map(i => (
          <div key={i} className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-warroom-border rounded-lg" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-warroom-border rounded w-3/4" />
                <div className="h-3 bg-warroom-border rounded w-1/2" />
                <div className="h-3 bg-warroom-border rounded w-1/4" />
              </div>
            </div>
          </div>
        ))}
        <p className="text-sm text-warroom-muted text-center">Loading reply log...</p>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <EmptyState
        icon={<Clock size={40} />}
        title="No replies yet"
        description="Auto-replies will appear here once your rules start matching."
      />
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex items-center gap-2">
        <input
          value={filterRule}
          onChange={(e) => setFilterRule(e.target.value)}
          placeholder="Filter by rule ID..."
          className="bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent w-48"
        />
        <select
          value={filterPlatform}
          onChange={(e) => setFilterPlatform(e.target.value)}
          className="bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
        >
          <option value="">All Platforms</option>
          <option value="instagram">Instagram</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-warroom-border">
              {["Time", "Platform", "Type", "Keyword", "Original Text", "Reply Sent", "Status"].map((h) => (
                <th key={h} className="px-3 py-2 text-[10px] uppercase tracking-wider text-warroom-muted font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-warroom-border/50 hover:bg-warroom-surface2/30 transition">
                <td className="px-3 py-2.5 text-xs text-warroom-muted whitespace-nowrap">{formatDate(log.created_at)}</td>
                <td className="px-3 py-2.5">
                  <span className="px-2 py-0.5 bg-warroom-bg rounded text-[10px] text-warroom-muted font-medium capitalize">
                    {log.platform}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <span className="px-2 py-0.5 bg-warroom-bg rounded text-[10px] text-warroom-muted font-medium capitalize">
                    {log.reply_type}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-xs text-warroom-accent font-medium">{log.keyword_matched}</td>
                <td className="px-3 py-2.5 text-xs text-warroom-muted max-w-[200px]" title={log.original_text}>
                  {truncate(log.original_text, 50)}
                </td>
                <td className="px-3 py-2.5 text-xs text-warroom-text max-w-[200px]" title={log.reply_sent}>
                  {truncate(log.reply_sent, 50)}
                </td>
                <td className="px-3 py-2.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                    log.status === "sent"
                      ? "bg-emerald-500/15 text-emerald-400"
                      : log.status === "failed"
                        ? "bg-red-500/15 text-red-400"
                        : "bg-warroom-bg text-warroom-muted"
                  }`}>
                    {log.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Load more */}
      {hasMore && (
        <div className="flex justify-center pt-2">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg hover:text-warroom-text transition flex items-center gap-1.5"
          >
            {loadingMore ? <Loader2 size={14} className="animate-spin" /> : <ChevronDown size={14} />}
            Load More
          </button>
        </div>
      )}
    </div>
  );
}
