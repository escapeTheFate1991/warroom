"use client";

import { useState, useEffect } from "react";
import {
  Search, Plus, Trash2, Settings, 
  ToggleLeft, ToggleRight, X,
  ChevronDown, ChevronUp, Package, Wrench
} from "lucide-react";
import { API, authFetch } from "@/lib/api";


interface Skill {
  id: string;
  name: string;
  description: string;
  source: "workspace" | "bundled";
  enabled: boolean;
  path: string;
}

interface SkillContent {
  content: string;
}

interface CreateSkillData {
  name: string;
  description: string;
  instructions: string;
}

export default function SkillsManager() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);
  const [skillContent, setSkillContent] = useState<Record<string, string>>({});
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createData, setCreateData] = useState<CreateSkillData>({ name: "", description: "", instructions: "" });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Fetch skills
  const fetchSkills = async () => {
    try {
      const res = await authFetch(`${API}/api/skills`);
      if (res.ok) {
        const data = await res.json();
        setSkills(data);
      }
    } catch (error) {
      console.error("Failed to fetch skills:", error);
    } finally {
      setLoading(false);
    }
  };

  // Toggle skill enabled/disabled
  const toggleSkill = async (skillId: string, enabled: boolean) => {
    try {
      const res = await authFetch(`${API}/api/skills/${skillId}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled })
      });
      if (res.ok) {
        fetchSkills(); // Refresh
      }
    } catch (error) {
      console.error("Failed to toggle skill:", error);
    }
  };

  // Fetch skill content
  const fetchSkillContent = async (skillId: string) => {
    if (skillContent[skillId]) return; // Already cached
    try {
      const res = await authFetch(`${API}/api/skills/${skillId}/content`);
      if (res.ok) {
        const data: SkillContent = await res.json();
        setSkillContent(prev => ({ ...prev, [skillId]: data.content }));
      }
    } catch (error) {
      console.error("Failed to fetch skill content:", error);
    }
  };

  // Create new skill
  const createSkill = async () => {
    if (!createData.name.trim()) return;
    try {
      const res = await authFetch(`${API}/api/skills/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createData)
      });
      if (res.ok) {
        setShowCreateModal(false);
        setCreateData({ name: "", description: "", instructions: "" });
        fetchSkills();
      }
    } catch (error) {
      console.error("Failed to create skill:", error);
    }
  };

  // Delete skill
  const deleteSkill = async (skillId: string) => {
    try {
      const res = await authFetch(`${API}/api/skills/${skillId}`, { method: "DELETE" });
      if (res.ok) {
        setDeleteConfirm(null);
        fetchSkills();
      }
    } catch (error) {
      console.error("Failed to delete skill:", error);
    }
  };

  // Expand/collapse skill card
  const handleSkillClick = (skillId: string) => {
    if (expandedSkill === skillId) {
      setExpandedSkill(null);
    } else {
      setExpandedSkill(skillId);
      fetchSkillContent(skillId);
    }
  };

  useEffect(() => {
    fetchSkills();
  }, []);

  // Filter skills
  const filteredSkills = skills.filter(skill => 
    skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    skill.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const workspaceSkills = filteredSkills.filter(s => s.source === "workspace");
  const bundledSkills = filteredSkills.filter(s => s.source === "bundled");

  const truncateDescription = (desc: string, lines: number = 2) => {
    const words = desc.split(' ');
    const wordsPerLine = 10; // Rough estimate
    const maxWords = words.slice(0, wordsPerLine * lines);
    return maxWords.length < words.length 
      ? maxWords.join(' ') + '...' 
      : desc;
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-warroom-accent"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3 flex-shrink-0">
        <Settings size={18} className="text-warroom-accent" />
        <h2 className="text-lg font-bold text-warroom-text">Skills Manager</h2>
        <div className="ml-auto">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-black rounded-lg hover:opacity-80 transition-opacity"
          >
            <Plus size={16} />
            Create Skill
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <Search size={20} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-warroom-muted" />
            <input
              type="text"
              placeholder="Search skills by name or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
            />
          </div>
        </div>

        <div className="space-y-8">
          {/* Workspace Skills Section */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <Wrench size={20} className="text-green-400" />
              <h3 className="text-xl font-semibold text-warroom-text">Workspace</h3>
              <span className="bg-green-400/20 text-green-400 px-2 py-1 rounded-full text-sm font-medium">
                {workspaceSkills.length}
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {workspaceSkills.map((skill) => (
                <div key={skill.id} className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
                  {/* Card Header - Clickable */}
                  <div 
                    className="p-4 cursor-pointer hover:bg-warroom-surface/80 transition-colors"
                    onClick={() => handleSkillClick(skill.id)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-semibold text-warroom-text truncate">{skill.name}</h4>
                      <div className="flex items-center gap-2">
                        <span className="bg-green-400/20 text-green-400 px-2 py-1 rounded text-xs">
                          workspace
                        </span>
                        {expandedSkill === skill.id ? (
                          <ChevronUp size={16} className="text-warroom-muted" />
                        ) : (
                          <ChevronDown size={16} className="text-warroom-muted" />
                        )}
                      </div>
                    </div>
                    {skill.description && (
                      <p className="text-sm text-warroom-muted leading-relaxed">
                        {truncateDescription(skill.description)}
                      </p>
                    )}
                  </div>

                  {/* Card Actions */}
                  <div className="px-4 pb-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSkill(skill.id, !skill.enabled);
                        }}
                        className="flex items-center gap-2"
                      >
                        {skill.enabled ? (
                          <ToggleRight size={20} className="text-warroom-accent" />
                        ) : (
                          <ToggleLeft size={20} className="text-warroom-muted" />
                        )}
                        <span className={`text-sm ${skill.enabled ? 'text-warroom-accent' : 'text-warroom-muted'}`}>
                          {skill.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </button>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm(skill.id);
                      }}
                      className="p-1 text-red-400 hover:bg-red-400/20 rounded transition-colors"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  {/* Expanded Content */}
                  {expandedSkill === skill.id && skillContent[skill.id] && (
                    <div className="border-t border-warroom-border p-4 bg-warroom-surface/50">
                      <h5 className="text-sm font-medium text-warroom-text mb-2">SKILL.md</h5>
                      <pre className="text-xs text-warroom-muted bg-black/20 p-3 rounded overflow-auto max-h-64 whitespace-pre-wrap">
                        {skillContent[skill.id]}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {workspaceSkills.length === 0 && (
              <div className="text-center py-12 text-warroom-muted">
                No workspace skills found {searchTerm && `matching "${searchTerm}"`}
              </div>
            )}
          </div>

          {/* Bundled Skills Section */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <Package size={20} className="text-blue-400" />
              <h3 className="text-xl font-semibold text-warroom-text">Bundled</h3>
              <span className="bg-blue-400/20 text-blue-400 px-2 py-1 rounded-full text-sm font-medium">
                {bundledSkills.length}
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {bundledSkills.map((skill) => (
                <div key={skill.id} className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
                  {/* Card Header - Clickable */}
                  <div 
                    className="p-4 cursor-pointer hover:bg-warroom-surface/80 transition-colors"
                    onClick={() => handleSkillClick(skill.id)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-semibold text-warroom-text truncate">{skill.name}</h4>
                      <div className="flex items-center gap-2">
                        <span className="bg-blue-400/20 text-blue-400 px-2 py-1 rounded text-xs">
                          bundled
                        </span>
                        {expandedSkill === skill.id ? (
                          <ChevronUp size={16} className="text-warroom-muted" />
                        ) : (
                          <ChevronDown size={16} className="text-warroom-muted" />
                        )}
                      </div>
                    </div>
                    {skill.description && (
                      <p className="text-sm text-warroom-muted leading-relaxed">
                        {truncateDescription(skill.description)}
                      </p>
                    )}
                  </div>

                  {/* Card Actions */}
                  <div className="px-4 pb-4">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSkill(skill.id, !skill.enabled);
                      }}
                      className="flex items-center gap-2"
                    >
                      {skill.enabled ? (
                        <ToggleRight size={20} className="text-warroom-accent" />
                      ) : (
                        <ToggleLeft size={20} className="text-warroom-muted" />
                      )}
                      <span className={`text-sm ${skill.enabled ? 'text-warroom-accent' : 'text-warroom-muted'}`}>
                        {skill.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </button>
                  </div>

                  {/* Expanded Content */}
                  {expandedSkill === skill.id && skillContent[skill.id] && (
                    <div className="border-t border-warroom-border p-4 bg-warroom-surface/50">
                      <h5 className="text-sm font-medium text-warroom-text mb-2">SKILL.md</h5>
                      <pre className="text-xs text-warroom-muted bg-black/20 p-3 rounded overflow-auto max-h-64 whitespace-pre-wrap">
                        {skillContent[skill.id]}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {bundledSkills.length === 0 && (
              <div className="text-center py-12 text-warroom-muted">
                No bundled skills found {searchTerm && `matching "${searchTerm}"`}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Skill Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-lg w-full max-w-2xl mx-4">
            <div className="flex items-center justify-between p-6 border-b border-warroom-border">
              <h3 className="text-lg font-semibold text-warroom-text">Create New Skill</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 text-warroom-muted hover:text-warroom-text"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-2">Name *</label>
                <input
                  type="text"
                  value={createData.name}
                  onChange={(e) => setCreateData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="skill-name (lowercase, hyphens only)"
                  className="w-full px-3 py-2 bg-warroom-surface border border-warroom-border rounded text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-2">Description</label>
                <input
                  type="text"
                  value={createData.description}
                  onChange={(e) => setCreateData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description of what this skill does"
                  className="w-full px-3 py-2 bg-warroom-surface border border-warroom-border rounded text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-warroom-text mb-2">Instructions</label>
                <textarea
                  value={createData.instructions}
                  onChange={(e) => setCreateData(prev => ({ ...prev, instructions: e.target.value }))}
                  placeholder="Detailed instructions for how this skill works..."
                  rows={8}
                  className="w-full px-3 py-2 bg-warroom-surface border border-warroom-border rounded text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent resize-none"
                />
              </div>
            </div>
            
            <div className="flex items-center justify-end gap-3 p-6 border-t border-warroom-border">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-warroom-muted hover:text-warroom-text"
              >
                Cancel
              </button>
              <button
                onClick={createSkill}
                disabled={!createData.name.trim()}
                className="px-4 py-2 bg-warroom-accent text-black rounded hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Skill
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-lg w-full max-w-md mx-4">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-warroom-text mb-4">Delete Skill</h3>
              <p className="text-warroom-muted mb-6">
                Are you sure you want to delete "{deleteConfirm}"? This action cannot be undone.
              </p>
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="px-4 py-2 text-warroom-muted hover:text-warroom-text"
                >
                  Cancel
                </button>
                <button
                  onClick={() => deleteSkill(deleteConfirm)}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}