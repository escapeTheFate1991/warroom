"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Bot,
  Building2,
  Calendar,
  ChevronLeft,
  Filter,
  Loader2,
  Mail,
  MessageSquare,
  Phone,
  Search,
  User,
  X,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */

interface CommRecord {
  id: string;
  type: "call" | "sms" | "email";
  direction: "inbound" | "outbound";
  status: string;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  organization: string | null;
  employee: string | null;
  agent: string | null;
  subject: string | null;
  summary: string | null;
  transcript: string | null;
  pain_points: string | null;
  services: string | null;
  schedule_pref: string | null;
  duration_seconds: number | null;
  occurred_at: string;
  metadata: Record<string, string | number | boolean | null>;
}

/* ── Constants ─────────────────────────────────────────── */

const TYPE_ICON: Record<string, typeof Phone> = { call: Phone, sms: MessageSquare, email: Mail };
const TYPE_COLOR: Record<string, string> = {
  call: "text-green-400",
  sms: "text-cyan-400",
  email: "text-blue-400",
};
const STATUS_BADGE: Record<string, string> = {
  completed: "bg-green-500/15 text-green-400",
  sent: "bg-cyan-500/15 text-cyan-400",
  delivered: "bg-green-500/15 text-green-400",
  failed: "bg-red-500/15 text-red-400",
  "no-answer": "bg-yellow-500/15 text-yellow-400",
  bounced: "bg-red-500/15 text-red-400",
  initiated: "bg-blue-500/15 text-blue-400",
  queued: "bg-gray-500/15 text-gray-400",
};

function formatDuration(seconds: number | null) {
  if (!seconds) return null;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return days === 1 ? "Yesterday" : `${days}d ago`;
}

/* ── Call Intake Sub-Component ──────────────────────────── */

