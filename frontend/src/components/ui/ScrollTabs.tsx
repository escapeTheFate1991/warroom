"use client";

import { useRef, useEffect } from "react";

interface Tab {
  id: string;
  label: string;
  icon?: any;
  count?: number | string;
}

interface ScrollTabsProps {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
  size?: "sm" | "md";
}

/**
 * Horizontally scrollable tab bar for mobile.
 * Scrolls active tab into view. Hides scrollbar.
 */
export default function ScrollTabs({ tabs, active, onChange, size = "md" }: ScrollTabsProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (activeRef.current && scrollRef.current) {
      const container = scrollRef.current;
      const el = activeRef.current;
      const offset = el.offsetLeft - container.offsetWidth / 2 + el.offsetWidth / 2;
      container.scrollTo({ left: Math.max(0, offset), behavior: "smooth" });
    }
  }, [active]);

  const py = size === "sm" ? "py-2" : "py-3";
  const px = size === "sm" ? "px-3" : "px-4";
  const textSize = size === "sm" ? "text-xs" : "text-sm";

  return (
    <div
      ref={scrollRef}
      className="flex overflow-x-auto scrollbar-none border-b border-warroom-border bg-warroom-surface flex-shrink-0"
      style={{ WebkitOverflowScrolling: "touch" }}
    >
      {tabs.map((tab) => {
        const isActive = active === tab.id;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            ref={isActive ? activeRef : undefined}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-1.5 ${px} ${py} ${textSize} font-medium border-b-2 transition whitespace-nowrap flex-shrink-0 ${
              isActive
                ? "text-warroom-accent border-warroom-accent bg-warroom-accent/5"
                : "text-warroom-muted border-transparent hover:text-warroom-text"
            }`}
          >
            {Icon && <Icon size={size === "sm" ? 14 : 16} />}
            {tab.label}
            {tab.count !== undefined && (
              <span className="text-xs bg-warroom-bg px-1.5 py-0.5 rounded-full">{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
