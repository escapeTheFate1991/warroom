"""Social accounts model for multi-account management."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class SocialAccountsBase(DeclarativeBase):
    pass


class SocialAccount(SocialAccountsBase):
    """Model for storing encrypted social media credentials."""
    __tablename__ = "social_accounts"
    __table_args__ = (
        Index("ix_social_accounts_org_id", "org_id"),
        Index("ix_social_accounts_platform", "platform"),
        Index("ix_social_accounts_status", "status"),
        {"schema": "public"},
    )

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # 'instagram', 'tiktok', etc.
    account_type = Column(String(20), nullable=False)  # 'scraping', 'posting', 'primary'
    username = Column(String(255), nullable=False)
    password_encrypted = Column(Text, nullable=True)  # encrypted storage
    totp_secret_encrypted = Column(Text, nullable=True)  # encrypted 2FA secret
    status = Column(String(20), nullable=False, default="active")  # active, disabled, expired
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    notes = Column(Text, nullable=True)