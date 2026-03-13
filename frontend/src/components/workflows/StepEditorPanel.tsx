"use client";

import { useCallback, useEffect, useState } from "react";
import {
  X, Trash2, Plus, Zap, GitBranch, Play,
  Mail, Phone, Bell, ClipboardList, Bot, Send, MessageSquare,
  Clock, Calendar, Shield, Sparkles,
} from "lucide-react";
import type { Node } from "@xyflow/react";

/* ── Types ─────────────────────────────────────────────── */

interface StepEditorPanelProps {
  node: Node | null;
  onSave: (nodeId: string, data: Record<string, unknown>) => void;
  onClose: () => void;
}

interface Condition {
  field: string;
  operator: string;
  value: string;
}

/* ── Constants ─────────────────────────────────────────── */

const ENTITY_OPTIONS = [
  { value: "person", label: "Contact" },
  { value: "deal", label: "Deal" },
  { value: "activity", label: "Activity" },
  { value: "contact_submission", label: "Contact Submission" },
  { value: "social_event", label: "Social Event" },
];

const EVENT_OPTIONS: Record<string, { value: string; label: string }[]> = {
  person: [
    { value: "created", label: "is created" },
    { value: "updated", label: "is updated" },
  ],
  deal: [
    { value: "created", label: "is created" },
    { value: "updated", label: "is updated" },
    { value: "stage_changed", label: "changes stage" },
  ],
  activity: [
    { value: "created", label: "is created" },
    { value: "updated", label: "is updated" },
  ],
  contact_submission: [
    { value: "created", label: "is created" },
  ],
  social_event: [
    { value: "comment_received", label: "receives a comment" },
    { value: "dm_received", label: "receives a DM" },
    { value: "mention", label: "is mentioned" },
    { value: "keyword_comment", label: "comment matches keyword" },
  ],
};

const OPERATORS = [
  { value: "equals", label: "equals" },
  { value: "not_equals", label: "not equals" },
  { value: "gte", label: "≥ (at least)" },
  { value: "lte", label: "≤ (at most)" },
  { value: "in", label: "in" },
  { value: "not_empty", label: "has a value" },
  { value: "is_set", label: "is set" },
  { value: "contains", label: "contains" },
];

const VALUELESS_OPERATORS = new Set(["not_empty", "is_set"]);

const ACTION_TYPES = [
  { value: "send_email", label: "Send Email", icon: Mail },
  { value: "send_sms", label: "Send SMS", icon: MessageSquare },
  { value: "make_call", label: "Make Call", icon: Phone },
  { value: "delay", label: "Delay", icon: Clock },
  { value: "create_activity", label: "Create Activity", icon: ClipboardList },
  { value: "create_calendar_event", label: "Create Calendar Event", icon: Calendar },
  { value: "notify_owner", label: "Notify Owner", icon: Bell },
  { value: "ai_draft_message", label: "AI Draft Message", icon: Sparkles },
  { value: "ai_extract_details", label: "AI Extract Details", icon: Bot },
  { value: "ai_summarize_context", label: "AI Summarize Context", icon: Bot },
  { value: "ai_prioritize_lead", label: "AI Prioritize Lead", icon: Bot },
  { value: "approval_gate", label: "Approval Gate", icon: Shield },
  { value: "social_reply", label: "Social Comment Reply", icon: Send },
  { value: "social_dm", label: "Social DM Reply", icon: MessageSquare },
];

const DELAY_UNITS = [
  { value: "minutes", label: "Minutes" },
  { value: "hours", label: "Hours" },
  { value: "days", label: "Days" },
];

const ACTIVITY_TYPES = [
  { value: "task", label: "Task" },
  { value: "meeting", label: "Meeting" },
  { value: "call", label: "Call" },
  { value: "note", label: "Note" },
];

const CHANNEL_OPTIONS = [
  { value: "inbox", label: "Inbox" },
  { value: "sms", label: "SMS" },
  { value: "email", label: "Email" },
];

/* ── Shared Input Components ───────────────────────────── */

