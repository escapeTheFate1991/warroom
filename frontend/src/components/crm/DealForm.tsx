"use client";

import { useState, useEffect } from "react";
import { X, Save, Loader2, Search, Plus } from "lucide-react";
import { Pipeline, PipelineStage, Person, Organization, LeadSource, LeadType, DealFull } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface DealFormProps {
  deal: DealFull | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (deal: DealFull) => void;
  pipelines: Pipeline[];
  stages: PipelineStage[];
}

export default function DealForm({ deal, isOpen, onClose, onSave, pipelines, stages }: DealFormProps) {
  const [formData, setFormData] = useState<DealFull>({
    title: "",
    description: null,
    deal_value: null,
    person_id: null,
    organization_id: null,
    source_id: null,
    type_id: null,
    pipeline_id: 0,
    stage_id: 0,
    expected_close_date: null,
    status: null,
  });
  
  const [persons, setPersons] = useState<Person[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [sources, setSources] = useState<LeadSource[]>([]);
  const [types, setTypes] = useState<LeadType[]>([]);
  const [personSearch, setPersonSearch] = useState("");
  const [orgSearch, setOrgSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const isEditing = !!deal?.id;
  const currentStages = stages.filter(s => s.pipeline_id === formData.pipeline_id);

  // Initialize form data when modal opens or deal changes
  useEffect(() => {
    if (isOpen) {
      if (deal) {
        setFormData({ ...deal });
      } else {
        // Reset to default values for new deal
        const defaultPipeline = pipelines.find(p => p.is_default) || pipelines[0];
        const firstStage = stages.find(s => s.pipeline_id === defaultPipeline?.id);
        
        setFormData({
          title: "",
          description: null,
          deal_value: null,
          person_id: null,
          organization_id: null,
          source_id: null,
          type_id: null,
          pipeline_id: defaultPipeline?.id || 0,
          stage_id: firstStage?.id || 0,
          expected_close_date: null,
          status: null,
        });
      }
      
      // Load reference data
      loadReferenceData();
    }
  }, [isOpen, deal, pipelines, stages]);

  // Update stage options when pipeline changes
  useEffect(() => {
    if (formData.pipeline_id) {
      const newStages = stages.filter(s => s.pipeline_id === formData.pipeline_id);
      if (newStages.length > 0 && !newStages.find(s => s.id === formData.stage_id)) {
        setFormData(prev => ({ ...prev, stage_id: newStages[0].id }));
      }
    }
  }, [formData.pipeline_id, stages]);

  const loadReferenceData = async () => {
    setLoading(true);
    try {
      const [sourcesResp, typesResp, personsResp, orgsResp] = await Promise.all([
        fetch(`${API}/api/crm/lead-sources`),
        fetch(`${API}/api/crm/lead-types`),
        fetch(`${API}/api/crm/contacts/persons?limit=50`),
        fetch(`${API}/api/crm/contacts/organizations?limit=50`),
      ]);

      if (sourcesResp.ok) {
        const sourcesData = await sourcesResp.json();
        setSources(sourcesData);
      }

      if (typesResp.ok) {
        const typesData = await typesResp.json();
        setTypes(typesData);
      }

      if (personsResp.ok) {
        const personsData = await personsResp.json();
        setPersons(personsData);
      }

      if (orgsResp.ok) {
        const orgsData = await orgsResp.json();
        setOrganizations(orgsData);
      }
    } catch (error) {
      console.error("Failed to load reference data:", error);
    } finally {
      setLoading(false);
    }
  };

  const searchPersons = async (query: string) => {
    if (query.length < 2) return;
    
    try {
      const response = await fetch(`${API}/api/crm/contacts/persons/search?q=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        setPersons(data);
      }
    } catch (error) {
      console.error("Failed to search persons:", error);
    }
  };

  const searchOrganizations = async (query: string) => {
    if (query.length < 2) return;
    
    try {
      const response = await fetch(`${API}/api/crm/contacts/organizations/search?q=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
      }
    } catch (error) {
      console.error("Failed to search organizations:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const url = isEditing 
        ? `${API}/api/crm/deals/${deal!.id}`
        : `${API}/api/crm/deals`;
      
      const method = isEditing ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          deal_value: formData.deal_value ? Number(formData.deal_value) : null,
        }),
      });

      if (response.ok) {
        const savedDeal = await response.json();
        onSave(savedDeal);
        onClose();
      } else {
        console.error("Failed to save deal:", await response.text());
      }
    } catch (error) {
      console.error("Failed to save deal:", error);
    } finally {
      setSaving(false);
    }
  };

  const handlePersonSearch = (value: string) => {
    setPersonSearch(value);
    if (value) {
      searchPersons(value);
    }
  };

  const handleOrgSearch = (value: string) => {
    setOrgSearch(value);
    if (value) {
      searchOrganizations(value);
    }
  };

  const selectedPerson = persons.find(p => p.id === formData.person_id);
  const selectedOrg = organizations.find(o => o.id === formData.organization_id);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative min-h-full flex items-center justify-center p-4">
        <div className="relative bg-warroom-surface border border-warroom-border rounded-lg shadow-2xl w-full max-w-2xl">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-warroom-border">
            <h2 className="text-lg font-semibold text-warroom-text">
              {isEditing ? "Edit Deal" : "New Deal"}
            </h2>
            <button
              onClick={onClose}
              className="text-warroom-muted hover:text-warroom-text transition p-1"
            >
              <X size={20} />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                  required
                  placeholder="Deal title"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Deal Value
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted">$</span>
                  <input
                    type="number"
                    value={formData.deal_value || ""}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      deal_value: e.target.value ? Number(e.target.value) : null 
                    }))}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg pl-8 pr-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                    placeholder="0"
                    min="0"
                    step="0.01"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Expected Close Date
                </label>
                <input
                  type="date"
                  value={formData.expected_close_date || ""}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    expected_close_date: e.target.value || null 
                  }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                />
              </div>
            </div>

            {/* Pipeline & Stage */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Pipeline *
                </label>
                <select
                  value={formData.pipeline_id}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    pipeline_id: Number(e.target.value) 
                  }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                  style={{ colorScheme: "dark" }}
                  required
                >
                  <option value="">Select pipeline...</option>
                  {pipelines.map((pipeline) => (
                    <option key={pipeline.id} value={pipeline.id}>
                      {pipeline.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Stage *
                </label>
                <select
                  value={formData.stage_id}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    stage_id: Number(e.target.value) 
                  }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                  style={{ colorScheme: "dark" }}
                  required
                  disabled={!formData.pipeline_id}
                >
                  <option value="">Select stage...</option>
                  {currentStages.map((stage) => (
                    <option key={stage.id} value={stage.id}>
                      {stage.name} ({stage.probability}%)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Contact Information */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Person
                </label>
                <div className="relative">
                  <select
                    value={formData.person_id || ""}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      person_id: e.target.value ? Number(e.target.value) : null 
                    }))}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                    style={{ colorScheme: "dark" }}
                  >
                    <option value="">Select person...</option>
                    {persons.map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.name} {person.organization_name && `(${person.organization_name})`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Organization
                </label>
                <div className="relative">
                  <select
                    value={formData.organization_id || ""}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      organization_id: e.target.value ? Number(e.target.value) : null 
                    }))}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                    style={{ colorScheme: "dark" }}
                  >
                    <option value="">Select organization...</option>
                    {organizations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Source & Type */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Source
                </label>
                <select
                  value={formData.source_id || ""}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    source_id: e.target.value ? Number(e.target.value) : null 
                  }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                  style={{ colorScheme: "dark" }}
                >
                  <option value="">Select source...</option>
                  {sources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-warroom-text mb-1">
                  Type
                </label>
                <select
                  value={formData.type_id || ""}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    type_id: e.target.value ? Number(e.target.value) : null 
                  }))}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent"
                  style={{ colorScheme: "dark" }}
                >
                  <option value="">Select type...</option>
                  {types.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-warroom-text mb-1">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  description: e.target.value || null 
                }))}
                rows={4}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                placeholder="Deal description..."
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-warroom-border">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-warroom-muted hover:text-warroom-text transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || !formData.title || !formData.pipeline_id || !formData.stage_id}
                className="px-6 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-white font-medium transition flex items-center gap-2"
              >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                {saving ? "Saving..." : (isEditing ? "Update" : "Create")}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}