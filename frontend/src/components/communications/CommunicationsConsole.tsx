"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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

interface ContactGroup {
  key: string;
  name: string;
  phone: string | null;
  email: string | null;
  organization: string | null;
  records: CommRecord[];
  lastActivity: string;
  callCount: number;
  smsCount: number;
  emailCount: number;
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

function contactKey(r: CommRecord): string {
  // Group by name first, then phone, then email
  return r.contact_name?.toLowerCase().trim()
    || r.contact_phone?.replace(/\D/g, "")
    || r.contact_email?.toLowerCase().trim()
    || `unknown-${r.id}`;
}

/* ── Call Intake Sub-Component ──────────────────────────── */

function CallIntakeSection({ record }: { record: CommRecord }) {
  if (record.type !== "call") return null;
  if (!record.pain_points && !record.services && !record.schedule_pref) return null;
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-3 sm:p-4 space-y-2.5">
      <p className="text-[10px] font-semibold text-warroom-muted uppercase tracking-wider">Call Intake</p>
      {record.pain_points && (
        <div>
          <p className="text-[10px] font-medium text-warroom-muted uppercase mb-0.5">Pain Points</p>
          <p className="text-xs sm:text-sm text-warroom-text">{record.pain_points}</p>
        </div>
      )}
      {record.services && (
        <div>
          <p className="text-[10px] font-medium text-warroom-muted uppercase mb-0.5">Services</p>
          <p className="text-xs sm:text-sm text-warroom-text">{record.services}</p>
        </div>
      )}
      {record.schedule_pref && (
        <div>
          <p className="text-[10px] font-medium text-warroom-muted uppercase mb-0.5">Scheduling</p>
          <p className="text-xs sm:text-sm text-warroom-text">{record.schedule_pref}</p>
        </div>
      )}
    </div>
  );
}

/* ── Record Card (in contact detail thread) ─────────────── */

