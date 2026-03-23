"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  ChevronLeft, ChevronRight, Clock, FileText, Loader2, Eye, X,
  Plus, Trash2, CalendarDays, Activity, Pencil,
  MoreHorizontal, MapPin, Users, Bell, Type, CheckSquare, BellRing, Bot,
  Repeat, Globe, Briefcase
} from "lucide-react";
// Agent assignment control removed — socialRecycle
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";


/* ── Types ──────────────────────────────────────────────── */

interface DayData {
  has_memory: boolean;
  preview: string;
  size: number;
}

interface CalendarData {
  year: number;
  month: number;
  days: Record<string, DayData>;
}

interface DayDetail {
  date: string;
  content: string;
}

interface PersonalEvent {
  id: string;
  title: string;
  date: string;
  time?: string;
  end_time?: string;
  description?: string;
  type?: string;
  source: string;
  created_at: string;
  location?: string;
  guests?: string;
  notification?: string;
  recurrence?: string;
  all_day?: boolean;
  visibility?: string;
  status?: string;
  agent_assignments?: AgentAssignmentSummary[];
}

interface PersonalCalendarData {
  year: number;
  month: number;
  events: PersonalEvent[];
  google_connected: boolean;
}

type EventFormData = {
  title: string;
  date: string;
  time: string;
  end_time: string;
  description: string;
  type: string;
  location: string;
  guests: string;
  notification: string;
  recurrence: string;
  all_day: boolean;
  visibility: string;
  status: string;
};

const EMPTY_FORM: EventFormData = {
  title: "", date: "", time: "09:00", end_time: "10:00", description: "",
  type: "event", location: "", guests: "", notification: "30",
  recurrence: "none", all_day: false, visibility: "default", status: "busy",
};

/* ── Constants ──────────────────────────────────────────── */

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

type TabMode = "activities" | "personal";

const EVENT_COLORS: Record<string, string> = {
  meeting: "bg-blue-500",
  call: "bg-green-500",
  task: "bg-amber-500",
  deadline: "bg-red-500",
  personal: "bg-purple-500",
  event: "bg-blue-500",
  reminder: "bg-teal-500",
  default: "bg-warroom-accent",
};

const EVENT_DOT_COLORS: Record<string, string> = {
  meeting: "bg-blue-400",
  call: "bg-green-400",
  task: "bg-amber-400",
  deadline: "bg-red-400",
  personal: "bg-purple-400",
  event: "bg-blue-400",
  reminder: "bg-teal-400",
  default: "bg-warroom-accent",
};

type QuickAddTab = "event" | "task" | "reminder";

/* ── Quick-Add Event Modal ──────────────────────────────── */

