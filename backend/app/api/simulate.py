"""Mirofish Swarm Persona System + Social Friction Test Backend

Swarm intelligence engine that simulates how target audiences will react to content
BEFORE spending money generating or posting it.
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from collections import Counter, defaultdict

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id
from app.api.auth import get_current_user
from app.models.crm.user import User
from app.models.settings import Setting
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Helper: get Gemini key ─────────────────────────────────────────────

async def _get_gemini_key(db: AsyncSession) -> str:
    """Get Google AI Studio API key from settings or environment."""
    result = await db.execute(select(Setting.value).where(Setting.key == "google_ai_studio_api_key"))
    row = result.scalar_one_or_none()
    import os
    key = row or os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Google AI Studio API key not configured")
    return key


def _parse_jsonb_field(value: Union[str, dict, list]) -> Union[dict, list]:
    """Parse JSONB field that might come as string or already parsed."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {} if value == '{}' else []
    return value or {}


# ═══════════════════════════════════════════════════════════════════════
#  PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════

class PersonaCreate(BaseModel):
    name: str
    archetype: str
    demographics: Dict[str, Any] = Field(default_factory=dict)
    psychographics: Dict[str, Any] = Field(default_factory=dict)
    behavioral_logic: Dict[str, Any] = Field(default_factory=dict)
    collective_memory: List[str] = Field(default_factory=list)
    source_competitors: List[str] = Field(default_factory=list)


class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    archetype: Optional[str] = None
    demographics: Optional[Dict[str, Any]] = None
    psychographics: Optional[Dict[str, Any]] = None
    behavioral_logic: Optional[Dict[str, Any]] = None
    collective_memory: Optional[List[str]] = None
    source_competitors: Optional[List[str]] = None


class PersonaResponse(BaseModel):
    id: int
    org_id: int
    name: str
    archetype: str
    demographics: Dict[str, Any]
    psychographics: Dict[str, Any]
    behavioral_logic: Dict[str, Any]
    collective_memory: List[str]
    source_competitors: List[str]
    is_system: bool
    created_at: str
    updated_at: str


class ScriptInput(BaseModel):
    hook: str
    body: str
    cta: str


class SocialFrictionTestRequest(BaseModel):
    script: ScriptInput
    format_slug: str
    persona_ids: List[int]
    scene_count: int = 4
    audio_style: str = "trending_fast_paced"


class PersonaChatRequest(BaseModel):
    persona_id: int
    script: ScriptInput
    format_slug: str
    user_message: str


class SimulationResponse(BaseModel):
    id: int
    engagement_score: int
    predicted_metrics: Dict[str, Any]
    drop_off_timeline: List[Dict[str, Any]]
    predicted_comments: List[Dict[str, Any]]
    optimization_recommendation: Dict[str, Any]
    scene_friction_map: List[Dict[str, Any]]
    audio_recommendation: Dict[str, Any]
    created_at: str


class PersonaChatResponse(BaseModel):
    persona_name: str
    response: str
    behavioral_trigger: str
    suggested_fix: str


