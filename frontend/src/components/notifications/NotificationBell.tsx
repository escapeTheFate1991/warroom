"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Bell,
  BellOff,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Info,
  ListTodo,
  UserPlus,
  Calendar,
  Check,
  Trash2,
  X,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type NotificationType =
  | "alert"
  | "warning"
  | "success"
  | "info"
  | "task"
  | "lead"
  | "calendar";

interface NotificationData {
  link?: string;
  [key: string]: unknown;
}

interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  data?: NotificationData;
  read: boolean;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const POLL_INTERVAL_MS = 30_000;

const TYPE_META: Record<
  NotificationType,
  { icon: typeof Bell; color: string; emoji: string }
> = {
  alert:    { icon: AlertCircle,   color: "text-red-500",    emoji: "🔥" },
  warning:  { icon: AlertTriangle, color: "text-amber-500",  emoji: "⚠️" },
  success:  { icon: CheckCircle2,  color: "text-green-500",  emoji: "✅" },
  info:     { icon: Info,          color: "text-blue-500",    emoji: "🔔" },
  task:     { icon: ListTodo,      color: "text-purple-500",  emoji: "📋" },
  lead:     { icon: UserPlus,      color: "text-cyan-500",   emoji: "👤" },
  calendar: { icon: Calendar,      color: "text-orange-500", emoji: "📅" },
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/** Extract tab id from a notification link like "/prospects" → "prospects" */
function linkToTab(link: string): string | null {
  if (!link) return null;
  // Strip leading slash
  const tab = link.replace(/^\//, "");
  return tab || null;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

/* ---- Sound + Toast ------------------------------------------------ */

function playNotificationSound() {
  try {
    const ctx = new AudioContext();
    // Two-tone chime: C5 → E5
    [523.25, 659.25].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.15, ctx.currentTime + i * 0.15);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.15 + 0.4);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime + i * 0.15);
      osc.stop(ctx.currentTime + i * 0.15 + 0.4);
    });
  } catch { /* audio not available */ }
}

