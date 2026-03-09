"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bot,
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
import EntityAssignmentControl from "@/components/agents/EntityAssignmentControl";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";

type MarketingChannel = "email" | "sms" | "voice" | "social";

interface ChannelOption {
  value: MarketingChannel;
  label: string;
}

function getCampaignContentDefaults(channel: MarketingChannel, subject: string | null): Record<string, any> {
  if (channel === "sms") return { message: null, stages: [] as unknown[] };
  if (channel === "voice") return { script: null, stages: [] as unknown[] };
  if (channel === "social") return { posts: [] as unknown[], stages: [] as unknown[] };
  return { subject, body: null, stages: [] as unknown[] };
}

function getCampaignConfigDefaults(channel: MarketingChannel): Record<string, any> {
  if (channel === "sms") return { sender_number: null, track_clicks: true };
  if (channel === "voice") return { caller_id: null, voice_profile: null };
  if (channel === "social") return { platforms: [] as unknown[], profile_id: null };
  return { sender_profile: null, reply_to: null, track_opens: true };
}

function getSubjectPlaceholder(channel: MarketingChannel) {
  if (channel === "email") return "Email subject line";
  if (channel === "social") return "Campaign headline or theme";
  if (channel === "voice") return "Call topic or script title";
  return "Optional message summary";
}

function getAudiencePlaceholder(channel: MarketingChannel) {
  if (channel === "sms") return "Recipients (phone list or SMS segment)";
  if (channel === "voice") return "Recipients (call list or voice segment)";
  if (channel === "social") return "Audience segment or social target";
  return "Recipients (email list or segment)";
}

function getCampaignAssignmentHint(channel: MarketingChannel) {
  if (channel === "sms") return "Assign pooled agents to own SMS setup, targeting, and later messaging skills.";
  if (channel === "voice") return "Assign pooled agents to own voice setup, scripting, and later call orchestration hooks.";
  if (channel === "social") return "Assign pooled agents to own social setup, platform routing, and later publishing skills.";
  return "Assign pooled agents to own email setup, sequencing, and later marketing orchestration hooks.";
}

function summarizeAssignedAgents(assignments?: AgentAssignmentSummary[]) {
  if (!assignments || assignments.length === 0) return "No AI owners assigned";
  const names = assignments
    .map((assignment) => assignment.agent_name || assignment.agent_id)
    .slice(0, 2)
    .join(", ");
  const extra = assignments.length > 2 ? ` +${assignments.length - 2} more` : "";
  return `AI owners: ${names}${extra}`;
}

interface Campaign {
  id: number;
  name: string;
  channel: MarketingChannel;
  subject: string | null;
  status: boolean;
  type: string | null;
  use_case: string | null;
  mail_to: string | null;
  spooling: string | null;
  audience?: Record<string, any> | null;
  schedule?: Record<string, any> | null;
  content?: Record<string, any> | null;
  channel_config?: Record<string, any> | null;
  template_id: number | null;
  event_id: number | null;
  created_at: string;
  updated_at: string;
  agent_assignments?: AgentAssignmentSummary[];
}

interface CampaignType {
  value: string;
  label: string;
}

