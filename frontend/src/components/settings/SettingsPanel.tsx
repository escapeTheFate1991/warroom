"use client";

import { useState, useEffect, useCallback } from "react";
import { Settings, Key, Save, Eye, EyeOff, Check, AlertCircle, MapPin, Zap, Building2, Mail, Share2, Target, Bot, Shield } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Setting {
  key: string;
  value: string;
  category: string;
  description: string | null;
  is_secret: boolean;
}

const CATEGORY_META: Record<string, { label: string; icon: typeof Key; description: string }> = {
  api_keys: {
    label: "API Keys",
    icon: Key,
    description: "External service credentials for search, AI, and integrations",
  },
  general: {
    label: "General",
    icon: Building2,
    description: "Company info and general preferences",
  },
  leadgen: {
    label: "Lead Generation",
    icon: MapPin,
    description: "Configure lead search and enrichment behavior",
  },
};

const KEY_LABELS: Record<string, string> = {
  google_maps_api_key: "Google Maps API Key",
  serp_api_key: "SerpAPI Key",
  openai_api_key: "OpenAI API Key",
  company_name: "Company Name",
  default_search_location: "Default Search Location",
  max_search_results: "Max Search Results",
  auto_enrich: "Auto-Enrich Leads",
};

const SETTINGS_TABS = [
  { id: "general", label: "General", icon: Building2 },
  { id: "email", label: "Email Integration", icon: Mail },
  { id: "social", label: "Social Media", icon: Share2 },
  { id: "scoring", label: "Lead Scoring", icon: Target },
  { id: "automation", label: "Automation", icon: Bot },
  { id: "access", label: "Access Control", icon: Shield },
] as const;

type SettingsTab = typeof SETTINGS_TABS[number]["id"];

