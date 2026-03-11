"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import {
  MessageSquare, Share2, Film, Search,
  Users, BookOpen, GraduationCap, Building2,
  Mail, FileText, LayoutDashboard, Instagram, Youtube, BarChart3,
  ClipboardList, FileBarChart, Bot, Facebook, Twitter,
  CalendarDays, FileSignature, DollarSign, PhoneCall,
  BarChart2, PieChart, TrendingUp, UserPlus,
} from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import Sidebar from "@/components/navigation/Sidebar";
import TopBar from "@/components/navigation/TopBar";
import OutreachTimingBar from "@/components/OutreachTimingBar";
// MobileNav available for per-feature horizontal navs (not global layout)

const PanelLoader = () => (
  <div className="flex items-center justify-center h-64">
    <div className="animate-spin rounded-full h-8 w-8 border-2 border-warroom-accent border-t-transparent" />
  </div>
);

const ChatPanel = dynamic(() => import("@/components/chat/ChatPanel"), { loading: PanelLoader });
const KanbanPanel = dynamic(() => import("@/components/kanban/KanbanPanel"), { loading: PanelLoader });
const LibraryPanel = dynamic(() => import("@/components/library/LibraryPanel"), { loading: PanelLoader });
const EducatePanel = dynamic(() => import("@/components/library/EducatePanel"), { loading: PanelLoader });
const LeadgenPanel = dynamic(() => import("@/components/leadgen/LeadgenPanel"), { loading: PanelLoader });
const SettingsPanel = dynamic(() => import("@/components/settings/SettingsPanel"), { loading: PanelLoader });
const WorkflowsPanel = dynamic(() => import("@/components/workflows/WorkflowsPanel"), { loading: PanelLoader });
const ContactsManager = dynamic(() => import("@/components/crm/ContactsManager"), { loading: PanelLoader });
const SocialDashboard = dynamic(() => import("@/components/social/SocialDashboard"), { loading: PanelLoader });
const CampaignsPanel = dynamic(() => import("@/components/marketing/CampaignsPanel"), { loading: PanelLoader });
const EmailTemplatesPanel = dynamic(() => import("@/components/marketing/EmailTemplatesPanel"), { loading: PanelLoader });
const AgentFeaturePage = dynamic(() => import("@/components/agents/AgentFeaturePage"), { loading: PanelLoader });
const AgentEditPage = dynamic(() => import("@/components/agents/AgentEditPage"), { loading: PanelLoader });
const ContentPipeline = dynamic(() => import("@/components/content/ContentPipeline"), { loading: PanelLoader });
const CompetitorIntel = dynamic(() => import("@/components/intelligence/CompetitorIntel"), { loading: PanelLoader });
const CommandCenter = dynamic(() => import("@/components/dashboard/CommandCenter"), { loading: PanelLoader });
const ActivityCalendar = dynamic(() => import("@/components/dashboard/ActivityCalendar"), { loading: PanelLoader });
const PlatformContent = dynamic(() => import("@/components/content/PlatformContent"), { loading: PanelLoader });
const ContentTracker = dynamic(() => import("@/components/content/ContentTracker"), { loading: PanelLoader });
const ContractsPanel = dynamic(() => import("@/components/contracts/ContractsPanel"), { loading: PanelLoader });
const InvoicingPanel = dynamic(() => import("@/components/invoicing/InvoicingPanel"), { loading: PanelLoader });
const EmailInbox = dynamic(() => import("@/components/email/EmailInbox"), { loading: PanelLoader });
const ReportsOverview = dynamic(() => import("@/components/reports/ReportsOverview"), { loading: PanelLoader });
const ProspectsPanel = dynamic(() => import("@/components/prospects/ProspectsPanel"), { loading: PanelLoader });
const UnifiedPipeline = dynamic(() => import("@/components/crm/UnifiedPipeline"), { loading: PanelLoader });
const OrganizationsPanel = dynamic(() => import("@/components/crm/OrganizationsPanel"), { loading: PanelLoader });
const CommunicationsConsole = dynamic(() => import("@/components/communications/CommunicationsConsole"), { loading: PanelLoader });

