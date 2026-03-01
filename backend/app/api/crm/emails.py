"""CRM Emails API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_crm_db
from app.models.crm.email import Email, EmailAttachment, EmailTemplate
from app.models.crm.audit import AuditLog
from .schemas import EmailResponse, EmailCreate

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


@router.get("/emails", response_model=List[EmailResponse])
async def list_emails(
    person_id: Optional[int] = None,
    deal_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    folder: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List emails with filtering."""
    query = select(Email).options(
        selectinload(Email.attachments),
        selectinload(Email.person),
        selectinload(Email.deal)
    )
    
    if person_id:
        query = query.where(Email.person_id == person_id)
    if deal_id:
        query = query.where(Email.deal_id == deal_id)
    if is_read is not None:
        query = query.where(Email.is_read == is_read)
    if folder:
        # Search in JSONB folders field
        query = query.where(Email.folders.op('?')(folder))
    
    query = query.order_by(Email.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(email_id: int, mark_read: bool = Query(default=True),
                   db: AsyncSession = Depends(get_crm_db)):
    """Get email thread/single email."""
    result = await db.execute(
        select(Email)
        .options(
            selectinload(Email.attachments),
            selectinload(Email.person),
            selectinload(Email.deal),
            selectinload(Email.children),  # Thread replies
            selectinload(Email.parent)     # Parent if this is a reply
        )
        .where(Email.id == email_id)
    )
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Mark as read if requested
    if mark_read and not email.is_read:
        email.is_read = True
        await db.commit()
    
    return email


@router.post("/emails", response_model=EmailResponse)
async def compose_email(email_data: EmailCreate, user_id: Optional[int] = None,
                       db: AsyncSession = Depends(get_crm_db)):
    """Compose/send email (placeholder - stores in DB for now)."""
    # For now, just store the email in the database
    # In a full implementation, this would integrate with SMTP/Gmail API
    
    email = Email(**email_data.model_dump(exclude_unset=True))
    
    # Generate a unique message_id for tracking
    import uuid
    email.message_id = f"<{uuid.uuid4()}@warroom.local>"
    email.unique_id = str(uuid.uuid4())
    
    db.add(email)
    await db.commit()
    await db.refresh(email)
    
    # Log audit
    await log_audit(db, "email", email.id, "composed", user_id, 
                   new_values=email_data.model_dump())
    await db.commit()
    
    # TODO: Implement actual email sending via SMTP
    logger.info("Email composed and stored (actual sending not implemented): %s", email.subject)
    
    return email


@router.put("/emails/{email_id}/read")
async def mark_email_read(email_id: int, is_read: bool = True, 
                         db: AsyncSession = Depends(get_crm_db)):
    """Mark email as read/unread."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email.is_read = is_read
    await db.commit()
    
    return {"status": "updated", "email_id": email_id, "is_read": is_read}


@router.put("/emails/{email_id}/folder")
async def move_email_folder(email_id: int, folder: str, 
                           db: AsyncSession = Depends(get_crm_db)):
    """Move email to folder."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Add folder to the folders JSONB field
    folders = email.folders or {}
    folders[folder] = True
    email.folders = folders
    
    await db.commit()
    
    return {"status": "moved", "email_id": email_id, "folder": folder}


@router.delete("/emails/{email_id}")
async def delete_email(email_id: int, user_id: Optional[int] = None,
                      db: AsyncSession = Depends(get_crm_db)):
    """Delete an email."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    old_values = {
        "subject": email.subject,
        "source": email.source,
        "message_id": email.message_id
    }
    
    await db.execute(delete(Email).where(Email.id == email_id))
    
    # Log audit
    await log_audit(db, "email", email_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "email_id": email_id}


@router.get("/emails/{email_id}/thread", response_model=List[EmailResponse])
async def get_email_thread(email_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get full email thread."""
    # Get the root email
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Find root of thread
    root_email = email
    while root_email.parent_id:
        parent_result = await db.execute(
            select(Email).where(Email.id == root_email.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            break
        root_email = parent
    
    # Get all emails in thread using message_id or reference_ids
    thread_condition = Email.id == root_email.id
    
    if root_email.message_id:
        thread_condition = (
            (Email.message_id == root_email.message_id) |
            (Email.reference_ids.op('?')(root_email.message_id)) |
            (Email.parent_id == root_email.id)
        )
    
    result = await db.execute(
        select(Email)
        .where(thread_condition)
        .order_by(Email.created_at)
    )
    
    return result.scalars().all()


@router.get("/emails/unread-count")
async def get_unread_count(person_id: Optional[int] = None, deal_id: Optional[int] = None,
                          db: AsyncSession = Depends(get_crm_db)):
    """Get count of unread emails."""
    from sqlalchemy import func
    
    query = select(func.count(Email.id)).where(Email.is_read == False)
    
    if person_id:
        query = query.where(Email.person_id == person_id)
    if deal_id:
        query = query.where(Email.deal_id == deal_id)
    
    result = await db.execute(query)
    count = result.scalar() or 0
    
    return {"unread_count": count}


# ===== Email Templates =====

@router.get("/email-templates")
async def list_email_templates(db: AsyncSession = Depends(get_crm_db)):
    """List email templates."""
    result = await db.execute(
        select(EmailTemplate).order_by(EmailTemplate.name)
    )
    return result.scalars().all()


@router.get("/email-templates/{template_id}")
async def get_email_template(template_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get email template."""
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    return template


class EmailTemplateCreate(BaseModel):
    name: str
    subject: Optional[str] = None
    content: Optional[str] = None


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None


@router.post("/email-templates")
async def create_email_template(data: EmailTemplateCreate, db: AsyncSession = Depends(get_crm_db)):
    """Create a new email template."""
    template = EmailTemplate(name=data.name, subject=data.subject, content=data.content)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/email-templates/{template_id}")
async def update_email_template(template_id: int, data: EmailTemplateUpdate, db: AsyncSession = Depends(get_crm_db)):
    """Update an email template."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/email-templates/{template_id}")
async def delete_email_template(template_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Delete an email template."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    await db.execute(delete(EmailTemplate).where(EmailTemplate.id == template_id))
    await db.commit()
    return {"status": "deleted", "template_id": template_id}