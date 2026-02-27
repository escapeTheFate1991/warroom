"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MessageSquare, LayoutGrid, Users, BookOpen, Search, Zap, Brain, GraduationCap, Settings } from "lucide-react";
import ChatPanel from "@/components/chat/ChatPanel";
import KanbanPanel from "@/components/kanban/KanbanPanel";
import TeamPanel from "@/components/team/TeamPanel";
import LibraryPanel from "@/components/library/LibraryPanel";
import EducatePanel from "@/components/library/EducatePanel";
import LeadgenPanel from "@/components/leadgen/LeadgenPanel";
import SettingsPanel from "@/components/settings/SettingsPanel";

const TABS = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "kanban", label: "Tasks", icon: LayoutGrid },
  { id: "team", label: "Team", icon: Users },
  { id: "library", label: "Library", icon: BookOpen, children: [
    { id: "library-search", label: "Search", icon: Search },
    { id: "library-educate", label: "Educate", icon: GraduationCap },
  ]},
  { id: "leadgen", label: "Lead Gen", icon: Search },
] as const;

type TabId = "chat" | "kanban" | "team" | "library-search" | "library-educate" | "leadgen" | "settings";

export default function Page() {
  return (
    <Suspense>
      <WarRoom />
    </Suspense>
  );
}

function WarRoom() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as TabId) || "chat";
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const leaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isLibraryActive = activeTab === "library-search" || activeTab === "library-educate";

  // Clean up leave-close timer on unmount
  useEffect(() => () => { if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current); }, []);

  const openDropdown = (tabId: string) => {
    if (leaveTimerRef.current) { clearTimeout(leaveTimerRef.current); leaveTimerRef.current = null; }
    setHoveredTab(tabId);
  };

  const scheduleClose = () => {
    leaveTimerRef.current = setTimeout(() => setHoveredTab(null), 150);
  };

  const navigate = (tab: TabId) => {
    setActiveTab(tab);
    router.push(`/?tab=${tab}`, { scroll: false });
  };

  // Sync with URL on back/forward
  useEffect(() => {
    const tab = searchParams.get("tab") as TabId;
    if (tab && tab !== activeTab) setActiveTab(tab);
  }, [searchParams]);

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-16 bg-warroom-surface border-r border-warroom-border flex flex-col items-center py-4 gap-1">
        <div className="mb-6 flex items-center justify-center w-10 h-10 rounded-lg bg-warroom-accent">
          <Zap size={20} className="text-white" />
        </div>
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const hasChildren = "children" in tab && tab.children;
          const isActive = hasChildren
            ? isLibraryActive
            : activeTab === tab.id;

          return (
            <div
              key={tab.id}
              className="relative w-16"
              onMouseEnter={() => hasChildren && openDropdown(tab.id)}
              onMouseLeave={scheduleClose}
            >
              <button
                onClick={() => !hasChildren && navigate(tab.id as TabId)}
                className={`w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all ${
                  isActive
                    ? "bg-warroom-accent/20 text-warroom-accent"
                    : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/50"
                }`}
                title={tab.label}
              >
                <Icon size={20} />
                <span className="text-[9px] font-medium">{tab.label}</span>
              </button>

              {/* Dropdown for Library — appears to the right of the nav column */}
              {hasChildren && hoveredTab === tab.id && (
                <div
                  className="absolute left-full top-0 z-50 pl-1"
                  onMouseEnter={() => openDropdown(tab.id)}
                  onMouseLeave={scheduleClose}
                >
                  <div className="bg-warroom-surface border border-warroom-border rounded-lg shadow-xl py-2 min-w-[180px]">
                    {tab.children.map((child) => {
                      const ChildIcon = child.icon;
                      return (
                        <button
                          key={child.id}
                          onClick={() => {
                            navigate(child.id as TabId);
                            setHoveredTab(null);
                          }}
                          className={`w-full flex items-center gap-3 px-5 py-3 text-sm transition-all ${
                            activeTab === child.id
                              ? "text-warroom-accent bg-warroom-accent/10"
                              : "text-warroom-text hover:bg-warroom-border/50"
                          }`}
                        >
                          <ChildIcon size={16} />
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

        {/* Spacer + Settings at bottom */}
        <div className="flex-1" />
        <button
          onClick={() => navigate("settings")}
          className={`w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all mb-2 ${
            activeTab === "settings"
              ? "bg-warroom-accent/20 text-warroom-accent"
              : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/50"
          }`}
          title="Settings"
        >
          <Settings size={20} />
          <span className="text-[9px] font-medium">Settings</span>
        </button>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === "chat" && <ChatPanel />}
        {activeTab === "kanban" && <KanbanPanel />}
        {activeTab === "team" && <TeamPanel />}
        {activeTab === "library-search" && <LibraryPanel />}
        {activeTab === "library-educate" && <EducatePanel />}
        {activeTab === "leadgen" && <LeadgenPanel />}
        {activeTab === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
}