function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-warroom-muted">
      <div className="text-4xl mb-4">🚧</div>
      <h3 className="text-lg font-medium mb-2">{title}</h3>
      <p className="text-sm">This feature is under development.</p>
    </div>
  );
}

// Sidebar section structure (inspired by RAWGROWTH War Room)
const SECTIONS = [
  {
    label: "COMMAND",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "chat", label: "Chat", icon: MessageSquare },
      { id: "agents", label: "Agents", icon: Bot },
      { id: "calendar", label: "Calendar", icon: CalendarDays },
      { id: "communications", label: "Comms", icon: PhoneCall },
      { id: "email", label: "Email", icon: Mail },
      { id: "kanban", label: "Tasks", icon: ClipboardList },
    ],
  },
  {
    label: "SOCIALS",
    items: [
      { id: "social", label: "Analytics", icon: Share2 },
      { id: "intelligence", label: "Competitor Intel", icon: FileBarChart },
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
      { id: "pipeline-board", label: "Sales Pipeline", icon: ClipboardList },
      { id: "prospects", label: "Prospects", icon: UserPlus },
      { id: "organizations", label: "Organizations", icon: Building2 },
      { id: "crm-contacts", label: "Contacts", icon: Users },
    ],
  },
  {
    label: "FINANCE",
    items: [
      { id: "finance", label: "Finance", icon: DollarSign, children: [
        { id: "invoices", label: "Invoices", icon: FileText },
        { id: "contracts", label: "Contracts", icon: FileSignature },
      ]},
      { id: "reports", label: "Reports", icon: BarChart2, children: [
        { id: "reports-overview", label: "Overview", icon: PieChart },
        { id: "reports-revenue", label: "Revenue", icon: DollarSign },
        { id: "reports-sales", label: "Sales Activity", icon: TrendingUp },
      ]},
    ],
  },
  {
    label: "TOOLS",
    items: [
      { id: "workflows", label: "Workflows", icon: Bot },
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
  | "dashboard" | "chat" | "agents" | "agent-create" | "agent-edit" | "calendar" | "communications" | "email" | "social" | "pipeline" | "intelligence" | "prospects"
  | "content-instagram" | "content-youtube" | "content-facebook" | "content-x"
  | "kanban" | "leadgen"
  | "pipeline-board" | "organizations" | "crm-contacts"
  | "library-search" | "library-educate"
  | "workflows"
  | "marketing-campaigns" | "marketing-templates"
  | "invoices" | "contracts"
  | "reports-overview" | "reports-revenue" | "reports-sales"
  | "settings";

function normalizeTab(tab: string | null): TabId {
  if (!tab) return "dashboard";
  if (tab === "content-tracker") return "social";
  if (tab === "automation") return "workflows";
  // Legacy redirects — skills and soul now live inside agents
  if (tab === "skills" || tab === "soul") return "agents";
  return tab as TabId;
}

// Map parent IDs to their children active check
const PARENT_CHILDREN: Record<string, string[]> = {
  library: ["library-search", "library-educate"],
  marketing: ["marketing-campaigns", "marketing-templates"],
  finance: ["invoices", "contracts", "reports-overview", "reports-revenue", "reports-sales"],
  reports: ["reports-overview", "reports-revenue", "reports-sales"],
};

// Tabs that should highlight a specific sidebar item
const TAB_ALIASES: Record<string, string> = {
  "agent-create": "agents",
  "agent-edit": "agents",
};

export default function Page() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen bg-warroom-bg text-warroom-muted">Loading…</div>}>
      <WarRoom />
    </Suspense>
  );
}

