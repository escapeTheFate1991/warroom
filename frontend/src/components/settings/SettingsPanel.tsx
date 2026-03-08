"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Settings, Key, Save, Eye, EyeOff, Check, AlertCircle, MapPin, Zap, Building2, Mail, Share2, Package, Target, Bot, Shield, Plus, Edit, Trash2, Users, UserPlus, ChevronDown, Calendar, Loader2, Globe, X, RefreshCw } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import { useThemeContext } from "@/components/ui/ThemeProvider";


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
  business: {
    label: "Business Details",
    icon: Building2,
    description: "Legal entity info for contracts, invoices, and proposals",
  },
};

// Group API keys into logical drawers
const API_KEY_GROUPS: Record<string, { label: string; keys: string[] }> = {
  google: {
    label: "Google",
    keys: ["google_maps_api_key", "google_oauth_client_id", "google_oauth_client_secret"],
  },
  meta: {
    label: "Meta (Facebook / Instagram / Threads)",
    keys: ["meta_app_id", "meta_app_secret", "instagram_app_id", "instagram_app_secret", "threads_client_id", "threads_client_secret"],
  },
  x: {
    label: "X (Twitter)",
    keys: ["x_client_id", "x_client_secret"],
  },
  tiktok: {
    label: "TikTok",
    keys: ["tiktok_client_key", "tiktok_client_secret"],
  },
  ai: {
    label: "AI & Search",
    keys: ["openclaw_auth_token", "serp_api_key"],
  },
};

const KEY_LABELS: Record<string, string> = {
  google_maps_api_key: "Google Maps API Key",
  google_oauth_client_id: "OAuth Client ID (YouTube + Calendar)",
  google_oauth_client_secret: "OAuth Client Secret (YouTube + Calendar)",
  serp_api_key: "SerpAPI Key",
  openclaw_auth_token: "OpenClaw Auth Token",
  meta_app_id: "App ID",
  meta_app_secret: "App Secret",
  instagram_app_id: "Instagram App ID",
  instagram_app_secret: "Instagram App Secret",
  threads_client_id: "Threads Client ID",
  threads_client_secret: "Threads Client Secret",
  x_client_id: "Client ID",
  x_client_secret: "Client Secret",
  tiktok_client_key: "Client Key",
  tiktok_client_secret: "Client Secret",
  company_name: "Company Name",
  your_name: "Your Name",
  your_phone: "Your Phone",
  business_legal_name: "Legal Entity Name",
  business_dba: "DBA / Trade Name",
  business_address_line1: "Address Line 1",
  business_address_line2: "Address Line 2",
  business_city: "City",
  business_state: "State / Province",
  business_zip: "ZIP / Postal Code",
  business_country: "Country",
  business_phone: "Business Phone",
  business_email: "Business Email",
  business_website: "Website URL",
  business_ein: "EIN / Tax ID",
  business_entity_type: "Entity Type",
  business_state_of_formation: "State of Formation",
  business_logo_url: "Logo URL",
  business_authorized_signer: "Authorized Signer",
  business_signer_title: "Signer Title",
  default_search_location: "Default Search Location",
  max_search_results: "Max Search Results",
  auto_enrich: "Auto-Enrich Leads",
};

