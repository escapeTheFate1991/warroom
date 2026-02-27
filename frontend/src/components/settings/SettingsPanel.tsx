"use client";

import { useState, useEffect, useCallback } from "react";
import { Settings, Key, Save, Eye, EyeOff, Check, AlertCircle, MapPin, Zap, Building2, Mail, Share2, Target, Bot, Shield, Plus, Edit, Trash2, Users, UserPlus } from "lucide-react";

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

interface EmailSettings {
  smtp_host: string;
  smtp_port: string;
  smtp_username: string;
  smtp_password: string;
  imap_host: string;
  imap_port: string;
  from_name: string;
  from_email: string;
}

interface LeadScoringWeights {
  no_website: number;
  bad_website_score: number;
  mediocre_website: number;
  has_email: number;
  has_phone: number;
  high_google_rating: number;
  many_reviews: number;
  has_socials: number;
  old_platform: number;
}

interface LeadScoringThresholds {
  hot: number;
  warm: number;
  cold: number;
}

interface Role {
  id: number;
  name: string;
  description: string;
  permissions: string[];
}

interface User {
  id: number;
  name: string;
  email: string;
  role_id: number;
  status: boolean;
}

interface Workflow {
  id: number;
  name: string;
  entity_type: string;
  event: string;
  conditions: any;
  actions: any;
  is_active: boolean;
}