function WarRoom() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = normalizeTab(searchParams.get("tab"));
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleTabChange = useCallback((tab: string) => {
    const nextTab = normalizeTab(tab);
    setActiveTab(nextTab);
    router.push(`/?tab=${nextTab}`, { scroll: false });
  }, [router]);

  useEffect(() => {
    const rawTab = searchParams.get("tab");
    const nextTab = normalizeTab(rawTab);

    if (nextTab !== activeTab) {
      setActiveTab(nextTab);
    }

    if (rawTab === "content-tracker" || rawTab === "automation" || rawTab === "skills" || rawTab === "soul") {
      router.replace(`/?tab=${nextTab}`, { scroll: false });
    }
  }, [activeTab, router, searchParams]);

  const isChildActive = useCallback((parentId: string) => {
    const children = PARENT_CHILDREN[parentId];
    return children ? children.includes(activeTab) : false;
  }, [activeTab]);

  return (
    <div className="flex h-dvh bg-warroom-bg text-warroom-text overflow-hidden">
      <Sidebar
        menuSections={SECTIONS}
        activeTab={TAB_ALIASES[activeTab] || activeTab}
        setActiveTab={handleTabChange}
        isChildActive={isChildActive}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar
          activeTab={activeTab}
          userName={user?.name || user?.email}
          onLogout={logout}
          onMenuToggle={() => setSidebarOpen(true)}
        />
        <OutreachTimingBar />
        <main className="flex-1 overflow-hidden relative">
          {activeTab === "dashboard" && <CommandCenter />}
          {/* ChatPanel stays mounted (preserves WS + generating state across tab switches) */}
          <div className={activeTab === "chat" ? "contents" : "hidden"}>
            <ChatPanel />
          </div>
          {activeTab === "agents" && (
            <AgentFeaturePage onNavigate={(tab, params) => {
              const nextTab = normalizeTab(tab);
              setActiveTab(nextTab);
              if (params?.id) {
                router.push(`/?tab=${tab}&id=${params.id}`, { scroll: false });
              } else {
                router.push(`/?tab=${tab}`, { scroll: false });
              }
            }} />
          )}
          {activeTab === "agent-create" && (
            <AgentEditPage
              mode="create"
              onNavigate={(tab) => handleTabChange(tab)}
            />
          )}
          {activeTab === "agent-edit" && (
            <AgentEditPage
              mode="edit"
              agentId={searchParams.get("id") || undefined}
              onNavigate={(tab) => handleTabChange(tab)}
            />
          )}

          {activeTab === "social" && <SocialDashboard />}
          {activeTab === "content-instagram" && <PlatformContent platform="instagram" />}
          {activeTab === "content-youtube" && <PlatformContent platform="youtube" />}
          {activeTab === "content-facebook" && <PlatformContent platform="facebook" />}
          {activeTab === "content-x" && <PlatformContent platform="x" />}
          {activeTab === "pipeline" && <ContentPipeline />}
          {activeTab === "intelligence" && <CompetitorIntel />}
          {activeTab === "kanban" && <KanbanPanel />}
          {activeTab === "leadgen" && <LeadgenPanel />}
          {activeTab === "communications" && <CommunicationsConsole />}
          {activeTab === "prospects" && <ProspectsPanel />}
          {activeTab === "pipeline-board" && <UnifiedPipeline />}
          {activeTab === "organizations" && <OrganizationsPanel />}
          {activeTab === "crm-contacts" && <ContactsManager />}
          {activeTab === "library-search" && <LibraryPanel />}
          {activeTab === "library-educate" && <EducatePanel />}
          {activeTab === "workflows" && <WorkflowsPanel />}
          {activeTab === "marketing-campaigns" && <CampaignsPanel />}
          {activeTab === "marketing-templates" && <EmailTemplatesPanel />}
          {activeTab === "email" && <EmailInbox />}
          {activeTab === "calendar" && <ActivityCalendar />}

          {activeTab === "invoices" && <InvoicingPanel />}
          {activeTab === "contracts" && <ContractsPanel />}
          {activeTab === "reports-overview" && <ReportsOverview />}
          {activeTab === "reports-revenue" && <ComingSoon title="Revenue Reports" />}
          {activeTab === "reports-sales" && <ComingSoon title="Sales Activity" />}
          {activeTab === "settings" && <SettingsPanel />}
        </main>
      </div>
    </div>
  );
}
