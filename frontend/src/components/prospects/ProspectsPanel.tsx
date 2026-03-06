"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search, Filter, ArrowLeft, Star, Phone, Mail, Globe, MapPin,
  Calendar, ChevronDown, Loader2, RefreshCw, UserPlus, Building2,
  Clock, MessageSquare, Send, Trophy, XCircle, ExternalLink,
  AlertTriangle, TrendingUp, FileText, Eye, Save, X,
} from "lucide-react";
import { authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────── */

interface Prospect {
  id: string;
  source_id: number;
  source: "leadgen" | "form" | "email" | "referral";
  name: string;
  business_name: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  stage: ProspectStage;
  score: number;
  rating: number | null;
  reviews_count: number;
  review_sentiment_score: number | null;
  review_highlights: string[];
  review_pain_points: string[];
  review_opportunity_flags: string[];
  website_audit_score: number | null;
  website_audit_grade: string | null;
  contact_notes: string | null;
  contact_history: Array<{ date: string; by: string; notes: string; outcome: string }>;
  lead_tier: string | null;
  created_at: string | null;
  last_activity: string | null;
  original_message: string | null;
}

type ProspectStage = "new" | "contacted" | "meeting_scheduled" | "proposal_sent" | "won" | "lost";

interface ProspectStats {
  total: number;
  new_this_week: number;
  meetings_scheduled: number;
  won_this_month: number;
}

/* ── Constants ─────────────────────────────────────────────── */

const SOURCE_CONFIG: Record<string, { label: string; color: string }> = {
  leadgen:  { label: "Lead Gen",      color: "bg-blue-500/20 text-blue-400" },
  form:     { label: "Website Form",  color: "bg-emerald-500/20 text-emerald-400" },
  email:    { label: "Email",         color: "bg-purple-500/20 text-purple-400" },
  referral: { label: "Referral",      color: "bg-orange-500/20 text-orange-400" },
};

const STAGE_CONFIG: Record<ProspectStage, { label: string; color: string }> = {
  new:               { label: "New",               color: "bg-blue-500/20 text-blue-400" },
  contacted:         { label: "Contacted",         color: "bg-yellow-500/20 text-yellow-400" },
  meeting_scheduled: { label: "Meeting Scheduled", color: "bg-purple-500/20 text-purple-400" },
  proposal_sent:     { label: "Proposal Sent",     color: "bg-orange-500/20 text-orange-400" },
  won:               { label: "Won",               color: "bg-green-500/20 text-green-400" },
  lost:              { label: "Lost",              color: "bg-red-500/20 text-red-400" },
};

const ALL_STAGES: ProspectStage[] = ["new", "contacted", "meeting_scheduled", "proposal_sent", "won", "lost"];
const ALL_SOURCES = ["all", "leadgen", "form", "email", "referral"];
const SORT_OPTIONS = [
  { value: "created_at", label: "Newest First" },
  { value: "score", label: "By Score" },
  { value: "stage", label: "By Stage" },
];

/* ── Helpers ───────────────────────────────────────────────── */

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "—";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function sentimentDot(score: number | null): string {
  if (score === null) return "";
  if (score >= 0.3) return "bg-green-400";
  if (score >= -0.1) return "bg-yellow-400";
  return "bg-red-400";
}

/* ── Main Component ────────────────────────────────────────── */

export default function ProspectsPanel() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [stats, setStats] = useState<ProspectStats>({ total: 0, new_this_week: 0, meetings_scheduled: 0, won_this_month: 0 });
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Prospect | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [filterSource, setFilterSource] = useState("all");
  const [filterStage, setFilterStage] = useState("all");
  const [sortBy, setSortBy] = useState("created_at");

  const fetchProspects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch("/api/prospects/list", {
        method: "POST",
        body: JSON.stringify({
          source: filterSource === "all" ? null : filterSource,
          stage: filterStage === "all" ? null : filterStage,
          search: searchQuery || null,
          sort_by: sortBy,
          sort_dir: "desc",
          limit: 200,
          offset: 0,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setProspects(data.prospects || []);
        setStats(data.stats || { total: 0, new_this_week: 0, meetings_scheduled: 0, won_this_month: 0 });
      }
    } catch (err) {
      console.error("Failed to fetch prospects:", err);
    } finally {
      setLoading(false);
    }
  }, [filterSource, filterStage, searchQuery, sortBy]);

  useEffect(() => {
    fetchProspects();
  }, [fetchProspects]);

  if (selected) {
    return (
      <ProspectDetail
        prospect={selected}
        onBack={() => { setSelected(null); fetchProspects(); }}
        onUpdate={fetchProspects}
      />
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-6 pb-0">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-warroom-accent/20 flex items-center justify-center">
              <UserPlus size={20} className="text-warroom-accent" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-warroom-text">Prospects</h1>
              <p className="text-sm text-warroom-muted">Qualified leads, submissions & meetings</p>
            </div>
          </div>
          <button
            onClick={fetchProspects}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-warroom-muted hover:text-warroom-text transition-colors"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span className="text-sm">Refresh</span>
          </button>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <StatCard label="Total Prospects" value={stats.total} icon={<UserPlus size={16} />} color="text-warroom-accent" />
          <StatCard label="New This Week" value={stats.new_this_week} icon={<Clock size={16} />} color="text-blue-400" />
          <StatCard label="Meetings Scheduled" value={stats.meetings_scheduled} icon={<Calendar size={16} />} color="text-purple-400" />
          <StatCard label="Won This Month" value={stats.won_this_month} icon={<Trophy size={16} />} color="text-green-400" />
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
            <input
              type="text"
              placeholder="Search by name or business..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-sm text-warroom-text placeholder:text-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50"
            />
          </div>

          {/* Source Filter */}
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50 appearance-none cursor-pointer"
          >
            <option value="all">All Sources</option>
            <option value="leadgen">Lead Gen</option>
            <option value="form">Website Form</option>
            <option value="email">Email</option>
            <option value="referral">Referral</option>
          </select>

          {/* Stage Filter */}
          <select
            value={filterStage}
            onChange={(e) => setFilterStage(e.target.value)}
            className="px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50 appearance-none cursor-pointer"
          >
            <option value="all">All Stages</option>
            {ALL_STAGES.map((s) => (
              <option key={s} value={s}>{STAGE_CONFIG[s].label}</option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50 appearance-none cursor-pointer"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Card Grid */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-warroom-accent" />
          </div>
        ) : prospects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
            <UserPlus size={40} className="mb-3 opacity-40" />
            <p className="text-lg font-medium">No prospects found</p>
            <p className="text-sm mt-1">Discover leads or wait for contact form submissions</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {prospects.map((p) => (
              <ProspectCard key={p.id} prospect={p} onClick={() => setSelected(p)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Stat Card ─────────────────────────────────────────────── */

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: React.ReactNode; color: string }) {
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
      <div className="flex items-center gap-2 mb-1">
        <span className={color}>{icon}</span>
        <span className="text-xs text-warroom-muted">{label}</span>
      </div>
      <p className="text-2xl font-bold text-warroom-text">{value}</p>
    </div>
  );
}

/* ── Prospect Card ─────────────────────────────────────────── */

function ProspectCard({ prospect, onClick }: { prospect: Prospect; onClick: () => void }) {
  const src = SOURCE_CONFIG[prospect.source] || SOURCE_CONFIG.leadgen;
  const stg = STAGE_CONFIG[prospect.stage] || STAGE_CONFIG.new;
  const sentColor = sentimentDot(prospect.review_sentiment_score);

  return (
    <div
      onClick={onClick}
      className="bg-warroom-surface border border-warroom-border rounded-xl p-4 cursor-pointer hover:border-warroom-accent/40 hover:bg-warroom-accent/5 transition-all group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-warroom-text truncate group-hover:text-warroom-accent transition-colors">
            {prospect.business_name || prospect.name}
          </h3>
          {prospect.business_name && prospect.name !== prospect.business_name && (
            <p className="text-xs text-warroom-muted truncate">{prospect.name}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5 ml-2 flex-shrink-0">
          {sentColor && <span className={`w-2 h-2 rounded-full ${sentColor}`} title="Review sentiment" />}
        </div>
      </div>

      {/* Badges */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${src.color}`}>
          {src.label}
        </span>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${stg.color}`}>
          {stg.label}
        </span>
        {prospect.lead_tier === "hot" && (
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400">
            🔥 Hot
          </span>
        )}
      </div>

      {/* Contact Info */}
      <div className="space-y-1 mb-3">
        {prospect.phone && (
          <div className="flex items-center gap-2 text-xs text-warroom-muted">
            <Phone size={11} />
            <span className="truncate">{prospect.phone}</span>
          </div>
        )}
        {prospect.email && (
          <div className="flex items-center gap-2 text-xs text-warroom-muted">
            <Mail size={11} />
            <span className="truncate">{prospect.email}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-warroom-border/50">
        {prospect.rating !== null && (
          <div className="flex items-center gap-1">
            <Star size={12} className="text-yellow-400 fill-yellow-400" />
            <span className="text-xs text-warroom-muted">{prospect.rating.toFixed(1)}</span>
          </div>
        )}
        {prospect.score > 0 && (
          <div className="flex items-center gap-1">
            <TrendingUp size={12} className="text-warroom-accent" />
            <span className="text-xs text-warroom-muted">Score: {prospect.score}</span>
          </div>
        )}
        <span className="text-[10px] text-warroom-muted ml-auto">
          {timeAgo(prospect.last_activity)}
        </span>
      </div>
    </div>
  );
}

/* ── Prospect Detail ───────────────────────────────────────── */

function ProspectDetail({
  prospect: initial,
  onBack,
  onUpdate,
}: {
  prospect: Prospect;
  onBack: () => void;
  onUpdate: () => void;
}) {
  const [prospect, setProspect] = useState(initial);
  const [notes, setNotes] = useState(prospect.contact_notes || "");
  const [saving, setSaving] = useState(false);
  const [showMeetingForm, setShowMeetingForm] = useState(false);
  const [meetingDate, setMeetingDate] = useState("");
  const [meetingTime, setMeetingTime] = useState("10:00");
  const [meetingNotes, setMeetingNotes] = useState("");
  const [schedulingMeeting, setSchedulingMeeting] = useState(false);

  const updateStage = async (newStage: ProspectStage) => {
    try {
      const res = await authFetch(`/api/prospects/${prospect.id}/stage`, {
        method: "PATCH",
        body: JSON.stringify({ stage: newStage }),
      });
      if (res.ok) {
        setProspect((p) => ({ ...p, stage: newStage }));
        onUpdate();
      }
    } catch (err) {
      console.error("Failed to update stage:", err);
    }
  };

  const saveNotes = async () => {
    setSaving(true);
    try {
      const res = await authFetch(`/api/prospects/${prospect.id}/notes`, {
        method: "PATCH",
        body: JSON.stringify({ notes }),
      });
      if (res.ok) {
        setProspect((p) => ({ ...p, contact_notes: notes }));
      }
    } catch (err) {
      console.error("Failed to save notes:", err);
    } finally {
      setSaving(false);
    }
  };

  const scheduleMeeting = async () => {
    if (!meetingDate) return;
    setSchedulingMeeting(true);
    try {
      // Create calendar event
      await authFetch("/api/calendar/personal/events", {
        method: "POST",
        body: JSON.stringify({
          title: `Meeting: ${prospect.business_name || prospect.name}`,
          date: meetingDate,
          time: meetingTime,
          description: meetingNotes || `Prospect meeting with ${prospect.name}`,
          type: "meeting",
        }),
      });
      // Update stage
      await updateStage("meeting_scheduled");
      setShowMeetingForm(false);
      setMeetingDate("");
      setMeetingTime("10:00");
      setMeetingNotes("");
    } catch (err) {
      console.error("Failed to schedule meeting:", err);
    } finally {
      setSchedulingMeeting(false);
    }
  };

  const src = SOURCE_CONFIG[prospect.source] || SOURCE_CONFIG.leadgen;
  const stg = STAGE_CONFIG[prospect.stage] || STAGE_CONFIG.new;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-6 pb-4 border-b border-warroom-border">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-warroom-muted hover:text-warroom-text mb-3 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Prospects
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-warroom-text">
              {prospect.business_name || prospect.name}
            </h1>
            {prospect.business_name && prospect.name !== prospect.business_name && (
              <p className="text-sm text-warroom-muted">{prospect.name}</p>
            )}
            <div className="flex items-center gap-2 mt-2">
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${src.color}`}>
                {src.label}
              </span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${stg.color}`}>
                {stg.label}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowMeetingForm(true)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 text-sm transition-colors"
            >
              <Calendar size={14} />
              Schedule Meeting
            </button>
            {prospect.email && (
              <a
                href={`mailto:${prospect.email}`}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 text-sm transition-colors"
              >
                <Send size={14} />
                Send Email
              </a>
            )}
            <button
              onClick={() => updateStage(prospect.stage === "won" ? "lost" : "won")}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                prospect.stage === "won"
                  ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                  : "bg-green-500/20 text-green-400 hover:bg-green-500/30"
              }`}
            >
              {prospect.stage === "won" ? <XCircle size={14} /> : <Trophy size={14} />}
              {prospect.stage === "won" ? "Mark Lost" : "Mark Won"}
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Left Column — Contact + Source */}
          <div className="xl:col-span-2 space-y-6">
            {/* Contact Info */}
            <Section title="Contact Information">
              <div className="grid grid-cols-2 gap-4">
                <InfoRow icon={<Building2 size={14} />} label="Business" value={prospect.business_name} />
                <InfoRow icon={<UserPlus size={14} />} label="Contact" value={prospect.name} />
                <InfoRow icon={<Phone size={14} />} label="Phone" value={prospect.phone} />
                <InfoRow icon={<Mail size={14} />} label="Email" value={prospect.email} />
                <InfoRow icon={<Globe size={14} />} label="Website" value={prospect.website} link />
                <InfoRow icon={<MapPin size={14} />} label="Address" value={prospect.address} />
              </div>
            </Section>

            {/* Source Info */}
            {prospect.original_message && (
              <Section title="Original Message">
                <p className="text-sm text-warroom-muted whitespace-pre-wrap bg-warroom-bg/50 rounded-lg p-3">
                  {prospect.original_message}
                </p>
              </Section>
            )}

            {/* Lead Intelligence */}
            {prospect.source === "leadgen" && (
              <Section title="Lead Intelligence">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                  {prospect.rating !== null && (
                    <MiniStat label="Rating" value={
                      <div className="flex items-center gap-1">
                        <Star size={14} className="text-yellow-400 fill-yellow-400" />
                        <span>{prospect.rating.toFixed(1)}</span>
                        <span className="text-xs text-warroom-muted">({prospect.reviews_count})</span>
                      </div>
                    } />
                  )}
                  {prospect.website_audit_score !== null && (
                    <MiniStat label="Website Score" value={
                      <span>{prospect.website_audit_score}/100 ({prospect.website_audit_grade})</span>
                    } />
                  )}
                  <MiniStat label="Lead Score" value={prospect.score} />
                  {prospect.review_sentiment_score !== null && (
                    <MiniStat label="Sentiment" value={
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${sentimentDot(prospect.review_sentiment_score)}`} />
                        <span>{prospect.review_sentiment_score.toFixed(2)}</span>
                      </div>
                    } />
                  )}
                </div>

                {prospect.review_highlights.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-semibold text-warroom-muted mb-1.5">Review Highlights</p>
                    <div className="space-y-1">
                      {prospect.review_highlights.slice(0, 3).map((h, i) => (
                        <p key={i} className="text-xs text-warroom-muted/80 bg-warroom-bg/50 rounded-lg px-3 py-2">
                          &ldquo;{h}&rdquo;
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {prospect.review_pain_points.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-semibold text-warroom-muted mb-1.5">Pain Points</p>
                    <div className="flex flex-wrap gap-1.5">
                      {prospect.review_pain_points.map((p, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400">
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {prospect.review_opportunity_flags.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-warroom-muted mb-1.5">Opportunity Flags</p>
                    <div className="flex flex-wrap gap-1.5">
                      {prospect.review_opportunity_flags.map((f, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-400">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </Section>
            )}

            {/* Activity Timeline */}
            <Section title="Activity Timeline">
              {prospect.contact_history.length === 0 ? (
                <p className="text-sm text-warroom-muted/60">No activity recorded yet</p>
              ) : (
                <div className="space-y-3">
                  {prospect.contact_history.map((entry, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="w-2 h-2 rounded-full bg-warroom-accent mt-2 flex-shrink-0" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-warroom-text">{entry.by}</span>
                          <span className="text-[10px] text-warroom-muted">{timeAgo(entry.date)}</span>
                          {entry.outcome && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-warroom-border/50 text-warroom-muted">
                              {entry.outcome}
                            </span>
                          )}
                        </div>
                        {entry.notes && (
                          <p className="text-xs text-warroom-muted mt-0.5">{entry.notes}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          </div>

          {/* Right Column — Stage + Notes + Actions */}
          <div className="space-y-6">
            {/* Stage Selector */}
            <Section title="Stage">
              <select
                value={prospect.stage}
                onChange={(e) => updateStage(e.target.value as ProspectStage)}
                className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50"
              >
                {ALL_STAGES.map((s) => (
                  <option key={s} value={s}>{STAGE_CONFIG[s].label}</option>
                ))}
              </select>
            </Section>

            {/* Notes */}
            <Section title="Notes">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this prospect..."
                rows={6}
                className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-sm text-warroom-text placeholder:text-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50 resize-none"
              />
              <button
                onClick={saveNotes}
                disabled={saving}
                className="mt-2 flex items-center gap-2 px-3 py-2 rounded-lg bg-warroom-accent/20 text-warroom-accent hover:bg-warroom-accent/30 text-sm transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Save Notes
              </button>
            </Section>

            {/* Meeting Scheduler */}
            {showMeetingForm && (
              <Section title="Schedule Meeting">
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-warroom-muted mb-1 block">Date</label>
                    <input
                      type="date"
                      value={meetingDate}
                      onChange={(e) => setMeetingDate(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-warroom-muted mb-1 block">Time</label>
                    <input
                      type="time"
                      value={meetingTime}
                      onChange={(e) => setMeetingTime(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-sm text-warroom-text focus:outline-none focus:border-warroom-accent/50"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-warroom-muted mb-1 block">Notes</label>
                    <textarea
                      value={meetingNotes}
                      onChange={(e) => setMeetingNotes(e.target.value)}
                      placeholder="Meeting agenda..."
                      rows={3}
                      className="w-full px-3 py-2 rounded-lg bg-warroom-bg border border-warroom-border text-sm text-warroom-text placeholder:text-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50 resize-none"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={scheduleMeeting}
                      disabled={!meetingDate || schedulingMeeting}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 text-sm transition-colors disabled:opacity-50"
                    >
                      {schedulingMeeting ? <Loader2 size={14} className="animate-spin" /> : <Calendar size={14} />}
                      Schedule
                    </button>
                    <button
                      onClick={() => setShowMeetingForm(false)}
                      className="px-3 py-2 rounded-lg bg-warroom-border/30 text-warroom-muted hover:text-warroom-text text-sm transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </Section>
            )}

            {/* Quick Info */}
            {prospect.created_at && (
              <Section title="Meta">
                <div className="space-y-2 text-xs text-warroom-muted">
                  <div className="flex justify-between">
                    <span>Created</span>
                    <span>{new Date(prospect.created_at).toLocaleDateString()}</span>
                  </div>
                  {prospect.last_activity && (
                    <div className="flex justify-between">
                      <span>Last Activity</span>
                      <span>{timeAgo(prospect.last_activity)}</span>
                    </div>
                  )}
                  {prospect.lead_tier && (
                    <div className="flex justify-between">
                      <span>Lead Tier</span>
                      <span className="capitalize">{prospect.lead_tier}</span>
                    </div>
                  )}
                </div>
              </Section>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Shared Sub-components ─────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
      <h3 className="text-sm font-semibold text-warroom-text mb-3">{title}</h3>
      {children}
    </div>
  );
}

function InfoRow({ icon, label, value, link }: { icon: React.ReactNode; label: string; value: string | null | undefined; link?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2">
      <span className="text-warroom-muted mt-0.5 flex-shrink-0">{icon}</span>
      <div>
        <p className="text-[10px] text-warroom-muted">{label}</p>
        {link ? (
          <a
            href={value.startsWith("http") ? value : `https://${value}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-warroom-accent hover:underline flex items-center gap-1"
          >
            {value} <ExternalLink size={10} />
          </a>
        ) : (
          <p className="text-xs text-warroom-text">{value}</p>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-warroom-bg/50 rounded-lg p-2.5">
      <p className="text-[10px] text-warroom-muted mb-0.5">{label}</p>
      <div className="text-sm font-semibold text-warroom-text">{value}</div>
    </div>
  );
}
