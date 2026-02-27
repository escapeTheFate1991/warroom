"""CRM Custom Attribute models (EAV pattern)."""

from sqlalchemy import Column, Integer, Text, Boolean, Date, TIMESTAMP, ForeignKey, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Attribute(CrmBase):
    """Custom attributes definition."""
    __tablename__ = "attributes"
    __table_args__ = (
        UniqueConstraint('code', 'entity_type', name='uq_attribute_code_entity'),
        {"schema": "crm"}
    )

    id = Column(Integer, primary_key=True)
    code = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)  # text, textarea, boolean, number, date, datetime, select, multiselect, email, phone, lookup
    lookup_type = Column(Text)
    entity_type = Column(Text, nullable=False)  # deal, person, organization, product, quote
    sort_order = Column(Integer)
    validation = Column(Text)
    is_required = Column(Boolean, default=False)
    is_unique = Column(Boolean, default=False)
    quick_add = Column(Boolean, default=False)
    is_user_defined = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    options = relationship("AttributeOption", back_populates="attribute", cascade="all, delete-orphan")
    values = relationship("AttributeValue", back_populates="attribute", cascade="all, delete-orphan")


class AttributeOption(CrmBase):
    """Options for select/multiselect attributes."""
    __tablename__ = "attribute_options"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    attribute_id = Column(Integer, ForeignKey("crm.attributes.id", ondelete="CASCADE"))
    name = Column(Text)
    sort_order = Column(Integer)

    # Relationships
    attribute = relationship("Attribute", back_populates="options")


class AttributeValue(CrmBase):
    """Attribute values for entities (EAV pattern)."""
    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'attribute_id', name='uq_attribute_value_entity'),
        {"schema": "crm"}
    )

    id = Column(Integer, primary_key=True)
    entity_type = Column(Text, default='deals')
    entity_id = Column(Integer, nullable=False)
    attribute_id = Column(Integer, ForeignKey("crm.attributes.id", ondelete="CASCADE"))
    text_value = Column(Text)
    boolean_value = Column(Boolean)
    integer_value = Column(Integer)
    float_value = Column(Float)
    datetime_value = Column(TIMESTAMP(timezone=True))
    date_value = Column(Date)
    json_value = Column(JSONB)

    # Relationships
    attribute = relationship("Attribute", back_populates="values")