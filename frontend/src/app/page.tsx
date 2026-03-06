"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  MessageSquare, Zap, Settings, LogOut, Share2, Activity, Film, Eye, Search,
  UserSquare, Briefcase, Users, Calendar, BookOpen, GraduationCap, Package,
  Mail, FileText, LayoutGrid, LayoutDashboard, Instagram, Youtube, BarChart3,
  ClipboardList, FileBarChart, Telescope, Bot, Facebook, Twitter,
  CalendarDays, Puzzle, Heart,
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
import CommandCenter from "@/components/dashboard/CommandCenter";
import UsageWidget from "@/components/dashboard/UsageWidget";
import SkillsManager from "@/components/dashboard/SkillsManager";
import SoulEditor from "@/components/dashboard/SoulEditor";
import ActivityCalendar from "@/components/dashboard/ActivityCalendar";
import PlatformContent from "@/components/content/PlatformContent";
import ContentTracker from "@/components/content/ContentTracker";

// Sidebar section structure (inspired by RAWGROWTH War Room)
const SECTIONS = [
  {
    label: "COMMAND",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "chat", label: "Chat", icon: MessageSquare },
      { id: "agents", label: "Agents", icon: Bot },
      { id: "calendar", label: "Calendar", icon: CalendarDays },
      { id: "kanban", label: "Tasks", icon: ClipboardList },
    ],
  },
  {
    label: "SOCIALS",
    items: [
      { id: "content-tracker", label: "Tracker", icon: BarChart3 },
      { id: "social", label: "Analytics", icon: Share2 },
      { id: "intelligence", label: "Reports", icon: FileBarChart },
    ],
  },
  {
    label: "CONTENT",
    items: [
      { id: "pipeline", label: "Pipeline", icon: Film },
      { id: "content-instagram", label: "Instagram", icon: Instagram },
      { id: "content-youtube", label: "YouTube", icon: Youtube },
      { id: "content-facebook", label: "Facebook", icon: Facebook },
      { id: "content-x", label: "X", icon: Twitter },
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
    ],
  },
  {
    label: "TOOLS",
    items: [
      { id: "skills", label: "Skills", icon: Puzzle },
      { id: "soul", label: "Soul", icon: Heart },
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
  | "dashboard" | "chat" | "agents" | "activity" | "calendar" | "social" | "pipeline" | "intelligence"
  | "content-instagram" | "content-youtube" | "content-facebook" | "content-x" | "content-tracker"
  | "kanban" | "team" | "leadgen"
  | "crm-deals" | "crm-contacts" | "crm-activities" | "crm-products"
  | "library-search" | "library-educate"
  | "marketing-campaigns" | "marketing-templates"
  | "skills" | "soul"
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
  const initialTab = (searchParams.get("tab") as TabId) || "dashboard";
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
      <nav className="w-[180px] bg-warroom-surface border-r border-warroom-border flex flex-col py-3 gap-0.5 flex-shrink-0 overflow-y-auto scrollbar-thin scrollbar-thumb-warroom-border scrollbar-track-transparent">
        {/* Logo */}
        <div className="mb-4 flex items-center gap-2.5 px-4">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-warroom-accent to-purple-600">
            <Zap size={18} className="text-white" />
          </div>
          <span className="text-sm font-bold tracking-wide text-warroom-text/90">WAR ROOM</span>
        </div>

        {/* Sections */}
        {SECTIONS.map((section, si) => (
          <div key={section.label} className="w-full px-2">
            {si > 0 && <div className="h-px bg-warroom-border/40 my-2.5" />}
            <p className="text-[10px] text-warroom-text/40 font-semibold tracking-widest px-2 mb-1">{section.label}</p>
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
                        const firstChild = (item as any).children[0];
                        if (firstChild) navigate(firstChild.id as TabId);
                      }
                    }}
                    className={`w-full h-9 rounded-lg flex items-center gap-2.5 px-2.5 transition-all ${
                      isActive
                        ? "bg-warroom-accent/15 text-warroom-accent"
                        : "text-warroom-text/60 hover:text-warroom-text/90 hover:bg-warroom-border/30"
                    }`}
                    title={item.label}
                  >
                    <Icon size={16} strokeWidth={1.5} />
                    <span className="text-[13px] font-medium">{item.label}</span>
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

        {/* Spacer + Bottom */}
        <div className="flex-1" />

        <div className="px-2 mb-2">
          <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg bg-warroom-bg/40">
            <div className="w-7 h-7 rounded-full bg-warroom-accent/20 flex items-center justify-center flex-shrink-0">
              <span className="text-[11px] font-bold text-warroom-accent">{user?.name?.[0]?.toUpperCase()}</span>
            </div>
            <span className="text-xs font-medium text-warroom-text/70 truncate">{user?.name}</span>
          </div>
        </div>

        <div className="px-2 space-y-0.5 mb-2">
          <button onClick={() => navigate("settings")}
            className={`w-full h-9 rounded-lg flex items-center gap-2.5 px-2.5 transition-all ${
              activeTab === "settings" ? "bg-warroom-accent/15 text-warroom-accent" : "text-warroom-text/50 hover:text-warroom-text/80 hover:bg-warroom-border/30"
            }`}>
            <Settings size={16} strokeWidth={1.5} />
            <span className="text-[13px] font-medium">Settings</span>
          </button>

          <button onClick={logout}
            className="w-full h-9 rounded-lg flex items-center gap-2.5 px-2.5 text-warroom-text/50 hover:text-red-400 hover:bg-red-400/10 transition-all">
            <LogOut size={16} strokeWidth={1.5} />
            <span className="text-[13px] font-medium">Logout</span>
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-hidden relative">
        {activeTab === "dashboard" && <CommandCenter />}
        {activeTab === "chat" && <ChatPanel />}
        {activeTab === "agents" && <AgentServiceMap />}
        {activeTab === "activity" && <ActivityFeed />}
        {activeTab === "social" && <SocialDashboard />}
        {activeTab === "content-instagram" && <PlatformContent platform="instagram" />}
        {activeTab === "content-youtube" && <PlatformContent platform="youtube" />}
        {activeTab === "content-facebook" && <PlatformContent platform="facebook" />}
        {activeTab === "content-x" && <PlatformContent platform="x" />}
        {activeTab === "pipeline" && <ContentPipeline />}
        {activeTab === "content-tracker" && <ContentTracker />}
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
        {activeTab === "calendar" && <ActivityCalendar />}
        {activeTab === "skills" && <SkillsManager />}
        {activeTab === "soul" && <SoulEditor />}
        {activeTab === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
}
