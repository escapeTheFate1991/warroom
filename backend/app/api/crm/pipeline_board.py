"""CRM Pipeline Board — Stage Advancement with Gated Validation."""

import json
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.deal import Deal, PipelineStage
from app.models.crm.audit import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


class StageAdvanceRequest(BaseModel):
    target_stage_id: int
    reasoning: str = Field(..., min_length=10, description="Why is this deal advancing?")
    # Gate fields (optional — validated per stage)
    contact_method: Optional[str] = None
    contact_date: Optional[date] = None
    assigned_rep: Optional[str] = None
    pain_points: Optional[str] = None
    budget_range: Optional[str] = None
    bant_score: Optional[int] = None
    meeting_date: Optional[date] = None
    attendees: Optional[str] = None
    meeting_notes: Optional[str] = None
    proposal_doc_url: Optional[str] = None
    negotiation_notes: Optional[str] = None
    payment_terms: Optional[str] = None
    lost_reason: Optional[str] = None
    follow_up_date: Optional[date] = None


# Stage gate requirements: map from target stage probability to required fields
STAGE_GATES: dict[int, list[str]] = {
    20: ["contact_method", "contact_date", "assigned_rep"],
    40: ["pain_points", "budget_range"],
    60: ["meeting_date", "attendees", "meeting_notes"],
    80: ["proposal_doc_url", "negotiation_notes"],
    100: ["payment_terms"],
    0: ["lost_reason"],
}


@router.put("/deals/{deal_id}/advance")
async def advance_deal(
    request: Request,
    deal_id: int,
    req: StageAdvanceRequest,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Advance a deal to the next stage with gated validation."""
    org_id = get_org_id(request)

    # Get current deal with its stage info
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(404, "Deal not found")

    # Get current stage
    cur_stage_result = await db.execute(
        select(PipelineStage).where(PipelineStage.id == deal.stage_id)
    )
    current_stage = cur_stage_result.scalar_one_or_none()

    # Get target stage
    tgt_result = await db.execute(
        select(PipelineStage).where(PipelineStage.id == req.target_stage_id)
    )
    target_stage = tgt_result.scalar_one_or_none()
    if not target_stage:
        raise HTTPException(404, "Target stage not found")

    # Validate: can only advance +1 stage or move to Lost (probability=0)
    if current_stage and target_stage.probability != 0:
        if target_stage.sort_order != current_stage.sort_order + 1:
            raise HTTPException(400, "Can only advance one stage at a time")

    # Validate gate requirements
    required_fields = STAGE_GATES.get(target_stage.probability, [])
    missing = [f for f in required_fields if not getattr(req, f, None)]
    if missing:
        raise HTTPException(
            400,
            f"Missing required fields for this stage: {', '.join(missing)}",
        )

    # Append gate notes to description
    gate_note = f"\n\n--- Stage Advance: {target_stage.name} ---\n"
    gate_note += f"Reasoning: {req.reasoning}\n"
    for field in required_fields:
        value = getattr(req, field, None)
        if value is not None:
            gate_note += f"{field}: {value}\n"

    deal.description = (deal.description or "") + gate_note
    deal.stage_id = req.target_stage_id
    deal.updated_at = datetime.now()

    if target_stage.probability == 100:
        deal.status = True
        deal.closed_at = datetime.now()
    elif target_stage.probability == 0:
        deal.status = False
        deal.closed_at = datetime.now()
        if req.lost_reason:
            deal.lost_reason = req.lost_reason

    # Sync linked leadgen lead when deal is won/lost
    if deal.status is not None:
        from app.services.lead_deal_sync import sync_lead_from_deal
        await sync_lead_from_deal(db, deal_id, deal.status, lost_reason=req.lost_reason)

    # Audit log
    audit = AuditLog(
        entity_type="deal",
        entity_id=deal_id,
        action="stage_advance",
        new_values={
            "stage": target_stage.name,
            "reasoning": req.reasoning,
        },
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "message": f"Deal advanced to {target_stage.name}"}

