"use client";

import { useState, useEffect, useCallback } from "react";
import { Bot, FileText, Plus, Edit, Trash2, X, Copy, Eye } from "lucide-react";
import EntityAssignmentControl from "@/components/agents/EntityAssignmentControl";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";

type MarketingChannel = "email" | "sms" | "voice" | "social";

const CHANNEL_OPTIONS: { value: MarketingChannel; label: string }[] = [
  { value: "email", label: "Email" },
  { value: "sms", label: "SMS" },
  { value: "voice", label: "Voice" },
  { value: "social", label: "Social" },
];

function getTemplateContentDefaults(channel: MarketingChannel, content: string | null): Record<string, any> {
  if (channel === "sms") return { message: content, stages: [] as unknown[] };
  if (channel === "voice") return { script: content, stages: [] as unknown[] };
  if (channel === "social") {
    return { posts: content ? [{ body: content }] : [], stages: [] as unknown[] };
  }
  return { body: content, stages: [] as unknown[] };
}

function getTemplateConfigDefaults(channel: MarketingChannel): Record<string, any> {
  if (channel === "sms") return { sender_number: null, compliance_profile: null };
  if (channel === "voice") return { caller_id: null, voice_profile: null };
  if (channel === "social") return { platforms: [] as unknown[], profile_id: null };
  return { editor: "html", sender_profile: null };
}

function getContentLabel(channel: MarketingChannel) {
  if (channel === "sms") return "Message template";
  if (channel === "voice") return "Script template";
  if (channel === "social") return "Post draft";
  return "Body (HTML supported)";
}

function getContentPlaceholder(channel: MarketingChannel) {
  if (channel === "sms") return "Hi {{name}}, your SMS content here...";
  if (channel === "voice") return "Hello {{name}}, this is your voice script...";
  if (channel === "social") return "Draft your reusable social post or caption here...";
  return "<h1>Hello {{name}}</h1>\n<p>Your email content here...</p>";
}

function getSubjectPlaceholder(channel: MarketingChannel) {
  if (channel === "social") return "Optional campaign headline";
  if (channel === "voice") return "Optional script title";
  if (channel === "sms") return "Optional message summary";
  return "Email subject line";
}

function getTemplateAssignmentHint(channel: MarketingChannel) {
  if (channel === "sms") return "Assign pooled agents to own reusable SMS setup and future messaging skills.";
  if (channel === "voice") return "Assign pooled agents to own reusable voice setup and future call scripting skills.";
  if (channel === "social") return "Assign pooled agents to own reusable social setup and future publishing skills.";
  return "Assign pooled agents to own reusable email setup and future campaign drafting skills.";
}

function summarizeAssignedAgents(assignments?: AgentAssignmentSummary[]) {
  if (!assignments || assignments.length === 0) return "No AI owners assigned";
  const names = assignments
    .map((assignment) => assignment.agent_name || assignment.agent_id)
    .slice(0, 2)
    .join(", ");
  const extra = assignments.length > 2 ? ` +${assignments.length - 2} more` : "";
  return `AI owners: ${names}${extra}`;
}

function getPreviewContent(template: MarketingTemplate): string | null {
  if (template.channel === "sms") return template.content_blocks?.message || template.content;
  if (template.channel === "voice") return template.content_blocks?.script || template.content;
  if (template.channel === "social") {
    const firstPost = template.content_blocks?.posts?.[0];
    return (firstPost && typeof firstPost === "object" && "body" in firstPost ? firstPost.body : null) || template.content;
  }
  return template.content_blocks?.body || template.content;
}

interface MarketingTemplate {
  id: number;
  name: string;
  description: string | null;
  channel: MarketingChannel;
  subject: string | null;
  content: string | null;
  use_case: string | null;
  content_blocks?: Record<string, any> | null;
  channel_config?: Record<string, any> | null;
  agent_assignments?: AgentAssignmentSummary[];
  created_at: string;
  updated_at: string;
}

