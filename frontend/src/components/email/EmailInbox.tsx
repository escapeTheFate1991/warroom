"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Mail, Search, RefreshCw, Inbox, Check, ChevronLeft, ChevronRight, Filter, Bot,
} from "lucide-react";
import EntityAssignmentControl from "@/components/agents/EntityAssignmentControl";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";

/* ── Types ── */
interface EmailAccount {
  id: string;
  email: string;
  provider: string;
  name?: string;
}

interface EmailMessage {
  id: string;
  account_id: string;
  from_name: string;
  from_email: string;
  to: string[];
  subject: string;
  snippet: string;
  body_html?: string;
  body_text?: string;
  date: string;
  is_read: boolean;
  agent_assignments: AgentAssignmentSummary[];
}

interface MessagesResponse {
  messages: EmailMessage[];
  total: number;
  page: number;
  per_page: number;
}

type RawEmailMessage = Partial<EmailMessage> & {
  id: string | number;
  account_id?: string | number;
  from_address?: string;
  to_addresses?: Array<{ email?: string; name?: string } | string>;
  agent_assignments?: AgentAssignmentSummary[];
};

/* ── Helpers ── */
const LIMIT = 25;
const REFRESH_INTERVAL = 120_000; // 2 minutes

function relativeDate(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function fullDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

function sanitizeHTML(html: string): string {
  // Strip script/style tags and event handlers
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/\son\w+="[^"]*"/gi, "")
    .replace(/\son\w+='[^']*'/gi, "")
    .replace(/javascript:/gi, "");
}

function avatarLetter(name: string): string {
  return (name?.[0] ?? "?").toUpperCase();
}

function normalizeRecipients(value: RawEmailMessage["to_addresses"] | string[] | undefined): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => typeof entry === "string" ? entry : entry.email || entry.name || "")
    .filter(Boolean);
}

function normalizeMessage(raw: RawEmailMessage): EmailMessage {
  return {
    id: String(raw.id),
    account_id: String(raw.account_id ?? ""),
    from_name: raw.from_name || "",
    from_email: raw.from_email || raw.from_address || "",
    to: normalizeRecipients(raw.to || raw.to_addresses),
    subject: raw.subject || "",
    snippet: raw.snippet || "",
    body_html: raw.body_html,
    body_text: raw.body_text,
    date: raw.date || new Date().toISOString(),
    is_read: Boolean(raw.is_read),
    agent_assignments: Array.isArray(raw.agent_assignments) ? raw.agent_assignments : [],
  };
}

/* ── Skeleton Loader ── */
function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 animate-pulse">
      <div className="w-4 h-4 rounded bg-warroom-border/40" />
      <div className="w-8 h-8 rounded-full bg-warroom-border/40" />
      <div className="flex-1 space-y-2">
        <div className="h-3 bg-warroom-border/40 rounded w-1/3" />
        <div className="h-3 bg-warroom-border/40 rounded w-2/3" />
      </div>
      <div className="h-3 bg-warroom-border/40 rounded w-10" />
    </div>
  );
}

