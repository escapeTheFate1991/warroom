"""Settings model — key-value store for app configuration."""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class SettingsBase(DeclarativeBase):
    pass


class Setting(SettingsBase):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")
    category = Column(String(100), nullable=False, default="general")
    description = Column(Text, nullable=True)
    is_secret = Column(Integer, nullable=False, default=0)  # 1 = mask in API responses
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
