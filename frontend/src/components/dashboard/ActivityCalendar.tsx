"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Calendar, ChevronLeft, ChevronRight, Clock, FileText, Loader2, Eye, X,
  Plus, Trash2, CalendarDays, Activity, ExternalLink
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

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
}

interface PersonalCalendarData {
  year: number;
  month: number;
  events: PersonalEvent[];
  google_connected: boolean;
}

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
  default: "bg-warroom-accent",
};

/* ── Main Component ─────────────────────────────────────── */

export default function ActivityCalendar() {
  const [tab, setTab] = useState<TabMode>("activities");
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
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [newEvent, setNewEvent] = useState({ title: "", date: "", time: "", end_time: "", description: "", type: "meeting" });
  const [selectedPersonalDay, setSelectedPersonalDay] = useState<string | null>(null);

  /* ── Activity Calendar Logic ──────────────────────────── */

  const loadCalendarData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const monthStr = `${currentDate.year}-${currentDate.month.toString().padStart(2, "0")}`;
      const response = await fetch(`${API}/api/calendar?month=${monthStr}`);
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
      const response = await fetch(`${API}/api/calendar/day/${day}`);
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
      const response = await fetch(`${API}/api/calendar/personal?month=${monthStr}`);
      if (!response.ok) throw new Error("Failed to load personal calendar");
      setPersonalData(await response.json());
    } catch {
      setPersonalData(null);
    } finally {
      setPersonalLoading(false);
    }
  }, [currentDate]);

  const createEvent = async () => {
    if (!newEvent.title || !newEvent.date) return;
    try {
      const resp = await fetch(`${API}/api/calendar/personal/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newEvent),
      });
      if (resp.ok) {
        setShowAddEvent(false);
        setNewEvent({ title: "", date: "", time: "", end_time: "", description: "", type: "meeting" });
        loadPersonalData();
      }
    } catch {}
  };

  const deleteEvent = async (eventId: string) => {
    try {
      await fetch(`${API}/api/calendar/personal/events/${eventId}`, { method: "DELETE" });
      loadPersonalData();
    } catch {}
  };

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

        // Activity data
        const hasMemory = calendarData?.days[dateStr]?.has_memory || false;
        const memoryData = calendarData?.days[dateStr];

        // Personal events for this day
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

  const grid = generateCalendarGrid();

  /* ── Render ───────────────────────────────────────────── */

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-auto">
      <div className="bg-warroom-surface border border-warroom-border rounded-2xl overflow-hidden flex-1 flex flex-col">
        {/* Header with Tabs */}
        <div className="border-b border-warroom-border p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1 bg-warroom-bg rounded-xl p-1">
              <button
                onClick={() => setTab("activities")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  tab === "activities"
                    ? "bg-warroom-accent text-white shadow-sm"
                    : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-surface"
                }`}
              >
                <Activity size={15} />
                Activities
              </button>
              <button
                onClick={() => setTab("personal")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  tab === "personal"
                    ? "bg-warroom-accent text-white shadow-sm"
                    : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-surface"
                }`}
              >
                <CalendarDays size={15} />
                Personal
              </button>
            </div>

            <div className="flex items-center gap-2">
              {tab === "personal" && (
                <button
                  onClick={() => {
                    setNewEvent((e) => ({ ...e, date: `${currentDate.year}-${String(currentDate.month).padStart(2, "0")}-01` }));
                    setShowAddEvent(true);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warroom-accent text-white text-sm hover:bg-warroom-accent/80 transition"
                >
                  <Plus size={14} />
                  Add Event
                </button>
              )}
              <button
                onClick={() => navigateMonth(-1)}
                className="p-2 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition"
              >
                <ChevronLeft size={16} />
              </button>
              <div className="text-center min-w-[160px]">
                <h3 className="font-semibold text-warroom-text">
                  {MONTH_NAMES[currentDate.month - 1]} {currentDate.year}
                </h3>
              </div>
              <button
                onClick={() => navigateMonth(1)}
                className="p-2 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          {tab === "activities" && (
            <p className="text-xs text-warroom-muted">Daily memory files and agent activity tracking</p>
          )}
          {tab === "personal" && !personalData?.google_connected && (
            <div className="flex items-center gap-2 text-xs text-warroom-muted bg-warroom-bg rounded-lg px-3 py-2">
              <CalendarDays size={13} className="text-amber-400" />
              <span>Google Calendar not connected — showing local events only.</span>
              <button className="text-warroom-accent hover:underline ml-1 flex items-center gap-1">
                Connect <ExternalLink size={10} />
              </button>
            </div>
          )}

          {error && (
            <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Calendar Grid */}
        <div className="flex-1 p-4">
          {(loading || personalLoading) ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-warroom-accent" />
            </div>
          ) : (
            <div>
              {/* Day headers */}
              <div className="grid grid-cols-7 gap-2 mb-2">
                {DAY_NAMES.map((d) => (
                  <div key={d} className="text-center py-2">
                    <span className="text-xs font-medium text-warroom-muted">{d}</span>
                  </div>
                ))}
              </div>

              {/* Calendar days */}
              <div className="space-y-2">
                {grid.map((week, wi) => (
                  <div key={wi} className="grid grid-cols-7 gap-2">
                    {week.map((info, di) => {
                      const hasContent =
                        tab === "activities" ? info.hasMemory : info.dayEvents.length > 0;

                      return (
                        <button
                          key={di}
                          onClick={() => {
                            if (tab === "activities" && info.hasMemory) loadDayDetail(info.dateStr);
                            if (tab === "personal") setSelectedPersonalDay(info.dateStr === selectedPersonalDay ? null : info.dateStr);
                          }}
                          className={`
                            relative rounded-lg p-2 text-sm transition-colors border min-h-[72px] flex flex-col
                            ${!info.isCurrentMonth
                              ? "text-warroom-muted bg-warroom-bg/50 border-transparent cursor-default"
                              : hasContent
                                ? "bg-warroom-accent/10 border-warroom-accent/30 hover:bg-warroom-accent/20 cursor-pointer"
                                : tab === "personal"
                                  ? "bg-warroom-bg border-warroom-border hover:bg-warroom-surface cursor-pointer"
                                  : "bg-warroom-bg border-warroom-border cursor-default"
                            }
                            ${info.isToday ? "ring-2 ring-warroom-accent" : ""}
                          `}
                        >
                          <span
                            className={`font-medium text-xs ${
                              !info.isCurrentMonth
                                ? "text-warroom-muted"
                                : info.isToday
                                  ? "text-warroom-accent"
                                  : "text-warroom-text"
                            }`}
                          >
                            {info.day}
                          </span>

                          {/* Activity indicator */}
                          {tab === "activities" && info.hasMemory && (
                            <>
                              <div className="absolute top-1 right-1 w-2 h-2 bg-warroom-accent rounded-full" />
                              {info.memoryData && (
                                <div className="mt-auto">
                                  <div className="text-[9px] text-warroom-muted bg-warroom-bg/80 rounded px-1">
                                    {Math.round(info.memoryData.size / 1024)}K
                                  </div>
                                </div>
                              )}
                            </>
                          )}

                          {/* Personal event dots */}
                          {tab === "personal" && info.dayEvents.length > 0 && (
                            <div className="mt-1 flex flex-col gap-0.5 overflow-hidden">
                              {info.dayEvents.slice(0, 2).map((ev) => (
                                <div
                                  key={ev.id}
                                  className={`text-[9px] px-1 rounded truncate text-white ${EVENT_COLORS[ev.type || "default"] || EVENT_COLORS.default}`}
                                >
                                  {ev.time ? `${ev.time} ` : ""}{ev.title}
                                </div>
                              ))}
                              {info.dayEvents.length > 2 && (
                                <span className="text-[9px] text-warroom-muted">+{info.dayEvents.length - 2} more</span>
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

        {/* Personal day detail panel */}
        {tab === "personal" && selectedPersonalDay && (
          <div className="border-t border-warroom-border p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-warroom-text">
                {new Date(selectedPersonalDay + "T12:00:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setNewEvent((e) => ({ ...e, date: selectedPersonalDay }));
                    setShowAddEvent(true);
                  }}
                  className="flex items-center gap-1 text-xs text-warroom-accent hover:underline"
                >
                  <Plus size={12} />
                  Add
                </button>
                <button onClick={() => setSelectedPersonalDay(null)} className="text-warroom-muted hover:text-warroom-text">
                  <X size={14} />
                </button>
              </div>
            </div>
            {(() => {
              const events = personalData?.events?.filter((e) => e.date === selectedPersonalDay) || [];
              if (events.length === 0) return <p className="text-xs text-warroom-muted">No events scheduled</p>;
              return (
                <div className="space-y-2">
                  {events.map((ev) => (
                    <div key={ev.id} className="flex items-start gap-3 p-2 bg-warroom-bg rounded-lg border border-warroom-border">
                      <div className={`w-1 h-full min-h-[32px] rounded-full ${EVENT_COLORS[ev.type || "default"] || EVENT_COLORS.default}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-warroom-text">{ev.title}</p>
                        {ev.time && (
                          <p className="text-xs text-warroom-muted flex items-center gap-1 mt-0.5">
                            <Clock size={10} />
                            {ev.time}{ev.end_time ? ` – ${ev.end_time}` : ""}
                          </p>
                        )}
                        {ev.description && <p className="text-xs text-warroom-muted mt-1">{ev.description}</p>}
                      </div>
                      {ev.source === "local" && (
                        <button onClick={() => deleteEvent(ev.id)} className="text-warroom-muted hover:text-red-400 transition p-1">
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>
        )}
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

      {/* ── Add Event Modal ───────────────────────────────── */}
      {showAddEvent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowAddEvent(false)}>
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-warroom-border">
              <h3 className="font-semibold text-warroom-text flex items-center gap-2">
                <Plus size={18} className="text-warroom-accent" />
                New Event
              </h3>
              <button onClick={() => setShowAddEvent(false)} className="p-1 rounded hover:bg-warroom-bg transition">
                <X size={16} className="text-warroom-muted" />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="text-xs text-warroom-muted mb-1 block">Title *</label>
                <input
                  value={newEvent.title}
                  onChange={(e) => setNewEvent((ev) => ({ ...ev, title: e.target.value }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                  placeholder="Customer call, deadline..."
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-warroom-muted mb-1 block">Date *</label>
                  <input
                    type="date"
                    value={newEvent.date}
                    onChange={(e) => setNewEvent((ev) => ({ ...ev, date: e.target.value }))}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                  />
                </div>
                <div>
                  <label className="text-xs text-warroom-muted mb-1 block">Type</label>
                  <select
                    value={newEvent.type}
                    onChange={(e) => setNewEvent((ev) => ({ ...ev, type: e.target.value }))}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                  >
                    <option value="meeting">Meeting</option>
                    <option value="call">Call</option>
                    <option value="task">Task</option>
                    <option value="deadline">Deadline</option>
                    <option value="personal">Personal</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-warroom-muted mb-1 block">Start Time</label>
                  <input
                    type="time"
                    value={newEvent.time}
                    onChange={(e) => setNewEvent((ev) => ({ ...ev, time: e.target.value }))}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                  />
                </div>
                <div>
                  <label className="text-xs text-warroom-muted mb-1 block">End Time</label>
                  <input
                    type="time"
                    value={newEvent.end_time}
                    onChange={(e) => setNewEvent((ev) => ({ ...ev, end_time: e.target.value }))}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-warroom-muted mb-1 block">Description</label>
                <textarea
                  value={newEvent.description}
                  onChange={(e) => setNewEvent((ev) => ({ ...ev, description: e.target.value }))}
                  rows={2}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                  placeholder="Notes..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-warroom-border">
              <button onClick={() => setShowAddEvent(false)} className="px-4 py-2 rounded-lg text-sm text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg transition">Cancel</button>
              <button
                onClick={createEvent}
                disabled={!newEvent.title || !newEvent.date}
                className="px-4 py-2 rounded-lg text-sm bg-warroom-accent text-white hover:bg-warroom-accent/80 disabled:opacity-30 transition"
              >
                Create Event
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
