"""
Context Loading Trigger Engine

Orchestrates intelligent context loading based on development patterns.
Combines pattern matching with context selection algorithms.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from autoload.pattern_matcher import PatternMatcher, ContextPattern
from session.session_tracker import SessionTracker


@dataclass
class ContextSuggestion:
    """Represents a suggested context to load."""
    file_path: str
    relevance_score: float
    trigger_reason: str
    pattern_match: Optional[ContextPattern] = None


class TriggerEngine:
    """Intelligent context loading trigger system."""
    
    def __init__(self, project_root: str = "/home/eddy/Development/warroom"):
        self.project_root = Path(project_root)
        self.context_dir = self.project_root / ".context"
        self.autoload_dir = self.context_dir / "autoload"
        self.autoload_dir.mkdir(parents=True, exist_ok=True)
        
        self.pattern_matcher = PatternMatcher(project_root)
        self.session_tracker = SessionTracker(project_root)
        
        # Cache for loaded contexts to avoid re-loading
        self.loaded_contexts_cache = set()
        self.cache_expiry = 300  # 5 minutes
        self.last_cache_clear = time.time()
        
    def _clear_expired_cache(self):
        """Clear cache if expired."""
        current_time = time.time()
        if current_time - self.last_cache_clear > self.cache_expiry:
            self.loaded_contexts_cache.clear()
            self.last_cache_clear = current_time
    
    def trigger_from_error(self, error_message: str, file_path: str = None) -> List[ContextSuggestion]:
        """Trigger context loading from an error message."""
        self._clear_expired_cache()
        
        suggestions = []
        
        # Match error patterns
        error_matches = self.pattern_matcher.match_error(error_message)
        
        for match in error_matches:
            for context_file in match.context_files:
                # Calculate relevance score based on pattern priority and recency
                relevance_score = match.priority / 10.0
                
                # Boost score if error happened in recently modified file
                if file_path and self._is_recently_modified(file_path):
                    relevance_score += 0.3
                
                # Reduce score if context was recently loaded
                cache_key = f"error:{context_file}"
                if cache_key in self.loaded_contexts_cache:
                    relevance_score *= 0.5
                
                suggestions.append(ContextSuggestion(
                    file_path=context_file,
                    relevance_score=relevance_score,
                    trigger_reason=f"Error pattern match: {match.description}",
                    pattern_match=match
                ))
                
                self.loaded_contexts_cache.add(cache_key)
        
        # Track error for session context
        if error_message:
            self.session_tracker.track_error(error_message, file_path)
        
        return self._rank_suggestions(suggestions)
    
    def trigger_from_file(self, file_path: str) -> List[ContextSuggestion]:
        """Trigger context loading from file modification."""
        self._clear_expired_cache()
        
        suggestions = []
        
        # Convert to relative path for pattern matching
        try:
            rel_path = str(Path(file_path).relative_to(self.project_root))
        except ValueError:
            rel_path = file_path
        
        # Match file path patterns
        path_matches = self.pattern_matcher.match_file_path(rel_path)
        
        for match in path_matches:
            for context_file in match.context_files:
                relevance_score = match.priority / 10.0
                
                cache_key = f"file:{context_file}"
                if cache_key in self.loaded_contexts_cache:
                    relevance_score *= 0.7
                
                suggestions.append(ContextSuggestion(
                    file_path=context_file,
                    relevance_score=relevance_score,
                    trigger_reason=f"File path match: {match.description}",
                    pattern_match=match
                ))
                
                self.loaded_contexts_cache.add(cache_key)
        
        # Analyze file imports for additional context
        import_matches = self.pattern_matcher.analyze_file_imports(file_path)
        
        for match in import_matches:
            for context_file in match.context_files:
                relevance_score = (match.priority / 10.0) * 0.8  # Slightly lower for import matches
                
                cache_key = f"import:{context_file}"
                if cache_key in self.loaded_contexts_cache:
                    relevance_score *= 0.6
                
                suggestions.append(ContextSuggestion(
                    file_path=context_file,
                    relevance_score=relevance_score,
                    trigger_reason=f"Import pattern match: {match.description}",
                    pattern_match=match
                ))
                
                self.loaded_contexts_cache.add(cache_key)
        
        # Track file modification
        self.session_tracker.track_file_change(file_path)
        
        return self._rank_suggestions(suggestions)
    
    def trigger_from_task(self, task_description: str) -> List[ContextSuggestion]:
        """Trigger context loading from task description."""
        self._clear_expired_cache()
        
        suggestions = []
        
        # Match keywords in task description
        keyword_matches = self.pattern_matcher.match_keywords(task_description)
        
        for match in keyword_matches:
            for context_file in match.context_files:
                relevance_score = (match.priority / 10.0) * 0.9  # High relevance for explicit tasks
                
                cache_key = f"task:{context_file}"
                if cache_key in self.loaded_contexts_cache:
                    relevance_score *= 0.8
                
                suggestions.append(ContextSuggestion(
                    file_path=context_file,
                    relevance_score=relevance_score,
                    trigger_reason=f"Task keyword match: {match.description}",
                    pattern_match=match
                ))
                
                self.loaded_contexts_cache.add(cache_key)
        
        # Set task in session tracker
        self.session_tracker.set_task(task_description)
        
        return self._rank_suggestions(suggestions)
    
    def trigger_from_session_context(self) -> List[ContextSuggestion]:
        """Trigger context loading based on current session state."""
        self._clear_expired_cache()
        
        suggestions = []
        
        # Get session summary
        session_summary = self.session_tracker.get_session_summary()
        
        # Context from recent files
        for file_path in session_summary['recent_files']:
            file_suggestions = self.trigger_from_file(
                str(self.project_root / file_path)
            )
            
            # Boost relevance for session context
            for suggestion in file_suggestions:
                suggestion.relevance_score *= 1.2
                suggestion.trigger_reason += " (from session context)"
            
            suggestions.extend(file_suggestions)
        
        # Context from unresolved errors
        for error in session_summary['unresolved_errors']:
            error_suggestions = self.trigger_from_error(
                error['message'],
                error.get('file_path')
            )
            
            # Boost relevance for unresolved errors
            for suggestion in error_suggestions:
                suggestion.relevance_score *= 1.4
                suggestion.trigger_reason += " (unresolved error)"
            
            suggestions.extend(error_suggestions)
        
        # Context from current task
        if session_summary['current_task']:
            task_suggestions = self.trigger_from_task(session_summary['current_task'])
            suggestions.extend(task_suggestions)
        
        return self._rank_suggestions(suggestions)
    
    def _is_recently_modified(self, file_path: str) -> bool:
        """Check if file was recently modified in current session."""
        recent_files = self.session_tracker.get_recent_files(20)
        
        try:
            rel_path = str(Path(file_path).relative_to(self.project_root))
        except ValueError:
            rel_path = file_path
        
        return rel_path in recent_files
    
    def _rank_suggestions(self, suggestions: List[ContextSuggestion]) -> List[ContextSuggestion]:
        """Rank and deduplicate context suggestions."""
        # Deduplicate by file path, keeping highest relevance
        unique_suggestions = {}
        
        for suggestion in suggestions:
            if suggestion.file_path not in unique_suggestions:
                unique_suggestions[suggestion.file_path] = suggestion
            elif suggestion.relevance_score > unique_suggestions[suggestion.file_path].relevance_score:
                unique_suggestions[suggestion.file_path] = suggestion
        
        # Sort by relevance score (highest first)
        ranked = sorted(unique_suggestions.values(), 
                       key=lambda s: s.relevance_score, reverse=True)
        
        return ranked
    
    def get_context_recommendations(self, text: str = None, file_path: str = None, 
                                  max_suggestions: int = 5) -> List[ContextSuggestion]:
        """Get comprehensive context recommendations."""
        all_suggestions = []
        
        # Session-based context
        session_suggestions = self.trigger_from_session_context()
        all_suggestions.extend(session_suggestions)
        
        # Text-based context (error, task, or general)
        if text:
            # Try as error first
            error_suggestions = self.trigger_from_error(text, file_path)
            if error_suggestions:
                all_suggestions.extend(error_suggestions)
            else:
                # Try as task/keywords
                task_suggestions = self.trigger_from_task(text)
                all_suggestions.extend(task_suggestions)
        
        # File-based context
        if file_path:
            file_suggestions = self.trigger_from_file(file_path)
            all_suggestions.extend(file_suggestions)
        
        # Rank all suggestions
        ranked = self._rank_suggestions(all_suggestions)
        
        return ranked[:max_suggestions]
    
    def auto_load_context(self, trigger_text: str = None, file_path: str = None) -> Dict[str, Any]:
        """Automatically load relevant context and return summary."""
        start_time = time.time()
        
        recommendations = self.get_context_recommendations(trigger_text, file_path)
        
        loaded_contexts = []
        
        for suggestion in recommendations:
            # Check if context file exists
            context_file_path = self.context_dir / suggestion.file_path
            
            if context_file_path.exists():
                try:
                    with open(context_file_path, 'r') as f:
                        content = f.read()
                    
                    loaded_contexts.append({
                        'file': suggestion.file_path,
                        'relevance_score': suggestion.relevance_score,
                        'reason': suggestion.trigger_reason,
                        'content_preview': content[:200] + "..." if len(content) > 200 else content,
                        'content_length': len(content)
                    })
                    
                    # Track context loading
                    self.session_tracker.track_context_loaded(
                        context_type="auto_load",
                        context_source=suggestion.file_path
                    )
                    
                except Exception as e:
                    print(f"Warning: Failed to load context file {suggestion.file_path}: {e}")
            else:
                print(f"Warning: Context file not found: {suggestion.file_path}")
        
        load_time = time.time() - start_time
        
        return {
            'loaded_contexts': loaded_contexts,
            'total_contexts': len(loaded_contexts),
            'load_time_ms': round(load_time * 1000, 2),
            'trigger_text': trigger_text,
            'trigger_file': file_path,
            'recommendations_considered': len(recommendations)
        }


if __name__ == "__main__":
    # CLI interface for trigger engine
    import sys
    
    engine = TriggerEngine()
    
    if len(sys.argv) < 2:
        print("Usage: python trigger_engine.py [error|file|task|session|auto] 'text or path'")
        print("Examples:")
        print("  python trigger_engine.py error 'JWT token expired'")
        print("  python trigger_engine.py file 'backend/app/auth/jwt.py'")
        print("  python trigger_engine.py task 'fix authentication bug'")
        print("  python trigger_engine.py session")
        print("  python trigger_engine.py auto 'TokenExpiredError' --file 'backend/app/auth/jwt.py'")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "error":
        text = sys.argv[2] if len(sys.argv) > 2 else ""
        suggestions = engine.trigger_from_error(text)
    elif command == "file":
        file_path = sys.argv[2] if len(sys.argv) > 2 else ""
        suggestions = engine.trigger_from_file(file_path)
    elif command == "task":
        task = sys.argv[2] if len(sys.argv) > 2 else ""
        suggestions = engine.trigger_from_task(task)
    elif command == "session":
        suggestions = engine.trigger_from_session_context()
    elif command == "auto":
        text = sys.argv[2] if len(sys.argv) > 2 else None
        file_path = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--file" else None
        result = engine.auto_load_context(text, file_path)
        
        print(f"Auto-loaded {result['total_contexts']} contexts in {result['load_time_ms']}ms:")
        for context in result['loaded_contexts']:
            print(f"\n📄 {context['file']} (score: {context['relevance_score']:.2f})")
            print(f"   Reason: {context['reason']}")
            print(f"   Preview: {context['content_preview']}")
        sys.exit(0)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    print(f"Context suggestions for '{sys.argv[2] if len(sys.argv) > 2 else command}':")
    for suggestion in suggestions:
        print(f"\n📄 {suggestion.file_path} (score: {suggestion.relevance_score:.2f})")
        print(f"   Reason: {suggestion.trigger_reason}")
        if suggestion.pattern_match:
            print(f"   Pattern: {suggestion.pattern_match.pattern}")