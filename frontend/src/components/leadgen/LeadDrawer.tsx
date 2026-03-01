"use client";

import { useState, useEffect } from "react";
import { 
  X, 
  Phone, 
  Globe, 
  MapPin, 
  Mail, 
  Star, 
  Facebook, 
  Instagram, 
  Linkedin, 
  Twitter,
  FileText,
  MessageSquare,
  Phone as PhoneIcon,
  StickyNote,
  AlertCircle,
  CheckCircle,
  Copy,
  Save,
  Loader2,
  UserPlus
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

export interface LeadFull {
  id: number;
  business_name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  phone: string | null;
  website: string | null;
  google_rating: number | null;
  google_reviews_count: number;
  business_category: string | null;
  emails: string[];
  website_phones?: string[];
  has_website: boolean;
  website_audit_score: number | null;
  website_audit_grade: string | null;
  website_audit_summary: string | null;
  website_audit_top_fixes: string[];
  audit_lite_flags: string[];
  lead_score: number;
  lead_tier: string;
  enrichment_status: string;
  facebook_url: string | null;
  instagram_url: string | null;
  linkedin_url: string | null;
  twitter_url: string | null;
  outreach_status: string;
  contacted_by: string | null;
  contacted_at: string | null;
  contact_outcome: string | null;
  contact_notes: string | null;
  contact_history: any[];
  contact_who_answered: string | null;
  contact_owner_name: string | null;
  contact_economic_buyer: string | null;
  contact_champion: string | null;
  notes: string | null;
  tags: string[];
  website_platform: string | null;
}

interface LeadDrawerProps {
  lead: LeadFull | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdate?: (lead: LeadFull) => void;
}

const TIER_COLORS: Record<string, string> = {
  hot: "bg-red-500/20 text-red-400 border-red-500/30",
  warm: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  cold: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  unscored: "bg-warroom-border/20 text-warroom-muted border-warroom-border",
};

const STATUS_COLORS: Record<string, string> = {
  none: "bg-warroom-border/20 text-warroom-muted",
  contacted: "bg-blue-500/20 text-blue-400",
  in_progress: "bg-yellow-500/20 text-yellow-400",
  won: "bg-green-500/20 text-green-400",
  lost: "bg-red-500/20 text-red-400",
};

const CONTACT_OUTCOMES = [
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
  { value: "follow_up", label: "Follow Up" },
  { value: "no_answer", label: "No Answer" },
  { value: "callback", label: "Callback" },
];

function AssignButton({ lead, onAssigned }: { lead: LeadFull; onAssigned: (dealId: number) => void }) {
  const [showForm, setShowForm] = useState(false);
  const [assignTo, setAssignTo] = useState("");
  const [users, setUsers] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<{ dealId: number; assignee: string } | null>(null);

  useEffect(() => {
    fetch(`${API}/api/crm/users`).then(r => r.json()).then(setUsers).catch(() => {});
  }, []);

  const handleAssign = async () => {
    if (!assignTo) return;
    setLoading(true);
    try {
      // Convert lead to CRM deal
      const res = await fetch(`${API}/api/crm/deals/convert-from-lead`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          leadgen_lead_id: lead.id,
          title: lead.business_name,
          assigned_to: assignTo,
          business_name: lead.business_name,
          business_category: lead.business_category,
          phone: lead.phone,
          website: lead.website,
          emails: lead.emails,
          address: lead.address,
          city: lead.city,
          state: lead.state,
        }),
      });
      if (res.ok) {
        const deal = await res.json();
        // Mark lead as in_progress
        await fetch(`${API}/api/leadgen/leads/${lead.id}/contact`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contacted_by: assignTo,
            outcome: "follow_up",
            notes: `Assigned to ${assignTo} — deal created in CRM pipeline`,
          }),
        });
        onAssigned(deal.id);
        setSuccess({ dealId: deal.id, assignee: assignTo });
        setShowForm(false);
      }
    } catch (err) {
      console.error("Failed to assign:", err);
    } finally {
      setLoading(false);
    }
  };

  if (lead.outreach_status === "won") return null;

  return (
    <div>
      {success ? (
        <div className="space-y-3 p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle size={16} />
            <span className="text-sm font-medium">Successfully assigned to pipeline!</span>
          </div>
          <div className="text-xs text-warroom-muted">
            {lead.business_name} has been assigned to {success.assignee} and added to the CRM pipeline.
          </div>
          <a
            href="/?tab=crm-deals"
            className="inline-flex items-center gap-2 text-xs text-warroom-accent hover:text-warroom-accent/80 font-medium"
          >
            View in CRM Deals →
          </a>
        </div>
      ) : !showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition text-sm font-medium"
        >
          <UserPlus size={16} />
          Assign to Pipeline
        </button>
      ) : (
        <div className="space-y-3">
          <div>
            <label className="text-xs text-warroom-muted block mb-1">Assign to</label>
            <select
              value={assignTo}
              onChange={(e) => setAssignTo(e.target.value)}
              className="w-full bg-[#0d1117] border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text"
            >
              <option value="">Select team member...</option>
              {users.map((u) => (
                <option key={u.id} value={u.name}>{u.name}</option>
              ))}
              <option value="custom">Type a name...</option>
            </select>
          </div>
          {assignTo === "custom" && (
            <input
              type="text"
              placeholder="Enter name..."
              onChange={(e) => setAssignTo(e.target.value)}
              className="w-full bg-[#0d1117] border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text"
            />
          )}
          <div className="flex gap-2">
            <button
              onClick={handleAssign}
              disabled={!assignTo || loading}
              className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
            >
              {loading ? <Loader2 size={14} className="animate-spin mx-auto" /> : "Assign & Start Pipeline"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-warroom-border/30 hover:bg-warroom-border/50 text-warroom-text rounded-lg text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function LeadDrawer({ lead, isOpen, onClose, onUpdate }: LeadDrawerProps) {
  const [activeTab, setActiveTab] = useState<"audit" | "contact" | "scripts" | "notes">("contact");
  const [contactForm, setContactForm] = useState({
    contacted_by: "",
    who_answered: "",
    owner_name: "",
    economic_buyer: "",
    champion: "",
    outcome: "",
    notes: "",
  });
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [settings, setSettings] = useState<Record<string, string>>({});

  // Load platform settings for script generation
  useEffect(() => {
    fetch(`${API}/api/settings?category=general`)
      .then(r => r.ok ? r.json() : [])
      .then((items: any[]) => {
        const map: Record<string, string> = {};
        items.forEach((s: any) => { map[s.key] = s.value || ""; });
        setSettings(map);
      })
      .catch(() => {});
  }, []);

  // Reset form when lead changes
  useEffect(() => {
    if (lead) {
      setContactForm({
        contacted_by: lead.contacted_by || "",
        who_answered: lead.contact_who_answered || "",
        owner_name: lead.contact_owner_name || "",
        economic_buyer: lead.contact_economic_buyer || "",
        champion: lead.contact_champion || "",
        outcome: lead.contact_outcome || "",
        notes: lead.contact_notes || "",
      });
      setNotes(lead.notes || "");
    }
  }, [lead]);

  if (!isOpen || !lead) return null;

  const handleContactSubmit = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API}/api/leadgen/leads/${lead.id}/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(contactForm),
      });
      if (response.ok) {
        const updatedLead = await response.json();
        onUpdate?.(updatedLead);
      }
    } catch (error) {
      console.error("Failed to save contact:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleNotesSubmit = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API}/api/leadgen/leads/${lead.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes }),
      });
      if (response.ok) {
        const updatedLead = await response.json();
        onUpdate?.(updatedLead);
      }
    } catch (error) {
      console.error("Failed to save notes:", error);
    } finally {
      setSaving(false);
    }
  };

  const triggerAudit = async () => {
    setAuditLoading(true);
    try {
      const response = await fetch(`${API}/api/leadgen/leads/${lead.id}/audit`, {
        method: "POST",
      });
      if (response.ok) {
        // Poll for results
        const checkAudit = async () => {
          const auditResponse = await fetch(`${API}/api/leadgen/leads/${lead.id}/audit`);
          if (auditResponse.ok) {
            const updatedLead = await auditResponse.json();
            onUpdate?.(updatedLead);
          }
        };
        setTimeout(checkAudit, 2000);
      }
    } catch (error) {
      console.error("Failed to trigger audit:", error);
    } finally {
      setAuditLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  const companyName = settings.company_name || "yieldlabs";
  const userName = settings.your_name || contactForm.contacted_by || "";
  const contactName = lead.contact_owner_name || lead.contact_who_answered || "";

  const generateColdCallScript = () => {
    const greeting = contactName ? `May I speak with ${contactName}?` : "Who am I speaking with?";
    const websiteStatus = lead.has_website ? "I took a look at your website" : "I noticed you don't currently have a website";
    const auditIssues = lead.audit_lite_flags.length > 0 
      ? ` and found some areas that could boost your online presence: ${lead.audit_lite_flags.slice(0, 2).join(", ")}`
      : "";
    
    return `Hi, this is ${userName || "[Your Name]"} from ${companyName}. I'm calling about ${lead.business_name}. ${greeting}

${websiteStatus}${auditIssues}. I specialize in helping ${lead.business_category || "businesses like yours"} increase their online visibility and attract more customers.

Could I take just 2 minutes to show you how we've helped similar businesses in ${lead.city || "your area"} grow their customer base by 30-50%?

When would be a good time for a quick 15-minute conversation this week?`;
  };

  const generateColdEmail = () => {
    const recipientEmail = lead.emails?.[0] || "";
    const recipientName = contactName || "there";
    
    return `To: ${recipientEmail}
Subject: Quick question about ${lead.business_name}'s online presence

Hi ${recipientName},

I was looking at ${lead.business_name} online and ${lead.has_website ? "visited your website" : "noticed you might not have a website yet"}.

${lead.audit_lite_flags.length > 0 ? `I ran a quick analysis and spotted a few quick wins that could help you attract more customers online.` : "I help businesses like yours increase their online visibility."}

Would you be interested in a free 5-minute consultation to see how we could help ${lead.business_name} grow?

I've helped other ${lead.business_category || "local businesses"} in ${lead.city || "the area"} increase their customer base by 30-50%.

Best regards,
${userName || "[Your Name]"}
${companyName}
${lead.phone || ""}`;
  };

  const socialLinks = [
    { url: lead.facebook_url, icon: Facebook, label: "Facebook" },
    { url: lead.instagram_url, icon: Instagram, label: "Instagram" },
    { url: lead.linkedin_url, icon: Linkedin, label: "LinkedIn" },
    { url: lead.twitter_url, icon: Twitter, label: "Twitter" },
  ].filter(link => link.url);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Drawer */}
      <div className="absolute right-0 top-0 h-full w-[600px] bg-warroom-surface border-l border-warroom-border shadow-2xl">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex-shrink-0 p-6 border-b border-warroom-border">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <h2 className="text-xl font-semibold text-warroom-text mb-2">
                      {lead.business_name}
                    </h2>
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`text-xs font-medium px-2 py-1 rounded-full border ${TIER_COLORS[lead.lead_tier] || TIER_COLORS.unscored}`}>
                        {lead.lead_tier}
                      </span>
                      <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[lead.outreach_status] || STATUS_COLORS.none}`}>
                        {lead.outreach_status.replace("_", " ").toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-warroom-muted hover:text-warroom-text transition p-2"
                  >
                    <X size={20} />
                  </button>
                </div>

                {/* Contact Info */}
                <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                  {lead.address && (
                    <div className="flex items-center gap-2 text-warroom-muted">
                      <MapPin size={14} />
                      <span>{[lead.address, lead.city, lead.state].filter(Boolean).join(", ")}</span>
                    </div>
                  )}
                  {lead.phone && (
                    <div className="flex items-center gap-2 text-warroom-muted">
                      <Phone size={14} />
                      <span>{lead.phone}</span>
                    </div>
                  )}
                  {lead.website && (
                    <div className="flex items-center gap-2">
                      <Globe size={14} className="text-warroom-muted" />
                      <a 
                        href={lead.website} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-warroom-accent hover:underline"
                      >
                        {(() => { try { return new URL(lead.website).hostname; } catch { return lead.website; } })()}
                      </a>
                    </div>
                  )}
                  {lead.emails[0] && (
                    <div className="flex items-center gap-2 text-warroom-accent">
                      <Mail size={14} />
                      <span>{lead.emails[0]}</span>
                    </div>
                  )}
                </div>

                {/* Rating & Social */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {lead.google_rating && (
                      <div className="flex items-center gap-1 text-sm text-warroom-muted">
                        <Star size={14} className="text-yellow-400" />
                        <span>{lead.google_rating} ({lead.google_reviews_count} reviews)</span>
                      </div>
                    )}
                    
                    {socialLinks.length > 0 && (
                      <div className="flex items-center gap-2">
                        {socialLinks.map(({ url, icon: Icon, label }) => (
                          <a
                            key={label}
                            href={url!}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-warroom-muted hover:text-warroom-accent transition"
                            title={label}
                          >
                            <Icon size={16} />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Lead Score */}
                  <div className="text-right">
                    <div className="text-sm text-warroom-muted">Lead Score</div>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-warroom-border rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-warroom-accent transition-all"
                          style={{ width: `${lead.lead_score}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-warroom-text">{lead.lead_score}</span>
                    </div>
                  </div>
                </div>

                {/* Assign to Pipeline */}
                <div className="mt-4 pt-4 border-t border-warroom-border">
                  <AssignButton lead={lead} onAssigned={(dealId) => {
                    // Update lead status to in_progress (shows yellow border)
                    const updatedLead = { ...lead, outreach_status: "in_progress" };
                    onUpdate?.(updatedLead);
                  }} />
                </div>

                {lead.contacted_by && lead.contacted_at && (
                  <div className="mt-3 p-2 bg-warroom-bg rounded-lg">
                    <div className="text-xs text-warroom-muted">
                      Contacted by {lead.contacted_by} on {new Date(lead.contacted_at).toLocaleDateString()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex-shrink-0 border-b border-warroom-border">
            <div className="flex">
              {[
                { id: "audit", label: "Audit", icon: FileText },
                { id: "contact", label: "Contact", icon: PhoneIcon },
                { id: "scripts", label: "Scripts", icon: MessageSquare },
                { id: "notes", label: "Notes", icon: StickyNote },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition border-b-2 ${
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
            {activeTab === "audit" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-warroom-text">Website Audit</h3>
                  <button
                    onClick={triggerAudit}
                    disabled={auditLoading}
                    className="px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition flex items-center gap-1"
                  >
                    {auditLoading ? <Loader2 size={14} className="animate-spin" /> : <AlertCircle size={14} />}
                    {auditLoading ? "Running..." : "Trigger Audit"}
                  </button>
                </div>

                {lead.audit_lite_flags.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">Issues Found</h4>
                    <div className="flex flex-wrap gap-2">
                      {lead.audit_lite_flags.map((flag) => (
                        <span
                          key={flag}
                          className="text-xs px-2 py-1 bg-orange-500/20 text-orange-400 rounded-full"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {lead.website_audit_score && (
                  <div>
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">Audit Score</h4>
                    <div className="p-3 bg-warroom-bg rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-warroom-text">Score: {lead.website_audit_score}/100</span>
                        <span className="text-sm font-medium text-warroom-accent">{lead.website_audit_grade}</span>
                      </div>
                    </div>
                  </div>
                )}

                {lead.website_audit_summary && (
                  <div>
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">Summary</h4>
                    <div className="p-3 bg-warroom-bg rounded-lg text-sm text-warroom-text">
                      {lead.website_audit_summary}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "contact" && (
              <div className="space-y-4">
                {/* Enriched Data from Website Scrape */}
                {(lead.emails.length > 0 || (lead.website_phones && lead.website_phones.length > 0)) && (
                  <div className="p-4 bg-warroom-accent/5 border border-warroom-accent/20 rounded-lg space-y-3">
                    <h4 className="text-xs font-semibold text-warroom-accent flex items-center gap-2">
                      <CheckCircle size={14} />
                      Enriched Contact Data
                    </h4>
                    {lead.emails.length > 0 && (
                      <div>
                        <label className="text-[10px] text-warroom-muted uppercase tracking-wide">Emails Found</label>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {lead.emails.map((email, i) => (
                            <button
                              key={i}
                              onClick={() => copyToClipboard(email)}
                              className="text-xs px-2 py-1 bg-warroom-bg border border-warroom-border rounded flex items-center gap-1 hover:border-warroom-accent transition text-warroom-text"
                              title="Click to copy"
                            >
                              <Mail size={10} /> {email}
                              <Copy size={9} className="text-warroom-muted" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {lead.website_phones && lead.website_phones.length > 0 && (
                      <div>
                        <label className="text-[10px] text-warroom-muted uppercase tracking-wide">Phones Found</label>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {lead.website_phones.map((phone, i) => (
                            <button
                              key={i}
                              onClick={() => copyToClipboard(phone)}
                              className="text-xs px-2 py-1 bg-warroom-bg border border-warroom-border rounded flex items-center gap-1 hover:border-warroom-accent transition text-warroom-text"
                              title="Click to copy"
                            >
                              <Phone size={10} /> {phone}
                              <Copy size={9} className="text-warroom-muted" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {lead.enrichment_status === "pending" && lead.has_website && (
                  <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-center gap-2 text-xs text-yellow-400">
                    <Loader2 size={14} className="animate-spin" />
                    Enrichment in progress — scraping website for contact details...
                  </div>
                )}

                {!lead.has_website && (
                  <div className="p-3 bg-warroom-bg border border-warroom-border rounded-lg text-xs text-warroom-muted">
                    No website found — contact details must be gathered manually.
                  </div>
                )}

                <h3 className="text-sm font-semibold text-warroom-text">Contact Information</h3>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Contacted By</label>
                    <input
                      value={contactForm.contacted_by}
                      onChange={(e) => setContactForm(prev => ({ ...prev, contacted_by: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder="Your name"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Who Answered</label>
                    <input
                      value={contactForm.who_answered}
                      onChange={(e) => setContactForm(prev => ({ ...prev, who_answered: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder="Contact person"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Owner Name</label>
                    <input
                      value={contactForm.owner_name}
                      onChange={(e) => setContactForm(prev => ({ ...prev, owner_name: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder="Business owner"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Economic Buyer</label>
                    <input
                      value={contactForm.economic_buyer}
                      onChange={(e) => setContactForm(prev => ({ ...prev, economic_buyer: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder="Decision maker"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Champion</label>
                    <input
                      value={contactForm.champion}
                      onChange={(e) => setContactForm(prev => ({ ...prev, champion: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder="Internal advocate"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Outcome</label>
                    <select
                      value={contactForm.outcome}
                      onChange={(e) => setContactForm(prev => ({ ...prev, outcome: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      style={{ colorScheme: "dark" }}
                    >
                      <option value="">Select outcome...</option>
                      {CONTACT_OUTCOMES.map(({ value, label }) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-warroom-muted mb-1">Notes</label>
                  <textarea
                    value={contactForm.notes}
                    onChange={(e) => setContactForm(prev => ({ ...prev, notes: e.target.value }))}
                    rows={4}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                    placeholder="Call notes, follow-up actions, etc."
                  />
                </div>

                <button
                  onClick={handleContactSubmit}
                  disabled={saving}
                  className="w-full px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? "Saving..." : "Save Contact"}
                </button>

                {/* Contact History */}
                {lead.contact_history.length > 0 && (
                  <div className="mt-6">
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">Contact History</h4>
                    <div className="space-y-2">
                      {lead.contact_history.map((contact: any, index) => (
                        <div key={index} className="p-3 bg-warroom-bg rounded-lg">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-warroom-muted">
                              {contact.contacted_by} • {new Date(contact.contacted_at).toLocaleDateString()}
                            </span>
                            <span className="text-xs px-2 py-0.5 bg-warroom-border rounded-full">
                              {contact.outcome}
                            </span>
                          </div>
                          {contact.notes && (
                            <p className="text-xs text-warroom-text">{contact.notes}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "scripts" && (
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-warroom-text">Cold Call Script</h3>
                    <button
                      onClick={() => copyToClipboard(generateColdCallScript())}
                      className="px-2 py-1 text-xs bg-warroom-border/50 hover:bg-warroom-border transition rounded flex items-center gap-1"
                    >
                      <Copy size={12} /> Copy
                    </button>
                  </div>
                  <div className="p-4 bg-warroom-bg rounded-lg border border-warroom-border">
                    <pre className="text-xs text-warroom-text whitespace-pre-wrap font-mono">
                      {generateColdCallScript()}
                    </pre>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-warroom-text">Cold Email Template</h3>
                    <button
                      onClick={() => copyToClipboard(generateColdEmail())}
                      className="px-2 py-1 text-xs bg-warroom-border/50 hover:bg-warroom-border transition rounded flex items-center gap-1"
                    >
                      <Copy size="12" /> Copy
                    </button>
                  </div>
                  <div className="p-4 bg-warroom-bg rounded-lg border border-warroom-border">
                    <pre className="text-xs text-warroom-text whitespace-pre-wrap font-mono">
                      {generateColdEmail()}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "notes" && (
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-warroom-text">Notes</h3>
                
                <div>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={8}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                    placeholder="Add your notes about this lead..."
                  />
                </div>

                {lead.tags.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {lead.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs px-2 py-1 bg-warroom-accent/20 text-warroom-accent rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={handleNotesSubmit}
                  disabled={saving}
                  className="w-full px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? "Saving..." : "Save Notes"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}