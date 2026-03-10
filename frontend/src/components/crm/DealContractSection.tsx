"use client";

import { useState, useEffect } from "react";
import {
  FileSignature, Send, Loader2, CheckCircle, ExternalLink,
  ChevronDown, AlertCircle,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface Product {
  id: number;
  name: string;
  price_cents: number;
}

interface DealContract {
  id: number;
  contract_number: string;
  client_name: string;
  client_email: string;
  client_company: string | null;
  plan_name: string;
  monthly_price: number;
  status: string;
  deal_stage: string | null;
  created_at: string;
}

interface DealContractSectionProps {
  dealId: number;
  personName: string | null;
  personEmail: string | null;
  organizationName: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  sent: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  viewed: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  signed: "bg-green-500/20 text-green-400 border-green-500/30",
  active: "bg-green-500/20 text-green-400 border-green-500/30",
  cancelled: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function DealContractSection({
  dealId, personName, personEmail, organizationName,
}: DealContractSectionProps) {
  const [contracts, setContracts] = useState<DealContract[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [selectedProduct, setSelectedProduct] = useState<number | null>(null);
  const [termMonths, setTermMonths] = useState(12);

  // Fetch existing contracts for this deal
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [contractsRes, productsRes] = await Promise.all([
          authFetch(`${API}/api/contracts/by-deal/${dealId}`),
          authFetch(`${API}/api/stripe/products`),
        ]);
        if (contractsRes.ok) setContracts(await contractsRes.json());
        if (productsRes.ok) {
          const prods = await productsRes.json();
          setProducts(prods);
          if (prods.length > 0 && !selectedProduct) setSelectedProduct(prods[0].id);
        }
      } catch { /* ignore */ }
      finally { setLoading(false); }
    };
    fetchData();
  }, [dealId]);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await authFetch(`${API}/api/contracts/from-deal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          deal_id: dealId,
          product_id: selectedProduct,
          term_months: termMonths,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to create contract" }));
        throw new Error(err.detail || "Failed to create contract");
      }
      const created = await res.json();
      setSuccess(`Contract ${created.contract_number} created`);
      setShowForm(false);
      // Refresh contracts list
      const refreshRes = await authFetch(`${API}/api/contracts/by-deal/${dealId}`);
      if (refreshRes.ok) setContracts(await refreshRes.json());
    } catch (e: any) {
      setError(e.message || "Failed to create contract");
    } finally {
      setCreating(false);
    }
  };

  const handleSend = async (contractId: number) => {
    setSending(contractId);
    setError(null);
    try {
      const res = await authFetch(`${API}/api/contracts/${contractId}/send`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to send" }));
        throw new Error(err.detail || "Failed to send contract");
      }
      setSuccess("Contract sent to client");
      // Refresh
      const refreshRes = await authFetch(`${API}/api/contracts/by-deal/${dealId}`);
      if (refreshRes.ok) setContracts(await refreshRes.json());
    } catch (e: any) {
      setError(e.message || "Failed to send contract");
    } finally {
      setSending(null);
    }
  };

  const fmtPrice = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(n);

  if (loading) {
    return (
      <div className="p-5 border-b border-warroom-border">
        <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-2">Contract</h3>
        <div className="flex items-center justify-center py-4 text-warroom-muted text-sm">
          <Loader2 size={14} className="animate-spin mr-2" />Loading…
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 border-b border-warroom-border">
      <h3 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-3">Contract</h3>

      {/* Status messages */}
      {error && (
        <div className="mb-3 p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
          <AlertCircle size={12} />{error}
        </div>
      )}
      {success && (
        <div className="mb-3 p-2 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-xs flex items-center gap-2">
          <CheckCircle size={12} />{success}
        </div>
      )}

      {/* Existing contracts */}
      {contracts.length > 0 && (
        <div className="space-y-2 mb-3">
          {contracts.map((c) => (
            <div key={c.id} className="p-3 rounded-lg bg-warroom-bg border border-warroom-border">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-warroom-text">{c.contract_number}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${STATUS_STYLES[c.status] || STATUS_STYLES.draft}`}>
                  {c.status}
                </span>
              </div>
              <div className="text-xs text-warroom-muted">
                {c.plan_name} · {fmtPrice(c.monthly_price)}/mo
              </div>
              <div className="flex items-center gap-2 mt-2">
                {c.status === "draft" && (
                  <button
                    onClick={() => handleSend(c.id)}
                    disabled={sending === c.id || !c.client_email}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/30 transition disabled:opacity-50"
                  >
                    {sending === c.id ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
                    Send to Client
                  </button>
                )}
                <a
                  href={`/contracts?id=${c.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-warroom-muted hover:text-warroom-text transition"
                >
                  <ExternalLink size={11} />View
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create contract form */}
      {showForm ? (
        <div className="p-3 rounded-lg bg-warroom-bg border border-warroom-border space-y-3">
          {/* Pre-filled info (read-only) */}
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-warroom-muted">Client</span>
              <span className="text-warroom-text">{personName || "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-warroom-muted">Email</span>
              <span className="text-warroom-text">{personEmail || "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-warroom-muted">Company</span>
              <span className="text-warroom-text">{organizationName || "—"}</span>
            </div>
          </div>

          <div className="border-t border-warroom-border pt-2 space-y-2">
            {/* Product */}
            <div>
              <label className="block text-[11px] text-warroom-muted mb-1">Product</label>
              <div className="relative">
                <select
                  value={selectedProduct ?? ""}
                  onChange={(e) => setSelectedProduct(Number(e.target.value))}
                  className="w-full bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text appearance-none pr-8"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {fmtPrice(p.price_cents / 100)}/mo
                    </option>
                  ))}
                </select>
                <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" />
              </div>
            </div>

            {/* Term */}
            <div>
              <label className="block text-[11px] text-warroom-muted mb-1">Term (months)</label>
              <input
                type="number"
                min={1}
                max={60}
                value={termMonths}
                onChange={(e) => setTermMonths(Number(e.target.value))}
                className="w-full bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={handleCreate}
              disabled={creating}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg transition disabled:opacity-50"
            >
              {creating ? <Loader2 size={12} className="animate-spin" /> : <FileSignature size={12} />}
              Create Contract
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-2 text-xs text-warroom-muted hover:text-warroom-text transition"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium bg-warroom-bg border border-warroom-border hover:bg-warroom-border/30 rounded-lg text-warroom-muted hover:text-warroom-text transition"
        >
          <FileSignature size={14} />
          Create Contract
        </button>
      )}
    </div>
  );
}