let _toastCallback: ((n: Notification) => void) | null = null;
export function onToast(cb: (n: Notification) => void) { _toastCallback = cb; }

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<Notification | null>(null);
  const [lastSeenId, setLastSeenId] = useState<string | null>(null);
  const router = useRouter();

  /* ---- Fetch ---------------------------------------------------- */

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/notifications`);
      if (!res.ok) return;
      const data = await res.json();
      const list: Notification[] = Array.isArray(data) ? data : (data.notifications ?? []);
      
      // Detect new unread notifications → sound + toast
      const unread = list.filter(n => !n.read);
      if (unread.length > 0 && lastSeenId !== null) {
        const newest = unread[0];
        if (newest.id !== lastSeenId) {
          playNotificationSound();
          setToast(newest);
          setTimeout(() => setToast(null), 8000);
        }
      }
      if (unread.length > 0) {
        setLastSeenId(unread[0].id);
      }
      
      setNotifications(list);
    } catch {
      // Silently ignore; will retry on next poll
    }
  }, [lastSeenId]);

  useEffect(() => {
    fetchNotifications();
    const id = setInterval(fetchNotifications, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchNotifications]);

  /* ---- Escape to close ------------------------------------------ */

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  /* ---- Actions -------------------------------------------------- */

  const markRead = async (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
    try {
      await authFetch(`${API}/api/notifications/${id}/read`, { method: "PATCH" });
    } catch { /* optimistic */ }
  };

  const handleNotificationClick = async (n: Notification) => {
    // Mark as read
    await markRead(n.id);

    // Navigate to linked tab if available
    const link = n.data?.link;
    if (link) {
      const tab = linkToTab(link);
      if (tab) {
        setOpen(false);
        router.push(`/?tab=${tab}`);
      }
    }
  };

  const markAllRead = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    try {
      await authFetch(`${API}/api/notifications/read-all`, { method: "POST" });
    } catch { /* optimistic */ }
  };

  const clearAll = async () => {
    setNotifications([]);
    try {
      await authFetch(`${API}/api/notifications`, { method: "DELETE" });
    } catch {
      fetchNotifications();
    }
  };

  /* ---- Derived -------------------------------------------------- */

  const unreadCount = notifications.filter((n) => !n.read).length;
  const sorted = [...notifications].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  /* ---- Render --------------------------------------------------- */

  return (
    <>
      {/* Toast Banner */}
      {toast && (
        <div className="fixed top-4 right-4 z-[9999] animate-in slide-in-from-top-2 fade-in duration-300 max-w-sm">
          <div className={`flex items-start gap-3 px-4 py-3 rounded-xl shadow-2xl border backdrop-blur-sm ${
            toast.type === "alert" || toast.type === "warning"
              ? "bg-red-500/10 border-red-500/30 text-red-300"
              : "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
          }`}>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">{toast.title}</p>
              <p className="text-xs opacity-80 mt-0.5 line-clamp-2">{toast.message}</p>
            </div>
            <button onClick={() => setToast(null)} className="text-warroom-muted hover:text-white mt-0.5">
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Bell Button */}
      <button
        onClick={() => setOpen(true)}
        className="relative p-2 rounded-lg hover:bg-warroom-surface transition-colors text-warroom-muted hover:text-warroom-text"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        aria-haspopup="dialog"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full leading-none">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Modal Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

          {/* Modal */}
          <div
            role="dialog"
            aria-label="Notifications"
            className="relative w-full max-w-md mx-4 bg-warroom-surface border border-warroom-border rounded-xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-warroom-border">
              <h2 className="text-base font-semibold text-warroom-text flex items-center gap-2">
                <Bell className="w-4.5 h-4.5" />
                Notifications
                {unreadCount > 0 && (
                  <span className="text-xs bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded-full">
                    {unreadCount} new
                  </span>
                )}
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={markAllRead}
                  className="flex items-center gap-1 text-xs text-warroom-muted hover:text-warroom-text transition-colors px-2 py-1 rounded hover:bg-warroom-bg"
                  title="Mark all read"
                >
                  <Check className="w-3.5 h-3.5" />
                  Read All
                </button>
                <button
                  onClick={clearAll}
                  className="flex items-center gap-1 text-xs text-warroom-muted hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-warroom-bg"
                  title="Clear all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear
                </button>
                <button
                  onClick={() => setOpen(false)}
                  className="p-1 rounded hover:bg-warroom-bg text-warroom-muted hover:text-warroom-text transition-colors ml-1"
                  aria-label="Close notifications"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* List */}
            <div className="max-h-[60vh] overflow-y-auto">
              {sorted.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-14 gap-2 text-warroom-muted">
                  <BellOff className="w-10 h-10 opacity-30" />
                  <span className="text-sm">No notifications</span>
                  <span className="text-xs opacity-60">You&apos;re all caught up</span>
                </div>
              ) : (
                sorted.map((n) => {
                  const meta = TYPE_META[n.type] ?? TYPE_META.info;
                  const Icon = meta.icon;
                  const hasLink = !!n.data?.link;

                  return (
                    <button
                      key={n.id}
                      onClick={() => handleNotificationClick(n)}
                      className={`w-full flex items-start gap-3 px-5 py-3.5 text-left transition-colors border-b border-warroom-border/30 last:border-0 ${
                        hasLink ? "cursor-pointer hover:bg-warroom-accent/5" : "hover:bg-warroom-bg/50"
                      } ${n.read ? "opacity-50" : ""}`}
                    >
                      <div className={`mt-0.5 shrink-0 ${meta.color}`}>
                        <Icon className="w-4.5 h-4.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-warroom-text truncate">
                            {n.title}
                          </span>
                          {!n.read && (
                            <span className="shrink-0 w-2 h-2 rounded-full bg-blue-500" />
                          )}
                        </div>
                        <p className="text-xs text-warroom-muted line-clamp-2 mt-0.5">
                          {n.message}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-warroom-muted/60">
                            {relativeTime(n.created_at)}
                          </span>
                          {hasLink && (
                            <span className="text-[10px] text-warroom-accent/60">
                              → View
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
