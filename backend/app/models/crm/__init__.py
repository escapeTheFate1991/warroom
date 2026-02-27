"""CRM SQLAlchemy Models"""

from sqlalchemy.orm import DeclarativeBase

class CrmBase(DeclarativeBase):
    """Base class for all CRM models with crm schema."""
    pass

# Import all models to make them available
from .user import User, Role, Group, UserGroup
from .contact import Person, Organization, Tag, PersonTag, DealTag
from .deal import Deal, Pipeline, PipelineStage, LeadSource, LeadType, DealProduct
from .activity import Activity, ActivityParticipant, DealActivity, PersonActivity
from .product import Product
from .email import Email, EmailAttachment, EmailTemplate
from .marketing import MarketingCampaign, MarketingEvent
from .quote import Quote, QuoteItem, DealQuote
from .attribute import Attribute, AttributeOption, AttributeValue
from .automation import Workflow, Webhook
from .audit import AuditLog, Import, SavedFilter

__all__ = [
    "CrmBase",
    "User", "Role", "Group", "UserGroup",
    "Person", "Organization", "Tag", "PersonTag", "DealTag",
    "Deal", "Pipeline", "PipelineStage", "LeadSource", "LeadType", "DealProduct",
    "Activity", "ActivityParticipant", "DealActivity", "PersonActivity",
    "Product",
    "Email", "EmailAttachment", "EmailTemplate",
    "MarketingCampaign", "MarketingEvent",
    "Quote", "QuoteItem", "DealQuote",
    "Attribute", "AttributeOption", "AttributeValue",
    "Workflow", "Webhook",
    "AuditLog", "Import", "SavedFilter"
]