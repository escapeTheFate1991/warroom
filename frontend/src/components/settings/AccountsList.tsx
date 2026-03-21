"use client";

import { useState } from "react";
import { Edit, Trash2, Eye, Shield, Clock, AlertCircle, CheckCircle, Key, Loader2 } from "lucide-react";
import { API, authFetch } from "@/lib/api";
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

interface AccountsListProps {
  accounts: SocialAccount[];
  onAccountDeleted: () => void;
}

interface Credentials {
  username: string;
  password: string;
  totp_secret: string;
  current_totp_code: string;
}

export default function AccountsList({ accounts, onAccountDeleted }: AccountsListProps) {
  const [editingAccount, setEditingAccount] = useState<SocialAccount | null>(null);
  const [viewingCredentials, setViewingCredentials] = useState<{ [key: number]: Credentials }>({});
  const [loadingCredentials, setLoadingCredentials] = useState<{ [key: number]: boolean }>({});
  const [testingConnection, setTestingConnection] = useState<{ [key: number]: boolean }>({});
  const [testResults, setTestResults] = useState<{ [key: number]: { success: boolean; message: string } }>({});

  const handleEdit = (account: SocialAccount) => {
    setEditingAccount(account);
  };

  const handleDelete = async (account: SocialAccount) => {
    if (!confirm(`Are you sure you want to delete @${account.username}? This cannot be undone.`)) {
      return;
    }

    try {
      const response = await authFetch(`${API}/api/settings/social-accounts/${account.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to delete account");
      }

      onAccountDeleted();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to delete account");
    }
  };

  const handleViewCredentials = async (account: SocialAccount) => {
    if (viewingCredentials[account.id]) {
      // Hide credentials
      setViewingCredentials(prev => {
        const newState = { ...prev };
        delete newState[account.id];
        return newState;
      });
      return;
    }

    // Load credentials
    setLoadingCredentials(prev => ({ ...prev, [account.id]: true }));
    try {
      const response = await authFetch(`${API}/api/settings/social-accounts/${account.id}/credentials`);
      
      if (!response.ok) {
        throw new Error("Failed to load credentials");
      }

      const credentials = await response.json();
      setViewingCredentials(prev => ({ ...prev, [account.id]: credentials }));
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to load credentials");
    } finally {
      setLoadingCredentials(prev => ({ ...prev, [account.id]: false }));
    }
  };

  const handleTestConnection = async (account: SocialAccount) => {
    setTestingConnection(prev => ({ ...prev, [account.id]: true }));
    setTestResults(prev => {
      const newResults = { ...prev };
      delete newResults[account.id];
      return newResults;
    });

    try {
      const response = await authFetch(`${API}/api/settings/social-accounts/${account.id}/test`, {
        method: "POST",
      });

      const result = await response.json();
      setTestResults(prev => ({ ...prev, [account.id]: result }));
    } catch (error) {
      setTestResults(prev => ({ 
        ...prev, 
        [account.id]: { 
          success: false, 
          message: error instanceof Error ? error.message : "Test failed" 
        } 
      }));
    } finally {
      setTestingConnection(prev => ({ ...prev, [account.id]: false }));
    }
  };

  const getAccountTypeInfo = (type: string) => {
    switch (type) {
      case "scraping":
        return { label: "Scraping", color: "bg-blue-500/20 text-blue-400", icon: "🔍" };
      case "posting":
        return { label: "Posting", color: "bg-green-500/20 text-green-400", icon: "📝" };
      case "primary":
        return { label: "Primary", color: "bg-purple-500/20 text-purple-400", icon: "⭐" };
      default:
        return { label: type, color: "bg-gray-500/20 text-gray-400", icon: "📱" };
    }
  };

  const getStatusInfo = (status: string) => {
    switch (status) {
      case "active":
        return { label: "Active", color: "bg-green-500/20 text-green-400" };
      case "disabled":
        return { label: "Disabled", color: "bg-gray-500/20 text-gray-400" };
      case "expired":
        return { label: "Expired", color: "bg-yellow-500/20 text-yellow-400" };
      case "error":
        return { label: "Error", color: "bg-red-500/20 text-red-400" };
      default:
        return { label: status, color: "bg-gray-500/20 text-gray-400" };
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (accounts.length === 0) {
    return (
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-8 text-center">
        <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-warroom-accent/10 flex items-center justify-center">
          <Shield size={24} className="text-warroom-accent" />
        </div>
        <h4 className="text-sm font-semibold text-warroom-text">No accounts configured</h4>
        <p className="text-sm text-warroom-muted mt-2">
          Add your first Instagram account to start using multi-account features for competitor intelligence and content automation.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {accounts.map((account) => {
        const typeInfo = getAccountTypeInfo(account.account_type);
        const statusInfo = getStatusInfo(account.status);
        const credentials = viewingCredentials[account.id];
        const isLoadingCredentials = loadingCredentials[account.id];
        const isTestingConnection = testingConnection[account.id];
        const testResult = testResults[account.id];

        return (
          <div key={account.id} className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
            {/* Main Account Info */}
            <div className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center text-white font-semibold">
                    {account.username.slice(0, 2).toUpperCase()}
                  </div>

                  {/* Account Details */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-sm font-semibold text-warroom-text">@{account.username}</h4>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeInfo.color}`}>
                        {typeInfo.icon} {typeInfo.label}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}>
                        {statusInfo.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-warroom-muted">
                      <div className="flex items-center gap-1">
                        <Key size={12} />
                        <span>Password: {account.has_password ? "Configured" : "Not set"}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Shield size={12} />
                        <span>2FA: {account.has_totp_secret ? "Configured" : "Not set"}</span>
                      </div>
                      {account.last_used_at && (
                        <div className="flex items-center gap-1">
                          <Clock size={12} />
                          <span>Last used: {formatDate(account.last_used_at)}</span>
                        </div>
                      )}
                    </div>

                    {account.notes && (
                      <p className="text-xs text-warroom-muted mt-2">{account.notes}</p>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleViewCredentials(account)}
                    disabled={isLoadingCredentials}
                    className="p-2 text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg rounded-lg transition"
                    title={credentials ? "Hide credentials" : "View credentials"}
                  >
                    {isLoadingCredentials ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
                  </button>

                  <button
                    onClick={() => handleTestConnection(account)}
                    disabled={isTestingConnection}
                    className="p-2 text-warroom-muted hover:text-green-400 hover:bg-green-500/10 rounded-lg transition"
                    title="Test connection"
                  >
                    {isTestingConnection ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                  </button>

                  <button
                    onClick={() => handleEdit(account)}
                    className="p-2 text-warroom-muted hover:text-warroom-accent hover:bg-warroom-accent/10 rounded-lg transition"
                    title="Edit account"
                  >
                    <Edit size={16} />
                  </button>

                  <button
                    onClick={() => handleDelete(account)}
                    className="p-2 text-warroom-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                    title="Delete account"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {/* Test Result */}
              {testResult && (
                <div className={`mt-3 p-3 rounded-lg border text-sm ${
                  testResult.success
                    ? 'bg-green-500/10 border-green-500/20 text-green-400'
                    : 'bg-red-500/10 border-red-500/20 text-red-400'
                }`}>
                  <div className="flex items-center gap-2">
                    {testResult.success ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                    <span>{testResult.message}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Credentials View */}
            {credentials && (
              <div className="border-t border-warroom-border bg-warroom-bg/50 p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Username</label>
                    <div className="bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm font-mono">
                      {credentials.username}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Password</label>
                    <div className="bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm font-mono">
                      {credentials.password ? "••••••••••••" : "Not set"}
                    </div>
                  </div>

                  {credentials.totp_secret && (
                    <>
                      <div>
                        <label className="block text-xs font-medium text-warroom-muted mb-1">TOTP Secret</label>
                        <div className="bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm font-mono">
                          {credentials.totp_secret}
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-warroom-muted mb-1">Current TOTP Code</label>
                        <div className="bg-green-500/10 border border-green-500/20 rounded px-3 py-2 text-sm font-mono text-green-400">
                          {credentials.current_totp_code}
                        </div>
                      </div>
                    </>
                  )}
                </div>

                <div className="mt-3 text-xs text-warroom-muted">
                  ⚠️ Keep these credentials secure. They provide full access to this Instagram account.
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Edit Modal */}
      {editingAccount && (
        <InstagramAccountForm
          account={editingAccount}
          onClose={() => setEditingAccount(null)}
          onAccountAdded={() => {
            setEditingAccount(null);
            onAccountDeleted(); // Refresh the list
          }}
        />
      )}
    </div>
  );
}