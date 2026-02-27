// Shared types for CRM components

export interface Pipeline {
  id: number;
  name: string;
  is_default: boolean;
  rotten_days: number;
}

export interface PipelineStage {
  id: number;
  code: string;
  name: string;
  probability: number;
  sort_order: number;
  pipeline_id: number;
}

export interface Deal {
  id: number;
  title: string;
  description: string | null;
  deal_value: number | null;
  status: boolean | null;
  expected_close_date: string | null;
  person_name: string | null;
  organization_name: string | null;
  stage_id: number;
  pipeline_id: number;
  created_at: string;
  updated_at: string;
  days_in_stage: number;
  is_rotten: boolean;
}

export interface DealFull {
  id: number;
  title: string;
  description: string | null;
  deal_value: number | null;
  status: boolean | null;
  lost_reason: string | null;
  expected_close_date: string | null;
  closed_at: string | null;
  person_id: number | null;
  person_name: string | null;
  organization_id: number | null;
  organization_name: string | null;
  source_id: number | null;
  source_name: string | null;
  type_id: number | null;
  type_name: string | null;
  pipeline_id: number;
  pipeline_name: string;
  stage_id: number;
  stage_name: string;
  stage_probability: number;
  user_id: number | null;
  user_name: string | null;
  created_at: string;
  updated_at: string;
  days_in_stage: number;
  is_rotten: boolean;
}

export interface Person {
  id: number;
  name: string;
  emails: any[];
  organization_id: number | null;
  organization_name?: string;
}

export interface Organization {
  id: number;
  name: string;
}

export interface LeadSource {
  id: number;
  name: string;
}

export interface LeadType {
  id: number;
  name: string;
}

export interface Activity {
  id: number;
  title: string;
  type: string;
  comment: string | null;
  schedule_from: string | null;
  schedule_to: string | null;
  is_done: boolean;
  user_name: string;
  created_at: string;
}

export interface Product {
  id: number;
  name: string;
  sku: string | null;
  price: number;
  quantity: number;
  amount: number;
}

export interface Email {
  id: number;
  subject: string;
  from_addr: any;
  is_read: boolean;
  created_at: string;
}

// Form-specific type for creating/editing deals
export interface DealFormData {
  id?: number;
  title: string;
  description: string | null;
  deal_value: number | null;
  person_id: number | null;
  organization_id: number | null;
  source_id: number | null;
  type_id: number | null;
  pipeline_id: number;
  stage_id: number;
  expected_close_date: string | null;
  status: boolean | null;
}