function RecordCard({ record }: { record: CommRecord }) {
  const Icon = TYPE_ICON[record.type] || Phone;
  const isInbound = record.direction === "inbound";

  return (
    <div className={`flex gap-3 ${isInbound ? "" : "flex-row-reverse"}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isInbound ? "bg-blue-500/10" : "bg-green-500/10"
      }`}>
        {isInbound ? <ArrowDownLeft size={14} className="text-blue-400" /> : <ArrowUpRight size={14} className="text-green-400" />}
      </div>

      <div className={`flex-1 min-w-0 max-w-[85%] ${isInbound ? "" : "flex flex-col items-end"}`}>
        <div className={`bg-warroom-surface border border-warroom-border rounded-xl p-3 sm:p-4 ${
          isInbound ? "rounded-tl-sm" : "rounded-tr-sm"
        }`}>
          {/* Header */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <Icon size={12} className={TYPE_COLOR[record.type]} />
            <span className="text-[10px] sm:text-xs font-semibold text-warroom-text capitalize">{record.type}</span>
            {record.subject && (
              <span className="text-[10px] sm:text-xs text-warroom-text/80 truncate">— {record.subject}</span>
            )}
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ml-auto ${STATUS_BADGE[record.status] || "bg-warroom-border/20 text-warroom-muted"}`}>
              {record.status}
            </span>
          </div>

          {/* Summary / Content */}
          {(record.summary || record.transcript) && (
            <p className="text-xs sm:text-sm text-warroom-text/90 leading-relaxed whitespace-pre-wrap">
              {record.summary || record.transcript}
            </p>
          )}

          {/* Call Intake */}
          {record.type === "call" && (record.pain_points || record.services || record.schedule_pref) && (
            <div className="mt-3">
              <CallIntakeSection record={record} />
            </div>
          )}

          {/* Original form submission */}
          {record.metadata?.submission_message && (
            <div className="mt-3 pt-3 border-t border-warroom-border/50">
              <p className="text-[10px] font-medium text-warroom-muted uppercase mb-1">Form Submission</p>
              <p className="text-xs text-warroom-text/80 whitespace-pre-wrap">{String(record.metadata.submission_message)}</p>
            </div>
          )}

          {/* Footer meta */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {record.duration_seconds != null && record.duration_seconds > 0 && (
              <span className="text-[10px] text-warroom-muted">{formatDuration(record.duration_seconds)}</span>
            )}
            {record.agent && (
              <span className="text-[10px] text-warroom-muted flex items-center gap-1">
                <Bot size={9} /> {record.agent}
              </span>
            )}
          </div>
        </div>

        <p className="text-[10px] text-warroom-muted mt-1 px-1">
          {new Date(record.occurred_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────── */

export default function CommunicationsConsole() {
  const [records, setRecords] = useState<CommRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [selectedContact, setSelectedContact] = useState<string | null>(null);

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
      params.set("per_page", "200");

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

  // Group records by contact
  const contactGroups: ContactGroup[] = useMemo(() => {
    const map = new Map<string, ContactGroup>();

    for (const r of records) {
      const key = contactKey(r);
      if (!map.has(key)) {
        map.set(key, {
          key,
          name: r.contact_name || r.contact_phone || r.contact_email || "Unknown",
          phone: r.contact_phone,
          email: r.contact_email,
          organization: r.organization,
          records: [],
          lastActivity: r.occurred_at,
          callCount: 0,
          smsCount: 0,
          emailCount: 0,
        });
      }
      const group = map.get(key)!;
      group.records.push(r);
      if (r.type === "call") group.callCount++;
      else if (r.type === "sms") group.smsCount++;
      else if (r.type === "email") group.emailCount++;
      // Update latest activity
      if (new Date(r.occurred_at) > new Date(group.lastActivity)) {
        group.lastActivity = r.occurred_at;
      }
      // Fill in missing contact info from other records
      if (!group.phone && r.contact_phone) group.phone = r.contact_phone;
      if (!group.email && r.contact_email) group.email = r.contact_email;
      if (!group.organization && r.organization) group.organization = r.organization;
      // Prefer actual name over phone/email
      if (r.contact_name && group.name === (group.phone || group.email || "Unknown")) {
        group.name = r.contact_name;
      }
    }

    // Sort groups: most recent activity first
    return Array.from(map.values()).sort(
      (a, b) => new Date(b.lastActivity).getTime() - new Date(a.lastActivity).getTime()
    );
  }, [records]);

  const activeGroup = contactGroups.find(g => g.key === selectedContact) || null;

  const clearFilters = () => {
    setSearch("");
    setTypeFilter("");
    setDirectionFilter("");
    setSelectedContact(null);
  };

  const hasFilters = search || typeFilter || directionFilter;

  /* ── Render ── */

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-warroom-border flex items-center px-3 sm:px-6 py-2 sm:py-0 sm:h-14 gap-2 sm:gap-3 shrink-0">
        {activeGroup && (
          <button onClick={() => setSelectedContact(null)} className="md:hidden p-1 text-warroom-muted hover:text-warroom-text">
            <ChevronLeft size={18} />
          </button>
        )}
        <Phone size={16} className="text-warroom-accent shrink-0" />
        <h2 className="text-sm font-semibold truncate">
          {activeGroup ? activeGroup.name : "Communications"}
        </h2>
        <span className="text-[10px] sm:text-xs text-warroom-muted shrink-0">
          {activeGroup ? `${activeGroup.records.length} interactions` : `${contactGroups.length} contacts · ${total} records`}
        </span>
        <div className="flex-1" />
        {!activeGroup && (
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-1.5 rounded-lg transition ${showFilters ? "bg-warroom-accent/20 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text"}`}
          >
            <Filter size={14} />
          </button>
        )}
      </div>

      {/* Search + Filters (only visible on contact list view) */}
      {!activeGroup && (
        <div className="border-b border-warroom-border px-3 sm:px-6 py-2 sm:py-3 space-y-2 sm:space-y-3 shrink-0">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search contacts, transcripts, messages..."
              className="w-full bg-warroom-bg border border-warroom-border rounded-xl pl-9 pr-9 py-2 text-sm text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted hover:text-warroom-text">
                <X size={12} />
              </button>
            )}
          </div>

          {showFilters && (
            <div className="flex flex-wrap items-center gap-2">
              {(["call", "sms", "email"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeFilter(typeFilter === t ? "" : t)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
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

              {(["inbound", "outbound"] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDirectionFilter(directionFilter === d ? "" : d)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
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
                    <X size={10} /> Clear
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Content: Contacts List + Contact Detail */}
      <div className="flex-1 flex overflow-hidden">
        {/* Contact List */}
        <div className={`${selectedContact ? "hidden md:block md:w-[340px] lg:w-[380px] md:border-r md:border-warroom-border" : "w-full"} overflow-y-auto`}>
          {loading ? (
            <div className="flex items-center justify-center py-20 text-warroom-muted">
              <Loader2 size={20} className="animate-spin mr-2" />
              <span className="text-sm">Loading...</span>
            </div>
          ) : contactGroups.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
              <Phone size={40} className="mb-3 opacity-20" />
              <p className="text-sm">No communications found</p>
              {hasFilters && (
                <button onClick={clearFilters} className="mt-2 text-xs text-warroom-accent hover:underline">Clear filters</button>
              )}
            </div>
          ) : (
            <div>
              {contactGroups.map((group) => {
                const isActive = selectedContact === group.key;
                const latestRecord = group.records[0];
                return (
                  <button
                    key={group.key}
                    onClick={() => setSelectedContact(group.key)}
                    className={`w-full text-left px-3 sm:px-4 py-3 sm:py-4 border-b border-warroom-border/50 hover:bg-warroom-surface/50 transition ${
                      isActive ? "bg-warroom-accent/5 border-l-2 border-l-warroom-accent" : ""
                    }`}
                  >
                    <div className="flex items-start gap-2.5 sm:gap-3">
                      {/* Avatar circle */}
                      <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-warroom-accent/10 flex items-center justify-center shrink-0">
                        <User size={16} className="text-warroom-accent" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs sm:text-sm font-semibold text-warroom-text truncate">{group.name}</span>
                          <span className="text-[10px] text-warroom-muted ml-auto shrink-0">
                            {relativeTime(group.lastActivity)}
                          </span>
                        </div>

                        {group.organization && (
                          <p className="text-[10px] sm:text-xs text-warroom-muted truncate mb-0.5 flex items-center gap-1">
                            <Building2 size={9} className="shrink-0" /> {group.organization}
                          </p>
                        )}

                        {/* Latest message preview */}
                        <p className="text-[10px] sm:text-xs text-warroom-muted truncate">
                          {latestRecord.subject || latestRecord.summary || "No content"}
                        </p>

                        {/* Type counts */}
                        <div className="flex items-center gap-2 mt-1.5">
                          {group.callCount > 0 && (
                            <span className="text-[10px] text-green-400 flex items-center gap-0.5">
                              <Phone size={9} /> {group.callCount}
                            </span>
                          )}
                          {group.smsCount > 0 && (
                            <span className="text-[10px] text-cyan-400 flex items-center gap-0.5">
                              <MessageSquare size={9} /> {group.smsCount}
                            </span>
                          )}
                          {group.emailCount > 0 && (
                            <span className="text-[10px] text-blue-400 flex items-center gap-0.5">
                              <Mail size={9} /> {group.emailCount}
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

        {/* Contact Detail / Thread View */}
        {activeGroup ? (
          <div className="flex-1 flex flex-col overflow-hidden bg-warroom-bg">
            {/* Contact header card */}
            <div className="sticky top-0 bg-warroom-bg border-b border-warroom-border px-3 sm:px-6 py-3 z-10 shrink-0">
              <div className="flex items-center gap-3">
                <button onClick={() => setSelectedContact(null)} className="md:hidden p-1 text-warroom-muted hover:text-warroom-text">
                  <ChevronLeft size={18} />
                </button>
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-warroom-accent/10 flex items-center justify-center shrink-0">
                  <User size={16} className="text-warroom-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-warroom-text truncate">{activeGroup.name}</h3>
                  <div className="flex items-center gap-2 sm:gap-3 text-[10px] sm:text-xs text-warroom-muted flex-wrap">
                    {activeGroup.phone && <span className="flex items-center gap-1"><Phone size={9} /> {activeGroup.phone}</span>}
                    {activeGroup.email && <span className="flex items-center gap-1 truncate"><Mail size={9} /> {activeGroup.email}</span>}
                    {activeGroup.organization && <span className="flex items-center gap-1"><Building2 size={9} /> {activeGroup.organization}</span>}
                  </div>
                </div>
                {/* Type counts */}
                <div className="flex items-center gap-2 shrink-0">
                  {activeGroup.callCount > 0 && (
                    <span className="text-[10px] sm:text-xs bg-green-500/10 text-green-400 px-1.5 sm:px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Phone size={10} /> {activeGroup.callCount}
                    </span>
                  )}
                  {activeGroup.smsCount > 0 && (
                    <span className="text-[10px] sm:text-xs bg-cyan-500/10 text-cyan-400 px-1.5 sm:px-2 py-0.5 rounded-full flex items-center gap-1">
                      <MessageSquare size={10} /> {activeGroup.smsCount}
                    </span>
                  )}
                  {activeGroup.emailCount > 0 && (
                    <span className="text-[10px] sm:text-xs bg-blue-500/10 text-blue-400 px-1.5 sm:px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Mail size={10} /> {activeGroup.emailCount}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Thread / timeline */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4">
              {[...activeGroup.records]
                .sort((a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime())
                .map((record) => (
                  <RecordCard key={record.id} record={record} />
                ))}
            </div>
          </div>
        ) : (
          /* Empty state when no contact selected (desktop) */
          <div className="hidden md:flex flex-1 items-center justify-center bg-warroom-bg text-warroom-muted">
            <div className="text-center">
              <MessageSquare size={48} className="mx-auto mb-3 opacity-10" />
              <p className="text-sm">Select a contact to view conversation</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