export default function CampaignsPanel() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [types, setTypes] = useState<CampaignType[]>([]);
  const [channels, setChannels] = useState<ChannelOption[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Campaign | null>(null);

  // Form
  const [formName, setFormName] = useState("");
  const [formChannel, setFormChannel] = useState<MarketingChannel>("email");
  const [formSubject, setFormSubject] = useState("");
  const [formType, setFormType] = useState("");
  const [formUseCase, setFormUseCase] = useState("");
  const [formMailTo, setFormMailTo] = useState("");

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/crm/campaigns`);
      if (res.ok) setCampaigns(await res.json());
    } catch {}
    setLoading(false);
  }, []);

  const loadTypes = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/crm/campaign-types`);
      if (res.ok) {
        const data = await res.json();
        setTypes(data.types || []);
        setChannels(data.channels || []);
      }
    } catch {}
  }, []);

  useEffect(() => {
    loadCampaigns();
    loadTypes();
  }, [loadCampaigns, loadTypes]);

  const syncCampaignAssignments = useCallback((campaignId: number, assignments: AgentAssignmentSummary[]) => {
    setCampaigns((current) => current.map((campaign) => (
      campaign.id === campaignId ? { ...campaign, agent_assignments: assignments } : campaign
    )));
    setEditing((current) => (
      current && current.id === campaignId ? { ...current, agent_assignments: assignments } : current
    ));
  }, []);

  function resetForm() {
    setFormName("");
    setFormChannel("email");
    setFormSubject("");
    setFormType("");
    setFormUseCase("");
    setFormMailTo("");
    setEditing(null);
    setShowForm(false);
  }

  function openEdit(c: Campaign) {
    setEditing(c);
    setFormName(c.name);
    setFormChannel(c.channel || "email");
    setFormSubject(c.subject || "");
    setFormType(c.type || "");
    setFormUseCase(c.use_case || "");
    setFormMailTo(c.mail_to || c.audience?.segment || "");
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim()) return;

    const content = {
      ...getCampaignContentDefaults(formChannel, formSubject || null),
      ...(editing?.channel === formChannel ? editing.content || {} : {}),
    };
    const channelConfig = {
      ...getCampaignConfigDefaults(formChannel),
      ...(editing?.channel === formChannel ? editing.channel_config || {} : {}),
    };
    const audience = {
      recipients: editing?.audience?.recipients || [],
      ...(editing?.audience || {}),
      segment: formMailTo || null,
    };
    const schedule = {
      mode: "manual",
      stages: editing?.schedule?.stages || [],
      ...(editing?.schedule || {}),
    };

    if (formChannel === "email") {
      content.subject = formSubject || null;
    }

    const body = {
      name: formName,
      channel: formChannel,
      subject: formSubject || null,
      type: formType || null,
      use_case: formUseCase || null,
      mail_to: formMailTo || null,
      audience,
      schedule,
      content,
      channel_config: channelConfig,
    };

    try {
      const url = editing
        ? `${API}/api/crm/campaigns/${editing.id}`
        : `${API}/api/crm/campaigns`;
      const res = await authFetch(url, {
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
      await authFetch(`${API}/api/crm/campaigns/${id}`, { method: "DELETE" });
      loadCampaigns();
    } catch {}
  }

  async function sendCampaign(id: number) {
    if (!confirm("Send this campaign now?")) return;
    try {
      await authFetch(`${API}/api/crm/campaigns/${id}/send`, { method: "POST" });
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
              <select
                value={formChannel}
                onChange={(e) => setFormChannel(e.target.value as MarketingChannel)}
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text"
              >
                {channels.map((channel) => (
                  <option key={channel.value} value={channel.value}>{channel.label}</option>
                ))}
                {channels.length === 0 && (
                  <>
                    <option value="email">Email</option>
                    <option value="sms">SMS</option>
                    <option value="voice">Voice</option>
                    <option value="social">Social</option>
                  </>
                )}
              </select>
              <input
                type="text"
                value={formSubject}
                onChange={(e) => setFormSubject(e.target.value)}
                placeholder={getSubjectPlaceholder(formChannel)}
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
                value={formUseCase}
                onChange={(e) => setFormUseCase(e.target.value)}
                placeholder="Reusable use case (optional)"
                className="px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <input
                type="text"
                value={formMailTo}
                onChange={(e) => setFormMailTo(e.target.value)}
                placeholder={getAudiencePlaceholder(formChannel)}
                className="col-span-2 px-3 py-1.5 text-xs bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
            </div>
            <div className="rounded-xl border border-warroom-border bg-warroom-bg/60 p-3">
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-warroom-muted">
                <Bot size={13} className="text-warroom-accent" />
                <span>AI orchestration</span>
              </div>
              <p className="mt-1 text-xs text-warroom-muted">{getCampaignAssignmentHint(formChannel)}</p>
              {editing ? (
                <EntityAssignmentControl
                  className="mt-3 border-0 bg-transparent p-0"
                  entityType="marketing_campaign"
                  entityId={editing.id}
                  emptyLabel={`No AI owners assigned to this ${formChannel} campaign yet.`}
                  initialAssignments={editing.agent_assignments || []}
                  onAssignmentsChange={(assignments) => syncCampaignAssignments(editing.id, assignments)}
                  title={`Own ${formChannel} campaign: ${formName || editing.name}`}
                />
              ) : (
                <p className="mt-2 text-[11px] text-warroom-muted">
                  Save this campaign first to assign pooled agents for {formChannel} orchestration.
                </p>
              )}
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
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-warroom-accent/10 text-warroom-accent border border-warroom-accent/20 uppercase">
                        {campaign.channel}
                      </span>
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
                    {campaign.use_case && (
                      <p className="text-[10px] text-warroom-muted mt-0.5">Use case: {campaign.use_case}</p>
                    )}
                    <p className="text-[10px] text-warroom-muted mt-0.5 flex items-center gap-1">
                      <Bot size={10} />
                      {summarizeAssignedAgents(campaign.agent_assignments)}
                    </p>
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
