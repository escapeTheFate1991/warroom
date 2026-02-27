"""CRM Product models."""

from sqlalchemy import Column, Integer, Text, Numeric, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Product(CrmBase):
    """CRM Products/Services."""
    __tablename__ = "products"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    sku = Column(Text, unique=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    quantity = Column(Integer, default=0)
    price = Column(Numeric(12, 4))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    deals = relationship("DealProduct", back_populates="product")
    quote_items = relationship("QuoteItem", back_populates="product")