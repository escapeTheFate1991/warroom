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
  BarChart3,
  Download,
  Award,
  Target,
  Wrench,
  Pencil,
  Check,
  Maximize2,
  Minimize2
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
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
  agent_assignments?: { agent_id: string; agent_name: string; status: string }[];

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

const CALL_OUTCOMES = [
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
  { value: "follow_up", label: "Follow Up" },
  { value: "no_answer", label: "No Answer" },
  { value: "callback", label: "Callback" },
  { value: "voicemail", label: "Voicemail" },
];

const EMAIL_OUTCOMES = [
  { value: "email_sent", label: "Email Sent" },
  { value: "email_replied", label: "Reply Received" },
  { value: "email_bounced", label: "Bounced" },
  { value: "follow_up", label: "Follow Up Needed" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
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
          // Propagate enrichment data to deal metadata
          google_place_id: (lead as any).google_place_id,
          google_rating: (lead as any).google_rating,
          yelp_url: (lead as any).yelp_url,
          yelp_rating: (lead as any).yelp_rating,
          audit_lite_flags: (lead as any).audit_lite_flags,
          website_audit_score: (lead as any).website_audit_score,
          website_audit_grade: (lead as any).website_audit_grade,
          website_audit_summary: (lead as any).website_audit_summary,
          website_audit_top_fixes: (lead as any).website_audit_top_fixes,
          review_pain_points: (lead as any).review_pain_points,
          review_opportunity_flags: (lead as any).review_opportunity_flags,
          lead_score: (lead as any).lead_score,
          lead_tier: (lead as any).lead_tier,
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
    contact_method: "call" as "call" | "email",
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
        contact_method: "call",
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

  // Inline editing state
  const [isEditingDetails, setIsEditingDetails] = useState(false);
  const [isPopoutOpen, setIsPopoutOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    business_name: "",
    phone: "",
    address: "",
    city: "",
    state: "",
    website: "",
    email: "",
  });
  const [savingDetails, setSavingDetails] = useState(false);

  // Reset edit form when lead changes
  useEffect(() => {
    if (lead) {
      setEditForm({
        business_name: lead.business_name || "",
        phone: lead.phone || "",
        address: lead.address || "",
        city: lead.city || "",
        state: lead.state || "",
        website: lead.website || "",
        email: lead.emails?.[0] || "",
      });
      setIsEditingDetails(false);
    }
  }, [lead]);

  const handleSaveDetails = async () => {
    if (!lead) return;
    setSavingDetails(true);
    try {
      const payload: Record<string, unknown> = {};
      if (editForm.business_name !== (lead.business_name || "")) payload.business_name = editForm.business_name;
      if (editForm.phone !== (lead.phone || "")) payload.phone = editForm.phone || null;
      if (editForm.address !== (lead.address || "")) payload.address = editForm.address || null;
      if (editForm.city !== (lead.city || "")) payload.city = editForm.city || null;
      if (editForm.state !== (lead.state || "")) payload.state = editForm.state || null;
      if (editForm.website !== (lead.website || "")) payload.website = editForm.website || null;
      const newEmail = editForm.email.trim();
      const oldEmail = lead.emails?.[0] || "";
      if (newEmail !== oldEmail) {
        payload.emails = newEmail ? [newEmail, ...lead.emails.slice(1)] : lead.emails.slice(1);
      }
      if (Object.keys(payload).length === 0) {
        setIsEditingDetails(false);
        return;
      }
      const response = await authFetch(`${API}/api/leadgen/leads/${lead.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        const updatedLead = await response.json();
        onUpdate?.(updatedLead);
        setIsEditingDetails(false);
      }
    } catch (error) {
      console.error("Failed to save details:", error);
    } finally {
      setSavingDetails(false);
    }
  };

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
          // Propagate enrichment data to deal metadata
          google_place_id: (lead as any).google_place_id,
          google_rating: (lead as any).google_rating,
          yelp_url: (lead as any).yelp_url,
          yelp_rating: (lead as any).yelp_rating,
          audit_lite_flags: (lead as any).audit_lite_flags,
          website_audit_score: (lead as any).website_audit_score,
          website_audit_grade: (lead as any).website_audit_grade,
          website_audit_summary: (lead as any).website_audit_summary,
          website_audit_top_fixes: (lead as any).website_audit_top_fixes,
          review_pain_points: (lead as any).review_pain_points,
          review_opportunity_flags: (lead as any).review_opportunity_flags,
          lead_score: (lead as any).lead_score,
          lead_tier: (lead as any).lead_tier,
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
        setContactForm(prev => ({ ...prev, contact_method: "call", outcome: "", notes: "", who_answered: "", owner_name: "", economic_buyer: "", champion: "" }));
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

  const downloadAuditPdf = () => {
    const biz = lead.business_name;
    const score = lead.website_audit_score ?? deepAudit?.overall_score ?? "N/A";
    const grade = lead.website_audit_grade ?? deepAudit?.overall_grade ?? "N/A";
    const summary = deepAudit?.ai_summary || lead.website_audit_summary || "";
    const recommendations = deepAudit?.ai_recommendations || [];
    const findings = deepAudit?.findings || [];
    const topFixes = lead.website_audit_top_fixes || [];
    const liteFlags = lead.audit_lite_flags || [];

    const findingsHtml = findings.length > 0
      ? findings.map((f: DeepAuditFinding) => `<tr><td style="padding:6px 10px;border-bottom:1px solid #eee;">${f.category}</td><td style="padding:6px 10px;border-bottom:1px solid #eee;">${f.metric}</td><td style="padding:6px 10px;border-bottom:1px solid #eee;color:${f.status === 'fail' ? '#dc2626' : f.status === 'warn' ? '#d97706' : '#16a34a'}">${f.status.toUpperCase()}</td><td style="padding:6px 10px;border-bottom:1px solid #eee;">${f.finding}</td><td style="padding:6px 10px;border-bottom:1px solid #eee;">${f.recommendation}</td></tr>`).join("")
      : "";

    const categoriesHtml = deepAudit?.categories
      ? Object.entries(deepAudit.categories).map(([name, cat]) => {
          const c = cat as DeepAuditCategory;
          return `<div style="display:inline-block;width:130px;text-align:center;margin:8px;padding:12px;border:1px solid #e5e7eb;border-radius:8px;"><div style="font-size:24px;font-weight:bold;color:${c.score >= 70 ? '#16a34a' : c.score >= 40 ? '#d97706' : '#dc2626'}">${c.score}</div><div style="font-size:11px;color:#6b7280;margin-top:4px;">${name.replace(/_/g, " ").toUpperCase()}</div></div>`;
        }).join("")
      : "";

    const html = `<!DOCTYPE html><html><head><title>Website Audit — ${biz}</title><style>body{font-family:-apple-system,system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#1f2937;line-height:1.6}h1{font-size:22px;margin-bottom:4px}h2{font-size:16px;margin-top:28px;border-bottom:2px solid #e5e7eb;padding-bottom:6px}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;padding:8px 10px;background:#f9fafb;border-bottom:2px solid #e5e7eb;font-size:12px;text-transform:uppercase;color:#6b7280}ul{padding-left:20px}li{margin-bottom:6px;font-size:14px}.score-badge{display:inline-block;font-size:36px;font-weight:bold;padding:8px 20px;border-radius:12px;margin-right:12px}.grade-badge{display:inline-block;font-size:28px;font-weight:bold;padding:8px 16px;border-radius:8px;background:#f3f4f6}@media print{body{margin:20px}}</style></head><body>
<h1>Website Audit Report</h1>
<p style="color:#6b7280;margin-bottom:20px;">${biz} · ${lead.website || "No website"} · ${new Date().toLocaleDateString()}</p>
<div style="margin:20px 0;"><span class="score-badge" style="background:${typeof score === 'number' && score >= 70 ? '#dcfce7;color:#16a34a' : typeof score === 'number' && score >= 40 ? '#fef3c7;color:#d97706' : '#fee2e2;color:#dc2626'}">${score}/100</span><span class="grade-badge">${grade}</span></div>
${summary ? `<h2>Summary</h2><p>${summary}</p>` : ""}
${categoriesHtml ? `<h2>Category Scores</h2><div>${categoriesHtml}</div>` : ""}
${recommendations.length > 0 ? `<h2>AI Recommendations</h2><ul>${recommendations.map(r => `<li>${r}</li>`).join("")}</ul>` : ""}
${findingsHtml ? `<h2>Detailed Findings</h2><table><thead><tr><th>Category</th><th>Metric</th><th>Status</th><th>Finding</th><th>Recommendation</th></tr></thead><tbody>${findingsHtml}</tbody></table>` : ""}
${topFixes.length > 0 ? `<h2>Top Fixes</h2><ul>${topFixes.map(f => `<li>${f}</li>`).join("")}</ul>` : ""}
${liteFlags.length > 0 ? `<h2>Audit Flags</h2><ul>${liteFlags.map(f => `<li>${f}</li>`).join("")}</ul>` : ""}
<p style="margin-top:40px;font-size:12px;color:#9ca3af;">Generated by WarRoom · ${new Date().toISOString()}</p>
</body></html>`;

    const w = window.open("", "_blank");
    if (w) {
      w.document.write(html);
      w.document.close();
      setTimeout(() => w.print(), 500);
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

  const companyName = settings.company_name || "Stuff N Things";
  const userName = settings.your_name || contactForm.contacted_by || "";
  const userPhone = settings.your_phone || "";
  const contactName = lead.contact_owner_name || lead.contact_who_answered || "";

  const generateColdCallScript = () => {
    const caller = userName || "[Your Name]";
    const biz = lead.business_name;
    const category = (lead.business_category || "local business").replace(/_/g, " ");
    const city = lead.city || "your area";
    const greeting = contactName ? `Is this ${contactName}?` : "Who am I speaking with?";

    // Determine variant based on lead data
    const hasLowReviews = (lead.google_rating != null && lead.google_rating < 4.0) ||
      (lead.yelp_rating != null && lead.yelp_rating < 4.0);

    // Build specific findings from audit data
    const findings: string[] = [];
    if (deepAudit?.ai_recommendations) {
      findings.push(...deepAudit.ai_recommendations.slice(0, 3));
    } else if (deepAudit?.findings) {
      deepAudit.findings
        .filter((f: DeepAuditFinding) => f.status === "fail" || f.status === "warn")
        .slice(0, 3)
        .forEach((f: DeepAuditFinding) => findings.push(f.finding));
    }
    if (findings.length === 0 && lead.audit_lite_flags.length > 0) {
      findings.push(...lead.audit_lite_flags.slice(0, 3));
    }
    if (findings.length === 0 && lead.website_audit_top_fixes?.length > 0) {
      findings.push(...lead.website_audit_top_fixes.slice(0, 3));
    }
    // Distill finding keywords for natural conversation
    const painPoints = findings.length > 0
      ? findings.map(f => f.split(/[—\-:,.]/)[0].trim().toLowerCase()).filter(Boolean).slice(0, 3)
      : [];

    let script: string;
    let objections: string;

    if (!lead.has_website) {
      // ── NO WEBSITE variant ──
      script = `Hi, this is ${caller} from ${companyName}. ${greeting}

I'm reaching out because I work with ${category} businesses in ${city}, and I noticed ${biz} doesn't have a website right now. Do you have 30 seconds?

[WAIT FOR YES]

Here's why I'm calling — when someone in ${city} needs a ${category}, they Google it. Without a site, those customers are going straight to your competitors.

We build and manage websites for local businesses. Done-for-you, no upfront cost, starts at $299 a month. We've got several ${category} clients already.

Can I send you a quick example of what we'd build for ${biz}? Takes 15 minutes to walk through.`;
    } else if (hasLowReviews) {
      // ── LOW REVIEWS variant ──
      const rating = lead.google_rating || lead.yelp_rating || "low";
      script = `Hi, this is ${caller} from ${companyName}. ${greeting}

I work with ${category} businesses in ${city}. I noticed ${biz} has a ${rating}-star rating online. Do you have 30 seconds?

[WAIT FOR YES]

Here's the thing — most people won't call a business under 4 stars. But it's not just about getting more reviews. Your website needs to make it easy for happy customers to leave one.

We help businesses like yours build a site that drives reviews, shows off your work, and builds trust before someone ever picks up the phone.

Can I send you a free breakdown of what we'd fix? No cost, just the data.`;
    } else {
      // ── HAS WEBSITE (with audit issues) variant ──
      const painPointOpener = painPoints.length > 0
        ? `things like ${painPoints.join(", ")}`
        : "some technical issues";
      const scoreText = lead.website_audit_score != null
        ? `Your site scored ${lead.website_audit_score} out of 100 on our audit. `
        : "";
      script = `Hi, this is ${caller} from ${companyName}. ${greeting}

I work with ${category} businesses in ${city}. I ran a quick audit on ${biz}'s website and noticed ${painPointOpener} that could be quietly costing you customers. Do you have 30 seconds?

[WAIT FOR YES]

${scoreText}These are the kinds of small technical issues that push potential ${city} customers to competing ${category} companies without you ever knowing.

I put together a full breakdown with the exact fixes. Would you like me to send it over? No cost and no pitch — just figured you might find it useful.`;
    }

    // ── Objection handlers ──
    objections = `
---
OBJECTION HANDLERS:

"I'm busy right now"
→ Totally understand. Can I email you the report instead? Takes 2 minutes to read. What's the best email?

"Not interested"
→ Fair enough. Just so you know — we found ${painPoints.length > 0 ? painPoints[0] : "an issue"} that's likely costing you customers. I'll send the data in case you change your mind. What's your email?

"I already have a web person"
→ No problem. We're not trying to replace anyone. The audit might actually help them — it catches things most developers miss. Want me to send it to you or directly to them?`;

    return script + objections;
  };

  const generateColdEmail = () => {
    const recipientEmail = lead.emails?.[0] || "";
    const recipientName = contactName || "there";
    const sender = userName || "[Your Name]";
    const phone = userPhone || "";
    const biz = lead.business_name;
    const category = (lead.business_category || "local business").replace(/_/g, " ");
    const city = lead.city || "your area";

    // Build specific findings from deepest available data
    const findings: string[] = [];
    if (deepAudit?.ai_recommendations) {
      findings.push(...deepAudit.ai_recommendations.slice(0, 3));
    } else if (deepAudit?.findings) {
      deepAudit.findings
        .filter((f: DeepAuditFinding) => f.status === "fail" || f.status === "warn")
        .slice(0, 3)
        .forEach((f: DeepAuditFinding) => findings.push(`${f.finding} — ${f.recommendation}`));
    }
    if (findings.length === 0 && lead.website_audit_top_fixes?.length > 0) {
      findings.push(...lead.website_audit_top_fixes.slice(0, 3));
    }
    if (findings.length === 0 && lead.audit_lite_flags.length > 0) {
      findings.push(...lead.audit_lite_flags.slice(0, 3));
    }

    const findingsBullets = findings.length > 0
      ? findings.map((f) => `• ${f}`).join("\n")
      : "";

    // Build short keyword summary for the "full breakdown" line (e.g. "XML, FAQ, sitemap")
    const findingsKeywords = findings.length > 0
      ? findings.map((f) => {
          // Extract short keyword from finding text
          const lower = f.toLowerCase();
          if (lower.includes("faq")) return "FAQ structure";
          if (lower.includes("sitemap")) return "sitemap";
          if (lower.includes("xml")) return "XML";
          if (lower.includes("ssl") || lower.includes("https")) return "SSL/HTTPS";
          if (lower.includes("schema") || lower.includes("structured")) return "structured data";
          if (lower.includes("seo")) return "local SEO";
          if (lower.includes("mobile") || lower.includes("responsive")) return "mobile optimization";
          if (lower.includes("speed") || lower.includes("performance") || lower.includes("load")) return "page speed";
          if (lower.includes("meta") || lower.includes("title")) return "meta tags";
          if (lower.includes("review")) return "review visibility";
          if (lower.includes("image") || lower.includes("alt")) return "image optimization";
          if (lower.includes("analytics") || lower.includes("tracking")) return "analytics setup";
          // Fallback: first few words
          return f.split(/[—\-,.]/).map(s => s.trim())[0]?.slice(0, 30) || f.slice(0, 25);
        }).filter((v, i, a) => a.indexOf(v) === i).join(", ")
      : "";

    const hasLowReviews = (lead.google_rating != null && lead.google_rating < 4.0) ||
      (lead.yelp_rating != null && lead.yelp_rating < 4.0);

    let subject: string;
    let body: string;

    if (!lead.has_website) {
      // ── NO WEBSITE ──
      subject = `${biz} — customers can't find you online`;
      body = `Hi ${recipientName},

I was looking into ${category} businesses in ${city} and noticed ${biz} doesn't have a website yet.

That means when someone nearby searches for a ${category}, they're finding your competitors instead. Every day without a site is leads going somewhere else.

We build and manage websites for local businesses — done-for-you, starting at $299/mo. No upfront cost.

Worth a 10-minute call to see if it makes sense?

— ${sender}${phone ? `\n${phone}` : ""}`;
    } else if (hasLowReviews && !findingsBullets) {
      // ── LOW REVIEWS (no audit data) ──
      const rating = lead.google_rating || lead.yelp_rating || "low";
      subject = `${biz}'s ${rating}-star rating is costing you`;
      body = `Hi ${recipientName},

I noticed ${biz} has a ${rating}-star rating on Google. For ${category} businesses, anything under 4.2 means most people scroll right past.

The fix starts with your website — making it easy for happy customers to leave reviews, showing off your best work, and building trust before they call.

I've got a few ideas specific to ${biz}. Can I send you a quick breakdown?

— ${sender}${phone ? `\n${phone}` : ""}`;
    } else {
      // ── AUDIT HOOK (default) ──
      const scoreText = lead.website_audit_score != null
        ? `I ran a quick audit on ${biz}'s website and it scored ${lead.website_audit_score}/100. A few things stood out:`
        : `I took a look at ${biz}'s website and noticed a few things:`;
      subject = lead.website_audit_score != null
        ? `Quick question about ${biz}'s website`
        : `Noticed something on ${biz}'s website`;
      const breakdownLine = findingsKeywords
        ? `I put together a full breakdown with the exact fixes (${findingsKeywords}, etc.).`
        : `I put together a full breakdown with the exact fixes.`;
      body = `Hi ${recipientName},

${scoreText}

${findingsBullets || "There are small technical issues that could be quietly costing you customers."}

These are the kinds of things that quietly push potential ${city} customers to competing ${category} companies without you ever knowing.

${breakdownLine}

Would you like me to send it over?

No cost and no pitch — just figured you might find it useful.

Best,
${sender}${phone ? `\n${phone}` : ""}`;
    }

    return `To: ${recipientEmail}
Subject: ${subject}

${body}`;
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
                    {isEditingDetails ? (
                      <input
                        value={editForm.business_name}
                        onChange={(e) => setEditForm({ ...editForm, business_name: e.target.value })}
                        className="text-xl font-semibold text-warroom-text mb-2 bg-warroom-bg border border-warroom-border rounded px-2 py-1 w-full focus:outline-none focus:border-warroom-accent"
                      />
                    ) : (
                      <h2 className="text-xl font-semibold text-warroom-text mb-2">
                        {lead.business_name}
                      </h2>
                    )}
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
                      onClick={() => {
                        if (isEditingDetails) { handleSaveDetails(); }
                        else { setIsEditingDetails(true); }
                      }}
                      disabled={savingDetails}
                      className="flex items-center gap-1 px-2 py-1.5 text-warroom-muted hover:text-warroom-accent transition rounded-lg text-xs"
                      title={isEditingDetails ? "Save changes" : "Edit details"}
                    >
                      {savingDetails ? <Loader2 size={14} className="animate-spin" /> : isEditingDetails ? <Check size={14} /> : <Pencil size={14} />}
                    </button>
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
                {isEditingDetails ? (
                  <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                    <div className="flex items-center gap-2">
                      <MapPin size={14} className="text-warroom-muted shrink-0" />
                      <input value={editForm.address} onChange={(e) => setEditForm({ ...editForm, address: e.target.value })} placeholder="Address" className="bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text w-full focus:outline-none focus:border-warroom-accent" />
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin size={14} className="text-warroom-muted shrink-0 opacity-0" />
                      <input value={editForm.city} onChange={(e) => setEditForm({ ...editForm, city: e.target.value })} placeholder="City" className="bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text w-full focus:outline-none focus:border-warroom-accent" />
                      <input value={editForm.state} onChange={(e) => setEditForm({ ...editForm, state: e.target.value })} placeholder="ST" className="bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text w-16 focus:outline-none focus:border-warroom-accent" />
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone size={14} className="text-warroom-muted shrink-0" />
                      <input value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} placeholder="Phone" className="bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text w-full focus:outline-none focus:border-warroom-accent" />
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail size={14} className="text-warroom-muted shrink-0" />
                      <input value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} placeholder="Email" className="bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text w-full focus:outline-none focus:border-warroom-accent" />
                    </div>
                    <div className="flex items-center gap-2 col-span-2">
                      <Globe size={14} className="text-warroom-muted shrink-0" />
                      <input value={editForm.website} onChange={(e) => setEditForm({ ...editForm, website: e.target.value })} placeholder="Website URL" className="bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text w-full focus:outline-none focus:border-warroom-accent" />
                    </div>
                  </div>
                ) : (
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
                )}

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
              <div className="space-y-6">
                {/* ── Audit Lite Section ──────────────────────────────── */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-warroom-text flex items-center gap-2">
                      <BarChart3 size={16} className="text-warroom-accent" />
                      Audit Lite
                    </h3>
                    <button
                      onClick={downloadAuditPdf}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-warroom-text hover:bg-warroom-bg border border-warroom-border transition"
                    >
                      <Download size={12} />
                      Download PDF
                    </button>
                  </div>

                  {/* Score Tiles */}
                  <div className="grid grid-cols-2 gap-3">
                    {/* Website Score */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Globe size={14} className="text-warroom-muted" />
                        <span className="text-[10px] font-medium text-warroom-muted uppercase tracking-wider">Website Score</span>
                      </div>
                      {lead.website_audit_score != null ? (
                        <div className="flex items-end gap-2">
                          <span className="text-2xl font-bold text-warroom-text">{lead.website_audit_score}</span>
                          <span className="text-xs text-warroom-muted mb-1">/100</span>
                          {lead.website_audit_grade && (
                            <span className={`ml-auto text-lg font-bold px-2 py-0.5 rounded-lg ${
                              lead.website_audit_grade === "A" ? "bg-green-500/20 text-green-400" :
                              lead.website_audit_grade === "B" ? "bg-blue-500/20 text-blue-400" :
                              lead.website_audit_grade === "C" ? "bg-yellow-500/20 text-yellow-400" :
                              lead.website_audit_grade === "D" ? "bg-orange-500/20 text-orange-400" :
                              "bg-red-500/20 text-red-400"
                            }`}>{lead.website_audit_grade}</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-sm text-warroom-muted">No data</span>
                      )}
                    </div>

                    {/* Google Rating */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Star size={14} className="text-yellow-400" />
                        <span className="text-[10px] font-medium text-warroom-muted uppercase tracking-wider">Google Rating</span>
                      </div>
                      {lead.google_rating != null ? (
                        <div className="flex items-end gap-2">
                          <span className="text-2xl font-bold text-warroom-text">{lead.google_rating}</span>
                          <span className="text-xs text-warroom-muted mb-1">/ 5</span>
                          <div className="ml-auto flex items-center gap-0.5">
                            {[1, 2, 3, 4, 5].map((s) => (
                              <Star
                                key={s}
                                size={12}
                                className={s <= Math.round(lead.google_rating!) ? "text-yellow-400 fill-yellow-400" : "text-warroom-border"}
                              />
                            ))}
                          </div>
                        </div>
                      ) : (
                        <span className="text-sm text-warroom-muted">No data</span>
                      )}
                    </div>

                    {/* Yelp Rating */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Star size={14} className="text-red-400" />
                        <span className="text-[10px] font-medium text-warroom-muted uppercase tracking-wider">Yelp Rating</span>
                      </div>
                      {lead.yelp_rating != null ? (
                        <div className="flex items-end gap-2">
                          <span className="text-2xl font-bold text-warroom-text">{lead.yelp_rating}</span>
                          <span className="text-xs text-warroom-muted mb-1">/ 5</span>
                          <span className="ml-auto text-xs text-warroom-muted">{lead.yelp_reviews_count} reviews</span>
                        </div>
                      ) : (
                        <span className="text-sm text-warroom-muted">No data</span>
                      )}
                    </div>

                    {/* Lead Score */}
                    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Target size={14} className="text-warroom-accent" />
                        <span className="text-[10px] font-medium text-warroom-muted uppercase tracking-wider">Lead Score</span>
                      </div>
                      <div className="flex items-end gap-2">
                        <span className="text-2xl font-bold text-warroom-text">{lead.lead_score}</span>
                        <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full border ${TIER_COLORS[lead.lead_tier] || TIER_COLORS.unscored}`}>
                          {lead.lead_tier}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Audit Flags */}
                  {lead.audit_lite_flags.length > 0 && (
                    <div>
                      <h4 className="text-[10px] font-medium text-warroom-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <AlertCircle size={12} />
                        Audit Flags
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {lead.audit_lite_flags.map((flag) => (
                          <span
                            key={flag}
                            className="text-[11px] px-2.5 py-1 rounded-full font-medium bg-orange-500/15 text-orange-400 border border-orange-500/20"
                          >
                            {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Top Fixes */}
                  {lead.website_audit_top_fixes && lead.website_audit_top_fixes.length > 0 && (
                    <div>
                      <h4 className="text-[10px] font-medium text-warroom-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <Wrench size={12} />
                        Top Fixes
                      </h4>
                      <ul className="space-y-1.5">
                        {lead.website_audit_top_fixes.map((fix, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-warroom-text">
                            <span className="text-warroom-accent font-bold mt-0.5 shrink-0">{i + 1}.</span>
                            <span>{fix}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Audit Summary */}
                  {lead.website_audit_summary && (
                    <div className="p-3 bg-warroom-bg rounded-lg border border-warroom-border">
                      <p className="text-xs text-warroom-muted leading-relaxed">{lead.website_audit_summary}</p>
                    </div>
                  )}
                </div>

                {/* ── Divider ────────────────────────────────────────── */}
                <div className="border-t border-warroom-border" />

                {/* ── Deep AI Audit Section ───────────────────────────── */}
                <div className="space-y-4">
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
                </div>

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

                {/* No deep audit yet — prompt user */}
                {!deepAudit && !auditLoading && (
                  <div className="p-4 bg-warroom-bg rounded-lg border border-warroom-border text-center">
                    <p className="text-xs text-warroom-muted">No deep audit has been run yet.</p>
                    <p className="text-[10px] text-warroom-accent mt-1">Click &quot;Run Deep Audit&quot; for a comprehensive AI-powered analysis →</p>
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
                {/* Pop-out button */}
                <div className="flex justify-end">
                  <button
                    onClick={() => setIsPopoutOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-warroom-muted hover:text-warroom-accent border border-warroom-border rounded-lg transition"
                    title="Open in larger view"
                  >
                    <Maximize2 size={12} />
                    Pop Out
                  </button>
                </div>
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

                <h3 className="text-sm font-semibold text-warroom-text">Log Activity</h3>

                {/* Call / Email toggle */}
                <div className="flex gap-1 p-1 bg-warroom-bg rounded-lg border border-warroom-border">
                  <button
                    onClick={() => setContactForm(prev => ({ ...prev, contact_method: "call", outcome: "" }))}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${contactForm.contact_method === "call" ? "bg-warroom-accent text-white" : "text-warroom-muted hover:text-warroom-text"}`}
                  >
                    <Phone size={12} /> Call
                  </button>
                  <button
                    onClick={() => setContactForm(prev => ({ ...prev, contact_method: "email", outcome: "" }))}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${contactForm.contact_method === "email" ? "bg-warroom-accent text-white" : "text-warroom-muted hover:text-warroom-text"}`}
                  >
                    <Mail size={12} /> Email
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">{contactForm.contact_method === "email" ? "Sent By" : "Contacted By"}</label>
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
                    <label className="block text-xs font-medium text-warroom-muted mb-1">{contactForm.contact_method === "email" ? "Recipient" : "Who Answered"}</label>
                    <input
                      value={contactForm.who_answered}
                      onChange={(e) => setContactForm(prev => ({ ...prev, who_answered: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder={contactForm.contact_method === "email" ? "Email recipient" : "Contact person"}
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
                      {(contactForm.contact_method === "email" ? EMAIL_OUTCOMES : CALL_OUTCOMES).map(({ value, label }) => (
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
                    placeholder={contactForm.contact_method === "email" ? "Email subject, body summary, follow-up plan..." : "Call notes, follow-up actions, etc."}
                  />
                </div>

                <button
                  onClick={handleContactSubmit}
                  disabled={saving}
                  className="w-full px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? "Saving..." : contactForm.contact_method === "email" ? "Log Email" : "Log Call"}
                </button>

                {/* Contact History */}
                {lead.contact_history.length > 0 && (
                  <div className="mt-6">
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">Activity History</h4>
                    <div className="space-y-2">
                      {lead.contact_history.map((contact: any, index) => {
                        const dateStr = contact.date || contact.contacted_at;
                        const byStr = contact.by || contact.contacted_by || "";
                        const method = contact.method || "call";
                        const parsed = dateStr ? new Date(dateStr) : null;
                        const formattedDate = parsed && !isNaN(parsed.getTime())
                          ? parsed.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })
                          : "Unknown date";
                        return (
                        <div key={index} className="p-3 bg-warroom-bg rounded-lg">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-warroom-muted flex items-center gap-1.5">
                              {method === "email" ? <Mail size={10} /> : <Phone size={10} />}
                              {byStr} • {formattedDate}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              method === "email" ? "bg-blue-500/20 text-blue-400" : "bg-warroom-border"
                            }`}>
                              {(contact.outcome || "").replace(/_/g, " ")}
                            </span>
                          </div>
                          {(contact.notes || contact.who_answered) && (
                            <p className="text-xs text-warroom-text">
                              {contact.who_answered && <span className="text-warroom-muted">{method === "email" ? "To: " : "Spoke with: "}{contact.who_answered} · </span>}
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

      {/* Pop-out Modal */}
      {isPopoutOpen && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setIsPopoutOpen(false)} />
          <div className="relative w-[90vw] max-w-[1200px] h-[85vh] bg-warroom-surface border border-warroom-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border shrink-0">
              <div>
                <h2 className="text-lg font-semibold text-warroom-text">{lead.business_name}</h2>
                <p className="text-xs text-warroom-muted">{lead.phone} · {lead.emails?.[0] || "No email"} · {lead.city}, {lead.state}</p>
              </div>
              <button onClick={() => setIsPopoutOpen(false)} className="p-2 text-warroom-muted hover:text-warroom-text transition rounded-lg hover:bg-warroom-border/30">
                <Minimize2 size={18} />
              </button>
            </div>
            {/* Modal body — 3 columns */}
            <div className="flex-1 overflow-hidden grid grid-cols-3 divide-x divide-warroom-border">
              {/* Column 1: Contact Form */}
              <div className="overflow-y-auto p-5 space-y-4">
                <h3 className="text-sm font-semibold text-warroom-text mb-3">Log Activity</h3>
                <div className="flex gap-1 p-1 bg-warroom-bg rounded-lg border border-warroom-border mb-3">
                  <button onClick={() => setContactForm(prev => ({ ...prev, contact_method: "call", outcome: "" }))} className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${contactForm.contact_method === "call" ? "bg-warroom-accent text-white" : "text-warroom-muted hover:text-warroom-text"}`}><Phone size={12} /> Call</button>
                  <button onClick={() => setContactForm(prev => ({ ...prev, contact_method: "email", outcome: "" }))} className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${contactForm.contact_method === "email" ? "bg-warroom-accent text-white" : "text-warroom-muted hover:text-warroom-text"}`}><Mail size={12} /> Email</button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">{contactForm.contact_method === "email" ? "Sent By" : "Contacted By"}</label>
                    <select value={contactForm.contacted_by} onChange={(e) => setContactForm(prev => ({ ...prev, contacted_by: e.target.value }))} className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer" style={{ colorScheme: "dark" }}>
                      <option value="">Select...</option>
                      {teamMembers.map((u) => (<option key={u.id} value={u.name}>{u.name}</option>))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Who Answered</label>
                    <input value={contactForm.who_answered} onChange={(e) => setContactForm(prev => ({ ...prev, who_answered: e.target.value }))} className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" placeholder="Contact person" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Owner Name</label>
                    <input value={contactForm.owner_name} onChange={(e) => setContactForm(prev => ({ ...prev, owner_name: e.target.value }))} className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" placeholder="Business owner" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">Outcome</label>
                    <select value={contactForm.outcome} onChange={(e) => setContactForm(prev => ({ ...prev, outcome: e.target.value }))} className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" style={{ colorScheme: "dark" }}>
                      <option value="">Select outcome...</option>
                      {(contactForm.contact_method === "email" ? EMAIL_OUTCOMES : CALL_OUTCOMES).map(({ value, label }) => (<option key={value} value={value}>{label}</option>))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-warroom-muted mb-1">Notes</label>
                  <textarea value={contactForm.notes} onChange={(e) => setContactForm(prev => ({ ...prev, notes: e.target.value }))} rows={6} className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none" placeholder={contactForm.contact_method === "email" ? "Email subject, body summary, follow-up plan..." : "Call notes, follow-up actions, etc."} />
                </div>
                <button onClick={handleContactSubmit} disabled={saving} className="w-full px-4 py-2.5 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2">
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? "Saving..." : contactForm.contact_method === "email" ? "Log Email" : "Log Call"}
                </button>
                {/* Activity History */}
                {lead.contact_history.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-medium text-warroom-muted mb-2">History ({lead.contact_history.length})</h4>
                    <div className="space-y-2 max-h-[200px] overflow-y-auto">
                      {lead.contact_history.map((contact: any, index) => {
                        const dateStr = contact.date || contact.contacted_at;
                        const byStr = contact.by || contact.contacted_by || "";
                        const m = contact.method || "call";
                        const parsed = dateStr ? new Date(dateStr) : null;
                        const formattedDate = parsed && !isNaN(parsed.getTime()) ? parsed.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "Unknown";
                        return (
                          <div key={index} className="p-2 bg-warroom-bg rounded-lg text-xs">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-warroom-muted flex items-center gap-1">{m === "email" ? <Mail size={10} /> : <Phone size={10} />} {byStr} · {formattedDate}</span>
                              <span className={`px-1.5 py-0.5 rounded-full ${m === "email" ? "bg-blue-500/20 text-blue-400" : "bg-warroom-border"}`}>{(contact.outcome || "").replace(/_/g, " ")}</span>
                            </div>
                            {contact.notes && <p className="text-warroom-text">{contact.notes}</p>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Column 2: Call Script */}
              <div className="overflow-y-auto p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-warroom-text">Cold Call Script</h3>
                  <button onClick={() => copyToClipboard(generateColdCallScript())} className="px-2 py-1 text-xs bg-warroom-border/50 hover:bg-warroom-border transition rounded flex items-center gap-1"><Copy size={12} /> Copy</button>
                </div>
                <pre className="text-xs text-warroom-text whitespace-pre-wrap font-mono p-4 bg-warroom-bg rounded-lg border border-warroom-border">{generateColdCallScript()}</pre>
              </div>

              {/* Column 3: Email Template */}
              <div className="overflow-y-auto p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-warroom-text">Cold Email Template</h3>
                  <button onClick={() => copyToClipboard(generateColdEmail())} className="px-2 py-1 text-xs bg-warroom-border/50 hover:bg-warroom-border transition rounded flex items-center gap-1"><Copy size={12} /> Copy</button>
                </div>
                <pre className="text-xs text-warroom-text whitespace-pre-wrap font-mono p-4 bg-warroom-bg rounded-lg border border-warroom-border">{generateColdEmail()}</pre>
              </div>
            </div>
          </div>
        </div>
      )}

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