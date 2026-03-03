"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  MessageSquare, Zap, Settings, LogOut, Share2, Activity, Film, Eye, Search,
  UserSquare, Briefcase, Users, Calendar, BookOpen, GraduationCap, Package,
  Mail, FileText, LayoutGrid,
} from "lucide-react";
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
import AgentServiceMap from "@/components/agents/AgentServiceMap";
import ContentPipeline from "@/components/content/ContentPipeline";
import CompetitorIntel from "@/components/intelligence/CompetitorIntel";
import ActivityFeed from "@/components/agents/ActivityFeed";

// Sidebar section structure
const SECTIONS = [
  {
    label: "COMMAND",
    items: [
      { id: "chat", label: "Chat", icon: MessageSquare },
      { id: "agents", label: "Agents", icon: Activity },
      { id: "activity", label: "Activity", icon: Zap },
    ],
  },
  {
    label: "CONTENT",
    items: [
      { id: "social", label: "Social", icon: Share2 },
      { id: "pipeline", label: "Pipeline", icon: Film },
      { id: "intelligence", label: "Intel", icon: Eye },
    ],
  },
  {
    label: "OPERATIONS",
    items: [
      { id: "leadgen", label: "Leads", icon: Search },
      { id: "crm", label: "CRM", icon: UserSquare, children: [
        { id: "crm-deals", label: "Deals", icon: Briefcase },
        { id: "crm-contacts", label: "Contacts", icon: Users },
        { id: "crm-activities", label: "Activities", icon: Calendar },
        { id: "crm-products", label: "Products", icon: Package },
      ]},
      { id: "kanban", label: "Tasks", icon: LayoutGrid },
    ],
  },
  {
    label: "TOOLS",
    items: [
      { id: "library", label: "Library", icon: BookOpen, children: [
        { id: "library-search", label: "Search", icon: Search },
        { id: "library-educate", label: "Educate", icon: GraduationCap },
      ]},
      { id: "marketing", label: "Marketing", icon: Mail, children: [
        { id: "marketing-campaigns", label: "Campaigns", icon: Mail },
        { id: "marketing-templates", label: "Templates", icon: FileText },
      ]},
    ],
  },
] as const;

type TabId =
  | "chat" | "agents" | "activity" | "social" | "pipeline" | "intelligence"
  | "kanban" | "team" | "leadgen"
  | "crm-deals" | "crm-contacts" | "crm-activities" | "crm-products"
  | "library-search" | "library-educate"
  | "marketing-campaigns" | "marketing-templates"
  | "settings";

