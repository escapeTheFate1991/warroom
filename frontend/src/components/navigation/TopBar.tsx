"use client";

import { useState, useRef, useEffect } from "react";
import { Sun, Moon, User, LogOut, ChevronDown, Menu } from "lucide-react";
import NotificationBell from "@/components/notifications/NotificationBell";
import GlobalSearch from "@/components/GlobalSearch";
import { useThemeContext } from "@/components/ui/ThemeProvider";



interface TopBarProps {
  activeTab: string;
  userName?: string;
  onLogout: () => void;
  onMenuToggle?: () => void; // hamburger for mobile sidebar
  onNavigate?: (tab: string) => void;
}

export default function TopBar({ activeTab, userName, onLogout, onMenuToggle, onNavigate }: TopBarProps) {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { theme, toggleTheme } = useThemeContext();

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };
    if (showUserMenu) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showUserMenu]);



  return (
    <div className="bg-warroom-surface border-b border-warroom-border px-3 py-2.5 flex-shrink-0">
      <div className="flex items-center justify-center gap-2">
        {/* Hamburger (mobile only) */}
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="p-2 rounded-lg hover:bg-warroom-bg transition-colors text-warroom-muted hover:text-warroom-text lg:hidden flex-shrink-0"
            title="Menu"
          >
            <Menu size={20} />
          </button>
        )}

        {/* Global Search */}
        <GlobalSearch />

        {/* Actions sit right next to search */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-warroom-surface2/50 hover:shadow-glow-sm transition-all text-warroom-muted hover:text-warroom-text" title="Toggle theme">
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </button>

          <NotificationBell />

          <div className="relative" ref={menuRef}>
            <button onClick={() => setShowUserMenu(!showUserMenu)} className="flex items-center gap-1.5 rounded-lg p-1.5 hover:bg-warroom-surface2/50 hover:shadow-glow-sm transition-all">
              <div className="w-7 h-7 rounded-full bg-warroom-gradient flex items-center justify-center flex-shrink-0">
                <User size={14} className="text-white" />
              </div>
              <ChevronDown size={13} className="text-warroom-muted hidden sm:block" />
            </button>
            {showUserMenu && (
              <div className="absolute right-0 top-full mt-1 w-48 glass-card shadow-xl py-1 z-50">
                <button
                  onClick={() => { setShowUserMenu(false); onNavigate?.("profile"); }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-warroom-text hover:bg-warroom-bg transition-colors border-b border-warroom-border"
                >
                  <User size={14} className="text-warroom-accent" />
                  {userName || "Profile"}
                </button>
                <button onClick={onLogout} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-warroom-bg transition-colors">
                  <LogOut size={14} /> Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
