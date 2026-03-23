#!/usr/bin/env python3
"""
Session Manager - Development session context tracking

Tracks and manages development session state:
- Current task and objectives
- Files recently modified/viewed
- Error patterns and resolutions
- Context degradation detection
- Session handoff between developers/agents

Integrates with War Room's agent communication and vector memory.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import subprocess

import click
import aiofiles
from dataclasses import dataclass, asdict
import hashlib

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.services.vector_memory import store_memory, search_memory

logger = logging.getLogger(__name__)

@dataclass
class SessionContext:
    """Current development session context."""
    session_id: str
    current_task: str
    objective: str
    priority: int  # 1-10
    started_at: str
    last_activity: str
    files_modified: List[str]
    files_viewed: List[str]
    error_patterns: List[Dict[str, Any]]
    resolved_issues: List[Dict[str, Any]]
    context_quality: float  # 0.0-1.0
    tags: List[str]
    
@dataclass
class ContextDegradation:
    """Context degradation detection."""
    severity: str  # low, medium, high, critical
    reason: str
    recommendations: List[str]
    last_check: str


class SessionManager:
    """Development session context manager."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.context_dir = self.project_root / ".context"
        self.sessions_dir = self.context_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Session tracking
        self.current_session: Optional[SessionContext] = None
        self.session_file = self.sessions_dir / "current.json"
        
    async def start_session(self, task: str, objective: str = "", priority: int = 5, org_id: str = "1") -> SessionContext:
        """Start a new development session."""
        session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        session = SessionContext(
            session_id=session_id,
            current_task=task,
            objective=objective or f"Working on: {task}",
            priority=priority,
            started_at=datetime.utcnow().isoformat(),
            last_activity=datetime.utcnow().isoformat(),
            files_modified=[],
            files_viewed=[],
            error_patterns=[],
            resolved_issues=[],
            context_quality=1.0,
            tags=self._extract_tags(task, objective)
        )
        
        self.current_session = session
        await self._save_session()
        
        # Store session start in vector memory
        await self._store_session_event("session_start", {
            "task": task,
            "objective": objective,
            "priority": priority
        }, org_id)
        
        logger.info(f"Started session {session_id}: {task}")
        return session
    
    async def update_session(self, 
                           task: str = None,
                           objective: str = None,
                           priority: int = None,
                           org_id: str = "1") -> Optional[SessionContext]:
        """Update current session context."""
        if not self.current_session:
            return None
        
        updated = False
        if task and task != self.current_session.current_task:
            self.current_session.current_task = task
            updated = True
            
        if objective and objective != self.current_session.objective:
            self.current_session.objective = objective
            updated = True
            
        if priority and priority != self.current_session.priority:
            self.current_session.priority = priority
            updated = True
        
        if updated:
            self.current_session.last_activity = datetime.utcnow().isoformat()
            self.current_session.tags = self._extract_tags(
                self.current_session.current_task,
                self.current_session.objective
            )
            await self._save_session()
            
            # Store update in vector memory
            await self._store_session_event("session_update", {
                "task": self.current_session.current_task,
                "objective": self.current_session.objective,
                "priority": self.current_session.priority
            }, org_id)
        
        return self.current_session
    
    async def track_file_activity(self, file_path: str, activity_type: str = "modified", org_id: str = "1"):
        """Track file activity (modified, viewed, created)."""
        if not self.current_session:
            await self._load_or_create_session()
        
        # Normalize file path
        normalized_path = self._normalize_file_path(file_path)
        timestamp = datetime.utcnow().isoformat()
        
        if activity_type == "modified":
            if normalized_path not in self.current_session.files_modified:
                self.current_session.files_modified.append(normalized_path)
                # Keep only last 20 files
                self.current_session.files_modified = self.current_session.files_modified[-20:]
        elif activity_type == "viewed":
            if normalized_path not in self.current_session.files_viewed:
                self.current_session.files_viewed.append(normalized_path)
                # Keep only last 30 files
                self.current_session.files_viewed = self.current_session.files_viewed[-30:]
        
        self.current_session.last_activity = timestamp
        await self._save_session()
        
        # Store significant file activities in memory
        if activity_type == "modified":
            await self._store_session_event("file_modified", {
                "file_path": normalized_path,
                "timestamp": timestamp
            }, org_id)
    
    async def track_error(self, error_message: str, error_type: str, stack_trace: str = None, org_id: str = "1"):
        """Track error occurrence during session."""
        if not self.current_session:
            await self._load_or_create_session()
        
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_message": error_message,
            "error_type": error_type,
            "stack_trace": stack_trace,
            "context_files": self.current_session.files_modified[-5:] if self.current_session.files_modified else [],
            "resolved": False
        }
        
        self.current_session.error_patterns.append(error_entry)
        # Keep only last 10 errors
        self.current_session.error_patterns = self.current_session.error_patterns[-10:]
        
        self.current_session.last_activity = datetime.utcnow().isoformat()
        await self._save_session()
        
        # Store error in vector memory for pattern detection
        error_text = f"Error: {error_message} | Type: {error_type} | Context: {', '.join(error_entry['context_files'])}"
        await store_memory(
            org_id=org_id,
            user_id="session_manager",
            text=error_text,
            metadata={
                "type": "error_tracking",
                "error_type": error_type,
                "session_id": self.current_session.session_id,
                "context_files": error_entry["context_files"],
                "timestamp": error_entry["timestamp"]
            }
        )
    
    async def track_resolution(self, error_index: int, solution: str, org_id: str = "1"):
        """Track error resolution."""
        if not self.current_session or error_index >= len(self.current_session.error_patterns):
            return
        
        error = self.current_session.error_patterns[error_index]
        error["resolved"] = True
        error["solution"] = solution
        error["resolved_at"] = datetime.utcnow().isoformat()
        
        # Add to resolved issues
        resolution_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_message": error["error_message"],
            "error_type": error["error_type"],
            "solution": solution,
            "resolution_time_minutes": self._calculate_resolution_time(error["timestamp"])
        }
        
        self.current_session.resolved_issues.append(resolution_entry)
        # Keep only last 20 resolutions
        self.current_session.resolved_issues = self.current_session.resolved_issues[-20:]
        
        self.current_session.last_activity = datetime.utcnow().isoformat()
        await self._save_session()
        
        # Store resolution in vector memory
        resolution_text = f"Resolution: {error['error_message']} | Solution: {solution} | Type: {error['error_type']}"
        await store_memory(
            org_id=org_id,
            user_id="session_manager",
            text=resolution_text,
            metadata={
                "type": "error_resolution",
                "error_type": error["error_type"],
                "session_id": self.current_session.session_id,
                "resolution_time_minutes": resolution_entry["resolution_time_minutes"],
                "timestamp": resolution_entry["timestamp"]
            }
        )
    
    async def get_session_context(self, org_id: str = "1") -> Dict[str, Any]:
        """Get comprehensive current session context."""
        if not self.current_session:
            await self._load_or_create_session()
        
        context = {
            "current_session": asdict(self.current_session) if self.current_session else None,
            "context_quality": await self._assess_context_quality(),
            "degradation": await self._check_context_degradation(),
            "recommendations": await self._get_context_recommendations(org_id),
            "related_sessions": await self._find_related_sessions(org_id)
        }
        
        return context
    
    async def handoff_session(self, to_agent: str, handoff_notes: str, org_id: str = "1") -> Dict[str, Any]:
        """Handoff session to another agent/developer."""
        if not self.current_session:
            return {"error": "No active session to handoff"}
        
        handoff_data = {
            "session_id": self.current_session.session_id,
            "handoff_time": datetime.utcnow().isoformat(),
            "from_agent": "session_manager",
            "to_agent": to_agent,
            "handoff_notes": handoff_notes,
            "context_snapshot": asdict(self.current_session),
            "context_quality": await self._assess_context_quality(),
            "critical_files": self.current_session.files_modified[-10:],
            "pending_errors": [e for e in self.current_session.error_patterns if not e.get("resolved", False)]
        }
        
        # Store handoff in memory
        handoff_text = f"Session handoff: {self.current_session.current_task} | To: {to_agent} | Notes: {handoff_notes}"
        await store_memory(
            org_id=org_id,
            user_id="session_manager",
            text=handoff_text,
            metadata={
                "type": "session_handoff",
                "session_id": self.current_session.session_id,
                "to_agent": to_agent,
                "context_quality": handoff_data["context_quality"],
                "timestamp": handoff_data["handoff_time"]
            }
        )
        
        # Archive current session
        await self._archive_session()
        
        return handoff_data
    
    async def end_session(self, summary: str = "", org_id: str = "1") -> Dict[str, Any]:
        """End current development session."""
        if not self.current_session:
            return {"error": "No active session to end"}
        
        session_summary = {
            "session_id": self.current_session.session_id,
            "ended_at": datetime.utcnow().isoformat(),
            "duration_minutes": self._calculate_session_duration(),
            "task": self.current_session.current_task,
            "objective": self.current_session.objective,
            "files_modified": len(self.current_session.files_modified),
            "errors_encountered": len(self.current_session.error_patterns),
            "errors_resolved": len([e for e in self.current_session.error_patterns if e.get("resolved", False)]),
            "context_quality": await self._assess_context_quality(),
            "summary": summary or "Session ended",
            "achievements": await self._generate_session_achievements()
        }
        
        # Store session summary in memory
        summary_text = f"Session ended: {self.current_session.current_task} | Duration: {session_summary['duration_minutes']} min | Files: {session_summary['files_modified']} | Summary: {summary}"
        await store_memory(
            org_id=org_id,
            user_id="session_manager",
            text=summary_text,
            metadata={
                "type": "session_summary",
                "session_id": self.current_session.session_id,
                "duration_minutes": session_summary["duration_minutes"],
                "context_quality": session_summary["context_quality"],
                "timestamp": session_summary["ended_at"]
            }
        )
        
        # Archive session
        await self._archive_session()
        self.current_session = None
        
        return session_summary
    
    async def search_session_history(self, query: str, limit: int = 5, org_id: str = "1") -> List[Dict[str, Any]]:
        """Search session history using semantic search."""
        try:
            results = await search_memory(org_id, f"session: {query}", limit=limit, score_threshold=0.6)
            
            session_results = []
            for hit in results:
                payload = hit.get("payload", {})
                metadata = payload.get("metadata", {})
                
                if metadata.get("type", "").startswith("session_"):
                    session_results.append({
                        "relevance": hit.get("score", 0.0),
                        "type": metadata.get("type"),
                        "session_id": metadata.get("session_id"),
                        "timestamp": metadata.get("timestamp"),
                        "content": payload.get("text", ""),
                        "metadata": metadata
                    })
            
            return sorted(session_results, key=lambda x: x["relevance"], reverse=True)
            
        except Exception as e:
            logger.error(f"Session history search failed: {e}")
            return []
    
    async def get_session_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get session statistics for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Load archived sessions
        archived_sessions = await self._load_archived_sessions(cutoff_date)
        
        stats = {
            "period_days": days,
            "total_sessions": len(archived_sessions),
            "total_duration_hours": 0,
            "average_session_duration_minutes": 0,
            "total_files_modified": 0,
            "total_errors": 0,
            "total_resolutions": 0,
            "error_resolution_rate": 0.0,
            "most_common_errors": {},
            "most_modified_files": {},
            "context_quality_trend": []
        }
        
        if not archived_sessions:
            return stats
        
        total_duration = 0
        total_files = set()
        error_types = {}
        file_counts = {}
        
        for session_data in archived_sessions:
            # Calculate duration
            start = datetime.fromisoformat(session_data.get("started_at", ""))
            end = datetime.fromisoformat(session_data.get("ended_at", session_data.get("started_at", "")))
            duration_minutes = (end - start).total_seconds() / 60
            total_duration += duration_minutes
            
            # Count files
            files_modified = session_data.get("files_modified", [])
            for file_path in files_modified:
                total_files.add(file_path)
                file_counts[file_path] = file_counts.get(file_path, 0) + 1
            
            # Count errors
            errors = session_data.get("error_patterns", [])
            resolutions = session_data.get("resolved_issues", [])
            stats["total_errors"] += len(errors)
            stats["total_resolutions"] += len(resolutions)
            
            for error in errors:
                error_type = error.get("error_type", "unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        stats["total_duration_hours"] = total_duration / 60
        stats["average_session_duration_minutes"] = total_duration / len(archived_sessions) if archived_sessions else 0
        stats["total_files_modified"] = len(total_files)
        stats["error_resolution_rate"] = (stats["total_resolutions"] / stats["total_errors"]) if stats["total_errors"] > 0 else 0
        
        # Top errors and files
        stats["most_common_errors"] = dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10])
        stats["most_modified_files"] = dict(sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return stats
    
    def _extract_tags(self, task: str, objective: str) -> List[str]:
        """Extract tags from task and objective."""
        text = f"{task} {objective}".lower()
        tags = []
        
        # Technology tags
        tech_keywords = {
            "api": "api", "database": "database", "frontend": "frontend", 
            "backend": "backend", "auth": "authentication", "jwt": "authentication",
            "react": "frontend", "typescript": "frontend", "python": "backend",
            "sql": "database", "docker": "infrastructure", "migration": "database"
        }
        
        for keyword, tag in tech_keywords.items():
            if keyword in text:
                tags.append(tag)
        
        # Priority tags
        urgent_keywords = ["urgent", "critical", "bug", "error", "fix", "broken"]
        if any(keyword in text for keyword in urgent_keywords):
            tags.append("urgent")
        
        feature_keywords = ["feature", "new", "implement", "add", "create"]
        if any(keyword in text for keyword in feature_keywords):
            tags.append("feature")
        
        return list(set(tags))  # Remove duplicates
    
    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path relative to project root."""
        path = Path(file_path)
        if path.is_absolute():
            try:
                return str(path.relative_to(self.project_root))
            except ValueError:
                return str(path)
        return str(path)
    
    def _calculate_resolution_time(self, error_timestamp: str) -> int:
        """Calculate resolution time in minutes."""
        try:
            error_time = datetime.fromisoformat(error_timestamp)
            resolution_time = datetime.utcnow()
            return int((resolution_time - error_time).total_seconds() / 60)
        except:
            return 0
    
    def _calculate_session_duration(self) -> int:
        """Calculate current session duration in minutes."""
        if not self.current_session:
            return 0
        
        try:
            start_time = datetime.fromisoformat(self.current_session.started_at)
            current_time = datetime.utcnow()
            return int((current_time - start_time).total_seconds() / 60)
        except:
            return 0
    
    async def _assess_context_quality(self) -> float:
        """Assess current context quality (0.0-1.0)."""
        if not self.current_session:
            return 0.0
        
        quality_score = 1.0
        
        # Age degradation
        session_age_hours = self._calculate_session_duration() / 60
        if session_age_hours > 24:
            quality_score *= 0.5  # Significant degradation after 24 hours
        elif session_age_hours > 8:
            quality_score *= 0.8  # Moderate degradation after 8 hours
        elif session_age_hours > 4:
            quality_score *= 0.9  # Slight degradation after 4 hours
        
        # Unresolved errors impact
        unresolved_errors = len([e for e in self.current_session.error_patterns if not e.get("resolved", False)])
        if unresolved_errors > 5:
            quality_score *= 0.6
        elif unresolved_errors > 2:
            quality_score *= 0.8
        
        # File activity relevance
        if not self.current_session.files_modified and session_age_hours > 1:
            quality_score *= 0.7  # No file activity is concerning
        
        return max(0.0, min(1.0, quality_score))
    
    async def _check_context_degradation(self) -> ContextDegradation:
        """Check for context degradation and provide recommendations."""
        quality = await self._assess_context_quality()
        
        if quality < 0.3:
            return ContextDegradation(
                severity="critical",
                reason="Context severely degraded due to time and/or errors",
                recommendations=[
                    "Start fresh session with clear objectives",
                    "Review and resolve pending errors",
                    "Validate recent changes"
                ],
                last_check=datetime.utcnow().isoformat()
            )
        elif quality < 0.5:
            return ContextDegradation(
                severity="high",
                reason="Context significantly degraded",
                recommendations=[
                    "Review session objectives and progress",
                    "Address unresolved errors",
                    "Update task documentation"
                ],
                last_check=datetime.utcnow().isoformat()
            )
        elif quality < 0.7:
            return ContextDegradation(
                severity="medium",
                reason="Moderate context degradation",
                recommendations=[
                    "Update session task if needed",
                    "Review recent file changes",
                    "Consider context refresh"
                ],
                last_check=datetime.utcnow().isoformat()
            )
        else:
            return ContextDegradation(
                severity="low",
                reason="Context quality is good",
                recommendations=[
                    "Continue current work",
                    "Maintain regular updates"
                ],
                last_check=datetime.utcnow().isoformat()
            )
    
    async def _get_context_recommendations(self, org_id: str) -> List[str]:
        """Get personalized context recommendations."""
        recommendations = []
        
        if not self.current_session:
            recommendations.append("Start a new development session")
            return recommendations
        
        # Check for similar past sessions
        similar_sessions = await search_memory(
            org_id, 
            f"session: {self.current_session.current_task}", 
            limit=3
        )
        
        if similar_sessions:
            recommendations.append("Review similar past sessions for patterns")
        
        # Check for unresolved errors
        unresolved = [e for e in self.current_session.error_patterns if not e.get("resolved", False)]
        if unresolved:
            recommendations.append(f"Address {len(unresolved)} unresolved errors")
        
        # Check session duration
        duration = self._calculate_session_duration()
        if duration > 480:  # 8 hours
            recommendations.append("Consider taking a break or ending session")
        elif duration > 240:  # 4 hours
            recommendations.append("Review progress and update objectives")
        
        return recommendations
    
    async def _find_related_sessions(self, org_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Find related past sessions."""
        if not self.current_session:
            return []
        
        # Search for sessions with similar tasks
        related = await search_memory(
            org_id,
            f"session: {self.current_session.current_task}",
            limit=limit
        )
        
        return [
            {
                "session_id": hit.get("payload", {}).get("metadata", {}).get("session_id"),
                "relevance": hit.get("score", 0.0),
                "content": hit.get("payload", {}).get("text", "")[:200]
            }
            for hit in related
            if hit.get("payload", {}).get("metadata", {}).get("session_id") != self.current_session.session_id
        ]
    
    async def _generate_session_achievements(self) -> List[str]:
        """Generate achievements/accomplishments for session."""
        if not self.current_session:
            return []
        
        achievements = []
        
        # Files modified
        if self.current_session.files_modified:
            achievements.append(f"Modified {len(self.current_session.files_modified)} files")
        
        # Errors resolved
        resolved_count = len([e for e in self.current_session.error_patterns if e.get("resolved", False)])
        if resolved_count > 0:
            achievements.append(f"Resolved {resolved_count} errors")
        
        # Session duration
        duration = self._calculate_session_duration()
        if duration > 120:
            achievements.append(f"Sustained {duration // 60}+ hour development session")
        
        # Task completion indicators
        task_lower = self.current_session.current_task.lower()
        if "implement" in task_lower and self.current_session.files_modified:
            achievements.append("Implementation progress made")
        elif "fix" in task_lower and resolved_count > 0:
            achievements.append("Bug fixes completed")
        elif "refactor" in task_lower and self.current_session.files_modified:
            achievements.append("Code refactoring performed")
        
        return achievements
    
    async def _load_or_create_session(self):
        """Load existing session or create a new one."""
        try:
            if self.session_file.exists():
                async with aiofiles.open(self.session_file, 'r') as f:
                    content = await f.read()
                    if content.strip():
                        data = json.loads(content)
                        self.current_session = SessionContext(**data)
                        return
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
        
        # Create new session if loading failed
        await self.start_session("Default development session", "General development work")
    
    async def _save_session(self):
        """Save current session to disk."""
        if not self.current_session:
            return
        
        try:
            async with aiofiles.open(self.session_file, 'w') as f:
                await f.write(json.dumps(asdict(self.current_session), indent=2))
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def _archive_session(self):
        """Archive current session to history."""
        if not self.current_session:
            return
        
        try:
            # Create archive file
            archive_file = self.sessions_dir / f"{self.current_session.session_id}.json"
            
            # Add end timestamp
            session_data = asdict(self.current_session)
            session_data["ended_at"] = datetime.utcnow().isoformat()
            
            async with aiofiles.open(archive_file, 'w') as f:
                await f.write(json.dumps(session_data, indent=2))
            
            # Remove current session file
            if self.session_file.exists():
                self.session_file.unlink()
            
            logger.info(f"Archived session {self.current_session.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to archive session: {e}")
    
    async def _load_archived_sessions(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Load archived sessions newer than cutoff date."""
        sessions = []
        
        for archive_file in self.sessions_dir.glob("*.json"):
            if archive_file.name == "current.json":
                continue
                
            try:
                async with aiofiles.open(archive_file, 'r') as f:
                    content = await f.read()
                    if content.strip():
                        session_data = json.loads(content)
                        
                        # Check if session is newer than cutoff
                        started_at = datetime.fromisoformat(session_data.get("started_at", ""))
                        if started_at > cutoff_date:
                            sessions.append(session_data)
                            
            except Exception as e:
                logger.error(f"Failed to load archived session {archive_file}: {e}")
        
        return sessions
    
    async def _store_session_event(self, event_type: str, event_data: Dict[str, Any], org_id: str):
        """Store session event in vector memory."""
        try:
            session_id = self.current_session.session_id if self.current_session else "unknown"
            event_text = f"Session event: {event_type} | Session: {session_id} | Data: {json.dumps(event_data)}"
            
            await store_memory(
                org_id=org_id,
                user_id="session_manager",
                text=event_text,
                metadata={
                    "type": f"session_{event_type}",
                    "session_id": session_id,
                    "event_data": event_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to store session event: {e}")


@click.command()
@click.option('--start', help='Start new session with task description')
@click.option('--update', help='Update current session task')
@click.option('--objective', help='Session objective (used with --start or --update)')
@click.option('--priority', type=int, help='Priority 1-10 (used with --start or --update)')
@click.option('--file-activity', help='Track file activity: path:type (e.g., "src/app.py:modified")')
@click.option('--track-error', help='Track error: "error_message|error_type|stack_trace"')
@click.option('--resolve-error', type=int, help='Resolve error by index with --solution')
@click.option('--solution', help='Solution description (used with --resolve-error)')
@click.option('--current', is_flag=True, help='Show current session context')
@click.option('--end', help='End session with summary')
@click.option('--handoff', help='Handoff session to agent with notes')
@click.option('--search', help='Search session history')
@click.option('--stats', is_flag=True, help='Show session statistics')
@click.option('--days', type=int, default=30, help='Days for statistics (default: 30)')
@click.option('--org-id', default="1", help='Organization ID')
def main(start, update, objective, priority, file_activity, track_error, resolve_error, 
         solution, current, end, handoff, search, stats, days, org_id):
    """War Room Session Manager - Development context tracking"""
    
    async def run():
        manager = SessionManager()
        
        if start:
            session = await manager.start_session(start, objective or "", priority or 5, org_id)
            click.echo(f"Started session: {session.session_id}")
            click.echo(f"Task: {session.current_task}")
            
        elif update:
            session = await manager.update_session(update, objective, priority, org_id)
            if session:
                click.echo(f"Updated session: {session.session_id}")
                click.echo(f"Task: {session.current_task}")
            else:
                click.echo("No active session to update")
                
        elif file_activity:
            try:
                file_path, activity_type = file_activity.split(":", 1)
                await manager.track_file_activity(file_path, activity_type, org_id)
                click.echo(f"Tracked {activity_type}: {file_path}")
            except ValueError:
                click.echo("File activity format: path:type (e.g., 'src/app.py:modified')")
                
        elif track_error:
            try:
                parts = track_error.split("|", 2)
                error_message = parts[0]
                error_type = parts[1] if len(parts) > 1 else "unknown"
                stack_trace = parts[2] if len(parts) > 2 else None
                
                await manager.track_error(error_message, error_type, stack_trace, org_id)
                click.echo(f"Tracked error: {error_type}")
            except Exception as e:
                click.echo(f"Error format: 'message|type|stack_trace' - {e}")
                
        elif resolve_error is not None:
            if not solution:
                click.echo("--solution required with --resolve-error")
            else:
                await manager.track_resolution(resolve_error, solution, org_id)
                click.echo(f"Resolved error {resolve_error}")
                
        elif current:
            context = await manager.get_session_context(org_id)
            click.echo(json.dumps(context, indent=2))
            
        elif end:
            summary = await manager.end_session(end, org_id)
            click.echo(json.dumps(summary, indent=2))
            
        elif handoff:
            to_agent = click.prompt("Handoff to agent")
            handoff_data = await manager.handoff_session(to_agent, handoff, org_id)
            click.echo(json.dumps(handoff_data, indent=2))
            
        elif search:
            results = await manager.search_session_history(search, org_id=org_id)
            for result in results:
                click.echo(f"[{result['type']}] {result['content'][:100]}...")
                
        elif stats:
            statistics = await manager.get_session_statistics(days)
            click.echo(json.dumps(statistics, indent=2))
            
        else:
            click.echo("Specify an action: --start, --update, --current, --end, --search, --stats, etc.")
    
    asyncio.run(run())


if __name__ == "__main__":
    main()