export default function SettingsPanel() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [settings, setSettings] = useState<Setting[]>([]);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  
  // Email settings state
  const [emailSettings, setEmailSettings] = useState<EmailSettings>({
    smtp_host: '',
    smtp_port: '587',
    smtp_username: '',
    smtp_password: '',
    imap_host: '',
    imap_port: '993',
    from_name: '',
    from_email: ''
  });
  const [testingConnection, setTestingConnection] = useState(false);
  
  // Social media state
  const [socialConnections, setSocialConnections] = useState<Record<string, boolean>>({
    facebook: false,
    instagram: false,
    linkedin: false,
    twitter: false,
    tiktok: false
  });
  
  // Lead scoring state
  const [scoringWeights, setScoringWeights] = useState<LeadScoringWeights>({
    no_website: 25,
    bad_website_score: 20,
    mediocre_website: 10,
    has_email: 10,
    has_phone: 5,
    high_google_rating: 5,
    many_reviews: 5,
    has_socials: 5,
    old_platform: 15
  });
  const [scoringThresholds, setScoringThresholds] = useState<LeadScoringThresholds>({
    hot: 60,
    warm: 35,
    cold: 15
  });
  
  // Access control state
  const [roles, setRoles] = useState<Role[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [showAddRole, setShowAddRole] = useState(false);
  const [showAddUser, setShowAddUser] = useState(false);
  
  // Workflows state
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [showWorkflowForm, setShowWorkflowForm] = useState(false);

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

  const loadEmailSettings = async () => {
    try {
      const resp = await fetch(`${API}/api/settings/email`);
      if (resp.ok) {
        const data = await resp.json();
        setEmailSettings(data);
      }
    } catch (error) {
      console.error("Failed to load email settings");
    }
  };

  const loadScoringSettings = async () => {
    try {
      const scoringResp = await fetch(`${API}/api/settings/lead-scoring`);
      if (scoringResp.ok) {
        const scoringData = await scoringResp.json();
        if (scoringData.weights) setScoringWeights(scoringData.weights);
        if (scoringData.thresholds) setScoringThresholds(scoringData.thresholds);
      }
    } catch (error) {
      console.error("Failed to load scoring settings");
    }
  };

  const loadRoles = async () => {
    try {
      const resp = await fetch(`${API}/api/crm/roles`);
      if (resp.ok) {
        const data = await resp.json();
        setRoles(data);
      }
    } catch (error) {
      console.error("Failed to load roles");
    }
  };

  const loadUsers = async () => {
    try {
      const resp = await fetch(`${API}/api/crm/users`);
      if (resp.ok) {
        const data = await resp.json();
        setUsers(data);
      }
    } catch (error) {
      console.error("Failed to load users");
    }
  };

  const loadWorkflows = async () => {
    try {
      const resp = await fetch(`${API}/api/crm/workflows`);
      if (resp.ok) {
        const data = await resp.json();
        setWorkflows(data);
      }
    } catch (error) {
      console.error("Failed to load workflows");
    }
  };

  useEffect(() => { 
    loadSettings(); 
    loadEmailSettings();
    loadScoringSettings();
    loadRoles();
    loadUsers();
    loadWorkflows();
  }, [loadSettings]);

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

  const saveEmailSettings = async () => {
    try {
      const resp = await fetch(`${API}/api/settings/email`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(emailSettings),
      });
      if (resp.ok) {
        alert("Email settings saved successfully!");
      }
    } catch (error) {
      alert("Failed to save email settings");
    }
  };

  const testEmailConnection = async () => {
    setTestingConnection(true);
    try {
      const resp = await fetch(`${API}/api/settings/email/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(emailSettings),
      });
      if (resp.ok) {
        alert("Email connection successful!");
      } else {
        alert("Email connection failed");
      }
    } catch (error) {
      alert("Failed to test email connection");
    } finally {
      setTestingConnection(false);
    }
  };

  const saveScoringSettings = async () => {
    try {
      const resp = await fetch(`${API}/api/settings/lead-scoring`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          weights: scoringWeights,
          thresholds: scoringThresholds
        }),
      });
      if (resp.ok) {
        alert("Lead scoring settings saved successfully!");
      }
    } catch (error) {
      alert("Failed to save lead scoring settings");
    }
  };

  const connectSocialPlatform = (platform: string) => {
    // Placeholder for OAuth flow
    alert(`Connect to ${platform} - OAuth integration coming soon`);
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
    const weightLabels = {
      no_website: 'No Website',
      bad_website_score: 'Bad Website Score',
      mediocre_website: 'Mediocre Website',
      has_email: 'Has Email',
      has_phone: 'Has Phone',
      high_google_rating: 'High Google Rating',
      many_reviews: 'Many Reviews',
      has_socials: 'Has Social Media',
      old_platform: 'Old Platform'
    };

    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-warroom-text mb-4">Lead Scoring Weights</h3>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(scoringWeights).map(([key, value]) => (
              <div key={key} className="bg-warroom-surface border border-warroom-border rounded-lg p-3">
                <label className="text-sm text-warroom-text block mb-2">
                  {weightLabels[key as keyof typeof weightLabels]}
                </label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => setScoringWeights(prev => ({
                    ...prev,
                    [key]: parseInt(e.target.value) || 0
                  }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded px-3 py-1 text-sm"
                  min="0"
                  max="100"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
          <h4 className="text-sm font-medium text-warroom-text mb-4">Tier Thresholds</h4>
          <div className="space-y-3">
            {Object.entries(scoringThresholds).map(([tier, threshold]) => (
              <div key={tier} className="flex items-center justify-between">
                <span className="text-sm text-warroom-text capitalize">{tier} Leads (≥)</span>
                <input
                  type="number"
                  value={threshold}
                  onChange={(e) => setScoringThresholds(prev => ({
                    ...prev,
                    [tier]: parseInt(e.target.value) || 0
                  }))}
                  className="w-20 bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-sm text-right"
                  min="0"
                  max="100"
                />
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={saveScoringSettings}
          className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
        >
          <Save size={16} />
          Save Scoring Settings
        </button>
      </div>
    );
  };

  const renderEmailTab = () => {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-warroom-text mb-4">SMTP Configuration</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-warroom-text block mb-2">SMTP Host</label>
              <input
                type="text"
                value={emailSettings.smtp_host}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, smtp_host: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="smtp.gmail.com"
              />
            </div>
            <div>
              <label className="text-sm text-warroom-text block mb-2">SMTP Port</label>
              <input
                type="text"
                value={emailSettings.smtp_port}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, smtp_port: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="587"
              />
            </div>
            <div>
              <label className="text-sm text-warroom-text block mb-2">Username</label>
              <input
                type="text"
                value={emailSettings.smtp_username}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, smtp_username: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="your-email@gmail.com"
              />
            </div>
            <div>
              <label className="text-sm text-warroom-text block mb-2">Password</label>
              <input
                type="password"
                value={emailSettings.smtp_password}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, smtp_password: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="Your app password"
              />
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-warroom-text mb-4">IMAP Configuration</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-warroom-text block mb-2">IMAP Host</label>
              <input
                type="text"
                value={emailSettings.imap_host}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, imap_host: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="imap.gmail.com"
              />
            </div>
            <div>
              <label className="text-sm text-warroom-text block mb-2">IMAP Port</label>
              <input
                type="text"
                value={emailSettings.imap_port}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, imap_port: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="993"
              />
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-warroom-text mb-4">From Information</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-warroom-text block mb-2">From Name</label>
              <input
                type="text"
                value={emailSettings.from_name}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, from_name: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="Your Company"
              />
            </div>
            <div>
              <label className="text-sm text-warroom-text block mb-2">From Email</label>
              <input
                type="email"
                value={emailSettings.from_email}
                onChange={(e) => setEmailSettings(prev => ({ ...prev, from_email: e.target.value }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                placeholder="noreply@yourcompany.com"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={testEmailConnection}
            disabled={testingConnection}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-surface hover:bg-warroom-surface/80 border border-warroom-border rounded-lg text-sm font-medium transition"
          >
            {testingConnection ? "Testing..." : "Test Connection"}
          </button>
          <button
            onClick={saveEmailSettings}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
          >
            <Save size={16} />
            Save Settings
          </button>
        </div>
      </div>
    );
  };

  const renderSocialTab = () => {
    const platforms = [
      { key: 'facebook', name: 'Facebook', color: 'bg-blue-600' },
      { key: 'instagram', name: 'Instagram', color: 'bg-pink-600' },
      { key: 'linkedin', name: 'LinkedIn', color: 'bg-blue-700' },
      { key: 'twitter', name: 'Twitter', color: 'bg-sky-500' },
      { key: 'tiktok', name: 'TikTok', color: 'bg-black' }
    ];

    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-warroom-text mb-4">Social Media Connections</h3>
          <div className="grid grid-cols-2 gap-4">
            {platforms.map((platform) => {
              const isConnected = socialConnections[platform.key];
              return (
                <div key={platform.key} className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 ${platform.color} rounded-lg flex items-center justify-center text-white text-xs font-bold`}>
                        {platform.name[0]}
                      </div>
                      <span className="text-sm font-medium text-warroom-text">{platform.name}</span>
                    </div>
                    <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                      isConnected 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-gray-400'}`} />
                      {isConnected ? 'Connected' : 'Disconnected'}
                    </div>
                  </div>
                  <button
                    onClick={() => connectSocialPlatform(platform.name)}
                    className={`w-full py-2 rounded-lg text-sm font-medium transition ${
                      isConnected
                        ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                        : 'bg-warroom-accent hover:bg-warroom-accent/80 text-white'
                    }`}
                  >
                    {isConnected ? 'Disconnect' : 'Connect'}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const renderAutomationTab = () => {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-warroom-text">Automation Workflows</h3>
          <button
            onClick={() => setShowWorkflowForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
          >
            <Plus size={16} />
            Create Workflow
          </button>
        </div>

        {workflows.length === 0 ? (
          <div className="text-center py-12 text-warroom-muted">
            <Bot size={32} className="mx-auto mb-4 opacity-50" />
            <p className="text-sm">No workflows configured yet</p>
            <p className="text-xs mt-1">Create your first automation workflow to get started</p>
          </div>
        ) : (
          <div className="space-y-3">
            {workflows.map((workflow) => (
              <div key={workflow.id} className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-warroom-text">{workflow.name}</h4>
                    <p className="text-xs text-warroom-muted mt-1">
                      {workflow.entity_type} • {workflow.event} • {workflow.is_active ? 'Active' : 'Inactive'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="p-1 hover:bg-warroom-bg rounded">
                      <Edit size={14} className="text-warroom-muted" />
                    </button>
                    <button className="p-1 hover:bg-warroom-bg rounded">
                      <Trash2 size={14} className="text-red-400" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {showWorkflowForm && (
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
            <h4 className="text-sm font-semibold text-warroom-text mb-4">Create New Workflow</h4>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-warroom-text block mb-2">Workflow Name</label>
                <input
                  type="text"
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
                  placeholder="Enter workflow name"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-warroom-text block mb-2">Entity Type</label>
                  <select className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm">
                    <option value="">Select entity type</option>
                    <option value="deal">Deal</option>
                    <option value="person">Person</option>
                    <option value="activity">Activity</option>
                    <option value="email">Email</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-warroom-text block mb-2">Trigger Event</label>
                  <select className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm">
                    <option value="">Select event</option>
                    <option value="created">Created</option>
                    <option value="updated">Updated</option>
                    <option value="deleted">Deleted</option>
                    <option value="stage_changed">Stage Changed</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowWorkflowForm(false)}
                  className="px-4 py-2 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded-lg text-sm font-medium transition"
                >
                  Cancel
                </button>
                <button className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition">
                  Create Workflow
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderAccessTab = () => {
    return (
      <div className="space-y-6">
        {/* Roles Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-warroom-text">Roles</h3>
            <button
              onClick={() => setShowAddRole(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded text-xs font-medium transition"
            >
              <Plus size={14} />
              Add Role
            </button>
          </div>
          <div className="space-y-2">
            {roles.map((role) => (
              <div 
                key={role.id}
                className="flex items-center justify-between bg-warroom-surface border border-warroom-border rounded-lg p-3 cursor-pointer hover:bg-warroom-surface/80"
                onClick={() => setSelectedRole(role)}
              >
                <div>
                  <h4 className="text-sm font-medium text-warroom-text">{role.name}</h4>
                  <p className="text-xs text-warroom-muted">{role.description}</p>
                </div>
                <div className="text-xs text-warroom-muted">
                  {role.permissions.length} permissions
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Users Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-warroom-text">Users</h3>
            <button
              onClick={() => setShowAddUser(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded text-xs font-medium transition"
            >
              <UserPlus size={14} />
              Add User
            </button>
          </div>
          <div className="space-y-2">
            {users.map((user) => (
              <div key={user.id} className="flex items-center justify-between bg-warroom-surface border border-warroom-border rounded-lg p-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-warroom-accent/20 rounded-full flex items-center justify-center">
                    <Users size={14} className="text-warroom-accent" />
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-warroom-text">{user.name}</h4>
                    <p className="text-xs text-warroom-muted">{user.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    user.status ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {user.status ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Permission Editor Modal */}
        {selectedRole && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6 max-w-md w-full mx-4">
              <h4 className="text-sm font-semibold text-warroom-text mb-4">
                Edit Permissions: {selectedRole.name}
              </h4>
              <div className="space-y-3 mb-4">
                {[
                  'deals.read', 'deals.write',
                  'contacts.read', 'contacts.write',
                  'activities.read', 'activities.write',
                  'settings.read', 'settings.write'
                ].map((permission) => (
                  <label key={permission} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedRole.permissions.includes(permission)}
                      className="rounded border-warroom-border"
                    />
                    <span className="text-sm text-warroom-text">{permission}</span>
                  </label>
                ))}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setSelectedRole(null)}
                  className="px-4 py-2 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded-lg text-sm font-medium transition"
                >
                  Cancel
                </button>
                <button className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition">
                  Save Permissions
                </button>
              </div>
            </div>
          </div>
        )}
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
          {activeTab === "email" && renderEmailTab()}
          {activeTab === "social" && renderSocialTab()}
          {activeTab === "scoring" && renderScoringTab()}
          {activeTab === "automation" && renderAutomationTab()}
          {activeTab === "access" && renderAccessTab()}
        </div>
      </div>
    </div>
  );
}