"""
Session State Tracking for War Room Development

Tracks current task, modified files, errors, and resolutions across development sessions.
Integrates with git workflow for branch-specific context preservation.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import hashlib


class SessionTracker:
    """Track development session state and context."""
    
    def __init__(self, project_root: str = "/home/eddy/Development/warroom"):
        self.project_root = Path(project_root)
        self.context_dir = self.project_root / ".context"
        self.session_dir = self.context_dir / "session"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session_file = self.session_dir / "current.json"
        self.sessions_history_file = self.session_dir / "history.json"
        
        self.current_session = self._load_current_session()
        
    def _load_current_session(self) -> Dict[str, Any]:
        """Load current session state or create new one."""
        if self.current_session_file.exists():
            with open(self.current_session_file, 'r') as f:
                session = json.load(f)
                # Resume session if recent (within 8 hours)
                start_time = datetime.fromisoformat(session.get('start_time', ''))
                if datetime.now() - start_time < timedelta(hours=8):
                    return session
        
        # Create new session
        return self._create_new_session()
    
    def _create_new_session(self) -> Dict[str, Any]:
        """Create a new development session."""
        session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        git_branch = self._get_current_branch()
        
        session = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'git_branch': git_branch,
            'current_task': None,
            'modified_files': [],
            'errors_encountered': [],
            'resolutions': [],
            'context_loaded': [],
            'working_directory': str(Path.cwd()),
            'last_activity': datetime.now().isoformat()
        }
        
        self._save_current_session(session)
        return session
    
    def _get_current_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'], 
                cwd=self.project_root,
                capture_output=True, 
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def _save_current_session(self, session: Dict[str, Any]):
        """Save current session state."""
        session['last_activity'] = datetime.now().isoformat()
        with open(self.current_session_file, 'w') as f:
            json.dump(session, f, indent=2)
    
    def start_session(self, task_description: str = None):
        """Start a new development session with optional task description."""
        self.current_session = self._create_new_session()
        if task_description:
            self.current_session['current_task'] = task_description
        self._save_current_session(self.current_session)
        print(f"🚀 Started session {self.current_session['session_id']}: {task_description}")
    
    def set_task(self, task_description: str):
        """Set current task description."""
        self.current_session['current_task'] = task_description
        self._save_current_session(self.current_session)
        print(f"📋 Task set: {task_description}")
    
    def track_file_change(self, file_path: str, change_type: str = "modified"):
        """Track a file modification."""
        file_entry = {
            'path': file_path,
            'change_type': change_type,
            'timestamp': datetime.now().isoformat(),
            'relative_path': str(Path(file_path).relative_to(self.project_root)) if Path(file_path).is_absolute() else file_path
        }
        
        # Avoid duplicates - update if same file modified recently
        existing_idx = None
        for i, existing in enumerate(self.current_session['modified_files']):
            if existing['relative_path'] == file_entry['relative_path']:
                # If modified within last 5 minutes, update existing entry
                existing_time = datetime.fromisoformat(existing['timestamp'])
                if datetime.now() - existing_time < timedelta(minutes=5):
                    existing_idx = i
                    break
        
        if existing_idx is not None:
            self.current_session['modified_files'][existing_idx] = file_entry
        else:
            self.current_session['modified_files'].append(file_entry)
            
        # Keep only last 50 file changes to avoid bloat
        self.current_session['modified_files'] = self.current_session['modified_files'][-50:]
        
        self._save_current_session(self.current_session)
    
    def track_error(self, error_message: str, file_path: str = None, line_number: int = None):
        """Track an error encountered during development."""
        error_entry = {
            'message': error_message,
            'file_path': file_path,
            'line_number': line_number,
            'timestamp': datetime.now().isoformat(),
            'resolved': False
        }
        
        self.current_session['errors_encountered'].append(error_entry)
        self._save_current_session(self.current_session)
        print(f"❌ Error tracked: {error_message[:100]}...")
    
    def track_resolution(self, resolution_description: str, related_error_idx: int = None):
        """Track resolution of an issue."""
        resolution_entry = {
            'description': resolution_description,
            'related_error_idx': related_error_idx,
            'timestamp': datetime.now().isoformat()
        }
        
        # Mark related error as resolved
        if related_error_idx is not None and related_error_idx < len(self.current_session['errors_encountered']):
            self.current_session['errors_encountered'][related_error_idx]['resolved'] = True
        
        self.current_session['resolutions'].append(resolution_entry)
        self._save_current_session(self.current_session)
        print(f"✅ Resolution tracked: {resolution_description}")
    
    def track_context_loaded(self, context_type: str, context_source: str):
        """Track context that was loaded during session."""
        context_entry = {
            'type': context_type,
            'source': context_source,
            'timestamp': datetime.now().isoformat()
        }
        
        self.current_session['context_loaded'].append(context_entry)
        self._save_current_session(self.current_session)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        session = self.current_session
        duration = datetime.now() - datetime.fromisoformat(session['start_time'])
        
        return {
            'session_id': session['session_id'],
            'duration_hours': duration.total_seconds() / 3600,
            'git_branch': session['git_branch'],
            'current_task': session['current_task'],
            'files_modified_count': len(session['modified_files']),
            'recent_files': [f['relative_path'] for f in session['modified_files'][-10:]],
            'errors_count': len(session['errors_encountered']),
            'unresolved_errors': [e for e in session['errors_encountered'] if not e['resolved']],
            'resolutions_count': len(session['resolutions']),
            'context_loaded_count': len(session['context_loaded'])
        }
    
    def end_session(self):
        """End current session and archive to history."""
        if not self.current_session:
            return
        
        # Load existing history
        history = []
        if self.sessions_history_file.exists():
            with open(self.sessions_history_file, 'r') as f:
                history = json.load(f)
        
        # Archive current session
        end_time = datetime.now()
        archived_session = dict(self.current_session)
        archived_session['end_time'] = end_time.isoformat()
        archived_session['duration_seconds'] = (
            end_time - datetime.fromisoformat(archived_session['start_time'])
        ).total_seconds()
        
        history.append(archived_session)
        
        # Keep only last 100 sessions
        history = history[-100:]
        
        with open(self.sessions_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Clear current session
        if self.current_session_file.exists():
            self.current_session_file.unlink()
        
        print(f"📚 Session {archived_session['session_id']} archived to history")
        
        self.current_session = None
    
    def get_recent_files(self, limit: int = 10) -> List[str]:
        """Get recently modified files in current session."""
        if not self.current_session:
            return []
            
        return [f['relative_path'] for f in self.current_session['modified_files'][-limit:]]
    
    def get_unresolved_errors(self) -> List[Dict[str, Any]]:
        """Get unresolved errors from current session."""
        if not self.current_session:
            return []
            
        return [e for e in self.current_session['errors_encountered'] if not e['resolved']]


if __name__ == "__main__":
    # CLI interface for session tracking
    import sys
    
    tracker = SessionTracker()
    
    if len(sys.argv) < 2:
        print("Usage: python session_tracker.py [start|status|end] [task_description]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "start":
        task = sys.argv[2] if len(sys.argv) > 2 else None
        tracker.start_session(task)
    elif command == "status":
        summary = tracker.get_session_summary()
        print(f"Session: {summary['session_id']} ({summary['duration_hours']:.1f}h)")
        print(f"Task: {summary['current_task'] or 'None'}")
        print(f"Branch: {summary['git_branch']}")
        print(f"Files modified: {summary['files_modified_count']}")
        print(f"Errors: {summary['errors_count']} ({len(summary['unresolved_errors'])} unresolved)")
    elif command == "end":
        tracker.end_session()
    else:
        print(f"Unknown command: {command}")