export default function SettingsPanel() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [settings, setSettings] = useState<Setting[]>([]);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const loadSettings = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/api/settings`);
      if (resp.ok) {
        const data = await resp.json();
        setSettings(data);
        // Initialize edit values with current values
        const vals: Record<string, string> = {};
        data.forEach((s: Setting) => {
          vals[s.key] = s.is_secret ? "" : s.value;
        });
        setEditValues(vals);
      }
    } catch {
      console.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  const saveSetting = async (key: string) => {
    const value = editValues[key];
    if (value === undefined) return;

    setSaving((p) => ({ ...p, [key]: true }));
    setErrors((p) => ({ ...p, [key]: "" }));
    setSaved((p) => ({ ...p, [key]: false }));

    try {
      const resp = await fetch(`${API}/api/settings/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        setErrors((p) => ({ ...p, [key]: err.detail || "Failed to save" }));
      } else {
        setSaved((p) => ({ ...p, [key]: true }));
        setTimeout(() => setSaved((p) => ({ ...p, [key]: false })), 2000);
        loadSettings();
      }
    } catch {
      setErrors((p) => ({ ...p, [key]: "Network error" }));
    } finally {
      setSaving((p) => ({ ...p, [key]: false }));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, key: string) => {
    if (e.key === "Enter") saveSetting(key);
  };

  // Group settings by category
  const grouped = settings.reduce<Record<string, Setting[]>>((acc, s) => {
    (acc[s.category] = acc[s.category] || []).push(s);
    return acc;
  }, {});

  const renderGeneralTab = () => {
    return (
      <div className="space-y-8">
        {Object.entries(CATEGORY_META).map(([catKey, meta]) => {
          const catSettings = grouped[catKey];
          if (!catSettings || catSettings.length === 0) return null;

          const Icon = meta.icon;

          return (
            <section key={catKey}>
              {/* Category header */}
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
                  <Icon size={16} className="text-warroom-accent" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold">{meta.label}</h3>
                  <p className="text-xs text-warroom-muted">{meta.description}</p>
                </div>
              </div>

              {/* Settings fields */}
              <div className="mt-4 space-y-3">
                {catSettings.map((setting) => {
                  const isRevealed = revealed[setting.key];
                  const isSaving = saving[setting.key];
                  const isSaved = saved[setting.key];
                  const error = errors[setting.key];
                  const hasValue = setting.value && setting.value !== "" && setting.value !== "••••";
                  const editValue = editValues[setting.key] ?? "";

                  return (
                    <div
                      key={setting.key}
                      className="bg-warroom-surface border border-warroom-border rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <label className="text-sm font-medium">
                            {KEY_LABELS[setting.key] || setting.key}
                          </label>
                          {setting.description && (
                            <p className="text-xs text-warroom-muted mt-0.5">{setting.description}</p>
                          )}
                        </div>
                        {setting.is_secret && hasValue && (
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                            Configured
                          </span>
                        )}
                        {setting.is_secret && !hasValue && (
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400">
                            Not Set
                          </span>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <input
                            type={setting.is_secret && !isRevealed ? "password" : "text"}
                            value={editValue}
                            onChange={(e) =>
                              setEditValues((p) => ({ ...p, [setting.key]: e.target.value }))
                            }
                            onKeyDown={(e) => handleKeyDown(e, setting.key)}
                            placeholder={
                              setting.is_secret
                                ? hasValue
                                  ? "Enter new value to update..."
                                  : "Paste your API key here..."
                                : "Enter value..."
                            }
                            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent font-mono"
                          />
                          {setting.is_secret && (
                            <button
                              onClick={() =>
                                setRevealed((p) => ({ ...p, [setting.key]: !p[setting.key] }))
                              }
                              className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted hover:text-warroom-text transition"
                            >
                              {isRevealed ? <EyeOff size={14} /> : <Eye size={14} />}
                            </button>
                          )}
                        </div>
                        <button
                          onClick={() => saveSetting(setting.key)}
                          disabled={isSaving || !editValue}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
                            isSaved
                              ? "bg-green-500/20 text-green-400"
                              : "bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40"
                          }`}
                        >
                          {isSaved ? (
                            <>
                              <Check size={14} /> Saved
                            </>
                          ) : isSaving ? (
                            "Saving..."
                          ) : (
                            <>
                              <Save size={14} /> Save
                            </>
                          )}
                        </button>
                      </div>

                      {error && (
                        <div className="flex items-center gap-1.5 mt-2 text-xs text-red-400">
                          <AlertCircle size={12} /> {error}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    );
  };

  const renderPlaceholderTab = (title: string, description: string) => {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
        <Settings size={48} className="mb-4 opacity-20" />
        <h3 className="text-lg font-medium text-warroom-text mb-2">{title}</h3>
        <p className="text-sm text-center max-w-md">{description}</p>
      </div>
    );
  };

  const renderScoringTab = () => {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-warroom-text mb-4">Current Lead Scoring Weights</h3>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: "Has Website", weight: "25%" },
              { label: "Google Rating", weight: "20%" },
              { label: "Review Count", weight: "15%" },
              { label: "Contact Information", weight: "20%" },
              { label: "Business Category", weight: "10%" },
              { label: "Location Quality", weight: "10%" },
            ].map(({ label, weight }) => (
              <div key={label} className="bg-warroom-surface border border-warroom-border rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-warroom-text">{label}</span>
                  <span className="text-sm font-medium text-warroom-accent">{weight}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
          <h4 className="text-sm font-medium text-warroom-text mb-2">Tier Thresholds</h4>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-red-400">🔥 Hot Leads</span>
              <span className="text-warroom-muted">Score ≥ 80</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-orange-400">🟠 Warm Leads</span>
              <span className="text-warroom-muted">Score 60-79</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-blue-400">🔵 Cold Leads</span>
              <span className="text-warroom-muted">Score 40-59</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-warroom-muted">Unscored</span>
              <span className="text-warroom-muted">Score &lt; 40</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-warroom-muted">
        <Settings size={24} className="animate-spin mr-3" />
        Loading settings...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3">
        <Settings size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Settings</h2>
      </div>

      {/* Horizontal Tabs */}
      <div className="border-b border-warroom-border bg-warroom-surface">
        <div className="flex overflow-x-auto">
          {SETTINGS_TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition ${
                activeTab === id
                  ? "text-warroom-accent border-warroom-accent bg-warroom-accent/5"
                  : "text-warroom-muted border-transparent hover:text-warroom-text"
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto">
          {activeTab === "general" && renderGeneralTab()}
          {activeTab === "email" && renderPlaceholderTab(
            "Email Integration",
            "Connect your email accounts and configure automated email campaigns for lead nurturing."
          )}
          {activeTab === "social" && renderPlaceholderTab(
            "Social Media",
            "Integrate with Facebook, LinkedIn, and other social platforms to enrich lead profiles and find additional contact information."
          )}
          {activeTab === "scoring" && renderScoringTab()}
          {activeTab === "automation" && renderPlaceholderTab(
            "Automation",
            "Set up automated workflows for lead qualification, follow-ups, and CRM integrations."
          )}
          {activeTab === "access" && renderPlaceholderTab(
            "Access Control",
            "Manage user permissions, team access levels, and security settings for your War Room instance."
          )}
        </div>
      </div>
    </div>
  );
}