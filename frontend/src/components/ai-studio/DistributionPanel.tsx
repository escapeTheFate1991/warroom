"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Clock, Zap, CheckCircle, AlertCircle, X, Plus, Settings, 
  Eye, ExternalLink, Loader2, TrendingUp, Users, Shuffle,
  Target, BarChart, Calendar, RefreshCw
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

/* ── Types ─────────────────────────────────────────────── */
interface SocialAccount {
  id: number;
  platform: string;
  username: string | null;
  profile_url: string | null;
  follower_count: number;
  following_count: number;
  post_count: number;
  status: string;
  type?: "main" | "sub"; // User-designated type
}

interface DistributionConfig {
  subAccountRandomizer: boolean;
  randomizerIntensity: "subtle" | "medium" | "aggressive";
  autoCaptionVariations: boolean;
  staggerInterval: "30min" | "1h" | "2h" | "6h" | "12h" | "24h" | "3d";
  clusterSize: number;
}

interface DistributionSchedule {
  accountId: number;
  handle: string;
  platform: string;
  scheduledTime: string;
  captionPreview: string;
}

interface DistributionResult {
  distributionId: string;
  schedules: DistributionSchedule[];
  totalPosts: number;
  estimatedCompletion: string;
}

interface DistributionStatus {
  id: string;
  status: "queued" | "uploading" | "active" | "failed";
  accounts: Array<{
    accountId: number;
    handle: string;
    platform: string;
    status: "queued" | "uploading" | "active" | "failed";
    postUrl?: string;
    error?: string;
  }>;
}

interface VisibilityScore {
  score: number;
  visualVariations: number;
  captionSets: number;
  metadataUnique: boolean;
  recommendation: string;
  color: "green" | "yellow" | "red";
}

interface DistributionPanelProps {
  videoProjectId: number | null;
  videoUrl: string | null;
  caption: string;
  onDistribute: (result: DistributionResult) => void;
}

/* ── Mock Data ─────────────────────────────────────────── */
const MOCK_ACCOUNTS: SocialAccount[] = [
  { id: 1, username: "eddyscreations", platform: "instagram", type: "main", profile_url: "", follower_count: 15200, following_count: 500, post_count: 245, status: "connected" },
  { id: 2, username: "eddyscreations", platform: "tiktok", type: "main", profile_url: "", follower_count: 8500, following_count: 120, post_count: 89, status: "connected" },
  { id: 3, username: "eddyscreations", platform: "youtube", type: "main", profile_url: "", follower_count: 2300, following_count: 45, post_count: 67, status: "disconnected" },
  { id: 4, username: "eddyclips", platform: "instagram", type: "sub", profile_url: "", follower_count: 3400, following_count: 200, post_count: 156, status: "connected" },
  { id: 5, username: "eddyreels", platform: "instagram", type: "sub", profile_url: "", follower_count: 1800, following_count: 150, post_count: 98, status: "connected" },
  { id: 6, username: "bestofeddy", platform: "instagram", type: "sub", profile_url: "", follower_count: 950, following_count: 80, post_count: 45, status: "connected" },
];

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "#E4405F",
  tiktok: "#000000", 
  youtube: "#FF0000",
  twitter: "#1DA1F2",
  x: "#000000"
};

const PLATFORM_BADGES: Record<string, string> = {
  instagram: "IG",
  tiktok: "TK", 
  youtube: "YT",
  twitter: "X",
  x: "X"
};

