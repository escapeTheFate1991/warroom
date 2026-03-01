"use client";

import { useState, useEffect } from "react";
import { Share2, Instagram, Facebook, Youtube, Twitter, Plus, X, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";

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
  { id: "instagram", name: "Instagram", icon: Instagram, color: "#E4405F" },
  { id: "facebook", name: "Facebook", icon: Facebook, color: "#1877F2" },
  { id: "threads", name: "Threads", color: "#000000" },
  { id: "youtube", name: "YouTube", icon: Youtube, color: "#FF0000" },
  { id: "x", name: "X (Twitter)", icon: Twitter, color: "#1DA1F2" },
];

export default function SocialDashboard() {
  const [selectedPlatform, setSelectedPlatform] = useState<string>("overall");
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [summary, setSummary] = useState<SocialSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showConnectSection, setShowConnectSection] = useState(false);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [connectPlatform, setConnectPlatform] = useState<string>("");
  const [connectForm, setConnectForm] = useState<ConnectAccountData>({
    platform: "",
    username: "",
    profile_url: "",
    follower_count: 0,
    following_count: 0,
    post_count: 0,
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [accountsResponse, summaryResponse] = await Promise.all([
        fetch("/api/social/accounts"),
        fetch(`/api/social/analytics${selectedPlatform !== "overall" ? `?platform=${selectedPlatform}` : ""}`),
      ]);

      if (accountsResponse.ok) {
        const accountsData = await accountsResponse.json();
        setAccounts(accountsData);
      }

      if (summaryResponse.ok) {
        const summaryData = await summaryResponse.json();
        setSummary(summaryData);
      }
    } catch (error) {
      console.error("Failed to fetch social data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedPlatform]);

  const handleConnect = async (formData: ConnectAccountData) => {
    try {
      const response = await fetch("/api/social/accounts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        await fetchData();
        setShowConnectModal(false);
        setConnectForm({
          platform: "",
          username: "",
          profile_url: "",
          follower_count: 0,
          following_count: 0,
          post_count: 0,
        });
      }
    } catch (error) {
      console.error("Failed to connect account:", error);
    }
  };

  const handleDisconnect = async (accountId: number) => {
    try {
      const response = await fetch(`/api/social/accounts/${accountId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error("Failed to disconnect account:", error);
    }
  };

  const openConnectModal = (platform: string) => {
    setConnectPlatform(platform);
    setConnectForm({ ...connectForm, platform });
    setShowConnectModal(true);
  };

  const getPlatformInfo = (platformId: string) => {
    return PLATFORMS.find(p => p.id === platformId) || { id: platformId, name: platformId, color: "#666" };
  };

  const isConnected = (platformId: string) => {
    return accounts.some(account => account.platform === platformId);
  };

  const getConnectedAccount = (platformId: string) => {
    return accounts.find(account => account.platform === platformId);
  };

  const PlatformIcon = ({ platform, size = 24 }: { platform: string; size?: number }) => {
    const platformInfo = getPlatformInfo(platform);
    const IconComponent = platformInfo.icon;

    if (IconComponent) {
      return <IconComponent size={size} style={{ color: platformInfo.color }} />;
    }

    return (
      <div
        className="rounded-full flex items-center justify-center text-white font-bold"
        style={{ 
          backgroundColor: platformInfo.color, 
          width: size, 
          height: size,
          fontSize: size * 0.5
        }}
      >
        {platform.charAt(0).toUpperCase()}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#0d1117] text-white">
        <div className="text-center">
          <Share2 className="mx-auto mb-4" size={48} />
          <p>Loading social media dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-[#0d1117] text-white overflow-auto">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Share2 size={32} className="text-blue-400" />
            <h1 className="text-2xl font-bold">Social Media Dashboard</h1>
          </div>

          {/* Platform Selector */}
          <div className="relative">
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="bg-[#161b22] border border-[#30363d] rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="overall">Overall</option>
              {PLATFORMS.map((platform) => (
                <option key={platform.id} value={platform.id}>
                  {platform.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-400">Total Followers</h3>
              <p className="text-2xl font-bold text-blue-400">
                {summary.total_followers.toLocaleString()}
              </p>
            </div>
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-400">Engagement Rate</h3>
              <p className="text-2xl font-bold text-green-400">
                {summary.engagement_rate.toFixed(1)}%
              </p>
            </div>
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-400">Total Impressions</h3>
              <p className="text-2xl font-bold text-purple-400">
                {summary.total_impressions.toLocaleString()}
              </p>
            </div>
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-400">Total Reach</h3>
              <p className="text-2xl font-bold text-orange-400">
                {summary.total_reach.toLocaleString()}
              </p>
            </div>
          </div>
        )}

        {/* Connect Accounts Section */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg mb-6">
          <button
            onClick={() => setShowConnectSection(!showConnectSection)}
            className="w-full flex items-center justify-between p-4 hover:bg-[#21262d] transition-colors"
          >
            <h2 className="text-lg font-semibold">Connect Social Accounts</h2>
            {showConnectSection ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>

          {showConnectSection && (
            <div className="p-4 pt-0">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {PLATFORMS.map((platform) => {
                  const connected = isConnected(platform.id);
                  const account = getConnectedAccount(platform.id);

                  return (
                    <div key={platform.id} className="bg-[#0d1117] border border-[#30363d] rounded-lg p-4">
                      <div className="flex items-center gap-3 mb-3">
                        <PlatformIcon platform={platform.id} size={24} />
                        <h3 className="font-medium">{platform.name}</h3>
                      </div>

                      {connected && account ? (
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-green-400 text-sm">●</span>
                            <span className="text-sm text-gray-300">Connected</span>
                          </div>
                          {account.username && (
                            <p className="text-sm text-gray-300 mb-2">@{account.username}</p>
                          )}
                          <p className="text-xs text-gray-400 mb-3">
                            {account.follower_count.toLocaleString()} followers
                          </p>
                          <div className="flex gap-2">
                            {account.profile_url && (
                              <a
                                href={account.profile_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:text-blue-300"
                              >
                                <ExternalLink size={16} />
                              </a>
                            )}
                            <button
                              onClick={() => handleDisconnect(account.id)}
                              className="text-red-400 hover:text-red-300"
                            >
                              <X size={16} />
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <span className="text-gray-500 text-sm">●</span>
                            <span className="text-sm text-gray-500">Not connected</span>
                          </div>
                          <button
                            onClick={() => openConnectModal(platform.id)}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm flex items-center gap-1"
                          >
                            <Plus size={14} />
                            Connect
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Analytics Charts Placeholder */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Analytics Overview</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Engagement Chart */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Engagement (Last 30 Days)</h3>
              <div className="bg-[#0d1117] border border-[#30363d] rounded p-4 h-48">
                {accounts.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-gray-500 text-sm">Connect accounts to see engagement data</div>
                ) : (
                  <svg viewBox="0 0 400 160" className="w-full h-full" preserveAspectRatio="none">
                    {accounts.map((acc, i) => {
                      const barHeight = Math.max(8, Math.min(140, (acc.follower_count / Math.max(...accounts.map(a => a.follower_count || 1))) * 140));
                      const barWidth = Math.max(20, 360 / accounts.length - 10);
                      const x = 20 + i * (barWidth + 10);
                      const platformColors: Record<string, string> = { instagram: "#E4405F", facebook: "#1877F2", youtube: "#FF0000", twitter: "#000", tiktok: "#00F2EA", threads: "#888" };
                      return (
                        <g key={acc.id}>
                          <rect x={x} y={160 - barHeight} width={barWidth} height={barHeight} rx={4} fill={platformColors[acc.platform] || "#3B82F6"} opacity={0.8} />
                          <text x={x + barWidth / 2} y={155} textAnchor="middle" className="text-[8px] fill-gray-500">{acc.platform.slice(0, 3)}</text>
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>
            </div>

            {/* Follower Growth */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Follower Growth</h3>
              <div className="bg-[#0d1117] border border-[#30363d] rounded p-4 h-48">
                {accounts.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-gray-500 text-sm">Connect accounts to see follower data</div>
                ) : (
                  <div className="h-full flex items-end gap-2 px-2">
                    {accounts.map((acc) => {
                      const maxFollowers = Math.max(...accounts.map(a => a.follower_count || 1));
                      const pct = ((acc.follower_count || 0) / maxFollowers) * 100;
                      const platformColors: Record<string, string> = { instagram: "#E4405F", facebook: "#1877F2", youtube: "#FF0000", twitter: "#1DA1F2", tiktok: "#00F2EA", threads: "#888" };
                      return (
                        <div key={acc.id} className="flex-1 flex flex-col items-center gap-1">
                          <span className="text-[10px] text-gray-400">{(acc.follower_count || 0).toLocaleString()}</span>
                          <div className="w-full rounded-t-md transition-all" style={{ height: `${Math.max(4, pct)}%`, backgroundColor: platformColors[acc.platform] || "#3B82F6", opacity: 0.8 }} />
                          <span className="text-[9px] text-gray-500 truncate w-full text-center">{acc.username || acc.platform}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Platform Breakdown Table */}
          {selectedPlatform === "overall" && accounts.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Platform Breakdown</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#30363d]">
                      <th className="text-left py-3">Platform</th>
                      <th className="text-left py-3">Followers</th>
                      <th className="text-left py-3">Posts</th>
                      <th className="text-left py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((account) => (
                      <tr key={account.id} className="border-b border-[#30363d]/50">
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <PlatformIcon platform={account.platform} size={20} />
                            <span>{getPlatformInfo(account.platform).name}</span>
                            {account.username && (
                              <span className="text-gray-400">@{account.username}</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3">{account.follower_count.toLocaleString()}</td>
                        <td className="py-3">{account.post_count.toLocaleString()}</td>
                        <td className="py-3">
                          <span className="text-green-400">Connected</span>
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

      {/* Connect Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Connect {getPlatformInfo(connectPlatform).name}</h3>
              <button
                onClick={() => setShowConnectModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
                <input
                  type="text"
                  value={connectForm.username}
                  onChange={(e) => setConnectForm({ ...connectForm, username: e.target.value })}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="@username"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Profile URL</label>
                <input
                  type="url"
                  value={connectForm.profile_url}
                  onChange={(e) => setConnectForm({ ...connectForm, profile_url: e.target.value })}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Followers</label>
                  <input
                    type="number"
                    value={connectForm.follower_count}
                    onChange={(e) => setConnectForm({ ...connectForm, follower_count: parseInt(e.target.value) || 0 })}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Following</label>
                  <input
                    type="number"
                    value={connectForm.following_count}
                    onChange={(e) => setConnectForm({ ...connectForm, following_count: parseInt(e.target.value) || 0 })}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Posts</label>
                <input
                  type="number"
                  value={connectForm.post_count}
                  onChange={(e) => setConnectForm({ ...connectForm, post_count: parseInt(e.target.value) || 0 })}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <p className="text-xs text-gray-400">
                Enter your account details to connect. OAuth integration will be added in a future update.
              </p>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowConnectModal(false)}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
              <button
                onClick={() => handleConnect(connectForm)}
                disabled={!connectForm.username}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded"
              >
                Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}