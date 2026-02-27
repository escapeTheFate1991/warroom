"use client";

import { useState, useEffect } from "react";
import { Phone, Search, Filter, X, Loader2 } from "lucide-react";
import LeadDrawer, { LeadFull } from "../leadgen/LeadDrawer";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

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

const OUTCOME_COLORS: Record<string, string> = {
  won: "bg-green-500/20 text-green-400",
  lost: "bg-red-500/20 text-red-400",
  follow_up: "bg-blue-500/20 text-blue-400",
  no_answer: "bg-gray-500/20 text-gray-400",
  callback: "bg-yellow-500/20 text-yellow-400",
};

export default function ContactsPanel() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [outcomeFilter, setOutcomeFilter] = useState("");
  const [contactedByFilter, setContactedByFilter] = useState("");
  const [selectedLead, setSelectedLead] = useState<LeadFull | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadContacts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (outcomeFilter) params.set("outcome", outcomeFilter);
      if (contactedByFilter) params.set("contacted_by", contactedByFilter);

      const response = await fetch(`${API}/api/leadgen/contacts?${params}`);
      if (response.ok) {
        const data = await response.json();
        setContacts(data);
      }
    } catch (error) {
      console.error("Failed to load contacts:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContacts();
  }, [outcomeFilter, contactedByFilter]);

  const handleContactClick = async (contact: Contact) => {
    try {
      // Fetch full lead data
      const response = await fetch(`${API}/api/leadgen/leads/${contact.id}`);
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
    // Refresh contacts list to reflect any changes
    loadContacts();
  };

  const closeDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedLead(null);
  };

  const clearFilters = () => {
    setOutcomeFilter("");
    setContactedByFilter("");
  };

  const uniqueContactedBy = [...new Set(contacts.map(c => c.contacted_by))].filter(Boolean);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3">
        <Phone size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Contacts</h2>
        <div className="text-xs text-warroom-muted">
          {contacts.length} contacted businesses
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
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

        {/* Contacts Table */}
        {!loading && contacts.length > 0 && (
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
                {contacts.map((contact) => (
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

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20 text-warroom-muted">
            <Loader2 size={24} className="animate-spin mr-3" />
            <span className="text-sm">Loading contacts...</span>
          </div>
        )}

        {/* Empty State */}
        {!loading && contacts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
            <Phone size={48} className="mb-4 opacity-20" />
            <p className="text-sm">No contacted businesses found</p>
            {(outcomeFilter || contactedByFilter) && (
              <button
                onClick={clearFilters}
                className="mt-2 text-xs text-warroom-accent hover:underline"
              >
                Clear filters to see all contacts
              </button>
            )}
          </div>
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