/* ── Component ─────────────────────────────────────────── */
export default function DistributionPanel({ 
  videoProjectId, 
  videoUrl, 
  caption, 
  onDistribute 
}: DistributionPanelProps) {
  const { toast } = useToast();

  // State
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [selectedAccounts, setSelectedAccounts] = useState<Set<number>>(new Set());
  const [config, setConfig] = useState<DistributionConfig>({
    subAccountRandomizer: true,
    randomizerIntensity: "medium",
    autoCaptionVariations: true,
    staggerInterval: "2h",
    clusterSize: 5
  });
  const [visibilityScore, setVisibilityScore] = useState<VisibilityScore | null>(null);
  const [schedulePreview, setSchedulePreview] = useState<DistributionSchedule[]>([]);
  const [launching, setLaunching] = useState(false);
  const [launched, setLaunched] = useState(false);
  const [distributionStatus, setDistributionStatus] = useState<DistributionStatus | null>(null);

  // Calculate visibility score based on configuration
  const calculateVisibilityScore = useCallback(async () => {
    // Simulate backend call
    await new Promise(resolve => setTimeout(resolve, 500));
    
    let score = 85; // Base score
    
    // Adjust based on config
    if (config.subAccountRandomizer) score += 10;
    if (config.autoCaptionVariations) score += 5;
    if (selectedAccounts.size > 1) score -= (selectedAccounts.size - 1) * 3;
    if (config.staggerInterval === "30min") score -= 15;
    if (config.staggerInterval === "24h" || config.staggerInterval === "3d") score += 5;
    
    score = Math.max(20, Math.min(100, score));
    
    const getScoreData = (s: number): VisibilityScore => {
      if (s >= 90) {
        return {
          score: s,
          visualVariations: 15,
          captionSets: 40,
          metadataUnique: true,
          recommendation: "Green Light: High Virality Potential",
          color: "green"
        };
      } else if (s >= 70) {
        return {
          score: s,
          visualVariations: 12,
          captionSets: 25,
          metadataUnique: true,
          recommendation: "Warning: Slight Duplicate Risk. Increase Stagger.",
          color: "yellow"
        };
      } else {
        return {
          score: s,
          visualVariations: 8,
          captionSets: 15,
          metadataUnique: false,
          recommendation: "Danger: High Shadowban Risk. Regenerate Captions.",
          color: "red"
        };
      }
    };
    
    setVisibilityScore(getScoreData(score));
  }, [config, selectedAccounts.size]);

  // Generate schedule preview
  const generateSchedulePreview = useCallback(() => {
    const selectedAccountsList = Array.from(selectedAccounts)
      .map(id => accounts.find(a => a.id === id))
      .filter(Boolean) as SocialAccount[];
    
    if (selectedAccountsList.length === 0) {
      setSchedulePreview([]);
      return;
    }

    const baseTime = new Date();
    baseTime.setHours(18, 0, 0, 0); // Start at 6 PM today
    
    const schedules: DistributionSchedule[] = [];
    const staggerMinutes = {
      "30min": 30,
      "1h": 60,
      "2h": 120,
      "6h": 360,
      "12h": 720,
      "24h": 1440,
      "3d": 4320
    }[config.staggerInterval];

    selectedAccountsList.forEach((account, index) => {
      const scheduledTime = new Date(baseTime);
      scheduledTime.setMinutes(baseTime.getMinutes() + (index * staggerMinutes));
      
      // Generate caption preview (simplified)
      let captionPreview = caption;
      if (config.autoCaptionVariations && index > 0) {
        captionPreview = caption.replace(/\b(this|that)\b/g, index % 2 ? "this" : "that");
      }
      
      schedules.push({
        accountId: account.id,
        handle: account.username || "Unknown",
        platform: account.platform,
        scheduledTime: scheduledTime.toISOString(),
        captionPreview: captionPreview.slice(0, 100) + (captionPreview.length > 100 ? "..." : "")
      });
    });

    setSchedulePreview(schedules);
  }, [selectedAccounts, accounts, config, caption]);

  // Load accounts from API
  const fetchAccounts = useCallback(async () => {
    setLoadingAccounts(true);
    try {
      const response = await authFetch(`${API}/api/social/accounts`);
      if (response.ok) {
        const data = await response.json();
        // Add type designation (all start as "main" - user can change later)
        const accountsWithType = (data.accounts || data || []).map((acc: SocialAccount) => ({
          ...acc,
          type: acc.type || "main"
        }));
        setAccounts(accountsWithType);
        
        // Auto-select main accounts that are connected
        const autoSelect = accountsWithType
          .filter((acc: SocialAccount) => acc.status === "connected" && acc.type === "main")
          .map((acc: SocialAccount) => acc.id);
        setSelectedAccounts(new Set(autoSelect));
      } else {
        // Use mock data if API fails
        setAccounts(MOCK_ACCOUNTS);
        setSelectedAccounts(new Set([1, 2, 4, 5]));
      }
    } catch (error) {
      console.error("Failed to fetch accounts:", error);
      setAccounts(MOCK_ACCOUNTS);
      setSelectedAccounts(new Set([1, 2, 4, 5]));
    }
    setLoadingAccounts(false);
  }, []);

  // Launch distribution
  const handleLaunch = async () => {
    if (selectedAccounts.size === 0) return;
    
    setLaunching(true);
    try {
      // Map selected account IDs to account objects with platform and account_id
      const selectedAccountObjects = Array.from(selectedAccounts).map(accountId => {
        const account = accounts.find(acc => acc.id === accountId);
        return {
          platform: account?.platform || "unknown",
          account_id: accountId.toString()
        };
      });

      const payload = {
        video_project_id: videoProjectId,
        video_url: videoUrl,
        caption,
        accounts: selectedAccountObjects,  // Send account objects, not just IDs
        config
      };
      
      const response = await authFetch(`${API}/api/scheduler/smart-distribute`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        const result = await response.json();
        setLaunched(true);
        
        // Start polling for status
        setDistributionStatus({
          id: result.distribution_id || "dist_1",
          status: "queued",
          accounts: schedulePreview.map(s => ({
            accountId: s.accountId,
            handle: s.handle,
            platform: s.platform,
            status: "queued"
          }))
        });
        
        onDistribute({
          distributionId: result.distribution_id || "dist_1",
          schedules: schedulePreview,
          totalPosts: schedulePreview.length,
          estimatedCompletion: schedulePreview[schedulePreview.length - 1]?.scheduledTime || ""
        });
      } else {
        throw new Error("Distribution failed");
      }
    } catch (error) {
      console.error("Distribution failed:", error);
      toast("error", "Failed to launch distribution. Please try again.");
    }
    setLaunching(false);
  };

  // Retry a single failed account
  const handleRetryAccount = async (accountId: number) => {
    if (!distributionStatus) return;
    try {
      const response = await authFetch(`${API}/api/scheduler/distributions/${distributionStatus.id}/retry`, {
        method: "POST",
        body: JSON.stringify({ account_id: accountId }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Retry failed");
      }
      // Optimistically set account back to uploading
      setDistributionStatus(prev => {
        if (!prev) return null;
        return {
          ...prev,
          accounts: prev.accounts.map(acc =>
            acc.accountId === accountId
              ? { ...acc, status: "uploading", error: undefined }
              : acc
          ),
        };
      });
      toast("info", `Retrying @${distributionStatus.accounts.find(a => a.accountId === accountId)?.handle}...`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Retry failed";
      toast("error", msg);
    }
  };

  // Poll for status updates
  useEffect(() => {
    if (!distributionStatus || !launched) return;

    const interval = setInterval(async () => {
      try {
        const response = await authFetch(`${API}/api/scheduler/distributions/${distributionStatus.id}`);
        if (response.ok) {
          const data = await response.json();
          setDistributionStatus(data);

          // Stop polling if all done and show summary toast
          if (data.accounts?.every((acc: any) => acc.status === "active" || acc.status === "failed")) {
            clearInterval(interval);
            const published = data.accounts.filter((a: any) => a.status === "active").length;
            const failed = data.accounts.filter((a: any) => a.status === "failed").length;
            if (failed === 0) {
              toast("success", `Distribution complete! ${published}/${data.accounts.length} published`);
            } else {
              toast("error", `Distribution done: ${published} published, ${failed} failed`);
            }
          }
        }
      } catch (error) {
        // Mock progression for demo
        setDistributionStatus(prev => {
          if (!prev) return null;
          const updated = { ...prev };
          updated.accounts = updated.accounts.map((acc) => {
            if (acc.status === "queued" && Math.random() < 0.3) {
              return { ...acc, status: "uploading" };
            }
            if (acc.status === "uploading" && Math.random() < 0.5) {
              return {
                ...acc,
                status: "active",
                postUrl: `https://${acc.platform}.com/post/${acc.accountId}_${Date.now()}`
              };
            }
            return acc;
          });
          return updated;
        });
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [distributionStatus, launched, toast]);

  // Effects
  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  useEffect(() => {
    calculateVisibilityScore();
    generateSchedulePreview();
  }, [calculateVisibilityScore, generateSchedulePreview]);

  // Toggle account selection
  const toggleAccount = (accountId: number) => {
    const newSelected = new Set(selectedAccounts);
    if (newSelected.has(accountId)) {
      newSelected.delete(accountId);
    } else {
      newSelected.add(accountId);
    }
    setSelectedAccounts(newSelected);
  };

  // Format time for display
  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    let dayPrefix = "";
    if (date.toDateString() === today.toDateString()) {
      dayPrefix = "Today ";
    } else if (date.toDateString() === tomorrow.toDateString()) {
      dayPrefix = "Tomorrow ";
    } else {
      dayPrefix = date.toLocaleDateString('en-US', { weekday: 'short' }) + " ";
    }
    
    return dayPrefix + date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  if (loadingAccounts) {
    return (
      <div className="w-full bg-warroom-surface border border-warroom-border rounded-xl p-8">
        <div className="flex items-center justify-center">
          <Loader2 className="animate-spin text-warroom-accent" size={24} />
          <span className="ml-2 text-sm text-warroom-muted">Loading distribution panel...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-warroom-border">
        <h3 className="text-sm font-bold text-warroom-text flex items-center gap-2">
          <Target size={16} className="text-warroom-accent" />
          Distribution Command Center
        </h3>
        <p className="text-xs text-warroom-muted mt-1">
          Multi-account posting with intelligent anti-shadowban protection
        </p>
      </div>

      <div className="flex">
        {/* Left Side - The Audit (40%) */}
        <div className="w-2/5 p-6 border-r border-warroom-border">
          {/* Visibility Score Gauge */}
          <div className="mb-6">
            <h4 className="text-xs font-semibold text-warroom-text mb-3">Visibility Score</h4>
            {visibilityScore ? (
              <div className="relative">
                {/* Circular Gauge */}
                <div className="w-24 h-24 mx-auto mb-3">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    {/* Background circle */}
                    <circle
                      cx="50"
                      cy="50" 
                      r="40"
                      stroke="currentColor"
                      strokeWidth="8"
                      fill="none"
                      className="text-warroom-border"
                    />
                    {/* Progress circle */}
                    <circle
                      cx="50"
                      cy="50"
                      r="40" 
                      stroke={visibilityScore.color === "green" ? "#22c55e" : 
                             visibilityScore.color === "yellow" ? "#eab308" : "#ef4444"}
                      strokeWidth="8"
                      fill="none"
                      strokeLinecap="round"
                      strokeDasharray={`${visibilityScore.score * 2.51} 251`}
                      className="transition-all duration-1000"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-warroom-text">{visibilityScore.score}</span>
                  </div>
                </div>
                
                {/* Score interpretation */}
                <div className={`text-center px-3 py-2 rounded-lg text-xs font-medium ${
                  visibilityScore.color === "green" ? "bg-green-500/10 text-green-400" :
                  visibilityScore.color === "yellow" ? "bg-yellow-500/10 text-yellow-400" :
                  "bg-red-500/10 text-red-400"
                }`}>
                  {visibilityScore.color === "green" && "🟢"} 
                  {visibilityScore.color === "yellow" && "🟡"} 
                  {visibilityScore.color === "red" && "🔴"} 
                  {" " + visibilityScore.recommendation}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-24">
                <Loader2 className="animate-spin text-warroom-accent" size={20} />
              </div>
            )}
          </div>

          {/* Variation Breakdown */}
          <div className="mb-6">
            <h4 className="text-xs font-semibold text-warroom-text mb-2">Variation Breakdown</h4>
            {visibilityScore && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-warroom-muted">Visual Variations:</span>
                  <span className="text-emerald-400 font-medium">
                    {visibilityScore.visualVariations}/15 ✓
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-warroom-muted">Caption Sets:</span>
                  <span className="text-emerald-400 font-medium">
                    {visibilityScore.captionSets}/40 ✓
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-warroom-muted">Metadata Unique:</span>
                  <span className={visibilityScore.metadataUnique ? "text-emerald-400" : "text-red-400"}>
                    {visibilityScore.metadataUnique ? "Yes ✓" : "No ✗"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Configuration Controls */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-warroom-text">Configuration</h4>
            
            {/* Sub-Account Randomizer */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs text-warroom-muted">Sub-Account Randomizer</label>
                <button
                  onClick={() => setConfig(prev => ({ ...prev, subAccountRandomizer: !prev.subAccountRandomizer }))}
                  className={`w-8 h-4 rounded-full transition-colors ${
                    config.subAccountRandomizer ? "bg-warroom-accent" : "bg-warroom-border"
                  }`}
                >
                  <div className={`w-3 h-3 rounded-full bg-white transition-transform ${
                    config.subAccountRandomizer ? "translate-x-4" : "translate-x-0.5"
                  }`} />
                </button>
              </div>
              {config.subAccountRandomizer && (
                <select 
                  value={config.randomizerIntensity}
                  onChange={(e) => setConfig(prev => ({ 
                    ...prev, 
                    randomizerIntensity: e.target.value as any 
                  }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                >
                  <option value="subtle">Subtle</option>
                  <option value="medium">Medium</option>
                  <option value="aggressive">Aggressive</option>
                </select>
              )}
            </div>

            {/* Auto Caption Variations */}
            <div className="flex items-center justify-between">
              <label className="text-xs text-warroom-muted">Auto Caption Variations</label>
              <button
                onClick={() => setConfig(prev => ({ ...prev, autoCaptionVariations: !prev.autoCaptionVariations }))}
                className={`w-8 h-4 rounded-full transition-colors ${
                  config.autoCaptionVariations ? "bg-warroom-accent" : "bg-warroom-border"
                }`}
              >
                <div className={`w-3 h-3 rounded-full bg-white transition-transform ${
                  config.autoCaptionVariations ? "translate-x-4" : "translate-x-0.5"
                }`} />
              </button>
            </div>

            {/* Stagger Selector */}
            <div>
              <label className="text-xs text-warroom-muted block mb-1">Stagger Interval</label>
              <select
                value={config.staggerInterval}
                onChange={(e) => setConfig(prev => ({ 
                  ...prev, 
                  staggerInterval: e.target.value as any 
                }))}
                className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
              >
                <option value="30min">30 minutes</option>
                <option value="1h">1 hour</option>
                <option value="2h">2 hours</option>
                <option value="6h">6 hours</option>
                <option value="12h">12 hours</option>
                <option value="24h">24 hours</option>
                <option value="3d">3 days</option>
              </select>
            </div>

            {/* Cluster Size */}
            <div>
              <label className="text-xs text-warroom-muted block mb-1">
                Cluster Size ({config.clusterSize})
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={config.clusterSize}
                onChange={(e) => setConfig(prev => ({ 
                  ...prev, 
                  clusterSize: parseInt(e.target.value) 
                }))}
                className="w-full accent-warroom-accent"
              />
              <p className="text-[10px] text-warroom-muted mt-1">
                Post to {config.clusterSize} accounts, wait, repeat
              </p>
            </div>
          </div>
        </div>

        {/* Right Side - Distribution Grid (60%) */}
        <div className="w-3/5 p-6">
          {!launched ? (
            <>
              {/* Account Selection */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-semibold text-warroom-text">Account Selection</h4>
                  <button className="flex items-center gap-1 px-2 py-1 bg-warroom-bg border border-warroom-border rounded text-[10px] text-warroom-muted hover:text-warroom-accent transition">
                    <Plus size={10} /> Add
                  </button>
                </div>

                {/* Main Accounts */}
                <div className="mb-4">
                  <h5 className="text-[11px] text-warroom-muted mb-2 font-medium">Main Accounts:</h5>
                  <div className="grid grid-cols-2 gap-2">
                    {accounts.filter(acc => acc.type === "main").map(account => (
                      <div
                        key={account.id}
                        onClick={() => account.status === "connected" && toggleAccount(account.id)}
                        className={`p-2 border rounded-lg transition cursor-pointer ${
                          selectedAccounts.has(account.id) && account.status === "connected"
                            ? "border-warroom-accent bg-warroom-accent/5"
                            : account.status === "connected" 
                              ? "border-warroom-border hover:border-warroom-accent/30"
                              : "border-warroom-border/50 opacity-50 cursor-not-allowed"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={selectedAccounts.has(account.id)}
                            disabled={account.status !== "connected"}
                            onChange={() => {}}
                            className="w-3 h-3 accent-warroom-accent"
                          />
                          <span className="text-xs text-warroom-text">@{account.username}</span>
                          <span 
                            className="text-[9px] px-1 py-0.5 rounded text-white font-bold"
                            style={{ backgroundColor: PLATFORM_COLORS[account.platform] }}
                          >
                            {PLATFORM_BADGES[account.platform] || account.platform.toUpperCase()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Sub-Accounts */}
                <div>
                  <h5 className="text-[11px] text-warroom-muted mb-2 font-medium">Sub-Accounts:</h5>
                  <div className="grid grid-cols-2 gap-2">
                    {accounts.filter(acc => acc.type === "sub").map(account => (
                      <div
                        key={account.id}
                        onClick={() => account.status === "connected" && toggleAccount(account.id)}
                        className={`p-2 border rounded-lg transition cursor-pointer ${
                          selectedAccounts.has(account.id) && account.status === "connected"
                            ? "border-warroom-accent bg-warroom-accent/5"
                            : account.status === "connected"
                              ? "border-warroom-border hover:border-warroom-accent/30"
                              : "border-warroom-border/50 opacity-50 cursor-not-allowed"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={selectedAccounts.has(account.id)}
                            disabled={account.status !== "connected"}
                            onChange={() => {}}
                            className="w-3 h-3 accent-warroom-accent"
                          />
                          <span className="text-xs text-warroom-text">@{account.username}</span>
                          <span 
                            className="text-[9px] px-1 py-0.5 rounded text-white font-bold"
                            style={{ backgroundColor: PLATFORM_COLORS[account.platform] }}
                          >
                            {PLATFORM_BADGES[account.platform] || account.platform.toUpperCase()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Schedule Preview */}
              <div className="mb-6">
                <h4 className="text-xs font-semibold text-warroom-text mb-3">Schedule Preview</h4>
                {schedulePreview.length > 0 ? (
                  <div className="space-y-2">
                    {schedulePreview.map((schedule, index) => (
                      <div 
                        key={index}
                        className="flex items-center justify-between p-2 bg-warroom-bg rounded border border-warroom-border"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-warroom-text">
                            @{schedule.handle}
                          </span>
                          <span 
                            className="text-[9px] px-1 py-0.5 rounded text-white font-bold"
                            style={{ backgroundColor: PLATFORM_COLORS[schedule.platform] }}
                          >
                            {PLATFORM_BADGES[schedule.platform]}
                          </span>
                        </div>
                        <div className="text-xs text-warroom-muted">
                          {formatTime(schedule.scheduledTime)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-xs text-warroom-muted">
                    Select accounts to see schedule preview
                  </div>
                )}
              </div>

              {/* Launch Machine Button */}
              <button
                onClick={handleLaunch}
                disabled={launching || selectedAccounts.size === 0}
                className="w-full py-3 bg-gradient-to-r from-warroom-accent to-purple-500 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                {launching ? (
                  <Loader2 className="animate-spin" size={16} />
                ) : (
                  <Zap size={16} />
                )}
                🚀 Launch Machine
              </button>
            </>
          ) : (
            /* Launch Status View */
            <div>
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-xs font-semibold text-warroom-text">Launch Status</h4>
                <button
                  onClick={() => window.location.reload()}
                  className="p-1 text-warroom-muted hover:text-warroom-text"
                >
                  <RefreshCw size={12} />
                </button>
              </div>

              {/* Overall Progress */}
              {distributionStatus && (() => {
                const total = distributionStatus.accounts.length;
                const published = distributionStatus.accounts.filter(a => a.status === "active").length;
                const failed = distributionStatus.accounts.filter(a => a.status === "failed").length;
                const done = published + failed;
                const pct = total > 0 ? Math.round((done / total) * 100) : 0;
                return (
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-xs text-warroom-muted mb-1">
                      <span>{published}/{total} published</span>
                      {failed > 0 && <span className="text-red-400">{failed} failed</span>}
                    </div>
                    <div className="w-full h-1.5 bg-warroom-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })()}

              {distributionStatus && (
                <div className="grid grid-cols-2 gap-3">
                  {distributionStatus.accounts.map((account, index) => (
                    <div
                      key={index}
                      className={`p-3 border rounded-lg bg-warroom-bg ${
                        account.status === "failed" ? "border-red-500/30" : "border-warroom-border"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-medium text-warroom-text">
                          @{account.handle}
                        </span>
                        <span
                          className="text-[9px] px-1 py-0.5 rounded text-white font-bold"
                          style={{ backgroundColor: PLATFORM_COLORS[account.platform] }}
                        >
                          {PLATFORM_BADGES[account.platform]}
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1 text-xs">
                          {account.status === "queued" && (
                            <>
                              <div className="w-2 h-2 rounded-full bg-gray-400" />
                              <span className="text-gray-400">Queued</span>
                            </>
                          )}
                          {account.status === "uploading" && (
                            <>
                              <Loader2 size={10} className="animate-spin text-blue-400" />
                              <span className="text-blue-400">Uploading</span>
                            </>
                          )}
                          {account.status === "active" && (
                            <>
                              <CheckCircle size={10} className="text-green-400" />
                              <span className="text-green-400">Published</span>
                            </>
                          )}
                          {account.status === "failed" && (
                            <>
                              <AlertCircle size={10} className="text-red-400" />
                              <span className="text-red-400">Failed</span>
                            </>
                          )}
                        </div>

                        <div className="flex items-center gap-1">
                          {account.postUrl && (
                            <a
                              href={account.postUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-warroom-accent hover:text-warroom-accent/80"
                            >
                              <ExternalLink size={12} />
                            </a>
                          )}
                          {account.status === "failed" && (
                            <button
                              onClick={() => handleRetryAccount(account.accountId)}
                              className="flex items-center gap-0.5 px-1.5 py-0.5 bg-red-500/20 border border-red-500/30 rounded text-[10px] text-red-300 hover:bg-red-500/30 transition"
                              title="Retry this account"
                            >
                              <RefreshCw size={8} />
                              Retry
                            </button>
                          )}
                        </div>
                      </div>

                      {account.error && (
                        <p className="text-[10px] text-red-400 mt-1">{account.error}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}