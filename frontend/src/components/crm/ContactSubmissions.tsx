"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Inbox, Search, Filter, ChevronDown, ChevronRight, Loader2,
  MessageSquare, Clock, User, X, RefreshCw,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────── */

interface Submission {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  message: string;
  status: SubmissionStatus;
  assigned_to: string | null;
  notes: string | null;
  created_at: string;
}

interface CRMUser {
  id: number;
  name: string;
}

interface PaginatedResponse {
  submissions: Submission[];
  total: number;
  page: number;
  limit: number;
}

type SubmissionStatus = "new" | "read" | "in_progress" | "replied" | "closed" | "spam";

/* ── Constants ─────────────────────────────────────────────── */

const STATUS_CONFIG: Record<SubmissionStatus, { label: string; color: string; dot: string }> = {
  new:         { label: "New",         color: "bg-blue-500/20 text-blue-400 border-blue-500/30",    dot: "bg-blue-400" },
  read:        { label: "Read",        color: "bg-gray-500/20 text-gray-400 border-gray-500/30",    dot: "bg-gray-400" },
  in_progress: { label: "In Progress", color: "bg-amber-500/20 text-amber-400 border-amber-500/30", dot: "bg-amber-400" },
  replied:     { label: "Replied",     color: "bg-green-500/20 text-green-400 border-green-500/30",  dot: "bg-green-400" },
  closed:      { label: "Closed",      color: "bg-slate-500/20 text-slate-400 border-slate-500/30",  dot: "bg-slate-400" },
  spam:        { label: "Spam",        color: "bg-red-500/20 text-red-400 border-red-500/30",       dot: "bg-red-400" },
};

const ALL_STATUSES = Object.keys(STATUS_CONFIG) as SubmissionStatus[];
const PER_PAGE = 25;
const REFRESH_INTERVAL_MS = 60_000;

/* ── Helpers ───────────────────────────────────────────────── */

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}

/* ── Component ─────────────────────────────────────────────── */

