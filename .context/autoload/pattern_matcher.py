"""
Pattern Matching for Auto-Loading Context

Matches error messages, file paths, and import statements to relevant context.
Implements intelligent pattern recognition for context triggers.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class ContextPattern:
    """Represents a pattern that can trigger context loading."""
    pattern: str
    pattern_type: str  # 'error', 'import', 'filepath', 'keyword'
    context_files: List[str]
    priority: int
    description: str


class PatternMatcher:
    """Match development patterns to relevant context files."""
    
    def __init__(self, project_root: str = "/home/eddy/Development/warroom"):
        self.project_root = Path(project_root)
        self.context_dir = self.project_root / ".context"
        self.patterns_file = self.context_dir / "autoload" / "patterns.json"
        
        # Ensure directory exists
        self.patterns_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> List[ContextPattern]:
        """Load context patterns from configuration."""
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r') as f:
                pattern_data = json.load(f)
                return [ContextPattern(**p) for p in pattern_data]
        
        # Create default patterns for War Room
        return self._create_default_patterns()
    
    def _create_default_patterns(self) -> List[ContextPattern]:
        """Create default patterns for War Room context loading."""
        patterns = [
            # JWT/Auth errors
            ContextPattern(
                pattern=r"(JWT|token|auth|unauthorized|403|401)",
                pattern_type="error",
                context_files=["authentication.md", "jwt-implementation.md", "api-auth.md"],
                priority=10,
                description="Authentication and JWT-related errors"
            ),
            
            # Database/PostgreSQL errors
            ContextPattern(
                pattern=r"(postgres|database|connection|relation.*does not exist|psycopg)",
                pattern_type="error", 
                context_files=["database-schema.md", "postgres-setup.md", "migration-patterns.md"],
                priority=9,
                description="Database and PostgreSQL errors"
            ),
            
            # Next.js/React errors
            ContextPattern(
                pattern=r"(next|react|hydration|client.*server|SSR|getServerSideProps)",
                pattern_type="error",
                context_files=["nextjs-patterns.md", "ssr-hydration.md", "frontend-architecture.md"],
                priority=8,
                description="Next.js and React-related errors"
            ),
            
            # FastAPI/Backend errors
            ContextPattern(
                pattern=r"(fastapi|pydantic|uvicorn|422.*validation|internal server error)",
                pattern_type="error",
                context_files=["fastapi-patterns.md", "backend-architecture.md", "api-endpoints.md"],
                priority=8,
                description="FastAPI and backend errors"
            ),
            
            # Docker/Container errors
            ContextPattern(
                pattern=r"(docker|container|port.*already in use|failed to build)",
                pattern_type="error",
                context_files=["docker-setup.md", "container-architecture.md", "development-workflow.md"],
                priority=7,
                description="Docker and containerization errors"
            ),
            
            # File path patterns - Backend
            ContextPattern(
                pattern=r"backend/(app|models|services|auth)",
                pattern_type="filepath",
                context_files=["backend-architecture.md", "api-endpoints.md", "database-schema.md"],
                priority=6,
                description="Backend code modifications"
            ),
            
            # File path patterns - Frontend
            ContextPattern(
                pattern=r"frontend/(src|components|pages|lib)",
                pattern_type="filepath", 
                context_files=["frontend-architecture.md", "component-patterns.md", "nextjs-patterns.md"],
                priority=6,
                description="Frontend code modifications"
            ),
            
            # Import patterns - Auth
            ContextPattern(
                pattern=r"from.*auth.*import|import.*jwt|from.*middleware",
                pattern_type="import",
                context_files=["authentication.md", "middleware-patterns.md"],
                priority=5,
                description="Authentication and middleware imports"
            ),
            
            # Import patterns - Database
            ContextPattern(
                pattern=r"from.*models.*import|from.*database.*import|import.*sqlalchemy",
                pattern_type="import",
                context_files=["database-schema.md", "orm-patterns.md"],
                priority=5,
                description="Database and ORM imports"
            ),
            
            # Keywords - CRM specific
            ContextPattern(
                pattern=r"(contact|deal|lead|pipeline|crm|sales)",
                pattern_type="keyword",
                context_files=["crm-architecture.md", "sales-pipeline.md", "contact-management.md"],
                priority=4,
                description="CRM-related functionality"
            ),
            
            # Keywords - Content/Social
            ContextPattern(
                pattern=r"(social|content|instagram|tiktok|youtube|post|campaign)",
                pattern_type="keyword",
                context_files=["social-integrations.md", "content-pipeline.md", "social-auth.md"],
                priority=4,
                description="Social media and content features"
            ),
            
            # Keywords - AI/Intelligence
            ContextPattern(
                pattern=r"(ai|intelligence|competitor|agent|openai|anthropic)",
                pattern_type="keyword",
                context_files=["ai-integrations.md", "competitor-intel.md", "agent-patterns.md"],
                priority=4,
                description="AI and intelligence features"
            )
        ]
        
        # Save default patterns
        self._save_patterns(patterns)
        return patterns
    
    def _save_patterns(self, patterns: List[ContextPattern]):
        """Save patterns to configuration file."""
        pattern_data = [
            {
                'pattern': p.pattern,
                'pattern_type': p.pattern_type,
                'context_files': p.context_files,
                'priority': p.priority,
                'description': p.description
            }
            for p in patterns
        ]
        
        with open(self.patterns_file, 'w') as f:
            json.dump(pattern_data, f, indent=2)
    
    def match_error(self, error_message: str) -> List[ContextPattern]:
        """Match error message to context patterns."""
        matches = []
        
        for pattern in self.patterns:
            if pattern.pattern_type == 'error':
                if re.search(pattern.pattern, error_message, re.IGNORECASE):
                    matches.append(pattern)
        
        # Sort by priority (higher first)
        return sorted(matches, key=lambda p: p.priority, reverse=True)
    
    def match_file_path(self, file_path: str) -> List[ContextPattern]:
        """Match file path to context patterns."""
        matches = []
        
        for pattern in self.patterns:
            if pattern.pattern_type == 'filepath':
                if re.search(pattern.pattern, file_path, re.IGNORECASE):
                    matches.append(pattern)
        
        return sorted(matches, key=lambda p: p.priority, reverse=True)
    
    def match_import_statement(self, import_line: str) -> List[ContextPattern]:
        """Match import statement to context patterns."""
        matches = []
        
        for pattern in self.patterns:
            if pattern.pattern_type == 'import':
                if re.search(pattern.pattern, import_line, re.IGNORECASE):
                    matches.append(pattern)
        
        return sorted(matches, key=lambda p: p.priority, reverse=True)
    
    def match_keywords(self, text: str) -> List[ContextPattern]:
        """Match text content to keyword patterns."""
        matches = []
        
        for pattern in self.patterns:
            if pattern.pattern_type == 'keyword':
                if re.search(pattern.pattern, text, re.IGNORECASE):
                    matches.append(pattern)
        
        return sorted(matches, key=lambda p: p.priority, reverse=True)
    
    def match_any(self, text: str, context_type: str = None) -> List[ContextPattern]:
        """Match text against all relevant patterns."""
        all_matches = []
        
        if context_type is None or context_type == 'error':
            all_matches.extend(self.match_error(text))
        
        if context_type is None or context_type == 'filepath':
            all_matches.extend(self.match_file_path(text))
        
        if context_type is None or context_type == 'import':
            all_matches.extend(self.match_import_statement(text))
        
        if context_type is None or context_type == 'keyword':
            all_matches.extend(self.match_keywords(text))
        
        # Remove duplicates and sort by priority
        unique_matches = []
        seen = set()
        
        for match in sorted(all_matches, key=lambda p: p.priority, reverse=True):
            match_key = f"{match.pattern}:{match.pattern_type}"
            if match_key not in seen:
                seen.add(match_key)
                unique_matches.append(match)
        
        return unique_matches
    
    def add_pattern(self, pattern: str, pattern_type: str, context_files: List[str], 
                   priority: int, description: str):
        """Add a new context pattern."""
        new_pattern = ContextPattern(
            pattern=pattern,
            pattern_type=pattern_type,
            context_files=context_files,
            priority=priority,
            description=description
        )
        
        self.patterns.append(new_pattern)
        self._save_patterns(self.patterns)
    
    def remove_pattern(self, pattern: str, pattern_type: str):
        """Remove a context pattern."""
        self.patterns = [
            p for p in self.patterns 
            if not (p.pattern == pattern and p.pattern_type == pattern_type)
        ]
        self._save_patterns(self.patterns)
    
    def get_suggested_context(self, text: str, limit: int = 5) -> List[str]:
        """Get suggested context files based on text analysis."""
        matches = self.match_any(text)
        
        # Collect all context files from matches
        context_files = []
        seen = set()
        
        for match in matches[:limit]:
            for context_file in match.context_files:
                if context_file not in seen:
                    seen.add(context_file)
                    context_files.append(context_file)
        
        return context_files
    
    def analyze_file_imports(self, file_path: str) -> List[ContextPattern]:
        """Analyze a file's imports to suggest relevant context."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract import lines
            import_lines = []
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ')):
                    import_lines.append(stripped)
            
            # Match all imports
            all_matches = []
            for import_line in import_lines:
                matches = self.match_import_statement(import_line)
                all_matches.extend(matches)
            
            # Remove duplicates
            unique_matches = []
            seen = set()
            for match in all_matches:
                match_key = f"{match.pattern}:{match.pattern_type}"
                if match_key not in seen:
                    seen.add(match_key)
                    unique_matches.append(match)
            
            return sorted(unique_matches, key=lambda p: p.priority, reverse=True)
        
        except Exception as e:
            return []


if __name__ == "__main__":
    # CLI interface for pattern matching
    import sys
    
    matcher = PatternMatcher()
    
    if len(sys.argv) < 3:
        print("Usage: python pattern_matcher.py [error|filepath|import|keyword] 'text to match'")
        sys.exit(1)
    
    pattern_type = sys.argv[1]
    text = sys.argv[2]
    
    if pattern_type == "error":
        matches = matcher.match_error(text)
    elif pattern_type == "filepath":
        matches = matcher.match_file_path(text)
    elif pattern_type == "import":
        matches = matcher.match_import_statement(text)
    elif pattern_type == "keyword":
        matches = matcher.match_keywords(text)
    else:
        matches = matcher.match_any(text)
    
    print(f"Matches for '{text}':")
    for match in matches:
        print(f"  {match.description} (priority: {match.priority})")
        print(f"    Files: {', '.join(match.context_files)}")
        print()