// Map parent IDs to their children active check
const PARENT_CHILDREN: Record<string, string[]> = {
  crm: ["crm-deals", "crm-contacts", "crm-activities", "crm-products"],
  library: ["library-search", "library-educate"],
  marketing: ["marketing-campaigns", "marketing-templates"],
};

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

  useEffect(() => {
    const tab = searchParams.get("tab") as TabId;
    if (tab && tab !== activeTab) setActiveTab(tab);
  }, [searchParams]);

  const isChildActive = (parentId: string) => {
    const children = PARENT_CHILDREN[parentId];
    return children ? children.includes(activeTab) : false;
  };

  return (
    <div className="flex h-screen bg-warroom-bg text-warroom-text">
      {/* Sidebar */}
      <nav className="w-[72px] bg-warroom-surface border-r border-warroom-border flex flex-col items-center py-3 gap-0.5 flex-shrink-0">
        {/* Logo */}
        <div className="mb-4 flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-warroom-accent to-purple-600">
          <Zap size={20} className="text-white" />
        </div>

        {/* Sections */}
        {SECTIONS.map((section, si) => (
          <div key={section.label} className="w-full px-2">
            {si > 0 && <div className="h-px bg-warroom-border/50 my-2" />}
            <p className="text-[8px] text-warroom-muted/60 font-bold tracking-widest text-center mb-1">{section.label}</p>
            {section.items.map((item) => {
              const Icon = item.icon;
              const hasChildren = "children" in item && item.children;
              const isActive = hasChildren ? isChildActive(item.id) : activeTab === item.id;

              return (
                <div key={item.id} className="relative"
                  onMouseEnter={() => hasChildren && openDropdown(item.id)}
                  onMouseLeave={scheduleClose}>
                  <button
                    onClick={() => {
                      if (!hasChildren) navigate(item.id as TabId);
                      else if (hasChildren) {
                        // Click parent → go to first child
                        const firstChild = (item as any).children[0];
                        if (firstChild) navigate(firstChild.id as TabId);
                      }
                    }}
                    className={`w-full h-11 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all ${
                      isActive
                        ? "bg-warroom-accent/15 text-warroom-accent"
                        : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/30"
                    }`}
                    title={item.label}
                  >
                    <Icon size={18} />
                    <span className="text-[9px] font-medium leading-none">{item.label}</span>
                  </button>

                  {/* Flyout dropdown for items with children */}
                  {hasChildren && hoveredTab === item.id && (
                    <div className="absolute left-full top-0 z-50 pl-1"
                      onMouseEnter={() => openDropdown(item.id)}
                      onMouseLeave={scheduleClose}>
                      <div className="bg-warroom-surface border border-warroom-border rounded-xl shadow-2xl shadow-black/40 py-1.5 min-w-[160px]">
                        {(item as any).children.map((child: any) => {
                          const ChildIcon = child.icon;
                          return (
                            <button key={child.id}
                              onClick={() => { navigate(child.id as TabId); setHoveredTab(null); }}
                              className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-all ${
                                activeTab === child.id
                                  ? "text-warroom-accent bg-warroom-accent/10"
                                  : "text-warroom-text hover:bg-warroom-border/30"
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

        {/* Spacer + Bottom */}
        <div className="flex-1" />

        <div className="px-2 mb-2">
          <div className="text-center mb-2">
            <div className="w-8 h-8 rounded-full bg-warroom-accent/20 flex items-center justify-center mx-auto">
              <span className="text-xs font-bold text-warroom-accent">{user?.name?.[0]?.toUpperCase()}</span>
            </div>
          </div>
        </div>

        <button onClick={() => navigate("settings")}
          className={`w-[56px] h-11 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-all ${
            activeTab === "settings" ? "bg-warroom-accent/15 text-warroom-accent" : "text-warroom-muted hover:text-warroom-text hover:bg-warroom-border/30"
          }`} title="Settings">
          <Settings size={18} />
          <span className="text-[9px] font-medium">Settings</span>
        </button>

        <button onClick={logout}
          className="w-[56px] h-11 rounded-lg flex flex-col items-center justify-center gap-0.5 text-warroom-muted hover:text-red-400 hover:bg-red-400/10 transition-all mb-1"
          title="Logout">
          <LogOut size={18} />
          <span className="text-[9px] font-medium">Logout</span>
        </button>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === "chat" && <ChatPanel />}
        {activeTab === "agents" && <AgentServiceMap />}
        {activeTab === "activity" && <ActivityFeed />}
        {activeTab === "social" && <SocialDashboard />}
        {activeTab === "pipeline" && <ContentPipeline />}
        {activeTab === "intelligence" && <CompetitorIntel />}
        {activeTab === "kanban" && <KanbanPanel />}
        {activeTab === "leadgen" && <LeadgenPanel />}
        {activeTab === "crm-deals" && <DealsKanban />}
        {activeTab === "crm-contacts" && <ContactsManager />}
        {activeTab === "crm-activities" && <ActivitiesPanel />}
        {activeTab === "crm-products" && <ProductsPanel />}
        {activeTab === "library-search" && <LibraryPanel />}
        {activeTab === "library-educate" && <EducatePanel />}
        {activeTab === "marketing-campaigns" && <CampaignsPanel />}
        {activeTab === "marketing-templates" && <EmailTemplatesPanel />}
        {activeTab === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
}
