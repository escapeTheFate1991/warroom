export const ASSIGNABLE_ENTITY_TYPES = [
  "kanban_task",
  "leadgen_lead",
  "crm_contact",
  "crm_deal",
  "prospect_workflow",
  "crm_email",
  "email_message",
  "calendar_event",
  "marketing_campaign",
  "marketing_template",
  "marketing_event",
  "social_account",
] as const;

export const ASSIGNMENT_STATUSES = [
  "queued",
  "running",
  "completed",
  "failed",
  "cancelled",
] as const;

export type AssignableEntityType = (typeof ASSIGNABLE_ENTITY_TYPES)[number];
export type AssignmentStatus = (typeof ASSIGNMENT_STATUSES)[number];

export interface AgentAssignmentSummary {
  id: string;
  agent_id: string;
  agent_name?: string | null;
  agent_emoji?: string | null;
  agent_role?: string | null;
  entity_type: AssignableEntityType;
  entity_id: string;
  title?: string | null;
  priority: number;
  status: AssignmentStatus;
  metadata: Record<string, unknown>;
  result: Record<string, unknown>;
  assigned_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface AgentSummary {
  id: string;
  name: string;
  emoji: string;
  role: string;
  description: string;
  model: string;
  skills: string[];
  config: Record<string, unknown>;
  status: string;
  openclaw_agent_id: string | null;
  soul_md: string;
  active_assignments: number;
  active_tasks: number;
  created_at: string;
  updated_at: string;
  assignments?: AgentAssignmentSummary[];
  task_assignments?: AgentAssignmentSummary[];
}