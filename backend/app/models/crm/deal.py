"""CRM Deal models - Deal, Pipeline, Stages, Sources, Types."""

from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, Date, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Pipeline(CrmBase):
    """Sales pipelines."""
    __tablename__ = "pipelines"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    rotten_days = Column(Integer, default=30)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    stages = relationship("PipelineStage", back_populates="pipeline", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="pipeline")


class PipelineStage(CrmBase):
    """Pipeline stages."""
    __tablename__ = "pipeline_stages"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    code = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    probability = Column(Integer, default=0)  # 0-100%
    sort_order = Column(Integer, default=0)
    pipeline_id = Column(Integer, ForeignKey("crm.pipelines.id", ondelete="CASCADE"))

    # Relationships
    pipeline = relationship("Pipeline", back_populates="stages")
    deals = relationship("Deal", back_populates="stage")


class LeadSource(CrmBase):
    """Lead sources."""
    __tablename__ = "lead_sources"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    deals = relationship("Deal", back_populates="source")


class LeadType(CrmBase):
    """Lead types."""
    __tablename__ = "lead_types"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    deals = relationship("Deal", back_populates="type")


class Deal(CrmBase):
    """CRM Deals (sales opportunities)."""
    __tablename__ = "deals"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    deal_value = Column(Numeric(12, 4))
    status = Column(Boolean)  # NULL=open, true=won, false=lost
    lost_reason = Column(Text)
    expected_close_date = Column(Date)
    closed_at = Column(TIMESTAMP(timezone=True))
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="SET NULL"))
    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="SET NULL"))
    organization_id = Column(Integer, ForeignKey("crm.organizations.id", ondelete="SET NULL"))
    source_id = Column(Integer, ForeignKey("crm.lead_sources.id", ondelete="SET NULL"))
    type_id = Column(Integer, ForeignKey("crm.lead_types.id", ondelete="SET NULL"))
    pipeline_id = Column(Integer, ForeignKey("crm.pipelines.id", ondelete="SET NULL"))
    stage_id = Column(Integer, ForeignKey("crm.pipeline_stages.id", ondelete="SET NULL"))
    
    # Link to leadgen if deal originated from a lead
    leadgen_lead_id = Column(Integer)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="deals")
    person = relationship("Person", back_populates="deals")
    organization = relationship("Organization", back_populates="deals")
    source = relationship("LeadSource", back_populates="deals")
    type = relationship("LeadType", back_populates="deals")
    pipeline = relationship("Pipeline", back_populates="deals")
    stage = relationship("PipelineStage", back_populates="deals")
    
    # Related entities
    products = relationship("DealProduct", back_populates="deal", cascade="all, delete-orphan")
    activities = relationship("Activity", secondary="crm.deal_activities", back_populates="deals")
    emails = relationship("Email", back_populates="deal")
    quotes = relationship("Quote", secondary="crm.deal_quotes", back_populates="deals")
    tags = relationship("Tag", secondary="crm.deal_tags", back_populates="deals")


class DealProduct(CrmBase):
    """Deal-Product junction with quantities and pricing."""
    __tablename__ = "deal_products"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("crm.deals.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("crm.products.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)
    price = Column(Numeric(12, 4))
    amount = Column(Numeric(12, 4))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    deal = relationship("Deal", back_populates="products")
    product = relationship("Product", back_populates="deals")