"use client";

import { useState, useEffect } from "react";
import { Plus, Shield, Key, Users, Globe, Settings } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import AccountsList from "./AccountsList";
import InstagramAccountForm from "./InstagramAccountForm";

interface SocialAccount {
  id: number;
  platform: string;
  account_type: string;
  username: string;
  has_password: boolean;
  has_totp_secret: boolean;
  status: string;
  last_used_at: string | null;
  created_at: string;
  notes: string | null;
}

interface OAuthAccount {
  id: number;
  platform: string;
  username: string;
  display_name: string | null;
  profile_pic_url: string | null;
  follower_count: number | null;
  following_count: number | null;
  post_count: number | null;
  profile_url: string | null;
  status: string;
  connected_at: string;
  visibility_type: string;
}

interface TabSection {
  id: string;
  title: string;
  description: string;
  icon: typeof Key;
}

const TABS: TabSection[] = [
  {
    id: "instagram",
    title: "Instagram Accounts",
    description: "Username/password accounts for competitor intel scraping",
    icon: Key,
  },
  {
    id: "oauth",
    title: "OAuth Integrations",
    description: "Connected social media accounts for posting",
    icon: Globe,
  },
  {
    id: "api_keys",
    title: "API Keys",
    description: "Platform API credentials and app configurations",
    icon: Settings,
  },
];

