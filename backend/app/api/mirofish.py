"""MiroFish Simulation System API

Predictive content simulation using competitor data and persona modeling.
Phase 1: SimulationLite - uses existing competitor data for lightweight personas
Phase 2: Deep Psychographic - video analysis, OCEAN traits, behavioral modeling
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.services.mirofish_engine import MiroFishEngine

logger = logging.getLogger(__name__)

router = APIRouter()


class SimulationRequest(BaseModel):
    """Request for content simulation"""
    video_id: Optional[int] = None
    content_text: Optional[str] = None
    platform: str = "instagram"
    audience_context: Optional[str] = None


class SimulationResult(BaseModel):
    """Simulation results"""
    viral_score: int = Field(..., ge=0, le=100, description="Viral potential score 0-100")
    engagement_rate: float = Field(..., description="Predicted engagement rate")
    sentiment: Dict[str, float] = Field(..., description="Sentiment breakdown")
    recommendations: List[Dict[str, str]] = Field(..., description="Specific recommendations with reasoning")
    personas_used: int = Field(..., description="Number of personas in simulation")
    confidence: float = Field(..., description="Prediction confidence 0-1")


class AnalysisResult(BaseModel):
    """Post-publish analysis results"""
    actual_engagement: float
    predicted_engagement: float
    accuracy_score: float
    calibration_insights: List[str]
    persona_accuracy: List[Dict[str, Any]]


class SimulationHistory(BaseModel):
    """Historical simulation record"""
    id: int
    content_preview: str
    platform: str
    viral_score: int
    engagement_rate: float
    created_at: datetime
    actual_performance: Optional[Dict[str, Any]] = None


@router.post("/api/mirofish/simulate", response_model=SimulationResult)
async def simulate_content(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_tenant_db),
    org_id: int = Depends(get_org_id),
    user_id: int = Depends(get_user_id)
):
    """
    Run content through MiroFish simulation system.
    
    Uses existing competitor data to generate audience personas,
    then simulates their engagement with the provided content.
    """
    try:
        engine = MiroFishEngine()
        
        # Generate personas from competitor data
        personas = await engine.generate_personas(org_id, db)
        
        if not personas:
            raise HTTPException(
                status_code=400,
                detail="No competitor data available for simulation. Please add competitors in Intelligence tab."
            )
        
        # Prepare content data
        content_data = {
            "text": request.content_text,
            "platform": request.platform,
            "audience_context": request.audience_context,
            "video_id": request.video_id
        }
        
        # Run simulation
        result = await engine.simulate_content(content_data, personas)
        
        # Store simulation in history (background task)
        background_tasks.add_task(
            _store_simulation_history,
            org_id, user_id, request, result, personas
        )
        
        return SimulationResult(
            viral_score=result["viral_score"],
            engagement_rate=result["engagement_rate"],
            sentiment=result["sentiment"],
            recommendations=result["recommendations"],
            personas_used=len(personas),
            confidence=result["confidence"]
        )
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/api/mirofish/analyze", response_model=AnalysisResult)
async def analyze_post_performance(
    post_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    org_id: int = Depends(get_org_id),
    user_id: int = Depends(get_user_id)
):
    """
    Compare actual post performance against MiroFish prediction.
    
    Provides calibration insights and persona accuracy breakdown.
    """
    try:
        engine = MiroFishEngine()
        
        # Get stored prediction for this post
        prediction = await engine.get_stored_prediction(post_id, db)
        
        if not prediction:
            raise HTTPException(
                status_code=404,
                detail="No prediction found for this post"
            )
        
        # Compare with actual performance
        result = await engine.compare_actual_vs_predicted(post_id, prediction, db)
        
        return AnalysisResult(**result)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/api/mirofish/history", response_model=List[SimulationHistory])
async def get_simulation_history(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_db),
    org_id: int = Depends(get_org_id)
):
    """Get historical simulations for this organization"""
    try:
        engine = MiroFishEngine()
        history = await engine.get_simulation_history(org_id, db, limit, offset)
        
        return [SimulationHistory(**item) for item in history]
        
    except Exception as e:
        logger.error(f"Failed to get simulation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.post("/api/mirofish/file-simulate")
async def simulate_uploaded_file(
    file: UploadFile = File(...),
    platform: str = "instagram",
    audience_context: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_tenant_db),
    org_id: int = Depends(get_org_id),
    user_id: int = Depends(get_user_id)
):
    """
    Simulate content from uploaded video file (Content Sandbox mode).
    
    Extracts basic metadata and runs through simulation engine.
    Future versions will include video content analysis.
    """
    try:
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(
                status_code=400,
                detail="Only video files are supported"
            )
        
        # For Phase 1, we'll use filename and basic metadata
        content_data = {
            "filename": file.filename,
            "content_type": file.content_type,
            "platform": platform,
            "audience_context": audience_context,
            "upload_mode": "sandbox"
        }
        
        engine = MiroFishEngine()
        personas = await engine.generate_personas(org_id, db)
        
        if not personas:
            raise HTTPException(
                status_code=400,
                detail="No competitor data available for simulation"
            )
        
        result = await engine.simulate_content(content_data, personas)
        
        return SimulationResult(
            viral_score=result["viral_score"],
            engagement_rate=result["engagement_rate"],
            sentiment=result["sentiment"],
            recommendations=result["recommendations"],
            personas_used=len(personas),
            confidence=result["confidence"]
        )
        
    except Exception as e:
        logger.error(f"File simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"File simulation failed: {str(e)}")


async def _store_simulation_history(
    org_id: int,
    user_id: int,
    request: SimulationRequest,
    result: Dict[str, Any],
    personas: List[Dict[str, Any]]
):
    """Background task to store simulation in history"""
    try:
        from app.db.crm_db import crm_session
        from app.services.mirofish_engine import MiroFishEngine
        
        content_data = {
            "text": request.content_text,
            "platform": request.platform,
            "audience_context": request.audience_context,
            "video_id": request.video_id
        }
        
        async with crm_session() as db:
            engine = MiroFishEngine()
            simulation_id = await engine.store_simulation_result(
                org_id, content_data, result, personas, db
            )
            logger.info(f"Simulation {simulation_id} stored for org {org_id}, user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to store simulation history: {e}")