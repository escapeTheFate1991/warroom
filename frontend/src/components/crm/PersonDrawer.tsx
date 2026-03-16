"use client";

import { useState, useEffect } from "react";
import { X, Mail, Phone, Building2, User, Clock, Plus, CheckCircle2, Circle, Pencil, Save, Loader2 } from "lucide-react";
import { API, authFetch } from "@/lib/api";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import AgentAssignmentCard from "@/components/agents/AgentAssignmentCard";
import CallEvidence, { getCallEvidence } from "./CallEvidence";


interface Person {
  id: number;
  name: string;
  emails: { value: string; label: string }[];
  contact_numbers: { value: string; label: string }[];
  job_title: string | null;
  organization_id: number | null;
  organization?: Organization;
  notes?: string;
  agent_assignments?: AgentAssignmentSummary[];
  created_at: string;
}

interface Organization {
  id: number;
  name: string;
}

interface Deal {
  id: number;
  title: string;
  deal_value: number | null;
  status: boolean | null;
  stage?: { name: string };
  created_at: string;
}

interface Activity {
  id: number;
  title: string;
  type: string;
  comment: string | null;
  additional?: Record<string, unknown> | null;
  location?: string | null;
  schedule_from: string | null;
  schedule_to: string | null;
  is_done: boolean;
  created_at: string;
  deal?: { title: string };
}

interface PersonDrawerProps {
  person: Person | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdate?: (person: Person) => void;
}

const ACTIVITY_TYPES = [
  { value: "call", label: "Call" },
  { value: "meeting", label: "Meeting" },
  { value: "note", label: "Note" },
  { value: "task", label: "Task" },
  { value: "email", label: "Email" },
  { value: "lunch", label: "Lunch" },
];

