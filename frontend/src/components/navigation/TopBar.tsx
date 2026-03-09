"use client";

import { useState, useRef, useEffect } from "react";
import { Search, Sun, Moon, User, LogOut, ChevronDown, Menu } from "lucide-react";
import NotificationBell from "@/components/notifications/NotificationBell";
import { useThemeContext } from "@/components/ui/ThemeProvider";

const SEARCH_SCOPES: Record<string, { label: string; placeholder: string }> = {
  dashboard: { label: "Everything", placeholder: "Search metrics, deals, contacts..." },
  chat: { label: "Everything", placeholder: "Search anything..." },
  leadgen: { label: "Leads", placeholder: "Search leads by name, location..." },
  prospects: { label: "Prospects", placeholder: "Search prospects..." },
  "crm-deals": { label: "Deals", placeholder: "Search deals..." },
  "crm-contacts": { label: "Contacts", placeholder: "Search contacts..." },
  email: { label: "Email", placeholder: "Search emails..." },
  pipeline: { label: "Content", placeholder: "Search content..." },
  social: { label: "Social", placeholder: "Search social accounts..." },
  settings: { label: "Settings", placeholder: "Search settings..." },
};

const DEFAULT_SCOPE = { label: "Search", placeholder: "Search..." };

interface TopBarProps {
  activeTab: string;
  userName?: string;
  onLogout: () => void;
  onSearch?: (query: string, scope: string) => void;
  onMenuToggle?: () => void; // hamburger for mobile sidebar
}

export default function TopBar({ activeTab, userName, onLogout, onSearch, onMenuToggle }: TopBarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const scope = SEARCH_SCOPES[activeTab] || DEFAULT_SCOPE;
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

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && searchQuery.trim() && onSearch) {
      onSearch(searchQuery.trim(), activeTab);
    }
  };

  return (
    <div className="bg-warroom-surface border-b border-warroom-border px-3 py-2.5 flex-shrink-0">
      <div className="flex items-center gap-2">
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

        {/* Search */}
        <div className="relative flex-1 max-w-xl">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder={scope.placeholder}
            className="w-full pl-9 pr-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text placeholder:text-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50"
          />
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-warroom-bg transition-colors text-warroom-muted hover:text-warroom-text" title="Toggle theme">
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </button>

          <NotificationBell />

          <div className="relative" ref={menuRef}>
            <button onClick={() => setShowUserMenu(!showUserMenu)} className="flex items-center gap-1.5 rounded-lg p-1.5 hover:bg-warroom-bg transition-colors">
              <div className="w-7 h-7 rounded-full bg-warroom-accent/20 flex items-center justify-center flex-shrink-0">
                <User size={14} className="text-warroom-accent" />
              </div>
              <ChevronDown size={13} className="text-warroom-muted hidden sm:block" />
            </button>
            {showUserMenu && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-warroom-surface border border-warroom-border rounded-xl shadow-xl py-1 z-50">
                {userName && <div className="px-3 py-2 text-sm font-medium border-b border-warroom-border text-warroom-text break-words">{userName}</div>}
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
