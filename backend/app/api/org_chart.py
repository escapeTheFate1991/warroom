"""Org Chart & Goal Ancestry API for War Room

Manages organizational structure and goal hierarchy tracking.
"""

import logging
from typing import Any, Optional, List, Dict
from datetime import date
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Pydantic Models ────────────────────────────────────────────

class OrgMemberCreate(BaseModel):
    name: str
    member_type: str = "agent"  # 'human' | 'agent'
    title: Optional[str] = None
    department: Optional[str] = None
    role: str = "employee"  # 'ceo' | 'director' | 'manager' | 'employee' | 'contractor'
    reports_to_id: Optional[int] = None
    skills: List[str] = []
    budget_allocation: float = 0.0
    agent_id: Optional[int] = None
    user_id: Optional[int] = None

class OrgMemberUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    reports_to_id: Optional[int] = None
    skills: Optional[List[str]] = None
    budget_allocation: Optional[float] = None
    status: Optional[str] = None

class OrgMember(BaseModel):
    id: int
    org_id: int
    member_type: str
    agent_id: Optional[int]
    user_id: Optional[int]
    name: str
    title: Optional[str]
    department: Optional[str]
    reports_to_id: Optional[int]
    role: str
    skills: List[str]
    budget_allocation: float
    status: str
    hired_at: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    goal_type: str = "project"  # 'mission' | 'department' | 'project' | 'task'
    parent_goal_id: Optional[int] = None
    owner_member_id: Optional[int] = None
    due_date: Optional[date] = None

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    goal_type: Optional[str] = None
    parent_goal_id: Optional[int] = None
    owner_member_id: Optional[int] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    due_date: Optional[date] = None

class Goal(BaseModel):
    id: int
    org_id: int
    parent_goal_id: Optional[int]
    title: str
    description: Optional[str]
    goal_type: str
    owner_member_id: Optional[int]
    status: str
    progress: int
    due_date: Optional[date]
    created_at: str
    updated_at: str

class OrgTreeNode(BaseModel):
    id: int
    name: str
    title: Optional[str]
    department: Optional[str]
    role: str
    member_type: str
    status: str
    children: List['OrgTreeNode'] = []

class MoveRequest(BaseModel):
    new_reports_to_id: Optional[int]

# ── Org Members Endpoints ──────────────────────────────────────

@router.get("/api/org-chart/members", response_model=List[OrgMember])
async def list_org_members(
    request: Request,
    db=Depends(get_tenant_db)
):
    """List all organizational members with hierarchy info."""
    org_id = get_org_id(request)
    
    query = """
        SELECT id, org_id, member_type, agent_id, user_id, name, title, department,
               reports_to_id, role, skills, budget_allocation, status, hired_at,
               metadata, created_at, updated_at
        FROM org_members
        WHERE org_id = :org_id
        ORDER BY created_at ASC
    """
    
    result = await db.execute(text(query), {"org_id": org_id})
    members = []
    
    for row in result:
        members.append(OrgMember(
            id=row.id,
            org_id=row.org_id,
            member_type=row.member_type,
            agent_id=row.agent_id,
            user_id=row.user_id,
            name=row.name,
            title=row.title,
            department=row.department,
            reports_to_id=row.reports_to_id,
            role=row.role,
            skills=row.skills or [],
            budget_allocation=float(row.budget_allocation or 0),
            status=row.status,
            hired_at=row.hired_at.isoformat() if row.hired_at else "",
            metadata=row.metadata or {},
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else ""
        ))
    
    return members