export default function SocialAccountsTab() {
  const [activeTab, setActiveTab] = useState("instagram");
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [oauthAccounts, setOauthAccounts] = useState<OAuthAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load social accounts (username/password)
      const socialResp = await authFetch(`${API}/api/settings/social-accounts`);
      if (socialResp.ok) {
        const socialData = await socialResp.json();
        setSocialAccounts(socialData);
      }

      // Load OAuth accounts
      const oauthResp = await authFetch(`${API}/api/social/accounts`);
      if (oauthResp.ok) {
        const oauthData = await oauthResp.json();
        setOauthAccounts(oauthData);
      }
    } catch (error) {
      console.error("Failed to load social accounts:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAccountAdded = () => {
    setShowAddForm(false);
    loadData();
  };

  const handleAccountDeleted = () => {
    loadData();
  };

  const renderInstagramTab = () => {
    const instagramAccounts = socialAccounts.filter(acc => acc.platform === "instagram");

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-warroom-text">Instagram Accounts</h3>
            <p className="text-sm text-warroom-muted mt-1">
              Username/password accounts for competitor intelligence scraping and multi-account strategies
            </p>
          </div>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
          >
            <Plus size={16} />
            Add Account
          </button>
        </div>

        {/* Security Notice */}
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <Shield size={16} className="text-amber-400 flex-shrink-0" />
            <div>
              <h4 className="text-sm font-medium text-amber-400">Secure Credential Storage</h4>
              <p className="text-xs text-amber-300/80 mt-1">
                All passwords and 2FA secrets are encrypted using industry-standard AES-256 encryption. 
                Credentials are only decrypted when actively used for scraping operations.
              </p>
            </div>
          </div>
        </div>

        {/* Account Types Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-2 h-2 rounded-full bg-blue-400"></div>
              <span className="text-sm font-medium text-warroom-text">Scraping</span>
            </div>
            <p className="text-xs text-warroom-muted">
              Dedicated accounts for competitor intelligence and content analysis
            </p>
          </div>
          
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-400"></div>
              <span className="text-sm font-medium text-warroom-text">Posting</span>
            </div>
            <p className="text-xs text-warroom-muted">
              Accounts used for content publishing and engagement
            </p>
          </div>
          
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-2 h-2 rounded-full bg-purple-400"></div>
              <span className="text-sm font-medium text-warroom-text">Primary</span>
            </div>
            <p className="text-xs text-warroom-muted">
              Main business accounts for official brand presence
            </p>
          </div>
        </div>

        {/* Accounts List */}
        <AccountsList 
          accounts={instagramAccounts} 
          onAccountDeleted={handleAccountDeleted}
        />

        {/* Add Account Modal */}
        {showAddForm && (
          <InstagramAccountForm
            onClose={() => setShowAddForm(false)}
            onAccountAdded={handleAccountAdded}
          />
        )}
      </div>
    );
  };

  const renderOAuthTab = () => {
    const platforms = [
      { key: 'instagram', name: 'Instagram', icon: '📷', color: 'bg-gradient-to-r from-purple-500 to-pink-500' },
      { key: 'facebook', name: 'Facebook', icon: '📘', color: 'bg-blue-600' },
      { key: 'threads', name: 'Threads', icon: '🧵', color: 'bg-gray-800' },
      { key: 'x', name: 'X (Twitter)', icon: '🐦', color: 'bg-black' },
      { key: 'tiktok', name: 'TikTok', icon: '📱', color: 'bg-black' },
      { key: 'youtube', name: 'YouTube', icon: '🎥', color: 'bg-red-600' }
    ];

    const getAccountsByPlatform = (platform: string) => {
      return oauthAccounts.filter(account => account.platform === platform);
    };

    const formatNumber = (num: number | null) => {
      if (!num) return "—";
      if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
      if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
      return num.toString();
    };

    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-warroom-text">OAuth Integrations</h3>
          <p className="text-sm text-warroom-muted mt-1">
            Connected social media accounts for content publishing via official APIs
          </p>
        </div>

        <div className="space-y-4">
          {platforms.map((platform) => {
            const accounts = getAccountsByPlatform(platform.key);

            return (
              <div key={platform.key} className="bg-warroom-surface border border-warroom-border rounded-lg">
                {/* Platform header */}
                <div className="flex items-center justify-between p-4 border-b border-warroom-border/50">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 ${platform.color} rounded-lg flex items-center justify-center text-white text-lg`}>
                      {platform.icon}
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-warroom-text">{platform.name}</h4>
                      <p className="text-xs text-warroom-muted">
                        {accounts.length === 0 ? "No accounts connected" : `${accounts.length} account${accounts.length > 1 ? 's' : ''} connected`}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      window.open(`${API}/api/social/oauth/${platform.key === 'x' ? 'x' : platform.key === 'youtube' ? 'google' : 'meta'}/authorize${platform.key !== 'facebook' && platform.key !== 'x' && platform.key !== 'youtube' ? `?platform=${platform.key}` : ''}`, '_blank', 'width=600,height=700');
                    }}
                    className="flex items-center gap-2 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
                  >
                    <Plus size={14} />
                    Connect
                  </button>
                </div>

                {/* Connected accounts */}
                {accounts.length > 0 && (
                  <div className="p-4 space-y-3">
                    {accounts.map((account) => (
                      <div key={account.id} className="flex items-center justify-between p-3 bg-warroom-bg rounded-lg border border-warroom-border/30">
                        <div className="flex items-center gap-3">
                          {account.profile_pic_url ? (
                            <img
                              src={account.profile_pic_url}
                              alt={account.display_name || account.username}
                              className="w-8 h-8 rounded-full"
                            />
                          ) : (
                            <div className="w-8 h-8 bg-warroom-muted/20 rounded-full flex items-center justify-center">
                              <span className="text-xs text-warroom-muted">{(account.display_name || account.username)?.[0]?.toUpperCase()}</span>
                            </div>
                          )}
                          <div>
                            <p className="text-sm font-medium text-warroom-text">
                              {account.display_name || account.username}
                            </p>
                            <div className="flex items-center gap-3 text-xs text-warroom-muted">
                              <span>@{account.username}</span>
                              {account.follower_count && (
                                <span>{formatNumber(account.follower_count)} followers</span>
                              )}
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                account.visibility_type === 'shared_org' 
                                  ? 'bg-blue-500/20 text-blue-400'
                                  : account.visibility_type === 'shared'
                                  ? 'bg-green-500/20 text-green-400'
                                  : 'bg-gray-500/20 text-gray-400'
                              }`}>
                                {account.visibility_type === 'shared_org' ? 'Organization' : 
                                 account.visibility_type === 'shared' ? 'Shared' : 'Private'}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-green-400" title="Connected" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="bg-warroom-bg/50 border border-warroom-border/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-warroom-text mb-2">About OAuth Integrations</h4>
          <div className="space-y-1 text-xs text-warroom-muted">
            <p>• <strong>Secure:</strong> Uses official platform APIs with proper OAuth 2.0 flow</p>
            <p>• <strong>Rate Limited:</strong> Respects platform API limits and best practices</p>
            <p>• <strong>Token Management:</strong> Automatic token refresh and expiration handling</p>
            <p>• <strong>Permissions:</strong> Only requests necessary scopes for posting and reading</p>
          </div>
        </div>
      </div>
    );
  };

  const renderApiKeysTab = () => {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-warroom-text">API Keys & Credentials</h3>
          <p className="text-sm text-warroom-muted mt-1">
            Platform API credentials are managed in the main Settings → General tab
          </p>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6 text-center">
          <Settings size={48} className="mx-auto mb-4 text-warroom-muted/40" />
          <h4 className="text-sm font-medium text-warroom-text mb-2">API Keys Configuration</h4>
          <p className="text-sm text-warroom-muted mb-4">
            Social media API keys and app credentials are configured in the main Settings panel under the API Keys section.
          </p>
          <button
            onClick={() => window.location.href = "#general"}
            className="inline-flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
          >
            <Settings size={16} />
            Go to API Keys
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-warroom-bg border border-warroom-border/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-warroom-text mb-2">Required for OAuth</h4>
            <ul className="text-xs text-warroom-muted space-y-1">
              <li>• Meta App ID & Secret</li>
              <li>• Instagram App ID & Secret</li>
              <li>• Threads Client ID & Secret</li>
              <li>• X (Twitter) Client ID & Secret</li>
              <li>• TikTok Client Key & Secret</li>
              <li>• Google OAuth Client ID & Secret</li>
            </ul>
          </div>

          <div className="bg-warroom-bg border border-warroom-border/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-warroom-text mb-2">Already Configured</h4>
            <ul className="text-xs text-warroom-muted space-y-1">
              <li>• Instagram Scraper Credentials</li>
              <li>• TOTP 2FA Secret</li>
              <li>• Session Management</li>
              <li>• Rate Limiting</li>
            </ul>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-warroom-muted">Loading social accounts...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-warroom-border">
        <nav className="flex space-x-8">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm transition ${
                  activeTab === tab.id
                    ? "border-warroom-accent text-warroom-accent"
                    : "border-transparent text-warroom-muted hover:text-warroom-text hover:border-warroom-border"
                }`}
              >
                <Icon size={16} />
                {tab.title}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "instagram" && renderInstagramTab()}
        {activeTab === "oauth" && renderOAuthTab()}
        {activeTab === "api_keys" && renderApiKeysTab()}
      </div>
    </div>
  );
}