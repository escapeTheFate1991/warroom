"use client";

import { useState, useEffect } from "react";
import { Users, Building2, Plus, Search, Filter, Phone, Mail, MapPin } from "lucide-react";
import PersonDrawer from "./PersonDrawer";
import OrgDrawer from "./OrgDrawer";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Person {
  id: number;
  name: string;
  emails: { value: string; label: string }[];
  contact_numbers: { value: string; label: string }[];
  job_title: string | null;
  organization_id: number | null;
  organization?: Organization;
  created_at: string;
}

interface Organization {
  id: number;
  name: string;
  address: any;
  person_count?: number;
  deal_count?: number;
  created_at: string;
}

export default function ContactsManager() {
  const [activeTab, setActiveTab] = useState<"people" | "organizations">("people");
  const [persons, setPersons] = useState<Person[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [personDrawerOpen, setPersonDrawerOpen] = useState(false);
  const [orgDrawerOpen, setOrgDrawerOpen] = useState(false);

  useEffect(() => {
    if (activeTab === "people") {
      fetchPersons();
    } else {
      fetchOrganizations();
    }
  }, [activeTab]);

  const fetchPersons = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/crm/persons`);
      if (response.ok) {
        const data = await response.json();
        setPersons(data);
      }
    } catch (error) {
      console.error("Failed to fetch persons:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrganizations = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/crm/organizations`);
      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
      }
    } catch (error) {
      console.error("Failed to fetch organizations:", error);
    } finally {
      setLoading(false);
    }
  };

  const openPersonDrawer = (person: Person) => {
    setSelectedPerson(person);
    setPersonDrawerOpen(true);
  };

  const openOrgDrawer = (org: Organization) => {
    setSelectedOrg(org);
    setOrgDrawerOpen(true);
  };

  const filteredPersons = persons.filter(person =>
    person.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    person.emails.some(email => email.value.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (person.organization?.name || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredOrganizations = organizations.filter(org =>
    org.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full bg-[#0d1117] text-gray-200">
      {/* Header */}
      <div className="border-b border-[#30363d] p-6">
        <h1 className="text-2xl font-bold mb-4">Contacts</h1>
        
        {/* Tabs */}
        <div className="flex border-b border-[#30363d]">
          <button
            onClick={() => setActiveTab("people")}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition ${
              activeTab === "people"
                ? "border-blue-400 text-blue-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Users size={16} />
            People
          </button>
          <button
            onClick={() => setActiveTab("organizations")}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition ${
              activeTab === "organizations"
                ? "border-blue-400 text-blue-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Building2 size={16} />
            Organizations
          </button>
        </div>
      </div>

      {/* Filters and Actions */}
      <div className="p-6 border-b border-[#30363d]">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder={`Search ${activeTab}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-[#161b22] border border-[#30363d] rounded-lg text-gray-200 placeholder-gray-400 focus:outline-none focus:border-blue-400"
            />
          </div>
          <button className="p-2 text-gray-400 hover:text-gray-200 transition">
            <Filter size={16} />
          </button>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 transition">
            <Plus size={16} />
            Add {activeTab === "people" ? "Person" : "Organization"}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === "people" && (
          <div className="space-y-4">
            {loading ? (
              <div className="text-center py-8 text-gray-400">Loading people...</div>
            ) : filteredPersons.length === 0 ? (
              <div className="text-center py-8 text-gray-400">No people found</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[#30363d] text-left">
                      <th className="py-3 px-4 text-gray-400 font-medium">Name</th>
                      <th className="py-3 px-4 text-gray-400 font-medium">Email</th>
                      <th className="py-3 px-4 text-gray-400 font-medium">Phone</th>
                      <th className="py-3 px-4 text-gray-400 font-medium">Organization</th>
                      <th className="py-3 px-4 text-gray-400 font-medium">Job Title</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPersons.map((person) => (
                      <tr
                        key={person.id}
                        onClick={() => openPersonDrawer(person)}
                        className="border-b border-[#21262d] hover:bg-[#161b22] cursor-pointer transition"
                      >
                        <td className="py-3 px-4 font-medium">{person.name}</td>
                        <td className="py-3 px-4 text-gray-300">
                          {person.emails[0]?.value || "-"}
                        </td>
                        <td className="py-3 px-4 text-gray-300">
                          {person.contact_numbers[0]?.value || "-"}
                        </td>
                        <td className="py-3 px-4 text-gray-300">
                          {person.organization?.name || "-"}
                        </td>
                        <td className="py-3 px-4 text-gray-300">
                          {person.job_title || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === "organizations" && (
          <div className="space-y-4">
            {loading ? (
              <div className="text-center py-8 text-gray-400">Loading organizations...</div>
            ) : filteredOrganizations.length === 0 ? (
              <div className="text-center py-8 text-gray-400">No organizations found</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[#30363d] text-left">
                      <th className="py-3 px-4 text-gray-400 font-medium">Name</th>
                      <th className="py-3 px-4 text-gray-400 font-medium">People</th>
                      <th className="py-3 px-4 text-gray-400 font-medium">Deals</th>
                      <th className="py-3 px-4 text-gray-400 font-medium">Address</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredOrganizations.map((org) => (
                      <tr
                        key={org.id}
                        onClick={() => openOrgDrawer(org)}
                        className="border-b border-[#21262d] hover:bg-[#161b22] cursor-pointer transition"
                      >
                        <td className="py-3 px-4 font-medium">{org.name}</td>
                        <td className="py-3 px-4 text-gray-300">
                          {org.person_count || 0}
                        </td>
                        <td className="py-3 px-4 text-gray-300">
                          {org.deal_count || 0}
                        </td>
                        <td className="py-3 px-4 text-gray-300">
                          {org.address?.street ? 
                            `${org.address.street}, ${org.address.city || ""}` : 
                            "-"
                          }
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Drawers */}
      <PersonDrawer
        person={selectedPerson}
        isOpen={personDrawerOpen}
        onClose={() => setPersonDrawerOpen(false)}
        onUpdate={(updatedPerson) => {
          setPersons(persons.map(p => p.id === updatedPerson.id ? updatedPerson : p));
        }}
      />

      <OrgDrawer
        organization={selectedOrg}
        isOpen={orgDrawerOpen}
        onClose={() => setOrgDrawerOpen(false)}
        onUpdate={(updatedOrg) => {
          setOrganizations(organizations.map(o => o.id === updatedOrg.id ? updatedOrg : o));
        }}
      />
    </div>
  );
}