/* ── Main Component ── */
export default function EmailInbox() {
  // State
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [messages, setMessages] = useState<EmailMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<EmailMessage | null>(null);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const silentRef = useRef(false);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [search]);

  // Fetch accounts
  useEffect(() => {
    (async () => {
      try {
        const res = await authFetch(`${API}/api/email/accounts`);
        if (!res.ok) return;
        const data = await res.json();
        const list: EmailAccount[] = Array.isArray(data) ? data : data.accounts ?? [];
        setAccounts(list);
        if (list.length > 0 && !selectedAccountId) setSelectedAccountId(list[0].id);
      } catch { /* silent */ }
    })();
  }, []);

  // Fetch messages
  const fetchMessages = useCallback(async (silent = false) => {
    if (!selectedAccountId) return;
    if (!silent) setLoading(true);
    silentRef.current = silent;
    try {
      const params = new URLSearchParams({
        account_id: selectedAccountId,
        page: String(page),
        per_page: String(LIMIT),
      });
      if (unreadOnly) params.set("is_read", "false");
      if (debouncedSearch) params.set("search", debouncedSearch);

      const res = await authFetch(`${API}/api/email/messages?${params}`);
      if (!res.ok) return;
      const data: MessagesResponse = await res.json();
      setMessages((data.messages ?? []).map((message) => normalizeMessage(message)));
      setTotal(data.total ?? 0);
    } catch { /* silent */ } finally {
      if (!silent) setLoading(false);
    }
  }, [selectedAccountId, page, unreadOnly, debouncedSearch]);

  useEffect(() => { fetchMessages(); }, [fetchMessages]);

  // Auto-refresh every 2 min
  useEffect(() => {
    const iv = setInterval(() => fetchMessages(true), REFRESH_INTERVAL);
    return () => clearInterval(iv);
  }, [fetchMessages]);

  // Select message → fetch full body
  const selectMessage = useCallback(async (msg: EmailMessage) => {
    setSelectedId(msg.id);
    setDetail(msg); // show what we have immediately
    setDetailLoading(true);
    try {
      const res = await authFetch(`${API}/api/email/messages/${msg.id}`);
      if (res.ok) {
        const full = normalizeMessage((await res.json()) as RawEmailMessage);
        setDetail(full);
        setMessages((prev) => prev.map((m) => m.id === msg.id ? { ...m, is_read: true, agent_assignments: full.agent_assignments } : m));
        // Update in list if now read
      }
    } catch { /* silent */ } finally {
      setDetailLoading(false);
    }
  }, []);

  // Mark as read
  const markAsRead = useCallback(async (id: string) => {
    try {
      await authFetch(`${API}/api/email/messages/${id}/read`, { method: "PATCH" });
      setMessages((prev) => prev.map((m) => m.id === id ? { ...m, is_read: true } : m));
      setDetail((prev) => prev && prev.id === id ? { ...prev, is_read: true } : prev);
    } catch { /* silent */ }
  }, []);

  // Bulk mark read
  const bulkMarkRead = useCallback(async () => {
    const ids = Array.from(checkedIds);
    await Promise.allSettled(ids.map((id) =>
      authFetch(`${API}/api/email/messages/${id}/read`, { method: "PATCH" })
    ));
    setMessages((prev) => prev.map((m) => checkedIds.has(m.id) ? { ...m, is_read: true } : m));
    setCheckedIds(new Set());
  }, [checkedIds]);

  // Sync
  const syncAccount = useCallback(async () => {
    if (!selectedAccountId) return;
    setSyncing(true);
    try {
      await authFetch(`${API}/api/email/accounts/${selectedAccountId}/sync`, { method: "POST" });
      await fetchMessages();
    } catch { /* silent */ } finally {
      setSyncing(false);
    }
  }, [selectedAccountId, fetchMessages]);

  // Checkbox toggle
  const toggleCheck = (id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const updateMessageAssignments = useCallback((messageId: string, assignments: AgentAssignmentSummary[]) => {
    setMessages((prev) => prev.map((message) => message.id === messageId ? { ...message, agent_assignments: assignments } : message));
    setDetail((prev) => prev && prev.id === messageId ? { ...prev, agent_assignments: assignments } : prev);
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  return (
    <div className="flex flex-col h-full bg-warroom-bg">
      {/* ── Top Bar ── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-warroom-border bg-warroom-surface/50">
        {/* Account selector */}
        <select
          value={selectedAccountId}
          onChange={(e) => { setSelectedAccountId(e.target.value); setPage(1); setSelectedId(null); setDetail(null); }}
          className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text focus:outline-none focus:ring-1 focus:ring-warroom-accent"
        >
          {accounts.length === 0 && <option value="">No accounts</option>}
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name || a.email}</option>
          ))}
        </select>

        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
          <input
            type="text"
            placeholder="Search emails…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-warroom-text placeholder:text-warroom-muted focus:outline-none focus:ring-1 focus:ring-warroom-accent"
          />
        </div>

        {/* Unread filter */}
        <button
          onClick={() => { setUnreadOnly((p) => !p); setPage(1); }}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            unreadOnly
              ? "bg-warroom-accent/15 text-warroom-accent border border-warroom-accent/30"
              : "bg-warroom-bg border border-warroom-border text-warroom-muted hover:text-warroom-text"
          }`}
        >
          <Filter size={14} />
          Unread
        </button>

        {/* Bulk actions */}
        {checkedIds.size > 0 && (
          <button
            onClick={bulkMarkRead}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-warroom-accent/15 text-warroom-accent border border-warroom-accent/30 hover:bg-warroom-accent/25 transition-colors"
          >
            <Check size={14} />
            Mark {checkedIds.size} read
          </button>
        )}

        {/* Sync */}
        <button
          onClick={syncAccount}
          disabled={syncing || !selectedAccountId}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-warroom-bg border border-warroom-border text-warroom-muted hover:text-warroom-text disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
          Sync
        </button>
      </div>

      {/* ── Two-pane body ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Message list */}
        <div className="w-[40%] border-r border-warroom-border flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-6">
                <Inbox size={48} className="text-warroom-muted/40 mb-4" />
                <p className="text-warroom-muted text-sm">
                  No emails yet — connect your email in Settings → Email &amp; Calendar
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  onClick={() => selectMessage(msg)}
                  className={`flex items-center gap-3 px-4 py-3 cursor-pointer border-b border-warroom-border/30 transition-colors ${
                    selectedId === msg.id
                      ? "bg-warroom-accent/10"
                      : "hover:bg-warroom-surface/60"
                  }`}
                >
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={checkedIds.has(msg.id)}
                    onChange={(e) => { e.stopPropagation(); toggleCheck(msg.id); }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-4 h-4 rounded border-warroom-border bg-warroom-bg text-warroom-accent focus:ring-warroom-accent flex-shrink-0"
                  />

                  {/* Unread dot */}
                  <div className="w-2 flex-shrink-0">
                    {!msg.is_read && (
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                    )}
                  </div>

                  {/* Avatar */}
                  <div className="w-8 h-8 rounded-full bg-warroom-accent/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-warroom-accent">
                      {avatarLetter(msg.from_name)}
                    </span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`text-sm truncate ${!msg.is_read ? "font-semibold text-warroom-text" : "text-warroom-text/80"}`}>
                        {msg.from_name || msg.from_email}
                      </span>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {msg.agent_assignments.length > 0 && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-warroom-accent/15 px-1.5 py-0.5 text-[10px] text-warroom-accent">
                            <Bot size={10} />
                            {msg.agent_assignments.length}
                          </span>
                        )}
                        <span className="text-xs text-warroom-muted">{relativeDate(msg.date)}</span>
                      </div>
                    </div>
                    <p className={`text-sm truncate ${!msg.is_read ? "font-medium text-warroom-text/90" : "text-warroom-muted"}`}>
                      {msg.subject}
                    </p>
                    <p className="text-xs text-warroom-muted truncate">{msg.snippet}</p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination */}
          {!loading && totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-2 border-t border-warroom-border bg-warroom-surface/30">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="flex items-center gap-1 px-2 py-1 rounded text-sm text-warroom-muted hover:text-warroom-text disabled:opacity-30 transition-colors"
              >
                <ChevronLeft size={14} /> Prev
              </button>
              <span className="text-xs text-warroom-muted">
                Page {page} of {totalPages} · {total} emails
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="flex items-center gap-1 px-2 py-1 rounded text-sm text-warroom-muted hover:text-warroom-text disabled:opacity-30 transition-colors"
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Right: Message detail */}
        <div className="w-[60%] flex flex-col overflow-hidden">
          {!detail ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <Mail size={48} className="text-warroom-muted/30 mb-4" />
              <p className="text-warroom-muted text-sm">Select an email to read</p>
            </div>
          ) : detailLoading ? (
            <div className="p-6 space-y-4 animate-pulse">
              <div className="h-6 bg-warroom-border/40 rounded w-2/3" />
              <div className="h-4 bg-warroom-border/40 rounded w-1/2" />
              <div className="h-4 bg-warroom-border/40 rounded w-1/3" />
              <div className="h-px bg-warroom-border/40 my-4" />
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-3 bg-warroom-border/40 rounded" style={{ width: `${70 + Math.random() * 30}%` }} />
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Detail header */}
              <div className="px-6 py-4 border-b border-warroom-border space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-lg font-semibold text-warroom-text leading-tight">
                    {detail.subject || "(no subject)"}
                  </h2>
                  {!detail.is_read && (
                    <button
                      onClick={() => markAsRead(detail.id)}
                      className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs bg-warroom-accent/15 text-warroom-accent border border-warroom-accent/30 hover:bg-warroom-accent/25 transition-colors flex-shrink-0"
                    >
                      <Check size={12} /> Mark as read
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-warroom-accent/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-bold text-warroom-accent">
                      {avatarLetter(detail.from_name)}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-warroom-text">
                      {detail.from_name}{" "}
                      <span className="text-warroom-muted font-normal">&lt;{detail.from_email}&gt;</span>
                    </p>
                    <p className="text-xs text-warroom-muted">
                      To: {detail.to?.join(", ") || "—"} · {fullDate(detail.date)}
                    </p>
                  </div>
                </div>
                <EntityAssignmentControl
                  entityType="email_message"
                  entityId={detail.id}
                  title={detail.subject || "Email message"}
                  initialAssignments={detail.agent_assignments}
                  onAssignmentsChange={(assignments) => updateMessageAssignments(detail.id, assignments)}
                  emptyLabel="No AI agents assigned to this message yet."
                />
              </div>

              {/* Detail body */}
              <div className="flex-1 overflow-y-auto px-6 py-4">
                {detail.body_html ? (
                  <div
                    className="prose prose-invert prose-sm max-w-none text-warroom-text/90 [&_a]:text-warroom-accent [&_img]:max-w-full [&_img]:h-auto"
                    dangerouslySetInnerHTML={{ __html: sanitizeHTML(detail.body_html) }}
                  />
                ) : detail.body_text ? (
                  <pre className="whitespace-pre-wrap text-sm text-warroom-text/90 font-sans leading-relaxed">
                    {detail.body_text}
                  </pre>
                ) : (
                  <p className="text-warroom-muted text-sm italic">No content available</p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