function CallIntakeSection({ record }: { record: CommRecord }) {
  if (record.type !== "call") return null;
  if (!record.pain_points && !record.services && !record.schedule_pref) return null;
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider">Call Intake</h4>
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 space-y-3">
        {record.pain_points && (
          <div>
            <p className="text-[10px] font-medium text-warroom-muted uppercase mb-1">Pain Points</p>
            <p className="text-sm text-warroom-text">{record.pain_points}</p>
          </div>
        )}
        {record.services && (
          <div>
            <p className="text-[10px] font-medium text-warroom-muted uppercase mb-1">Services Interested In</p>
            <p className="text-sm text-warroom-text">{record.services}</p>
          </div>
        )}
        {record.schedule_pref && (
          <div>
            <p className="text-[10px] font-medium text-warroom-muted uppercase mb-1">Scheduling Preference</p>
            <p className="text-sm text-warroom-text">{record.schedule_pref}</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────── */

export default function CommunicationsConsole() {
  const [records, setRecords] = useState<CommRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<CommRecord | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [directionFilter, setDirectionFilter] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(t);
  }, [search]);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (debouncedSearch) params.set("search", debouncedSearch);
      if (typeFilter) params.set("type", typeFilter);
      if (directionFilter) params.set("direction", directionFilter);
      params.set("per_page", "100");

      const res = await authFetch(`${API}/api/comms/logs?${params}`);
      if (res.ok) {
        const data = await res.json();
        setRecords(data.items || []);
        setTotal(data.total || 0);
      }
    } catch (err) {
      console.error("Failed to load comms:", err);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, typeFilter, directionFilter]);

  useEffect(() => { loadRecords(); }, [loadRecords]);

  const clearFilters = () => {
    setSearch("");
    setTypeFilter("");
    setDirectionFilter("");
    setSelected(null);
  };

  const hasFilters = search || typeFilter || directionFilter;

  /* ── Render ── */

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 shrink-0">
        <Phone size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Communications</h2>
        <span className="text-xs text-warroom-muted">{total} records</span>
        <div className="flex-1" />
        <button onClick={() => setShowFilters(!showFilters)} className={`p-1.5 rounded-lg transition ${showFilters ? "bg-warroom-accent/20 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text"}`}>
          <Filter size={14} />
        </button>
      </div>

      {/* Search + Filters */}
      <div className="border-b border-warroom-border px-6 py-3 space-y-3 shrink-0">
        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transcripts, contacts, messages..."
            className="w-full bg-warroom-bg border border-warroom-border rounded-xl pl-9 pr-9 py-2 text-sm text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted hover:text-warroom-text">
              <X size={12} />
            </button>
          )}
        </div>

        {/* Filter chips */}
        {showFilters && (
          <div className="flex flex-wrap items-center gap-2">
            {/* Type */}
            {(["call", "sms", "email"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(typeFilter === t ? "" : t)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  typeFilter === t ? "bg-warroom-accent/20 text-warroom-accent border border-warroom-accent/30" : "bg-warroom-surface border border-warroom-border text-warroom-muted hover:text-warroom-text"
                }`}
              >
                {t === "call" && <Phone size={11} />}
                {t === "sms" && <MessageSquare size={11} />}
                {t === "email" && <Mail size={11} />}
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}

            <div className="w-px h-5 bg-warroom-border" />

            {/* Direction */}
            {(["inbound", "outbound"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDirectionFilter(directionFilter === d ? "" : d)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  directionFilter === d ? "bg-warroom-accent/20 text-warroom-accent border border-warroom-accent/30" : "bg-warroom-surface border border-warroom-border text-warroom-muted hover:text-warroom-text"
                }`}
              >
                {d === "inbound" ? <ArrowDownLeft size={11} /> : <ArrowUpRight size={11} />}
                {d.charAt(0).toUpperCase() + d.slice(1)}
              </button>
            ))}

            {hasFilters && (
              <>
                <div className="w-px h-5 bg-warroom-border" />
                <button onClick={clearFilters} className="text-[10px] text-warroom-muted hover:text-warroom-text flex items-center gap-1">
                  <X size={10} /> Clear all
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Content: List + Detail */}
      <div className="flex-1 flex overflow-hidden">
        {/* List */}
        <div className={`${selected ? "hidden md:block md:w-[380px] md:border-r md:border-warroom-border" : "w-full"} overflow-y-auto`}>
          {loading ? (
            <div className="flex items-center justify-center py-20 text-warroom-muted">
              <Loader2 size={20} className="animate-spin mr-2" />
              <span className="text-sm">Loading communications...</span>
            </div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
              <Phone size={40} className="mb-3 opacity-20" />
              <p className="text-sm">No communications found</p>
              {hasFilters && (
                <button onClick={clearFilters} className="mt-2 text-xs text-warroom-accent hover:underline">Clear filters</button>
              )}
            </div>
          ) : (
            <div>
              {records.map((r) => {
                const Icon = TYPE_ICON[r.type] || Phone;
                const isActive = selected?.id === r.id;
                return (
                  <button
                    key={r.id}
                    onClick={() => setSelected(r)}
                    className={`w-full text-left px-5 py-4 border-b border-warroom-border/50 hover:bg-warroom-surface/50 transition ${
                      isActive ? "bg-warroom-accent/5 border-l-2 border-l-warroom-accent" : ""
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Icon */}
                      <div className={`mt-0.5 ${TYPE_COLOR[r.type] || "text-warroom-muted"}`}>
                        <Icon size={16} />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-medium text-warroom-text truncate">
                            {r.contact_name || r.contact_phone || r.contact_email || "Unknown"}
                          </span>
                          {r.direction === "inbound" ? (
                            <ArrowDownLeft size={10} className="text-blue-400 shrink-0" />
                          ) : (
                            <ArrowUpRight size={10} className="text-green-400 shrink-0" />
                          )}
                          <span className="text-[10px] text-warroom-muted ml-auto shrink-0">
                            {relativeTime(r.occurred_at)}
                          </span>
                        </div>
                        {r.subject && (
                          <p className="text-xs text-warroom-text/80 truncate mb-0.5">{r.subject}</p>
                        )}
                        <p className="text-xs text-warroom-muted truncate">
                          {r.summary || "No content"}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${STATUS_BADGE[r.status] || "bg-warroom-border/20 text-warroom-muted"}`}>
                            {r.status}
                          </span>
                          {r.organization && (
                            <span className="text-[10px] text-warroom-muted flex items-center gap-1">
                              <Building2 size={9} /> {r.organization}
                            </span>
                          )}
                          {r.agent && (
                            <span className="text-[10px] text-warroom-muted flex items-center gap-1">
                              <Bot size={9} /> {r.agent}
                            </span>
                          )}
                          {r.duration_seconds && (
                            <span className="text-[10px] text-warroom-muted">
                              {formatDuration(r.duration_seconds)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selected && (
          <div className="flex-1 overflow-y-auto bg-warroom-bg">
            {/* Detail Header */}
            <div className="sticky top-0 bg-warroom-bg border-b border-warroom-border px-6 py-3 flex items-center gap-3 z-10">
              <button onClick={() => setSelected(null)} className="md:hidden p-1.5 text-warroom-muted hover:text-warroom-text">
                <ChevronLeft size={18} />
              </button>
              <div className={TYPE_COLOR[selected.type]}>
                {selected.type === "call" && <Phone size={18} />}
                {selected.type === "sms" && <MessageSquare size={18} />}
                {selected.type === "email" && <Mail size={18} />}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-warroom-text truncate">
                  {selected.contact_name || selected.contact_phone || "Unknown Contact"}
                </h3>
                <p className="text-xs text-warroom-muted">
                  {selected.type.toUpperCase()} · {selected.direction} · {new Date(selected.occurred_at).toLocaleString()}
                </p>
              </div>
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_BADGE[selected.status] || "bg-warroom-border/20 text-warroom-muted"}`}>
                {selected.status}
              </span>
            </div>

            <div className="p-6 space-y-6">
              {/* Contact Info */}
              <div className="grid grid-cols-2 gap-4">
                {selected.contact_phone && (
                  <div className="flex items-center gap-2 text-sm">
                    <Phone size={13} className="text-warroom-muted" />
                    <span className="text-warroom-text">{selected.contact_phone}</span>
                  </div>
                )}
                {selected.contact_email && (
                  <div className="flex items-center gap-2 text-sm">
                    <Mail size={13} className="text-warroom-muted" />
                    <span className="text-warroom-accent">{selected.contact_email}</span>
                  </div>
                )}
                {selected.organization && (
                  <div className="flex items-center gap-2 text-sm">
                    <Building2 size={13} className="text-warroom-muted" />
                    <span className="text-warroom-text">{selected.organization}</span>
                  </div>
                )}
                {selected.agent && (
                  <div className="flex items-center gap-2 text-sm">
                    <Bot size={13} className="text-warroom-muted" />
                    <span className="text-warroom-text">{selected.agent}</span>
                  </div>
                )}
                {selected.duration_seconds != null && selected.duration_seconds > 0 && (
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar size={13} className="text-warroom-muted" />
                    <span className="text-warroom-text">{formatDuration(selected.duration_seconds)}</span>
                  </div>
                )}
              </div>

              {/* Call Intake Details */}
              <CallIntakeSection record={selected} />

              {/* Transcript / Content */}
              {selected.transcript && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider">
                    {selected.type === "call" ? "Transcript" : selected.type === "email" ? "Email Body" : "Message"}
                  </h4>
                  <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                    <p className="text-sm text-warroom-text whitespace-pre-wrap leading-relaxed">{selected.transcript}</p>
                  </div>
                </div>
              )}

              {/* Original Message (from submission) */}
              {selected.metadata?.submission_message && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider">Original Form Submission</h4>
                  <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                    <p className="text-sm text-warroom-text whitespace-pre-wrap leading-relaxed">
                      {String(selected.metadata.submission_message)}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
