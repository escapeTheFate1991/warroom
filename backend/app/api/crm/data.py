"""CRM Data Management API endpoints."""

import logging
import csv
import io
import base64
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.audit import AuditLog, Import
from app.models.crm.deal import Deal
from app.models.crm.contact import Person, Organization
from app.models.crm.product import Product
from .schemas import ImportRequest, ImportResponse, DeduplicateRequest

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


async def process_import(import_id: int, entity_type: str, csv_data: str, 
                        mapping: Dict[str, str], user_id: Optional[int] = None):
    """Background task to process CSV import."""
    from app.db.crm_db import crm_session
    
    async with crm_session() as db:
        try:
            # Get the import record
            import_result = await db.execute(select(Import).where(Import.id == import_id))
            import_record = import_result.scalar_one()
            
            # Parse CSV data
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            total_rows = 0
            processed_rows = 0
            errors = []
            
            # Count total rows first
            rows = list(reader)
            total_rows = len(rows)
            import_record.total_rows = total_rows
            await db.commit()
            
            for row_num, row in enumerate(rows, 1):
                try:
                    # Map CSV columns to model fields
                    mapped_data = {}
                    for csv_column, model_field in mapping.items():
                        if csv_column in row and row[csv_column]:
                            value = row[csv_column].strip()
                            if value:  # Only include non-empty values
                                mapped_data[model_field] = value
                    
                    if not mapped_data:
                        continue  # Skip empty rows
                    
                    # Create entity based on type
                    if entity_type == "deals":
                        entity = Deal(**mapped_data)
                    elif entity_type == "persons":
                        # Handle emails as JSON array
                        if "emails" in mapped_data:
                            email_value = mapped_data["emails"]
                            if isinstance(email_value, str):
                                mapped_data["emails"] = [{"value": email_value, "label": "work"}]
                        entity = Person(**mapped_data)
                    elif entity_type == "organizations":
                        entity = Organization(**mapped_data)
                    elif entity_type == "products":
                        entity = Product(**mapped_data)
                    else:
                        raise ValueError(f"Unsupported entity type: {entity_type}")
                    
                    db.add(entity)
                    processed_rows += 1
                    
                    # Commit in batches
                    if processed_rows % 50 == 0:
                        await db.commit()
                        import_record.processed_rows = processed_rows
                        await db.commit()
                
                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    errors.append(error_msg)
                    logger.error("Import error: %s", error_msg)
            
            # Final commit
            await db.commit()
            
            # Update import record
            import_record.processed_rows = processed_rows
            import_record.errors = errors
            import_record.status = "completed" if not errors else "completed_with_errors"
            
            await db.commit()
            
            # Log audit
            await log_audit(db, "import", import_id, "completed", user_id, 
                           new_values={
                               "entity_type": entity_type,
                               "total_rows": total_rows,
                               "processed_rows": processed_rows,
                               "errors_count": len(errors)
                           })
            await db.commit()
            
            logger.info("Import %d completed: %d/%d rows processed, %d errors", 
                       import_id, processed_rows, total_rows, len(errors))
            
        except Exception as e:
            logger.error("Import %d failed: %s", import_id, e, exc_info=True)
            import_record.status = "failed"
            import_record.errors = [str(e)]
            await db.commit()


