"""Anchor Agent Service — Platform-Wide AI Assistant "Alex"

Alex is a query routing service that understands natural language questions and 
routes them to the right data source across all War Room features.

Features:
- Sales reports (deals, pipeline, forecast)
- Social engagement metrics 
- Content scheduling status
- Contact/organization search
- Agent task status
- Platform help and navigation
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AnchorAgent:
    """Platform-wide AI assistant that can answer questions about any War Room feature."""
    
    CAPABILITIES = {
        "sales_report": {
            "keywords": ["sales", "revenue", "deals", "pipeline", "forecast", "won", "lost", "value"],
            "handler": "_handle_sales_query"
        },
        "social_metrics": {
            "keywords": ["engagement", "followers", "likes", "comments", "shares", "social", "instagram", "tiktok", "views", "reach"],
            "handler": "_handle_social_query"
        },
        "content_schedule": {
            "keywords": ["scheduled", "posts", "calendar", "upcoming", "publish", "content"],
            "handler": "_handle_content_query"
        },
        "contacts": {
            "keywords": ["contacts", "leads", "people", "prospects", "email", "person", "organization"],
            "handler": "_handle_contacts_query"
        },
        "platform_help": {
            "keywords": ["where", "how", "find", "use", "feature", "help", "what is", "navigate"],
            "handler": "_handle_help_query"
        },
        "agent_tasks": {
            "keywords": ["tasks", "agents", "assigned", "completed", "progress", "queue"],
            "handler": "_handle_tasks_query"
        }
    }

    @staticmethod
    def _classify_query(query: str) -> Dict[str, str]:
        """Classify a natural language query to determine the right capability."""
        query_lower = query.lower()
        best_match = None
        max_matches = 0
        
        for capability_name, capability_info in AnchorAgent.CAPABILITIES.items():
            matches = sum(1 for keyword in capability_info["keywords"] if keyword in query_lower)
            if matches > max_matches:
                max_matches = matches
                best_match = capability_name
        
        # Default to help if no strong match
        if not best_match or max_matches == 0:
            best_match = "platform_help"
            
        return {
            "capability": best_match,
            "handler": AnchorAgent.CAPABILITIES[best_match]["handler"],
            "confidence": max_matches
        }

    @staticmethod
    async def process_query(db: AsyncSession, org_id: int, user_id: int, query: str) -> Dict[str, Any]:
        """Route a natural language query to the right data source."""
        classification = AnchorAgent._classify_query(query)
        handler = getattr(AnchorAgent, classification["handler"])
        
        result = await handler(db, org_id, user_id, query)
        result.update({
            "capability": classification["capability"],
            "confidence": classification["confidence"],
            "query": query
        })
        
        return result

    @staticmethod
    async def _handle_sales_query(db: AsyncSession, org_id: int, user_id: int, query: str) -> Dict[str, Any]:
        """Pull sales data — deals by stage, pipeline forecast, won/lost summary."""
        try:
            # Get time period from query if specified
            start_date, end_date = parse_time_period(query)
            
            # Get deals grouped by status
            deals_query = text("""
                SELECT 
                    ps.name as stage_name,
                    COUNT(*) as deal_count,
                    SUM(COALESCE(d.deal_value, 0)) as total_value,
                    AVG(COALESCE(d.deal_value, 0)) as avg_value
                FROM crm.deals d
                LEFT JOIN crm.pipeline_stages ps ON d.stage_id = ps.id
                WHERE d.org_id = :org_id 
                AND d.created_at >= :start_date 
                AND d.created_at <= :end_date
                GROUP BY ps.id, ps.name
                ORDER BY total_value DESC
            """)
            
            result = await db.execute(deals_query, {
                "org_id": org_id,
                "start_date": start_date,
                "end_date": end_date
            })
            deals_by_stage = [dict(row._mapping) for row in result.fetchall()]
            
            # Get won/lost summary
            summary_query = text("""
                SELECT 
                    CASE 
                        WHEN status IS NULL THEN 'Open'
                        WHEN status = true THEN 'Won'
                        WHEN status = false THEN 'Lost'
                    END as deal_status,
                    COUNT(*) as count,
                    SUM(COALESCE(deal_value, 0)) as total_value
                FROM crm.deals 
                WHERE org_id = :org_id 
                AND created_at >= :start_date 
                AND created_at <= :end_date
                GROUP BY status
                ORDER BY total_value DESC
            """)
            
            result = await db.execute(summary_query, {
                "org_id": org_id,
                "start_date": start_date,
                "end_date": end_date
            })
            summary = [dict(row._mapping) for row in result.fetchall()]
            
            # Generate natural language summary
            total_deals = sum(s["count"] for s in summary)
            total_value = sum(s["total_value"] for s in summary)
            won_deals = next((s for s in summary if s["deal_status"] == "Won"), {"count": 0, "total_value": 0})
            
            time_desc = _get_time_description(start_date, end_date)
            summary_text = f"You have {total_deals} deals worth ${total_value:,.2f} {time_desc}. " \
                          f"{won_deals['count']} deals won (${won_deals['total_value']:,.2f})."
            
            return {
                "data": {
                    "deals_by_stage": deals_by_stage,
                    "summary": summary,
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()}
                },
                "summary": summary_text
            }
            
        except Exception as e:
            logger.error(f"Sales query failed: {e}")
            return {"error": "Failed to fetch sales data", "summary": "Sorry, I couldn't retrieve your sales information."}

    @staticmethod
    async def _handle_social_query(db: AsyncSession, org_id: int, user_id: int, query: str) -> Dict[str, Any]:
        """Pull social engagement metrics for specified time period."""
        try:
            start_date, end_date = parse_time_period(query)
            
            # Get social analytics summary
            analytics_query = text("""
                SELECT 
                    sa.platform,
                    COUNT(DISTINCT sa.account_id) as account_count,
                    SUM(sa.impressions) as total_impressions,
                    SUM(sa.engagement) as total_engagement,
                    AVG(sa.engagement_rate) as avg_engagement_rate,
                    SUM(sa.followers_gained) as followers_gained,
                    SUM(sa.likes) as total_likes,
                    SUM(sa.comments) as total_comments,
                    SUM(sa.shares) as total_shares
                FROM crm.social_analytics sa
                JOIN crm.social_accounts acc ON sa.account_id = acc.id
                WHERE acc.org_id = :org_id 
                AND sa.metric_date >= :start_date 
                AND sa.metric_date <= :end_date
                GROUP BY sa.platform
                ORDER BY total_engagement DESC
            """)
            
            result = await db.execute(analytics_query, {
                "org_id": org_id,
                "start_date": start_date.date(),
                "end_date": end_date.date()
            })
            platform_metrics = [dict(row._mapping) for row in result.fetchall()]
            
            # Get content performance
            content_query = text("""
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(CASE WHEN status = 'published' THEN 1 END) as published_posts,
                    AVG(cm.viral_score) as avg_viral_score,
                    SUM(cm.views) as total_views,
                    SUM(cm.likes + cm.comments + cm.shares + cm.saves) as total_engagements
                FROM public.scheduled_posts sp
                LEFT JOIN public.content_metrics cm ON sp.id = cm.post_id
                WHERE sp.org_id = :org_id 
                AND sp.created_at >= :start_date 
                AND sp.created_at <= :end_date
            """)
            
            result = await db.execute(content_query, {
                "org_id": org_id,
                "start_date": start_date,
                "end_date": end_date
            })
            content_metrics = dict(result.fetchone()._mapping)
            
            # Generate summary
            total_engagement = sum(p["total_engagement"] or 0 for p in platform_metrics)
            total_impressions = sum(p["total_impressions"] or 0 for p in platform_metrics)
            
            time_desc = _get_time_description(start_date, end_date)
            summary_text = f"Social metrics {time_desc}: {total_impressions:,} impressions, {total_engagement:,} engagements across {len(platform_metrics)} platforms. "
            
            if content_metrics.get("published_posts"):
                summary_text += f"{content_metrics['published_posts']} posts published with {content_metrics.get('total_views', 0):,} total views."
            
            return {
                "data": {
                    "platform_metrics": platform_metrics,
                    "content_metrics": content_metrics,
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()}
                },
                "summary": summary_text
            }
            
        except Exception as e:
            logger.error(f"Social query failed: {e}")
            return {"error": "Failed to fetch social metrics", "summary": "Sorry, I couldn't retrieve your social media data."}

    @staticmethod  
    async def _handle_content_query(db: AsyncSession, org_id: int, user_id: int, query: str) -> Dict[str, Any]:
        """Show scheduled/published content status."""
        try:
            start_date, end_date = parse_time_period(query)
            
            # Get scheduled content summary
            scheduled_query = text("""
                SELECT 
                    status,
                    platform,
                    COUNT(*) as count,
                    MIN(scheduled_for) as earliest_scheduled,
                    MAX(scheduled_for) as latest_scheduled
                FROM public.scheduled_posts 
                WHERE org_id = :org_id 
                AND created_at >= :start_date 
                AND created_at <= :end_date
                GROUP BY status, platform
                ORDER BY status, count DESC
            """)
            
            result = await db.execute(scheduled_query, {
                "org_id": org_id,
                "start_date": start_date,
                "end_date": end_date
            })
            content_status = [dict(row._mapping) for row in result.fetchall()]
            
            # Get upcoming posts (next 7 days)
            upcoming_query = text("""
                SELECT 
                    platform,
                    scheduled_for,
                    caption,
                    status
                FROM public.scheduled_posts 
                WHERE org_id = :org_id 
                AND status IN ('scheduled', 'draft')
                AND scheduled_for BETWEEN NOW() AND NOW() + INTERVAL '7 days'
                ORDER BY scheduled_for
                LIMIT 10
            """)
            
            result = await db.execute(upcoming_query, {"org_id": org_id})
            upcoming_posts = [dict(row._mapping) for row in result.fetchall()]
            
            # Generate summary
            total_content = sum(s["count"] for s in content_status)
            published_count = sum(s["count"] for s in content_status if s["status"] == "published")
            scheduled_count = sum(s["count"] for s in content_status if s["status"] == "scheduled")
            
            time_desc = _get_time_description(start_date, end_date)
            summary_text = f"Content {time_desc}: {total_content} total pieces, {published_count} published, {scheduled_count} scheduled. "
            
            if upcoming_posts:
                next_post = upcoming_posts[0]
                summary_text += f"Next post: {next_post['platform']} at {next_post['scheduled_for']}."
            
            return {
                "data": {
                    "content_status": content_status,
                    "upcoming_posts": upcoming_posts,
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()}
                },
                "summary": summary_text
            }
            
        except Exception as e:
            logger.error(f"Content query failed: {e}")
            return {"error": "Failed to fetch content data", "summary": "Sorry, I couldn't retrieve your content information."}

    @staticmethod
    async def _handle_contacts_query(db: AsyncSession, org_id: int, user_id: int, query: str) -> Dict[str, Any]:
        """Search contacts, leads, organizations."""
        try:
            # Extract search terms (remove capability keywords)
            search_term = re.sub(r'\b(contacts?|leads?|people|prospects?|email|person|organization)\b', '', query, flags=re.IGNORECASE)
            search_term = search_term.strip()
            
            # If we have a specific search term, search for it
            if search_term:
                # Search persons
                persons_query = text("""
                    SELECT 'person' as type, id, name, emails, job_title, 
                           o.name as organization_name
                    FROM crm.persons p
                    LEFT JOIN crm.organizations o ON p.organization_id = o.id
                    WHERE p.org_id = :org_id 
                    AND (LOWER(p.name) LIKE :search 
                         OR LOWER(p.emails::text) LIKE :search
                         OR LOWER(o.name) LIKE :search)
                    ORDER BY p.name
                    LIMIT 10
                """)
                
                # Search organizations
                orgs_query = text("""
                    SELECT 'organization' as type, id, name, emails, 
                           NULL as job_title, NULL as organization_name
                    FROM crm.organizations
                    WHERE org_id = :org_id 
                    AND (LOWER(name) LIKE :search 
                         OR LOWER(emails::text) LIKE :search)
                    ORDER BY name
                    LIMIT 10
                """)
                
                search_pattern = f"%{search_term.lower()}%"
                
                persons_result = await db.execute(persons_query, {"org_id": org_id, "search": search_pattern})
                orgs_result = await db.execute(orgs_query, {"org_id": org_id, "search": search_pattern})
                
                contacts = [dict(row._mapping) for row in persons_result.fetchall()]
                contacts.extend([dict(row._mapping) for row in orgs_result.fetchall()])
                
                summary_text = f"Found {len(contacts)} contacts matching '{search_term}'"
                
            else:
                # General contact stats
                stats_query = text("""
                    SELECT 
                        'persons' as type,
                        COUNT(*) as count,
                        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_count
                    FROM crm.persons WHERE org_id = :org_id
                    UNION ALL
                    SELECT 
                        'organizations' as type,
                        COUNT(*) as count,
                        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_count
                    FROM crm.organizations WHERE org_id = :org_id
                """)
                
                result = await db.execute(stats_query, {"org_id": org_id})
                stats = [dict(row._mapping) for row in result.fetchall()]
                contacts = []
                
                total_persons = next((s["count"] for s in stats if s["type"] == "persons"), 0)
                total_orgs = next((s["count"] for s in stats if s["type"] == "organizations"), 0)
                
                summary_text = f"You have {total_persons} contacts and {total_orgs} organizations in your CRM."
            
            return {
                "data": {
                    "contacts": contacts,
                    "search_term": search_term
                },
                "summary": summary_text
            }
            
        except Exception as e:
            logger.error(f"Contacts query failed: {e}")
            return {"error": "Failed to search contacts", "summary": "Sorry, I couldn't search your contacts."}

    @staticmethod
    async def _handle_help_query(db: AsyncSession, org_id: int, user_id: int, query: str) -> Dict[str, Any]:
        """Answer platform navigation and feature questions."""
        
        FEATURE_MAP = {
            "contacts": {
                "tab": "crm-contacts",
                "description": "Manage contacts, leads, and organizations",
                "features": ["Add contacts", "Import CSV", "Custom fields", "Tags"]
            },
            "deals": {
                "tab": "pipeline-board",
                "description": "Visual sales pipeline with drag-and-drop stages",
                "features": ["Pipeline view", "Forecast", "Deal products"]
            },
            "social": {
                "tab": "social",
                "description": "Social media dashboard — connect and manage accounts",
                "features": ["Connect Instagram/TikTok/etc", "View analytics", "Schedule posts"]
            },
            "agents": {
                "tab": "agents",
                "description": "Create and manage AI agents with custom skills",
                "features": ["Create agents", "Assign skills", "View task history"]
            },
            "scheduler": {
                "tab": "scheduler",
                "description": "Content calendar for scheduling social media posts",
                "features": ["Schedule posts", "Calendar view", "Auto-publish"]
            },
            "video_studio": {
                "tab": "ugc-studio",
                "description": "Video Copycat — reverse-engineer competitor videos",
                "features": ["Analyze videos", "Generate scripts", "Create assets"]
            },
            "library": {
                "tab": "library",
                "description": "Mental Library — process videos into knowledge documents",
                "features": ["Add YouTube URLs", "View processed documents", "Convert to skills"]
            },
            "workflows": {
                "tab": "workflows",
                "description": "Automate business processes with workflow templates",
                "features": ["Create workflows", "Trigger automation", "Track executions"]
            },
            "email": {
                "tab": "email",
                "description": "Email inbox integration",
                "features": ["Connect Gmail/IMAP", "Send/receive emails", "Templates"]
            },
            "kanban": {
                "tab": "kanban",
                "description": "Task management with Kanban board",
                "features": ["Create tasks", "Assign to agents", "Track progress"]
            },
            "settings": {
                "tab": "settings",
                "description": "Platform settings and integrations",
                "features": ["API keys", "OAuth connections", "User preferences"]
            },
        }
        
        # Find relevant features based on query
        query_lower = query.lower()
        matches = []
        
        for feature_key, feature_info in FEATURE_MAP.items():
            score = 0
            if feature_key in query_lower:
                score += 10
            if any(keyword in query_lower for keyword in feature_info["description"].lower().split()):
                score += 5
            if any(feature.lower() in query_lower for feature in feature_info["features"]):
                score += 3
                
            if score > 0:
                matches.append((score, feature_key, feature_info))
        
        matches.sort(reverse=True, key=lambda x: x[0])
        
        if matches:
            best_match = matches[0]
            feature_info = best_match[2]
            summary_text = f"Go to the '{best_match[1].title()}' tab. {feature_info['description']}. " \
                          f"Available features: {', '.join(feature_info['features'])}."
            
            relevant_features = [{"name": k, **v} for score, k, v in matches[:3]]
        else:
            summary_text = "I'm not sure which feature you're looking for. Here are the main areas of War Room you can explore."
            relevant_features = [{"name": k, **v} for k, v in FEATURE_MAP.items()]
        
        return {
            "data": {
                "relevant_features": relevant_features,
                "all_features": FEATURE_MAP
            },
            "summary": summary_text
        }

    @staticmethod
    async def _handle_tasks_query(db: AsyncSession, org_id: int, user_id: int, query: str) -> Dict[str, Any]:
        """Show agent task status and results."""
        try:
            start_date, end_date = parse_time_period(query)
            
            # Get task summary by status
            tasks_query = text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(priority) as avg_priority
                FROM public.agent_task_queue
                WHERE org_id = :org_id 
                AND created_at >= :start_date 
                AND created_at <= :end_date
                GROUP BY status
                ORDER BY 
                    CASE status 
                        WHEN 'in_progress' THEN 1
                        WHEN 'pending' THEN 2
                        WHEN 'assigned' THEN 3
                        WHEN 'completed' THEN 4
                        WHEN 'failed' THEN 5
                        WHEN 'cancelled' THEN 6
                        ELSE 7
                    END
            """)
            
            result = await db.execute(tasks_query, {
                "org_id": org_id,
                "start_date": start_date,
                "end_date": end_date
            })
            task_summary = [dict(row._mapping) for row in result.fetchall()]
            
            # Get recent active tasks
            recent_query = text("""
                SELECT 
                    task_title,
                    status,
                    priority,
                    created_at,
                    started_at,
                    completed_at
                FROM public.agent_task_queue
                WHERE org_id = :org_id 
                AND status IN ('pending', 'assigned', 'in_progress')
                ORDER BY 
                    CASE status 
                        WHEN 'in_progress' THEN 1
                        WHEN 'assigned' THEN 2
                        WHEN 'pending' THEN 3
                    END,
                    priority DESC,
                    created_at DESC
                LIMIT 10
            """)
            
            result = await db.execute(recent_query, {"org_id": org_id})
            active_tasks = [dict(row._mapping) for row in result.fetchall()]
            
            # Generate summary
            total_tasks = sum(s["count"] for s in task_summary)
            in_progress = sum(s["count"] for s in task_summary if s["status"] == "in_progress")
            pending = sum(s["count"] for s in task_summary if s["status"] == "pending")
            completed = sum(s["count"] for s in task_summary if s["status"] == "completed")
            
            time_desc = _get_time_description(start_date, end_date)
            summary_text = f"Agent tasks {time_desc}: {total_tasks} total, {in_progress} in progress, {pending} pending, {completed} completed."
            
            return {
                "data": {
                    "task_summary": task_summary,
                    "active_tasks": active_tasks,
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()}
                },
                "summary": summary_text
            }
            
        except Exception as e:
            logger.error(f"Tasks query failed: {e}")
            return {"error": "Failed to fetch task data", "summary": "Sorry, I couldn't retrieve your task information."}


