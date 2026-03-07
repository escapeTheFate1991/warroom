"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import {
  MessageSquare, Share2, Film, Search,
  UserSquare, Users, Calendar, BookOpen, GraduationCap, Package,
  Mail, FileText, LayoutDashboard, Instagram, Youtube,
  ClipboardList, FileBarChart, Bot, Facebook, Twitter,
  CalendarDays, Puzzle, Heart, Inbox, FileSignature, DollarSign,
  BarChart2, PieChart, TrendingUp, UserPlus,
} from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import Sidebar from "@/components/navigation/Sidebar";
import TopBar from "@/components/navigation/TopBar";

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
const ContactsManager = dynamic(() => import("@/components/crm/ContactsManager"), { loading: PanelLoader });
const ActivitiesPanel = dynamic(() => import("@/components/crm/ActivitiesPanel"), { loading: PanelLoader });
const ProductsPanel = dynamic(() => import("@/components/crm/ProductsPanel"), { loading: PanelLoader });
const SocialDashboard = dynamic(() => import("@/components/social/SocialDashboard"), { loading: PanelLoader });
const CampaignsPanel = dynamic(() => import("@/components/marketing/CampaignsPanel"), { loading: PanelLoader });
const EmailTemplatesPanel = dynamic(() => import("@/components/marketing/EmailTemplatesPanel"), { loading: PanelLoader });
const AgentServiceMap = dynamic(() => import("@/components/agents/AgentServiceMap"), { loading: PanelLoader });
const AgentManager = dynamic(() => import("@/components/agents/AgentManager"), { loading: PanelLoader });
const ContentPipeline = dynamic(() => import("@/components/content/ContentPipeline"), { loading: PanelLoader });
const CompetitorIntel = dynamic(() => import("@/components/intelligence/CompetitorIntel"), { loading: PanelLoader });
const CommandCenter = dynamic(() => import("@/components/dashboard/CommandCenter"), { loading: PanelLoader });
const SkillsManager = dynamic(() => import("@/components/dashboard/SkillsManager"), { loading: PanelLoader });
const SoulEditor = dynamic(() => import("@/components/dashboard/SoulEditor"), { loading: PanelLoader });
const ActivityCalendar = dynamic(() => import("@/components/dashboard/ActivityCalendar"), { loading: PanelLoader });
const PlatformContent = dynamic(() => import("@/components/content/PlatformContent"), { loading: PanelLoader });
const ContactSubmissions = dynamic(() => import("@/components/crm/ContactSubmissions"), { loading: PanelLoader });
const ContractsPanel = dynamic(() => import("@/components/contracts/ContractsPanel"), { loading: PanelLoader });
const InvoicingPanel = dynamic(() => import("@/components/invoicing/InvoicingPanel"), { loading: PanelLoader });
const EmailInbox = dynamic(() => import("@/components/email/EmailInbox"), { loading: PanelLoader });
const ReportsOverview = dynamic(() => import("@/components/reports/ReportsOverview"), { loading: PanelLoader });
const ProspectsPanel = dynamic(() => import("@/components/prospects/ProspectsPanel"), { loading: PanelLoader });
const UnifiedPipeline = dynamic(() => import("@/components/crm/UnifiedPipeline"), { loading: PanelLoader });

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
      { id: "crm", label: "CRM", icon: UserSquare, children: [
        { id: "crm-contacts", label: "Contacts", icon: Users },
        { id: "crm-activities", label: "Activities", icon: Calendar },
        { id: "crm-products", label: "Products", icon: Package },
        { id: "crm-submissions", label: "Submissions", icon: Inbox },
      ]},
      { id: "pipeline-board", label: "Sales Pipeline", icon: ClipboardList },
      { id: "leadgen", label: "Leads", icon: Search },
      { id: "prospects", label: "Prospects", icon: UserPlus },
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
  | "dashboard" | "chat" | "agents" | "calendar" | "email" | "social" | "pipeline" | "intelligence" | "prospects"
  | "content-instagram" | "content-youtube" | "content-facebook" | "content-x"
  | "kanban" | "leadgen"
  | "pipeline-board"
  | "crm-contacts" | "crm-activities" | "crm-products" | "crm-submissions"
  | "library-search" | "library-educate"
  | "marketing-campaigns" | "marketing-templates"
  | "skills" | "soul"
  | "invoices" | "contracts"
  | "reports-overview" | "reports-revenue" | "reports-sales"
  | "settings";

function normalizeTab(tab: string | null): TabId {
  if (!tab) return "dashboard";
  if (tab === "content-tracker") return "social";
  return tab as TabId;
}

// Map parent IDs to their children active check
const PARENT_CHILDREN: Record<string, string[]> = {
  crm: ["crm-contacts", "crm-activities", "crm-products", "crm-submissions"],
  library: ["library-search", "library-educate"],
  marketing: ["marketing-campaigns", "marketing-templates"],
  finance: ["invoices", "contracts", "reports-overview", "reports-revenue", "reports-sales"],
  reports: ["reports-overview", "reports-revenue", "reports-sales"],
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

    if (rawTab === "content-tracker") {
      router.replace("/?tab=social", { scroll: false });
    }
  }, [activeTab, router, searchParams]);

  const isChildActive = useCallback((parentId: string) => {
    const children = PARENT_CHILDREN[parentId];
    return children ? children.includes(activeTab) : false;
  }, [activeTab]);

  return (
    <div className="flex h-screen bg-warroom-bg text-warroom-text overflow-hidden">
      <Sidebar menuSections={SECTIONS} activeTab={activeTab} setActiveTab={handleTabChange} isChildActive={isChildActive} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar activeTab={activeTab} userName={user?.name || user?.email} onLogout={logout} />
        <main className="flex-1 overflow-hidden relative">
          {activeTab === "dashboard" && <CommandCenter />}
          {activeTab === "chat" && <ChatPanel />}
          {activeTab === "agents" && (
            <div className="h-full overflow-y-auto p-6 space-y-8">
              <AgentManager />
              <div className="border-t border-warroom-border pt-6">
                <h3 className="text-sm font-semibold text-warroom-muted mb-4 px-1">Live Activity</h3>
                <AgentServiceMap />
              </div>
            </div>
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
          {activeTab === "prospects" && <ProspectsPanel />}
          {activeTab === "pipeline-board" && <UnifiedPipeline />}
          {activeTab === "crm-contacts" && <ContactsManager />}
          {activeTab === "crm-activities" && <ActivitiesPanel />}
          {activeTab === "crm-products" && <ProductsPanel />}
          {activeTab === "crm-submissions" && <ContactSubmissions />}
          {activeTab === "library-search" && <LibraryPanel />}
          {activeTab === "library-educate" && <EducatePanel />}
          {activeTab === "marketing-campaigns" && <CampaignsPanel />}
          {activeTab === "marketing-templates" && <EmailTemplatesPanel />}
          {activeTab === "email" && <EmailInbox />}
          {activeTab === "calendar" && <ActivityCalendar />}
          {activeTab === "skills" && <SkillsManager />}
          {activeTab === "soul" && <SoulEditor />}
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
