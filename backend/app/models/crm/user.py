"""CRM User, Role, and Group models."""

from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Role(CrmBase):
    """User roles with granular permissions."""
    __tablename__ = "roles"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)  # admin, manager, member, viewer
    description = Column(Text)
    permission_type = Column(Text, nullable=False, default='custom')  # all, custom
    permissions = Column(JSONB, default=[])
    # Permissions format: ["social:read", "social:write", "crm:read", "crm:write",
    #   "leads:read", "leads:write", "content:read", "content:write",
    #   "settings:read", "settings:write", "users:read", "users:manage",
    #   "org:manage", "billing:manage"]
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="role")


class Group(CrmBase):
    """User groups."""
    __tablename__ = "groups"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", secondary="crm.user_groups", back_populates="groups")


class User(CrmBase):
    """CRM Users with org membership and auth fields."""
    __tablename__ = "users"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text)
    image = Column(Text)
    status = Column(Boolean, default=True)  # active/inactive

    # Organization (tenant)
    org_id = Column(Integer, ForeignKey("crm.organizations_tenant.id", ondelete="SET NULL"))
    role_id = Column(Integer, ForeignKey("crm.roles.id", ondelete="SET NULL"))
    is_superadmin = Column(Boolean, default=False)  # Platform-level admin (Eddy)

    # Email verification
    email_verified = Column(Boolean, default=False)
    verification_code = Column(Text)  # 6-digit code
    verification_expires = Column(TIMESTAMP(timezone=True))

    # Password reset
    reset_code = Column(Text)  # 6-digit code
    reset_expires = Column(TIMESTAMP(timezone=True))

    # Session tracking
    last_login = Column(TIMESTAMP(timezone=True))
    login_count = Column(Integer, default=0)
    
    # Billing/Grandfathering
    is_grandfathered = Column(Boolean, default=False)  # First 100 customers locked at $99

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    org = relationship("Tenant", back_populates="members", foreign_keys=[org_id])
    role = relationship("Role", back_populates="users")
    groups = relationship("Group", secondary="crm.user_groups", back_populates="users")
    
    # CRM entities (not the tenant org)
    deals = relationship("Deal", back_populates="user")
    organizations = relationship("Organization", back_populates="user")
    persons = relationship("Person", back_populates="user")
    activities = relationship("Activity", back_populates="user")
    quotes = relationship("Quote", back_populates="user")
    tags = relationship("Tag", back_populates="user")
    saved_filters = relationship("SavedFilter", back_populates="user")

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.is_superadmin:
            return True
        if self.role and self.role.permission_type == 'all':
            return True
        if self.role and self.role.permissions:
            return permission in self.role.permissions
        return False


class UserGroup(CrmBase):
    """User-Group junction table."""
    __tablename__ = "user_groups"
    __table_args__ = {"schema": "crm"}

    group_id = Column(Integer, ForeignKey("crm.groups.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="CASCADE"), primary_key=True)
