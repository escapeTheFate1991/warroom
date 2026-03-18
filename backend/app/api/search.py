"""Global Search API - Search across all War Room data sources."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchResult:
    """Single search result."""
    
    def __init__(self, id: str, type: str, title: str, subtitle: str, url: str):
        self.id = id
        self.type = type
        self.title = title
        self.subtitle = subtitle
        self.url = url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "subtitle": self.subtitle,
            "url": self.url,
        }


async def search_contacts(db: AsyncSession, query: str, org_id: int, limit: int = 5) -> List[SearchResult]:
    """Search contacts."""
    try:
        sql = text("""
            SELECT id, 
                   COALESCE(name, email, 'Unnamed Contact') as title,
                   COALESCE(job_title, company, email, '') as subtitle
            FROM crm.contacts 
            WHERE org_id = :org_id 
              AND (
                COALESCE(name, '') ILIKE :search
                OR COALESCE(email, '') ILIKE :search
                OR COALESCE(company, '') ILIKE :search
                OR COALESCE(job_title, '') ILIKE :search
              )
            ORDER BY 
              CASE 
                WHEN COALESCE(name, '') ILIKE :exact THEN 1
                WHEN COALESCE(email, '') ILIKE :exact THEN 2
                ELSE 3
              END,
              name
            LIMIT :limit
        """)
        
        result = await db.execute(sql, {
            "org_id": org_id,
            "search": f"%{query}%",
            "exact": query,
            "limit": limit
        })
        
        contacts = []
        for row in result.fetchall():
            contacts.append(SearchResult(
                id=f"contact-{row.id}",
                type="Contact",
                title=row.title,
                subtitle=row.subtitle,
                url=f"/?tab=crm-contacts&id={row.id}"
            ))
        
        return contacts
    except Exception as e:
        logger.error(f"Error searching contacts: {e}")
        return []


async def search_deals(db: AsyncSession, query: str, org_id: int, limit: int = 5) -> List[SearchResult]:
    """Search deals."""
    try:
        sql = text("""
            SELECT id, title, company_name, value
            FROM crm.deals 
            WHERE org_id = :org_id 
              AND (
                title ILIKE :search
                OR COALESCE(company_name, '') ILIKE :search
              )
            ORDER BY 
              CASE 
                WHEN title ILIKE :exact THEN 1
                ELSE 2
              END,
              title
            LIMIT :limit
        """)
        
        result = await db.execute(sql, {
            "org_id": org_id,
            "search": f"%{query}%",
            "exact": query,
            "limit": limit
        })
        
        deals = []
        for row in result.fetchall():
            subtitle = row.company_name or ""
            if row.value:
                subtitle = f"{subtitle} • ${row.value:,.0f}" if subtitle else f"${row.value:,.0f}"
            
            deals.append(SearchResult(
                id=f"deal-{row.id}",
                type="Deal", 
                title=row.title or "Untitled Deal",
                subtitle=subtitle,
                url=f"/?tab=pipeline-board&deal={row.id}"
            ))
        
        return deals
    except Exception as e:
        logger.error(f"Error searching deals: {e}")
        return []


async def search_competitors(db: AsyncSession, query: str, org_id: int, limit: int = 5) -> List[SearchResult]:
    """Search competitors."""
    try:
        sql = text("""
            SELECT id, handle, platform
            FROM crm.competitors 
            WHERE org_id = :org_id 
              AND (
                handle ILIKE :search
                OR platform ILIKE :search
              )
            ORDER BY 
              CASE 
                WHEN handle ILIKE :exact THEN 1
                ELSE 2
              END,
              handle
            LIMIT :limit
        """)
        
        result = await db.execute(sql, {
            "org_id": org_id,
            "search": f"%{query}%",
            "exact": query,
            "limit": limit
        })
        
        competitors = []
        for row in result.fetchall():
            competitors.append(SearchResult(
                id=f"competitor-{row.id}",
                type="Competitor",
                title=row.handle or "Unknown Handle",
                subtitle=row.platform or "",
                url=f"/?tab=intelligence&competitor={row.id}"
            ))
        
        return competitors
    except Exception as e:
        logger.error(f"Error searching competitors: {e}")
        return []


async def search_competitor_posts(db: AsyncSession, query: str, org_id: int, limit: int = 3) -> List[SearchResult]:
    """Search competitor posts."""
    try:
        sql = text("""
            SELECT cp.id, 
                   COALESCE(cp.hook, LEFT(cp.post_text, 50), 'Untitled Post') as title,
                   c.handle as competitor_handle,
                   c.platform
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE c.org_id = :org_id 
              AND (
                COALESCE(cp.hook, '') ILIKE :search
                OR COALESCE(cp.post_text, '') ILIKE :search
              )
            ORDER BY 
              CASE 
                WHEN COALESCE(cp.hook, '') ILIKE :exact THEN 1
                ELSE 2
              END,
              cp.created_at DESC
            LIMIT :limit
        """)
        
        result = await db.execute(sql, {
            "org_id": org_id,
            "search": f"%{query}%",
            "exact": query,
            "limit": limit
        })
        
        posts = []
        for row in result.fetchall():
            posts.append(SearchResult(
                id=f"post-{row.id}",
                type="Post",
                title=row.title,
                subtitle=f"@{row.competitor_handle} • {row.platform}",
                url=f"/?tab=intelligence&post={row.id}"
            ))
        
        return posts
    except Exception as e:
        logger.error(f"Error searching competitor posts: {e}")
        return []


async def search_digital_copies(db: AsyncSession, query: str, org_id: int, limit: int = 5) -> List[SearchResult]:
    """Search digital copies."""
    try:
        sql = text("""
            SELECT id, name, created_at
            FROM public.ugc_digital_copies 
            WHERE name ILIKE :search
            ORDER BY 
              CASE 
                WHEN name ILIKE :exact THEN 1
                ELSE 2
              END,
              created_at DESC
            LIMIT :limit
        """)
        
        result = await db.execute(sql, {
            "search": f"%{query}%",
            "exact": query,
            "limit": limit
        })
        
        copies = []
        for row in result.fetchall():
            copies.append(SearchResult(
                id=f"digital-copy-{row.id}",
                type="Digital Copy",
                title=row.name,
                subtitle=f"Created {row.created_at.strftime('%m/%d/%y')}",
                url=f"/?tab=ai-studio&copy={row.id}"
            ))
        
        return copies
    except Exception as e:
        logger.error(f"Error searching digital copies: {e}")
        return []


async def search_leads(db: AsyncSession, query: str, org_id: int, limit: int = 5) -> List[SearchResult]:
    """Search leads."""
    try:
        sql = text("""
            SELECT id, company_name, contact_name, email
            FROM crm.leads 
            WHERE org_id = :org_id 
              AND (
                COALESCE(company_name, '') ILIKE :search
                OR COALESCE(contact_name, '') ILIKE :search
                OR COALESCE(email, '') ILIKE :search
              )
            ORDER BY 
              CASE 
                WHEN COALESCE(company_name, '') ILIKE :exact THEN 1
                WHEN COALESCE(contact_name, '') ILIKE :exact THEN 2
                ELSE 3
              END,
              company_name
            LIMIT :limit
        """)
        
        result = await db.execute(sql, {
            "org_id": org_id,
            "search": f"%{query}%",
            "exact": query,
            "limit": limit
        })
        
        leads = []
        for row in result.fetchall():
            title = row.company_name or row.contact_name or row.email or "Unknown Lead"
            subtitle = ""
            if row.contact_name and row.company_name:
                subtitle = f"{row.contact_name}"
            elif row.email:
                subtitle = row.email
            
            leads.append(SearchResult(
                id=f"lead-{row.id}",
                type="Lead",
                title=title,
                subtitle=subtitle,
                url=f"/?tab=leadgen&lead={row.id}"
            ))
        
        return leads
    except Exception as e:
        logger.error(f"Error searching leads: {e}")
        return []


@router.get("/search")
async def global_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Maximum results", le=20),
    db: AsyncSession = Depends(get_tenant_db),
    org_id: int = Depends(get_org_id)
):
    """Global search across all War Room data."""
    
    if not q.strip():
        return {"results": []}
    
    query = q.strip()
    
    # Search all data sources in parallel
    results = []
    
    # Get results from each source (limiting each to preserve mix)
    per_source_limit = max(2, limit // 6)  # Distribute across 6 sources
    
    try:
        # Execute all searches
        contacts = await search_contacts(db, query, org_id, per_source_limit)
        deals = await search_deals(db, query, org_id, per_source_limit)
        competitors = await search_competitors(db, query, org_id, per_source_limit)
        posts = await search_competitor_posts(db, query, org_id, per_source_limit)
        digital_copies = await search_digital_copies(db, query, org_id, per_source_limit)
        leads = await search_leads(db, query, org_id, per_source_limit)
        
        # Combine all results
        all_results = contacts + deals + competitors + posts + digital_copies + leads
        
        # Sort by relevance (exact matches first, then by type priority)
        type_priority = {
            "Contact": 1,
            "Deal": 2,
            "Lead": 3,
            "Competitor": 4,
            "Post": 5,
            "Digital Copy": 6
        }
        
        def relevance_score(result: SearchResult):
            exact_match = query.lower() in result.title.lower()
            return (0 if exact_match else 1, type_priority.get(result.type, 99))
        
        sorted_results = sorted(all_results, key=relevance_score)
        
        # Return top results
        final_results = sorted_results[:limit]
        
        return {
            "results": [result.to_dict() for result in final_results]
        }
        
    except Exception as e:
        logger.error(f"Global search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")