export default function EmailTemplatesPanel() {
  const [templates, setTemplates] = useState<MarketingTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<MarketingTemplate | null>(null);
  const [previewing, setPreviewing] = useState<MarketingTemplate | null>(null);

  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formChannel, setFormChannel] = useState<MarketingChannel>("email");
  const [formSubject, setFormSubject] = useState("");
  const [formContent, setFormContent] = useState("");
  const [formUseCase, setFormUseCase] = useState("");

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/crm/email-templates`);
      if (res.ok) setTemplates(await res.json());
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { loadTemplates(); }, [loadTemplates]);

  const syncTemplateAssignments = useCallback((templateId: number, assignments: AgentAssignmentSummary[]) => {
    setTemplates((current) => current.map((template) => (
      template.id === templateId ? { ...template, agent_assignments: assignments } : template
    )));
    setEditing((current) => (
      current && current.id === templateId ? { ...current, agent_assignments: assignments } : current
    ));
    setPreviewing((current) => (
      current && current.id === templateId ? { ...current, agent_assignments: assignments } : current
    ));
  }, []);

  function resetForm() {
    setFormName("");
    setFormDescription("");
    setFormChannel("email");
    setFormSubject("");
    setFormContent("");
    setFormUseCase("");
    setEditing(null);
    setShowForm(false);
  }

  function openEdit(t: MarketingTemplate) {
    setEditing(t);
    setFormName(t.name);
    setFormDescription(t.description || "");
    setFormChannel(t.channel || "email");
    setFormSubject(t.subject || "");
    setFormContent(t.content || "");
    setFormUseCase(t.use_case || "");
    setShowForm(true);
  }

  function duplicate(t: MarketingTemplate) {
    setEditing(null);
    setFormName(`${t.name} (Copy)`);
    setFormDescription(t.description || "");
    setFormChannel(t.channel || "email");
    setFormSubject(t.subject || "");
    setFormContent(t.content || "");
    setFormUseCase(t.use_case || "");
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim()) return;

    const body = {
      name: formName,
      description: formDescription || null,
      channel: formChannel,
      subject: formSubject || null,
      content: formContent || null,
      use_case: formUseCase || null,
      content_blocks: {
        ...getTemplateContentDefaults(formChannel, formContent || null),
        ...(editing?.channel === formChannel ? editing.content_blocks || {} : {}),
      },
      channel_config: {
        ...getTemplateConfigDefaults(formChannel),
        ...(editing?.channel === formChannel ? editing.channel_config || {} : {}),
      },
    };

    try {
      const url = editing
        ? `${API}/api/crm/email-templates/${editing.id}`
        : `${API}/api/crm/email-templates`;
      const res = await authFetch(url, {
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
      await authFetch(`${API}/api/crm/email-templates/${id}`, { method: "DELETE" });
      loadTemplates();
    } catch {}
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <FileText size={16} />
          Templates
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
              <p className="text-xs">No templates yet</p>
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
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-warroom-text">{template.name}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-warroom-accent/10 text-warroom-accent border border-warroom-accent/20 uppercase">
                          {template.channel}
                        </span>
                      </div>
                      {template.use_case && (
                        <p className="text-[10px] text-warroom-muted mt-0.5">Use case: {template.use_case}</p>
                      )}
                      {template.subject && (
                        <p className="text-xs text-warroom-muted mt-0.5">Subject: {template.subject}</p>
                      )}
                      {template.description && (
                        <p className="text-[10px] text-warroom-muted mt-0.5 truncate">{template.description}</p>
                      )}
                      <p className="text-[10px] text-warroom-muted mt-0.5 flex items-center gap-1">
                        <Bot size={10} />
                        {summarizeAssignedAgents(template.agent_assignments)}
                      </p>
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
              <div className="grid grid-cols-2 gap-3">
                <select
                  value={formChannel}
                  onChange={(e) => setFormChannel(e.target.value as MarketingChannel)}
                  className="w-full px-3 py-2 text-sm bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text"
                >
                  {CHANNEL_OPTIONS.map((channel) => (
                    <option key={channel.value} value={channel.value}>{channel.label}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={formUseCase}
                  onChange={(e) => setFormUseCase(e.target.value)}
                  placeholder="Reusable use case (optional)"
                  className="w-full px-3 py-2 text-sm bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
                />
              </div>
              <textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Template description or intended setup"
                rows={2}
                className="w-full px-3 py-2 text-sm bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent resize-none"
              />
              <input
                type="text"
                value={formSubject}
                onChange={(e) => setFormSubject(e.target.value)}
                  placeholder={getSubjectPlaceholder(formChannel)}
                className="w-full px-3 py-2 text-sm bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
              />
              <div>
                <label className="text-xs text-warroom-muted mb-1 block">
                  {getContentLabel(formChannel)}
                </label>
                <textarea
                  value={formContent}
                  onChange={(e) => setFormContent(e.target.value)}
                  placeholder={getContentPlaceholder(formChannel)}
                  rows={16}
                  className="w-full px-3 py-2 text-sm font-mono bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent resize-none"
                />
              </div>
              <div className="rounded-xl border border-warroom-border bg-warroom-bg/60 p-3">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-warroom-muted">
                  <Bot size={13} className="text-warroom-accent" />
                  <span>AI orchestration</span>
                </div>
                <p className="mt-1 text-xs text-warroom-muted">{getTemplateAssignmentHint(formChannel)}</p>
                {editing ? (
                  <EntityAssignmentControl
                    className="mt-3 border-0 bg-transparent p-0"
                    entityType="marketing_template"
                    entityId={editing.id}
                    emptyLabel={`No AI owners assigned to this ${formChannel} template yet.`}
                    initialAssignments={editing.agent_assignments || []}
                    onAssignmentsChange={(assignments) => syncTemplateAssignments(editing.id, assignments)}
                    title={`Own ${formChannel} template: ${formName || editing.name}`}
                  />
                ) : (
                  <p className="mt-2 text-[11px] text-warroom-muted">
                    Save this template first to assign pooled agents for {formChannel} orchestration.
                  </p>
                )}
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
                <p className="text-[10px] text-warroom-muted uppercase">{previewing.channel}</p>
                {previewing.use_case && (
                  <p className="text-xs text-warroom-muted">Use case: {previewing.use_case}</p>
                )}
                {previewing.subject && (
                  <p className="text-xs text-warroom-muted">Subject: {previewing.subject}</p>
                )}
              </div>
              <button onClick={() => setPreviewing(null)} className="text-warroom-muted hover:text-warroom-text">
                <X size={16} />
              </button>
            </div>
            <div className="p-6">
              {getPreviewContent(previewing) ? (
                previewing.channel === "email" ? (
                <div
                  className="bg-white rounded-lg p-4 text-black text-sm"
                  dangerouslySetInnerHTML={{ __html: getPreviewContent(previewing) || "" }}
                />
                ) : (
                  <pre className="whitespace-pre-wrap text-sm text-warroom-text/90 leading-relaxed">
                    {getPreviewContent(previewing) || ""}
                  </pre>
                )
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
