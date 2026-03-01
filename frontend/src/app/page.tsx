"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MessageSquare, LayoutGrid, Users, BookOpen, Search, Zap, Brain, GraduationCap, Settings, Calendar, UserSquare, Briefcase, Package, Mail, FileText, LogOut, Share2 } from "lucide-react";
import { AuthProvider, useAuth } from "@/components/AuthProvider";
import ChatPanel from "@/components/chat/ChatPanel";
import KanbanPanel from "@/components/kanban/KanbanPanel";
import TeamPanel from "@/components/team/TeamPanel";
import LibraryPanel from "@/components/library/LibraryPanel";
import EducatePanel from "@/components/library/EducatePanel";
import LeadgenPanel from "@/components/leadgen/LeadgenPanel";
import SettingsPanel from "@/components/settings/SettingsPanel";
import ContactsManager from "@/components/crm/ContactsManager";
import ActivitiesPanel from "@/components/crm/ActivitiesPanel";
import DealsKanban from "@/components/crm/DealsKanban";
import ProductsPanel from "@/components/crm/ProductsPanel";
import SocialDashboard from "@/components/social/SocialDashboard";
import CampaignsPanel from "@/components/marketing/CampaignsPanel";
import EmailTemplatesPanel from "@/components/marketing/EmailTemplatesPanel";

const TABS = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "kanban", label: "Tasks", icon: LayoutGrid },
  { id: "team", label: "Team", icon: Users },
  { id: "library", label: "Library", icon: BookOpen, children: [
    { id: "library-search", label: "Search", icon: Search },
    { id: "library-educate", label: "Educate", icon: GraduationCap },
  ]},
  { id: "crm", label: "CRM", icon: UserSquare, children: [
    { id: "crm-deals", label: "Deals", icon: Briefcase },
    { id: "crm-contacts", label: "Contacts", icon: Users },
    { id: "crm-activities", label: "Activities", icon: Calendar },
    { id: "crm-products", label: "Products", icon: Package },
  ]},
  { id: "leadgen", label: "Lead Gen", icon: Search },
  { id: "marketing", label: "Marketing", icon: Mail, children: [
    { id: "marketing-campaigns", label: "Campaigns", icon: Mail },
    { id: "marketing-templates", label: "Email Templates", icon: FileText },
    { id: "marketing-social", label: "Social Media", icon: Share2 },
  ]},
] as const;

type TabId = "chat" | "kanban" | "team" | "library-search" | "library-educate" | "crm-deals" | "crm-contacts" | "crm-activities" | "crm-products" | "leadgen" | "marketing-campaigns" | "marketing-templates" | "marketing-social" | "settings";

export default function Page() {
  return (
    <Suspense>
      <WarRoom />
    </Suspense>
  );
}

function WarRoom() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as TabId) || "chat";
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const leaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isLibraryActive = activeTab === "library-search" || activeTab === "library-educate";
  const isCrmActive = activeTab === "crm-deals" || activeTab === "crm-contacts" || activeTab === "crm-activities" || activeTab === "crm-products";
  const isMarketingActive = activeTab === "marketing-campaigns" || activeTab === "marketing-templates" || activeTab === "marketing-social";

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
            ? tab.id === "library" ? isLibraryActive : 
              tab.id === "crm" ? isCrmActive : 
              tab.id === "marketing" ? isMarketingActive : false
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

        {/* Spacer + User info + Settings at bottom */}
        <div className="flex-1" />
        
        {/* User info */}
        <div className="px-2 mb-3">
          <div className="text-center">
            <div className="w-8 h-8 rounded-full bg-warroom-accent flex items-center justify-center mx-auto mb-1">
              <span className="text-xs font-medium text-white">{user?.name?.[0]?.toUpperCase()}</span>
            </div>
            <span className="text-[9px] text-warroom-muted block">{user?.name}</span>
          </div>
        </div>

        {/* Settings button */}
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

        {/* Logout button */}
        <button
          onClick={logout}
          className="w-12 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all mb-2 text-warroom-muted hover:text-red-400 hover:bg-red-400/10"
          title="Logout"
        >
          <LogOut size={20} />
          <span className="text-[9px] font-medium">Logout</span>
        </button>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === "chat" && <ChatPanel />}
        {activeTab === "kanban" && <KanbanPanel />}
        {activeTab === "team" && <TeamPanel />}
        {activeTab === "library-search" && <LibraryPanel />}
        {activeTab === "library-educate" && <EducatePanel />}
        {activeTab === "crm-deals" && <DealsKanban />}
        {activeTab === "crm-contacts" && <ContactsManager />}
        {activeTab === "crm-activities" && <ActivitiesPanel />}
        {activeTab === "crm-products" && <ProductsPanel />}
        {activeTab === "leadgen" && <LeadgenPanel />}
        {activeTab === "marketing-campaigns" && <CampaignsPanel />}
        {activeTab === "marketing-templates" && <EmailTemplatesPanel />}
        {activeTab === "marketing-social" && <SocialDashboard />}
        {activeTab === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
}
