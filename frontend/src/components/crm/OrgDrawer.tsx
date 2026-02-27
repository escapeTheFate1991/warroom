"use client";

import { useState, useEffect } from "react";
import { X, Building2, MapPin, Users, DollarSign } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Organization {
  id: number;
  name: string;
  address: any;
  notes?: string;
  created_at: string;
}

interface Person {
  id: number;
  name: string;
  emails: { value: string; label: string }[];
  job_title: string | null;
}

interface Deal {
  id: number;
  title: string;
  deal_value: number | null;
  status: boolean | null;
  stage?: { name: string };
  created_at: string;
}

interface OrgDrawerProps {
  organization: Organization | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdate?: (organization: Organization) => void;
}

export default function OrgDrawer({ organization, isOpen, onClose, onUpdate }: OrgDrawerProps) {
  const [activeTab, setActiveTab] = useState<"people" | "deals" | "notes">("people");
  const [people, setPeople] = useState<Person[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (organization && isOpen) {
      if (activeTab === "people") {
        fetchPeople();
      } else if (activeTab === "deals") {
        fetchDeals();
      }
      setNotes(organization.notes || "");
    }
  }, [organization, isOpen, activeTab]);

  const fetchPeople = async () => {
    if (!organization) return;
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/crm/organizations/${organization.id}/persons`);
      if (response.ok) {
        const data = await response.json();
        setPeople(data);
      }
    } catch (error) {
      console.error("Failed to fetch people:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDeals = async () => {
    if (!organization) return;
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/crm/organizations/${organization.id}/deals`);
      if (response.ok) {
        const data = await response.json();
        setDeals(data);
      }
    } catch (error) {
      console.error("Failed to fetch deals:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !organization) return null;

  const formatAddress = (address: any) => {
    if (!address) return null;
    const parts = [address.street, address.city, address.state, address.zip].filter(Boolean);
    return parts.length > 0 ? parts.join(", ") : null;
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Drawer */}
      <div className="absolute right-0 top-0 h-full w-[600px] bg-[#161b22] border-l border-[#30363d] shadow-2xl">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex-shrink-0 p-6 border-b border-[#30363d]">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <h2 className="text-xl font-semibold text-gray-200 mb-3">
                      {organization.name}
                    </h2>

                    {/* Organization Info */}
                    <div className="space-y-2">
                      {formatAddress(organization.address) && (
                        <div className="flex items-start gap-2 text-sm">
                          <MapPin size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-300">{formatAddress(organization.address)}</span>
                        </div>
                      )}
                    </div>

                    <div className="text-xs text-gray-400 mt-3">
                      Created {new Date(organization.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-200 transition p-2"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex-shrink-0 border-b border-[#30363d]">
            <div className="flex">
              {[
                { id: "people", label: "People", icon: Users },
                { id: "deals", label: "Deals", icon: DollarSign },
                { id: "notes", label: "Notes" },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition border-b-2 ${
                    activeTab === id
                      ? "text-blue-400 border-blue-400 bg-blue-400/5"
                      : "text-gray-400 border-transparent hover:text-gray-200"
                  }`}
                >
                  {Icon && <Icon size={16} />}
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "people" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-200">People</h3>
                </div>

                {loading ? (
                  <div className="text-center py-8 text-gray-400">Loading people...</div>
                ) : people.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">No people found</div>
                ) : (
                  <div className="space-y-3">
                    {people.map((person) => (
                      <div key={person.id} className="p-4 bg-[#0d1117] border border-[#30363d] rounded-lg">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-medium text-gray-200">{person.name}</h4>
                            {person.job_title && (
                              <div className="text-sm text-gray-400 mt-1">
                                {person.job_title}
                              </div>
                            )}
                            {person.emails[0] && (
                              <div className="text-sm text-blue-400 mt-1">
                                {person.emails[0].value}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "deals" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-200">Deals</h3>
                </div>

                {loading ? (
                  <div className="text-center py-8 text-gray-400">Loading deals...</div>
                ) : deals.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">No deals found</div>
                ) : (
                  <div className="space-y-3">
                    {deals.map((deal) => (
                      <div key={deal.id} className="p-4 bg-[#0d1117] border border-[#30363d] rounded-lg">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-medium text-gray-200">{deal.title}</h4>
                            {deal.stage && (
                              <div className="text-xs text-gray-400 mt-1">
                                Stage: {deal.stage.name}
                              </div>
                            )}
                            {deal.status !== null && (
                              <div className={`text-xs mt-1 px-2 py-0.5 rounded-full inline-block ${
                                deal.status === true 
                                  ? "bg-green-500/20 text-green-400"
                                  : deal.status === false
                                  ? "bg-red-500/20 text-red-400"
                                  : "bg-yellow-500/20 text-yellow-400"
                              }`}>
                                {deal.status === true ? "Won" : deal.status === false ? "Lost" : "Open"}
                              </div>
                            )}
                          </div>
                          <div className="text-right">
                            {deal.deal_value && (
                              <div className="text-sm font-medium text-green-400">
                                ${deal.deal_value.toLocaleString()}
                              </div>
                            )}
                            <div className="text-xs text-gray-400">
                              {new Date(deal.created_at).toLocaleDateString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "notes" && (
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-200">Notes</h3>
                
                <div>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={12}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-400 resize-none"
                    placeholder="Add notes about this organization..."
                  />
                </div>

                <button className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition">
                  Save Notes
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}