"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import {
  MessageSquare, Share2, Film,
  LayoutDashboard, Instagram, Youtube, BarChart3,
  FileBarChart, Bot, Facebook,
  CalendarDays, Sparkles, Zap, Video, Settings,
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
const SettingsPanel = dynamic(() => import("@/components/settings/SettingsPanel"), { loading: PanelLoader });
const SocialDashboard = dynamic(() => import("@/components/dashboard/SocialDashboard"), { loading: PanelLoader });
const ContentPipeline = dynamic(() => import("@/components/content/ContentPipeline"), { loading: PanelLoader });
const CompetitorIntel = dynamic(() => import("@/components/intelligence/CompetitorIntel"), { loading: PanelLoader });
const ActivityCalendar = dynamic(() => import("@/components/dashboard/ActivityCalendar"), { loading: PanelLoader });
const ContentToSocial = dynamic(() => import("@/components/content/ContentToSocial"), { loading: PanelLoader });

// New Platform-Specific Pages
const InstagramPage = dynamic(() => import("@/components/social/platforms/InstagramPage"), { loading: PanelLoader });
const TikTokPage = dynamic(() => import("@/components/social/platforms/TikTokPage"), { loading: PanelLoader });
const YouTubeShortsPage = dynamic(() => import("@/components/social/platforms/YouTubeShortsPage"), { loading: PanelLoader });
const FacebookPage = dynamic(() => import("@/components/social/platforms/FacebookPage"), { loading: PanelLoader });

// Scheduler Components
const SchedulerCalendar = dynamic(() => import("@/components/scheduler/SchedulerCalendar"), { loading: PanelLoader });
const AIStudioPanel = dynamic(() => import("@/components/ai-studio/AIStudioPanel"), { loading: PanelLoader });
const AutoReplyPanel = dynamic(() => import("@/components/auto-reply/AutoReplyPanel"), { loading: PanelLoader });

function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-warroom-muted">
      <div className="text-4xl mb-4">🚧</div>
      <h3 className="text-lg font-medium mb-2">{title}</h3>
      <p className="text-sm">This feature is under development.</p>
    </div>
  );
}

// Sidebar section structure (socialRecycle focused)
const SECTIONS = [
  {
    label: "COMMAND",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "chat", label: "Chat", icon: MessageSquare },
      { id: "calendar", label: "Calendar", icon: CalendarDays },
    ],
  },
  {
    label: "CONTENT",
    items: [
      { id: "ai-studio", label: "AI Studio", icon: Sparkles },
      { id: "pipeline", label: "Content Pipeline", icon: Film },
      { id: "content-social", label: "URL → Social", icon: Share2 },
      { id: "scheduler", label: "Scheduler", icon: CalendarDays },
    ],
  },
  {
    label: "PLATFORMS",
    items: [
      { id: "social-instagram", label: "Instagram", icon: Instagram },
      { id: "social-tiktok", label: "TikTok", icon: Video },
      { id: "social-youtube", label: "YouTube Shorts", icon: Youtube },
      { id: "social-facebook", label: "Facebook", icon: Facebook },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { id: "intelligence", label: "Competitor Intel", icon: FileBarChart },
      { id: "social", label: "Analytics", icon: BarChart3 },
      { id: "mirofish", label: "Mirofish", icon: Zap },
    ],
  },
  {
    label: "AUTOMATION",
    items: [
      { id: "auto-reply", label: "Auto-Reply", icon: Bot },
    ],
  },
  {
    label: "SETTINGS",
    items: [
      { id: "settings", label: "Settings", icon: Settings },
    ],
  },
] as const;

type TabId =
  | "dashboard" | "chat" | "calendar" | "social" | "pipeline" | "content-social" | "intelligence" 
  | "social-instagram" | "social-tiktok" | "social-youtube" | "social-facebook"
  | "scheduler"
  | "ai-studio" | "auto-reply" | "mirofish"
  | "settings";

function normalizeTab(tab: string | null): TabId {
  if (!tab) return "dashboard";
  if (tab === "content-tracker") return "social";
  if (tab === "automation") return "auto-reply";
  // Legacy redirects for removed features
  if (tab === "agents" || tab === "skills" || tab === "soul") return "dashboard";
  if (tab === "workflows" || tab === "kanban" || tab === "leadgen") return "dashboard";
  if (tab === "organizations" || tab === "crm-contacts" || tab === "prospects") return "dashboard";
  return tab as TabId;
}

// Map parent IDs to their children active check (none for simplified social nav)
const PARENT_CHILDREN: Record<string, string[]> = {};

// Tabs that should highlight a specific sidebar item (none for simplified social nav)
const TAB_ALIASES: Record<string, string> = {};

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

    if (rawTab && rawTab !== nextTab) {
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
          onNavigate={handleTabChange}
        />
        <OutreachTimingBar />
        <main className="flex-1 overflow-hidden relative">
          {activeTab === "dashboard" && <SocialDashboard />}
          {/* ChatPanel stays mounted (preserves WS + generating state across tab switches) */}
          <div className={activeTab === "chat" ? "contents" : "hidden"}>
            <ChatPanel />
          </div>

          {activeTab === "social" && <SocialDashboard />}
          {activeTab === "pipeline" && <ContentPipeline />}
          {activeTab === "content-social" && <ContentToSocial />}
          
          {/* Platform-Specific Pages */}
          {activeTab === "social-instagram" && <InstagramPage />}
          {activeTab === "social-tiktok" && <TikTokPage />}
          {activeTab === "social-youtube" && <YouTubeShortsPage />}
          {activeTab === "social-facebook" && <FacebookPage />}
          
          {/* Scheduler Components */}
          {activeTab === "scheduler" && <SchedulerCalendar />}

          {activeTab === "intelligence" && <CompetitorIntel />}
          {activeTab === "calendar" && <ActivityCalendar />}
          {activeTab === "ai-studio" && <AIStudioPanel />}
          {activeTab === "auto-reply" && <AutoReplyPanel />}
          {activeTab === "mirofish" && <ComingSoon title="Mirofish" />}
          {activeTab === "settings" && <SettingsPanel />}
        </main>
      </div>
    </div>
  );
}