const SETTINGS_TABS = [
  { id: "general", label: "General", icon: Building2 },
  { id: "business", label: "Business Details", icon: Building2 },
  { id: "email", label: "Email & Calendar", icon: Mail },
  { id: "social", label: "Social Media", icon: Share2 },
  { id: "products", label: "Products", icon: Package },
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

interface EmailAccount {
  id: number;
  provider: 'gmail' | 'imap';
  email: string;
  status: 'connected' | 'disconnected' | 'error';
  last_synced?: string;
}

interface ImapConfig {
  host: string;
  port: string;
  username: string;
  password: string;
  ssl: boolean;
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

interface Product {
  id: number;
  name: string;
  sku: string | null;
  description: string | null;
  price: number | null;
  quantity: number;
  created_at: string;
  updated_at: string;
}

interface ProductFormData {
  name: string;
  sku: string;
  description: string;
  price: string;
  quantity: string;
}

export default function SettingsPanel() {
  const { theme, toggleTheme } = useThemeContext();
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [settings, setSettings] = useState<Setting[]>([]);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<Record<string, boolean>>({}); // Track if user is editing a secret
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [openDrawers, setOpenDrawers] = useState<Record<string, boolean>>({});
  
  // Google Calendar state
  const [googleCalStatus, setGoogleCalStatus] = useState<{ connected: boolean; email?: string }>({ connected: false });
  const [googleCalLoading, setGoogleCalLoading] = useState(false);
  const [googleCalError, setGoogleCalError] = useState("");

  // Refs for cleanup of Google Calendar OAuth popup polling
  const googlePopupCheckRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const googleMessageHandlerRef = useRef<((event: MessageEvent) => void) | null>(null);

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

  // Email accounts state (for reading emails)
  const [emailAccounts, setEmailAccounts] = useState<EmailAccount[]>([]);
  const [emailProvider, setEmailProvider] = useState<'gmail' | 'imap'>('gmail');
  const [imapConfig, setImapConfig] = useState<ImapConfig>({
    host: '',
    port: '993',
    username: '',
    password: '',
    ssl: true,
  });
  const [imapConnecting, setImapConnecting] = useState(false);
  const [imapStatus, setImapStatus] = useState<{ success?: boolean; message?: string } | null>(null);
  const [gmailConnecting, setGmailConnecting] = useState(false);
  const [gmailError, setGmailError] = useState('');
  const [syncingAccountId, setSyncingAccountId] = useState<number | null>(null);

  // Refs for Gmail OAuth popup polling
  const gmailPopupCheckRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const gmailMessageHandlerRef = useRef<((event: MessageEvent) => void) | null>(null);

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

  // Product management state
  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productError, setProductError] = useState("");
  const [showProductModal, setShowProductModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [savingProduct, setSavingProduct] = useState(false);
  const [productFormData, setProductFormData] = useState<ProductFormData>({
    name: "",
    sku: "",
    description: "",
    price: "",
    quantity: "0",
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
      const resp = await authFetch(`${API}/api/settings`);
      if (resp.ok) {
        const data = await resp.json();
        setSettings(data);
        // Initialize edit values — use masked value for secrets so they show as filled
        const vals: Record<string, string> = {};
        data.forEach((s: Setting) => {
          vals[s.key] = s.value; // Backend already masks secrets (••••••••xxxx)
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
      const resp = await authFetch(`${API}/api/settings/email`);
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
      const scoringResp = await authFetch(`${API}/api/settings/lead-scoring`);
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
      const resp = await authFetch(`${API}/api/crm/roles`);
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
      const resp = await authFetch(`${API}/api/crm/users`);
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
      const resp = await authFetch(`${API}/api/crm/workflows`);
      if (resp.ok) {
        const data = await resp.json();
        setWorkflows(data);
      }
    } catch (error) {
      console.error("Failed to load workflows");
    }
  };

  const loadGoogleCalStatus = async () => {
    try {
      const res = await authFetch(`${API}/api/calendar/google/status`);
      if (res.ok) setGoogleCalStatus(await res.json());
    } catch {
      setGoogleCalStatus({ connected: false });
    }
  };

  const loadEmailAccounts = async () => {
    try {
      const res = await authFetch(`${API}/api/email/accounts`);
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : (data.accounts ?? []);
        setEmailAccounts(list.map((a: Record<string, unknown>) => ({
          ...a,
          status: a.is_active ? 'connected' : 'disconnected',
          last_synced: a.last_sync_at,
        })));
      }
    } catch {
      console.error("Failed to load email accounts");
    }
  };

  const loadProducts = useCallback(async () => {
    setProductsLoading(true);
    setProductError("");
    try {
      const response = await authFetch(`${API}/api/crm/products`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to load products");
      }
      const data = await response.json();
      setProducts(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load products";
      setProductError(message);
      console.error("Failed to load products:", error);
    } finally {
      setProductsLoading(false);
    }
  }, []);

  const cleanupGmailOAuth = useCallback(() => {
    if (gmailPopupCheckRef.current) {
      clearInterval(gmailPopupCheckRef.current);
      gmailPopupCheckRef.current = null;
    }
    if (gmailMessageHandlerRef.current) {
      window.removeEventListener("message", gmailMessageHandlerRef.current);
      gmailMessageHandlerRef.current = null;
    }
  }, []);

  const connectGmail = async () => {
    setGmailConnecting(true);
    setGmailError('');
    cleanupGmailOAuth();
    try {
      const res = await authFetch(`${API}/api/email/accounts/gmail/connect`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Failed to get Gmail auth URL");
      }
      const { auth_url } = await res.json();
      const popup = window.open(auth_url, "gmail-auth", "width=500,height=700,left=200,top=100");

      const handler = (event: MessageEvent) => {
        if (event.data?.type === "gmail-connected") {
          cleanupGmailOAuth();
          loadEmailAccounts();
          setGmailConnecting(false);
        } else if (event.data?.type === "gmail-error") {
          cleanupGmailOAuth();
          setGmailError(event.data.error || "Gmail OAuth failed");
          setGmailConnecting(false);
        }
      };
      gmailMessageHandlerRef.current = handler;
      window.addEventListener("message", handler);

      gmailPopupCheckRef.current = setInterval(() => {
        if (popup?.closed) {
          cleanupGmailOAuth();
          loadEmailAccounts();
          setGmailConnecting(false);
        }
      }, 1000);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to connect Gmail";
      setGmailError(message);
      setGmailConnecting(false);
    }
  };

  const disconnectEmailAccount = async (accountId: number) => {
    if (!confirm("Disconnect this email account?")) return;
    try {
      await authFetch(`${API}/api/email/accounts/${accountId}`, { method: "DELETE" });
      loadEmailAccounts();
    } catch {
      console.error("Failed to disconnect email account");
    }
  };

  const syncEmailAccount = async (accountId: number) => {
    setSyncingAccountId(accountId);
    try {
      await authFetch(`${API}/api/email/accounts/${accountId}/sync`, { method: "POST" });
      loadEmailAccounts();
    } catch {
      console.error("Failed to sync email account");
    } finally {
      setSyncingAccountId(null);
    }
  };

  const connectImap = async () => {
    setImapConnecting(true);
    setImapStatus(null);
    try {
      const res = await authFetch(`${API}/api/email/accounts/imap/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(imapConfig),
      });
      if (res.ok) {
        setImapStatus({ success: true, message: "Connected successfully!" });
        loadEmailAccounts();
        setImapConfig({ host: '', port: '993', username: '', password: '', ssl: true });
      } else {
        const err = await res.json().catch(() => null);
        setImapStatus({ success: false, message: err?.detail || "Connection failed" });
      }
    } catch {
      setImapStatus({ success: false, message: "Network error" });
    } finally {
      setImapConnecting(false);
    }
  };

  const cleanupGoogleOAuth = useCallback(() => {
    if (googlePopupCheckRef.current) {
      clearInterval(googlePopupCheckRef.current);
      googlePopupCheckRef.current = null;
    }
    if (googleMessageHandlerRef.current) {
      window.removeEventListener("message", googleMessageHandlerRef.current);
      googleMessageHandlerRef.current = null;
    }
  }, []);

  const connectGoogleCal = async () => {
    setGoogleCalLoading(true);
    setGoogleCalError("");
    cleanupGoogleOAuth(); // Clear any stale listeners from previous attempts
    try {
      const res = await authFetch(`${API}/api/calendar/google/auth-url`);
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Failed to get auth URL");
      }
      const { auth_url } = await res.json();
      const popup = window.open(auth_url, "google-calendar-auth", "width=500,height=700,left=200,top=100");

      const handler = (event: MessageEvent) => {
        if (event.data?.type === "google-calendar-connected") {
          cleanupGoogleOAuth();
          loadGoogleCalStatus();
          setGoogleCalLoading(false);
        } else if (event.data?.type === "google-calendar-error") {
          cleanupGoogleOAuth();
          setGoogleCalError(event.data.error || "OAuth failed");
          setGoogleCalLoading(false);
        }
      };
      googleMessageHandlerRef.current = handler;
      window.addEventListener("message", handler);

      googlePopupCheckRef.current = setInterval(() => {
        if (popup?.closed) {
          cleanupGoogleOAuth();
          loadGoogleCalStatus();
          setGoogleCalLoading(false);
        }
      }, 1000);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to connect";
      setGoogleCalError(message);
      setGoogleCalLoading(false);
    }
  };

  const disconnectGoogleCal = async () => {
    if (!confirm("Disconnect Google Calendar? You'll need to reconnect to sync events again.")) return;
    setGoogleCalLoading(true);
    try {
      await authFetch(`${API}/api/calendar/google/disconnect`, { method: "POST" });
      setGoogleCalStatus({ connected: false });
    } catch (err) {
      console.error("Failed to disconnect Google Calendar:", err);
    }
    setGoogleCalLoading(false);
  };

  useEffect(() => { 
    loadSettings(); 
    loadEmailSettings();
    loadScoringSettings();
    loadRoles();
    loadUsers();
    loadWorkflows();
    loadGoogleCalStatus();
    loadEmailAccounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadSettings]);

  // Cleanup Google OAuth and Gmail OAuth listeners on unmount
  useEffect(() => {
    return () => {
      cleanupGoogleOAuth();
      cleanupGmailOAuth();
    };
  }, [cleanupGoogleOAuth, cleanupGmailOAuth]);

  useEffect(() => {
    if (activeTab === "products") {
      loadProducts();
    }
  }, [activeTab, loadProducts]);

  const saveSetting = async (key: string) => {
    const value = editValues[key];
    if (value === undefined) return;

    setSaving((p) => ({ ...p, [key]: true }));
    setErrors((p) => ({ ...p, [key]: "" }));
    setSaved((p) => ({ ...p, [key]: false }));

    try {
      const resp = await authFetch(`${API}/api/settings/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        setErrors((p) => ({ ...p, [key]: err.detail || "Failed to save" }));
      } else {
        setSaved((p) => ({ ...p, [key]: true }));
        setEditing((p) => ({ ...p, [key]: false })); // Exit edit mode after save
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
      const resp = await authFetch(`${API}/api/settings/email`, {
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
      const resp = await authFetch(`${API}/api/settings/email/test`, {
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
      const resp = await authFetch(`${API}/api/settings/lead-scoring`, {
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
    alert(`Connect to ${platform} - Configure in Social Media settings`);
  };

  const handleAddProduct = () => {
    setEditingProduct(null);
    setProductError("");
    setProductFormData({
      name: "",
      sku: "",
      description: "",
      price: "",
      quantity: "0",
    });
    setShowProductModal(true);
  };

  const handleEditProduct = (product: Product) => {
    setEditingProduct(product);
    setProductError("");
    setProductFormData({
      name: product.name,
      sku: product.sku || "",
      description: product.description || "",
      price: product.price?.toString() || "",
      quantity: product.quantity.toString(),
    });
    setShowProductModal(true);
  };

  const handleCloseProductModal = () => {
    setShowProductModal(false);
    setEditingProduct(null);
  };

  const handleSubmitProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProduct(true);
    setProductError("");

    try {
      const payload = {
        name: productFormData.name.trim(),
        sku: productFormData.sku.trim() || null,
        description: productFormData.description.trim() || null,
        price: productFormData.price === "" ? null : parseFloat(productFormData.price),
        quantity: productFormData.quantity === "" ? 0 : parseInt(productFormData.quantity, 10) || 0,
      };

      const response = await authFetch(
        editingProduct ? `${API}/api/crm/products/${editingProduct.id}` : `${API}/api/crm/products`,
        {
          method: editingProduct ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to save product");
      }

      handleCloseProductModal();
      loadProducts();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save product";
      setProductError(message);
      console.error("Failed to save product:", error);
    } finally {
      setSavingProduct(false);
    }
  };

  const handleDeleteProduct = async (product: Product) => {
    if (!confirm(`Are you sure you want to delete "${product.name}"?`)) return;

    setProductError("");
    try {
      const response = await authFetch(`${API}/api/crm/products/${product.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to delete product");
      }

      loadProducts();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete product";
      setProductError(message);
      console.error("Failed to delete product:", error);
    }
  };

  // Group settings by category
  const grouped = settings.reduce<Record<string, Setting[]>>((acc, s) => {
    (acc[s.category] = acc[s.category] || []).push(s);
    return acc;
  }, {});

  const toggleDrawer = (id: string) => {
    setOpenDrawers((p) => ({ ...p, [id]: !p[id] }));
  };

  const renderSettingField = (setting: Setting) => {
    const isRevealed = revealed[setting.key];
    const isEditing = editing[setting.key];
    const isSaving = saving[setting.key];
    const isSaved = saved[setting.key];
    const error = errors[setting.key];
    const isMasked = setting.value?.startsWith("••••");
    const hasValue = setting.is_secret
      ? isMasked
      : !!(setting.value && setting.value !== "");
    const editValue = editValues[setting.key] ?? "";
    const displayValue = (setting.is_secret && hasValue && !isEditing) ? setting.value : editValue;
    const canSave = setting.is_secret
      ? (isEditing && editValue.length > 0 && !editValue.startsWith("••••"))
      : (editValue.length > 0);

    return (
      <div key={setting.key} className="bg-warroom-bg/50 border border-warroom-border/50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-sm font-medium">
            {KEY_LABELS[setting.key] || setting.key}
          </label>
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
              type={setting.is_secret && !isRevealed && !isEditing ? "password" : "text"}
              value={displayValue}
              onChange={(e) => {
                if (setting.is_secret && !isEditing) {
                  setEditing((p) => ({ ...p, [setting.key]: true }));
                  setEditValues((p) => ({ ...p, [setting.key]: e.target.value.replace(/^•+/, "") }));
                } else {
                  setEditValues((p) => ({ ...p, [setting.key]: e.target.value }));
                }
              }}
              onFocus={() => {
                if (setting.is_secret && hasValue && !isEditing) {
                  setEditing((p) => ({ ...p, [setting.key]: true }));
                  setEditValues((p) => ({ ...p, [setting.key]: "" }));
                }
              }}
              onBlur={() => {
                if (setting.is_secret && isEditing && !editValue) {
                  setEditing((p) => ({ ...p, [setting.key]: false }));
                  setEditValues((p) => ({ ...p, [setting.key]: setting.value }));
                }
              }}
              onKeyDown={(e) => handleKeyDown(e, setting.key)}
              placeholder={
                setting.is_secret
                  ? hasValue ? "Enter new value to replace..." : "Paste your API key here..."
                  : "Enter value..."
              }
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent font-mono"
            />
            {setting.is_secret && hasValue && !isEditing && (
              <button
                onClick={() => setRevealed((p) => ({ ...p, [setting.key]: !p[setting.key] }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted hover:text-warroom-text transition"
              >
                {isRevealed ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            )}
          </div>
          <button
            onClick={() => saveSetting(setting.key)}
            disabled={isSaving || !canSave}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
              isSaved
                ? "bg-green-500/20 text-green-400"
                : "bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40"
            }`}
          >
            {isSaved ? (<><Check size={14} /> Saved</>) : isSaving ? "Saving..." : (<><Save size={14} /> Save</>)}
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-1.5 mt-2 text-xs text-red-400">
            <AlertCircle size={12} /> {error}
          </div>
        )}
      </div>
    );
  };

  const renderBusinessTab = () => {
    const sections = [
      {
        title: "Company Identity",
        description: "Legal entity and registration details",
        fields: [
          { key: "business_legal_name", label: "Legal Name" },
          { key: "business_dba", label: "DBA / Trade Name" },
          { key: "business_entity_type", label: "Entity Type" },
          { key: "business_state_of_formation", label: "State of Formation" },
        ],
      },
      {
        title: "Contact Information",
        description: "Business contact details for contracts and invoices",
        fields: [
          { key: "business_email", label: "Business Email" },
          { key: "business_phone", label: "Business Phone" },
          { key: "business_website", label: "Website" },
        ],
      },
      {
        title: "Address",
        description: "Primary business address",
        fields: [
          { key: "business_address_line1", label: "Address Line 1" },
          { key: "business_address_line2", label: "Address Line 2" },
          { key: "business_city", label: "City" },
          { key: "business_state", label: "State / Province" },
          { key: "business_zip", label: "ZIP / Postal Code" },
          { key: "business_country", label: "Country" },
        ],
      },
      {
        title: "Legal & Tax",
        description: "Tax identification and authorized signers",
        fields: [
          { key: "business_ein", label: "EIN / Tax ID" },
          { key: "business_authorized_signer", label: "Authorized Signer" },
          { key: "business_signer_title", label: "Signer Title" },
        ],
      },
      {
        title: "Branding",
        description: "Logo and visual identity for generated documents",
        fields: [
          { key: "business_logo_url", label: "Logo URL" },
        ],
      },
    ];

    return (
      <div className="space-y-8">
        {sections.map((section) => (
          <section key={section.title}>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
                <Building2 size={16} className="text-warroom-accent" />
              </div>
              <div>
                <h3 className="text-sm font-semibold">{section.title}</h3>
                <p className="text-xs text-warroom-muted">{section.description}</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              {section.fields.map((field) => {
                const setting = settings.find((s) => s.key === field.key);
                if (!setting) return null;
                return renderSettingField(setting);
              })}
            </div>
          </section>
        ))}
      </div>
    );
  };

  const renderGeneralTab = () => {
    // Collect all api_keys settings into a lookup
    const apiKeySettings = (grouped["api_keys"] || []).reduce<Record<string, Setting>>((acc, s) => {
      acc[s.key] = s;
      return acc;
    }, {});

    // Keys that are in a drawer group
    const groupedKeys = new Set(Object.values(API_KEY_GROUPS).flatMap((g) => g.keys));

    // Ungrouped api_keys (fallback)
    const ungroupedApiKeys = (grouped["api_keys"] || []).filter((s) => !groupedKeys.has(s.key));

    return (
      <div className="space-y-8">
        {/* Appearance toggle */}
        <div className="flex items-center justify-between p-4 bg-warroom-bg rounded-xl border border-warroom-border">
          <div>
            <h4 className="text-sm font-semibold">Appearance</h4>
            <p className="text-xs text-warroom-muted mt-1">Toggle between dark and light mode</p>
          </div>
          <button
            onClick={toggleTheme}
            className="relative w-14 h-7 rounded-full transition-colors duration-200"
            style={{ backgroundColor: theme === "dark" ? "#1e1e2e" : "#6366f1" }}
          >
            <div
              className="absolute top-0.5 w-6 h-6 rounded-full bg-white shadow transition-transform duration-200 flex items-center justify-center text-xs"
              style={{ transform: theme === "dark" ? "translateX(2px)" : "translateX(30px)" }}
            >
              {theme === "dark" ? "🌙" : "☀️"}
            </div>
          </button>
        </div>

        {/* General & Leadgen — render flat like before */}
        {["general", "leadgen"].map((catKey) => {
          const meta = CATEGORY_META[catKey];
          const catSettings = grouped[catKey];
          if (!meta || !catSettings || catSettings.length === 0) return null;
          const Icon = meta.icon;

          return (
            <section key={catKey}>
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
                  <Icon size={16} className="text-warroom-accent" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold">{meta.label}</h3>
                  <p className="text-xs text-warroom-muted">{meta.description}</p>
                </div>
              </div>
              <div className="mt-4 space-y-3">
                {catSettings.map((setting) => renderSettingField(setting))}
              </div>
            </section>
          );
        })}

        {/* API Keys — collapsible drawers */}
        {(grouped["api_keys"] || []).length > 0 && (
          <section>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
                <Key size={16} className="text-warroom-accent" />
              </div>
              <div>
                <h3 className="text-sm font-semibold">API Keys & Credentials</h3>
                <p className="text-xs text-warroom-muted">Grouped by provider — click to expand</p>
              </div>
            </div>

            <div className="space-y-2">
              {Object.entries(API_KEY_GROUPS).map(([groupId, group]) => {
                const groupSettings = group.keys
                  .map((k) => apiKeySettings[k])
                  .filter(Boolean);
                if (groupSettings.length === 0) return null;

                const isOpen = openDrawers[groupId] ?? false;
                const configuredCount = groupSettings.filter((s) =>
                  s.is_secret ? s.value?.startsWith("••••") : !!(s.value && s.value !== "")
                ).length;

                return (
                  <div key={groupId} className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
                    <button
                      onClick={() => toggleDrawer(groupId)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-warroom-accent/5 transition"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">{group.label}</span>
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                          configuredCount === groupSettings.length
                            ? "bg-green-500/20 text-green-400"
                            : configuredCount > 0
                            ? "bg-yellow-500/20 text-yellow-400"
                            : "bg-warroom-border text-warroom-muted"
                        }`}>
                          {configuredCount}/{groupSettings.length}
                        </span>
                      </div>
                      <ChevronDown
                        size={16}
                        className={`text-warroom-muted transition-transform ${isOpen ? "rotate-180" : ""}`}
                      />
                    </button>

                    {isOpen && (
                      <div className="px-4 pb-4 space-y-3 border-t border-warroom-border/50 pt-3">
                        {groupSettings.map((setting) => renderSettingField(setting))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Ungrouped api keys */}
              {ungroupedApiKeys.length > 0 && (
                <div className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleDrawer("_other")}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-warroom-accent/5 transition"
                  >
                    <span className="text-sm font-medium">Other</span>
                    <ChevronDown
                      size={16}
                      className={`text-warroom-muted transition-transform ${openDrawers["_other"] ? "rotate-180" : ""}`}
                    />
                  </button>
                  {openDrawers["_other"] && (
                    <div className="px-4 pb-4 space-y-3 border-t border-warroom-border/50 pt-3">
                      {ungroupedApiKeys.map((setting) => renderSettingField(setting))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        )}
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
    const gmailAccount = emailAccounts.find(a => a.provider === 'gmail');
    const imapAccount = emailAccounts.find(a => a.provider === 'imap');

    return (
      <div className="space-y-8">
        {/* ── 1. Google Calendar (unchanged) ────────────────────────── */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
              <Calendar size={16} className="text-warroom-accent" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">Google Calendar</h3>
              <p className="text-xs text-warroom-muted">Sync your personal Google Calendar events</p>
            </div>
          </div>

          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
            {googleCalStatus.connected ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
                  <div>
                    <p className="text-sm font-medium text-warroom-text">Connected</p>
                    <p className="text-xs text-warroom-muted">{googleCalStatus.email}</p>
                  </div>
                </div>
                <button
                  onClick={disconnectGoogleCal}
                  disabled={googleCalLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 border border-red-500/20 transition"
                >
                  {googleCalLoading ? <Loader2 size={12} className="animate-spin" /> : <X size={12} />}
                  Disconnect
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-gray-500" />
                  <div>
                    <p className="text-sm font-medium text-warroom-text">Not connected</p>
                    <p className="text-xs text-warroom-muted">Connect to sync Google Calendar events to your Personal calendar</p>
                  </div>
                </div>
                <button
                  onClick={connectGoogleCal}
                  disabled={googleCalLoading}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm bg-warroom-accent hover:bg-warroom-accent/80 text-white font-medium transition"
                >
                  {googleCalLoading ? <Loader2 size={14} className="animate-spin" /> : <Globe size={14} />}
                  Connect
                </button>
              </div>
            )}

            {googleCalError && (
              <div className="flex items-center gap-1.5 mt-3 p-2 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
                <AlertCircle size={12} />
                <span>{googleCalError}</span>
                <button onClick={() => setGoogleCalError("")} className="ml-auto hover:text-red-300">✕</button>
              </div>
            )}

            <p className="text-[11px] text-warroom-muted/60 mt-3">
              Events sync automatically every 2 minutes while viewing the calendar. Use the Resync button on the calendar for instant refresh.
            </p>
          </div>
        </section>

        {/* ── 2. Email Reading (NEW) ─────────────────────── */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
              <Mail size={16} className="text-warroom-accent" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">Email Reading</h3>
              <p className="text-xs text-warroom-muted">Connect your inbox to read and sync emails</p>
            </div>
          </div>

          {/* Provider toggle tabs */}
          <div className="flex gap-1 mb-4 bg-warroom-bg border border-warroom-border rounded-lg p-1">
            <button
              onClick={() => setEmailProvider('gmail')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
                emailProvider === 'gmail'
                  ? 'bg-warroom-surface text-warroom-text shadow-sm'
                  : 'text-warroom-muted hover:text-warroom-text'
              }`}
            >
              <Globe size={14} />
              Gmail
            </button>
            <button
              onClick={() => setEmailProvider('imap')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
                emailProvider === 'imap'
                  ? 'bg-warroom-surface text-warroom-text shadow-sm'
                  : 'text-warroom-muted hover:text-warroom-text'
              }`}
            >
              <Mail size={14} />
              IMAP
            </button>
          </div>

          {/* Gmail sub-section */}
          {emailProvider === 'gmail' && (
            <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
              {gmailAccount && gmailAccount.status === 'connected' ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
                      <div>
                        <p className="text-sm font-medium text-warroom-text">Connected</p>
                        <p className="text-xs text-warroom-muted">{gmailAccount.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => syncEmailAccount(gmailAccount.id)}
                        disabled={syncingAccountId === gmailAccount.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-warroom-text hover:bg-warroom-bg border border-warroom-border transition"
                      >
                        {syncingAccountId === gmailAccount.id ? (
                          <Loader2 size={12} className="animate-spin" />
                        ) : (
                          <RefreshCw size={12} />
                        )}
                        Sync Now
                      </button>
                      <button
                        onClick={() => disconnectEmailAccount(gmailAccount.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 border border-red-500/20 transition"
                      >
                        <X size={12} />
                        Disconnect
                      </button>
                    </div>
                  </div>
                  {gmailAccount.last_synced && (
                    <p className="text-[11px] text-warroom-muted/60">
                      Last synced: {new Date(gmailAccount.last_synced).toLocaleString()}
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-gray-500" />
                    <div>
                      <p className="text-sm font-medium text-warroom-text">Not connected</p>
                      <p className="text-xs text-warroom-muted">Connect your Gmail account to read emails via Google API</p>
                    </div>
                  </div>
                  <button
                    onClick={connectGmail}
                    disabled={gmailConnecting}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm bg-warroom-accent hover:bg-warroom-accent/80 text-white font-medium transition"
                  >
                    {gmailConnecting ? <Loader2 size={14} className="animate-spin" /> : <Globe size={14} />}
                    Connect Gmail
                  </button>
                </div>
              )}

              {gmailError && (
                <div className="flex items-center gap-1.5 mt-3 p-2 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
                  <AlertCircle size={12} />
                  <span>{gmailError}</span>
                  <button onClick={() => setGmailError('')} className="ml-auto hover:text-red-300">✕</button>
                </div>
              )}
            </div>
          )}

          {/* IMAP sub-section */}
          {emailProvider === 'imap' && (
            <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 space-y-4">
              {imapAccount && imapAccount.status === 'connected' ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
                      <div>
                        <p className="text-sm font-medium text-warroom-text">Connected via IMAP</p>
                        <p className="text-xs text-warroom-muted">{imapAccount.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => syncEmailAccount(imapAccount.id)}
                        disabled={syncingAccountId === imapAccount.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-warroom-text hover:bg-warroom-bg border border-warroom-border transition"
                      >
                        {syncingAccountId === imapAccount.id ? (
                          <Loader2 size={12} className="animate-spin" />
                        ) : (
                          <RefreshCw size={12} />
                        )}
                        Sync Now
                      </button>
                      <button
                        onClick={() => disconnectEmailAccount(imapAccount.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 border border-red-500/20 transition"
                      >
                        <X size={12} />
                        Disconnect
                      </button>
                    </div>
                  </div>
                  {imapAccount.last_synced && (
                    <p className="text-[11px] text-warroom-muted/60">
                      Last synced: {new Date(imapAccount.last_synced).toLocaleString()}
                    </p>
                  )}
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-warroom-text block mb-2">IMAP Host</label>
                      <input
                        type="text"
                        value={imapConfig.host}
                        onChange={(e) => setImapConfig(prev => ({ ...prev, host: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
                        placeholder="imap.gmail.com"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-warroom-text block mb-2">Port</label>
                      <input
                        type="text"
                        value={imapConfig.port}
                        onChange={(e) => setImapConfig(prev => ({ ...prev, port: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
                        placeholder="993"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-warroom-text block mb-2">Username</label>
                      <input
                        type="text"
                        value={imapConfig.username}
                        onChange={(e) => setImapConfig(prev => ({ ...prev, username: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
                        placeholder="you@example.com"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-warroom-text block mb-2">Password</label>
                      <input
                        type="password"
                        value={imapConfig.password}
                        onChange={(e) => setImapConfig(prev => ({ ...prev, password: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent"
                        placeholder="Your app password"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <div
                        onClick={() => setImapConfig(prev => ({ ...prev, ssl: !prev.ssl }))}
                        className={`relative w-10 h-5 rounded-full transition cursor-pointer ${
                          imapConfig.ssl ? 'bg-warroom-accent' : 'bg-warroom-border'
                        }`}
                      >
                        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                          imapConfig.ssl ? 'translate-x-5' : 'translate-x-0.5'
                        }`} />
                      </div>
                      <span className="text-sm text-warroom-text">SSL / TLS</span>
                    </label>

                    <button
                      onClick={connectImap}
                      disabled={imapConnecting || !imapConfig.host || !imapConfig.username || !imapConfig.password}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm bg-warroom-accent hover:bg-warroom-accent/80 text-white font-medium transition disabled:opacity-40"
                    >
                      {imapConnecting ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                      Test &amp; Connect
                    </button>
                  </div>

                  {imapStatus && (
                    <div className={`flex items-center gap-1.5 p-2 rounded-lg text-xs ${
                      imapStatus.success
                        ? 'bg-green-500/10 border border-green-500/20 text-green-400'
                        : 'bg-red-500/10 border border-red-500/20 text-red-400'
                    }`}>
                      {imapStatus.success ? <Check size={12} /> : <AlertCircle size={12} />}
                      <span>{imapStatus.message}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </section>

        {/* ── 3. Email Sending (SMTP) ─────────────────────── */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
              <Mail size={16} className="text-warroom-accent" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">Email Sending (SMTP)</h3>
              <p className="text-xs text-warroom-muted">Configure outbound email delivery</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-medium text-warroom-muted uppercase tracking-wider mb-3">SMTP Server</h4>
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
              <h4 className="text-xs font-medium text-warroom-muted uppercase tracking-wider mb-3">From Information</h4>
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
        </section>
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

  const renderProductsTab = () => {
    const formatPrice = (price: number | null) => {
      if (price === null) return "—";
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
      }).format(price);
    };

    const getProductStatus = (product: Product) => {
      if (product.quantity > 10) {
        return { label: "In stock", detail: `${product.quantity} available`, className: "bg-green-500/20 text-green-400" };
      }
      if (product.quantity > 0) {
        return { label: "Low stock", detail: `${product.quantity} left`, className: "bg-yellow-500/20 text-yellow-400" };
      }
      return { label: "Out of stock", detail: "0 available", className: "bg-red-500/20 text-red-400" };
    };

    return (
      <>
        <div className="space-y-6">
          <section>
            <div className="flex items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
                  <Package size={16} className="text-warroom-accent" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold">Products</h3>
                  <p className="text-xs text-warroom-muted">Manage your product catalog for CRM deals and quoting.</p>
                </div>
              </div>
              <button
                onClick={handleAddProduct}
                className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
              >
                <Plus size={16} />
                Add Product
              </button>
            </div>

            {productError && (
              <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                <AlertCircle size={14} />
                <span>{productError}</span>
              </div>
            )}

            {productsLoading ? (
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-10 flex items-center justify-center text-warroom-muted">
                <Loader2 size={18} className="animate-spin mr-2" />
                Loading products...
              </div>
            ) : products.length === 0 ? (
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-10 text-center">
                <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-warroom-accent/10 flex items-center justify-center">
                  <Package size={22} className="text-warroom-accent" />
                </div>
                <h4 className="text-sm font-semibold text-warroom-text">No products yet</h4>
                <p className="text-sm text-warroom-muted mt-2 mb-5">Add products here to make them available throughout the CRM.</p>
                <button
                  onClick={handleAddProduct}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
                >
                  <Plus size={14} />
                  Add Product
                </button>
              </div>
            ) : (
              <div className="bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="bg-warroom-bg border-b border-warroom-border">
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Price</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Description</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Status</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-warroom-muted">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.map((product) => {
                        const status = getProductStatus(product);
                        return (
                          <tr key={product.id} className="border-b border-warroom-border/50 last:border-b-0 hover:bg-warroom-bg/40 transition">
                            <td className="px-4 py-4 align-top">
                              <p className="font-medium text-warroom-text">{product.name}</p>
                              <p className="text-xs text-warroom-muted mt-1">SKU: {product.sku || "—"}</p>
                            </td>
                            <td className="px-4 py-4 align-top text-warroom-text font-medium">{formatPrice(product.price)}</td>
                            <td className="px-4 py-4 align-top text-warroom-muted max-w-md">
                              <p className="line-clamp-2">{product.description || "No description provided."}</p>
                            </td>
                            <td className="px-4 py-4 align-top">
                              <span className={`inline-flex flex-col px-2.5 py-1 rounded-full text-xs font-medium ${status.className}`}>
                                <span>{status.label}</span>
                                <span className="opacity-80">{status.detail}</span>
                              </span>
                            </td>
                            <td className="px-4 py-4 align-top">
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  onClick={() => handleEditProduct(product)}
                                  className="p-2 text-warroom-muted hover:text-warroom-accent hover:bg-warroom-bg rounded-lg transition"
                                  title="Edit product"
                                >
                                  <Edit size={14} />
                                </button>
                                <button
                                  onClick={() => handleDeleteProduct(product)}
                                  className="p-2 text-warroom-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                                  title="Delete product"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        </div>

        {showProductModal && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex min-h-screen items-center justify-center px-4 py-8">
              <div className="absolute inset-0 bg-black/50" onClick={handleCloseProductModal} />
              <div className="relative w-full max-w-lg bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden shadow-xl">
                <form onSubmit={handleSubmitProduct}>
                  <div className="px-6 py-4 border-b border-warroom-border flex items-center justify-between">
                    <div>
                      <h4 className="text-lg font-semibold text-warroom-text">
                        {editingProduct ? "Edit Product" : "Add Product"}
                      </h4>
                      <p className="text-xs text-warroom-muted mt-1">Products added here are available throughout the CRM.</p>
                    </div>
                    <button
                      type="button"
                      onClick={handleCloseProductModal}
                      className="text-warroom-muted hover:text-warroom-text transition"
                    >
                      <X size={18} />
                    </button>
                  </div>

                  <div className="px-6 py-5 space-y-4">
                    {productError && (
                      <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                        <AlertCircle size={14} />
                        <span>{productError}</span>
                      </div>
                    )}

                    <div>
                      <label className="block text-xs font-medium text-warroom-muted mb-1">Product Name *</label>
                      <input
                        type="text"
                        required
                        value={productFormData.name}
                        onChange={(e) => setProductFormData((prev) => ({ ...prev, name: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                        placeholder="Enter product name"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-warroom-muted mb-1">SKU</label>
                      <input
                        type="text"
                        value={productFormData.sku}
                        onChange={(e) => setProductFormData((prev) => ({ ...prev, sku: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent font-mono"
                        placeholder="Optional SKU"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-warroom-muted mb-1">Description</label>
                      <textarea
                        value={productFormData.description}
                        onChange={(e) => setProductFormData((prev) => ({ ...prev, description: e.target.value }))}
                        rows={3}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                        placeholder="Optional product description"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-warroom-muted mb-1">Price</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={productFormData.price}
                          onChange={(e) => setProductFormData((prev) => ({ ...prev, price: e.target.value }))}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                          placeholder="0.00"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-warroom-muted mb-1">Quantity</label>
                        <input
                          type="number"
                          min="0"
                          value={productFormData.quantity}
                          onChange={(e) => setProductFormData((prev) => ({ ...prev, quantity: e.target.value }))}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                          placeholder="0"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="px-6 py-4 border-t border-warroom-border flex items-center justify-end gap-3">
                    <button
                      type="button"
                      onClick={handleCloseProductModal}
                      className="px-4 py-2 text-sm border border-warroom-border text-warroom-text hover:bg-warroom-bg rounded-lg transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={savingProduct}
                      className="px-4 py-2 text-sm bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-60 text-white rounded-lg transition flex items-center gap-2"
                    >
                      {savingProduct ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                      {savingProduct ? "Saving..." : editingProduct ? "Update Product" : "Add Product"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}
      </>
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
        <div className={activeTab === "products" ? "max-w-6xl mx-auto" : "max-w-2xl mx-auto"}>
          {activeTab === "general" && renderGeneralTab()}
          {activeTab === "business" && renderBusinessTab()}
          {activeTab === "email" && renderEmailTab()}
          {activeTab === "social" && renderSocialTab()}
          {activeTab === "products" && renderProductsTab()}
          {activeTab === "scoring" && renderScoringTab()}
          {activeTab === "automation" && renderAutomationTab()}
          {activeTab === "access" && renderAccessTab()}
        </div>
      </div>
    </div>
  );
}