@router.post("/api/org-chart/members", response_model=OrgMember)
async def create_org_member(
    member: OrgMemberCreate,
    request: Request,
    db=Depends(get_tenant_db)
):
    """Add a new organizational member."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Validate reports_to_id exists if provided
    if member.reports_to_id:
        check_query = "SELECT id FROM org_members WHERE id = :reports_to_id AND org_id = :org_id"
        check_result = await db.execute(text(check_query), {
            "reports_to_id": member.reports_to_id,
            "org_id": org_id
        })
        if not check_result.fetchone():
            raise HTTPException(status_code=404, detail="Reports-to member not found")
    
    insert_query = """
        INSERT INTO org_members 
        (org_id, member_type, agent_id, user_id, name, title, department, 
         reports_to_id, role, skills, budget_allocation)
        VALUES 
        (:org_id, :member_type, :agent_id, :user_id, :name, :title, :department,
         :reports_to_id, :role, :skills, :budget_allocation)
        RETURNING id, created_at, updated_at, hired_at, metadata, status
    """
    
    result = await db.execute(text(insert_query), {
        "org_id": org_id,
        "member_type": member.member_type,
        "agent_id": member.agent_id,
        "user_id": member.user_id,
        "name": member.name,
        "title": member.title,
        "department": member.department,
        "reports_to_id": member.reports_to_id,
        "role": member.role,
        "skills": member.skills,
        "budget_allocation": member.budget_allocation
    })
    
    row = result.fetchone()
    await db.commit()
    
    return OrgMember(
        id=row.id,
        org_id=org_id,
        member_type=member.member_type,
        agent_id=member.agent_id,
        user_id=member.user_id,
        name=member.name,
        title=member.title,
        department=member.department,
        reports_to_id=member.reports_to_id,
        role=member.role,
        skills=member.skills,
        budget_allocation=member.budget_allocation,
        status=row.status,
        hired_at=row.hired_at.isoformat() if row.hired_at else "",
        metadata=row.metadata or {},
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else ""
    )

@router.put("/api/org-chart/members/{member_id}", response_model=OrgMember)
async def update_org_member(
    member_id: int,
    updates: OrgMemberUpdate,
    request: Request,
    db=Depends(get_tenant_db)
):
    """Update an organizational member."""
    org_id = get_org_id(request)
    
    # Build dynamic update query
    update_fields = []
    params = {"member_id": member_id, "org_id": org_id}
    
    for field, value in updates.dict(exclude_unset=True).items():
        if field == "reports_to_id" and value:
            # Validate reports_to_id exists
            check_query = "SELECT id FROM org_members WHERE id = :reports_to_id AND org_id = :org_id"
            check_result = await db.execute(text(check_query), {
                "reports_to_id": value,
                "org_id": org_id
            })
            if not check_result.fetchone():
                raise HTTPException(status_code=404, detail="Reports-to member not found")
        
        update_fields.append(f"{field} = :{field}")
        params[field] = value
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    update_fields.append("updated_at = NOW()")
    
    update_query = f"""
        UPDATE org_members 
        SET {", ".join(update_fields)}
        WHERE id = :member_id AND org_id = :org_id
        RETURNING id, org_id, member_type, agent_id, user_id, name, title, department,
                  reports_to_id, role, skills, budget_allocation, status, hired_at,
                  metadata, created_at, updated_at
    """
    
    result = await db.execute(text(update_query), params)
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    
    await db.commit()
    
    return OrgMember(
        id=row.id,
        org_id=row.org_id,
        member_type=row.member_type,
        agent_id=row.agent_id,
        user_id=row.user_id,
        name=row.name,
        title=row.title,
        department=row.department,
        reports_to_id=row.reports_to_id,
        role=row.role,
        skills=row.skills or [],
        budget_allocation=float(row.budget_allocation or 0),
        status=row.status,
        hired_at=row.hired_at.isoformat() if row.hired_at else "",
        metadata=row.metadata or {},
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else ""
    )

@router.delete("/api/org-chart/members/{member_id}")
async def remove_org_member(
    member_id: int,
    request: Request,
    db=Depends(get_tenant_db)
):
    """Remove an organizational member (sets status to 'offboarded')."""
    org_id = get_org_id(request)
    
    query = """
        UPDATE org_members 
        SET status = 'offboarded', updated_at = NOW()
        WHERE id = :member_id AND org_id = :org_id
    """
    
    result = await db.execute(text(query), {"member_id": member_id, "org_id": org_id})
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    await db.commit()
    return {"message": "Member offboarded successfully"}

@router.get("/api/org-chart/tree", response_model=List[OrgTreeNode])
async def get_org_tree(
    request: Request,
    db=Depends(get_tenant_db)
):
    """Get organizational tree structure for React Flow rendering."""
    org_id = get_org_id(request)
    
    # Get all active members
    query = """
        SELECT id, name, title, department, role, member_type, reports_to_id, status
        FROM org_members
        WHERE org_id = :org_id AND status = 'active'
        ORDER BY id
    """
    
    result = await db.execute(text(query), {"org_id": org_id})
    members = []
    
    for row in result:
        members.append({
            "id": row.id,
            "name": row.name,
            "title": row.title,
            "department": row.department,
            "role": row.role,
            "member_type": row.member_type,
            "reports_to_id": row.reports_to_id,
            "status": row.status
        })
    
    # Build tree structure
    member_dict = {m["id"]: m for m in members}
    roots = []
    
    for member in members:
        member["children"] = []
        if member["reports_to_id"] is None:
            roots.append(member)
        else:
            parent = member_dict.get(member["reports_to_id"])
            if parent:
                parent["children"].append(member)
    
    # Convert to response model
    def build_tree_node(member_data):
        return OrgTreeNode(
            id=member_data["id"],
            name=member_data["name"],
            title=member_data["title"],
            department=member_data["department"],
            role=member_data["role"],
            member_type=member_data["member_type"],
            status=member_data["status"],
            children=[build_tree_node(child) for child in member_data["children"]]
        )
    
    return [build_tree_node(root) for root in roots]

@router.put("/api/org-chart/members/{member_id}/move")
async def move_org_member(
    member_id: int,
    move_request: MoveRequest,
    request: Request,
    db=Depends(get_tenant_db)
):
    """Move a member to a new reporting structure."""
    org_id = get_org_id(request)
    
    # Validate new reports_to_id exists if provided
    if move_request.new_reports_to_id:
        check_query = "SELECT id FROM org_members WHERE id = :reports_to_id AND org_id = :org_id"
        check_result = await db.execute(text(check_query), {
            "reports_to_id": move_request.new_reports_to_id,
            "org_id": org_id
        })
        if not check_result.fetchone():
            raise HTTPException(status_code=404, detail="New manager not found")
        
        # Prevent circular reporting (member can't report to themselves or their subordinates)
        circular_check = """
            WITH RECURSIVE reporting_chain AS (
                SELECT id, reports_to_id FROM org_members WHERE id = :new_reports_to_id AND org_id = :org_id
                UNION ALL
                SELECT om.id, om.reports_to_id 
                FROM org_members om
                JOIN reporting_chain rc ON om.id = rc.reports_to_id
                WHERE om.org_id = :org_id
            )
            SELECT 1 FROM reporting_chain WHERE id = :member_id
        """
        circular_result = await db.execute(text(circular_check), {
            "member_id": member_id,
            "new_reports_to_id": move_request.new_reports_to_id,
            "org_id": org_id
        })
        if circular_result.fetchone():
            raise HTTPException(status_code=400, detail="Circular reporting relationship detected")
    
    # Update reporting structure
    update_query = """
        UPDATE org_members 
        SET reports_to_id = :new_reports_to_id, updated_at = NOW()
        WHERE id = :member_id AND org_id = :org_id
    """
    
    result = await db.execute(text(update_query), {
        "member_id": member_id,
        "new_reports_to_id": move_request.new_reports_to_id,
        "org_id": org_id
    })
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    await db.commit()
    return {"message": "Member moved successfully"}

# ── Goals Endpoints ─────────────────────────────────────────────

@router.get("/api/org-goals", response_model=List[Goal])
async def list_goals(
    request: Request,
    db=Depends(get_tenant_db)
):
    """List all goals with ancestry chain info."""
    org_id = get_org_id(request)
    
    query = """
        SELECT id, org_id, parent_goal_id, title, description, goal_type,
               owner_member_id, status, progress, due_date, created_at, updated_at
        FROM org_goals
        WHERE org_id = :org_id
        ORDER BY created_at ASC
    """
    
    result = await db.execute(text(query), {"org_id": org_id})
    goals = []
    
    for row in result:
        goals.append(Goal(
            id=row.id,
            org_id=row.org_id,
            parent_goal_id=row.parent_goal_id,
            title=row.title,
            description=row.description,
            goal_type=row.goal_type,
            owner_member_id=row.owner_member_id,
            status=row.status,
            progress=row.progress,
            due_date=row.due_date,
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else ""
        ))
    
    return goals

@router.post("/api/org-goals", response_model=Goal)
async def create_goal(
    goal: GoalCreate,
    request: Request,
    db=Depends(get_tenant_db)
):
    """Create a new goal."""
    org_id = get_org_id(request)
    
    # Validate parent_goal_id if provided
    if goal.parent_goal_id:
        check_query = "SELECT id FROM org_goals WHERE id = :parent_goal_id AND org_id = :org_id"
        check_result = await db.execute(text(check_query), {
            "parent_goal_id": goal.parent_goal_id,
            "org_id": org_id
        })
        if not check_result.fetchone():
            raise HTTPException(status_code=404, detail="Parent goal not found")
    
    # Validate owner_member_id if provided
    if goal.owner_member_id:
        check_query = "SELECT id FROM org_members WHERE id = :owner_member_id AND org_id = :org_id"
        check_result = await db.execute(text(check_query), {
            "owner_member_id": goal.owner_member_id,
            "org_id": org_id
        })
        if not check_result.fetchone():
            raise HTTPException(status_code=404, detail="Owner member not found")
    
    insert_query = """
        INSERT INTO org_goals 
        (org_id, parent_goal_id, title, description, goal_type, owner_member_id, due_date)
        VALUES 
        (:org_id, :parent_goal_id, :title, :description, :goal_type, :owner_member_id, :due_date)
        RETURNING id, status, progress, created_at, updated_at
    """
    
    result = await db.execute(text(insert_query), {
        "org_id": org_id,
        "parent_goal_id": goal.parent_goal_id,
        "title": goal.title,
        "description": goal.description,
        "goal_type": goal.goal_type,
        "owner_member_id": goal.owner_member_id,
        "due_date": goal.due_date
    })
    
    row = result.fetchone()
    await db.commit()
    
    return Goal(
        id=row.id,
        org_id=org_id,
        parent_goal_id=goal.parent_goal_id,
        title=goal.title,
        description=goal.description,
        goal_type=goal.goal_type,
        owner_member_id=goal.owner_member_id,
        status=row.status,
        progress=row.progress,
        due_date=goal.due_date,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else ""
    )

@router.put("/api/org-goals/{goal_id}", response_model=Goal)
async def update_goal(
    goal_id: int,
    updates: GoalUpdate,
    request: Request,
    db=Depends(get_tenant_db)
):
    """Update a goal."""
    org_id = get_org_id(request)
    
    # Build dynamic update query
    update_fields = []
    params = {"goal_id": goal_id, "org_id": org_id}
    
    for field, value in updates.dict(exclude_unset=True).items():
        if field == "parent_goal_id" and value:
            # Validate parent exists
            check_query = "SELECT id FROM org_goals WHERE id = :parent_goal_id AND org_id = :org_id"
            check_result = await db.execute(text(check_query), {
                "parent_goal_id": value,
                "org_id": org_id
            })
            if not check_result.fetchone():
                raise HTTPException(status_code=404, detail="Parent goal not found")
        
        if field == "owner_member_id" and value:
            # Validate owner exists
            check_query = "SELECT id FROM org_members WHERE id = :owner_member_id AND org_id = :org_id"
            check_result = await db.execute(text(check_query), {
                "owner_member_id": value,
                "org_id": org_id
            })
            if not check_result.fetchone():
                raise HTTPException(status_code=404, detail="Owner member not found")
        
        update_fields.append(f"{field} = :{field}")
        params[field] = value
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    update_fields.append("updated_at = NOW()")
    
    update_query = f"""
        UPDATE org_goals 
        SET {", ".join(update_fields)}
        WHERE id = :goal_id AND org_id = :org_id
        RETURNING id, org_id, parent_goal_id, title, description, goal_type,
                  owner_member_id, status, progress, due_date, created_at, updated_at
    """
    
    result = await db.execute(text(update_query), params)
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    await db.commit()
    
    return Goal(
        id=row.id,
        org_id=row.org_id,
        parent_goal_id=row.parent_goal_id,
        title=row.title,
        description=row.description,
        goal_type=row.goal_type,
        owner_member_id=row.owner_member_id,
        status=row.status,
        progress=row.progress,
        due_date=row.due_date,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else ""
    )

# Fix forward reference
OrgTreeNode.model_rebuild()