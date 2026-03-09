"use client";

import { useState } from "react";
import { Bot, Puzzle } from "lucide-react";
import dynamic from "next/dynamic";
import AgentManager from "./AgentManager";

const PanelLoader = () => (
  <div className="flex items-center justify-center h-64">
    <div className="animate-spin rounded-full h-8 w-8 border-2 border-warroom-accent border-t-transparent" />
  </div>
);

const SkillsManager = dynamic(
  () => import("@/components/dashboard/SkillsManager"),
  { loading: PanelLoader }
);
const AgentServiceMap = dynamic(
  () => import("@/components/agents/AgentServiceMap"),
  { loading: PanelLoader }
);

interface AgentFeaturePageProps {
  onNavigate: (tab: string, params?: Record<string, string>) => void;
}

const TABS = [
  { id: "agents", label: "Agents", icon: Bot },
  { id: "skills-store", label: "Skills Store", icon: Puzzle },
] as const;

type FeatureTab = (typeof TABS)[number]["id"];

export default function AgentFeaturePage({ onNavigate }: AgentFeaturePageProps) {
  const [activeTab, setActiveTab] = useState<FeatureTab>("agents");

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Tab Bar */}
      <div className="flex border-b border-warroom-border flex-shrink-0 px-6">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? "border-warroom-accent text-warroom-accent bg-warroom-accent/5"
                  : "border-transparent text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg"
              }`}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "agents" && (
          <div className="h-full overflow-y-auto p-6 space-y-8">
            <AgentManager onNavigate={onNavigate} />
            <div className="border-t border-warroom-border pt-6">
              <h3 className="text-sm font-semibold text-warroom-muted mb-4 px-1">
                Live Activity
              </h3>
              <AgentServiceMap />
            </div>
          </div>
        )}
        {activeTab === "skills-store" && <SkillsManager />}
      </div>
    </div>
  );
}
