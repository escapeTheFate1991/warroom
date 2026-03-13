"""Bidirectional sync between CRM deals and leadgen leads.

When a deal status changes (won/lost), the linked lead's outreach_status
is updated to match, and vice-versa.
"""

import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Mapping: deal status (bool|None) -> lead outreach_status
_DEAL_STATUS_TO_LEAD = {
    True: "won",
    False: "lost",
    None: "in_progress",  # re-opened deal
}

# Mapping: lead outreach_status -> deal status (bool|None)
_LEAD_STATUS_TO_DEAL = {
    "won": True,
    "lost": False,
    "in_progress": None,
    "contacted": None,
    "none": None,
}


async def sync_lead_from_deal(db: AsyncSession, deal_id: int, deal_status: bool | None,
                               lost_reason: str | None = None) -> None:
    """Update the linked leadgen lead when a deal's status changes.

    Call this from any CRM endpoint that sets deal.status (pipeline_board, deals).
    The session can be either a CRM or leadgen session — we use fully-qualified
    schema names so it works from either search_path.
    """
    # Look up the leadgen_lead_id on the deal
    row = await db.execute(
        text("SELECT leadgen_lead_id FROM crm.deals WHERE id = :did"),
        {"did": deal_id},
    )
    result = row.scalar_one_or_none()
    if not result:
        return  # no linked lead

    lead_id = result
    new_outreach = _DEAL_STATUS_TO_LEAD.get(deal_status, "in_progress")

    await db.execute(
        text("""
            UPDATE leadgen.leads
               SET outreach_status = :status,
                   contact_outcome = :outcome,
                   contact_notes   = COALESCE(contact_notes, '') ||
                                     CASE WHEN :note != '' THEN E'\\n[Deal sync] ' || :note ELSE '' END,
                   updated_at      = :now
             WHERE id = :lid
        """),
        {
            "status": new_outreach,
            "outcome": new_outreach,
            "note": lost_reason or "",
            "now": datetime.now(),
            "lid": lead_id,
        },
    )
    logger.info("Synced lead %d outreach_status→%s from deal %d", lead_id, new_outreach, deal_id)


async def sync_deal_from_lead(db: AsyncSession, lead_id: int,
                               outreach_status: str,
                               lost_reason: str | None = None) -> None:
    """Update any linked CRM deal when a lead's outreach_status changes.

    Call this from the leadgen log_contact endpoint.
    """
    deal_status = _LEAD_STATUS_TO_DEAL.get(outreach_status)

    # Find deals linked to this lead
    rows = await db.execute(
        text("SELECT id FROM crm.deals WHERE leadgen_lead_id = :lid"),
        {"lid": lead_id},
    )
    deal_ids = [r[0] for r in rows.fetchall()]
    if not deal_ids:
        return

    now = datetime.now()
    for did in deal_ids:
        updates = {
            "status": deal_status,
            "now": now,
            "did": did,
        }
        extra_cols = ""
        if deal_status is not None:
            extra_cols += ", closed_at = :now"
        if outreach_status == "lost" and lost_reason:
            extra_cols += ", lost_reason = :reason"
            updates["reason"] = lost_reason

        await db.execute(
            text(f"""
                UPDATE crm.deals
                   SET status     = :status,
                       updated_at = :now
                       {extra_cols}
                 WHERE id = :did
            """),
            updates,
        )
        logger.info("Synced deal %d status→%s from lead %d", did, deal_status, lead_id)

