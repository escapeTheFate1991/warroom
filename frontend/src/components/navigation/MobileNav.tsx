"use client";

import { useRef, useEffect } from "react";

interface NavItem {
  id: string;
  label: string;
  icon: any;
}

interface MobileNavProps {
  items: NavItem[];
  activeTab: string;
  onSelect: (id: string) => void;
}

/**
 * Horizontal scrolling tab nav for mobile + tablet.
 * Auto-scrolls to keep active tab visible.
 */
export default function MobileNav({ items, activeTab, onSelect }: MobileNavProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  // Auto-scroll active tab into view
  useEffect(() => {
    if (activeRef.current && scrollRef.current) {
      const container = scrollRef.current;
      const el = activeRef.current;
      const offset = el.offsetLeft - container.offsetWidth / 2 + el.offsetWidth / 2;
      container.scrollTo({ left: offset, behavior: "smooth" });
    }
  }, [activeTab]);

  return (
    <div
      ref={scrollRef}
      className="flex items-center gap-1 px-3 py-2 overflow-x-auto scrollbar-none bg-warroom-surface border-b border-warroom-border flex-shrink-0"
      style={{ WebkitOverflowScrolling: "touch" }}
    >
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            ref={isActive ? activeRef : undefined}
            onClick={() => onSelect(item.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all flex-shrink-0 ${
              isActive
                ? "bg-warroom-accent/15 text-warroom-accent"
                : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/30"
            }`}
          >
            <Icon size={14} strokeWidth={1.5} />
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
