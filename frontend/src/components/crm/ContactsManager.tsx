"use client";

import { useState, useEffect } from "react";
import { Users, Phone, Search, Filter, X, Loader2, UserPlus, Mail } from "lucide-react";
import LeadDrawer, { LeadFull } from "../leadgen/LeadDrawer";
import { API, authFetch } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";
import EmptyState from "@/components/ui/EmptyState";


interface Contact {
  id: number;
  business_name: string;
  contacted_by: string;
  contacted_at: string;
  contact_outcome: string;
  contact_notes: string;
  city: string | null;
  state: string | null;
  phone: string | null;
  website: string | null;
  lead_score: number;
  lead_tier: string;
}

interface CRMContact {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  company: string | null;
  source: string;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
}

// TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
const MOCK_CRM_CONTACTS: CRMContact[] = [
  { id: 1, name: "John Smith", email: "john@acmecorp.com", phone: "(512) 555-0142", company: "Acme Corp", source: "leadgen", assigned_to: "Edwin", created_at: "2026-02-20T10:00:00Z", updated_at: "2026-03-01T14:30:00Z" },
  { id: 2, name: "Sarah Chen", email: "sarah@techstart.io", phone: "(415) 555-0198", company: "TechStart Inc", source: "referral", assigned_to: "Edwin", created_at: "2026-02-15T09:00:00Z", updated_at: "2026-03-03T11:00:00Z" },
  { id: 3, name: "Mike Johnson", email: "mike@blueskymedia.com", phone: "(512) 555-0234", company: "BlueSky Media", source: "website", assigned_to: null, created_at: "2026-01-10T08:00:00Z", updated_at: "2026-02-28T16:00:00Z" },
  { id: 4, name: "Lisa Park", email: "lisa@greenleaf.org", phone: "(512) 555-0311", company: "GreenLeaf Organics", source: "leadgen", assigned_to: "Edwin", created_at: "2026-02-01T12:00:00Z", updated_at: "2026-03-05T10:00:00Z" },
  { id: 5, name: "David Wilson", email: "david@novafinancial.com", phone: "(212) 555-0455", company: "Nova Financial", source: "cold_call", assigned_to: "Edwin", created_at: "2026-01-15T14:00:00Z", updated_at: "2026-03-02T09:00:00Z" },
  { id: 6, name: "Emma Davis", email: "emma@meridiangroup.com", phone: null, company: "Meridian Group", source: "referral", assigned_to: null, created_at: "2026-01-05T11:00:00Z", updated_at: "2026-03-04T15:00:00Z" },
];

// TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
const MOCK_CONTACT_HISTORY: Contact[] = [
  { id: 1, business_name: "Joe's Plumbing & Heating", contacted_by: "Edwin", contacted_at: "2026-03-05T10:30:00Z", contact_outcome: "follow_up", contact_notes: "Interested in website redesign, scheduling follow-up call next week", city: "Austin", state: "TX", phone: "(512) 555-0142", website: "https://joesplumbing.com", lead_score: 85, lead_tier: "hot" },
  { id: 2, business_name: "Bright Spark Electric", contacted_by: "Edwin", contacted_at: "2026-03-04T14:00:00Z", contact_outcome: "won", contact_notes: "Signed contract for website + SEO package", city: "Austin", state: "TX", phone: "(512) 555-0198", website: "https://brightspark.com", lead_score: 72, lead_tier: "warm" },
  { id: 3, business_name: "Cool Breeze HVAC", contacted_by: "Edwin", contacted_at: "2026-03-03T09:15:00Z", contact_outcome: "no_answer", contact_notes: "Left voicemail, will try again Thursday", city: "Round Rock", state: "TX", phone: "(512) 555-0234", website: null, lead_score: 91, lead_tier: "hot" },
  { id: 4, business_name: "Green Thumb Landscaping", contacted_by: "Edwin", contacted_at: "2026-03-02T16:00:00Z", contact_outcome: "callback", contact_notes: "Owner busy, asked to call back Friday afternoon", city: "Austin", state: "TX", phone: "(512) 555-0311", website: "https://greenthumbatx.com", lead_score: 88, lead_tier: "hot" },
  { id: 5, business_name: "Sunrise Dental Care", contacted_by: "Edwin", contacted_at: "2026-03-01T11:00:00Z", contact_outcome: "lost", contact_notes: "Already has a web agency, not interested", city: "Cedar Park", state: "TX", phone: "(512) 555-0455", website: "https://sunrisedental.com", lead_score: 45, lead_tier: "cold" },
];

const OUTCOME_COLORS: Record<string, string> = {
  won: "bg-green-500/20 text-green-400",
  lost: "bg-red-500/20 text-red-400",
  follow_up: "bg-blue-500/20 text-blue-400",
  no_answer: "bg-gray-500/20 text-gray-400",
  callback: "bg-yellow-500/20 text-yellow-400",
};

