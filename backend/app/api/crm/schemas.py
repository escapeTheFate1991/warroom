"""Pydantic schemas for CRM API endpoints."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, validator

from app.api.agent_contract import AgentAssignmentSummary


# Base configuration for ORM mode
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ===== User & ACL Schemas =====

class RoleResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    permission_type: str = "custom"
    permissions: List[str] = []
    created_at: datetime
    updated_at: datetime

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_type: str = "custom"
    permissions: List[str] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_type: Optional[str] = None
    permissions: Optional[List[str]] = None

class UserResponse(BaseSchema):
    id: int
    name: str
    email: str
    image: Optional[str] = None
    status: bool = True
    role_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class UserCreate(BaseModel):
    name: str
    email: str
    password_hash: Optional[str] = None
    image: Optional[str] = None
    role_id: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    image: Optional[str] = None
    status: Optional[bool] = None
    role_id: Optional[int] = None


# ===== Contact Schemas =====

class PersonResponse(BaseSchema):
    id: int
    name: str
    emails: List[Dict[str, str]] = []
    contact_numbers: Optional[List[Dict[str, str]]] = None
    job_title: Optional[str] = None
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    agent_assignments: List[AgentAssignmentSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ContactPersonResponse(PersonResponse):
    organization_name: Optional[str] = None


class CRMContactResponse(BaseSchema):
    id: int
    name: str
    email: str = ""
    phone: Optional[str] = None
    company: Optional[str] = None
    source: str = "crm"
    assigned_to: Optional[str] = None
    agent_assignments: List[AgentAssignmentSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class PersonCreate(BaseModel):
    name: str
    emails: List[Dict[str, str]] = []
    contact_numbers: Optional[List[Dict[str, str]]] = None
    job_title: Optional[str] = None
    organization_id: Optional[int] = None
    user_id: Optional[int] = None

class PersonUpdate(BaseModel):
    name: Optional[str] = None
    emails: Optional[List[Dict[str, str]]] = None
    contact_numbers: Optional[List[Dict[str, str]]] = None
    job_title: Optional[str] = None
    organization_id: Optional[int] = None
    user_id: Optional[int] = None

def _normalize_contact_list(val: Any) -> Optional[List[Dict[str, str]]]:
    """Normalize emails/contact_numbers — accept both string lists and dict lists."""
    if val is None:
        return None
    if not isinstance(val, list):
        return None
    result = []
    for item in val:
        if isinstance(item, dict):
            result.append(item)
        elif isinstance(item, str):
            result.append({"label": "primary", "value": item})
        else:
            result.append({"label": "primary", "value": str(item)})
    return result


class OrganizationResponse(BaseSchema):
    id: int
    name: str
    address: Optional[Dict[str, Any]] = None
    emails: Optional[List[Dict[str, str]]] = None
    contact_numbers: Optional[List[Dict[str, str]]] = None
    user_id: Optional[int] = None
    leadgen_lead_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @validator("emails", "contact_numbers", pre=True)
    def normalize_contacts(cls, v):
        return _normalize_contact_list(v)

class OrganizationCreate(BaseModel):
    name: str
    address: Optional[Dict[str, Any]] = None
    emails: Optional[List[Dict[str, str]]] = None
    contact_numbers: Optional[List[Dict[str, str]]] = None
    user_id: Optional[int] = None
    leadgen_lead_id: Optional[int] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    emails: Optional[List[Dict[str, str]]] = None
    contact_numbers: Optional[List[Dict[str, str]]] = None
    user_id: Optional[int] = None

class PersonSearchRequest(BaseModel):
    query: str
    search_fields: List[str] = ["name", "email", "phone"]


# ===== Deal Schemas =====

class PipelineResponse(BaseSchema):
    id: int
    name: str
    is_default: bool = False
    rotten_days: int = 30
    created_at: datetime
    updated_at: datetime

class PipelineCreate(BaseModel):
    name: str
    is_default: bool = False
    rotten_days: int = 30

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None
    rotten_days: Optional[int] = None

class PipelineStageResponse(BaseSchema):
    id: int
    code: str
    name: str
    probability: int = 0
    sort_order: int = 0
    pipeline_id: int

class PipelineStageCreate(BaseModel):
    code: str
    name: str
    probability: int = 0
    sort_order: int = 0

class PipelineStageUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    probability: Optional[int] = None
    sort_order: Optional[int] = None

class StageReorderRequest(BaseModel):
    stage_orders: List[Dict[str, int]]  # [{"id": 1, "sort_order": 1}, ...]

class DealResponse(BaseSchema):
    id: int
    title: str
    description: Optional[str] = None
    deal_value: Optional[Decimal] = None
    status: Optional[bool] = None  # None=open, True=won, False=lost
    lost_reason: Optional[str] = None
    expected_close_date: Optional[date] = None
    closed_at: Optional[datetime] = None
    user_id: Optional[int] = None
    person_id: Optional[int] = None
    organization_id: Optional[int] = None
    source_id: Optional[int] = None
    type_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    stage_id: Optional[int] = None
    leadgen_lead_id: Optional[int] = None
    person_name: Optional[str] = None
    person_phone: Optional[str] = None
    person_email: Optional[str] = None
    organization_name: Optional[str] = None
    source_name: Optional[str] = None
    type_name: Optional[str] = None
    pipeline_name: Optional[str] = None
    stage_name: Optional[str] = None
    stage_probability: int = 0
    user_name: Optional[str] = None
    agent_assignments: List[AgentAssignmentSummary] = Field(default_factory=list)
    days_in_stage: int = 0
    is_rotten: bool = False
    created_at: datetime
    updated_at: datetime

class DealCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deal_value: Optional[Decimal] = None
    expected_close_date: Optional[date] = None
    user_id: Optional[int] = None
    person_id: Optional[int] = None
    organization_id: Optional[int] = None
    source_id: Optional[int] = None
    type_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    stage_id: Optional[int] = None
    leadgen_lead_id: Optional[int] = None

class DealUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deal_value: Optional[Decimal] = None
    status: Optional[bool] = None
    lost_reason: Optional[str] = None
    expected_close_date: Optional[date] = None
    user_id: Optional[int] = None
    person_id: Optional[int] = None
    organization_id: Optional[int] = None
    source_id: Optional[int] = None
    type_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    stage_id: Optional[int] = None

class DealStageMove(BaseModel):
    stage_id: int
    
class DealForecast(BaseSchema):
    stage_id: int
    stage_name: str
    deals_count: int
    total_value: Decimal
    weighted_value: Decimal  # total_value * probability
    probability: int

class ConvertFromLeadRequest(BaseModel):
    leadgen_lead_id: int
    title: Optional[str] = None
    assigned_to: Optional[str] = None
    business_name: Optional[str] = None
    business_category: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    emails: Optional[List[str]] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    # Enrichment data to propagate
    google_place_id: Optional[str] = None
    google_rating: Optional[float] = None
    yelp_url: Optional[str] = None
    yelp_rating: Optional[float] = None
    audit_lite_flags: Optional[List[str]] = None
    website_audit_score: Optional[int] = None
    website_audit_grade: Optional[str] = None
    website_audit_summary: Optional[str] = None
    website_audit_top_fixes: Optional[List[str]] = None
    review_pain_points: Optional[List[str]] = None
    review_opportunity_flags: Optional[List[str]] = None
    lead_score: Optional[int] = None
    lead_tier: Optional[str] = None


# ===== Activity Schemas =====

class ActivityResponse(BaseSchema):
    id: int
    title: Optional[str] = None
    type: str
    comment: Optional[str] = None
    additional: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    schedule_from: Optional[datetime] = None
    schedule_to: Optional[datetime] = None
    is_done: bool = False
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class ActivityCreate(BaseModel):
    title: Optional[str] = None
    type: str
    comment: Optional[str] = None
    additional: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    schedule_from: Optional[datetime] = None
    schedule_to: Optional[datetime] = None
    user_id: Optional[int] = None

class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    comment: Optional[str] = None
    additional: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    schedule_from: Optional[datetime] = None
    schedule_to: Optional[datetime] = None
    is_done: Optional[bool] = None
    user_id: Optional[int] = None


class CommunicationHistoryTarget(BaseModel):
    person_id: Optional[int] = None
    deal_id: Optional[int] = None
    prospect_id: Optional[str] = None


class CommunicationHistoryScope(BaseModel):
    person_ids: List[int] = Field(default_factory=list)
    deal_ids: List[int] = Field(default_factory=list)
    leadgen_lead_id: Optional[int] = None


class CommunicationHistoryItem(BaseModel):
    entry_id: str
    source: str
    channel: str
    occurred_at: Optional[datetime] = None
    created_at: datetime
    title: Optional[str] = None
    content: Optional[str] = None
    linked_person_ids: List[int] = Field(default_factory=list)
    linked_deal_ids: List[int] = Field(default_factory=list)
    participant_person_ids: List[int] = Field(default_factory=list)
    direction: Optional[str] = None
    status: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    addresses: Optional[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class CommunicationHistoryResponse(BaseModel):
    target: CommunicationHistoryTarget
    resolved_scope: CommunicationHistoryScope
    items: List[CommunicationHistoryItem] = Field(default_factory=list)


# ===== Workflow Schemas =====

class WorkflowTemplateProvenance(BaseModel):
    kind: Literal["seed", "custom"] = "seed"
    seed_key: Optional[str] = None
    derived_from_template_id: Optional[int] = None
    root_template_id: Optional[int] = None
    version: int = 1


class WorkflowTemplateResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    entity_type: Optional[str] = None
    event: Optional[str] = None
    condition_type: str = "and"
    conditions: Any = Field(default_factory=list)
    actions: Any = Field(default_factory=list)
    is_seed: bool = False
    seed_key: Optional[str] = None
    version: int = 1
    provenance: WorkflowTemplateProvenance
    created_at: datetime
    updated_at: datetime


class WorkflowProvenance(BaseModel):
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    template_seed_key: Optional[str] = None
    derived_from_workflow_id: Optional[int] = None
    derived_from_workflow_name: Optional[str] = None
    root_workflow_id: Optional[int] = None
    root_workflow_name: Optional[str] = None
    version: int = 1


class WorkflowResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    event: Optional[str] = None
    condition_type: str = "and"
    conditions: Any = Field(default_factory=list)
    actions: Any = Field(default_factory=list)
    is_active: bool = True
    assigned_agent_id: Optional[int] = None
    template_id: Optional[int] = None
    derived_from_workflow_id: Optional[int] = None
    root_workflow_id: Optional[int] = None
    version: int = 1
    provenance: WorkflowProvenance
    created_at: datetime
    updated_at: datetime


class WorkflowCloneRequest(BaseModel):
    name: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    event: Optional[str] = None
    condition_type: Optional[str] = None
    conditions: Optional[Any] = None
    actions: Optional[Any] = None
    is_active: Optional[bool] = None


WorkflowEntityType = Literal["deal", "person", "activity", "email"]
WorkflowEventType = Literal["created", "updated", "deleted", "stage_changed"]
WorkflowConditionType = Literal["and", "or"]


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    entity_type: WorkflowEntityType
    event: WorkflowEventType
    condition_type: WorkflowConditionType = "and"
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    is_active: bool = True
    assigned_agent_id: Optional[int] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[WorkflowEntityType] = None
    event: Optional[WorkflowEventType] = None
    condition_type: Optional[WorkflowConditionType] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    assigned_agent_id: Optional[int] = None


# ===== Product Schemas =====

class ProductResponse(BaseSchema):
    id: int
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    quantity: int = 0
    price: Optional[Decimal] = None
    billing_interval: str = "monthly"
    features: List[str] = []
    stripe_price_id: Optional[str] = None
    is_active: bool = True
    tier_level: int = 1
    category: str = "general"
    created_at: datetime
    updated_at: datetime

class ProductCreate(BaseModel):
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    quantity: int = 0
    price: Optional[Decimal] = None
    billing_interval: str = "monthly"
    features: List[str] = []
    stripe_price_id: Optional[str] = None
    is_active: bool = True
    tier_level: int = 1
    category: str = "general"

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[Decimal] = None
    billing_interval: Optional[str] = None
    features: Optional[List[str]] = None
    stripe_price_id: Optional[str] = None
    is_active: Optional[bool] = None
    tier_level: Optional[int] = None
    category: Optional[str] = None


# ===== Email Schemas =====

class EmailResponse(BaseSchema):
    id: int
    subject: Optional[str] = None
    source: str
    name: Optional[str] = None
    reply: Optional[str] = None
    is_read: bool = False
    folders: Optional[Dict[str, Any]] = None
    from_addr: Optional[Dict[str, Any]] = None
    sender: Optional[Dict[str, Any]] = None
    reply_to: Optional[Dict[str, Any]] = None
    cc: Optional[Dict[str, Any]] = None
    bcc: Optional[Dict[str, Any]] = None
    unique_id: Optional[str] = None
    message_id: Optional[str] = None
    reference_ids: Optional[Dict[str, Any]] = None
    person_id: Optional[int] = None
    deal_id: Optional[int] = None
    parent_id: Optional[int] = None
    agent_assignments: List[AgentAssignmentSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class EmailCreate(BaseModel):
    subject: Optional[str] = None
    source: str = "web"
    name: Optional[str] = None
    reply: Optional[str] = None
    from_addr: Optional[Dict[str, Any]] = None
    sender: Optional[Dict[str, Any]] = None
    reply_to: Optional[Dict[str, Any]] = None
    cc: Optional[Dict[str, Any]] = None
    bcc: Optional[Dict[str, Any]] = None
    person_id: Optional[int] = None
    deal_id: Optional[int] = None


# ===== Marketing Schemas =====

MarketingChannel = Literal["email", "sms", "voice", "social"]

class MarketingEventResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    date: Optional[date] = None
    agent_assignments: List[AgentAssignmentSummary] = Field(default_factory=list)
    created_at: datetime

class MarketingEventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    date: Optional[date] = None

class MarketingEventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None

class MarketingCampaignResponse(BaseSchema):
    id: int
    name: str
    channel: MarketingChannel = "email"
    subject: Optional[str] = None
    status: bool = False
    type: Optional[str] = None
    use_case: Optional[str] = None
    mail_to: Optional[str] = None
    spooling: Optional[str] = None
    audience: Dict[str, Any] = Field(default_factory=dict)
    schedule: Dict[str, Any] = Field(default_factory=dict)
    content: Dict[str, Any] = Field(default_factory=dict)
    channel_config: Dict[str, Any] = Field(default_factory=dict)
    template_id: Optional[int] = None
    event_id: Optional[int] = None
    agent_assignments: List[AgentAssignmentSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class MarketingCampaignCreate(BaseModel):
    name: str
    channel: MarketingChannel = "email"
    subject: Optional[str] = None
    type: Optional[str] = None
    use_case: Optional[str] = None
    mail_to: Optional[str] = None
    audience: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    channel_config: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None
    event_id: Optional[int] = None

class MarketingCampaignUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[MarketingChannel] = None
    subject: Optional[str] = None
    status: Optional[bool] = None
    type: Optional[str] = None
    use_case: Optional[str] = None
    mail_to: Optional[str] = None
    spooling: Optional[str] = None
    audience: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    channel_config: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None
    event_id: Optional[int] = None


class EmailTemplateResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    channel: MarketingChannel = "email"
    subject: Optional[str] = None
    content: Optional[str] = None
    use_case: Optional[str] = None
    content_blocks: Dict[str, Any] = Field(default_factory=dict)
    channel_config: Dict[str, Any] = Field(default_factory=dict)
    agent_assignments: List[AgentAssignmentSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EmailTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    channel: MarketingChannel = "email"
    subject: Optional[str] = None
    content: Optional[str] = None
    use_case: Optional[str] = None
    content_blocks: Optional[Dict[str, Any]] = None
    channel_config: Optional[Dict[str, Any]] = None


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    channel: Optional[MarketingChannel] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    use_case: Optional[str] = None
    content_blocks: Optional[Dict[str, Any]] = None
    channel_config: Optional[Dict[str, Any]] = None


# ===== Attribute Schemas =====

class AttributeResponse(BaseSchema):
    id: int
    code: str
    name: str
    type: str
    lookup_type: Optional[str] = None
    entity_type: str
    sort_order: Optional[int] = None
    validation: Optional[str] = None
    is_required: bool = False
    is_unique: bool = False
    quick_add: bool = False
    is_user_defined: bool = True
    created_at: datetime

class AttributeCreate(BaseModel):
    code: str
    name: str
    type: str
    lookup_type: Optional[str] = None
    entity_type: str
    sort_order: Optional[int] = None
    validation: Optional[str] = None
    is_required: bool = False
    is_unique: bool = False
    quick_add: bool = False

class AttributeValueSet(BaseModel):
    attribute_values: Dict[int, Any]  # {attribute_id: value}


# ===== Data Management Schemas =====

class ImportRequest(BaseModel):
    entity_type: str
    file_data: str  # Base64 CSV data
    mapping: Dict[str, str]  # CSV column -> model field mapping

class ImportResponse(BaseSchema):
    id: int
    entity_type: str
    status: str
    total_rows: int = 0
    processed_rows: int = 0
    errors: List[str] = []
    created_at: datetime
    updated_at: datetime

class DeduplicateRequest(BaseModel):
    entity_type: str
    match_fields: List[str]  # Fields to match on for duplicates
    merge_strategy: str = "newest"  # "newest", "oldest", "manual"


# ===== Audit Schemas =====

class AuditLogResponse(BaseSchema):
    id: int
    entity_type: str
    entity_id: int
    action: str
    user_id: Optional[int] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    created_at: datetime