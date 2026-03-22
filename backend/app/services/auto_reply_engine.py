"""Auto-reply matching engine — scans text against keyword rules and selects replies."""

import logging
import random

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm.auto_reply import AutoReplyLog, AutoReplyRule

logger = logging.getLogger(__name__)


class AutoReplyEngine:
    """Keyword-based auto-reply matching engine."""

    @staticmethod
    def _text_contains_keyword(text: str, keyword: str, case_sensitive: bool) -> bool:
        if case_sensitive:
            return keyword in text
        return keyword.lower() in text.lower()

    @staticmethod
    def _match_any(text: str, keywords: list[str], case_sensitive: bool) -> str | None:
        """Return first matched keyword, or None."""
        for kw in keywords:
            if AutoReplyEngine._text_contains_keyword(text, kw, case_sensitive):
                return kw
        return None

    @staticmethod
    def _match_all(text: str, keywords: list[str], case_sensitive: bool) -> str | None:
        """Return comma-joined keywords if ALL match, else None."""
        for kw in keywords:
            if not AutoReplyEngine._text_contains_keyword(text, kw, case_sensitive):
                return None
        return ", ".join(keywords)

    @staticmethod
    def _match_exact(text: str, keywords: list[str], case_sensitive: bool) -> str | None:
        """Return matched keyword if any keyword is an exact phrase match in text."""
        for kw in keywords:
            if case_sensitive:
                if kw == text or kw in text:
                    return kw
            else:
                if kw.lower() == text.lower() or kw.lower() in text.lower():
                    return kw
        return None

    @staticmethod
    async def find_matching_rule(
        db: AsyncSession,
        org_id: int,
        platform: str,
        rule_type: str,
        text: str,
        commenter_name: str = "",
    ) -> tuple[AutoReplyRule, str, str] | None:
        """Find the first active rule matching the text.

        Returns (rule, matched_keyword, selected_reply) or None.
        """
        result = await db.execute(
            select(AutoReplyRule).where(
                AutoReplyRule.org_id == org_id,
                or_(AutoReplyRule.platform == platform, AutoReplyRule.platform == "all"),
                or_(AutoReplyRule.rule_type == rule_type, AutoReplyRule.rule_type == "both"),
                AutoReplyRule.is_active == True,
            ).order_by(AutoReplyRule.id)
        )
        rules = result.scalars().all()

        for rule in rules:
            matched_keyword = None

            if rule.match_mode == "any":
                matched_keyword = AutoReplyEngine._match_any(text, rule.keywords, rule.case_sensitive)
            elif rule.match_mode == "all":
                matched_keyword = AutoReplyEngine._match_all(text, rule.keywords, rule.case_sensitive)
            elif rule.match_mode == "exact":
                matched_keyword = AutoReplyEngine._match_exact(text, rule.keywords, rule.case_sensitive)

            if matched_keyword is not None:
                selected_reply = random.choice(rule.replies)
                # Template variable replacement
                selected_reply = selected_reply.replace("{{commenter_name}}", commenter_name)
                return (rule, matched_keyword, selected_reply)

        return None

    @staticmethod
    async def check_duplicate(db: AsyncSession, org_id: int, external_id: str) -> bool:
        """Check if we already processed this external_id."""
        result = await db.execute(
            select(AutoReplyLog.id).where(
                AutoReplyLog.org_id == org_id,
                AutoReplyLog.external_id == external_id,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def log_reply(
        db: AsyncSession,
        rule_id: int | None,
        org_id: int,
        platform: str,
        rule_type: str,
        original_text: str,
        matched_keyword: str | None,
        reply_sent: str | None,
        social_account_id: int | None,
        external_id: str | None,
        status: str,
        error_message: str | None = None,
    ) -> AutoReplyLog:
        """Insert into auto_reply_log and return the entry."""
        entry = AutoReplyLog(
            rule_id=rule_id,
            org_id=org_id,
            platform=platform,
            rule_type=rule_type,
            original_text=original_text,
            matched_keyword=matched_keyword,
            reply_sent=reply_sent,
            social_account_id=social_account_id,
            external_id=external_id,
            status=status,
            error_message=error_message,
        )
        db.add(entry)
        await db.flush()
        return entry
