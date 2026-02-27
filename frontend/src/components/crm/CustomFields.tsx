"use client";

import { useState, useEffect } from "react";
import { Plus, Edit, Trash2, Settings, Type, Hash, Calendar, CheckSquare, List } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface CustomAttribute {
  id: number;
  code: string;
  name: string;
  type: string;
  entity_type: string;
  is_required: boolean;
  sort_order: number;
  options?: AttributeOption[];
}

interface AttributeOption {
  id: number;
  name: string;
  sort_order: number;
}

interface AttributeForm {
  name: string;
  code: string;
  type: string;
  is_required: boolean;
  options: string[];
}

const ENTITY_TYPES = [
  { value: 'deal', label: 'Deals' },
  { value: 'person', label: 'Persons' },
  { value: 'organization', label: 'Organizations' },
  { value: 'product', label: 'Products' }
];

const FIELD_TYPES = [
  { value: 'text', label: 'Text', icon: Type },
  { value: 'textarea', label: 'Long Text', icon: Type },
  { value: 'number', label: 'Number', icon: Hash },
  { value: 'date', label: 'Date', icon: Calendar },
  { value: 'datetime', label: 'Date & Time', icon: Calendar },
  { value: 'boolean', label: 'Yes/No', icon: CheckSquare },
  { value: 'select', label: 'Dropdown', icon: List },
  { value: 'multiselect', label: 'Multi-select', icon: List }
];