export default function PersonDrawer({ person, isOpen, onClose, onUpdate }: PersonDrawerProps) {
  const [activeTab, setActiveTab] = useState<"deals" | "activities" | "notes">("activities");
  const [deals, setDeals] = useState<Deal[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "",
    job_title: "",
    emails: [{ label: "primary", value: "" }],
    contact_numbers: [{ label: "primary", value: "" }],
  });
  const [saving, setSaving] = useState(false);
  const [showActivityForm, setShowActivityForm] = useState(false);
  const [activityForm, setActivityForm] = useState({
    type: "call",
    title: "",
    comment: "",
    schedule_from: "",
    schedule_to: "",
  });

  useEffect(() => {
    if (person && isOpen) {
      if (activeTab === "deals") {
        fetchDeals();
      } else if (activeTab === "activities") {
        fetchActivities();
      }
      setNotes(person.notes || "");
      setIsEditing(false);
    }
  }, [person, isOpen, activeTab]);

  const startEditing = () => {
    if (!person) return;
    setEditForm({
      name: person.name || "",
      job_title: person.job_title || "",
      emails: person.emails.length > 0 ? person.emails : [{ label: "primary", value: "" }],
      contact_numbers: person.contact_numbers.length > 0 ? person.contact_numbers : [{ label: "primary", value: "" }],
    });
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
  };

  const handleSaveContact = async () => {
    if (!person) return;
    setSaving(true);
    try {
      const response = await authFetch(`${API}/api/crm/persons/${person.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editForm.name,
          job_title: editForm.job_title || null,
          emails: editForm.emails.filter(e => e.value.trim()),
          contact_numbers: editForm.contact_numbers.filter(p => p.value.trim()),
        }),
      });
      if (response.ok) {
        const updated = await response.json();
        setIsEditing(false);
        if (onUpdate) onUpdate(updated);
      } else {
        console.error("Failed to update contact:", await response.text());
      }
    } catch (error) {
      console.error("Failed to update contact:", error);
    } finally {
      setSaving(false);
    }
  };

  const fetchDeals = async () => {
    if (!person) return;
    setLoading(true);
    try {
      const response = await authFetch(`${API}/api/crm/persons/${person.id}/deals`);
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

  const fetchActivities = async () => {
    if (!person) return;
    setLoading(true);
    try {
      const response = await authFetch(`${API}/api/crm/activities?person_id=${person.id}`);
      if (response.ok) {
        const data = await response.json();
        setActivities(data);
      }
    } catch (error) {
      console.error("Failed to fetch activities:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleActivityDone = async (activityId: number, isDone: boolean) => {
    try {
      const response = await authFetch(`${API}/api/crm/activities/${activityId}/done`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_done: isDone }),
      });
      if (response.ok) {
        setActivities(activities.map(a => 
          a.id === activityId ? { ...a, is_done: isDone } : a
        ));
      }
    } catch (error) {
      console.error("Failed to update activity:", error);
    }
  };

  const createActivity = async () => {
    if (!person) return;
    
    try {
      const response = await authFetch(`${API}/api/crm/activities`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...activityForm,
          person_id: person.id,
        }),
      });
      
      if (response.ok) {
        const newActivity = await response.json();
        setActivities([newActivity, ...activities]);
        setShowActivityForm(false);
        setActivityForm({
          type: "call",
          title: "",
          comment: "",
          schedule_from: "",
          schedule_to: "",
        });
      }
    } catch (error) {
      console.error("Failed to create activity:", error);
    }
  };

  if (!isOpen || !person) return null;

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "call": return <Phone size={14} />;
      case "meeting": return <User size={14} />;
      case "email": return <Mail size={14} />;
      default: return <Clock size={14} />;
    }
  };

  const formatDateTime = (dateTime: string | null) => {
    if (!dateTime) return "";
    return new Date(dateTime).toLocaleString();
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
                    {isEditing ? (
                      <div className="space-y-3">
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">Name</label>
                          <input
                            type="text"
                            value={editForm.name}
                            onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                            className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 text-sm focus:outline-none focus:border-purple-500"
                            placeholder="Contact name"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">Job Title</label>
                          <input
                            type="text"
                            value={editForm.job_title}
                            onChange={(e) => setEditForm(prev => ({ ...prev, job_title: e.target.value }))}
                            className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 text-sm focus:outline-none focus:border-purple-500"
                            placeholder="Job title"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">Emails</label>
                          {editForm.emails.map((email, idx) => (
                            <div key={idx} className="flex gap-2 mb-1">
                              <input
                                type="email"
                                value={email.value}
                                onChange={(e) => {
                                  const updated = [...editForm.emails];
                                  updated[idx] = { ...updated[idx], value: e.target.value };
                                  setEditForm(prev => ({ ...prev, emails: updated }));
                                }}
                                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 text-sm focus:outline-none focus:border-purple-500"
                                placeholder="email@example.com"
                              />
                              {editForm.emails.length > 1 && (
                                <button
                                  onClick={() => setEditForm(prev => ({ ...prev, emails: prev.emails.filter((_, i) => i !== idx) }))}
                                  className="text-gray-500 hover:text-red-400 p-2"
                                ><X size={14} /></button>
                              )}
                            </div>
                          ))}
                          <button
                            onClick={() => setEditForm(prev => ({ ...prev, emails: [...prev.emails, { label: "other", value: "" }] }))}
                            className="text-xs text-purple-400 hover:text-purple-300 mt-1"
                          >+ Add email</button>
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">Phone Numbers</label>
                          {editForm.contact_numbers.map((phone, idx) => (
                            <div key={idx} className="flex gap-2 mb-1">
                              <input
                                type="tel"
                                value={phone.value}
                                onChange={(e) => {
                                  const updated = [...editForm.contact_numbers];
                                  updated[idx] = { ...updated[idx], value: e.target.value };
                                  setEditForm(prev => ({ ...prev, contact_numbers: updated }));
                                }}
                                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 text-sm focus:outline-none focus:border-purple-500"
                                placeholder="(555) 123-4567"
                              />
                              {editForm.contact_numbers.length > 1 && (
                                <button
                                  onClick={() => setEditForm(prev => ({ ...prev, contact_numbers: prev.contact_numbers.filter((_, i) => i !== idx) }))}
                                  className="text-gray-500 hover:text-red-400 p-2"
                                ><X size={14} /></button>
                              )}
                            </div>
                          ))}
                          <button
                            onClick={() => setEditForm(prev => ({ ...prev, contact_numbers: [...prev.contact_numbers, { label: "other", value: "" }] }))}
                            className="text-xs text-purple-400 hover:text-purple-300 mt-1"
                          >+ Add phone</button>
                        </div>
                        <div className="flex gap-2 pt-2">
                          <button
                            onClick={handleSaveContact}
                            disabled={saving || !editForm.name.trim()}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-lg text-sm font-medium transition"
                          >
                            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                            Save
                          </button>
                          <button
                            onClick={cancelEditing}
                            className="px-3 py-1.5 bg-[#21262d] hover:bg-[#30363d] rounded-lg text-sm text-gray-400 transition"
                          >Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-2 mb-2">
                          <h2 className="text-xl font-semibold text-gray-200">
                            {person.name}
                          </h2>
                          <button
                            onClick={startEditing}
                            className="text-gray-500 hover:text-purple-400 transition p-1"
                            title="Edit contact"
                          >
                            <Pencil size={14} />
                          </button>
                        </div>
                    
                        {person.job_title && (
                          <div className="text-sm text-gray-400 mb-2">
                            {person.job_title}
                          </div>
                        )}

                        {person.organization && (
                          <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
                            <Building2 size={14} />
                            {person.organization.name}
                          </div>
                        )}

                        {/* Contact Info */}
                        <div className="space-y-2">
                          {person.emails.map((email, index) => (
                            <div key={index} className="flex items-center gap-2 text-sm">
                              <Mail size={14} className="text-gray-400" />
                              <span className="text-blue-400">{email.value}</span>
                              {email.label && (
                                <span className="text-xs text-gray-500">({email.label})</span>
                              )}
                            </div>
                          ))}
                      
                          {person.contact_numbers.map((phone, index) => (
                            <div key={index} className="flex items-center gap-2 text-sm">
                              <Phone size={14} className="text-gray-400" />
                              <span className="text-gray-300">{phone.value}</span>
                              {phone.label && (
                                <span className="text-xs text-gray-500">({phone.label})</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </>
                    )}
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
                { id: "deals", label: "Deals" },
                { id: "activities", label: "Activities" },
                { id: "notes", label: "Notes" },
              ].map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition border-b-2 ${
                    activeTab === id
                      ? "text-blue-400 border-blue-400 bg-blue-400/5"
                      : "text-gray-400 border-transparent hover:text-gray-200"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="mb-6">
              <AgentAssignmentCard
                entityType="crm_contact"
                entityId={person.id}
                initialAssignments={person.agent_assignments}
                title={`Work contact: ${person.name}`}
              />
            </div>

            {activeTab === "deals" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-200">Associated Deals</h3>
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

            {activeTab === "activities" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-200">Activities</h3>
                  <button
                    onClick={() => setShowActivityForm(!showActivityForm)}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition flex items-center gap-1"
                  >
                    <Plus size={14} />
                    Add Activity
                  </button>
                </div>

                {showActivityForm && (
                  <div className="p-4 bg-[#0d1117] border border-[#30363d] rounded-lg space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">Type</label>
                        <select
                          value={activityForm.type}
                          onChange={(e) => setActivityForm(prev => ({ ...prev, type: e.target.value }))}
                          className="w-full bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-400"
                          style={{ colorScheme: "dark" }}
                        >
                          {ACTIVITY_TYPES.map(type => (
                            <option key={type.value} value={type.value}>{type.label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">Title</label>
                        <input
                          value={activityForm.title}
                          onChange={(e) => setActivityForm(prev => ({ ...prev, title: e.target.value }))}
                          className="w-full bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-400"
                          placeholder="Activity title"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Comment</label>
                      <textarea
                        value={activityForm.comment}
                        onChange={(e) => setActivityForm(prev => ({ ...prev, comment: e.target.value }))}
                        rows={3}
                        className="w-full bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-400 resize-none"
                        placeholder="Activity notes..."
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">Start Time</label>
                        <input
                          type="datetime-local"
                          value={activityForm.schedule_from}
                          onChange={(e) => setActivityForm(prev => ({ ...prev, schedule_from: e.target.value }))}
                          className="w-full bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-400"
                          style={{ colorScheme: "dark" }}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">End Time</label>
                        <input
                          type="datetime-local"
                          value={activityForm.schedule_to}
                          onChange={(e) => setActivityForm(prev => ({ ...prev, schedule_to: e.target.value }))}
                          className="w-full bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-400"
                          style={{ colorScheme: "dark" }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setShowActivityForm(false)}
                        className="px-3 py-1.5 text-gray-400 hover:text-gray-200 transition text-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={createActivity}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition"
                      >
                        Create
                      </button>
                    </div>
                  </div>
                )}

                {loading ? (
                  <div className="text-center py-8 text-gray-400">Loading activities...</div>
                ) : activities.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">No activities found</div>
                ) : (
                  <div className="space-y-3">
                    {activities.map((activity) => (
                      <div key={activity.id} className="p-4 bg-[#0d1117] border border-[#30363d] rounded-lg">
                        <div className="flex items-start gap-3">
                          <button
                            onClick={() => toggleActivityDone(activity.id, !activity.is_done)}
                            className="mt-1 text-gray-400 hover:text-blue-400 transition"
                          >
                            {activity.is_done ? (
                              <CheckCircle2 size={16} className="text-green-400" />
                            ) : (
                              <Circle size={16} />
                            )}
                          </button>
                          
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              {getActivityIcon(activity.type)}
                              <span className="font-medium text-gray-200">{activity.title}</span>
                              <span className="text-xs px-2 py-0.5 bg-gray-700 text-gray-300 rounded-full capitalize">
                                {activity.type}
                              </span>
                            </div>
                            
                            {activity.comment && (
                              <p className="text-sm text-gray-300 mb-2">{activity.comment}</p>
                            )}
                            {activity.type === "call" && (() => {
                              const evidence = getCallEvidence(activity);
                              return <CallEvidence recordingUrl={evidence.recordingUrl} transcript={evidence.transcript} className="mb-2" />;
                            })()}
                            
                            <div className="flex items-center justify-between text-xs text-gray-400">
                              <div>
                                {activity.schedule_from && (
                                  <span>{formatDateTime(activity.schedule_from)}</span>
                                )}
                                {activity.deal && (
                                  <span className="ml-2">• Deal: {activity.deal.title}</span>
                                )}
                              </div>
                              <span>{new Date(activity.created_at).toLocaleDateString()}</span>
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
                    placeholder="Add notes about this person..."
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