export default function ContactSubmissions() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [users, setUsers] = useState<CRMUser[]>([]);
  const [patchingId, setPatchingId] = useState<number | null>(null);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const notesRef = useRef<HTMLTextAreaElement | null>(null);

  /* ── Data fetching ──────────────────────────────────────── */

  const fetchSubmissions = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (searchQuery) params.set("search", searchQuery);
      params.set("page", String(page));
      params.set("limit", String(PER_PAGE));

      const res = await authFetch(`${API}/api/contact-submissions?${params}`);
      if (res.ok) {
        const data: PaginatedResponse = await res.json();
        setSubmissions(data.submissions);
        setTotal(data.total);
      }
    } catch (err) {
      console.error("Failed to fetch submissions:", err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchQuery, page]);

  const fetchUsers = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/crm/users`);
      if (res.ok) {
        const data: CRMUser[] = await res.json();
        setUsers(data);
      }
    } catch (err) {
      console.error("Failed to fetch users:", err);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);
  useEffect(() => { fetchSubmissions(); }, [fetchSubmissions]);

  // Auto-refresh
  useEffect(() => {
    refreshTimer.current = setInterval(() => fetchSubmissions(true), REFRESH_INTERVAL_MS);
    return () => { if (refreshTimer.current) clearInterval(refreshTimer.current); };
  }, [fetchSubmissions]);

  // Reset page on filter change
  useEffect(() => { setPage(1); }, [statusFilter, searchQuery]);

  /* ── Patch helpers ──────────────────────────────────────── */

  const patchSubmission = async (id: number, body: Partial<Pick<Submission, "status" | "assigned_to" | "notes">>) => {
    setPatchingId(id);
    try {
      const res = await authFetch(`${API}/api/contact-submissions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const updated: Submission = await res.json();
        setSubmissions((prev) => prev.map((s) => (s.id === id ? { ...s, ...updated } : s)));
      }
    } catch (err) {
      console.error("Failed to patch submission:", err);
    } finally {
      setPatchingId(null);
    }
  };

  /* ── Derived ────────────────────────────────────────────── */

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));

  /* ── Render ─────────────────────────────────────────────── */

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-500/15 flex items-center justify-center">
            <Inbox size={18} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-warroom-text">Contact Submissions</h1>
            <p className="text-xs text-warroom-muted">{total} submission{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <button
          onClick={() => fetchSubmissions()}
          className="p-2 rounded-lg text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/30 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-warroom-border/60">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
          <input
            type="text"
            placeholder="Search name or email…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-9 pl-9 pr-3 rounded-lg bg-warroom-bg border border-warroom-border text-sm text-warroom-text placeholder:text-warroom-muted focus:outline-none focus:border-warroom-accent/50 transition-colors"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-warroom-muted hover:text-warroom-text">
              <X size={14} />
            </button>
          )}
        </div>

        {/* Status filter */}
        <div className="relative">
          <button
            onClick={() => setShowStatusDropdown((v) => !v)}
            className="h-9 px-3 rounded-lg bg-warroom-bg border border-warroom-border text-sm text-warroom-text flex items-center gap-2 hover:border-warroom-accent/40 transition-colors"
          >
            <Filter size={14} className="text-warroom-muted" />
            <span>{statusFilter ? STATUS_CONFIG[statusFilter as SubmissionStatus].label : "All Statuses"}</span>
            <ChevronDown size={14} className="text-warroom-muted" />
          </button>
          {showStatusDropdown && (
            <div className="absolute top-full mt-1 left-0 z-50 bg-warroom-surface border border-warroom-border rounded-xl shadow-2xl shadow-black/40 py-1.5 min-w-[160px]">
              <button
                onClick={() => { setStatusFilter(""); setShowStatusDropdown(false); }}
                className={`w-full text-left px-4 py-2 text-sm transition-colors ${!statusFilter ? "text-warroom-accent bg-warroom-accent/10" : "text-warroom-text/70 hover:text-warroom-text hover:bg-warroom-border/30"}`}
              >
                All Statuses
              </button>
              {ALL_STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setShowStatusDropdown(false); }}
                  className={`w-full text-left px-4 py-2 text-sm flex items-center gap-2 transition-colors ${statusFilter === s ? "text-warroom-accent bg-warroom-accent/10" : "text-warroom-text/70 hover:text-warroom-text hover:bg-warroom-border/30"}`}
                >
                  <span className={`w-2 h-2 rounded-full ${STATUS_CONFIG[s].dot}`} />
                  {STATUS_CONFIG[s].label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {loading && submissions.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 size={24} className="animate-spin text-warroom-muted" />
          </div>
        ) : submissions.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-14 h-14 rounded-2xl bg-warroom-border/30 flex items-center justify-center mb-4">
              <Inbox size={28} className="text-warroom-muted" />
            </div>
            <p className="text-warroom-text font-medium mb-1">No submissions yet</p>
            <p className="text-sm text-warroom-muted">Connect your contact form webhook to start receiving submissions.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-warroom-surface z-10">
              <tr className="border-b border-warroom-border/60 text-warroom-muted text-xs uppercase tracking-wider">
                <th className="text-left py-3 px-6 font-medium">Name</th>
                <th className="text-left py-3 px-4 font-medium">Email</th>
                <th className="text-left py-3 px-4 font-medium">Phone</th>
                <th className="text-left py-3 px-4 font-medium">Message</th>
                <th className="text-left py-3 px-4 font-medium">Status</th>
                <th className="text-left py-3 px-4 font-medium">Submitted</th>
                <th className="text-left py-3 px-4 font-medium">Assigned To</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => {
                const isExpanded = expandedId === sub.id;
                const cfg = STATUS_CONFIG[sub.status] || STATUS_CONFIG.new;

                return (
                  <SubmissionRow
                    key={sub.id}
                    submission={sub}
                    isExpanded={isExpanded}
                    statusConfig={cfg}
                    users={users}
                    patching={patchingId === sub.id}
                    onToggle={() => setExpandedId(isExpanded ? null : sub.id)}
                    onPatch={(body) => patchSubmission(sub.id, body)}
                  />
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-3 border-t border-warroom-border/60">
          <p className="text-xs text-warroom-muted">
            Page {page} of {totalPages} · {total} total
          </p>
          <div className="flex items-center gap-1.5">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-warroom-bg border border-warroom-border text-warroom-text disabled:opacity-30 disabled:cursor-not-allowed hover:bg-warroom-border/40 transition-colors"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-warroom-bg border border-warroom-border text-warroom-text disabled:opacity-30 disabled:cursor-not-allowed hover:bg-warroom-border/40 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Row subcomponent ──────────────────────────────────────── */

interface SubmissionRowProps {
  submission: Submission;
  isExpanded: boolean;
  statusConfig: { label: string; color: string; dot: string };
  users: CRMUser[];
  patching: boolean;
  onToggle: () => void;
  onPatch: (body: Partial<Pick<Submission, "status" | "assigned_to" | "notes">>) => void;
}

function SubmissionRow({ submission, isExpanded, statusConfig, users, patching, onToggle, onPatch }: SubmissionRowProps) {
  const [localNotes, setLocalNotes] = useState(submission.notes || "");
  const [statusOpen, setStatusOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const statusDropdownRef = useRef<HTMLDivElement>(null);
  const assignDropdownRef = useRef<HTMLDivElement>(null);

  // Sync local notes when submission updates externally
  useEffect(() => { setLocalNotes(submission.notes || ""); }, [submission.notes]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (statusDropdownRef.current && !statusDropdownRef.current.contains(e.target as Node)) setStatusOpen(false);
      if (assignDropdownRef.current && !assignDropdownRef.current.contains(e.target as Node)) setAssignOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleNotesBlur = () => {
    const trimmed = localNotes.trim();
    if (trimmed !== (submission.notes || "").trim()) {
      onPatch({ notes: trimmed });
    }
  };

  const assignedUser = users.find((u) => String(u.id) === submission.assigned_to || u.name === submission.assigned_to);

  return (
    <>
      {/* Main row */}
      <tr
        onClick={onToggle}
        className={`border-b border-warroom-border/30 cursor-pointer transition-colors ${
          isExpanded ? "bg-warroom-accent/5" : "hover:bg-warroom-border/20"
        }`}
      >
        <td className="py-3 px-6">
          <div className="flex items-center gap-2">
            {isExpanded ? <ChevronDown size={14} className="text-warroom-muted flex-shrink-0" /> : <ChevronRight size={14} className="text-warroom-muted flex-shrink-0" />}
            <span className="font-medium text-warroom-text">{submission.name}</span>
          </div>
        </td>
        <td className="py-3 px-4 text-warroom-muted">{submission.email}</td>
        <td className="py-3 px-4 text-warroom-muted">{submission.phone || "—"}</td>
        <td className="py-3 px-4 text-warroom-muted max-w-[200px]">
          <span className="block truncate">{truncate(submission.message, 60)}</span>
        </td>
        <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
          <div className="relative" ref={statusDropdownRef}>
            <button
              onClick={() => setStatusOpen((v) => !v)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${statusConfig.color} transition-colors hover:opacity-80`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${statusConfig.dot}`} />
              {statusConfig.label}
              <ChevronDown size={12} />
            </button>
            {statusOpen && (
              <div className="absolute top-full mt-1 left-0 z-50 bg-warroom-surface border border-warroom-border rounded-xl shadow-2xl shadow-black/40 py-1.5 min-w-[140px]">
                {ALL_STATUSES.map((s) => (
                  <button
                    key={s}
                    onClick={() => { onPatch({ status: s }); setStatusOpen(false); }}
                    className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors ${
                      submission.status === s ? "text-warroom-accent bg-warroom-accent/10" : "text-warroom-text/70 hover:text-warroom-text hover:bg-warroom-border/30"
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${STATUS_CONFIG[s].dot}`} />
                    {STATUS_CONFIG[s].label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </td>
        <td className="py-3 px-4">
          <div className="flex items-center gap-1.5 text-warroom-muted text-xs">
            <Clock size={12} />
            {relativeTime(submission.created_at)}
          </div>
        </td>
        <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
          <div className="relative" ref={assignDropdownRef}>
            <button
              onClick={() => setAssignOpen((v) => !v)}
              className="inline-flex items-center gap-1.5 text-xs text-warroom-muted hover:text-warroom-text transition-colors"
            >
              <User size={12} />
              <span>{assignedUser?.name || "Unassigned"}</span>
              <ChevronDown size={12} />
            </button>
            {assignOpen && (
              <div className="absolute top-full mt-1 right-0 z-50 bg-warroom-surface border border-warroom-border rounded-xl shadow-2xl shadow-black/40 py-1.5 min-w-[140px]">
                <button
                  onClick={() => { onPatch({ assigned_to: "" }); setAssignOpen(false); }}
                  className="w-full text-left px-3 py-2 text-xs text-warroom-text/70 hover:text-warroom-text hover:bg-warroom-border/30 transition-colors"
                >
                  Unassigned
                </button>
                {users.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => { onPatch({ assigned_to: String(u.id) }); setAssignOpen(false); }}
                    className={`w-full text-left px-3 py-2 text-xs transition-colors ${
                      String(u.id) === submission.assigned_to ? "text-warroom-accent bg-warroom-accent/10" : "text-warroom-text/70 hover:text-warroom-text hover:bg-warroom-border/30"
                    }`}
                  >
                    {u.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </td>
      </tr>

      {/* Expanded detail */}
      {isExpanded && (
        <tr className="bg-warroom-accent/5">
          <td colSpan={7} className="px-6 py-4">
            <div className="grid grid-cols-2 gap-6">
              {/* Full message */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare size={14} className="text-warroom-muted" />
                  <span className="text-xs font-medium text-warroom-muted uppercase tracking-wider">Full Message</span>
                </div>
                <div className="bg-warroom-bg rounded-lg p-4 border border-warroom-border/50 text-sm text-warroom-text whitespace-pre-wrap min-h-[80px]">
                  {submission.message}
                </div>
              </div>

              {/* Notes */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-warroom-muted uppercase tracking-wider">Notes</span>
                  {patching && <Loader2 size={12} className="animate-spin text-warroom-accent" />}
                </div>
                <textarea
                  value={localNotes}
                  onChange={(e) => setLocalNotes(e.target.value)}
                  onBlur={handleNotesBlur}
                  placeholder="Add notes…"
                  className="w-full bg-warroom-bg rounded-lg p-4 border border-warroom-border/50 text-sm text-warroom-text placeholder:text-warroom-muted focus:outline-none focus:border-warroom-accent/50 resize-none min-h-[80px] transition-colors"
                  rows={4}
                />
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