def parse_time_period(query: str) -> Tuple[datetime, datetime]:
    """Parse natural language time references."""
    now = datetime.now()
    query_lower = query.lower()
    
    if "last hour" in query_lower or "past hour" in query_lower:
        return now - timedelta(hours=1), now
    elif "today" in query_lower:
        return now.replace(hour=0, minute=0, second=0, microsecond=0), now
    elif "yesterday" in query_lower:
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=0, minute=0, second=0, microsecond=0), yesterday.replace(hour=23, minute=59, second=59)
    elif "this week" in query_lower:
        days_since_monday = now.weekday()
        monday = now - timedelta(days=days_since_monday)
        return monday.replace(hour=0, minute=0, second=0, microsecond=0), now
    elif "last week" in query_lower:
        days_since_monday = now.weekday()
        last_monday = now - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.replace(hour=0, minute=0, second=0, microsecond=0), last_sunday.replace(hour=23, minute=59, second=59)
    elif "this month" in query_lower:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now
    elif "last 30 days" in query_lower or "past 30 days" in query_lower:
        return now - timedelta(days=30), now
    elif "last 7 days" in query_lower or "past 7 days" in query_lower:
        return now - timedelta(days=7), now
    else:
        # Default to last 30 days
        return now - timedelta(days=30), now


def _get_time_description(start_date: datetime, end_date: datetime) -> str:
    """Get a natural language description of the time period."""
    now = datetime.now()
    
    if start_date.date() == end_date.date() == now.date():
        return "today"
    elif (now - start_date).days == 1 and start_date.date() == end_date.date():
        return "yesterday"
    elif (now - start_date).days <= 1:
        return "in the last hour"
    elif (now - start_date).days <= 7:
        return "this week"
    elif (now - start_date).days <= 30:
        return "in the last 30 days"
    else:
        return f"from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"