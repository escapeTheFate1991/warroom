"use client";

import { useState, useEffect, useCallback } from "react";
import { FileText, Plus, Edit, Trash2, X, Copy, Eye } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface EmailTemplate {
  id: number;
  name: string;
  subject: string | null;
  content: string | null;
  created_at: string;
  updated_at: string;
}

export default function EmailTemplatesPanel() {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<EmailTemplate | null>(null);
  const [previewing, setPreviewing] = useState<EmailTemplate | null>(null);

  const [formName, setFormName] = useState("");
  const [formSubject, setFormSubject] = useState("");
  const [formContent, setFormContent] = useState("");

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/crm/email-templates`);
      if (res.ok) setTemplates(await res.json());
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { loadTemplates(); }, [loadTemplates]);

  function resetForm() {
    setFormName("");
    setFormSubject("");
    setFormContent("");
    setEditing(null);
    setShowForm(false);
  }

  function openEdit(t: EmailTemplate) {
    setEditing(t);
    setFormName(t.name);
    setFormSubject(t.subject || "");
    setFormContent(t.content || "");
    setShowForm(true);
  }

  function duplicate(t: EmailTemplate) {
    setEditing(null);
    setFormName(`${t.name} (Copy)`);
    setFormSubject(t.subject || "");
    setFormContent(t.content || "");
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim()) return;

    // The backend only has GET for templates - we'll need to add POST/PUT/DELETE
    // For now, use the emails endpoint pattern
    const body = { name: formName, subject: formSubject || null, content: formContent || null };

    try {
      const url = editing
        ? `${API}/api/crm/email-templates/${editing.id}`
        : `${API}/api/crm/email-templates`;
      const res = await fetch(url, {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        resetForm();
        loadTemplates();
      }
    } catch {}
  }

  async function deleteTemplate(id: number) {
    if (!confirm("Delete this template?")) return;
    try {
      await fetch(`${API}/api/crm/email-templates/${id}`, { method: "DELETE" });
      loadTemplates();
    } catch {}
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <FileText size={16} />
          Email Templates
        </h2>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 text-white rounded-lg text-xs transition-colors"
        >
          <Plus size={14} />
          New Template
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Template List */}
        <div className={`${showForm || previewing ? "w-1/2" : "w-full"} border-r border-warroom-border overflow-y-auto`}>
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-warroom-accent border-t-transparent" />
            </div>
          ) : templates.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-warroom-muted">
              <FileText size={32} className="mb-2 opacity-20" />
              <p className="text-xs">No email templates yet</p>
            </div>
          ) : (
            <div className="divide-y divide-warroom-border">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className={`px-6 py-3 hover:bg-warroom-surface/50 transition-colors group cursor-pointer ${
                    previewing?.id === template.id ? "bg-warroom-accent/10 border-l-2 border-l-warroom-accent" : ""
                  }`}
                  onClick={() => setPreviewing(template)}
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <span className="text-sm font-medium text-warroom-text">{template.name}</span>
                      {template.subject && (
                        <p className="text-xs text-warroom-muted mt-0.5">Subject: {template.subject}</p>
                      )}
                      <p className="text-[10px] text-warroom-muted mt-0.5">
                        Updated {new Date(template.updated_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => { e.stopPropagation(); duplicate(template); }}
                        className="p-1.5 text-warroom-muted hover:text-warroom-accent transition-colors"
                        title="Duplicate"
                      >
                        <Copy size={13} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); openEdit(template); }}
                        className="p-1.5 text-warroom-muted hover:text-warroom-accent transition-colors"
                      >
                        <Edit size={13} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteTemplate(template.id); }}
                        className="p-1.5 text-warroom-muted hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Editor / Preview Panel */}
        {showForm && (
          <div className="w-1/2 overflow-y-auto p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-warroom-text">
                  {editing ? "Edit Template" : "New Template"}
                </h3>
                <button type="button" onClick={resetForm} className="text-warroom-muted hover:text-warroom-text">
                  <X size={16} />
                </button>
              </div>

              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Template name *"
                required
                className="w-full px-3 py-2 text-sm bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <input
                type="text"
                value={formSubject}
                onChange={(e) => setFormSubject(e.target.value)}
                placeholder="Email subject line"
                className="w-full px-3 py-2 text-sm bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <div>
                <label className="text-xs text-warroom-muted mb-1 block">
                  Body (HTML supported)
                </label>
                <textarea
                  value={formContent}
                  onChange={(e) => setFormContent(e.target.value)}
                  placeholder="<h1>Hello {{name}}</h1>\n<p>Your email content here...</p>"
                  rows={16}
                  className="w-full px-3 py-2 text-sm font-mono bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent resize-none"
                />
              </div>

              <div className="flex justify-end gap-2">
                <button type="button" onClick={resetForm} className="px-3 py-1.5 text-xs text-warroom-muted">
                  Cancel
                </button>
                <button type="submit" className="px-4 py-1.5 text-xs bg-warroom-accent text-white rounded-lg">
                  {editing ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </div>
        )}

        {previewing && !showForm && (
          <div className="w-1/2 overflow-y-auto">
            <div className="px-6 py-3 border-b border-warroom-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-warroom-text">{previewing.name}</h3>
                {previewing.subject && (
                  <p className="text-xs text-warroom-muted">Subject: {previewing.subject}</p>
                )}
              </div>
              <button onClick={() => setPreviewing(null)} className="text-warroom-muted hover:text-warroom-text">
                <X size={16} />
              </button>
            </div>
            <div className="p-6">
              {previewing.content ? (
                <div
                  className="bg-white rounded-lg p-4 text-black text-sm"
                  dangerouslySetInnerHTML={{ __html: previewing.content }}
                />
              ) : (
                <p className="text-warroom-muted text-xs">No content</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
