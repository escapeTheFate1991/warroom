"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  PenSquare,
  Phone,
  Search,
  Send,
  User,
  X,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import QuickActions from "./QuickActions";

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
  person_id: number | null;
  occurred_at: string;
  metadata: Record<string, string | number | boolean | null>;
}

interface ContactGroup {
  key: string;
  name: string;
  phone: string | null;
  email: string | null;
  organization: string | null;
  person_id: number | null;
  records: CommRecord[];
  lastActivity: string;
  callCount: number;
  smsCount: number;
  emailCount: number;
}

interface CRMPerson {
  id: number;
  name: string;
  emails: Array<{ value: string; label?: string }>;
  contact_numbers: Array<{ value: string; label?: string }>;
  organization_name?: string;
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

/* ── Compose Modal ─────────────────────────────────────── */

function ComposeModal({ onClose, onSent }: { onClose: () => void; onSent: () => void }) {
  const [contactSearch, setContactSearch] = useState("");
  const [contactResults, setContactResults] = useState<CRMPerson[]>([]);
  const [selectedContact, setSelectedContact] = useState<CRMPerson | null>(null);
  const [messageType, setMessageType] = useState<"sms" | "email">("email");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchTimer = useRef<NodeJS.Timeout | null>(null);

  // Typeahead contact search
  useEffect(() => {
    if (!contactSearch || contactSearch.length < 2) {
      setContactResults([]);
      return;
    }
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await authFetch(`${API}/api/crm/contacts/persons?search=${encodeURIComponent(contactSearch)}&limit=10`);
        if (res.ok) {
          const data = await res.json();
          setContactResults(data || []);
        }
      } catch {
        // ignore
      } finally {
        setSearchLoading(false);
      }
    }, 300);
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [contactSearch]);

  const selectedPhone = selectedContact?.contact_numbers?.[0]?.value || null;
  const selectedEmail = selectedContact?.emails?.[0]?.value || null;

  const canSend = selectedContact && body.trim() && (
    (messageType === "sms" && selectedPhone) ||
    (messageType === "email" && selectedEmail)
  );

  const handleSend = async () => {
    if (!canSend) return;
    setSending(true);
    setResult(null);

    try {
      if (messageType === "sms" && selectedPhone) {
        const res = await authFetch(`${API}/api/twilio/sms`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ to: selectedPhone, body: body.trim() }),
        });
        if (res.ok) {
          setResult({ ok: true, msg: "SMS sent" });
        } else {
          const data = await res.json().catch(() => ({}));
          setResult({ ok: false, msg: data.detail || "Failed to send SMS" });
        }
      } else if (messageType === "email" && selectedEmail) {
        const res = await authFetch(`${API}/api/email/send`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ to: selectedEmail, subject: subject || "Message from War Room", body: body.trim() }),
        });
        if (res.ok) {
          setResult({ ok: true, msg: "Email sent" });
        } else {
          const data = await res.json().catch(() => ({}));
          setResult({ ok: false, msg: data.detail || "Failed to send email" });
        }
      }

      if (!result || result.ok !== false) {
        setTimeout(() => {
          onSent();
          onClose();
        }, 1500);
      }
    } catch {
      setResult({ ok: false, msg: "Network error" });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-lg overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-warroom-border">
          <div className="flex items-center gap-2">
            <PenSquare size={16} className="text-warroom-accent" />
            <h3 className="text-sm font-semibold text-warroom-text">New Message</h3>
          </div>
          <button onClick={onClose} className="p-1 text-warroom-muted hover:text-warroom-text">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* To: contact search */}
          <div>
            <label className="text-xs text-warroom-muted mb-1 block">To</label>
            {selectedContact ? (
              <div className="flex items-center gap-2 bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2">
                <User size={14} className="text-warroom-accent shrink-0" />
                <span className="text-sm text-warroom-text flex-1">{selectedContact.name}</span>
                <button onClick={() => { setSelectedContact(null); setContactSearch(""); }} className="text-warroom-muted hover:text-warroom-text">
                  <X size={12} />
                </button>
              </div>
            ) : (
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
                <input
                  value={contactSearch}
                  onChange={(e) => setContactSearch(e.target.value)}
                  placeholder="Search contacts..."
                  className="w-full bg-warroom-bg border border-warroom-border rounded-xl pl-9 pr-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50"
                  autoFocus
                />
                {searchLoading && <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted animate-spin" />}
                {contactResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-warroom-surface border border-warroom-border rounded-xl shadow-lg max-h-48 overflow-y-auto z-10">
                    {contactResults.map((person) => (
                      <button
                        key={person.id}
                        onClick={() => { setSelectedContact(person); setContactResults([]); setContactSearch(""); }}
                        className="w-full text-left px-4 py-2.5 hover:bg-warroom-bg transition flex items-center gap-2"
                      >
                        <User size={12} className="text-warroom-accent shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm text-warroom-text truncate">{person.name}</p>
                          <p className="text-[10px] text-warroom-muted truncate">
                            {person.emails?.[0]?.value || ""} {person.contact_numbers?.[0]?.value ? `· ${person.contact_numbers[0].value}` : ""}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Type toggle */}
          {selectedContact && (
            <div className="flex gap-2">
              {selectedPhone && (
                <button
                  onClick={() => setMessageType("sms")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    messageType === "sms"
                      ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                      : "bg-warroom-bg border border-warroom-border text-warroom-muted hover:text-warroom-text"
                  }`}
                >
                  <MessageSquare size={12} /> SMS
                </button>
              )}
              {selectedEmail && (
                <button
                  onClick={() => setMessageType("email")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    messageType === "email"
                      ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                      : "bg-warroom-bg border border-warroom-border text-warroom-muted hover:text-warroom-text"
                  }`}
                >
                  <Mail size={12} /> Email
                </button>
              )}
            </div>
          )}

          {/* Subject (email only) */}
          {messageType === "email" && selectedContact && (
            <div>
              <label className="text-xs text-warroom-muted mb-1 block">Subject</label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Email subject..."
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50"
              />
            </div>
          )}

          {/* Body */}
          {selectedContact && (
            <div>
              <label className="text-xs text-warroom-muted mb-1 block">Message</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder={messageType === "sms" ? "Type your message..." : "Write your email..."}
                rows={messageType === "sms" ? 3 : 5}
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50 resize-none"
              />
              {messageType === "sms" && (
                <p className="text-[10px] text-warroom-muted mt-1">{body.length}/160 characters</p>
              )}
            </div>
          )}

          {/* Result */}
          {result && (
            <p className={`text-xs ${result.ok ? "text-green-400" : "text-red-400"}`}>
              {result.ok ? "✓" : "✗"} {result.msg}
            </p>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="px-3 py-2 text-xs text-warroom-muted hover:text-warroom-text transition">
              Cancel
            </button>
            <button
              onClick={handleSend}
              disabled={!canSend || sending}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium text-white bg-warroom-accent hover:bg-warroom-accent/80 transition disabled:opacity-40"
            >
              {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
              Send
            </button>
          </div>
        </div>
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
  const [showCompose, setShowCompose] = useState(false);

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
          person_id: r.person_id || null,
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
      if (!group.person_id && r.person_id) group.person_id = r.person_id;
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

  // Optimistic update: add a sent message to the active thread + refresh after delay
  const handleMessageSent = useCallback((type: "sms" | "email" | "call", body?: string, subject?: string) => {
    if (!activeGroup) return;

    const optimisticRecord: CommRecord = {
      id: `optimistic-${Date.now()}`,
      type,
      direction: "outbound",
      status: "sent",
      contact_name: activeGroup.name,
      contact_phone: activeGroup.phone,
      contact_email: activeGroup.email,
      organization: activeGroup.organization,
      employee: null,
      agent: null,
      subject: subject || null,
      summary: body?.slice(0, 100) || (type === "call" ? "Call initiated" : null),
      transcript: body || null,
      pain_points: null,
      services: null,
      schedule_pref: null,
      duration_seconds: null,
      person_id: activeGroup.person_id,
      occurred_at: new Date().toISOString(),
      metadata: {},
    };

    setRecords(prev => [optimisticRecord, ...prev]);

    // Refresh from server after short delay
    setTimeout(() => loadRecords(), 3000);
  }, [activeGroup, loadRecords]);

  /* ── Render ── */

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-warroom-border flex items-center px-3 sm:px-6 py-2 sm:py-0 sm:h-14 gap-2 sm:gap-3 shrink-0">
        {activeGroup && (
          <button onClick={() => setSelectedContact(null)} className="p-1 text-warroom-muted hover:text-warroom-text">
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

      {/* Content: Full-width list OR full-width detail (no split) */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Contact List — hidden when a contact is selected */}
        <div className={`${selectedContact ? "hidden" : "w-full"} overflow-y-auto`}>
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

        {/* Contact Detail / Thread View — full width, replaces list */}
        {activeGroup ? (
          <div className="w-full flex flex-col overflow-hidden bg-warroom-bg">
            {/* Contact header card */}
            <div className="sticky top-0 bg-warroom-bg border-b border-warroom-border px-3 sm:px-6 py-3 z-10 shrink-0">
              <div className="flex items-center gap-3">
                <button onClick={() => setSelectedContact(null)} className="p-1.5 rounded-lg text-warroom-muted hover:text-warroom-text hover:bg-warroom-surface transition">
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
                {/* QuickActions */}
                <QuickActions
                  phone={activeGroup.phone}
                  email={activeGroup.email}
                  name={activeGroup.name}
                  onSent={handleMessageSent}
                />
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
            <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4 max-w-4xl mx-auto w-full">
              {[...activeGroup.records]
                .sort((a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime())
                .map((record) => (
                  <RecordCard key={record.id} record={record} />
                ))}
            </div>
          </div>
        ) : null}

        {/* Compose FAB */}
        {!activeGroup && (
          <button
            onClick={() => setShowCompose(true)}
            className="absolute bottom-6 right-6 bg-warroom-accent hover:bg-warroom-accent/80 text-white rounded-full shadow-lg w-12 h-12 flex items-center justify-center transition-all hover:scale-105"
            title="New Message"
          >
            <PenSquare size={20} />
          </button>
        )}
      </div>

      {/* Compose Modal */}
      {showCompose && (
        <ComposeModal
          onClose={() => setShowCompose(false)}
          onSent={loadRecords}
        />
      )}
    </div>
  );
}