# ═══════════════════════════════════════════════════════════════════════
#  PERSONA CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/personas", response_model=List[PersonaResponse])
async def list_personas(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all personas for the organization (system + custom)."""
    org_id = get_org_id(request)
    
    result = await db.execute(text("""
        SELECT id, org_id, name, archetype, demographics, psychographics, 
               behavioral_logic, collective_memory, source_competitors, 
               is_system, created_at, updated_at
        FROM crm.swarm_personas 
        WHERE org_id = :org_id OR is_system = true
        ORDER BY is_system DESC, name ASC
    """), {"org_id": org_id})
    
    rows = result.fetchall()
    personas = []
    
    for row in rows:
        personas.append(PersonaResponse(
            id=row.id,
            org_id=row.org_id,
            name=row.name,
            archetype=row.archetype,
            demographics=_parse_jsonb_field(row.demographics),
            psychographics=_parse_jsonb_field(row.psychographics),
            behavioral_logic=_parse_jsonb_field(row.behavioral_logic),
            collective_memory=_parse_jsonb_field(row.collective_memory) if row.collective_memory else [],
            source_competitors=row.source_competitors if row.source_competitors else [],
            is_system=row.is_system,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat()
        ))
    
    return personas


@router.get("/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a single persona by ID."""
    org_id = get_org_id(request)
    
    result = await db.execute(text("""
        SELECT id, org_id, name, archetype, demographics, psychographics,
               behavioral_logic, collective_memory, source_competitors,
               is_system, created_at, updated_at
        FROM crm.swarm_personas 
        WHERE id = :id AND (org_id = :org_id OR is_system = true)
    """), {"id": persona_id, "org_id": org_id})
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    return PersonaResponse(
        id=row.id,
        org_id=row.org_id,
        name=row.name,
        archetype=row.archetype,
        demographics=_parse_jsonb_field(row.demographics),
        psychographics=_parse_jsonb_field(row.psychographics),
        behavioral_logic=_parse_jsonb_field(row.behavioral_logic),
        collective_memory=_parse_jsonb_field(row.collective_memory) if row.collective_memory else [],
        source_competitors=row.source_competitors if row.source_competitors else [],
        is_system=row.is_system,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat()
    )


@router.post("/personas", response_model=Dict[str, Any])
async def create_persona(
    request: Request,
    body: PersonaCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a custom persona for the organization."""
    org_id = get_org_id(request)
    
    # Convert lists to PostgreSQL arrays
    source_competitors_pg = f"{{{','.join(body.source_competitors)}}}" if body.source_competitors else "{}"
    
    result = await db.execute(text("""
        INSERT INTO crm.swarm_personas 
        (org_id, name, archetype, demographics, psychographics, behavioral_logic, 
         collective_memory, source_competitors, is_system, updated_at)
        VALUES (:org_id, :name, :archetype, :demographics, :psychographics, :behavioral_logic,
                :collective_memory, :source_competitors, false, NOW())
        RETURNING id
    """), {
        "org_id": org_id,
        "name": body.name,
        "archetype": body.archetype,
        "demographics": json.dumps(body.demographics),
        "psychographics": json.dumps(body.psychographics),
        "behavioral_logic": json.dumps(body.behavioral_logic),
        "collective_memory": json.dumps(body.collective_memory),
        "source_competitors": source_competitors_pg
    })
    
    persona_id = result.scalar()
    await db.commit()
    
    return {"id": persona_id, "message": "Persona created successfully"}


@router.put("/personas/{persona_id}", response_model=Dict[str, Any])
async def update_persona(
    persona_id: int,
    request: Request,
    body: PersonaUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update a persona (only non-system personas)."""
    org_id = get_org_id(request)
    
    # Check if persona exists and is editable
    check_result = await db.execute(text("""
        SELECT id, is_system FROM crm.swarm_personas 
        WHERE id = :id AND org_id = :org_id
    """), {"id": persona_id, "org_id": org_id})
    
    row = check_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Persona not found")
    if row.is_system:
        raise HTTPException(status_code=403, detail="Cannot edit system personas")
    
    # Build update query dynamically
    update_fields = []
    params = {"id": persona_id}
    
    if body.name is not None:
        update_fields.append("name = :name")
        params["name"] = body.name
    if body.archetype is not None:
        update_fields.append("archetype = :archetype")
        params["archetype"] = body.archetype
    if body.demographics is not None:
        update_fields.append("demographics = :demographics")
        params["demographics"] = json.dumps(body.demographics)
    if body.psychographics is not None:
        update_fields.append("psychographics = :psychographics")
        params["psychographics"] = json.dumps(body.psychographics)
    if body.behavioral_logic is not None:
        update_fields.append("behavioral_logic = :behavioral_logic")
        params["behavioral_logic"] = json.dumps(body.behavioral_logic)
    if body.collective_memory is not None:
        update_fields.append("collective_memory = :collective_memory")
        params["collective_memory"] = json.dumps(body.collective_memory)
    if body.source_competitors is not None:
        update_fields.append("source_competitors = :source_competitors")
        params["source_competitors"] = f"{{{','.join(body.source_competitors)}}}" if body.source_competitors else "{}"
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields.append("updated_at = NOW()")
    
    await db.execute(text(f"""
        UPDATE crm.swarm_personas 
        SET {', '.join(update_fields)}
        WHERE id = :id
    """), params)
    
    await db.commit()
    
    return {"message": "Persona updated successfully"}


@router.delete("/personas/{persona_id}")
async def delete_persona(
    persona_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Delete a persona (only non-system personas)."""
    org_id = get_org_id(request)
    
    # Check if persona exists and is deletable
    check_result = await db.execute(text("""
        SELECT id, is_system FROM crm.swarm_personas 
        WHERE id = :id AND org_id = :org_id
    """), {"id": persona_id, "org_id": org_id})
    
    row = check_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Persona not found")
    if row.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system personas")
    
    await db.execute(text("""
        DELETE FROM crm.swarm_personas WHERE id = :id
    """), {"id": persona_id})
    
    await db.commit()
    
    return {"message": "Persona deleted successfully"}


# ═══════════════════════════════════════════════════════════════════════
#  PERSONA GENERATION
# ═══════════════════════════════════════════════════════════════════════

@router.post("/generate-personas")
async def generate_personas_from_competitors(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Auto-generate audience personas from competitor comments data."""
    org_id = get_org_id(request)
    
    try:
        # Pull all comments_data from competitor_posts
        comments_result = await db.execute(text("""
            SELECT comments_data, platform, handle 
            FROM crm.competitor_posts 
            WHERE org_id = :org_id AND comments_data IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 500
        """), {"org_id": org_id})
        
        comments_rows = comments_result.fetchall()
        
        if not comments_rows:
            raise HTTPException(status_code=404, detail="No competitor comments data found")
        
        # Analyze comments to extract themes
        all_comments = []
        for row in comments_rows:
            comments = _parse_jsonb_field(row.comments_data)
            if isinstance(comments, list):
                all_comments.extend(comments)
        
        if not all_comments:
            raise HTTPException(status_code=400, detail="No comments data to analyze")
        
        # Sample comments for analysis (avoid token overload)
        import random
        sample_size = min(100, len(all_comments))
        sampled_comments = random.sample(all_comments, sample_size)
        
        # Build analysis prompt
        api_key = await _get_gemini_key(db)
        
        prompt = f"""You are a persona generation engine. Analyze these social media comments to extract 3-5 distinct audience archetypes.

COMMENTS SAMPLE ({len(sampled_comments)} comments):
{json.dumps(sampled_comments[:50], indent=2)}

Generate personas that would write these types of comments. Look for:
1. Recurring vocabulary patterns
2. Sentiment and tone clusters
3. Technical vs. casual language
4. Pain points and desires mentioned
5. Demographic hints (roles, experience levels)

You MUST respond in this exact JSON format:
{{
  "personas": [
    {{
      "name": "<descriptive persona name>",
      "archetype": "<slug_format>",
      "demographics": {{
        "age_range": "<age range>",
        "primary_roles": ["<role1>", "<role2>"],
        "tech_experience": "<beginner|intermediate|advanced>"
      }},
      "psychographics": {{
        "core_desires": ["<desire1>", "<desire2>", "<desire3>"],
        "friction_points": ["<friction1>", "<friction2>", "<friction3>"],
        "content_bias": {{
          "format_preference": "<format type>",
          "hook_sensitivity": <0.0-1.0>,
          "visual_style": "<style preference>"
        }}
      }},
      "behavioral_logic": {{
        "interaction_triggers": {{
          "comment_on": ["<trigger1>", "<trigger2>"],
          "share_on": ["<trigger1>", "<trigger2>"],
          "bookmark_on": ["<trigger1>", "<trigger2>"]
        }},
        "comment_style": {{
          "tone": "<tone description>",
          "vocabulary_keywords": ["<word1>", "<word2>", "<word3>"]
        }}
      }}
    }}
  ]
}}"""
        
        # Call Gemini API
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048,
                        "responseMimeType": "application/json"
                    },
                },
            )
            
            if resp.status_code != 200:
                logger.error(f"Gemini API error: {resp.status_code} - {resp.text}")
                raise HTTPException(status_code=503, detail="Gemini API error")
            
            response_data = resp.json()
            content_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse the JSON response
            try:
                analysis = json.loads(content_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response: {e}")
                raise HTTPException(status_code=503, detail="Invalid response from AI")
        
        # Insert generated personas into database
        created_personas = []
        
        for persona_data in analysis.get("personas", []):
            source_competitors_pg = f"{{{','.join([row.handle for row in comments_rows[:10]])}}}"
            
            result = await db.execute(text("""
                INSERT INTO crm.swarm_personas 
                (org_id, name, archetype, demographics, psychographics, behavioral_logic, 
                 collective_memory, source_competitors, is_system, updated_at)
                VALUES (:org_id, :name, :archetype, :demographics, :psychographics, :behavioral_logic,
                        :collective_memory, :source_competitors, false, NOW())
                RETURNING id
            """), {
                "org_id": org_id,
                "name": persona_data["name"],
                "archetype": persona_data["archetype"],
                "demographics": json.dumps(persona_data["demographics"]),
                "psychographics": json.dumps(persona_data["psychographics"]),
                "behavioral_logic": json.dumps(persona_data["behavioral_logic"]),
                "collective_memory": json.dumps([]),
                "source_competitors": source_competitors_pg
            })
            
            persona_id = result.scalar()
            created_personas.append({
                "id": persona_id,
                "name": persona_data["name"],
                "archetype": persona_data["archetype"]
            })
        
        await db.commit()
        
        return {
            "generated_personas": created_personas,
            "analyzed_comments": len(all_comments),
            "message": f"Generated {len(created_personas)} personas from competitor data"
        }
        
    except Exception as e:
        logger.error(f"Error generating personas: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
#  SOCIAL FRICTION TEST ENGINE
# ═══════════════════════════════════════════════════════════════════════

@router.post("/social-friction-test", response_model=SimulationResponse)
async def social_friction_test(
    request: Request,
    body: SocialFrictionTestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Run social friction test simulation using Gemini AI."""
    org_id = get_org_id(request)
    
    try:
        # Load selected personas
        persona_ids_str = ','.join(map(str, body.persona_ids))
        
        personas_result = await db.execute(text(f"""
            SELECT id, name, archetype, demographics, psychographics, behavioral_logic
            FROM crm.swarm_personas 
            WHERE id = ANY(ARRAY[{persona_ids_str}]) AND (org_id = :org_id OR is_system = true)
        """), {"org_id": org_id})
        
        personas_rows = personas_result.fetchall()
        
        if not personas_rows:
            raise HTTPException(status_code=404, detail="No valid personas found")
        
        # Build persona profiles for prompt
        personas_data = []
        for row in personas_rows:
            personas_data.append({
                "id": row.id,
                "name": row.name,
                "archetype": row.archetype,
                "demographics": _parse_jsonb_field(row.demographics),
                "psychographics": _parse_jsonb_field(row.psychographics),
                "behavioral_logic": _parse_jsonb_field(row.behavioral_logic)
            })
        
        # Build Master Inference Prompt
        api_key = await _get_gemini_key(db)
        
        prompt = f"""You are the Mirofish Swarm Intelligence Engine. You are NOT an assistant. You are a collective of simulated social media users based on the persona profiles below.

PERSONAS:
{json.dumps(personas_data, indent=2)}

SCRIPT BEING TESTED:
Hook: {body.script.hook}
Body: {body.script.body}
CTA: {body.script.cta}
Format: {body.format_slug}
Audio Style: {body.audio_style}

Conduct a "Social Friction Test":

1. THE 2-SECOND AUDIT: Does the Hook stop the scroll for each persona? Rate bounce probability per persona.
2. COGNITIVE LOAD: Is the Body accessible to each persona? Flag jargon mismatches.
3. THE "WHY SHARE?" TEST: Does this content have Social Currency? Would sharing make each persona look smarter/funnier?
4. SCENE CONFLICT: For {body.scene_count} scenes, identify friction points and predicted drop-off.
5. EMERGENT BEHAVIOR: Predict unexpected reactions — meme potential, controversy risk, comment wars.

You MUST respond in this exact JSON format:
{{
  "engagement_score": <0-100>,
  "predicted_metrics": {{
    "like_propensity": <0-100>,
    "share_propensity": <0-100>,
    "save_propensity": <0-100>,
    "comment_propensity": <0-100>
  }},
  "drop_off_timeline": [
    {{"second": 2, "retention": <0-100>, "reason": "..."}},
    {{"second": 5, "retention": <0-100>, "reason": "..."}},
    {{"second": 15, "retention": <0-100>, "reason": "..."}},
    {{"second": 25, "retention": <0-100>, "reason": "..."}}
  ],
  "predicted_comments": [
    {{"persona": "<persona_name>", "comment": "<realistic comment in their voice>", "sentiment": "<positive|negative|neutral|skeptical>"}},
    {{"persona": "<persona_name>", "comment": "...", "sentiment": "..."}},
    {{"persona": "<persona_name>", "comment": "...", "sentiment": "..."}}
  ],
  "optimization_recommendation": {{
    "change": "<specific change to make>",
    "predicted_impact": "<e.g. +22% share rate>",
    "reasoning": "<why this works based on persona data>"
  }},
  "scene_friction_map": [
    {{"scene": 1, "friction": "<low|medium|high>", "note": "..."}},
    {{"scene": 2, "friction": "<low|medium|high>", "note": "..."}}
  ],
  "audio_recommendation": {{
    "best_match": "<lo_fi|cinematic|trending_fast_paced>",
    "reason": "<why based on persona preferences>"
  }}
}}"""
        
        # Call Gemini API
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 2048,
                        "responseMimeType": "application/json"
                    },
                },
            )
            
            if resp.status_code != 200:
                logger.error(f"Gemini API error: {resp.status_code} - {resp.text}")
                raise HTTPException(status_code=503, detail="Gemini API error")
            
            response_data = resp.json()
            content_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse the JSON response
            try:
                simulation_result = json.loads(content_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response: {e}")
                raise HTTPException(status_code=503, detail="Invalid response from AI")
        
        # Store simulation result in database
        result = await db.execute(text("""
            INSERT INTO crm.simulation_results 
            (org_id, script_hook, script_body, script_cta, format_slug, persona_ids,
             engagement_score, predicted_metrics, drop_off_timeline, predicted_comments,
             optimization_recommendation, scene_friction_map, audio_recommendation)
            VALUES (:org_id, :script_hook, :script_body, :script_cta, :format_slug, :persona_ids,
                    :engagement_score, :predicted_metrics, :drop_off_timeline, :predicted_comments,
                    :optimization_recommendation, :scene_friction_map, :audio_recommendation)
            RETURNING id, created_at
        """), {
            "org_id": org_id,
            "script_hook": body.script.hook,
            "script_body": body.script.body,
            "script_cta": body.script.cta,
            "format_slug": body.format_slug,
            "persona_ids": body.persona_ids,
            "engagement_score": simulation_result.get("engagement_score", 0),
            "predicted_metrics": json.dumps(simulation_result.get("predicted_metrics", {})),
            "drop_off_timeline": json.dumps(simulation_result.get("drop_off_timeline", [])),
            "predicted_comments": json.dumps(simulation_result.get("predicted_comments", [])),
            "optimization_recommendation": json.dumps(simulation_result.get("optimization_recommendation", {})),
            "scene_friction_map": json.dumps(simulation_result.get("scene_friction_map", [])),
            "audio_recommendation": json.dumps(simulation_result.get("audio_recommendation", {}))
        })
        
        simulation_row = result.fetchone()
        await db.commit()
        
        return SimulationResponse(
            id=simulation_row.id,
            engagement_score=simulation_result.get("engagement_score", 0),
            predicted_metrics=simulation_result.get("predicted_metrics", {}),
            drop_off_timeline=simulation_result.get("drop_off_timeline", []),
            predicted_comments=simulation_result.get("predicted_comments", []),
            optimization_recommendation=simulation_result.get("optimization_recommendation", {}),
            scene_friction_map=simulation_result.get("scene_friction_map", []),
            audio_recommendation=simulation_result.get("audio_recommendation", {}),
            created_at=simulation_row.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error running social friction test: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
#  PERSONA CHAT
# ═══════════════════════════════════════════════════════════════════════

@router.post("/persona-chat", response_model=PersonaChatResponse)
async def persona_chat(
    request: Request,
    body: PersonaChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Chat with a simulated persona about their reaction to content."""
    org_id = get_org_id(request)
    
    try:
        # Load the persona
        persona_result = await db.execute(text("""
            SELECT id, name, archetype, demographics, psychographics, behavioral_logic
            FROM crm.swarm_personas 
            WHERE id = :id AND (org_id = :org_id OR is_system = true)
        """), {"id": body.persona_id, "org_id": org_id})
        
        persona_row = persona_result.fetchone()
        if not persona_row:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        persona_data = {
            "name": persona_row.name,
            "archetype": persona_row.archetype,
            "demographics": _parse_jsonb_field(persona_row.demographics),
            "psychographics": _parse_jsonb_field(persona_row.psychographics),
            "behavioral_logic": _parse_jsonb_field(persona_row.behavioral_logic)
        }
        
        # Build chat prompt
        api_key = await _get_gemini_key(db)
        
        prompt = f"""You ARE {persona_data['name']} - a {persona_data['archetype']} persona who just watched this content:

CONTENT YOU WATCHED:
Hook: {body.script.hook}
Body: {body.script.body}
CTA: {body.script.cta}
Format: {body.format_slug}

YOUR PERSONA PROFILE:
{json.dumps(persona_data, indent=2)}

The user is asking you: "{body.user_message}"

Respond AS THIS PERSONA, using their:
- Vocabulary and communication style
- Emotional triggers and friction points
- Natural reaction to this type of content
- Honest opinion about what worked/didn't work

Also identify what specific behavioral trigger caused your reaction, and suggest one fix for the content.

You MUST respond in this exact JSON format:
{{
  "response": "<your response as the persona>",
  "behavioral_trigger": "<which friction_point or trigger was activated>",
  "suggested_fix": "<one specific improvement to make>"
}}"""
        
        # Call Gemini API
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.9,
                        "maxOutputTokens": 1024,
                        "responseMimeType": "application/json"
                    },
                },
            )
            
            if resp.status_code != 200:
                logger.error(f"Gemini API error: {resp.status_code} - {resp.text}")
                raise HTTPException(status_code=503, detail="Gemini API error")
            
            response_data = resp.json()
            content_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse the JSON response
            try:
                chat_result = json.loads(content_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response: {e}")
                raise HTTPException(status_code=503, detail="Invalid response from AI")
        
        return PersonaChatResponse(
            persona_name=persona_data['name'],
            response=chat_result.get("response", "I'm not sure how to respond to that."),
            behavioral_trigger=chat_result.get("behavioral_trigger", "unknown"),
            suggested_fix=chat_result.get("suggested_fix", "No specific suggestion")
        )
        
    except Exception as e:
        logger.error(f"Error in persona chat: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
#  SIMULATION HISTORY
# ═══════════════════════════════════════════════════════════════════════

@router.get("/history", response_model=List[Dict[str, Any]])
async def get_simulation_history(
    request: Request,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List past simulations for the organization."""
    org_id = get_org_id(request)
    
    result = await db.execute(text("""
        SELECT id, script_hook, script_body, script_cta, format_slug, 
               engagement_score, created_at
        FROM crm.simulation_results 
        WHERE org_id = :org_id
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"org_id": org_id, "limit": limit})
    
    rows = result.fetchall()
    
    return [
        {
            "id": row.id,
            "script_hook": row.script_hook,
            "script_body": row.script_body,
            "script_cta": row.script_cta,
            "format_slug": row.format_slug,
            "engagement_score": row.engagement_score,
            "created_at": row.created_at.isoformat()
        }
        for row in rows
    ]


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation_result(
    simulation_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a specific simulation result."""
    org_id = get_org_id(request)
    
    result = await db.execute(text("""
        SELECT id, engagement_score, predicted_metrics, drop_off_timeline,
               predicted_comments, optimization_recommendation, scene_friction_map,
               audio_recommendation, created_at
        FROM crm.simulation_results 
        WHERE id = :id AND org_id = :org_id
    """), {"id": simulation_id, "org_id": org_id})
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return SimulationResponse(
        id=row.id,
        engagement_score=row.engagement_score,
        predicted_metrics=_parse_jsonb_field(row.predicted_metrics),
        drop_off_timeline=_parse_jsonb_field(row.drop_off_timeline),
        predicted_comments=_parse_jsonb_field(row.predicted_comments),
        optimization_recommendation=_parse_jsonb_field(row.optimization_recommendation),
        scene_friction_map=_parse_jsonb_field(row.scene_friction_map),
        audio_recommendation=_parse_jsonb_field(row.audio_recommendation),
        created_at=row.created_at.isoformat()
    )