@router.post("/import", response_model=ImportResponse)
async def import_csv(import_data: ImportRequest, background_tasks: BackgroundTasks,
                    user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Import CSV data for deals, contacts, or products."""
    # Validate entity type
    valid_types = ["deals", "persons", "organizations", "products"]
    if import_data.entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    # Decode base64 CSV data
    try:
        csv_data = base64.b64decode(import_data.file_data).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV data: {str(e)}")
    
    # Validate CSV format
    try:
        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames or []
        
        # Check if all mapped columns exist in CSV
        missing_columns = [col for col in import_data.mapping.keys() if col not in headers]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"CSV missing columns: {missing_columns}")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
    
    # Create import record
    import_record = Import(
        entity_type=import_data.entity_type,
        status="pending"
    )
    db.add(import_record)
    await db.commit()
    await db.refresh(import_record)
    
    # Start background import process
    background_tasks.add_task(process_import, import_record.id, import_data.entity_type, 
                             csv_data, import_data.mapping, user_id)
    
    return import_record


@router.get("/import/{import_id}", response_model=ImportResponse)
async def get_import_status(import_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get import status."""
    result = await db.execute(select(Import).where(Import.id == import_id))
    import_record = result.scalar_one_or_none()
    
    if not import_record:
        raise HTTPException(status_code=404, detail="Import not found")
    
    return import_record


@router.get("/imports", response_model=List[ImportResponse])
async def list_imports(
    entity_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db)
):
    """List import history."""
    query = select(Import)
    
    if entity_type:
        query = query.where(Import.entity_type == entity_type)
    if status:
        query = query.where(Import.status == status)
    
    query = query.order_by(Import.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/export/{entity_type}")
async def export_csv(entity_type: str, db: AsyncSession = Depends(get_crm_db)):
    """Export entity data to CSV."""
    from fastapi.responses import StreamingResponse
    
    valid_types = ["deals", "persons", "organizations", "products"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    # Generate CSV based on entity type
    output = io.StringIO()
    writer = csv.writer(output)
    
    if entity_type == "deals":
        # Export deals
        query = select(Deal).order_by(Deal.created_at.desc())
        result = await db.execute(query)
        deals = result.scalars().all()
        
        # Write headers
        writer.writerow([
            "ID", "Title", "Description", "Deal Value", "Status", "Expected Close Date",
            "User ID", "Person ID", "Organization ID", "Pipeline ID", "Stage ID",
            "Created At", "Updated At"
        ])
        
        # Write data
        for deal in deals:
            writer.writerow([
                deal.id, deal.title, deal.description, deal.deal_value,
                "Won" if deal.status is True else "Lost" if deal.status is False else "Open",
                deal.expected_close_date, deal.user_id, deal.person_id,
                deal.organization_id, deal.pipeline_id, deal.stage_id,
                deal.created_at, deal.updated_at
            ])
    
    elif entity_type == "persons":
        # Export persons
        query = select(Person).order_by(Person.name)
        result = await db.execute(query)
        persons = result.scalars().all()
        
        writer.writerow([
            "ID", "Name", "Emails", "Contact Numbers", "Job Title",
            "Organization ID", "User ID", "Created At", "Updated At"
        ])
        
        for person in persons:
            emails = "; ".join([email.get("value", "") for email in (person.emails or [])])
            phones = "; ".join([phone.get("value", "") for phone in (person.contact_numbers or [])])
            
            writer.writerow([
                person.id, person.name, emails, phones, person.job_title,
                person.organization_id, person.user_id, person.created_at, person.updated_at
            ])
    
    elif entity_type == "organizations":
        # Export organizations
        query = select(Organization).order_by(Organization.name)
        result = await db.execute(query)
        orgs = result.scalars().all()
        
        writer.writerow([
            "ID", "Name", "Address", "User ID", "Leadgen Lead ID",
            "Created At", "Updated At"
        ])
        
        for org in orgs:
            address_str = str(org.address) if org.address else ""
            writer.writerow([
                org.id, org.name, address_str, org.user_id, org.leadgen_lead_id,
                org.created_at, org.updated_at
            ])
    
    elif entity_type == "products":
        # Export products
        query = select(Product).order_by(Product.name)
        result = await db.execute(query)
        products = result.scalars().all()
        
        writer.writerow([
            "ID", "SKU", "Name", "Description", "Quantity", "Price",
            "Created At", "Updated At"
        ])
        
        for product in products:
            writer.writerow([
                product.id, product.sku, product.name, product.description,
                product.quantity, product.price, product.created_at, product.updated_at
            ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity_type}_export.csv"}
    )


@router.post("/deduplicate/{entity_type}")
async def deduplicate_entities(entity_type: str, dedup_request: DeduplicateRequest,
                              user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Find and merge duplicate entities."""
    valid_types = ["deals", "persons", "organizations", "products"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    if entity_type != dedup_request.entity_type:
        raise HTTPException(status_code=400, detail="Entity type mismatch")
    
    # This is a complex operation - for now, just identify duplicates
    # Full implementation would require sophisticated matching logic
    
    duplicates = []
    
    if entity_type == "persons":
        # Find persons with same email or name
        if "email" in dedup_request.match_fields:
            # This would require custom SQL to search in JSONB emails array
            result = await db.execute(text("""
                SELECT p1.id, p1.name, p1.emails, p2.id as dup_id, p2.name as dup_name
                FROM crm.persons p1
                JOIN crm.persons p2 ON p1.id < p2.id
                WHERE p1.emails::text LIKE '%' || (p2.emails->>0->>'value') || '%'
                   OR p2.emails::text LIKE '%' || (p1.emails->>0->>'value') || '%'
                LIMIT 100
            """))
            
            for row in result.all():
                duplicates.append({
                    "primary_id": row[0],
                    "primary_name": row[1],
                    "duplicate_id": row[3],
                    "duplicate_name": row[4],
                    "match_reason": "Similar email"
                })
    
    elif entity_type == "organizations":
        # Find organizations with same or similar names
        result = await db.execute(text("""
            SELECT o1.id, o1.name, o2.id as dup_id, o2.name as dup_name
            FROM crm.organizations o1
            JOIN crm.organizations o2 ON o1.id < o2.id
            WHERE LOWER(o1.name) = LOWER(o2.name)
               OR similarity(o1.name, o2.name) > 0.8
            LIMIT 100
        """))
        
        for row in result.all():
            duplicates.append({
                "primary_id": row[0],
                "primary_name": row[1],
                "duplicate_id": row[2],
                "duplicate_name": row[3],
                "match_reason": "Similar name"
            })
    
    # Log audit
    await log_audit(db, entity_type, 0, "deduplication_scan", user_id, 
                   new_values={"found_duplicates": len(duplicates), "match_fields": dedup_request.match_fields})
    await db.commit()
    
    return {
        "entity_type": entity_type,
        "duplicates_found": len(duplicates),
        "duplicates": duplicates[:20],  # Return first 20 for review
        "match_fields": dedup_request.match_fields,
        "merge_strategy": dedup_request.merge_strategy
    }


@router.get("/import-templates/{entity_type}")
async def get_import_template(entity_type: str):
    """Get CSV import template for entity type."""
    valid_types = ["deals", "persons", "organizations", "products"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    templates = {
        "deals": {
            "required_fields": ["title"],
            "optional_fields": ["description", "deal_value", "expected_close_date"],
            "example_mapping": {
                "Deal Name": "title",
                "Description": "description", 
                "Value": "deal_value",
                "Close Date": "expected_close_date"
            }
        },
        "persons": {
            "required_fields": ["name"],
            "optional_fields": ["emails", "job_title"],
            "example_mapping": {
                "Full Name": "name",
                "Email": "emails",
                "Job Title": "job_title"
            }
        },
        "organizations": {
            "required_fields": ["name"],
            "optional_fields": ["address"],
            "example_mapping": {
                "Company Name": "name",
                "Address": "address"
            }
        },
        "products": {
            "required_fields": ["name"],
            "optional_fields": ["sku", "description", "price", "quantity"],
            "example_mapping": {
                "Product Name": "name",
                "SKU": "sku",
                "Price": "price",
                "Stock": "quantity"
            }
        }
    }
    
    return templates[entity_type]