const inputClass = "w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50 transition";
const selectClass = "w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50 transition";
const labelClass = "text-xs font-medium text-warroom-muted uppercase tracking-wide";
const textareaClass = "w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text text-sm focus:outline-none focus:border-warroom-accent/50 transition resize-none";

function Label({ children }: { children: React.ReactNode }) {
  return <label className={labelClass}>{children}</label>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

/* ── Trigger Editor ────────────────────────────────────── */

function TriggerEditor({ data, onChange }: { data: Record<string, unknown>; onChange: (d: Record<string, unknown>) => void }) {
  const entityType = (data.entity_type as string) || "deal";
  const event = (data.event as string) || "created";
  const events = EVENT_OPTIONS[entityType] || EVENT_OPTIONS.deal;

  return (
    <div className="space-y-4">
      <Field label="Entity Type">
        <select
          value={entityType}
          onChange={(e) => {
            const newEntity = e.target.value;
            const newEvents = EVENT_OPTIONS[newEntity] || [];
            const firstEvent = newEvents[0]?.value || "created";
            onChange({ ...data, entity_type: newEntity, event: firstEvent });
          }}
          className={selectClass}
          style={{ colorScheme: "dark" }}
        >
          {ENTITY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </Field>

      <Field label="Event">
        <select
          value={event}
          onChange={(e) => onChange({ ...data, event: e.target.value })}
          className={selectClass}
          style={{ colorScheme: "dark" }}
        >
          {events.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </Field>
    </div>
  );
}

/* ── Condition Editor ──────────────────────────────────── */

function ConditionEditor({ data, onChange }: { data: Record<string, unknown>; onChange: (d: Record<string, unknown>) => void }) {
  const conditionType = (data.conditionType as string) || "and";
  const conditions = ((data.conditions as Condition[]) || []).map((c) => ({
    field: c.field || "",
    operator: c.operator || "equals",
    value: c.value || "",
  }));

  const updateConditions = (newConditions: Condition[]) => {
    onChange({ ...data, conditions: newConditions });
  };

  const addCondition = () => {
    updateConditions([...conditions, { field: "", operator: "equals", value: "" }]);
  };

  const removeCondition = (index: number) => {
    updateConditions(conditions.filter((_, i) => i !== index));
  };

  const updateCondition = (index: number, updates: Partial<Condition>) => {
    updateConditions(conditions.map((c, i) => (i === index ? { ...c, ...updates } : c)));
  };

  return (
    <div className="space-y-4">
      {/* AND / OR toggle */}
      <Field label="Match Type">
        <div className="flex rounded-lg border border-warroom-border overflow-hidden">
          {(["and", "or"] as const).map((type) => (
            <button
              key={type}
              onClick={() => onChange({ ...data, conditionType: type })}
              className={`flex-1 py-2 text-xs font-semibold uppercase transition ${
                conditionType === type
                  ? "bg-warroom-accent text-white"
                  : "bg-warroom-bg text-warroom-muted hover:text-warroom-text"
              }`}
            >
              {type === "and" ? "All Match (AND)" : "Any Match (OR)"}
            </button>
          ))}
        </div>
      </Field>

      {/* Condition rows */}
      <div className="space-y-3">
        <Label>Conditions</Label>
        {conditions.map((c, i) => (
          <div key={i} className="bg-warroom-bg rounded-lg p-3 space-y-2 border border-warroom-border/50">
            <div className="flex items-center gap-2">
              <input
                value={c.field}
                onChange={(e) => updateCondition(i, { field: e.target.value })}
                placeholder="Field name"
                className={inputClass}
              />
              <button
                onClick={() => removeCondition(i)}
                className="p-1.5 rounded-lg text-warroom-muted hover:text-red-400 hover:bg-red-500/10 transition flex-shrink-0"
              >
                <Trash2 size={14} />
              </button>
            </div>
            <select
              value={c.operator}
              onChange={(e) => updateCondition(i, { operator: e.target.value })}
              className={selectClass}
              style={{ colorScheme: "dark" }}
            >
              {OPERATORS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            {!VALUELESS_OPERATORS.has(c.operator) && (
              <input
                value={c.value}
                onChange={(e) => updateCondition(i, { value: e.target.value })}
                placeholder="Value"
                className={inputClass}
              />
            )}
          </div>
        ))}
        <button
          onClick={addCondition}
          className="flex items-center gap-1.5 text-xs text-warroom-accent hover:text-warroom-accent/80 transition"
        >
          <Plus size={14} />
          Add Condition
        </button>
      </div>
    </div>
  );
}

/* ── Action Editor ─────────────────────────────────────── */

function ActionEditor({ data, onChange }: { data: Record<string, unknown>; onChange: (d: Record<string, unknown>) => void }) {
  const actionType = (data.actionType as string) || "send_email";

  const setField = (key: string, value: unknown) => {
    onChange({ ...data, [key]: value });
  };

  const renderForm = () => {
    switch (actionType) {
      case "send_email":
        return (
          <>
            <Field label="Subject">
              <input
                value={(data.subject as string) || ""}
                onChange={(e) => setField("subject", e.target.value)}
                placeholder="Email subject"
                className={inputClass}
              />
            </Field>
            <Field label="Body">
              <textarea
                value={(data.body as string) || ""}
                onChange={(e) => setField("body", e.target.value)}
                placeholder="Email body..."
                rows={4}
                className={textareaClass}
              />
            </Field>
            <Field label="Channel Label">
              <input
                value={(data.channel as string) || ""}
                onChange={(e) => setField("channel", e.target.value)}
                placeholder="e.g. main-email"
                className={inputClass}
              />
            </Field>
          </>
        );

      case "send_sms":
        return (
          <>
            <Field label="Message">
              <textarea
                value={(data.message as string) || ""}
                onChange={(e) => setField("message", e.target.value)}
                placeholder="SMS message..."
                rows={3}
                className={textareaClass}
              />
            </Field>
            <Field label="Channel Label">
              <input
                value={(data.channel as string) || ""}
                onChange={(e) => setField("channel", e.target.value)}
                placeholder="e.g. twilio-sms"
                className={inputClass}
              />
            </Field>
          </>
        );

      case "make_call":
        return (
          <>
            <Field label="Message / Goal">
              <textarea
                value={(data.message as string) || (data.goal as string) || ""}
                onChange={(e) => setField("message", e.target.value)}
                placeholder="Call objective..."
                rows={3}
                className={textareaClass}
              />
            </Field>
            <Field label="Channel Label">
              <input
                value={(data.channel as string) || ""}
                onChange={(e) => setField("channel", e.target.value)}
                placeholder="e.g. vapi-phone"
                className={inputClass}
              />
            </Field>
          </>
        );

      case "delay":
        return (
          <div className="flex gap-3">
            <div className="flex-1 space-y-1.5">
              <Label>Duration</Label>
              <input
                type="number"
                min={1}
                value={(data.duration as number) || 1}
                onChange={(e) => setField("duration", parseInt(e.target.value) || 1)}
                className={inputClass}
              />
            </div>
            <div className="flex-1 space-y-1.5">
              <Label>Unit</Label>
              <select
                value={(data.unit as string) || "minutes"}
                onChange={(e) => setField("unit", e.target.value)}
                className={selectClass}
                style={{ colorScheme: "dark" }}
              >
                {DELAY_UNITS.map((u) => (
                  <option key={u.value} value={u.value}>{u.label}</option>
                ))}
              </select>
            </div>
          </div>
        );

      case "create_activity":
        return (
          <>
            <Field label="Activity Type">
              <select
                value={(data.activity_type as string) || "task"}
                onChange={(e) => setField("activity_type", e.target.value)}
                className={selectClass}
                style={{ colorScheme: "dark" }}
              >
                {ACTIVITY_TYPES.map((a) => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Title">
              <input
                value={(data.title as string) || ""}
                onChange={(e) => setField("title", e.target.value)}
                placeholder="Activity title"
                className={inputClass}
              />
            </Field>
          </>
        );

      case "create_calendar_event":
        return (
          <>
            <Field label="Summary">
              <input
                value={(data.summary as string) || ""}
                onChange={(e) => setField("summary", e.target.value)}
                placeholder="Event summary"
                className={inputClass}
              />
            </Field>
            <div className="flex gap-3">
              <div className="flex-1 space-y-1.5">
                <Label>Duration</Label>
                <input
                  type="number"
                  min={1}
                  value={(data.duration as number) || 30}
                  onChange={(e) => setField("duration", parseInt(e.target.value) || 30)}
                  className={inputClass}
                />
              </div>
              <div className="flex-1 space-y-1.5">
                <Label>Unit</Label>
                <select
                  value={(data.unit as string) || "minutes"}
                  onChange={(e) => setField("unit", e.target.value)}
                  className={selectClass}
                  style={{ colorScheme: "dark" }}
                >
                  {DELAY_UNITS.map((u) => (
                    <option key={u.value} value={u.value}>{u.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </>
        );

      case "notify_owner":
        return (
          <>
            <Field label="Channel">
              <select
                value={(data.channel as string) || "inbox"}
                onChange={(e) => setField("channel", e.target.value)}
                className={selectClass}
                style={{ colorScheme: "dark" }}
              >
                {CHANNEL_OPTIONS.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Message">
              <textarea
                value={(data.message as string) || ""}
                onChange={(e) => setField("message", e.target.value)}
                placeholder="Notification message..."
                rows={3}
                className={textareaClass}
              />
            </Field>
          </>
        );

      case "ai_draft_message":
        return (
          <>
            <Field label="Goal">
              <textarea
                value={(data.goal as string) || ""}
                onChange={(e) => setField("goal", e.target.value)}
                placeholder="What should the AI draft?"
                rows={3}
                className={textareaClass}
              />
            </Field>
            <Field label="Channel">
              <select
                value={(data.channel as string) || "email"}
                onChange={(e) => setField("channel", e.target.value)}
                className={selectClass}
                style={{ colorScheme: "dark" }}
              >
                {CHANNEL_OPTIONS.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </Field>
            <div className="flex items-center justify-between">
              <Label>Approval Required</Label>
              <button
                onClick={() => setField("approval_required", !data.approval_required)}
                className={`relative w-10 h-5 rounded-full transition ${
                  data.approval_required ? "bg-warroom-accent" : "bg-warroom-border"
                }`}
              >
                <span
                  className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                    data.approval_required ? "translate-x-5" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
          </>
        );

      case "ai_extract_details":
      case "ai_summarize_context":
      case "ai_prioritize_lead":
        return (
          <Field label="Goal">
            <textarea
              value={(data.goal as string) || ""}
              onChange={(e) => setField("goal", e.target.value)}
              placeholder="What should the AI do?"
              rows={4}
              className={textareaClass}
            />
          </Field>
        );

      case "approval_gate":
        return (
          <>
            <Field label="Required For (comma-separated tags)">
              <input
                value={(data.required_for as string) || ""}
                onChange={(e) => setField("required_for", e.target.value)}
                placeholder="e.g. high-value, enterprise"
                className={inputClass}
              />
            </Field>
            <Field label="Approver">
              <input
                value={(data.approver as string) || ""}
                onChange={(e) => setField("approver", e.target.value)}
                placeholder="Approver name or role"
                className={inputClass}
              />
            </Field>
            <Field label="Notes">
              <textarea
                value={(data.notes as string) || ""}
                onChange={(e) => setField("notes", e.target.value)}
                placeholder="Approval notes..."
                rows={3}
                className={textareaClass}
              />
            </Field>
          </>
        );

      case "social_reply":
        return (
          <>
            <Field label="Reply Message">
              <textarea
                value={(data.message as string) || ""}
                onChange={(e) => setField("message", e.target.value)}
                placeholder="Your public comment reply..."
                rows={3}
                className={textareaClass}
              />
            </Field>
            <p className="text-[10px] text-warroom-muted">Use {'{{commenter_name}}'} to personalize. Reply will be posted publicly under the comment.</p>
          </>
        );

      case "social_dm":
        return (
          <>
            <Field label="DM Message">
              <textarea
                value={(data.message as string) || ""}
                onChange={(e) => setField("message", e.target.value)}
                placeholder="Your private DM message..."
                rows={4}
                className={textareaClass}
              />
            </Field>
            <p className="text-[10px] text-warroom-muted">Use {'{{commenter_name}}'} to personalize. This message will be sent as a private Instagram DM.</p>
          </>
        );

      default:
        return (
          <p className="text-xs text-warroom-muted italic">No configuration available for this action type.</p>
        );
    }
  };

  return (
    <div className="space-y-4">
      <Field label="Action Type">
        <select
          value={actionType}
          onChange={(e) => {
            const newType = e.target.value;
            const actionConfig = ACTION_TYPES.find((a) => a.value === newType);
            onChange({
              actionType: newType,
              title: actionConfig?.label || "Action",
              detail: "",
            });
          }}
          className={selectClass}
          style={{ colorScheme: "dark" }}
        >
          {ACTION_TYPES.map((a) => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>
      </Field>
      <div className="border-b border-warroom-border" />
      {renderForm()}
    </div>
  );
}

/* ── Node Header Config ────────────────────────────────── */

const NODE_HEADER: Record<string, { icon: typeof Zap; label: string; color: string }> = {
  trigger: { icon: Zap, label: "Trigger", color: "text-emerald-400" },
  condition: { icon: GitBranch, label: "Condition", color: "text-violet-400" },
  action: { icon: Play, label: "Action", color: "text-blue-400" },
};

/* ── Main Panel ────────────────────────────────────────── */

export default function StepEditorPanel({ node, onSave, onClose }: StepEditorPanelProps) {
  const [editData, setEditData] = useState<Record<string, unknown>>({});

  // Sync local state when node changes
  useEffect(() => {
    if (node) {
      setEditData({ ...(node.data as Record<string, unknown>) });
    }
  }, [node]);

  const handleSave = useCallback(() => {
    if (!node) return;
    onSave(node.id, editData);
    onClose();
  }, [node, editData, onSave, onClose]);

  if (!node) return null;

  const nodeType = node.type || "action";
  const header = NODE_HEADER[nodeType] || NODE_HEADER.action;
  const Icon = header.icon;

  return (
    <>
      {/* Backdrop on mobile */}
      <div
        className="fixed inset-0 bg-black/40 z-40 md:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-[400px] bg-warroom-surface border-l border-warroom-border z-50 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200 md:relative md:z-auto md:animate-none">
        {/* Header */}
        <div className="h-14 border-b border-warroom-border flex items-center justify-between px-4 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className={`w-7 h-7 rounded-lg ${
              nodeType === "trigger" ? "bg-emerald-500/20" :
              nodeType === "condition" ? "bg-violet-500/20" :
              "bg-blue-500/20"
            } flex items-center justify-center`}>
              <Icon size={14} className={header.color} />
            </div>
            <div>
              <p className={`text-[10px] ${header.color} font-semibold uppercase tracking-wider`}>{header.label}</p>
              <p className="text-xs text-warroom-text font-medium">{node.id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-warroom-bg text-warroom-muted hover:text-warroom-text transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <div className="flex-1 overflow-y-auto p-4">
          {nodeType === "trigger" && (
            <TriggerEditor data={editData} onChange={setEditData} />
          )}
          {nodeType === "condition" && (
            <ConditionEditor data={editData} onChange={setEditData} />
          )}
          {nodeType === "action" && (
            <ActionEditor data={editData} onChange={setEditData} />
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-warroom-border px-4 py-3 flex items-center gap-2 flex-shrink-0">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 text-sm text-warroom-muted hover:text-warroom-text border border-warroom-border rounded-lg hover:bg-warroom-bg transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex-1 px-4 py-2 text-sm font-medium text-white bg-warroom-accent rounded-lg hover:bg-warroom-accent/80 transition"
          >
            Save
          </button>
        </div>
      </div>
    </>
  );
}
