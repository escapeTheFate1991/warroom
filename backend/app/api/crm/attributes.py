"""CRM Attributes API endpoints."""

import logging
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.attribute import Attribute, AttributeOption, AttributeValue
from app.models.crm.audit import AuditLog
from .schemas import AttributeResponse, AttributeCreate, AttributeValueSet

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


@router.get("/attributes", response_model=List[AttributeResponse])
async def list_attributes(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (deal, person, organization, product, quote)"),
    db: AsyncSession = Depends(get_crm_db),
):
    """List attributes for entity type."""
    query = select(Attribute)
    
    if entity_type:
        query = query.where(Attribute.entity_type == entity_type)
    
    query = query.order_by(Attribute.sort_order.nulls_last(), Attribute.name)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/attributes/{attribute_id}", response_model=AttributeResponse)
async def get_attribute(attribute_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single attribute."""
    result = await db.execute(
        select(Attribute).where(Attribute.id == attribute_id)
    )
    attribute = result.scalar_one_or_none()
    
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    
    return attribute


@router.post("/attributes", response_model=AttributeResponse)
async def create_attribute(attribute_data: AttributeCreate, user_id: Optional[int] = None,
                          db: AsyncSession = Depends(get_crm_db)):
    """Create custom attribute."""
    # Check for duplicate code within same entity type
    existing = await db.execute(
        select(Attribute).where(
            Attribute.code == attribute_data.code,
            Attribute.entity_type == attribute_data.entity_type
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Attribute code already exists for this entity type")
    
    attribute = Attribute(**attribute_data.model_dump(exclude_unset=True))
    db.add(attribute)
    await db.commit()
    await db.refresh(attribute)
    
    # Log audit
    await log_audit(db, "attribute", attribute.id, "created", user_id, 
                   new_values=attribute_data.model_dump())
    await db.commit()
    
    return attribute


@router.put("/attributes/{attribute_id}", response_model=AttributeResponse)
async def update_attribute(attribute_id: int, attribute_data: AttributeCreate,
                          user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update custom attribute."""
    result = await db.execute(select(Attribute).where(Attribute.id == attribute_id))
    attribute = result.scalar_one_or_none()
    
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    
    # Check for duplicate code if changing
    if attribute_data.code != attribute.code:
        existing = await db.execute(
            select(Attribute).where(
                Attribute.code == attribute_data.code,
                Attribute.entity_type == attribute_data.entity_type,
                Attribute.id != attribute_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Attribute code already exists for this entity type")
    
    # Store old values for audit
    old_values = {
        "code": attribute.code,
        "name": attribute.name,
        "type": attribute.type,
        "is_required": attribute.is_required
    }
    
    # Update fields
    update_data = attribute_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(attribute, field, value)
    
    await db.commit()
    await db.refresh(attribute)
    
    # Log audit
    await log_audit(db, "attribute", attribute.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return attribute


@router.delete("/attributes/{attribute_id}")
async def delete_attribute(attribute_id: int, user_id: Optional[int] = None,
                          db: AsyncSession = Depends(get_crm_db)):
    """Delete custom attribute."""
    result = await db.execute(select(Attribute).where(Attribute.id == attribute_id))
    attribute = result.scalar_one_or_none()
    
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    
    if not attribute.is_user_defined:
        raise HTTPException(status_code=400, detail="Cannot delete system attribute")
    
    old_values = {
        "code": attribute.code,
        "name": attribute.name,
        "entity_type": attribute.entity_type
    }
    
    # Delete all attribute values first (cascade should handle this, but being explicit)
    await db.execute(delete(AttributeValue).where(AttributeValue.attribute_id == attribute_id))
    await db.execute(delete(Attribute).where(Attribute.id == attribute_id))
    
    # Log audit
    await log_audit(db, "attribute", attribute_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "attribute_id": attribute_id}


@router.get("/entities/{entity_type}/{entity_id}/attributes")
async def get_entity_attributes(entity_type: str, entity_id: int, 
                               db: AsyncSession = Depends(get_crm_db)):
    """Get attribute values for an entity."""
    # Get all attributes for this entity type
    attributes_result = await db.execute(
        select(Attribute).where(Attribute.entity_type == entity_type)
    )
    attributes = attributes_result.scalars().all()
    
    # Get all values for this entity
    values_result = await db.execute(
        select(AttributeValue).where(
            AttributeValue.entity_type == entity_type,
            AttributeValue.entity_id == entity_id
        )
    )
    values = {v.attribute_id: v for v in values_result.scalars().all()}
    
    # Combine attributes with their values
    result = []
    for attr in attributes:
        value_obj = values.get(attr.id)
        value = None
        
        if value_obj:
            # Extract the appropriate value based on attribute type
            if attr.type == "text":
                value = value_obj.text_value
            elif attr.type == "boolean":
                value = value_obj.boolean_value
            elif attr.type == "number":
                value = value_obj.integer_value or value_obj.float_value
            elif attr.type == "date":
                value = value_obj.date_value.isoformat() if value_obj.date_value else None
            elif attr.type == "datetime":
                value = value_obj.datetime_value.isoformat() if value_obj.datetime_value else None
            elif attr.type in ("select", "multiselect"):
                value = value_obj.json_value
        
        result.append({
            "attribute_id": attr.id,
            "code": attr.code,
            "name": attr.name,
            "type": attr.type,
            "value": value,
            "is_required": attr.is_required
        })
    
    return {"attributes": result}


@router.put("/entities/{entity_type}/{entity_id}/attributes")
async def set_entity_attributes(entity_type: str, entity_id: int, 
                               values_data: AttributeValueSet,
                               user_id: Optional[int] = None,
                               db: AsyncSession = Depends(get_crm_db)):
    """Set attribute values for an entity."""
    # Validate entity_type
    valid_types = ["deal", "person", "organization", "product", "quote"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    # Get existing values
    existing_result = await db.execute(
        select(AttributeValue).where(
            AttributeValue.entity_type == entity_type,
            AttributeValue.entity_id == entity_id
        )
    )
    existing_values = {v.attribute_id: v for v in existing_result.scalars().all()}
    
    # Get attributes to validate types
    attr_ids = list(values_data.attribute_values.keys())
    attributes_result = await db.execute(
        select(Attribute).where(Attribute.id.in_(attr_ids))
    )
    attributes = {a.id: a for a in attributes_result.scalars().all()}
    
    old_values = {}
    new_values = {}
    
    for attribute_id, value in values_data.attribute_values.items():
        attribute = attributes.get(attribute_id)
        if not attribute:
            continue
            
        if attribute.entity_type != entity_type:
            continue
        
        # Get or create attribute value record
        attr_value = existing_values.get(attribute_id)
        if not attr_value:
            attr_value = AttributeValue(
                entity_type=entity_type,
                entity_id=entity_id,
                attribute_id=attribute_id
            )
            db.add(attr_value)
        else:
            # Store old value for audit
            old_values[attribute.code] = _extract_value_from_attribute_value(attr_value, attribute.type)
        
        # Clear all value fields first
        attr_value.text_value = None
        attr_value.boolean_value = None
        attr_value.integer_value = None
        attr_value.float_value = None
        attr_value.date_value = None
        attr_value.datetime_value = None
        attr_value.json_value = None
        
        # Set the appropriate field based on attribute type
        if value is not None:
            if attribute.type == "text" or attribute.type == "textarea":
                attr_value.text_value = str(value)
            elif attribute.type == "boolean":
                attr_value.boolean_value = bool(value)
            elif attribute.type == "number":
                if isinstance(value, int):
                    attr_value.integer_value = value
                else:
                    attr_value.float_value = float(value)
            elif attribute.type == "date":
                from datetime import datetime
                if isinstance(value, str):
                    attr_value.date_value = datetime.fromisoformat(value).date()
                else:
                    attr_value.date_value = value
            elif attribute.type == "datetime":
                from datetime import datetime
                if isinstance(value, str):
                    attr_value.datetime_value = datetime.fromisoformat(value)
                else:
                    attr_value.datetime_value = value
            elif attribute.type in ("select", "multiselect"):
                attr_value.json_value = value
        
        new_values[attribute.code] = value
    
    await db.commit()
    
    # Log audit if there were changes
    if old_values or new_values:
        await log_audit(db, f"{entity_type}_attributes", entity_id, "attributes_updated", 
                       user_id, old_values, new_values)
        await db.commit()
    
    return {"status": "updated", "entity_type": entity_type, "entity_id": entity_id}


def _extract_value_from_attribute_value(attr_value: AttributeValue, attr_type: str) -> Any:
    """Extract the appropriate value from an AttributeValue based on type."""
    if attr_type == "text" or attr_type == "textarea":
        return attr_value.text_value
    elif attr_type == "boolean":
        return attr_value.boolean_value
    elif attr_type == "number":
        return attr_value.integer_value or attr_value.float_value
    elif attr_type == "date":
        return attr_value.date_value.isoformat() if attr_value.date_value else None
    elif attr_type == "datetime":
        return attr_value.datetime_value.isoformat() if attr_value.datetime_value else None
    elif attr_type in ("select", "multiselect"):
        return attr_value.json_value
    return None


@router.get("/attribute-types")
async def get_attribute_types():
    """Get available attribute types."""
    return {
        "types": [
            {"value": "text", "label": "Text"},
            {"value": "textarea", "label": "Text Area"},
            {"value": "boolean", "label": "Yes/No"},
            {"value": "number", "label": "Number"},
            {"value": "date", "label": "Date"},
            {"value": "datetime", "label": "Date & Time"},
            {"value": "select", "label": "Select (dropdown)"},
            {"value": "multiselect", "label": "Multi-select"},
            {"value": "email", "label": "Email"},
            {"value": "phone", "label": "Phone"},
            {"value": "lookup", "label": "Lookup"}
        ]
    }


@router.get("/entity-types")
async def get_entity_types():
    """Get available entity types for attributes."""
    return {
        "types": [
            {"value": "deal", "label": "Deals"},
            {"value": "person", "label": "Persons"},
            {"value": "organization", "label": "Organizations"},
            {"value": "product", "label": "Products"},
            {"value": "quote", "label": "Quotes"}
        ]
    }