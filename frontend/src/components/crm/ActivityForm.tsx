"use client";

import { useState, useEffect } from "react";
import { X, Save, Search } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface ActivityFormProps {
  isOpen: boolean;
  onClose: () => void;
  onActivityCreated: (activity: Activity) => void;
}

interface Activity {
  id: number;
  title: string;
  type: string;
  comment: string | null;
  schedule_from: string | null;
  schedule_to: string | null;
  location: string | null;
  is_done: boolean;
  person?: { id: number; name: string };
  deal?: { id: number; title: string };
  created_at: string;
}

interface Person {
  id: number;
  name: string;
  emails: { value: string; label: string }[];
}

interface Deal {
  id: number;
  title: string;
  deal_value: number | null;
}

const ACTIVITY_TYPES = [
  { value: "call", label: "Call" },
  { value: "meeting", label: "Meeting" },
  { value: "note", label: "Note" },
  { value: "task", label: "Task" },
  { value: "email", label: "Email" },
  { value: "lunch", label: "Lunch" },
];

export default function ActivityForm({ isOpen, onClose, onActivityCreated }: ActivityFormProps) {
  const [formData, setFormData] = useState({
    type: "call",
    title: "",
    comment: "",
    schedule_from: "",
    schedule_to: "",
    location: "",
    person_id: "",
    deal_id: "",
  });
  const [saving, setSaving] = useState(false);
  const [people, setPeople] = useState<Person[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [personSearch, setPersonSearch] = useState("");
  const [dealSearch, setDealSearch] = useState("");
  const [showPersonDropdown, setShowPersonDropdown] = useState(false);
  const [showDealDropdown, setShowDealDropdown] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchPeople();
      fetchDeals();
    }
  }, [isOpen]);

  useEffect(() => {
    if (personSearch.length > 0) {
      fetchPeople(personSearch);
    }
  }, [personSearch]);

  useEffect(() => {
    if (dealSearch.length > 0) {
      fetchDeals(dealSearch);
    }
  }, [dealSearch]);

  const fetchPeople = async (search = "") => {
    try {
      const params = search ? `?search=${encodeURIComponent(search)}` : "";
      const response = await fetch(`${API}/api/crm/persons${params}`);
      if (response.ok) {
        const data = await response.json();
        setPeople(data);
      }
    } catch (error) {
      console.error("Failed to fetch people:", error);
    }
  };

  const fetchDeals = async (search = "") => {
    try {
      const params = search ? `?search=${encodeURIComponent(search)}` : "";
      const response = await fetch(`${API}/api/crm/deals${params}`);
      if (response.ok) {
        const data = await response.json();
        setDeals(data);
      }
    } catch (error) {
      console.error("Failed to fetch deals:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const payload = {
        type: formData.type,
        title: formData.title,
        comment: formData.comment || null,
        schedule_from: formData.schedule_from || null,
        schedule_to: formData.schedule_to || null,
        location: formData.location || null,
        person_id: formData.person_id ? parseInt(formData.person_id) : null,
        deal_id: formData.deal_id ? parseInt(formData.deal_id) : null,
      };

      const response = await fetch(`${API}/api/crm/activities`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const newActivity = await response.json();
        onActivityCreated(newActivity);
        resetForm();
      } else {
        console.error("Failed to create activity");
      }
    } catch (error) {
      console.error("Failed to create activity:", error);
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setFormData({
      type: "call",
      title: "",
      comment: "",
      schedule_from: "",
      schedule_to: "",
      location: "",
      person_id: "",
      deal_id: "",
    });
    setPersonSearch("");
    setDealSearch("");
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const selectPerson = (person: Person) => {
    setFormData(prev => ({ ...prev, person_id: person.id.toString() }));
    setPersonSearch(person.name);
    setShowPersonDropdown(false);
  };

  const selectDeal = (deal: Deal) => {
    setFormData(prev => ({ ...prev, deal_id: deal.id.toString() }));
    setDealSearch(deal.title);
    setShowDealDropdown(false);
  };

  const filteredPeople = people.filter(person =>
    person.name.toLowerCase().includes(personSearch.toLowerCase())
  );

  const filteredDeals = deals.filter(deal =>
    deal.title.toLowerCase().includes(dealSearch.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />
      
      {/* Modal */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="relative bg-[#161b22] border border-[#30363d] rounded-lg shadow-2xl w-full max-w-2xl">
          <form onSubmit={handleSubmit}>
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-[#30363d]">
              <h2 className="text-lg font-semibold text-gray-200">Add Activity</h2>
              <button
                type="button"
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-200 transition"
              >
                <X size={20} />
              </button>
            </div>

            {/* Form Content */}
            <div className="p-6 space-y-4">
              {/* Type and Title */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Activity Type
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400"
                    style={{ colorScheme: "dark" }}
                    required
                  >
                    {ACTIVITY_TYPES.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Title
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400"
                    placeholder="Activity title..."
                    required
                  />
                </div>
              </div>

              {/* Comment */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Comment
                </label>
                <textarea
                  value={formData.comment}
                  onChange={(e) => setFormData(prev => ({ ...prev, comment: e.target.value }))}
                  rows={3}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400 resize-none"
                  placeholder="Activity notes or details..."
                />
              </div>

              {/* Schedule Times */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Start Time
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.schedule_from}
                    onChange={(e) => setFormData(prev => ({ ...prev, schedule_from: e.target.value }))}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400"
                    style={{ colorScheme: "dark" }}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    End Time
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.schedule_to}
                    onChange={(e) => setFormData(prev => ({ ...prev, schedule_to: e.target.value }))}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400"
                    style={{ colorScheme: "dark" }}
                  />
                </div>
              </div>

              {/* Location */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400"
                  placeholder="Meeting location or address..."
                />
              </div>

              {/* Link to Person */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Link to Person
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={personSearch}
                    onChange={(e) => {
                      setPersonSearch(e.target.value);
                      setShowPersonDropdown(true);
                    }}
                    onFocus={() => setShowPersonDropdown(true)}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 pr-10 text-gray-200 focus:outline-none focus:border-blue-400"
                    placeholder="Search for a person..."
                  />
                  <Search size={16} className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                </div>
                
                {showPersonDropdown && filteredPeople.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-[#0d1117] border border-[#30363d] rounded-lg shadow-lg max-h-40 overflow-y-auto">
                    {filteredPeople.slice(0, 10).map((person) => (
                      <button
                        key={person.id}
                        type="button"
                        onClick={() => selectPerson(person)}
                        className="w-full text-left px-3 py-2 hover:bg-[#161b22] transition text-gray-200"
                      >
                        <div className="font-medium">{person.name}</div>
                        {person.emails[0] && (
                          <div className="text-xs text-gray-400">{person.emails[0].value}</div>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Link to Deal */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Link to Deal
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={dealSearch}
                    onChange={(e) => {
                      setDealSearch(e.target.value);
                      setShowDealDropdown(true);
                    }}
                    onFocus={() => setShowDealDropdown(true)}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 pr-10 text-gray-200 focus:outline-none focus:border-blue-400"
                    placeholder="Search for a deal..."
                  />
                  <Search size={16} className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                </div>
                
                {showDealDropdown && filteredDeals.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-[#0d1117] border border-[#30363d] rounded-lg shadow-lg max-h-40 overflow-y-auto">
                    {filteredDeals.slice(0, 10).map((deal) => (
                      <button
                        key={deal.id}
                        type="button"
                        onClick={() => selectDeal(deal)}
                        className="w-full text-left px-3 py-2 hover:bg-[#161b22] transition text-gray-200"
                      >
                        <div className="font-medium">{deal.title}</div>
                        {deal.deal_value && (
                          <div className="text-xs text-green-400">
                            ${deal.deal_value.toLocaleString()}
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-[#30363d]">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-gray-400 hover:text-gray-200 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || !formData.title}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    Create Activity
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}