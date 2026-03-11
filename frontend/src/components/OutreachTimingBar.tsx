"use client";

import { useState, useEffect, useCallback } from "react";
import { Phone, Mail, Clock, AlertTriangle, X } from "lucide-react";
import { API, authFetch } from "@/lib/api";

type AlertLevel = "peak" | "good" | "ok" | "bad" | "hidden";
type OutreachType = "call" | "email" | "both" | "none";

interface TimingInfo {
  level: AlertLevel;
  type: OutreachType;
  message: string;
  detail?: string;
}

function getTimingInfo(now: Date): TimingInfo {
  const hour = now.getHours();
  const minute = now.getMinutes();
  const time = hour + minute / 60;
  const day = now.getDay(); // 0=Sun, 6=Sat

  // Weekends — bad
  if (day === 0 || day === 6) {
    return { level: "bad", type: "none", message: "Weekend — outreach not recommended", detail: "Best days: Tue–Thu" };
  }

  // Monday/Friday — suboptimal
  const isSuboptimalDay = day === 1 || day === 5;

  // Lunch hour 12–1 PM — bad
  if (time >= 12 && time < 13) {
    return { level: "bad", type: "none", message: "Lunch hour — avoid outreach", detail: "12:00–1:00 PM" };
  }

  // Best cold call: 10–12 AM (pre-lunch)
  const isPeakCall1 = time >= 10 && time < 12;
  // Best cold call: 4–5 PM (end of day)
  const isPeakCall2 = time >= 16 && time < 17;
  // Best cold email: 8–10 AM (early morning)
  const isPeakEmail1 = time >= 8 && time < 10;
  // Best cold email: 1–3 PM (post-lunch)
  const isPeakEmail2 = time >= 13 && time < 15;

  const isBestDay = day >= 2 && day <= 4; // Tue, Wed, Thu

  // Peak windows on best days
  if (isBestDay) {
    // Overlapping windows
    if (isPeakCall1 && isPeakEmail1) {
      // 10 AM is overlap of call (10-12) and email (8-10) — only at exactly 10
      // Actually 8-10 email, 10-12 call — no overlap
    }

    if (isPeakEmail1) {
      return {
        level: "peak",
        type: "email",
        message: "Prime email window — send now",
        detail: `8:00–10:00 AM · B2B/Corporate sweet spot`,
      };
    }

    if (isPeakCall1) {
      return {
        level: "peak",
        type: "call",
        message: "Peak cold call window",
        detail: "10:00 AM–12:00 PM · Pre-lunch prime time",
      };
    }

    if (isPeakEmail2) {
      return {
        level: "peak",
        type: "email",
        message: "Post-lunch email window",
        detail: "1:00–3:00 PM · Tech/Startup contacts respond well now",
      };
    }

    if (isPeakCall2) {
      return {
        level: "peak",
        type: "call",
        message: "End-of-day call window",
        detail: "4:00–5:00 PM · Decision-makers wrapping up",
      };
    }

    // Industry-specific secondary windows on best days
    if (time >= 6 && time < 8) {
      return {
        level: "good",
        type: "call",
        message: "Executive outreach window",
        detail: "6:00–8:00 AM · C-suite available early",
      };
    }

    if (time >= 15 && time < 16) {
      return {
        level: "good",
        type: "both",
        message: "Creative/Freelancer window",
        detail: "3:00–5:00 PM · Freelancers & creatives most responsive",
      };
    }
  }

  // Suboptimal days (Mon/Fri) but during good windows
  if (isSuboptimalDay) {
    if (isPeakEmail1) {
      return {
        level: "ok",
        type: "email",
        message: `${day === 1 ? "Monday" : "Friday"} — email window open`,
        detail: "8:00–10:00 AM · Response rates lower than mid-week",
      };
    }
    if (isPeakCall1) {
      return {
        level: "ok",
        type: "call",
        message: `${day === 1 ? "Monday" : "Friday"} — calling window`,
        detail: "10:00 AM–12:00 PM · Expect lower connect rates",
      };
    }
    if (isPeakEmail2) {
      return {
        level: "ok",
        type: "email",
        message: `${day === 1 ? "Monday" : "Friday"} — afternoon email window`,
        detail: "1:00–3:00 PM · Acceptable but not ideal",
      };
    }
    if (isPeakCall2) {
      return {
        level: "ok",
        type: "call",
        message: `${day === 1 ? "Monday" : "Friday"} — late call window`,
        detail: "4:00–5:00 PM · Some decision-makers available",
      };
    }
  }

  // Outside business hours
  if (time < 6 || time >= 20) {
    return { level: "hidden", type: "none", message: "", detail: "" };
  }

  // Business hours but no specific window
  if (time >= 17 && time < 20) {
    return { level: "bad", type: "none", message: "After hours — outreach not recommended", detail: "Resume tomorrow morning" };
  }

  return { level: "hidden", type: "none", message: "", detail: "" };
}

const LEVEL_STYLES: Record<AlertLevel, string> = {
  peak: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
  good: "bg-cyan-500/10 border-cyan-500/20 text-cyan-400",
  ok: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  bad: "bg-warroom-surface border-warroom-border text-warroom-muted",
  hidden: "",
};

const TYPE_ICONS: Record<OutreachType, typeof Phone | typeof Mail | typeof Clock> = {
  call: Phone,
  email: Mail,
  both: Clock,
  none: AlertTriangle,
};

export default function OutreachTimingBar() {
  const [timing, setTiming] = useState<TimingInfo | null>(null);
  const [enabled, setEnabled] = useState<boolean | null>(null); // null = loading
  const [dismissed, setDismissed] = useState(false);

  const checkTiming = useCallback(() => {
    setTiming(getTimingInfo(new Date()));
  }, []);

  // Load setting
  useEffect(() => {
    authFetch(`${API}/api/settings`)
      .then((r) => (r.ok ? r.json() : []))
      .then((items: { key: string; value: string }[]) => {
        const setting = items.find((s) => s.key === "outreach_timing_alerts");
        // Default to enabled if setting doesn't exist
        setEnabled(!setting || setting.value !== "disabled");
      })
      .catch(() => setEnabled(true));
  }, []);

  // Timer
  useEffect(() => {
    checkTiming();
    const interval = setInterval(checkTiming, 60_000);
    return () => clearInterval(interval);
  }, [checkTiming]);

  // Don't render if disabled, loading, dismissed, or hidden level
  if (enabled === null || !enabled || dismissed) return null;
  if (!timing || timing.level === "hidden") return null;

  const Icon = TYPE_ICONS[timing.type];

  return (
    <div className={`flex items-center gap-3 px-4 py-2 border-b text-sm ${LEVEL_STYLES[timing.level]}`}>
      <Icon size={16} className="shrink-0" />
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="font-medium truncate">{timing.message}</span>
        {timing.detail && (
          <span className="text-xs opacity-70 truncate hidden sm:inline">
            — {timing.detail}
          </span>
        )}
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="shrink-0 opacity-50 hover:opacity-100 transition"
        title="Dismiss for this session"
      >
        <X size={14} />
      </button>
    </div>
  );
}
