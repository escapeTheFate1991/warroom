"""Organization (tenant) model for multi-tenant isolation."""

from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Tenant(CrmBase):
    """Tenant (Organization) — top-level multi-tenant container.
    
    Each org is fully isolated: users see only their org's data.
    Admin creates orgs and assigns users to them.
    """
    __tablename__ = "organizations_tenant"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)  # URL-friendly identifier
    domain = Column(Text)  # Optional custom domain
    logo_url = Column(Text)
    is_active = Column(Boolean, default=True)
    max_users = Column(Integer, default=10)
    plan = Column(Text, default="free")  # free, pro, enterprise
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    members = relationship("User", back_populates="org", foreign_keys="[User.org_id]")
