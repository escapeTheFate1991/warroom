"use client";

import { useState, useEffect, useCallback } from "react";
import { Share2, Instagram, Facebook, Youtube, Twitter, Plus, X, ExternalLink, TrendingUp, TrendingDown, Users, Eye, BarChart3, Zap, ChevronDown, ChevronUp, Radio } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface SocialAccount {
  id: number;
  platform: string;
  username: string | null;
  profile_url: string | null;
  follower_count: number;
  following_count: number;
  post_count: number;
  connected_at: string;
  last_synced: string | null;
  status: string;
}

interface SocialSummary {
  total_followers: number;
  total_engagement: number;
  total_impressions: number;
  total_reach: number;
  engagement_rate: number;
  accounts_connected: number;
}

interface ConnectAccountData {
  platform: string;
  username: string;
  profile_url: string;
  follower_count: number;
  following_count: number;
  post_count: number;
}

const PLATFORMS = [
  { id: "instagram", name: "Instagram", icon: Instagram, color: "#E4405F", gradient: "from-pink-500 to-purple-600" },
  { id: "facebook", name: "Facebook", icon: Facebook, color: "#1877F2", gradient: "from-blue-500 to-blue-700" },
  { id: "threads", name: "Threads", color: "#000000", gradient: "from-gray-600 to-gray-800" },
  { id: "youtube", name: "YouTube", icon: Youtube, color: "#FF0000", gradient: "from-red-500 to-red-700" },
  { id: "x", name: "X", icon: Twitter, color: "#000000", gradient: "from-gray-700 to-gray-900" },
  { id: "tiktok", name: "TikTok", color: "#00F2EA", gradient: "from-cyan-400 to-pink-500" },
];

