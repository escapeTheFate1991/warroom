"use client";

import { useState, useEffect, useCallback } from "react";
import {
  CreditCard,
  Check,
  AlertCircle,
  Loader2,
  RefreshCw,
  Plus,
  Edit,
  Trash2,
  X,
  Save,
  Zap,
  CheckCircle,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────

interface StripeConfig {
  mode: string;
  public_key: string;
  connected: boolean;
  error?: string;
}

interface StripeProduct {
  id: number;
  stripe_product_id: string | null;
  stripe_price_id: string | null;
  name: string;
  description: string | null;
  price_cents: number;
  interval: string;
  features: string[];
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

interface ProductFormData {
  name: string;
  description: string;
  price_cents: string;
  interval: string;
  features: string[];
  sort_order: string;
}

const EMPTY_FORM: ProductFormData = {
  name: "",
  description: "",
  price_cents: "",
  interval: "month",
  features: [],
  sort_order: "0",
};

// ── Component ───────────────────────────────────────────────────────

export default function StripeSettingsPanel() {
  const [config, setConfig] = useState<StripeConfig | null>(null);
  const [products, setProducts] = useState<StripeProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [productsLoading, setProductsLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{ synced: number; errors: { product: string; error: string }[] } | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [togglingMode, setTogglingMode] = useState(false);
  const [error, setError] = useState("");

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<StripeProduct | null>(null);
  const [formData, setFormData] = useState<ProductFormData>(EMPTY_FORM);
  const [savingProduct, setSavingProduct] = useState(false);
  const [newFeature, setNewFeature] = useState("");

  // ── Data loading ──────────────────────────────────────────────────

  const loadConfig = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/stripe`);
      if (res.ok) setConfig(await res.json());
    } catch {
      setError("Failed to load Stripe config");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProducts = useCallback(async () => {
    setProductsLoading(true);
    try {
      const res = await authFetch(`${API}/api/stripe/products`);
      if (res.ok) {
        const data = await res.json();
        setProducts(data.filter((p: StripeProduct) => p.is_active));
      }
    } catch {
      setError("Failed to load products");
    } finally {
      setProductsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
    loadProducts();
  }, [loadConfig, loadProducts]);

  // ── Actions ───────────────────────────────────────────────────────

  const toggleMode = async () => {
    if (!config) return;
    setTogglingMode(true);
    const newMode = config.mode === "test" ? "live" : "test";
    try {
      const res = await authFetch(`${API}/api/stripe`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: newMode }),
      });
      if (res.ok) {
        await loadConfig();
      }
    } catch {
      setError("Failed to toggle mode");
    } finally {
      setTogglingMode(false);
    }
  };

  const testConnection = async () => {
    setTestingConnection(true);
    try {
      const res = await authFetch(`${API}/api/stripe/test-connection`);
      if (res.ok) {
        const data = await res.json();
        setConfig((prev) => prev ? { ...prev, connected: data.connected, error: data.error } : prev);
      }
    } catch {
      setError("Connection test failed");
    } finally {
      setTestingConnection(false);
    }
  };

  const syncProducts = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await authFetch(`${API}/api/stripe/sync`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setSyncResult(data);
        await loadProducts();
      }
    } catch {
      setError("Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  // ── Product CRUD ──────────────────────────────────────────────────

  const openAddModal = () => {
    setEditingProduct(null);
    setFormData(EMPTY_FORM);
    setNewFeature("");
    setShowModal(true);
  };

  const openEditModal = (product: StripeProduct) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      description: product.description || "",
      price_cents: (product.price_cents / 100).toFixed(2),
      interval: product.interval || "month",
      features: product.features || [],
      sort_order: product.sort_order.toString(),
    });
    setNewFeature("");
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingProduct(null);
    setError("");
  };

  const addFeature = () => {
    if (!newFeature.trim()) return;
    setFormData((prev) => ({ ...prev, features: [...prev.features, newFeature.trim()] }));
    setNewFeature("");
  };

  const removeFeature = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      features: prev.features.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProduct(true);
    setError("");

    const priceDollars = parseFloat(formData.price_cents);
    if (isNaN(priceDollars) || priceDollars < 0) {
      setError("Invalid price");
      setSavingProduct(false);
      return;
    }

    const payload = {
      name: formData.name.trim(),
      description: formData.description.trim() || null,
      price_cents: Math.round(priceDollars * 100),
      interval: formData.interval,
      features: formData.features,
      sort_order: parseInt(formData.sort_order) || 0,
    };

    try {
      const url = editingProduct
        ? `${API}/api/stripe/products/${editingProduct.id}`
        : `${API}/api/stripe/products`;

      const res = await authFetch(url, {
        method: editingProduct ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Failed to save product");
      }

      closeModal();
      await loadProducts();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save";
      setError(message);
    } finally {
      setSavingProduct(false);
    }
  };

  const deleteProduct = async (product: StripeProduct) => {
    if (!confirm(`Archive "${product.name}"? It will be deactivated in Stripe.`)) return;
    try {
      const res = await authFetch(`${API}/api/stripe/products/${product.id}`, {
        method: "DELETE",
      });
      if (res.ok) await loadProducts();
    } catch {
      setError("Failed to delete product");
    }
  };

  // ── Helpers ───────────────────────────────────────────────────────

  const formatPrice = (cents: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);

  const intervalLabel = (interval: string) => {
    if (interval === "one_time") return "one-time";
    return `/ ${interval}`;
  };

  // ── Render ────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-warroom-muted">
        <Loader2 size={18} className="animate-spin mr-2" />
        Loading Stripe settings...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* ── Connection Status Card ─────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
            <CreditCard size={16} className="text-purple-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Stripe Connection</h3>
            <p className="text-xs text-warroom-muted">Manage your Stripe integration and billing mode</p>
          </div>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5 space-y-4">
          {/* Connection status */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-2.5 h-2.5 rounded-full ${config?.connected ? "bg-green-400" : "bg-red-400"}`} />
              <div>
                <p className="text-sm font-medium text-warroom-text">
                  {config?.connected ? "Connected" : "Not connected"}
                </p>
                {config?.error && (
                  <p className="text-xs text-red-400 mt-0.5">{config.error}</p>
                )}
              </div>
            </div>
            <button
              onClick={testConnection}
              disabled={testingConnection}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-warroom-text hover:bg-warroom-bg border border-warroom-border transition"
            >
              {testingConnection ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Zap size={12} />
              )}
              Test
            </button>
          </div>

          {/* Mode toggle */}
          <div className="flex items-center justify-between pt-3 border-t border-warroom-border/50">
            <div>
              <p className="text-sm font-medium text-warroom-text">Mode</p>
              <p className="text-xs text-warroom-muted mt-0.5">
                {config?.mode === "live"
                  ? "Live mode — charges are real"
                  : "Test mode — no real charges"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium ${config?.mode === "test" ? "text-yellow-400" : "text-warroom-muted"}`}>
                Test
              </span>
              <button
                onClick={toggleMode}
                disabled={togglingMode}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  config?.mode === "live" ? "bg-green-500" : "bg-yellow-500"
                }`}
              >
                <span
                  className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                    config?.mode === "live" ? "translate-x-5" : "translate-x-0.5"
                  }`}
                />
              </button>
              <span className={`text-xs font-medium ${config?.mode === "live" ? "text-green-400" : "text-warroom-muted"}`}>
                Live
              </span>
            </div>
          </div>

          {config?.mode === "test" && (
            <div className="px-3 py-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
              <p className="text-xs text-yellow-400">
                ⚠️ Test mode active — products and prices are created in your Stripe test environment.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ── Products ───────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
              <CreditCard size={16} className="text-warroom-accent" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">Products & Pricing</h3>
              <p className="text-xs text-warroom-muted">Manage your Stripe products and subscription tiers</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={syncProducts}
              disabled={syncing}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-warroom-text hover:bg-warroom-bg border border-warroom-border transition"
            >
              {syncing ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <RefreshCw size={14} />
              )}
              Sync to Stripe
            </button>
            <button
              onClick={openAddModal}
              className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
            >
              <Plus size={16} />
              Add Product
            </button>
          </div>
        </div>

        {/* Sync result */}
        {syncResult && (
          <div className={`mb-4 px-3 py-2 rounded-lg text-xs flex items-center gap-2 ${
            syncResult.errors.length > 0
              ? "bg-yellow-500/10 border border-yellow-500/20 text-yellow-400"
              : "bg-green-500/10 border border-green-500/20 text-green-400"
          }`}>
            <CheckCircle size={12} />
            Synced {syncResult.synced} products.
            {syncResult.errors.length > 0 && (
              <span className="ml-1">{syncResult.errors.length} errors.</span>
            )}
            <button onClick={() => setSyncResult(null)} className="ml-auto hover:opacity-70">✕</button>
          </div>
        )}

        {error && (
          <div className="mb-4 flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
            <AlertCircle size={14} />
            <span>{error}</span>
            <button onClick={() => setError("")} className="ml-auto hover:opacity-70">✕</button>
          </div>
        )}

        {productsLoading ? (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-10 flex items-center justify-center text-warroom-muted">
            <Loader2 size={18} className="animate-spin mr-2" />
            Loading products...
          </div>
        ) : products.length === 0 ? (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-10 text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <CreditCard size={22} className="text-purple-400" />
            </div>
            <h4 className="text-sm font-semibold text-warroom-text">No products yet</h4>
            <p className="text-sm text-warroom-muted mt-2 mb-5">Add products to sync with your Stripe account.</p>
            <button
              onClick={openAddModal}
              className="inline-flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
            >
              <Plus size={14} />
              Add Product
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {products.map((product) => (
              <div
                key={product.id}
                className="bg-warroom-surface border border-warroom-border rounded-xl p-5 flex flex-col"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="text-base font-semibold text-warroom-text">{product.name}</h4>
                    {product.description && (
                      <p className="text-xs text-warroom-muted mt-1 line-clamp-2">{product.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => openEditModal(product)}
                      className="p-1.5 text-warroom-muted hover:text-warroom-accent hover:bg-warroom-bg rounded-lg transition"
                    >
                      <Edit size={13} />
                    </button>
                    <button
                      onClick={() => deleteProduct(product)}
                      className="p-1.5 text-warroom-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                {/* Price */}
                <div className="mb-4">
                  <span className="text-2xl font-bold text-warroom-text">
                    {formatPrice(product.price_cents)}
                  </span>
                  <span className="text-sm text-warroom-muted ml-1">
                    {intervalLabel(product.interval)}
                  </span>
                </div>

                {/* Features */}
                {product.features && product.features.length > 0 && (
                  <ul className="space-y-1.5 flex-1">
                    {product.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-warroom-muted">
                        <Check size={12} className="text-green-400 mt-0.5 shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {/* Stripe sync status */}
                <div className="mt-4 pt-3 border-t border-warroom-border/50">
                  {product.stripe_product_id ? (
                    <div className="flex items-center gap-1.5 text-[10px] text-green-400">
                      <CheckCircle size={10} />
                      Synced to Stripe
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[10px] text-warroom-muted">
                      <AlertCircle size={10} />
                      Not synced — click &quot;Sync to Stripe&quot;
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Add/Edit Modal ─────────────────────────────────────────── */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center px-4 py-8">
            <div className="absolute inset-0 bg-black/50" onClick={closeModal} />
            <div className="relative w-full max-w-lg bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden shadow-xl">
              <form onSubmit={handleSubmit}>
                <div className="px-6 py-4 border-b border-warroom-border flex items-center justify-between">
                  <div>
                    <h4 className="text-lg font-semibold text-warroom-text">
                      {editingProduct ? "Edit Product" : "Add Product"}
                    </h4>
                    <p className="text-xs text-warroom-muted mt-1">
                      {editingProduct ? "Update product details" : "Create a new subscription product"}
                    </p>
                  </div>
                  <button type="button" onClick={closeModal} className="text-warroom-muted hover:text-warroom-text transition">
                    <X size={18} />
                  </button>
                </div>

                <div className="px-6 py-5 space-y-4">
                  {error && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                      <AlertCircle size={14} />
                      <span>{error}</span>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Product Name *</label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder="e.g. Growth Plan"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Description</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
                      rows={2}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                      placeholder="Brief description of this plan"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-warroom-muted mb-1">Price (USD) *</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        required
                        value={formData.price_cents}
                        onChange={(e) => setFormData((p) => ({ ...p, price_cents: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                        placeholder="299.00"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-warroom-muted mb-1">Billing Interval</label>
                      <select
                        value={formData.interval}
                        onChange={(e) => setFormData((p) => ({ ...p, interval: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      >
                        <option value="month">Monthly</option>
                        <option value="year">Yearly</option>
                        <option value="one_time">One-time</option>
                      </select>
                    </div>
                  </div>

                  {/* Features */}
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Features</label>
                    <div className="space-y-1.5 mb-2">
                      {formData.features.map((feat, i) => (
                        <div key={i} className="flex items-center gap-2 bg-warroom-bg/50 border border-warroom-border/50 rounded-lg px-3 py-1.5">
                          <Check size={12} className="text-green-400 shrink-0" />
                          <span className="text-sm text-warroom-text flex-1">{feat}</span>
                          <button
                            type="button"
                            onClick={() => removeFeature(i)}
                            className="text-warroom-muted hover:text-red-400 transition"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newFeature}
                        onChange={(e) => setNewFeature(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            addFeature();
                          }
                        }}
                        className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                        placeholder="Add a feature..."
                      />
                      <button
                        type="button"
                        onClick={addFeature}
                        className="px-3 py-1.5 bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-muted hover:text-warroom-text transition"
                      >
                        <Plus size={14} />
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Sort Order</label>
                    <input
                      type="number"
                      min="0"
                      value={formData.sort_order}
                      onChange={(e) => setFormData((p) => ({ ...p, sort_order: e.target.value }))}
                      className="w-24 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                    />
                  </div>
                </div>

                <div className="px-6 py-4 border-t border-warroom-border flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={closeModal}
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
                    {savingProduct ? "Saving..." : editingProduct ? "Update" : "Create"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
