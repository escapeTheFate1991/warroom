"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Calendar,
  Phone,
  Mail,
  MessageSquare,
  Coffee,
  CheckSquare,
  Users,
  Plus,
  Check,
  Clock,
  AlertTriangle,
  Filter,
  Trash2,
  Edit,
  X,
  MapPin,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Activity {
  id: number;
  title: string | null;
  type: string;
  comment: string | null;
  additional: any;
  location: string | null;
  schedule_from: string | null;
  schedule_to: string | null;
  is_done: boolean;
  user_id: number | null;
  created_at: string;
  updated_at: string;
}

const ACTIVITY_ICONS: Record<string, any> = {
  call: Phone,
  meeting: Users,
  note: MessageSquare,
  task: CheckSquare,
  email: Mail,
  lunch: Coffee,
};

const ACTIVITY_COLORS: Record<string, string> = {
  call: "text-green-400 bg-green-400/10",
  meeting: "text-blue-400 bg-blue-400/10",
  note: "text-yellow-400 bg-yellow-400/10",
  task: "text-purple-400 bg-purple-400/10",
  email: "text-cyan-400 bg-cyan-400/10",
  lunch: "text-orange-400 bg-orange-400/10",
};

type ViewMode = "all" | "upcoming" | "overdue";

export default function ActivitiesPanel() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("all");
  const [filterType, setFilterType] = useState<string>("");
  const [filterDone, setFilterDone] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [editingActivity, setEditingActivity] = useState<Activity | null>(null);
  const [types, setTypes] = useState<string[]>([]);

  // Form state
  const [formTitle, setFormTitle] = useState("");
  const [formType, setFormType] = useState("task");
  const [formComment, setFormComment] = useState("");
  const [formLocation, setFormLocation] = useState("");
  const [formFrom, setFormFrom] = useState("");
  const [formTo, setFormTo] = useState("");

  const loadActivities = useCallback(async () => {
    setLoading(true);
    try {
      let url = `${API}/api/crm/activities`;
      if (viewMode === "upcoming") url = `${API}/api/crm/activities/upcoming?days_ahead=14`;
      else if (viewMode === "overdue") url = `${API}/api/crm/activities/overdue`;
      else {
        const params = new URLSearchParams();
        if (filterType) params.set("activity_type", filterType);
        if (filterDone === "done") params.set("is_done", "true");
        if (filterDone === "pending") params.set("is_done", "false");
        if (params.toString()) url += `?${params}`;
      }
      const res = await fetch(url);
      if (res.ok) setActivities(await res.json());
    } catch (err) {
      console.error("Failed to load activities:", err);
    }
    setLoading(false);
  }, [viewMode, filterType, filterDone]);

  const loadTypes = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/crm/activities/types`);
      if (res.ok) {
        const data = await res.json();
        setTypes(data.types || []);
      }
    } catch {}
  }, []);

  useEffect(() => {
    loadActivities();
    loadTypes();
  }, [loadActivities, loadTypes]);

  function resetForm() {
    setFormTitle("");
    setFormType("task");
    setFormComment("");
    setFormLocation("");
    setFormFrom("");
    setFormTo("");
    setEditingActivity(null);
    setShowForm(false);
  }

  function openEdit(activity: Activity) {
    setEditingActivity(activity);
    setFormTitle(activity.title || "");
    setFormType(activity.type);
    setFormComment(activity.comment || "");
    setFormLocation(activity.location || "");
    setFormFrom(activity.schedule_from ? activity.schedule_from.slice(0, 16) : "");
    setFormTo(activity.schedule_to ? activity.schedule_to.slice(0, 16) : "");
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: any = {
      title: formTitle || null,
      type: formType,
      comment: formComment || null,
      location: formLocation || null,
      schedule_from: formFrom ? new Date(formFrom).toISOString() : null,
      schedule_to: formTo ? new Date(formTo).toISOString() : null,
    };

    try {
      const url = editingActivity
        ? `${API}/api/crm/activities/${editingActivity.id}`
        : `${API}/api/crm/activities`;
      const res = await fetch(url, {
        method: editingActivity ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        resetForm();
        loadActivities();
      }
    } catch (err) {
      console.error("Failed to save activity:", err);
    }
  }

  async function toggleDone(activity: Activity) {
    try {
      if (!activity.is_done) {
        await fetch(`${API}/api/crm/activities/${activity.id}/done`, { method: "PUT" });
      } else {
        await fetch(`${API}/api/crm/activities/${activity.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_done: false }),
        });
      }
      loadActivities();
    } catch {}
  }

  async function deleteActivity(id: number) {
    if (!confirm("Delete this activity?")) return;
    try {
      await fetch(`${API}/api/crm/activities/${id}`, { method: "DELETE" });
      loadActivities();
    } catch {}
  }

  function formatDateTime(iso: string | null) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
      " " +
      d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }

  function isOverdue(activity: Activity) {
    if (activity.is_done || !activity.schedule_to) return false;
    return new Date(activity.schedule_to) < new Date();
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Calendar size={16} />
          Activities
        </h2>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 text-white rounded-lg text-xs transition-colors"
        >
          <Plus size={14} />
          New Activity
        </button>
      </div>

      {/* Filters */}
      <div className="px-6 py-3 border-b border-warroom-border flex items-center gap-3 flex-wrap">
        {/* View mode tabs */}
        <div className="flex bg-warroom-surface rounded-lg p-0.5 border border-warroom-border">
          {([["all", "All"], ["upcoming", "Upcoming"], ["overdue", "Overdue"]] as const).map(([mode, label]) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                viewMode === mode
                  ? "bg-warroom-accent text-white"
                  : "text-warroom-muted hover:text-warroom-text"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {viewMode === "all" && (
          <>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-2 py-1 text-xs bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text"
            >
              <option value="">All Types</option>
              {types.map((t) => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
            <select
              value={filterDone}
              onChange={(e) => setFilterDone(e.target.value)}
              className="px-2 py-1 text-xs bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="done">Done</option>
            </select>
          </>
        )}

        <span className="text-xs text-warroom-muted ml-auto">
          {activities.length} activit{activities.length === 1 ? "y" : "ies"}
        </span>
      </div>

      {/* New/Edit Activity Form */}
      {showForm && (
        <div className="px-6 py-4 border-b border-warroom-border bg-warroom-surface/50">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-warroom-text">
                {editingActivity ? "Edit Activity" : "New Activity"}
              </h3>
              <button type="button" onClick={resetForm} className="text-warroom-muted hover:text-warroom-text">
                <X size={14} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                placeholder="Title"
                className="col-span-2 px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text"
              >
                {types.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
              <input
                type="text"
                value={formLocation}
                onChange={(e) => setFormLocation(e.target.value)}
                placeholder="Location (optional)"
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <input
                type="datetime-local"
                value={formFrom}
                onChange={(e) => setFormFrom(e.target.value)}
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text focus:outline-none focus:border-warroom-accent"
              />
              <input
                type="datetime-local"
                value={formTo}
                onChange={(e) => setFormTo(e.target.value)}
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text focus:outline-none focus:border-warroom-accent"
              />
              <textarea
                value={formComment}
                onChange={(e) => setFormComment(e.target.value)}
                placeholder="Notes..."
                rows={2}
                className="col-span-2 px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent resize-none"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={resetForm}
                className="px-3 py-1.5 text-xs text-warroom-muted hover:text-warroom-text"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 text-xs bg-warroom-accent hover:bg-warroom-accent/80 text-white rounded-lg"
              >
                {editingActivity ? "Update" : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Activity List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-warroom-accent border-t-transparent" />
          </div>
        ) : activities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-warroom-muted">
            <Calendar size={32} className="mb-2 opacity-20" />
            <p className="text-xs">
              {viewMode === "overdue" ? "No overdue activities" : viewMode === "upcoming" ? "No upcoming activities" : "No activities yet"}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-warroom-border">
            {activities.map((activity) => {
              const Icon = ACTIVITY_ICONS[activity.type] || Calendar;
              const colorClass = ACTIVITY_COLORS[activity.type] || "text-gray-400 bg-gray-400/10";
              const overdue = isOverdue(activity);

              return (
                <div
                  key={activity.id}
                  className={`px-6 py-3 hover:bg-warroom-surface/50 transition-colors group ${
                    activity.is_done ? "opacity-60" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Done toggle */}
                    <button
                      onClick={() => toggleDone(activity)}
                      className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                        activity.is_done
                          ? "bg-green-500 border-green-500 text-white"
                          : "border-warroom-border hover:border-warroom-accent"
                      }`}
                    >
                      {activity.is_done && <Check size={12} />}
                    </button>

                    {/* Icon */}
                    <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${colorClass}`}>
                      <Icon size={16} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${activity.is_done ? "line-through text-warroom-muted" : "text-warroom-text"}`}>
                          {activity.title || `${activity.type.charAt(0).toUpperCase() + activity.type.slice(1)}`}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-warroom-surface text-warroom-muted border border-warroom-border">
                          {activity.type}
                        </span>
                        {overdue && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 flex items-center gap-1">
                            <AlertTriangle size={10} />
                            Overdue
                          </span>
                        )}
                      </div>

                      {activity.comment && (
                        <p className="text-xs text-warroom-muted mt-0.5 line-clamp-2">{activity.comment}</p>
                      )}

                      <div className="flex items-center gap-3 mt-1">
                        {activity.schedule_from && (
                          <span className="text-[10px] text-warroom-muted flex items-center gap-1">
                            <Clock size={10} />
                            {formatDateTime(activity.schedule_from)}
                            {activity.schedule_to && ` → ${formatDateTime(activity.schedule_to)}`}
                          </span>
                        )}
                        {activity.location && (
                          <span className="text-[10px] text-warroom-muted flex items-center gap-1">
                            <MapPin size={10} />
                            {activity.location}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => openEdit(activity)}
                        className="p-1 text-warroom-muted hover:text-warroom-accent transition-colors"
                      >
                        <Edit size={13} />
                      </button>
                      <button
                        onClick={() => deleteActivity(activity.id)}
                        className="p-1 text-warroom-muted hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