export default function ContactsManager() {
  const [activeTab, setActiveTab] = useState<"crm" | "activity" | "history">("crm");
  const [crmContacts, setCrmContacts] = useState<CRMContact[]>([]);
  const [contactHistory, setContactHistory] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [outcomeFilter, setOutcomeFilter] = useState("");
  const [contactedByFilter, setContactedByFilter] = useState("");
  const [selectedLead, setSelectedLead] = useState<LeadFull | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadCrmContacts = async () => {
    try {
      const response = await authFetch(`${API}/api/crm/contacts`);
      if (response.ok) {
        const data = await response.json();
        setCrmContacts(data);
      } else {
        // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
        console.error("Failed to load CRM contacts:", response.status);
        setCrmContacts(MOCK_CRM_CONTACTS);
      }
    } catch (error) {
      // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
      console.error("Failed to load CRM contacts:", error);
      setCrmContacts(MOCK_CRM_CONTACTS);
    }
  };

  const loadContactHistory = async () => {
    try {
      const params = new URLSearchParams();
      if (outcomeFilter) params.set("outcome", outcomeFilter);
      if (contactedByFilter) params.set("contacted_by", contactedByFilter);

      const response = await authFetch(`${API}/api/leadgen/contacts?${params}`);
      if (response.ok) {
        const data = await response.json();
        setContactHistory(data);
      } else {
        // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
        console.error("Failed to load contact history:", response.status);
        setContactHistory(MOCK_CONTACT_HISTORY);
      }
    } catch (error) {
      // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
      console.error("Failed to load contact history:", error);
      setContactHistory(MOCK_CONTACT_HISTORY);
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([
      loadCrmContacts(),
      activeTab === "history" ? loadContactHistory() : Promise.resolve()
    ]).finally(() => setLoading(false));
  }, [activeTab, outcomeFilter, contactedByFilter]);

  const handleContactClick = async (contact: Contact) => {
    try {
      // Fetch full lead data
      const response = await authFetch(`${API}/api/leadgen/leads/${contact.id}`);
      if (response.ok) {
        const fullLead: LeadFull = await response.json();
        setSelectedLead(fullLead);
        setIsDrawerOpen(true);
      }
    } catch (error) {
      console.error("Failed to fetch lead details:", error);
    }
  };

  const handleLeadUpdate = (updatedLead: LeadFull) => {
    setSelectedLead(updatedLead);
    // Refresh contact history if on that tab
    if (activeTab === "history") {
      loadContactHistory();
    }
  };

  const closeDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedLead(null);
  };

  const clearFilters = () => {
    setOutcomeFilter("");
    setContactedByFilter("");
  };

  const uniqueContactedBy = Array.from(new Set(contactHistory.map(c => c.contacted_by).filter(Boolean))) as string[];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Users size={16} />
          Contacts
        </h2>
        <button className="flex items-center gap-2 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition">
          <UserPlus size={14} />
          Add Contact
        </button>
      </div>

      {/* Tabs */}
      <div className="flex-shrink-0 border-b border-warroom-border">
        <div className="flex px-6">
          {[
            { id: "crm", label: "CRM Contacts", icon: Users },
            { id: "activity", label: "Activity", icon: Mail },
            { id: "history", label: "Contact History", icon: Phone },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition border-b-2 ${
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

      <div className="flex-1 overflow-y-auto p-6">
        {/* CRM Contacts Tab */}
        {activeTab === "crm" && (
          <div>
            {!loading && crmContacts.length > 0 && (
              <div className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-warroom-border bg-warroom-bg">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Name</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Email</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Company</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Phone</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Source</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Assigned To</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {crmContacts.map((contact) => (
                      <tr key={contact.id} className="border-b border-warroom-border/50 hover:bg-warroom-border/20 cursor-pointer">
                        <td className="px-4 py-3">
                          <p className="font-medium text-warroom-text">{contact.name}</p>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-warroom-text">{contact.email}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-warroom-muted">{contact.company || "—"}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-warroom-muted">{contact.phone || "—"}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs px-2 py-1 bg-warroom-border/20 text-warroom-muted rounded-full">
                            {contact.source}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-warroom-muted">{contact.assigned_to || "Unassigned"}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-warroom-muted text-xs">
                            {new Date(contact.created_at).toLocaleDateString()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {!loading && crmContacts.length === 0 && (
              <EmptyState
                icon={<Users size={40} />}
                title="No contacts yet"
                description="Add contacts manually or import them from your lead generation pipeline."
              />
            )}
          </div>
        )}

        {/* Activity Tab */}
        {activeTab === "activity" && (
          <ActivityList contactId={selectedLead?.id} />
        )}

        {/* Contact History Tab */}
        {activeTab === "history" && (
          <div>
            {/* Filters */}
            <div className="flex items-center gap-3 mb-4">
              <div className="text-xs text-warroom-muted font-medium">Filters:</div>
              
              {/* Outcome Filter */}
              <select
                value={outcomeFilter}
                onChange={(e) => setOutcomeFilter(e.target.value)}
                className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
                style={{ colorScheme: "dark" }}
              >
                <option value="">All Outcomes</option>
                <option value="won">Won</option>
                <option value="lost">Lost</option>
                <option value="follow_up">Follow Up</option>
                <option value="no_answer">No Answer</option>
                <option value="callback">Callback</option>
              </select>

              {/* Contacted By Filter */}
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
                <input
                  value={contactedByFilter}
                  onChange={(e) => setContactedByFilter(e.target.value)}
                  placeholder="Filter by contacted by..."
                  className="bg-warroom-surface border border-warroom-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
                />
              </div>

              {/* Contacted By Dropdown (alternative) */}
              {uniqueContactedBy.length > 0 && (
                <select
                  value={contactedByFilter}
                  onChange={(e) => setContactedByFilter(e.target.value)}
                  className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
                  style={{ colorScheme: "dark" }}
                >
                  <option value="">All Team Members</option>
                  {uniqueContactedBy.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              )}

              {/* Clear Filters */}
              {(outcomeFilter || contactedByFilter) && (
                <button
                  onClick={clearFilters}
                  className="text-[10px] text-warroom-muted hover:text-warroom-text flex items-center gap-1 transition"
                >
                  <X size={10} /> Clear
                </button>
              )}
            </div>

            {/* Contact History Table */}
            {!loading && contactHistory.length > 0 && (
              <div className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-warroom-border bg-warroom-bg">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Business</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Contacted By</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Date</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Outcome</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contactHistory.map((contact) => (
                      <tr 
                        key={contact.id}
                        className="border-b border-warroom-border/50 hover:bg-warroom-border/20 cursor-pointer"
                        onClick={() => handleContactClick(contact)}
                      >
                        <td className="px-4 py-3">
                          <p className="font-medium text-warroom-text">{contact.business_name}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-warroom-muted">
                              {[contact.city, contact.state].filter(Boolean).join(", ")}
                            </span>
                            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                              contact.lead_tier === "hot" ? "bg-red-500/20 text-red-400" :
                              contact.lead_tier === "warm" ? "bg-orange-500/20 text-orange-400" :
                              contact.lead_tier === "cold" ? "bg-blue-500/20 text-blue-400" :
                              "bg-warroom-border/20 text-warroom-muted"
                            }`}>
                              {contact.lead_tier}
                            </span>
                            <span className="text-xs text-warroom-muted">
                              Score: {contact.lead_score}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-warroom-text">{contact.contacted_by}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-warroom-muted text-xs">
                            {new Date(contact.contacted_at).toLocaleDateString()}
                          </span>
                          <div className="text-[10px] text-warroom-muted/70 mt-0.5">
                            {new Date(contact.contacted_at).toLocaleTimeString([], { 
                              hour: "2-digit", 
                              minute: "2-digit" 
                            })}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                            OUTCOME_COLORS[contact.contact_outcome] || "bg-warroom-border/20 text-warroom-muted"
                          }`}>
                            {contact.contact_outcome?.replace("_", " ") || "Unknown"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-xs text-warroom-muted max-w-xs truncate">
                            {contact.contact_notes || "No notes"}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Empty State */}
            {!loading && contactHistory.length === 0 && (
              <EmptyState
                icon={<Phone size={40} />}
                title="No contacted businesses found"
                description="Contact history will appear here once you reach out to leads."
                action={
                  (outcomeFilter || contactedByFilter)
                    ? { label: "Clear Filters", onClick: clearFilters }
                    : undefined
                }
              />
            )}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <LoadingState message="Loading contacts..." />
        )}
      </div>

      {/* Lead Drawer */}
      <LeadDrawer
        lead={selectedLead}
        isOpen={isDrawerOpen}
        onClose={closeDrawer}
        onUpdate={handleLeadUpdate}
      />
    </div>
  );
}

function ActivityList({ contactId }: { contactId?: number }) {
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!contactId) { setLoading(false); return; }
    authFetch(`${API}/api/crm/activities?person_id=${contactId}&limit=50`)
      .then(r => r.ok ? r.json() : [])
      .then(setActivities)
      .catch(() => setActivities([]))
      .finally(() => setLoading(false));
  }, [contactId, API]);

  if (loading) return <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-5 w-5 border-2 border-warroom-accent border-t-transparent" /></div>;
  if (activities.length === 0) return <div className="text-center py-8 text-warroom-muted text-xs">No activities for this contact yet</div>;

  const typeIcons: Record<string, string> = { call: "📞", meeting: "👥", note: "📝", task: "✅", email: "📧", lunch: "☕" };

  return (
    <div className="divide-y divide-warroom-border">
      {activities.map((a: any) => (
        <div key={a.id} className="py-2 flex items-start gap-3">
          <span className="text-base">{typeIcons[a.type] || "📋"}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-warroom-text">{a.title || a.type}</span>
              {a.is_done && <span className="text-[9px] px-1 py-0.5 bg-green-500/10 text-green-400 rounded">Done</span>}
            </div>
            {a.comment && <p className="text-[10px] text-warroom-muted mt-0.5 line-clamp-2">{a.comment}</p>}
            {a.schedule_from && <p className="text-[10px] text-warroom-muted mt-0.5">{new Date(a.schedule_from).toLocaleString()}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}