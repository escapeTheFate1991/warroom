"""CRM Pipelines API endpoints."""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_crm_db
from app.models.crm.deal import Pipeline, PipelineStage
from app.models.crm.audit import AuditLog
from .schemas import (
    PipelineResponse, PipelineCreate, PipelineUpdate,
    PipelineStageResponse, PipelineStageCreate, PipelineStageUpdate,
    StageReorderRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def log_audit(db: AsyncSession, entity_type: str, entity_id: int, action: str, 
                   user_id: Optional[int] = None, old_values: dict = None, new_values: dict = None):
    """Log audit trail for CRM operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        old_values=old_values,
        new_values=new_values
    )
    db.add(audit_log)


# ===== Pipelines CRUD =====

@router.get("/pipelines", response_model=List[PipelineResponse])
async def list_pipelines(db: AsyncSession = Depends(get_crm_db)):
    """List all pipelines."""
    result = await db.execute(
        select(Pipeline)
        .options(selectinload(Pipeline.stages))
        .order_by(Pipeline.is_default.desc(), Pipeline.name)
    )
    return result.scalars().all()


@router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single pipeline with stages."""
    result = await db.execute(
        select(Pipeline)
        .options(selectinload(Pipeline.stages))
        .where(Pipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    return pipeline


@router.post("/pipelines", response_model=PipelineResponse)
async def create_pipeline(pipeline_data: PipelineCreate, user_id: Optional[int] = None,
                         db: AsyncSession = Depends(get_crm_db)):
    """Create a new pipeline."""
    # If this is set as default, unset other defaults
    if pipeline_data.is_default:
        await db.execute(
            update(Pipeline).where(Pipeline.is_default == True).values(is_default=False)
        )
    
    pipeline = Pipeline(**pipeline_data.model_dump(exclude_unset=True))
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    
    # Create default stages if none exist
    if pipeline_data.is_default or not pipeline.stages:
        default_stages = [
            {"code": "new", "name": "New", "probability": 10, "sort_order": 1},
            {"code": "contacted", "name": "Contacted", "probability": 20, "sort_order": 2},
            {"code": "qualified", "name": "Qualified", "probability": 40, "sort_order": 3},
            {"code": "proposal", "name": "Proposal Made", "probability": 60, "sort_order": 4},
            {"code": "negotiation", "name": "Negotiation", "probability": 80, "sort_order": 5},
            {"code": "won", "name": "Won", "probability": 100, "sort_order": 6},
            {"code": "lost", "name": "Lost", "probability": 0, "sort_order": 7},
        ]
        
        for stage_data in default_stages:
            stage = PipelineStage(**stage_data, pipeline_id=pipeline.id)
            db.add(stage)
        
        await db.commit()
    
    # Log audit
    await log_audit(db, "pipeline", pipeline.id, "created", user_id, 
                   new_values=pipeline_data.model_dump())
    await db.commit()
    
    return pipeline


@router.put("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(pipeline_id: int, pipeline_data: PipelineUpdate, 
                         user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing pipeline."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Store old values for audit
    old_values = {
        "name": pipeline.name,
        "is_default": pipeline.is_default,
        "rotten_days": pipeline.rotten_days
    }
    
    # If setting as default, unset other defaults
    if pipeline_data.is_default and not pipeline.is_default:
        await db.execute(
            update(Pipeline).where(Pipeline.id != pipeline_id).values(is_default=False)
        )
    
    # Update fields
    update_data = pipeline_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pipeline, field, value)
    
    pipeline.updated_at = datetime.now()
    await db.commit()
    await db.refresh(pipeline)
    
    # Log audit
    await log_audit(db, "pipeline", pipeline.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return pipeline


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: int, user_id: Optional[int] = None,
                         db: AsyncSession = Depends(get_crm_db)):
    """Delete a pipeline."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    if pipeline.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default pipeline")
    
    # Check if pipeline has deals
    from app.models.crm.deal import Deal
    deals_count = await db.execute(select(Deal).where(Deal.pipeline_id == pipeline_id))
    if deals_count.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cannot delete pipeline with existing deals")
    
    old_values = {"name": pipeline.name, "is_default": pipeline.is_default}
    await db.execute(delete(Pipeline).where(Pipeline.id == pipeline_id))
    
    # Log audit
    await log_audit(db, "pipeline", pipeline_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "pipeline_id": pipeline_id}


# ===== Pipeline Stages CRUD =====

@router.get("/pipelines/{pipeline_id}/stages", response_model=List[PipelineStageResponse])
async def list_pipeline_stages(pipeline_id: int, db: AsyncSession = Depends(get_crm_db)):
    """List stages for a pipeline."""
    # Verify pipeline exists
    pipeline_result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    if not pipeline_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    result = await db.execute(
        select(PipelineStage)
        .where(PipelineStage.pipeline_id == pipeline_id)
        .order_by(PipelineStage.sort_order)
    )
    return result.scalars().all()


@router.post("/pipelines/{pipeline_id}/stages", response_model=PipelineStageResponse)
async def create_pipeline_stage(pipeline_id: int, stage_data: PipelineStageCreate,
                               user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Create a new stage in a pipeline."""
    # Verify pipeline exists
    pipeline_result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    if not pipeline_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Check for duplicate code/name in same pipeline
    existing = await db.execute(
        select(PipelineStage).where(
            PipelineStage.pipeline_id == pipeline_id,
            (PipelineStage.code == stage_data.code) | (PipelineStage.name == stage_data.name)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Stage code or name already exists in this pipeline")
    
    stage = PipelineStage(**stage_data.model_dump(exclude_unset=True), pipeline_id=pipeline_id)
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    
    # Log audit
    await log_audit(db, "pipeline_stage", stage.id, "created", user_id, 
                   new_values={**stage_data.model_dump(), "pipeline_id": pipeline_id})
    await db.commit()
    
    return stage


@router.put("/stages/{stage_id}", response_model=PipelineStageResponse)
async def update_pipeline_stage(stage_id: int, stage_data: PipelineStageUpdate,
                               user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing pipeline stage."""
    result = await db.execute(select(PipelineStage).where(PipelineStage.id == stage_id))
    stage = result.scalar_one_or_none()
    
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    # Store old values for audit
    old_values = {
        "code": stage.code,
        "name": stage.name,
        "probability": stage.probability,
        "sort_order": stage.sort_order
    }
    
    # Check for duplicate code/name if changing
    if stage_data.code and stage_data.code != stage.code:
        existing = await db.execute(
            select(PipelineStage).where(
                PipelineStage.pipeline_id == stage.pipeline_id,
                PipelineStage.code == stage_data.code,
                PipelineStage.id != stage_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Stage code already exists in this pipeline")
    
    if stage_data.name and stage_data.name != stage.name:
        existing = await db.execute(
            select(PipelineStage).where(
                PipelineStage.pipeline_id == stage.pipeline_id,
                PipelineStage.name == stage_data.name,
                PipelineStage.id != stage_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Stage name already exists in this pipeline")
    
    # Update fields
    update_data = stage_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stage, field, value)
    
    await db.commit()
    await db.refresh(stage)
    
    # Log audit
    await log_audit(db, "pipeline_stage", stage.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return stage


@router.delete("/stages/{stage_id}")
async def delete_pipeline_stage(stage_id: int, user_id: Optional[int] = None,
                               db: AsyncSession = Depends(get_crm_db)):
    """Delete a pipeline stage."""
    result = await db.execute(select(PipelineStage).where(PipelineStage.id == stage_id))
    stage = result.scalar_one_or_none()
    
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    # Check if stage has deals
    from app.models.crm.deal import Deal
    deals_count = await db.execute(select(Deal).where(Deal.stage_id == stage_id))
    if deals_count.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cannot delete stage with existing deals")
    
    old_values = {
        "code": stage.code,
        "name": stage.name,
        "pipeline_id": stage.pipeline_id
    }
    
    await db.execute(delete(PipelineStage).where(PipelineStage.id == stage_id))
    
    # Log audit
    await log_audit(db, "pipeline_stage", stage_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "stage_id": stage_id}


@router.put("/pipelines/{pipeline_id}/stages/reorder")
async def reorder_stages(pipeline_id: int, reorder_data: StageReorderRequest,
                        user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Reorder stages in a pipeline."""
    # Verify pipeline exists
    pipeline_result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    if not pipeline_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Update sort orders
    for stage_order in reorder_data.stage_orders:
        stage_id = stage_order.get("id")
        sort_order = stage_order.get("sort_order")
        
        if stage_id and sort_order is not None:
            await db.execute(
                update(PipelineStage)
                .where(PipelineStage.id == stage_id, PipelineStage.pipeline_id == pipeline_id)
                .values(sort_order=sort_order)
            )
    
    await db.commit()
    
    # Log audit
    await log_audit(db, "pipeline", pipeline_id, "stages_reordered", user_id, 
                   new_values={"stage_orders": reorder_data.stage_orders})
    await db.commit()
    
    return {"status": "reordered", "pipeline_id": pipeline_id}