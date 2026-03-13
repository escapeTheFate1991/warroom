"use client";

import { useState } from "react";
import { X, ArrowRight, Loader2 } from "lucide-react";
import { PipelineStage, Deal } from "./types";

// Required fields per target stage probability
const STAGE_GATES: Record<number, { field: string; label: string; type: string }[]> = {
  20: [
    { field: "contact_method", label: "Contact Method", type: "select" },
    { field: "contact_date", label: "Contact Date", type: "date" },
    { field: "assigned_rep", label: "Assigned Rep", type: "text" },
  ],
  40: [
    { field: "pain_points", label: "Pain Points", type: "textarea" },
    { field: "budget_range", label: "Budget Range", type: "text" },
  ],
  60: [
    { field: "meeting_date", label: "Meeting Date", type: "date" },
    { field: "attendees", label: "Attendees", type: "text" },
    { field: "meeting_notes", label: "Meeting Notes", type: "textarea" },
  ],
  80: [
    { field: "proposal_doc_url", label: "Proposal Document URL", type: "text" },
    { field: "negotiation_notes", label: "Negotiation Notes", type: "textarea" },
  ],
  100: [
    { field: "payment_terms", label: "Payment Terms", type: "text" },
  ],
  0: [
    { field: "lost_reason", label: "Lost Reason", type: "textarea" },
  ],
};

const CONTACT_METHODS = ["Phone", "Email", "LinkedIn", "In-Person", "Referral", "Other"];

interface StageGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  deal: Deal;
  fromStage: PipelineStage;
  toStage: PipelineStage;
  onAdvance: (data: Record<string, unknown>) => Promise<void>;
}

export default function StageGateModal({ isOpen, onClose, deal, fromStage, toStage, onAdvance }: StageGateModalProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [reasoning, setReasoning] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const isLostStage = toStage.probability === 0;
  const gateFields = STAGE_GATES[toStage.probability] || [];

  const handleSubmit = async () => {
    // For Lost stage, use lost_reason as the reasoning too
    const effectiveReasoning = isLostStage ? (formData["lost_reason"] || "") : reasoning;
    if (effectiveReasoning.length < 10) {
      setError(isLostStage ? "Lost reason must be at least 10 characters." : "Reasoning must be at least 10 characters.");
      return;
    }
    // Check all required gate fields
    for (const gf of gateFields) {
      if (!formData[gf.field]?.trim()) {
        setError(`"${gf.label}" is required.`);
        return;
      }
    }
    setError("");
    setSubmitting(true);
    try {
      await onAdvance({
        target_stage_id: toStage.id,
        reasoning: effectiveReasoning,
        ...formData,
      });
      // Reset
      setFormData({});
      setReasoning("");
    } catch (err: any) {
      setError(err?.message || "Failed to advance deal");
    } finally {
      setSubmitting(false);
    }
  };

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-warroom-surface border border-warroom-border rounded-xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-warroom-border">
          <div>
            <h2 className="text-base font-semibold text-warroom-text">Advancing: {deal.title}</h2>
            <div className="flex items-center gap-2 mt-1 text-xs text-warroom-muted">
              <span>{fromStage.name}</span>
              <ArrowRight size={12} />
              <span className="text-warroom-accent">{toStage.name}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-warroom-muted hover:text-warroom-text"><X size={18} /></button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {error && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">{error}</div>}

          {/* Dynamic gate fields */}
          {gateFields.map((gf) => (
            <div key={gf.field}>
              <label className="block text-xs font-medium text-warroom-muted mb-1">{gf.label} *</label>
              {gf.type === "textarea" ? (
                <textarea rows={3} value={formData[gf.field] || ""} onChange={(e) => updateField(gf.field, e.target.value)}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none" />
              ) : gf.type === "date" ? (
                <input type="date" value={formData[gf.field] || ""} onChange={(e) => updateField(gf.field, e.target.value)}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" style={{ colorScheme: "dark" }} />
              ) : gf.type === "select" && gf.field === "contact_method" ? (
                <select value={formData[gf.field] || ""} onChange={(e) => updateField(gf.field, e.target.value)}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" style={{ colorScheme: "dark" }}>
                  <option value="">Select method…</option>
                  {CONTACT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              ) : (
                <input type="text" value={formData[gf.field] || ""} onChange={(e) => updateField(gf.field, e.target.value)}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" />
              )}
            </div>
          ))}

          {/* Reasoning — required for non-Lost stages (Lost uses lost_reason as reasoning) */}
          {!isLostStage && (
            <div>
              <label className="block text-xs font-medium text-warroom-muted mb-1">Reasoning * <span className="font-normal">(min 10 chars)</span></label>
              <textarea rows={3} value={reasoning} onChange={(e) => setReasoning(e.target.value)} placeholder="Explain why this deal is ready to advance…"
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none" />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-5 border-t border-warroom-border">
          <button onClick={onClose} className="px-4 py-2 text-sm text-warroom-muted hover:text-warroom-text transition">Cancel</button>
          <button onClick={handleSubmit} disabled={submitting}
            className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition flex items-center gap-2 disabled:opacity-50">
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
            {isLostStage ? "Mark as Lost" : "Advance Deal"}
          </button>
        </div>
      </div>
    </div>
  );
}