// Maps platform → OAuth provider + query params
// Each platform has its own OAuth flow via the meta authorize endpoint
const OAUTH_PLATFORMS: Record<string, { provider: string; params?: Record<string, string> }> = {
  instagram: { provider: "meta", params: { platform: "instagram" } },  // → instagram.com/oauth
  facebook: { provider: "meta", params: { platform: "facebook" } },    // → facebook.com/dialog/oauth
  threads: { provider: "meta", params: { platform: "threads" } },      // → threads.net/oauth
  x: { provider: "x" },
  tiktok: { provider: "tiktok" },
  youtube: { provider: "google" },
};

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const w = 120, h = 40;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  return (
    <svg width={w} height={h} className="opacity-60">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function PlatformIcon({ platform, size = 20 }: { platform: string; size?: number }) {
  const p = PLATFORMS.find(x => x.id === platform);
  const Icon = p?.icon;
  if (Icon) return <Icon size={size} style={{ color: p.color }} />;
  return (
    <div className="rounded-full flex items-center justify-center text-white font-bold text-xs"
      style={{ backgroundColor: p?.color || "#666", width: size, height: size }}>
      {platform.charAt(0).toUpperCase()}
    </div>
  );
}

export default function SocialDashboard() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [summary, setSummary] = useState<SocialSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showManualModal, setShowManualModal] = useState(false);
  const [connectPlatform, setConnectPlatform] = useState("");
  const [connectForm, setConnectForm] = useState<ConnectAccountData>({ platform: "", username: "", profile_url: "", follower_count: 0, following_count: 0, post_count: 0 });

  const fetchData = useCallback(async () => {
    try {
      const [accResp, sumResp] = await Promise.all([
        fetch(`${API}/api/social/accounts`),
        fetch(`${API}/api/social/analytics`),
      ]);
      if (accResp.ok) setAccounts(await accResp.json());
      if (sumResp.ok) setSummary(await sumResp.json());
    } catch (e) {
      console.error("Failed to fetch social data:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Listen for OAuth popup completion via postMessage
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === "oauth_complete") {
        fetchData(); // Refresh accounts list
        if (event.data.status === "error" && event.data.error) {
          alert(event.data.error);
        }
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [fetchData]);

  const startOAuth = async (platform: string) => {
    const oauth = OAUTH_PLATFORMS[platform];
    if (!oauth) { openManual(platform); return; }
    try {
      const params = new URLSearchParams(oauth.params || {});
      const url = `${API}/api/social/oauth/${oauth.provider}/authorize${params.toString() ? "?" + params.toString() : ""}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (data.auth_url) { window.open(data.auth_url, "_blank", "width=600,height=700"); return; }
      }
      if (res.status === 400) alert(`OAuth not configured for ${platform}. Add credentials in Settings → API Keys.`);
    } catch { /* fallback */ }
    openManual(platform);
  };

  const openManual = (platform: string) => {
    setConnectPlatform(platform);
    setConnectForm({ platform, username: "", profile_url: "", follower_count: 0, following_count: 0, post_count: 0 });
    setShowManualModal(true);
  };

  const handleManualConnect = async () => {
    try {
      const res = await fetch(`${API}/api/social/accounts`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(connectForm),
      });
      if (res.ok) { fetchData(); setShowManualModal(false); }
    } catch (e) { console.error(e); }
  };

  const handleDisconnect = async (id: number) => {
    try {
      const res = await fetch(`${API}/api/social/accounts/${id}`, { method: "DELETE" });
      if (res.ok) fetchData();
    } catch (e) { console.error(e); }
  };

  const getAccount = (pid: string) => accounts.find(a => a.platform === pid);
  const isConnected = (pid: string) => accounts.some(a => a.platform === pid);

  // Mock sparkline data (will be real when analytics API populates)
  const mockSparkline = (seed: number) => Array.from({ length: 7 }, (_, i) => Math.floor(Math.abs(Math.sin(seed + i * 0.8)) * 500 + 100));

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-warroom-muted">
        <Share2 size={24} className="animate-spin mr-3" /> Loading social dashboard...
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Share2 size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Social Performance</h2>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-warroom-muted">{accounts.length} connected</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-6xl mx-auto space-y-6">

          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Total Followers", value: summary?.total_followers || accounts.reduce((s, a) => s + a.follower_count, 0), icon: Users, color: "text-blue-400", trend: "+12%" },
              { label: "Engagement Rate", value: summary?.engagement_rate || 0, icon: Zap, color: "text-green-400", trend: "+3.2%", suffix: "%", isRate: true },
              { label: "Total Impressions", value: summary?.total_impressions || 0, icon: Eye, color: "text-purple-400", trend: "+22%" },
              { label: "Accounts Connected", value: accounts.length, icon: BarChart3, color: "text-orange-400", trend: null },
            ].map((stat, i) => (
              <div key={i} className="bg-warroom-surface border border-warroom-border rounded-2xl p-5 hover:border-warroom-accent/30 transition-all group">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-warroom-muted font-medium">{stat.label}</span>
                  <stat.icon size={16} className={`${stat.color} opacity-60 group-hover:opacity-100 transition`} />
                </div>
                <div className="flex items-end gap-2">
                  <span className={`text-2xl font-bold ${stat.color}`}>
                    {stat.isRate ? (typeof stat.value === "number" ? stat.value.toFixed(1) : stat.value) : formatNum(typeof stat.value === "number" ? stat.value : 0)}
                    {stat.suffix || ""}
                  </span>
                  {stat.trend && (
                    <span className="text-xs text-green-400 flex items-center gap-0.5 mb-1">
                      <TrendingUp size={12} /> {stat.trend}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Platform Cards */}
          <div>
            <h3 className="text-sm font-semibold text-warroom-text mb-3">Platforms</h3>
            <div className="grid grid-cols-3 gap-4">
              {PLATFORMS.map((platform) => {
                const account = getAccount(platform.id);
                const connected = !!account;

                return (
                  <div key={platform.id}
                    className={`bg-warroom-surface border rounded-2xl p-5 transition-all ${
                      connected
                        ? "border-warroom-border hover:border-warroom-accent/40 hover:shadow-lg hover:shadow-warroom-accent/5"
                        : "border-warroom-border/50 opacity-60 hover:opacity-80"
                    }`}>
                    {/* Platform header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <PlatformIcon platform={platform.id} size={24} />
                        <div>
                          <span className="text-sm font-medium">{platform.name}</span>
                          {account?.username && (
                            <p className="text-xs text-warroom-muted">@{account.username}</p>
                          )}
                        </div>
                      </div>
                      {connected ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                          <span className="text-[10px] text-green-400 font-medium">LIVE</span>
                        </div>
                      ) : (
                        <button onClick={() => startOAuth(platform.id)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-xs font-medium transition">
                          <Plus size={12} /> Connect
                        </button>
                      )}
                    </div>

                    {connected && account ? (
                      <>
                        {/* Metrics */}
                        <div className="grid grid-cols-3 gap-3 mb-4">
                          <div>
                            <p className="text-lg font-bold">{formatNum(account.follower_count)}</p>
                            <p className="text-[10px] text-warroom-muted">Followers</p>
                          </div>
                          <div>
                            <p className="text-lg font-bold">{formatNum(account.post_count)}</p>
                            <p className="text-[10px] text-warroom-muted">Posts</p>
                          </div>
                          <div>
                            <p className="text-lg font-bold">{formatNum(account.following_count)}</p>
                            <p className="text-[10px] text-warroom-muted">Following</p>
                          </div>
                        </div>

                        {/* Sparkline */}
                        <div className="mb-3">
                          <MiniSparkline data={mockSparkline(account.id)} color={platform.color} />
                          <p className="text-[10px] text-warroom-muted mt-1">Daily engagement · Last 7 days</p>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-between pt-3 border-t border-warroom-border/50">
                          {account.profile_url && (
                            <a href={account.profile_url} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-warroom-accent hover:underline flex items-center gap-1">
                              <ExternalLink size={12} /> View Profile
                            </a>
                          )}
                          <button onClick={() => handleDisconnect(account.id)}
                            className="text-xs text-warroom-muted hover:text-red-400 transition">
                            Disconnect
                          </button>
                        </div>
                      </>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-xs text-warroom-muted">Connect {platform.name} to track performance</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recent Published Content */}
          {accounts.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-warroom-text mb-3">Recent Published Content</h3>
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-5">
                <div className="text-center py-8 text-warroom-muted">
                  <BarChart3 size={32} className="mx-auto mb-3 opacity-30" />
                  <p className="text-sm">Content tracking coming soon</p>
                  <p className="text-xs mt-1">Published posts will appear here with engagement metrics</p>
                </div>
              </div>
            </div>
          )}

          {/* Platform Breakdown Table */}
          {accounts.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-warroom-text mb-3">Platform Breakdown</h3>
              <div className="bg-warroom-surface border border-warroom-border rounded-2xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-warroom-border">
                      <th className="text-left py-3 px-5 text-xs text-warroom-muted font-medium">Platform</th>
                      <th className="text-left py-3 px-5 text-xs text-warroom-muted font-medium">Followers</th>
                      <th className="text-left py-3 px-5 text-xs text-warroom-muted font-medium">Posts</th>
                      <th className="text-left py-3 px-5 text-xs text-warroom-muted font-medium">Engagement</th>
                      <th className="text-left py-3 px-5 text-xs text-warroom-muted font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((account) => (
                      <tr key={account.id} className="border-b border-warroom-border/30 hover:bg-warroom-bg/50 transition">
                        <td className="py-3 px-5">
                          <div className="flex items-center gap-2">
                            <PlatformIcon platform={account.platform} size={18} />
                            <span className="font-medium">{PLATFORMS.find(p => p.id === account.platform)?.name}</span>
                            {account.username && <span className="text-warroom-muted">@{account.username}</span>}
                          </div>
                        </td>
                        <td className="py-3 px-5 font-medium">{formatNum(account.follower_count)}</td>
                        <td className="py-3 px-5">{formatNum(account.post_count)}</td>
                        <td className="py-3 px-5">
                          <MiniSparkline data={mockSparkline(account.id)} color={PLATFORMS.find(p => p.id === account.platform)?.color || "#6366f1"} />
                        </td>
                        <td className="py-3 px-5">
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs bg-green-500/10 text-green-400">
                            <div className="w-1.5 h-1.5 rounded-full bg-green-400" /> Connected
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Manual Connect Modal */}
      {showManualModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <PlatformIcon platform={connectPlatform} size={20} />
                Connect {PLATFORMS.find(p => p.id === connectPlatform)?.name}
              </h3>
              <button onClick={() => setShowManualModal(false)} className="text-warroom-muted hover:text-warroom-text"><X size={20} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Username</label>
                <input type="text" value={connectForm.username} onChange={e => setConnectForm({ ...connectForm, username: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent font-mono" placeholder="@username" />
              </div>
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Profile URL</label>
                <input type="url" value={connectForm.profile_url} onChange={e => setConnectForm({ ...connectForm, profile_url: e.target.value })}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent font-mono" placeholder="https://..." />
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[["Followers", "follower_count"], ["Following", "following_count"], ["Posts", "post_count"]].map(([label, key]) => (
                  <div key={key}>
                    <label className="text-xs text-warroom-muted block mb-1">{label}</label>
                    <input type="number" value={(connectForm as any)[key]} onChange={e => setConnectForm({ ...connectForm, [key]: parseInt(e.target.value) || 0 })}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-warroom-accent" />
                  </div>
                ))}
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowManualModal(false)} className="flex-1 px-4 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-sm hover:bg-warroom-surface transition">Cancel</button>
              <button onClick={handleManualConnect} disabled={!connectForm.username}
                className="flex-1 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 rounded-lg text-sm font-medium transition">Connect</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
