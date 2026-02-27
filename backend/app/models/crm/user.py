"""CRM User, Role, and Group models."""

from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Role(CrmBase):
    """User roles with permissions."""
    __tablename__ = "roles"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    permission_type = Column(Text, nullable=False, default='custom')  # all, custom
    permissions = Column(JSONB, default=[])
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="role")


class Group(CrmBase):
    """User groups."""
    __tablename__ = "groups"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", secondary="crm.user_groups", back_populates="groups")


class User(CrmBase):
    """CRM Users."""
    __tablename__ = "users"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text)
    image = Column(Text)
    status = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("crm.roles.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    role = relationship("Role", back_populates="users")
    groups = relationship("Group", secondary="crm.user_groups", back_populates="users")
    
    # Related entities
    deals = relationship("Deal", back_populates="user")
    organizations = relationship("Organization", back_populates="user")
    persons = relationship("Person", back_populates="user")
    activities = relationship("Activity", back_populates="user")
    quotes = relationship("Quote", back_populates="user")
    tags = relationship("Tag", back_populates="user")
    saved_filters = relationship("SavedFilter", back_populates="user")


class UserGroup(CrmBase):
    """User-Group junction table."""
    __tablename__ = "user_groups"
    __table_args__ = {"schema": "crm"}

    group_id = Column(Integer, ForeignKey("crm.groups.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="CASCADE"), primary_key=True)