export default function CustomFields() {
  const [selectedEntityType, setSelectedEntityType] = useState('deal');
  const [attributes, setAttributes] = useState<CustomAttribute[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingAttribute, setEditingAttribute] = useState<CustomAttribute | null>(null);
  const [form, setForm] = useState<AttributeForm>({
    name: '',
    code: '',
    type: 'text',
    is_required: false,
    options: []
  });

  const loadAttributes = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/api/crm/attributes?entity_type=${selectedEntityType}`);
      if (resp.ok) {
        const data = await resp.json();
        setAttributes(data);
      }
    } catch (error) {
      console.error('Failed to load attributes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAttributes();
  }, [selectedEntityType]);

  const generateCode = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '_')
      .substring(0, 50);
  };

  const handleNameChange = (name: string) => {
    setForm(prev => ({
      ...prev,
      name,
      code: prev.code === '' ? generateCode(name) : prev.code
    }));
  };

  const handleTypeChange = (type: string) => {
    setForm(prev => ({
      ...prev,
      type,
      options: ['select', 'multiselect'].includes(type) ? prev.options : []
    }));
  };

  const addOption = () => {
    setForm(prev => ({
      ...prev,
      options: [...prev.options, '']
    }));
  };

  const updateOption = (index: number, value: string) => {
    setForm(prev => ({
      ...prev,
      options: prev.options.map((opt, i) => i === index ? value : opt)
    }));
  };

  const removeOption = (index: number) => {
    setForm(prev => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index)
    }));
  };

  const resetForm = () => {
    setForm({
      name: '',
      code: '',
      type: 'text',
      is_required: false,
      options: []
    });
    setEditingAttribute(null);
    setShowForm(false);
  };

  const startEdit = (attribute: CustomAttribute) => {
    setEditingAttribute(attribute);
    setForm({
      name: attribute.name,
      code: attribute.code,
      type: attribute.type,
      is_required: attribute.is_required,
      options: attribute.options?.map(opt => opt.name) || []
    });
    setShowForm(true);
  };

  const saveAttribute = async () => {
    if (!form.name.trim() || !form.code.trim()) {
      alert('Name and code are required');
      return;
    }

    try {
      const payload = {
        ...form,
        entity_type: selectedEntityType,
        options: form.options.filter(opt => opt.trim())
      };

      const url = editingAttribute 
        ? `${API}/api/crm/attributes/${editingAttribute.id}`
        : `${API}/api/crm/attributes`;
      
      const method = editingAttribute ? 'PUT' : 'POST';
      
      const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (resp.ok) {
        resetForm();
        loadAttributes();
      } else {
        const error = await resp.json();
        alert(error.detail || 'Failed to save attribute');
      }
    } catch (error) {
      alert('Failed to save attribute');
    }
  };

  const deleteAttribute = async (id: number) => {
    if (!confirm('Are you sure you want to delete this custom field?')) {
      return;
    }

    try {
      const resp = await fetch(`${API}/api/crm/attributes/${id}`, {
        method: 'DELETE'
      });

      if (resp.ok) {
        loadAttributes();
      } else {
        alert('Failed to delete attribute');
      }
    } catch (error) {
      alert('Failed to delete attribute');
    }
  };

  const getTypeIcon = (type: string) => {
    const fieldType = FIELD_TYPES.find(ft => ft.value === type);
    if (!fieldType) return Type;
    return fieldType.icon;
  };

  const renderAttributeForm = () => (
    <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-warroom-text">
          {editingAttribute ? 'Edit Field' : 'Add New Field'}
        </h4>
        <button
          onClick={resetForm}
          className="text-warroom-muted hover:text-warroom-text"
        >
          ✕
        </button>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-warroom-text block mb-2">Field Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Enter field name"
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-sm text-warroom-text block mb-2">Field Code</label>
            <input
              type="text"
              value={form.code}
              onChange={(e) => setForm(prev => ({ ...prev, code: e.target.value }))}
              placeholder="field_code"
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>

        <div>
          <label className="text-sm text-warroom-text block mb-2">Field Type</label>
          <select
            value={form.type}
            onChange={(e) => handleTypeChange(e.target.value)}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
          >
            {FIELD_TYPES.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
        </div>

        {['select', 'multiselect'].includes(form.type) && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-warroom-text">Options</label>
              <button
                onClick={addOption}
                className="flex items-center gap-1 px-2 py-1 bg-warroom-accent hover:bg-warroom-accent/80 rounded text-xs font-medium transition"
              >
                <Plus size={12} />
                Add Option
              </button>
            </div>
            <div className="space-y-2">
              {form.options.map((option, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={option}
                    onChange={(e) => updateOption(index, e.target.value)}
                    placeholder={`Option ${index + 1}`}
                    className="flex-1 bg-warroom-bg border border-warroom-border rounded px-3 py-1.5 text-sm"
                  />
                  <button
                    onClick={() => removeOption(index)}
                    className="p-1.5 text-red-400 hover:bg-red-500/20 rounded transition"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              {form.options.length === 0 && (
                <div className="text-xs text-warroom-muted">
                  No options added yet. Click "Add Option" to add some.
                </div>
              )}
            </div>
          </div>
        )}

        <div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.is_required}
              onChange={(e) => setForm(prev => ({ ...prev, is_required: e.target.checked }))}
              className="rounded border-warroom-border"
            />
            <span className="text-sm text-warroom-text">Required field</span>
          </label>
        </div>

        <div className="flex gap-3">
          <button
            onClick={resetForm}
            className="px-4 py-2 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded-lg text-sm font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={saveAttribute}
            className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
          >
            {editingAttribute ? 'Update Field' : 'Create Field'}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3">
        <Settings size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Custom Fields</h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Entity Type Selector */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-warroom-text block mb-2">Entity Type</label>
              <select
                value={selectedEntityType}
                onChange={(e) => setSelectedEntityType(e.target.value)}
                className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
              >
                {ENTITY_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            
            {!showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
              >
                <Plus size={16} />
                Add Field
              </button>
            )}
          </div>

          {/* Add/Edit Form */}
          {showForm && renderAttributeForm()}

          {/* Attributes List */}
          {loading ? (
            <div className="flex items-center justify-center py-12 text-warroom-muted">
              <Settings size={24} className="animate-spin mr-3" />
              Loading custom fields...
            </div>
          ) : attributes.length === 0 ? (
            <div className="text-center py-12 text-warroom-muted">
              <Settings size={32} className="mx-auto mb-4 opacity-50" />
              <p className="text-sm">No custom fields found for {ENTITY_TYPES.find(t => t.value === selectedEntityType)?.label}</p>
              <p className="text-xs mt-1">Add your first custom field to get started</p>
            </div>
          ) : (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-warroom-text">
                Custom Fields ({attributes.length})
              </h3>
              
              {attributes.map((attribute) => {
                const TypeIcon = getTypeIcon(attribute.type);
                return (
                  <div 
                    key={attribute.id}
                    className="bg-warroom-surface border border-warroom-border rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="w-8 h-8 bg-warroom-accent/10 rounded-lg flex items-center justify-center">
                            <TypeIcon size={16} className="text-warroom-accent" />
                          </div>
                          <div>
                            <h4 className="text-sm font-medium text-warroom-text flex items-center gap-2">
                              {attribute.name}
                              {attribute.is_required && (
                                <span className="text-xs text-red-400">*</span>
                              )}
                            </h4>
                            <div className="flex items-center gap-3 text-xs text-warroom-muted mt-0.5">
                              <code className="bg-warroom-bg px-1 py-0.5 rounded font-mono">
                                {attribute.code}
                              </code>
                              <span className="capitalize">{attribute.type}</span>
                              {attribute.options && attribute.options.length > 0 && (
                                <span>{attribute.options.length} options</span>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        {/* Show options if it's a select field */}
                        {['select', 'multiselect'].includes(attribute.type) && attribute.options && (
                          <div className="ml-11 mt-2">
                            <div className="text-xs text-warroom-muted mb-1">Options:</div>
                            <div className="flex flex-wrap gap-1">
                              {attribute.options.map((option, index) => (
                                <span 
                                  key={index}
                                  className="px-2 py-0.5 bg-warroom-bg rounded text-xs"
                                >
                                  {option.name}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => startEdit(attribute)}
                          className="p-1.5 text-warroom-muted hover:text-warroom-accent hover:bg-warroom-accent/10 rounded transition"
                        >
                          <Edit size={14} />
                        </button>
                        <button
                          onClick={() => deleteAttribute(attribute.id)}
                          className="p-1.5 text-warroom-muted hover:text-red-400 hover:bg-red-500/10 rounded transition"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}