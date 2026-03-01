"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Mail,
  Plus,
  Send,
  Pause,
  Play,
  Trash2,
  Edit,
  X,
  Calendar,
  Target,
  BarChart3,
  Clock,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Campaign {
  id: number;
  name: string;
  subject: string | null;
  status: boolean;
  type: string | null;
  mail_to: string | null;
  spooling: string | null;
  template_id: number | null;
  event_id: number | null;
  created_at: string;
  updated_at: string;
}

interface CampaignType {
  value: string;
  label: string;
}

export default function CampaignsPanel() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [types, setTypes] = useState<CampaignType[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Campaign | null>(null);

  // Form
  const [formName, setFormName] = useState("");
  const [formSubject, setFormSubject] = useState("");
  const [formType, setFormType] = useState("");
  const [formMailTo, setFormMailTo] = useState("");

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/crm/campaigns`);
      if (res.ok) setCampaigns(await res.json());
    } catch {}
    setLoading(false);
  }, []);

  const loadTypes = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/crm/campaign-types`);
      if (res.ok) {
        const data = await res.json();
        setTypes(data.types || []);
      }
    } catch {}
  }, []);

  useEffect(() => {
    loadCampaigns();
    loadTypes();
  }, [loadCampaigns, loadTypes]);

  function resetForm() {
    setFormName("");
    setFormSubject("");
    setFormType("");
    setFormMailTo("");
    setEditing(null);
    setShowForm(false);
  }

  function openEdit(c: Campaign) {
    setEditing(c);
    setFormName(c.name);
    setFormSubject(c.subject || "");
    setFormType(c.type || "");
    setFormMailTo(c.mail_to || "");
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim()) return;

    const body = {
      name: formName,
      subject: formSubject || null,
      type: formType || null,
      mail_to: formMailTo || null,
    };

    try {
      const url = editing
        ? `${API}/api/crm/campaigns/${editing.id}`
        : `${API}/api/crm/campaigns`;
      const res = await fetch(url, {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        resetForm();
        loadCampaigns();
      }
    } catch {}
  }

  async function deleteCampaign(id: number) {
    if (!confirm("Delete this campaign?")) return;
    try {
      await fetch(`${API}/api/crm/campaigns/${id}`, { method: "DELETE" });
      loadCampaigns();
    } catch {}
  }

  async function sendCampaign(id: number) {
    if (!confirm("Send this campaign now?")) return;
    try {
      await fetch(`${API}/api/crm/campaigns/${id}/send`, { method: "POST" });
      loadCampaigns();
    } catch {}
  }

  const activeCampaigns = campaigns.filter((c) => c.status);
  const draftCampaigns = campaigns.filter((c) => !c.status);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Mail size={16} />
          Campaigns
        </h2>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 text-white rounded-lg text-xs transition-colors"
        >
          <Plus size={14} />
          New Campaign
        </button>
      </div>

      {/* Stats bar */}
      <div className="px-6 py-3 border-b border-warroom-border flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400" />
          <span className="text-xs text-warroom-muted">{activeCampaigns.length} Active</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-gray-400" />
          <span className="text-xs text-warroom-muted">{draftCampaigns.length} Draft</span>
        </div>
        <span className="text-xs text-warroom-muted ml-auto">{campaigns.length} total</span>
      </div>

      {/* Form */}
      {showForm && (
        <div className="px-6 py-4 border-b border-warroom-border bg-warroom-surface/50">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-warroom-text">
                {editing ? "Edit Campaign" : "New Campaign"}
              </h3>
              <button type="button" onClick={resetForm} className="text-warroom-muted hover:text-warroom-text">
                <X size={14} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Campaign name *"
                required
                className="col-span-2 px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <input
                type="text"
                value={formSubject}
                onChange={(e) => setFormSubject(e.target.value)}
                placeholder="Email subject line"
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text"
              >
                <option value="">Select type</option>
                {types.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
                <option value="newsletter">Newsletter</option>
                <option value="promotional">Promotional</option>
                <option value="drip">Drip</option>
                <option value="announcement">Announcement</option>
              </select>
              <input
                type="text"
                value={formMailTo}
                onChange={(e) => setFormMailTo(e.target.value)}
                placeholder="Recipients (email list or segment)"
                className="col-span-2 px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={resetForm} className="px-3 py-1.5 text-xs text-warroom-muted">
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 text-xs bg-warroom-accent text-white rounded-lg">
                {editing ? "Update" : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Campaign List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-warroom-accent border-t-transparent" />
          </div>
        ) : campaigns.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-warroom-muted">
            <Mail size={32} className="mb-2 opacity-20" />
            <p className="text-xs">No campaigns yet. Create your first one!</p>
          </div>
        ) : (
          <div className="divide-y divide-warroom-border">
            {campaigns.map((campaign) => (
              <div
                key={campaign.id}
                className="px-6 py-3 hover:bg-warroom-surface/50 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                    campaign.status ? "bg-green-400/10 text-green-400" : "bg-gray-400/10 text-gray-400"
                  }`}>
                    {campaign.status ? <Play size={16} /> : <Pause size={16} />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-warroom-text">{campaign.name}</span>
                      {campaign.type && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-warroom-surface text-warroom-muted border border-warroom-border">
                          {campaign.type}
                        </span>
                      )}
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        campaign.status
                          ? "bg-green-500/10 text-green-400"
                          : "bg-gray-500/10 text-gray-400"
                      }`}>
                        {campaign.status ? "Active" : "Draft"}
                      </span>
                    </div>
                    {campaign.subject && (
                      <p className="text-xs text-warroom-muted mt-0.5">Subject: {campaign.subject}</p>
                    )}
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-[10px] text-warroom-muted flex items-center gap-1">
                        <Clock size={10} />
                        {new Date(campaign.created_at).toLocaleDateString()}
                      </span>
                      {campaign.mail_to && (
                        <span className="text-[10px] text-warroom-muted flex items-center gap-1">
                          <Target size={10} />
                          {campaign.mail_to}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {!campaign.status && (
                      <button
                        onClick={() => sendCampaign(campaign.id)}
                        className="p-1.5 text-warroom-muted hover:text-green-400 transition-colors"
                        title="Send"
                      >
                        <Send size={13} />
                      </button>
                    )}
                    <button
                      onClick={() => openEdit(campaign)}
                      className="p-1.5 text-warroom-muted hover:text-warroom-accent transition-colors"
                    >
                      <Edit size={13} />
                    </button>
                    <button
                      onClick={() => deleteCampaign(campaign.id)}
                      className="p-1.5 text-warroom-muted hover:text-red-400 transition-colors"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
