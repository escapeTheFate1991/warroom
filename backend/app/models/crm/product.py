"""CRM Product models."""

from sqlalchemy import Column, Integer, Text, Numeric, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Product(CrmBase):
    """CRM Products/Services."""
    __tablename__ = "products"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    sku = Column(Text, unique=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    quantity = Column(Integer, default=0)
    price = Column(Numeric(12, 4))
    
    # New fields for pricing tiers
    billing_interval = Column(Text, default='monthly')  # monthly, yearly, one-time
    features = Column(JSONB, default=[])  # List of feature strings
    stripe_price_id = Column(Text)  # Stripe price ID for billing
    is_active = Column(Boolean, default=True)  # Enable/disable product
    tier_level = Column(Integer, default=1)  # 1=Starter, 2=Professional, 3=Enterprise
    category = Column(Text, default='general')  # e.g., 'ai-automation', 'crm', etc.
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    deals = relationship("DealProduct", back_populates="product")
    quote_items = relationship("QuoteItem", back_populates="product")