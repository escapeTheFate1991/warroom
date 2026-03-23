"""Auto-reply rules CRUD and log/stats endpoints."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.crm_db import get_tenant_db
from app.models.crm.auto_reply import AutoReplyLog, AutoReplyRule
from app.models.crm.user import User
from app.services.tenant import get_org_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    platform: str = "instagram"
    rule_type: str  # 'comment', 'dm', or 'follow'
    name: str
    keywords: List[str] = []  # Optional for follow triggers
    replies: List[str]
    match_mode: Optional[str] = "any"
    case_sensitive: bool = False
    is_active: bool = True
    delivery_channels: List[str] = ["dm"]  # comment, dm, or both

    @field_validator("replies")
    @classmethod
    def replies_not_empty(cls, v):
        if not v:
            raise ValueError("replies must be a non-empty array")
        return v

    @field_validator("rule_type")
    @classmethod
    def valid_rule_type(cls, v):
        if v not in ("comment", "dm", "follow"):
            raise ValueError("rule_type must be 'comment', 'dm', or 'follow'")
        return v

    @field_validator("match_mode")
    @classmethod
    def valid_match_mode(cls, v):
        if v and v not in ("any", "all", "exact"):
            raise ValueError("match_mode must be 'any', 'all', or 'exact'")
        return v

    @field_validator("delivery_channels")
    @classmethod
    def valid_delivery_channels(cls, v):
        if not v:
            raise ValueError("delivery_channels must not be empty")
        for channel in v:
            if channel not in ("comment", "dm"):
                raise ValueError("delivery_channels must contain only 'comment' or 'dm'")
        return v

    @classmethod
    def model_validate(cls, obj):
        """Cross-field validation."""
        result = super().model_validate(obj)
        # Follow rules must have no keywords and DM delivery only
        if result.rule_type == "follow":
            if result.keywords:
                raise ValueError("follow rules cannot have keywords")
            if "dm" not in result.delivery_channels:
                raise ValueError("follow rules must include 'dm' in delivery_channels")
        else:
            # Comment/DM rules must have keywords
            if not result.keywords:
                raise ValueError("comment/dm rules must have keywords")
        return result


class RuleUpdate(BaseModel):
    platform: Optional[str] = None
    rule_type: Optional[str] = None
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    replies: Optional[List[str]] = None
    match_mode: Optional[str] = None
    case_sensitive: Optional[bool] = None
    is_active: Optional[bool] = None
    delivery_channels: Optional[List[str]] = None

    @field_validator("replies")
    @classmethod
    def replies_not_empty(cls, v):
        if v is not None and not v:
            raise ValueError("replies must be a non-empty array")
        return v

    @field_validator("rule_type")
    @classmethod
    def valid_rule_type(cls, v):
        if v is not None and v not in ("comment", "dm", "follow"):
            raise ValueError("rule_type must be 'comment', 'dm', or 'follow'")
        return v

    @field_validator("match_mode")
    @classmethod
    def valid_match_mode(cls, v):
        if v is not None and v not in ("any", "all", "exact"):
            raise ValueError("match_mode must be 'any', 'all', or 'exact'")
        return v

    @field_validator("delivery_channels")
    @classmethod
    def valid_delivery_channels(cls, v):
        if v is not None:
            if not v:
                raise ValueError("delivery_channels must not be empty")
            for channel in v:
                if channel not in ("comment", "dm"):
                    raise ValueError("delivery_channels must contain only 'comment' or 'dm'")
        return v


# ── Helpers ──────────────────────────────────────────────────────────

def _serialize_rule(rule: AutoReplyRule) -> dict:
    return {
        "id": rule.id,
        "org_id": rule.org_id,
        "platform": rule.platform,
        "rule_type": rule.rule_type,
        "name": rule.name,
        "keywords": rule.keywords or [],
        "replies": rule.replies or [],
        "match_mode": rule.match_mode,
        "case_sensitive": rule.case_sensitive,
        "is_active": rule.is_active,
        "delivery_channels": rule.delivery_channels or ["dm"],
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def _serialize_log(entry: AutoReplyLog) -> dict:
    return {
        "id": entry.id,
        "rule_id": entry.rule_id,
        "org_id": entry.org_id,
        "platform": entry.platform,
        "rule_type": entry.rule_type,
        "trigger_type": entry.trigger_type or "keyword",
        "original_text": entry.original_text or "",
        "matched_keyword": entry.matched_keyword,
        "reply_sent": entry.reply_sent,
        "delivery_channel": entry.delivery_channel,
        "social_account_id": entry.social_account_id,
        "external_id": entry.external_id,
        "username": entry.username,
        "status": entry.status,
        "error_message": entry.error_message,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


async def _get_rule(db: AsyncSession, rule_id: int, org_id: int) -> AutoReplyRule:
    result = await db.execute(
        select(AutoReplyRule).where(
            AutoReplyRule.id == rule_id,
            AutoReplyRule.org_id == org_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/rules")
async def create_rule(
    request: Request,
    data: RuleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    
    # Validate follow rule constraints
    if data.rule_type == "follow":
        if data.keywords:
            raise HTTPException(status_code=422, detail="Follow rules cannot have keywords")
        if "dm" not in data.delivery_channels:
            raise HTTPException(status_code=422, detail="Follow rules must include 'dm' in delivery_channels")
    else:
        if not data.keywords:
            raise HTTPException(status_code=422, detail="Comment/DM rules must have keywords")
    
    rule = AutoReplyRule(
        org_id=org_id,
        platform=data.platform,
        rule_type=data.rule_type,
        name=data.name,
        keywords=data.keywords if data.rule_type != "follow" else [],
        replies=data.replies,
        match_mode=data.match_mode if data.rule_type != "follow" else None,
        case_sensitive=data.case_sensitive,
        is_active=data.is_active,
        delivery_channels=data.delivery_channels,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _serialize_rule(rule)


@router.get("/rules")
async def list_rules(
    request: Request,
    platform: Optional[str] = None,
    rule_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    query = select(AutoReplyRule).where(AutoReplyRule.org_id == org_id)
    if platform is not None:
        query = query.where(AutoReplyRule.platform == platform)
    if rule_type is not None:
        query = query.where(AutoReplyRule.rule_type == rule_type)
    if is_active is not None:
        query = query.where(AutoReplyRule.is_active == is_active)
    query = query.order_by(AutoReplyRule.created_at.desc())
    result = await db.execute(query)
    return [_serialize_rule(r) for r in result.scalars().all()]


@router.get("/rules/{rule_id}")
async def get_rule(
    request: Request,
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    rule = await _get_rule(db, rule_id, org_id)
    return _serialize_rule(rule)


@router.put("/rules/{rule_id}")
async def update_rule(
    request: Request,
    rule_id: int,
    data: RuleUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    rule = await _get_rule(db, rule_id, org_id)
    update_data = data.model_dump(exclude_unset=True)
    
    # Apply updates, but validate constraints
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    # Validate follow rule constraints after update
    if rule.rule_type == "follow":
        if rule.keywords:
            rule.keywords = []  # Clear keywords for follow rules
        if "dm" not in rule.delivery_channels:
            raise HTTPException(status_code=422, detail="Follow rules must include 'dm' in delivery_channels")
        rule.match_mode = None  # Clear match_mode for follow rules
    else:
        if not rule.keywords:
            raise HTTPException(status_code=422, detail="Comment/DM rules must have keywords")
    
    await db.commit()
    await db.refresh(rule)
    return _serialize_rule(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(
    request: Request,
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    rule = await _get_rule(db, rule_id, org_id)
    await db.delete(rule)
    await db.commit()
    return {"status": "deleted", "rule_id": rule_id}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(
    request: Request,
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    rule = await _get_rule(db, rule_id, org_id)
    rule.is_active = not rule.is_active
    await db.commit()
    await db.refresh(rule)
    return _serialize_rule(rule)


@router.get("/log")
async def list_log(
    request: Request,
    platform: Optional[str] = None,
    rule_type: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    query = select(AutoReplyLog).where(AutoReplyLog.org_id == org_id)
    if platform is not None:
        query = query.where(AutoReplyLog.platform == platform)
    if rule_type is not None:
        query = query.where(AutoReplyLog.rule_type == rule_type)
    query = query.order_by(AutoReplyLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return [_serialize_log(e) for e in result.scalars().all()]


@router.get("/stats")
async def get_stats(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    org_id = get_org_id(request)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Total replies sent
    total_result = await db.execute(
        select(func.count(AutoReplyLog.id)).where(
            AutoReplyLog.org_id == org_id,
            AutoReplyLog.status == "sent",
        )
    )
    total_replies = total_result.scalar() or 0

    # Replies today
    today_result = await db.execute(
        select(func.count(AutoReplyLog.id)).where(
            AutoReplyLog.org_id == org_id,
            AutoReplyLog.status == "sent",
            AutoReplyLog.created_at >= today_start,
        )
    )
    replies_today = today_result.scalar() or 0

    # Replies this week
    week_result = await db.execute(
        select(func.count(AutoReplyLog.id)).where(
            AutoReplyLog.org_id == org_id,
            AutoReplyLog.status == "sent",
            AutoReplyLog.created_at >= week_start,
        )
    )
    replies_this_week = week_result.scalar() or 0

    # Top rules by usage count
    top_rules_result = await db.execute(
        select(
            AutoReplyLog.rule_id,
            AutoReplyRule.name,
            func.count(AutoReplyLog.id).label("count"),
        )
        .join(AutoReplyRule, AutoReplyLog.rule_id == AutoReplyRule.id, isouter=True)
        .where(
            AutoReplyLog.org_id == org_id,
            AutoReplyLog.status == "sent",
            AutoReplyLog.rule_id.isnot(None),
        )
        .group_by(AutoReplyLog.rule_id, AutoReplyRule.name)
        .order_by(func.count(AutoReplyLog.id).desc())
        .limit(10)
    )
    top_rules = [
        {"rule_id": row.rule_id, "name": row.name, "count": row.count}
        for row in top_rules_result.all()
    ]

    # By platform breakdown
    platform_result = await db.execute(
        select(
            AutoReplyLog.platform,
            func.count(AutoReplyLog.id).label("count"),
        )
        .where(
            AutoReplyLog.org_id == org_id,
            AutoReplyLog.status == "sent",
        )
        .group_by(AutoReplyLog.platform)
    )
    by_platform = {row.platform: row.count for row in platform_result.all()}

    return {
        "total_replies_sent": total_replies,
        "replies_today": replies_today,
        "replies_this_week": replies_this_week,
        "top_rules": top_rules,
        "by_platform": by_platform,
    }
