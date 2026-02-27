"""CRM Quote models."""

from sqlalchemy import Column, Integer, Text, Numeric, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Quote(CrmBase):
    """CRM Quotes."""
    __tablename__ = "quotes"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    subject = Column(Text, nullable=False)
    description = Column(Text)
    billing_address = Column(JSONB)
    shipping_address = Column(JSONB)
    discount_percent = Column(Numeric(12, 4), default=0)
    discount_amount = Column(Numeric(12, 4))
    tax_amount = Column(Numeric(12, 4))
    adjustment_amount = Column(Numeric(12, 4))
    sub_total = Column(Numeric(12, 4))
    grand_total = Column(Numeric(12, 4))
    expired_at = Column(TIMESTAMP(timezone=True))
    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="SET NULL"))
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    person = relationship("Person", back_populates="quotes")
    user = relationship("User", back_populates="quotes")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
    deals = relationship("Deal", secondary="crm.deal_quotes", back_populates="quotes")


class QuoteItem(CrmBase):
    """Quote line items."""
    __tablename__ = "quote_items"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    quote_id = Column(Integer, ForeignKey("crm.quotes.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("crm.products.id", ondelete="SET NULL"))
    sku = Column(Text)
    name = Column(Text)
    quantity = Column(Integer, default=1)
    price = Column(Numeric(12, 4), default=0)
    discount_percent = Column(Numeric(12, 4), default=0)
    discount_amount = Column(Numeric(12, 4), default=0)
    tax_percent = Column(Numeric(12, 4), default=0)
    tax_amount = Column(Numeric(12, 4), default=0)
    total = Column(Numeric(12, 4), default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    quote = relationship("Quote", back_populates="items")
    product = relationship("Product", back_populates="quote_items")


class DealQuote(CrmBase):
    """Deal-Quote junction table."""
    __tablename__ = "deal_quotes"
    __table_args__ = {"schema": "crm"}

    deal_id = Column(Integer, ForeignKey("crm.deals.id", ondelete="CASCADE"), primary_key=True)
    quote_id = Column(Integer, ForeignKey("crm.quotes.id", ondelete="CASCADE"), primary_key=True)