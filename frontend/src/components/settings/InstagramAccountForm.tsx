"use client";

import { useState } from "react";
import { X, Save, Eye, EyeOff, AlertCircle, CheckCircle, Loader2, Shield, HelpCircle } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface InstagramAccountFormProps {
  onClose: () => void;
  onAccountAdded: () => void;
  account?: {
    id: number;
    username: string;
    account_type: string;
    notes?: string | null;
  } | null;
}

interface FormData {
  platform: string;
  account_type: string;
  username: string;
  password: string;
  totp_secret: string;
  notes: string;
}

const ACCOUNT_TYPES = [
  {
    value: "scraping",
    label: "Scraping",
    description: "For competitor intelligence and content analysis",
    icon: "🔍",
    color: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  },
  {
    value: "posting",
    label: "Posting",
    description: "For content publishing and engagement",
    icon: "📝",
    color: "bg-green-500/10 text-green-400 border-green-500/20",
  },
  {
    value: "primary",
    label: "Primary",
    description: "Main business account for official brand presence",
    icon: "⭐",
    color: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  },
];

export default function InstagramAccountForm({ onClose, onAccountAdded, account }: InstagramAccountFormProps) {
  const [formData, setFormData] = useState<FormData>({
    platform: "instagram",
    account_type: account?.account_type || "scraping",
    username: account?.username || "",
    password: "",
    totp_secret: "",
    notes: account?.notes || "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showTotpSecret, setShowTotpSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; totp_code?: string } | null>(null);

  const isEdit = !!account;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      const url = isEdit 
        ? `${API}/api/settings/social-accounts/${account.id}`
        : `${API}/api/settings/social-accounts`;
      
      const method = isEdit ? "PUT" : "POST";
      
      const payload = isEdit
        ? {
            account_type: formData.account_type,
            password: formData.password || undefined,
            totp_secret: formData.totp_secret || undefined,
            notes: formData.notes || undefined,
          }
        : {
            platform: formData.platform,
            account_type: formData.account_type,
            username: formData.username,
            password: formData.password || undefined,
            totp_secret: formData.totp_secret || undefined,
            notes: formData.notes || undefined,
          };

      const response = await authFetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Failed to ${isEdit ? 'update' : 'create'} account`);
      }

      onAccountAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    if (!formData.username || !formData.password) {
      setError("Username and password are required for testing");
      return;
    }

    setTesting(true);
    setError("");
    setTestResult(null);

    try {
      const response = await authFetch(`${API}/api/settings/social-accounts/test-connection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.username,
          password: formData.password,
          totp_secret: formData.totp_secret || undefined,
        }),
      });

      const result = await response.json();
      setTestResult(result);

      if (!result.success) {
        setError(result.message || "Connection test failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setTesting(false);
    }
  };

  const selectedAccountType = ACCOUNT_TYPES.find(t => t.value === formData.account_type);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center px-4 py-8">
        <div className="absolute inset-0 bg-black/50" onClick={onClose} />
        <div className="relative w-full max-w-lg bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden shadow-xl">
          <form onSubmit={handleSubmit}>
            {/* Header */}
            <div className="px-6 py-4 border-b border-warroom-border flex items-center justify-between">
              <div>
                <h4 className="text-lg font-semibold text-warroom-text">
                  {isEdit ? "Edit Instagram Account" : "Add Instagram Account"}
                </h4>
                <p className="text-xs text-warroom-muted mt-1">
                  {isEdit ? "Update account credentials and settings" : "Add username/password account for scraping and automation"}
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="text-warroom-muted hover:text-warroom-text transition"
              >
                <X size={18} />
              </button>
            </div>

            {/* Form Content */}
            <div className="px-6 py-5 space-y-6">
              {/* Security Notice */}
              <div className="bg-warroom-accent/10 border border-warroom-accent/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <Shield size={16} className="text-warroom-accent flex-shrink-0 mt-0.5" />
                  <div>
                    <h5 className="text-sm font-medium text-warroom-accent">Secure Storage</h5>
                    <p className="text-xs text-warroom-accent/80 mt-1">
                      All credentials are encrypted using AES-256 before storage. Passwords and 2FA secrets are never stored in plain text.
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                  <AlertCircle size={14} />
                  <span>{error}</span>
                </div>
              )}

              {/* Test Result */}
              {testResult && (
                <div className={`flex items-start gap-2 px-3 py-2 rounded-lg text-sm ${
                  testResult.success 
                    ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
                    : 'bg-red-500/10 border border-red-500/20 text-red-400'
                }`}>
                  {testResult.success ? <CheckCircle size={14} className="mt-0.5" /> : <AlertCircle size={14} className="mt-0.5" />}
                  <div className="flex-1">
                    <span>{testResult.message}</span>
                    {testResult.totp_code && (
                      <div className="mt-2 p-2 bg-warroom-surface/50 rounded border">
                        <span className="text-xs text-warroom-muted">Current TOTP Code:</span>
                        <span className="ml-2 font-mono font-semibold">{testResult.totp_code}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Account Type Selection */}
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-3">Account Type</label>
                <div className="space-y-3">
                  {ACCOUNT_TYPES.map((type) => (
                    <label
                      key={type.value}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition ${
                        formData.account_type === type.value
                          ? type.color
                          : 'border-warroom-border hover:border-warroom-accent/30'
                      }`}
                    >
                      <input
                        type="radio"
                        name="account_type"
                        value={type.value}
                        checked={formData.account_type === type.value}
                        onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">{type.icon}</span>
                          <span className="text-sm font-medium text-warroom-text">{type.label}</span>
                        </div>
                        <p className="text-xs text-warroom-muted">{type.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Username */}
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-2">
                  Instagram Username *
                </label>
                <input
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  disabled={isEdit} // Can't change username when editing
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent disabled:opacity-50"
                  placeholder="your_instagram_username"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-2">
                  Password {isEdit && "(leave blank to keep current)"}
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 pr-10 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                    placeholder={isEdit ? "Enter new password..." : "Enter account password"}
                    required={!isEdit}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted hover:text-warroom-text transition"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* TOTP Secret */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <label className="block text-sm font-medium text-warroom-text">
                    2FA TOTP Secret {isEdit && "(leave blank to keep current)"}
                  </label>
                  <div className="group relative">
                    <HelpCircle size={14} className="text-warroom-muted hover:text-warroom-text cursor-help" />
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-warroom-surface border border-warroom-border rounded-lg text-xs text-warroom-text shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10 whitespace-nowrap">
                      Base32 secret from your authenticator app setup
                    </div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type={showTotpSecret ? "text" : "password"}
                    value={formData.totp_secret}
                    onChange={(e) => setFormData({ ...formData, totp_secret: e.target.value })}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 pr-10 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent font-mono"
                    placeholder="JBSWY3DPEHPK3PXP..."
                  />
                  <button
                    type="button"
                    onClick={() => setShowTotpSecret(!showTotpSecret)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted hover:text-warroom-text transition"
                  >
                    {showTotpSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <p className="text-xs text-warroom-muted mt-1">
                  Optional: The base32 secret key from your 2FA app for automatic TOTP generation
                </p>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-2">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={3}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                  placeholder="Optional notes about this account..."
                />
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-warroom-border flex items-center justify-between">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testing || !formData.username || !formData.password}
                className="flex items-center gap-2 px-4 py-2 text-sm border border-warroom-border text-warroom-text hover:bg-warroom-bg disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition"
              >
                {testing ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                {testing ? "Testing..." : "Test Connection"}
              </button>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm border border-warroom-border text-warroom-text hover:bg-warroom-bg rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || (!isEdit && (!formData.username || !formData.password))}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-lg transition"
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? "Saving..." : isEdit ? "Update Account" : "Add Account"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}