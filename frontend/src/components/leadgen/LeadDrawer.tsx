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
  UserPlus,
  Rocket,
  TrendingUp,
  Zap,
  ChevronDown,
  ChevronRight,
  BarChart3
} from "lucide-react";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";
import AgentAssignmentCard from "@/components/agents/AgentAssignmentCard";
import ScrollTabs from "@/components/ui/ScrollTabs";
import QuickActions from "@/components/communications/QuickActions";


interface DeepAuditFinding {
  category: string;
  metric: string;
  status: "pass" | "warn" | "fail";
  score: number;
  finding: string;
  recommendation: string;
  impact: "high" | "medium" | "low";
}

interface DeepAuditCategory {
  score: number;
  weight: number;
  weighted_score: number;
  findings: DeepAuditFinding[];
}

interface CompetitorData {
  name: string;
  url: string;
  word_count: number;
  pages: number;
  has_blog: boolean;
  blog_post_count: number;
  schema_types: string[];
  social_link_count: number;
  has_review_widget: boolean;
  has_google_maps: boolean;
  has_faq: boolean;
}

interface DeepAuditResults {
  url: string;
  overall_score: number;
  overall_grade: string;
  audited_at: string;
  duration_seconds: number;
  categories: Record<string, DeepAuditCategory>;
  findings: DeepAuditFinding[];
  ai_summary: string;
  ai_recommendations: string[];
  competitor_analysis: CompetitorData[];
  competitor_comparison: {
    client?: CompetitorData;
    competitors?: CompetitorData[];
  };
  extraction: Record<string, any>;
  error?: string;
}

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

  // Deep AI Audit
  deep_audit_results: DeepAuditResults | null;
  deep_audit_score: number | null;
  deep_audit_grade: string | null;
  deep_audit_date: string | null;
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
  agent_assignments?: AgentAssignmentSummary[];

  // Reviews
  yelp_rating: number | null;
  yelp_reviews_count: number;
  review_highlights: string[] | null;
  review_sentiment_score: number | null;
  review_pain_points: string[] | null;
  review_opportunity_flags: string[] | null;

  // BBB
  bbb_url: string | null;
  bbb_rating: string | null;
  bbb_accredited: boolean | null;
  bbb_complaints: number;
  bbb_summary: string | null;

  // Glassdoor
  glassdoor_url: string | null;
  glassdoor_rating: number | null;
  glassdoor_review_count: number;
  glassdoor_summary: string | null;

  // Reddit
  reddit_mentions: Array<{ title: string; url: string; subreddit: string; snippet: string; date: string }> | null;

  // News
  news_mentions: Array<{ title: string; url: string; source: string; snippet: string; date: string }> | null;

  // Social scan
  social_scan: Record<string, { url: string; exists: boolean | null; title: string; description: string; followers: number | null }> | null;
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
  const [assignTo, setAssignTo] = useState("");
  const [users, setUsers] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<{ dealId: number; assignee: string } | null>(null);

  useEffect(() => {
    authFetch(`${API}/api/crm/users`).then(r => r.json()).then(setUsers).catch(() => {});
  }, []);

  const handleAssign = async () => {
    if (!assignTo) return;
    setLoading(true);
    try {
      // Convert lead to CRM deal
      const res = await authFetch(`${API}/api/crm/deals/convert-from-lead`, {
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
        await authFetch(`${API}/api/leadgen/leads/${lead.id}/contact`, {
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
      }
    } catch (err) {
      console.error("Failed to assign:", err);
    } finally {
      setLoading(false);
    }
  };

  if (lead.outreach_status === "won") return null;

  const isReady = assignTo && assignTo !== "custom";

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
          <button
            onClick={handleAssign}
            disabled={!isReady || loading}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition ${
              isReady
                ? "bg-green-600 hover:bg-green-700 text-white"
                : "bg-warroom-border/20 text-warroom-muted cursor-not-allowed"
            }`}
          >
            {loading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <>
                <UserPlus size={16} />
                Assign & Start Pipeline
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

function IntelSection({ title, emoji, children }: { title: string; emoji: string; children: React.ReactNode }) {
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
      <h4 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider flex items-center gap-2 mb-3">
        <span>{emoji}</span> {title}
      </h4>
      {children}
    </div>
  );
}

export default function LeadDrawer({ lead, isOpen, onClose, onUpdate }: LeadDrawerProps) {
  const [activeTab, setActiveTab] = useState<"audit" | "intel" | "contact" | "scripts" | "notes">("contact");
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
  const [deepAudit, setDeepAudit] = useState<DeepAuditResults | null>(lead?.deep_audit_results || null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [teamMembers, setTeamMembers] = useState<{ id: number; name: string }[]>([]);

  // Load platform settings for script generation
  useEffect(() => {
    authFetch(`${API}/api/settings?category=general`)
      .then(r => r.ok ? r.json() : [])
      .then((items: any[]) => {
        const map: Record<string, string> = {};
        items.forEach((s: any) => { map[s.key] = s.value || ""; });
        setSettings(map);
      })
      .catch(() => {});
    // Load team members for dropdown
    authFetch(`${API}/api/crm/users`)
      .then(r => r.ok ? r.json() : [])
      .then((users: any[]) => setTeamMembers(users.map((u: any) => ({ id: u.id, name: u.name }))))
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
      setDeepAudit(lead.deep_audit_results || null);
      setExpandedCategories(new Set());
    }
  }, [lead]);

  const [pipelineToast, setPipelineToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [startingPipeline, setStartingPipeline] = useState(false);

  useEffect(() => {
    if (pipelineToast) {
      const t = setTimeout(() => setPipelineToast(null), 4000);
      return () => clearTimeout(t);
    }
  }, [pipelineToast]);

  const startPipeline = async () => {
    if (!lead) return;
    setStartingPipeline(true);
    try {
      const res = await authFetch(`${API}/api/crm/deals/convert-from-lead`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          leadgen_lead_id: lead.id,
          title: lead.business_name,
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
        setPipelineToast({ type: "success", message: `✓ Deal created — ${lead.business_name} added to Lead Discovery` });
        const updatedLead = { ...lead, outreach_status: "in_progress" };
        onUpdate?.(updatedLead);
      } else {
        setPipelineToast({ type: "error", message: "Failed to create deal" });
      }
    } catch {
      setPipelineToast({ type: "error", message: "Failed to create deal" });
    } finally {
      setStartingPipeline(false);
    }
  };

  if (!isOpen || !lead) return null;

  const handleContactSubmit = async () => {
    setSaving(true);
    try {
      const response = await authFetch(`${API}/api/leadgen/leads/${lead.id}/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(contactForm),
      });
      if (response.ok) {
        const updatedLead = await response.json();
        onUpdate?.(updatedLead);
        // Reset form after successful save
        setContactForm(prev => ({ ...prev, outcome: "", notes: "", who_answered: "", owner_name: "", economic_buyer: "", champion: "" }));
      } else {
        const data = await response.json().catch(() => ({}));
        console.error("Save contact failed:", data.detail || response.status);
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
      const response = await authFetch(`${API}/api/leadgen/leads/${lead.id}`, {
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

  const triggerDeepAudit = async () => {
    setAuditLoading(true);
    try {
      const response = await authFetch(`${API}/api/leadgen/leads/${lead.id}/deep-audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry: lead.business_category || undefined,
        }),
      });
      if (response.ok) {
        const auditData = await response.json();
        setDeepAudit(auditData);
        // Refresh the full lead object
        const leadResponse = await authFetch(`${API}/api/leadgen/leads/${lead.id}`);
        if (leadResponse.ok) {
          const updatedLead = await leadResponse.json();
          onUpdate?.(updatedLead);
        }
      }
    } catch (error) {
      console.error("Failed to trigger deep audit:", error);
    } finally {
      setAuditLoading(false);
    }
  };

  const toggleCategory = (cat: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  const companyName = settings.company_name || "My Company";
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
                  <div className="flex items-center gap-2">
                    <button
                      onClick={startPipeline}
                      disabled={startingPipeline}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition"
                    >
                      {startingPipeline ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />}
                      Start Pipeline
                    </button>
                    <button
                      onClick={onClose}
                      className="text-warroom-muted hover:text-warroom-text transition p-2"
                    >
                      <X size={20} />
                    </button>
                  </div>
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
                  {(lead.phone || lead.emails?.[0]) && (
                    <div className="flex items-center gap-1 col-span-2">
                      <span className="text-xs text-warroom-muted mr-1">Quick:</span>
                      <QuickActions
                        phone={lead.phone}
                        email={lead.emails?.[0]}
                        name={lead.business_name}
                        size="sm"
                      />
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

                <AgentAssignmentCard
                  className="mt-4"
                  entityType="leadgen_lead"
                  entityId={lead.id}
                  initialAssignments={lead.agent_assignments}
                  title={`Work lead: ${lead.business_name}`}
                />
              </div>
            </div>
          </div>

          {/* Tabs */}
          <ScrollTabs
            tabs={[
              { id: "audit", label: "Audit", icon: FileText },
              { id: "intel", label: "Intel", icon: Globe },
              { id: "contact", label: "Contact", icon: PhoneIcon },
              { id: "scripts", label: "Scripts", icon: MessageSquare },
              { id: "notes", label: "Notes", icon: StickyNote },
            ]}
            active={activeTab}
            onChange={(id) => setActiveTab(id as any)}
          />

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "audit" && (
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-warroom-text flex items-center gap-2">
                    <Zap size={16} className="text-warroom-accent" />
                    Deep AI Audit
                  </h3>
                  <button
                    onClick={triggerDeepAudit}
                    disabled={auditLoading}
                    className="px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition flex items-center gap-1"
                  >
                    {auditLoading ? <Loader2 size={14} className="animate-spin" /> : <BarChart3 size={14} />}
                    {auditLoading ? "Analyzing..." : deepAudit ? "Re-run Audit" : "Run Deep Audit"}
                  </button>
                </div>

                {auditLoading && (
                  <div className="p-4 bg-warroom-accent/5 border border-warroom-accent/20 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Loader2 size={18} className="animate-spin text-warroom-accent" />
                      <div>
                        <p className="text-sm text-warroom-text font-medium">Running deep analysis...</p>
                        <p className="text-xs text-warroom-muted mt-0.5">Crawling site, checking robots.txt, sitemap, analyzing content with AI (15-30s)</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Quick flags from enrichment */}
                {lead.audit_lite_flags.length > 0 && !deepAudit && (
                  <div>
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">Quick Scan Issues</h4>
                    <div className="flex flex-wrap gap-2">
                      {lead.audit_lite_flags.map((flag) => (
                        <span key={flag} className="text-xs px-2 py-1 bg-orange-500/20 text-orange-400 rounded-full">{flag}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Deep Audit Results */}
                {deepAudit && (
                  <div className="space-y-4">
                    {/* Overall Score */}
                    <div className="p-4 bg-warroom-bg rounded-xl border border-warroom-border">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <span className="text-3xl font-bold text-warroom-text">{deepAudit.overall_score}</span>
                          <span className="text-sm text-warroom-muted">/100</span>
                        </div>
                        <span className={`text-2xl font-bold px-3 py-1 rounded-lg ${
                          deepAudit.overall_grade === "A" ? "bg-green-500/20 text-green-400" :
                          deepAudit.overall_grade === "B" ? "bg-blue-500/20 text-blue-400" :
                          deepAudit.overall_grade === "C" ? "bg-yellow-500/20 text-yellow-400" :
                          deepAudit.overall_grade === "D" ? "bg-orange-500/20 text-orange-400" :
                          "bg-red-500/20 text-red-400"
                        }`}>{deepAudit.overall_grade}</span>
                      </div>
                      <div className="w-full h-3 bg-warroom-border rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            deepAudit.overall_score >= 80 ? "bg-green-500" :
                            deepAudit.overall_score >= 60 ? "bg-yellow-500" :
                            deepAudit.overall_score >= 40 ? "bg-orange-500" : "bg-red-500"
                          }`}
                          style={{ width: `${deepAudit.overall_score}%` }}
                        />
                      </div>
                      {deepAudit.audited_at && (
                        <p className="text-[10px] text-warroom-muted mt-2">
                          Audited {new Date(deepAudit.audited_at).toLocaleDateString()} · {deepAudit.duration_seconds}s
                        </p>
                      )}
                    </div>

                    {/* Category Scores */}
                    <div className="space-y-2">
                      {Object.entries(deepAudit.categories).map(([catKey, cat]) => {
                        const isExpanded = expandedCategories.has(catKey);
                        const label = catKey.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
                        const failCount = cat.findings.filter(f => f.status === "fail").length;
                        const warnCount = cat.findings.filter(f => f.status === "warn").length;
                        return (
                          <div key={catKey} className="bg-warroom-bg rounded-xl border border-warroom-border overflow-hidden">
                            <button
                              onClick={() => toggleCategory(catKey)}
                              className="w-full flex items-center justify-between p-3 hover:bg-warroom-surface/50 transition text-left"
                            >
                              <div className="flex items-center gap-3">
                                {isExpanded ? <ChevronDown size={14} className="text-warroom-muted" /> : <ChevronRight size={14} className="text-warroom-muted" />}
                                <span className="text-sm font-medium text-warroom-text">{label}</span>
                                <span className="text-[10px] text-warroom-muted">({(cat.weight * 100).toFixed(0)}% weight)</span>
                              </div>
                              <div className="flex items-center gap-2">
                                {failCount > 0 && <span className="text-[10px] px-1.5 py-0.5 bg-red-500/15 text-red-400 rounded">{failCount} fail</span>}
                                {warnCount > 0 && <span className="text-[10px] px-1.5 py-0.5 bg-yellow-500/15 text-yellow-400 rounded">{warnCount} warn</span>}
                                <span className={`text-sm font-bold ${
                                  cat.score >= 80 ? "text-green-400" :
                                  cat.score >= 60 ? "text-yellow-400" :
                                  cat.score >= 40 ? "text-orange-400" : "text-red-400"
                                }`}>{cat.score}</span>
                              </div>
                            </button>
                            {isExpanded && (
                              <div className="border-t border-warroom-border/50 p-3 space-y-2">
                                {cat.findings.map((f, i) => (
                                  <div key={i} className="flex items-start gap-2 py-1.5">
                                    <span className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                                      f.status === "pass" ? "bg-green-400" :
                                      f.status === "warn" ? "bg-yellow-400" : "bg-red-400"
                                    }`} />
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-2">
                                        <span className="text-xs font-medium text-warroom-text">{f.metric}</span>
                                        {f.impact === "high" && f.status !== "pass" && (
                                          <span className="text-[9px] px-1 py-0.5 bg-red-500/10 text-red-400 rounded">HIGH</span>
                                        )}
                                      </div>
                                      <p className="text-[11px] text-warroom-muted mt-0.5">{f.finding}</p>
                                      {f.recommendation && (
                                        <p className="text-[11px] text-warroom-accent/80 mt-1">→ {f.recommendation}</p>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* AI Summary */}
                    {deepAudit.ai_summary && (
                      <div className="bg-warroom-accent/5 border border-warroom-accent/20 rounded-xl p-4">
                        <h4 className="text-xs font-semibold text-warroom-accent flex items-center gap-2 mb-2">
                          <Zap size={12} />
                          AI Analysis
                        </h4>
                        <p className="text-xs text-warroom-text whitespace-pre-line leading-relaxed">{deepAudit.ai_summary}</p>
                      </div>
                    )}

                    {/* AI Recommendations */}
                    {deepAudit.ai_recommendations && deepAudit.ai_recommendations.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-warroom-muted mb-2 flex items-center gap-2">
                          <TrendingUp size={12} />
                          Top Recommendations
                        </h4>
                        <div className="space-y-2">
                          {deepAudit.ai_recommendations.map((rec, i) => (
                            <div key={i} className="flex items-start gap-2 p-2.5 bg-warroom-bg rounded-lg border border-warroom-border/50">
                              <span className="text-xs font-bold text-warroom-accent mt-0.5">{i + 1}.</span>
                              <span className="text-xs text-warroom-text">{rec}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Competitor Comparison */}
                    {deepAudit.competitor_comparison?.competitors && deepAudit.competitor_comparison.competitors.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-warroom-muted mb-2 flex items-center gap-2">
                          <BarChart3 size={12} />
                          Competitor Gap Analysis
                        </h4>
                        <div className="overflow-x-auto">
                          <table className="w-full text-[11px]">
                            <thead>
                              <tr className="border-b border-warroom-border">
                                <th className="text-left py-2 pr-2 text-warroom-muted font-medium">Metric</th>
                                <th className="text-center py-2 px-2 text-warroom-accent font-medium truncate max-w-[100px]">
                                  {deepAudit.competitor_comparison.client?.name?.slice(0, 18) || "Client"}
                                </th>
                                {deepAudit.competitor_comparison.competitors.map((c, i) => (
                                  <th key={i} className="text-center py-2 px-2 text-warroom-muted font-medium truncate max-w-[100px]">
                                    {c.name?.slice(0, 18) || `Comp ${i + 1}`}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {[
                                { label: "Word Count", key: "word_count", format: (v: number) => v.toLocaleString() },
                                { label: "Pages", key: "pages", format: (v: number) => v.toString() },
                                { label: "Blog", key: "has_blog", format: (v: boolean, d: CompetitorData) => v ? `Yes${d.blog_post_count ? ` (${d.blog_post_count})` : ""}` : "No" },
                                { label: "Schema", key: "schema_types", format: (v: string[]) => v.length ? v.join(", ") : "None" },
                                { label: "Social Links", key: "social_link_count", format: (v: number) => v.toString() },
                                { label: "Reviews", key: "has_review_widget", format: (v: boolean) => v ? "Yes" : "No" },
                                { label: "Google Maps", key: "has_google_maps", format: (v: boolean) => v ? "Yes" : "No" },
                                { label: "FAQ", key: "has_faq", format: (v: boolean) => v ? "Yes" : "No" },
                              ].map((row) => {
                                const clientVal = (deepAudit.competitor_comparison.client as any)?.[row.key];
                                return (
                                  <tr key={row.key} className="border-b border-warroom-border/30">
                                    <td className="py-1.5 pr-2 text-warroom-muted">{row.label}</td>
                                    <td className="py-1.5 px-2 text-center text-warroom-text font-medium">
                                      {(row.format as any)(clientVal, deepAudit.competitor_comparison.client)}
                                    </td>
                                    {deepAudit.competitor_comparison.competitors!.map((comp, i) => {
                                      const compVal = (comp as any)[row.key];
                                      const isBetter = row.key === "word_count" ? compVal > (clientVal || 0) * 1.5 :
                                        row.key === "pages" ? compVal > (clientVal || 0) * 1.5 :
                                        row.key === "social_link_count" ? compVal > (clientVal || 0) :
                                        typeof compVal === "boolean" ? compVal && !clientVal :
                                        Array.isArray(compVal) ? compVal.length > (clientVal?.length || 0) : false;
                                      return (
                                        <td key={i} className={`py-1.5 px-2 text-center ${isBetter ? "text-green-400" : "text-warroom-muted"}`}>
                                          {(row.format as any)(compVal, comp)}
                                        </td>
                                      );
                                    })}
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Fallback: show basic audit if no deep audit */}
                {!deepAudit && !auditLoading && lead.website_audit_score != null && (
                  <div className="p-3 bg-warroom-bg rounded-lg border border-warroom-border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-warroom-text">Basic Audit Score: {lead.website_audit_score}/100</span>
                      <span className="text-sm font-medium text-warroom-accent">{lead.website_audit_grade}</span>
                    </div>
                    {lead.website_audit_summary && (
                      <p className="text-xs text-warroom-muted">{lead.website_audit_summary}</p>
                    )}
                    <p className="text-[10px] text-warroom-accent mt-2">Run a Deep AI Audit for comprehensive analysis →</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "intel" && (
              <div className="space-y-5">
                {/* BBB */}
                <IntelSection title="Better Business Bureau" emoji="🏛️">
                  {lead.bbb_url ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        {lead.bbb_rating && (
                          <span className={`text-lg font-bold ${lead.bbb_rating.startsWith('A') ? 'text-green-400' : lead.bbb_rating.startsWith('B') ? 'text-yellow-400' : 'text-red-400'}`}>
                            {lead.bbb_rating}
                          </span>
                        )}
                        {lead.bbb_accredited && (
                          <span className="text-[10px] px-2 py-0.5 bg-green-500/15 text-green-400 rounded-full font-medium">Accredited</span>
                        )}
                        {lead.bbb_complaints > 0 && (
                          <span className="text-[10px] px-2 py-0.5 bg-red-500/15 text-red-400 rounded-full">{lead.bbb_complaints} complaints</span>
                        )}
                      </div>
                      <a href={lead.bbb_url} target="_blank" rel="noopener" className="text-xs text-warroom-accent hover:underline block truncate">{lead.bbb_url}</a>
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted">No BBB profile found</p>
                  )}
                </IntelSection>

                {/* Glassdoor */}
                <IntelSection title="Glassdoor" emoji="🏢">
                  {lead.glassdoor_url ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        {lead.glassdoor_rating != null && (
                          <span className="text-lg font-bold text-warroom-text">{lead.glassdoor_rating}/5</span>
                        )}
                        {lead.glassdoor_review_count > 0 && (
                          <span className="text-xs text-warroom-muted">{lead.glassdoor_review_count} reviews</span>
                        )}
                      </div>
                      {lead.glassdoor_summary && <p className="text-xs text-warroom-muted">{lead.glassdoor_summary}</p>}
                      <a href={lead.glassdoor_url} target="_blank" rel="noopener" className="text-xs text-warroom-accent hover:underline block truncate">{lead.glassdoor_url}</a>
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted">No Glassdoor listing found</p>
                  )}
                </IntelSection>

                {/* Yelp */}
                <IntelSection title="Yelp Reviews" emoji="⭐">
                  {lead.yelp_rating != null || lead.yelp_reviews_count > 0 ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        {lead.yelp_rating != null && <span className="text-lg font-bold text-warroom-text">{lead.yelp_rating}/5</span>}
                        <span className="text-xs text-warroom-muted">{lead.yelp_reviews_count} reviews</span>
                      </div>
                      {lead.review_sentiment_score != null && (
                        <div className="text-xs text-warroom-muted">
                          Sentiment: <span className={lead.review_sentiment_score >= 0 ? "text-green-400" : "text-red-400"}>
                            {lead.review_sentiment_score > 0 ? "+" : ""}{(lead.review_sentiment_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                      {lead.review_pain_points && lead.review_pain_points.length > 0 && (
                        <div>
                          <p className="text-[10px] text-warroom-muted uppercase mb-1">Pain Points</p>
                          <div className="flex flex-wrap gap-1.5">
                            {lead.review_pain_points.map((p, i) => (
                              <span key={i} className="text-[10px] px-2 py-0.5 bg-red-500/15 text-red-400 rounded-full">{p}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {lead.review_opportunity_flags && lead.review_opportunity_flags.length > 0 && (
                        <div>
                          <p className="text-[10px] text-warroom-muted uppercase mb-1">Opportunity Flags</p>
                          <div className="flex flex-wrap gap-1.5">
                            {lead.review_opportunity_flags.map((f, i) => (
                              <span key={i} className="text-[10px] px-2 py-0.5 bg-orange-500/15 text-orange-400 rounded-full">{f}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted">No Yelp data</p>
                  )}
                </IntelSection>

                {/* Social Presence */}
                <IntelSection title="Social Presence" emoji="📱">
                  {lead.social_scan && Object.keys(lead.social_scan).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(lead.social_scan).map(([platform, info]) => (
                        <div key={platform} className="flex items-center justify-between py-1.5 border-b border-warroom-border/30 last:border-0">
                          <div className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${info.exists ? "bg-green-400" : info.exists === false ? "bg-red-400" : "bg-gray-400"}`} />
                            <span className="text-xs text-warroom-text capitalize">{platform}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {info.followers != null && (
                              <span className="text-[10px] text-warroom-muted">{info.followers.toLocaleString()} followers</span>
                            )}
                            <a href={info.url} target="_blank" rel="noopener" className="text-[10px] text-warroom-accent hover:underline">View</a>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted">No social profiles found</p>
                  )}
                </IntelSection>

                {/* Reddit Mentions */}
                <IntelSection title="Reddit Mentions" emoji="🗣️">
                  {lead.reddit_mentions && lead.reddit_mentions.length > 0 ? (
                    <div className="space-y-2">
                      {lead.reddit_mentions.map((m, i) => (
                        <a key={i} href={m.url} target="_blank" rel="noopener" className="block p-2 bg-warroom-bg rounded-lg hover:bg-warroom-surface transition">
                          <p className="text-xs text-warroom-text font-medium">{m.title}</p>
                          <p className="text-[10px] text-warroom-muted mt-0.5">r/{m.subreddit} · {m.date || "unknown date"}</p>
                          {m.snippet && <p className="text-[10px] text-warroom-muted mt-1 line-clamp-2">{m.snippet}</p>}
                        </a>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted">No Reddit mentions found</p>
                  )}
                </IntelSection>

                {/* News Mentions */}
                <IntelSection title="News & Press" emoji="📰">
                  {lead.news_mentions && lead.news_mentions.length > 0 ? (
                    <div className="space-y-2">
                      {lead.news_mentions.map((m, i) => (
                        <a key={i} href={m.url} target="_blank" rel="noopener" className="block p-2 bg-warroom-bg rounded-lg hover:bg-warroom-surface transition">
                          <p className="text-xs text-warroom-text font-medium">{m.title}</p>
                          <p className="text-[10px] text-warroom-muted mt-0.5">{m.source} · {m.date || ""}</p>
                          {m.snippet && <p className="text-[10px] text-warroom-muted mt-1 line-clamp-2">{m.snippet}</p>}
                        </a>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-warroom-muted">No news coverage found</p>
                  )}
                </IntelSection>
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
                    <select
                      value={contactForm.contacted_by}
                      onChange={(e) => setContactForm(prev => ({ ...prev, contacted_by: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
                      style={{ colorScheme: "dark" }}
                    >
                      <option value="">Select team member...</option>
                      {teamMembers.map((u) => (
                        <option key={u.id} value={u.name}>{u.name}</option>
                      ))}
                    </select>
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
                      {lead.contact_history.map((contact: any, index) => {
                        // Backend stores "date" and "by", not "contacted_at" / "contacted_by"
                        const dateStr = contact.date || contact.contacted_at;
                        const byStr = contact.by || contact.contacted_by || "";
                        const parsed = dateStr ? new Date(dateStr) : null;
                        const formattedDate = parsed && !isNaN(parsed.getTime())
                          ? parsed.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })
                          : "Unknown date";
                        return (
                        <div key={index} className="p-3 bg-warroom-bg rounded-lg">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-warroom-muted">
                              {byStr} • {formattedDate}
                            </span>
                            <span className="text-xs px-2 py-0.5 bg-warroom-border rounded-full">
                              {contact.outcome}
                            </span>
                          </div>
                          {(contact.notes || contact.who_answered) && (
                            <p className="text-xs text-warroom-text">
                              {contact.who_answered && <span className="text-warroom-muted">Spoke with: {contact.who_answered} · </span>}
                              {contact.notes}
                            </p>
                          )}
                        </div>
                        );
                      })}
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

      {/* Pipeline Toast */}
      {pipelineToast && (
        <div className={`fixed bottom-6 right-6 z-[70] px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 ${
          pipelineToast.type === "success"
            ? "bg-green-600/90 text-white"
            : "bg-red-600/90 text-white"
        }`}>
          {pipelineToast.message}
          <button onClick={() => setPipelineToast(null)} className="ml-2 opacity-70 hover:opacity-100">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}