function QuickAddModal({
  date,
  initialTitle,
  onClose,
  onSave,
  onMoreOptions,
}: {
  date: string;
  initialTitle?: string;
  onClose: () => void;
  onSave: (data: EventFormData) => void;
  onMoreOptions: (data: EventFormData) => void;
}) {
  const [activeTab, setActiveTab] = useState<QuickAddTab>("event");
  const [form, setForm] = useState<EventFormData>({
    ...EMPTY_FORM,
    date,
    title: initialTitle || "",
    type: "event",
  });
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => { titleRef.current?.focus(); }, []);

  const update = (patch: Partial<EventFormData>) => setForm((f) => ({ ...f, ...patch }));

  const handleTabChange = (tab: QuickAddTab) => {
    setActiveTab(tab);
    update({ type: tab });
  };

  const formattedDate = new Date(date + "T12:00:00").toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-md shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Title input */}
        <div className="p-4 pb-0">
          <input
            ref={titleRef}
            value={form.title}
            onChange={(e) => update({ title: e.target.value })}
            placeholder="Add title"
            className="w-full bg-transparent text-xl font-semibold text-warroom-text placeholder-warroom-muted/50 focus:outline-none border-b border-warroom-border pb-3"
          />
        </div>

        {/* Type tabs */}
        <div className="flex items-center gap-1 px-4 pt-3 pb-2">
          {([
            { key: "event" as QuickAddTab, label: "Event", icon: CalendarDays },
            { key: "task" as QuickAddTab, label: "Task", icon: CheckSquare },
            { key: "reminder" as QuickAddTab, label: "Reminder", icon: BellRing },
          ]).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => handleTabChange(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                activeTab === key
                  ? "bg-warroom-accent text-white"
                  : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg"
              }`}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>

        <div className="px-4 pb-4 space-y-3">
          {/* Date + Time */}
          <div className="flex items-center gap-2 text-sm text-warroom-muted">
            <Clock size={15} className="shrink-0" />
            <span>{formattedDate}</span>
          </div>

          {!form.all_day && (
            <div className="flex items-center gap-2 pl-6">
              <input
                type="time"
                value={form.time}
                onChange={(e) => update({ time: e.target.value })}
                className="bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              />
              <span className="text-warroom-muted text-sm">–</span>
              <input
                type="time"
                value={form.end_time}
                onChange={(e) => update({ end_time: e.target.value })}
                className="bg-warroom-bg border border-warroom-border rounded-lg px-2 py-1.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              />
            </div>
          )}

          {/* Guests */}
          {activeTab === "event" && (
            <div className="flex items-center gap-2">
              <Users size={15} className="text-warroom-muted shrink-0" />
              <input
                value={form.guests}
                onChange={(e) => update({ guests: e.target.value })}
                placeholder="Add guests"
                className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
              />
            </div>
          )}

          {/* Location */}
          <div className="flex items-center gap-2">
            <MapPin size={15} className="text-warroom-muted shrink-0" />
            <input
              value={form.location}
              onChange={(e) => update({ location: e.target.value })}
              placeholder="Add location"
              className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
            />
          </div>

          {/* Description */}
          <div className="flex items-start gap-2">
            <FileText size={15} className="text-warroom-muted shrink-0 mt-2" />
            <textarea
              value={form.description}
              onChange={(e) => update({ description: e.target.value })}
              placeholder="Add description"
              rows={2}
              className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent resize-none"
            />
          </div>

          {/* Notification */}
          <div className="flex items-center gap-2">
            <Bell size={15} className="text-warroom-muted shrink-0" />
            <select
              value={form.notification}
              onChange={(e) => update({ notification: e.target.value })}
              className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
            >
              <option value="10">10 minutes before</option>
              <option value="30">30 minutes before</option>
              <option value="60">1 hour before</option>
              <option value="none">No notification</option>
            </select>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-warroom-border">
          <button
            onClick={() => onMoreOptions(form)}
            className="text-sm text-warroom-muted hover:text-warroom-accent transition"
          >
            More options
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg transition"
            >
              Cancel
            </button>
            <button
              onClick={() => onSave(form)}
              disabled={!form.title}
              className="px-5 py-2 rounded-lg text-sm bg-warroom-accent text-white hover:bg-warroom-accent/80 disabled:opacity-30 transition font-medium"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Event Detail Popover ───────────────────────────────── */

function EventDetailPopover({
  event,
  onClose,
  onEdit,
  onDelete,
  onAssignmentsChange,
}: {
  event: PersonalEvent;
  onClose: () => void;
  onEdit: (event: PersonalEvent) => void;
  onDelete: (eventId: string) => void;
  onAssignmentsChange: (eventId: string, assignments: AgentAssignmentSummary[]) => void;
}) {
  const dotColor = EVENT_DOT_COLORS[event.type || "default"] || EVENT_DOT_COLORS.default;

  const formattedDate = new Date(event.date + "T12:00:00").toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-sm shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with close */}
        <div className="flex items-start justify-between p-4 pb-2">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className={`w-3 h-3 rounded-full shrink-0 ${dotColor}`} />
            <h3 className="font-semibold text-warroom-text text-lg truncate">{event.title}</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-warroom-bg transition shrink-0 ml-2">
            <X size={16} className="text-warroom-muted" />
          </button>
        </div>

        {/* Date + Time */}
        <div className="px-4 pb-3">
          <div className="flex items-center gap-2 text-sm text-warroom-muted">
            <Clock size={14} />
            <span>{formattedDate}</span>
            {event.time && (
              <span className="text-warroom-text font-medium">
                {event.time}{event.end_time ? ` – ${event.end_time}` : ""}
              </span>
            )}
          </div>

          {event.location && (
            <div className="flex items-center gap-2 text-sm text-warroom-muted mt-2">
              <MapPin size={14} />
              <span>{event.location}</span>
            </div>
          )}

          {event.guests && (
            <div className="flex items-center gap-2 text-sm text-warroom-muted mt-2">
              <Users size={14} />
              <span>{event.guests}</span>
            </div>
          )}

          {event.description && (
            <div className="flex items-start gap-2 text-sm text-warroom-muted mt-2">
              <FileText size={14} className="shrink-0 mt-0.5" />
              <span className="whitespace-pre-wrap">{event.description}</span>
            </div>
          )}

          {event.notification && event.notification !== "none" && (
            <div className="flex items-center gap-2 text-sm text-warroom-muted mt-2">
              <Bell size={14} />
              <span>
                {event.notification === "10" ? "10 minutes before" :
                 event.notification === "30" ? "30 minutes before" :
                 event.notification === "60" ? "1 hour before" : `${event.notification} min before`}
              </span>
            </div>
          )}

          {/* Agent assignment control removed — socialRecycle */}
        </div>

        {/* Action buttons */}
        {event.source === "local" && (
          <div className="flex items-center gap-1 px-4 pb-4 pt-1 border-t border-warroom-border mt-1">
            <button
              onClick={() => onEdit(event)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg transition"
              title="Edit"
            >
              <Pencil size={15} />
              <span>Edit</span>
            </button>
            <button
              onClick={() => { onDelete(event.id); onClose(); }}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-warroom-muted hover:text-red-400 hover:bg-red-500/10 transition"
              title="Delete"
            >
              <Trash2 size={15} />
              <span>Delete</span>
            </button>
            <div className="flex-1" />
            <button
              className="p-2 rounded-lg text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg transition"
              title="More options"
              onClick={() => onEdit(event)}
            >
              <MoreHorizontal size={16} />
            </button>
          </div>
        )}

        {/* Calendar owner */}
        <div className="px-4 pb-3 pt-1">
          <div className="flex items-center gap-2 text-xs text-warroom-muted">
            <CalendarDays size={12} />
            <span>{event.source === "local" ? "War Room Calendar" : "Google Calendar"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Full Event Editor Modal ────────────────────────────── */

function FullEventEditorModal({
  initialData,
  editingEvent,
  onClose,
  onSave,
}: {
  initialData: EventFormData;
  editingEvent?: PersonalEvent | null;
  onClose: () => void;
  onSave: (data: EventFormData, existingId?: string) => void;
}) {
  const [form, setForm] = useState<EventFormData>(initialData);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => { titleRef.current?.focus(); }, []);

  const update = (patch: Partial<EventFormData>) => setForm((f) => ({ ...f, ...patch }));

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-warroom-border">
          <input
            ref={titleRef}
            value={form.title}
            onChange={(e) => update({ title: e.target.value })}
            placeholder="Add title"
            className="flex-1 bg-transparent text-xl font-semibold text-warroom-text placeholder-warroom-muted/50 focus:outline-none mr-4"
          />
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg transition"
            >
              Cancel
            </button>
            <button
              onClick={() => onSave(form, editingEvent?.id)}
              disabled={!form.title || !form.date}
              className="px-5 py-2 rounded-lg text-sm bg-warroom-accent text-white hover:bg-warroom-accent/80 disabled:opacity-30 transition font-medium"
            >
              Save
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-5 space-y-5">
          {/* Date + Time section */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Clock size={18} className="text-warroom-muted shrink-0" />
              <div className="flex items-center gap-3 flex-wrap">
                <input
                  type="date"
                  value={form.date}
                  onChange={(e) => update({ date: e.target.value })}
                  className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                />
                {!form.all_day && (
                  <>
                    <input
                      type="time"
                      value={form.time}
                      onChange={(e) => update({ time: e.target.value })}
                      className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                    />
                    <span className="text-warroom-muted">–</span>
                    <input
                      type="time"
                      value={form.end_time}
                      onChange={(e) => update({ end_time: e.target.value })}
                      className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                    />
                  </>
                )}
              </div>
            </div>

            {/* All day toggle */}
            <div className="flex items-center gap-3 pl-8">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.all_day}
                  onChange={(e) => update({ all_day: e.target.checked })}
                  className="w-4 h-4 rounded border-warroom-border bg-warroom-bg text-warroom-accent focus:ring-warroom-accent focus:ring-offset-0"
                />
                <span className="text-sm text-warroom-text">All day</span>
              </label>
            </div>
          </div>

          {/* Recurrence */}
          <div className="flex items-center gap-3">
            <Repeat size={18} className="text-warroom-muted shrink-0" />
            <select
              value={form.recurrence}
              onChange={(e) => update({ recurrence: e.target.value })}
              className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
            >
              <option value="none">Does not repeat</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="custom">Custom...</option>
            </select>
          </div>

          {/* Guests */}
          <div className="flex items-center gap-3">
            <Users size={18} className="text-warroom-muted shrink-0" />
            <input
              value={form.guests}
              onChange={(e) => update({ guests: e.target.value })}
              placeholder="Add guests"
              className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
            />
          </div>

          {/* Location */}
          <div className="flex items-center gap-3">
            <MapPin size={18} className="text-warroom-muted shrink-0" />
            <input
              value={form.location}
              onChange={(e) => update({ location: e.target.value })}
              placeholder="Add location"
              className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
            />
          </div>

          {/* Notification */}
          <div className="flex items-center gap-3">
            <Bell size={18} className="text-warroom-muted shrink-0" />
            <div className="flex items-center gap-2">
              <select
                value={form.notification}
                onChange={(e) => update({ notification: e.target.value })}
                className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="10">10 minutes</option>
                <option value="30">30 minutes</option>
                <option value="60">1 hour</option>
                <option value="120">2 hours</option>
                <option value="1440">1 day</option>
                <option value="none">None</option>
              </select>
              <span className="text-sm text-warroom-muted">before</span>
            </div>
          </div>

          {/* Description */}
          <div className="flex items-start gap-3">
            <FileText size={18} className="text-warroom-muted shrink-0 mt-2" />
            <textarea
              value={form.description}
              onChange={(e) => update({ description: e.target.value })}
              placeholder="Add description"
              rows={4}
              className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent resize-none"
            />
          </div>

          {/* Type */}
          <div className="flex items-center gap-3">
            <Type size={18} className="text-warroom-muted shrink-0" />
            <select
              value={form.type}
              onChange={(e) => update({ type: e.target.value })}
              className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
            >
              <option value="event">Event</option>
              <option value="task">Task</option>
              <option value="reminder">Reminder</option>
              <option value="meeting">Meeting</option>
              <option value="call">Call</option>
              <option value="deadline">Deadline</option>
              <option value="personal">Personal</option>
            </select>
          </div>

          {/* Visibility + Status row */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <Globe size={18} className="text-warroom-muted shrink-0" />
              <select
                value={form.visibility}
                onChange={(e) => update({ visibility: e.target.value })}
                className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="default">Default visibility</option>
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
            </div>
            <div className="flex items-center gap-3">
              <Briefcase size={18} className="text-warroom-muted shrink-0" />
              <select
                value={form.status}
                onChange={(e) => update({ status: e.target.value })}
                className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="busy">Busy</option>
                <option value="free">Free</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Main Component ─────────────────────────────────────── */

export default function ActivityCalendar() {
  const [tab, setTab] = useState<TabMode>("personal");
  const quickAddInputRef = useRef<HTMLInputElement>(null);
  const [currentDate, setCurrentDate] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });

  /* Activities state */
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [dayDetail, setDayDetail] = useState<DayDetail | null>(null);
  const [dayLoading, setDayLoading] = useState(false);

  /* Personal state */
  const [personalData, setPersonalData] = useState<PersonalCalendarData | null>(null);
  const [personalLoading, setPersonalLoading] = useState(false);

  /* Google Calendar state */
  const [googleStatus, setGoogleStatus] = useState<{ connected: boolean; email?: string } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);

  /* Personal modals */
  const [quickAddDate, setQuickAddDate] = useState<string | null>(null);
  const [quickAddTitle, setQuickAddTitle] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<PersonalEvent | null>(null);
  const [fullEditorData, setFullEditorData] = useState<{ form: EventFormData; event?: PersonalEvent } | null>(null);

  /* ── Activity Calendar Logic ──────────────────────────── */

  const loadCalendarData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const monthStr = `${currentDate.year}-${currentDate.month.toString().padStart(2, "0")}`;
      const response = await authFetch(`${API}/api/calendar?month=${monthStr}`);
      if (!response.ok) throw new Error("Failed to load calendar data");
      setCalendarData(await response.json());
    } catch {
      setError("Failed to load calendar data");
    } finally {
      setLoading(false);
    }
  }, [currentDate]);

  const loadDayDetail = async (day: string) => {
    try {
      setDayLoading(true);
      setSelectedDay(day);
      const response = await authFetch(`${API}/api/calendar/day/${day}`);
      if (!response.ok) { setDayDetail(null); return; }
      setDayDetail(await response.json());
    } catch {
      setDayDetail(null);
    } finally {
      setDayLoading(false);
    }
  };

  /* ── Personal Calendar Logic ──────────────────────────── */

  const loadPersonalData = useCallback(async () => {
    try {
      setPersonalLoading(true);
      const monthStr = `${currentDate.year}-${currentDate.month.toString().padStart(2, "0")}`;
      const response = await authFetch(`${API}/api/calendar/personal?month=${monthStr}`);
      if (!response.ok) throw new Error("Failed to load personal calendar");
      setPersonalData(await response.json());
    } catch {
      setPersonalData(null);
    } finally {
      setPersonalLoading(false);
    }
  }, [currentDate]);

  const saveEvent = async (data: EventFormData, existingId?: string) => {
    if (!data.title || !data.date) return;

    const payload: Record<string, unknown> = {
      title: data.title,
      date: data.date,
      type: data.type,
      description: data.description || undefined,
      location: data.location || undefined,
      guests: data.guests || undefined,
      notification: data.notification || undefined,
      recurrence: data.recurrence || undefined,
      all_day: data.all_day,
      visibility: data.visibility,
      status: data.status,
    };

    if (!data.all_day) {
      payload.time = data.time || undefined;
      payload.end_time = data.end_time || undefined;
    }

    try {
      if (existingId) {
        await authFetch(`${API}/api/calendar/personal/events/${existingId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        await authFetch(`${API}/api/calendar/personal/events`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      setQuickAddDate(null);
      setFullEditorData(null);
      setSelectedEvent(null);
      loadPersonalData();
    } catch (err) {
      console.error("Failed to save event:", err);
    }
  };

  const deleteEvent = async (eventId: string) => {
    try {
      await authFetch(`${API}/api/calendar/personal/events/${eventId}`, { method: "DELETE" });
      loadPersonalData();
    } catch (err) {
      console.error("Failed to delete event:", err);
    }
  };

  /* ── Google Calendar Logic ──────────────────────────── */

  const loadGoogleStatus = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/calendar/google/status`);
      if (res.ok) setGoogleStatus(await res.json());
    } catch {
      setGoogleStatus({ connected: false });
    }
  }, []);

  const resyncCalendar = useCallback(async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await loadPersonalData();
      setLastSync(new Date());
    } finally {
      setSyncing(false);
    }
  }, [syncing, loadPersonalData]);

  const openQuickAdd = (dateStr: string) => {
    setQuickAddDate(dateStr);
  };

  const openFullEditor = (form: EventFormData, event?: PersonalEvent) => {
    setQuickAddDate(null);
    setSelectedEvent(null);
    setFullEditorData({ form, event });
  };

  const openEditFromEvent = (event: PersonalEvent) => {
    setSelectedEvent(null);
    setFullEditorData({
      form: {
        title: event.title,
        date: event.date,
        time: event.time || "09:00",
        end_time: event.end_time || "10:00",
        description: event.description || "",
        type: event.type || "event",
        location: event.location || "",
        guests: event.guests || "",
        notification: event.notification || "30",
        recurrence: event.recurrence || "none",
        all_day: event.all_day || false,
        visibility: event.visibility || "default",
        status: event.status || "busy",
      },
      event,
    });
  };

  const handleEventAssignmentsChange = useCallback((eventId: string, assignments: AgentAssignmentSummary[]) => {
    setPersonalData((prev) => prev ? {
      ...prev,
      events: prev.events.map((event) => event.id === eventId ? { ...event, agent_assignments: assignments } : event),
    } : prev);
    setSelectedEvent((prev) => prev && prev.id === eventId ? { ...prev, agent_assignments: assignments } : prev);
  }, []);

  /* ── Navigation ───────────────────────────────────────── */

  const navigateMonth = (delta: number) => {
    setCurrentDate((prev) => {
      let m = prev.month + delta, y = prev.year;
      if (m > 12) { m = 1; y++; } else if (m < 1) { m = 12; y--; }
      return { year: y, month: m };
    });
  };

  /* ── Calendar Grid ────────────────────────────────────── */

  const generateCalendarGrid = () => {
    const firstDay = new Date(currentDate.year, currentDate.month - 1, 1);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    const today = new Date();
    const todayStr = today.toISOString().split("T")[0];

    const grid = [];
    for (let week = 0; week < 6; week++) {
      const weekDays = [];
      for (let day = 0; day < 7; day++) {
        const d = new Date(startDate);
        d.setDate(startDate.getDate() + week * 7 + day);
        const dateStr = d.toISOString().split("T")[0];
        const isCurrentMonth = d.getMonth() === currentDate.month - 1;
        const isToday = dateStr === todayStr;

        const hasMemory = calendarData?.days[dateStr]?.has_memory || false;
        const memoryData = calendarData?.days[dateStr];
        const dayEvents = personalData?.events?.filter((e) => e.date === dateStr) || [];

        weekDays.push({ date: d, dateStr, day: d.getDate(), isCurrentMonth, isToday, hasMemory, memoryData, dayEvents });
      }
      grid.push(weekDays);
    }
    return grid;
  };

  /* ── Effects ──────────────────────────────────────────── */

  useEffect(() => { loadCalendarData(); }, [loadCalendarData]);
  useEffect(() => { if (tab === "personal") loadPersonalData(); }, [tab, loadPersonalData]);
  useEffect(() => { loadGoogleStatus(); }, [loadGoogleStatus]);

  // Auto-sync personal calendar every 2 minutes when on that tab
  useEffect(() => {
    if (tab !== "personal" || !googleStatus?.connected) return;
    const interval = setInterval(() => {
      loadPersonalData().then(() => setLastSync(new Date()));
    }, 120_000);
    return () => clearInterval(interval);
  }, [tab, googleStatus?.connected, loadPersonalData]);

  const grid = generateCalendarGrid();

  /* ── Render ───────────────────────────────────────────── */

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="bg-warroom-surface border-b border-warroom-border overflow-hidden flex-1 flex flex-col">
        {/* Header with Tabs */}
        <div className="border-b border-warroom-border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 bg-warroom-bg rounded-xl p-0.5">
              <button
                onClick={() => setTab("activities")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  tab === "activities"
                    ? "bg-warroom-accent text-white shadow-sm"
                    : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-surface"
                }`}
              >
                <Activity size={13} />
                Activities
              </button>
              <button
                onClick={() => setTab("personal")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  tab === "personal"
                    ? "bg-warroom-accent text-white shadow-sm"
                    : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-surface"
                }`}
              >
                <CalendarDays size={13} />
                Personal
              </button>
            </div>

            <div className="flex items-center gap-1.5 ml-auto">
              <button
                onClick={() => navigateMonth(-1)}
                className="p-1.5 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition"
              >
                <ChevronLeft size={14} />
              </button>
              <div className="text-center min-w-[120px]">
                <h3 className="text-sm font-semibold text-warroom-text">
                  {MONTH_NAMES[currentDate.month - 1]} {currentDate.year}
                </h3>
              </div>
              <button
                onClick={() => navigateMonth(1)}
                className="p-1.5 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>

          {tab === "activities" && (
            <p className="text-[11px] text-warroom-muted mt-1">Daily memory files and agent activity tracking</p>
          )}
          {tab === "personal" && (
            <div className="flex flex-wrap items-center gap-2 text-[11px] bg-warroom-bg rounded-lg px-2.5 py-1.5 mt-1">
              {googleStatus?.connected ? (
                <>
                  <div className="w-2 h-2 rounded-full bg-green-400" />
                  <span className="text-warroom-muted">
                    Synced with <span className="text-warroom-text">{googleStatus.email}</span>
                  </span>
                  {lastSync && (
                    <span className="text-warroom-muted/60">
                      · {lastSync.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  )}
                  <button
                    onClick={resyncCalendar}
                    disabled={syncing}
                    className="ml-auto flex items-center gap-1 text-warroom-muted hover:text-warroom-accent transition"
                    title="Resync now"
                  >
                    <Loader2 size={12} className={syncing ? "animate-spin" : ""} />
                    {syncing ? "Syncing..." : "Resync"}
                  </button>
                </>
              ) : (
                <>
                  <CalendarDays size={13} className="text-amber-400" />
                  <span className="text-warroom-muted">
                    Google Calendar not connected — go to <span className="text-warroom-accent">Settings → Email & Calendar</span> to connect.
                  </span>
                </>
              )}
            </div>
          )}

          {error && (
            <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Calendar Grid — Samsung-style: full width, tall rows, events inline */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {(loading || personalLoading) ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-warroom-accent" />
            </div>
          ) : (
            <div className="flex flex-col flex-1 min-h-0">
              {/* Day headers */}
              <div className="grid grid-cols-7 border-b border-warroom-border flex-shrink-0">
                {DAY_NAMES.map((d) => (
                  <div key={d} className="text-center py-1.5">
                    <span className="text-[11px] font-medium text-warroom-muted">{d}</span>
                  </div>
                ))}
              </div>

              {/* Calendar weeks */}
              <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
                {grid.map((week, wi) => (
                  <div key={wi} className="grid grid-cols-7 flex-1 min-h-[80px] border-b border-warroom-border/40">
                    {week.map((info, di) => {
                      const hasContent =
                        tab === "activities" ? info.hasMemory : info.dayEvents.length > 0;

                      return (
                        <button
                          key={di}
                          onClick={() => {
                            if (tab === "activities" && info.hasMemory) {
                              loadDayDetail(info.dateStr);
                            }
                            if (tab === "personal" && info.isCurrentMonth) {
                              openQuickAdd(info.dateStr);
                            }
                          }}
                          className={`
                            relative px-1 pt-1 pb-0.5 text-left transition-colors flex flex-col
                            ${di < 6 ? "border-r border-warroom-border/20" : ""}
                            ${!info.isCurrentMonth
                              ? "text-warroom-muted/40"
                              : hasContent
                                ? "hover:bg-warroom-accent/5 cursor-pointer"
                                : tab === "personal"
                                  ? "hover:bg-warroom-surface/50 cursor-pointer"
                                  : ""
                            }
                          `}
                        >
                          {/* Day number */}
                          <span className={`text-xs font-medium inline-flex items-center justify-center w-6 h-6 rounded-full mb-0.5 ${
                            info.isToday
                              ? "bg-warroom-accent text-white"
                              : !info.isCurrentMonth
                                ? "text-warroom-muted/40"
                                : "text-warroom-text"
                          }`}>
                            {info.day}
                          </span>

                          {/* Activity dot */}
                          {tab === "activities" && info.hasMemory && (
                            <div className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-warroom-accent rounded-full" />
                          )}

                          {/* Event chips — Samsung style */}
                          {tab === "personal" && info.dayEvents.length > 0 && (
                            <div className="flex flex-col gap-px overflow-hidden flex-1 min-w-0">
                              {info.dayEvents.slice(0, 3).map((ev) => (
                                <div
                                  key={ev.id}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedEvent(ev);
                                  }}
                                  className={`text-[9px] leading-tight px-1 py-px rounded-sm truncate text-white cursor-pointer hover:opacity-80 ${
                                    ev.source === "google"
                                      ? "bg-emerald-700"
                                      : EVENT_COLORS[ev.type || "default"] || EVENT_COLORS.default
                                  }`}
                                >
                                  {ev.source === "google" && <Globe size={7} className="mr-0.5 inline shrink-0" />}
                                  {ev.agent_assignments && ev.agent_assignments.length > 0 && <Bot size={7} className="mr-0.5 inline shrink-0" />}
                                  {ev.time ? `${ev.time} ` : ""}
                                  {ev.title}
                                </div>
                              ))}
                              {info.dayEvents.length > 3 && (
                                <span className="text-[8px] text-warroom-muted">+{info.dayEvents.length - 3}</span>
                              )}
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Activity Day Detail Modal ─────────────────────── */}
      {selectedDay && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={()=>{setSelectedDay(null);setDayDetail(null);}}>
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl max-w-4xl w-full max-h-[80vh] flex flex-col" onClick={(e)=>e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-warroom-border">
              <div className="flex items-center gap-3">
                <FileText size={20} className="text-warroom-accent" />
                <div>
                  <h3 className="font-semibold text-warroom-text">
                    {new Date(selectedDay + "T12:00:00").toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
                  </h3>
                  <p className="text-sm text-warroom-muted">Daily memory file</p>
                </div>
              </div>
              <button onClick={() => { setSelectedDay(null); setDayDetail(null); }} className="p-2 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition">
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {dayLoading ? (
                <div className="flex items-center justify-center py-12"><Loader2 size={24} className="animate-spin text-warroom-accent" /></div>
              ) : dayDetail ? (
                <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
                  <pre className="text-sm text-warroom-text font-mono whitespace-pre-wrap">{dayDetail.content}</pre>
                </div>
              ) : (
                <div className="text-center py-12 text-warroom-muted"><Eye size={24} className="mx-auto mb-2 opacity-20" /><p className="text-sm">No memory data for this day</p></div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Quick-Add Bar (bottom) ── */}
      {tab === "personal" && (
        <div className="flex items-center gap-2 px-3 py-2 border-t border-warroom-border bg-warroom-surface/80 flex-shrink-0">
          <input
            ref={quickAddInputRef}
            type="text"
            placeholder="Quick add event…"
            className="flex-1 bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder:text-warroom-muted/50 focus:outline-none focus:ring-1 focus:ring-warroom-accent"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.target as HTMLInputElement).value.trim()) {
                const today = new Date().toISOString().split("T")[0];
                const val = (e.target as HTMLInputElement).value.trim();
                saveEvent({ ...EMPTY_FORM, title: val, date: today });
                (e.target as HTMLInputElement).value = "";
              }
            }}
          />
          <button
            onClick={() => {
              const today = new Date().toISOString().split("T")[0];
              const inputVal = quickAddInputRef.current?.value?.trim() || "";
              setQuickAddTitle(inputVal);
              setQuickAddDate(today);
              if (quickAddInputRef.current) quickAddInputRef.current.value = "";
            }}
            className="w-10 h-10 rounded-full bg-warroom-muted/20 hover:bg-warroom-accent/20 flex items-center justify-center text-warroom-muted hover:text-warroom-accent transition flex-shrink-0"
          >
            <Plus size={20} />
          </button>
        </div>
      )}

      {/* ── Quick-Add Event Modal ─────────────────────────── */}
      {quickAddDate && (
        <QuickAddModal
          date={quickAddDate}
          initialTitle={quickAddTitle}
          onClose={() => { setQuickAddDate(null); setQuickAddTitle(""); }}
          onSave={(data) => saveEvent(data)}
          onMoreOptions={(data) => openFullEditor(data)}
        />
      )}

      {/* ── Event Detail Popover ──────────────────────────── */}
      {selectedEvent && (
        <EventDetailPopover
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onEdit={openEditFromEvent}
          onDelete={deleteEvent}
          onAssignmentsChange={handleEventAssignmentsChange}
        />
      )}

      {/* ── Full Event Editor Modal ──────────────────────── */}
      {fullEditorData && (
        <FullEventEditorModal
          initialData={fullEditorData.form}
          editingEvent={fullEditorData.event}
          onClose={() => setFullEditorData(null)}
          onSave={saveEvent}
        />
      )}
    </div>
  );
}
