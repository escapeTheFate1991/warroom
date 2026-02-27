"""Pydantic schemas for CRM API endpoints."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


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

class OrganizationResponse(BaseSchema):
    id: int
    name: str
    address: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    leadgen_lead_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class OrganizationCreate(BaseModel):
    name: str
    address: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    leadgen_lead_id: Optional[int] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
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


# ===== Product Schemas =====

class ProductResponse(BaseSchema):
    id: int
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    quantity: int = 0
    price: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

class ProductCreate(BaseModel):
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    quantity: int = 0
    price: Optional[Decimal] = None

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[Decimal] = None


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

class MarketingEventResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    date: Optional[date] = None
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
    subject: Optional[str] = None
    status: bool = False
    type: Optional[str] = None
    mail_to: Optional[str] = None
    spooling: Optional[str] = None
    template_id: Optional[int] = None
    event_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class MarketingCampaignCreate(BaseModel):
    name: str
    subject: Optional[str] = None
    type: Optional[str] = None
    mail_to: Optional[str] = None
    template_id: Optional[int] = None
    event_id: Optional[int] = None

class MarketingCampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[bool] = None
    type: Optional[str] = None
    mail_to: Optional[str] = None
    spooling: Optional[str] = None
    template_id: Optional[int] = None
    event_id: Optional[int] = None


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