"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { ChevronLeft, ChevronRight, Zap, Settings } from "lucide-react";

interface MenuItem {
  id: string;
  label: string;
  icon: any;
  children?: readonly MenuItem[];
}

interface MenuSection {
  readonly label: string;
  readonly items: readonly MenuItem[];
}

interface SidebarProps {
  menuSections: readonly MenuSection[];
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isChildActive: (parentId: string) => boolean;
}

export default function Sidebar({ menuSections, activeTab, setActiveTab, isChildActive }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const leaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navItemRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("warroom_sidebar_collapsed");
    if (saved === "true") setCollapsed(true);
  }, []);

  useEffect(() => () => { if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current); }, []);

  const toggleCollapse = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("warroom_sidebar_collapsed", String(next));
  };

  const openDropdown = useCallback((tabId: string) => {
    if (leaveTimerRef.current) { clearTimeout(leaveTimerRef.current); leaveTimerRef.current = null; }
    const el = navItemRefs.current[tabId];
    if (el) {
      const rect = el.getBoundingClientRect();
      setDropdownPos({ top: rect.top, left: rect.right });
    }
    setHoveredTab(tabId);
  }, []);

  const scheduleClose = useCallback(() => {
    leaveTimerRef.current = setTimeout(() => { setHoveredTab(null); setDropdownPos(null); }, 150);
  }, []);

  return (
    <nav className={`${collapsed ? "w-14" : "w-[180px]"} bg-warroom-surface border-r border-warroom-border flex flex-col py-3 gap-0.5 flex-shrink-0 overflow-y-auto scrollbar-thin scrollbar-thumb-warroom-border scrollbar-track-transparent transition-all duration-200`}>
      {/* Logo */}
      <div className={`mb-4 flex items-center ${collapsed ? "justify-center px-0" : "gap-2.5 px-4"}`}>
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-warroom-accent to-purple-600 flex-shrink-0">
          <Zap size={18} className="text-white" />
        </div>
        {!collapsed && <span className="text-sm font-bold tracking-wide text-warroom-text/90">WAR ROOM</span>}
      </div>

      {/* Sections */}
      {menuSections.map((section, si) => (
        <div key={section.label} className={`w-full ${collapsed ? "px-1" : "px-2"}`}>
          {si > 0 && <div className="h-px bg-warroom-border/40 my-2.5" />}
          {!collapsed && <p className="text-[10px] text-warroom-text/40 font-semibold tracking-widest px-2 mb-1">{section.label}</p>}
          {section.items.map((item) => {
            const Icon = item.icon;
            const hasChildren = item.children && item.children.length > 0;
            const isActive = hasChildren ? isChildActive(item.id) : activeTab === item.id;

            return (
              <div key={item.id} className="relative"
                ref={(el) => { navItemRefs.current[item.id] = el; }}
                onMouseEnter={() => hasChildren && openDropdown(item.id)}
                onMouseLeave={scheduleClose}>
                <button
                  onClick={() => {
                    if (!hasChildren) setActiveTab(item.id);
                    else if (item.children?.[0]) setActiveTab(item.children[0].id);
                  }}
                  className={`w-full h-9 rounded-lg flex items-center ${collapsed ? "justify-center px-0" : "gap-2.5 px-2.5"} transition-all ${
                    isActive
                      ? "bg-warroom-accent/15 text-warroom-accent"
                      : "text-warroom-text/60 hover:text-warroom-text/90 hover:bg-warroom-border/30"
                  }`}
                  title={item.label}
                >
                  <Icon size={16} strokeWidth={1.5} className="flex-shrink-0" />
                  {!collapsed && <span className="text-[13px] font-medium">{item.label}</span>}
                </button>

                {/* Flyout dropdown */}
                {hasChildren && hoveredTab === item.id && dropdownPos && (
                  <div className="fixed pl-1"
                    style={{ top: dropdownPos.top, left: dropdownPos.left, zIndex: 9999 }}
                    onMouseEnter={() => openDropdown(item.id)}
                    onMouseLeave={scheduleClose}>
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl shadow-2xl shadow-black/40 py-1.5 min-w-[160px]">
                      {item.children!.map((child) => {
                        const ChildIcon = child.icon;
                        return (
                          <button key={child.id}
                            onClick={() => { setActiveTab(child.id); setHoveredTab(null); setDropdownPos(null); }}
                            className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-all ${
                              activeTab === child.id
                                ? "text-warroom-accent bg-warroom-accent/10"
                                : "text-warroom-text/70 hover:text-warroom-text hover:bg-warroom-border/30"
                            }`}>
                            <ChildIcon size={15} />
                            {child.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Settings */}
      <div className={`${collapsed ? "px-1" : "px-2"} mb-1`}>
        <button onClick={() => setActiveTab("settings")}
          className={`w-full h-9 rounded-lg flex items-center ${collapsed ? "justify-center px-0" : "gap-2.5 px-2.5"} transition-all ${
            activeTab === "settings" ? "bg-warroom-accent/15 text-warroom-accent" : "text-warroom-text/50 hover:text-warroom-text/80 hover:bg-warroom-border/30"
          }`}
          title="Settings">
          <Settings size={16} strokeWidth={1.5} className="flex-shrink-0" />
          {!collapsed && <span className="text-[13px] font-medium">Settings</span>}
        </button>
      </div>

      {/* Collapse toggle */}
      <div className={`${collapsed ? "px-1" : "px-2"} mb-2`}>
        <button onClick={toggleCollapse}
          className="w-full h-9 rounded-lg flex items-center justify-center text-warroom-text/40 hover:text-warroom-text/70 hover:bg-warroom-border/30 transition-all"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </nav>
  );
}

