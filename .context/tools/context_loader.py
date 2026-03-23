#!/usr/bin/env python3
"""
Context Loader - Dynamic context retrieval for War Room development

Loads relevant context based on:
- Error messages and stack traces
- File paths and imports
- Natural language queries
- Current development session

Integrates with OpenClaw skills system and War Room vector memory.
"""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import click
import yaml
import aiofiles

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.services.vector_memory import search_memory, store_memory

logger = logging.getLogger(__name__)

class ContextLoader:
    """Dynamic context loading and retrieval system."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.context_dir = self.project_root / ".context"
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load context configuration from YAML."""
        config_path = self.context_dir / "context.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    async def query_context(self, query: str, org_id: str = "1") -> Dict[str, Any]:
        """Query context using natural language."""
        results = {
            "query": query,
            "context_sources": [],
            "relevant_files": [],
            "patterns": [],
            "suggestions": []
        }
        
        # 1. Search static context files
        static_context = await self._search_static_context(query)
        if static_context:
            results["context_sources"].extend(static_context)
        
        # 2. Search vector memory (if available)
        try:
            memory_results = await search_memory(org_id, query, limit=5, score_threshold=0.7)
            if memory_results:
                results["context_sources"].append({
                    "type": "vector_memory",
                    "results": memory_results,
                    "count": len(memory_results)
                })
        except Exception as e:
            logger.warning(f"Vector memory search failed: {e}")
        
        # 3. Search codebase semantically
        semantic_results = await self._search_codebase(query)
        if semantic_results:
            results["relevant_files"].extend(semantic_results)
        
        # 4. Pattern matching
        patterns = await self._match_patterns(query)
        if patterns:
            results["patterns"].extend(patterns)
        
        # 5. Generate suggestions
        suggestions = await self._generate_suggestions(query, results)
        results["suggestions"] = suggestions
        
        return results
    
    async def load_error_context(self, error_message: str, stack_trace: str = None) -> Dict[str, Any]:
        """Load context for debugging an error."""
        context = {
            "error_type": self._classify_error(error_message),
            "relevant_context": [],
            "similar_errors": [],
            "suggested_fixes": []
        }
        
        # Extract file paths from stack trace
        if stack_trace:
            file_paths = self._extract_file_paths(stack_trace)
            for file_path in file_paths:
                file_context = await self._get_file_context(file_path)
                if file_context:
                    context["relevant_context"].append(file_context)
        
        # Search for similar errors in memory
        try:
            similar_errors = await search_memory("1", f"error: {error_message}", limit=3)
            context["similar_errors"] = similar_errors
        except Exception as e:
            logger.warning(f"Error memory search failed: {e}")
        
        # Generate fix suggestions based on error type
        context["suggested_fixes"] = self._suggest_error_fixes(
            context["error_type"], error_message
        )
        
        return context
    
    async def load_file_context(self, file_path: str) -> Dict[str, Any]:
        """Load context for a specific file."""
        return await self._get_file_context(file_path)
    
    async def track_session_context(self, 
                                  current_task: str = None,
                                  files_modified: List[str] = None,
                                  error_patterns: List[str] = None) -> Dict[str, Any]:
        """Track and update current development session context."""
        session_file = self.context_dir / "sessions" / "current.json"
        session_file.parent.mkdir(exist_ok=True)
        
        # Load existing session or create new
        session_data = {}
        if session_file.exists():
            async with aiofiles.open(session_file, 'r') as f:
                content = await f.read()
                session_data = json.loads(content) if content.strip() else {}
        
        # Update session data
        if current_task:
            session_data["current_task"] = current_task
        if files_modified:
            session_data.setdefault("files_modified", []).extend(files_modified)
            # Keep only last 20 files
            session_data["files_modified"] = session_data["files_modified"][-20:]
        if error_patterns:
            session_data.setdefault("error_patterns", []).extend(error_patterns)
            # Keep only last 10 errors
            session_data["error_patterns"] = session_data["error_patterns"][-10:]
        
        session_data["last_updated"] = datetime.utcnow().isoformat()
        
        # Save session
        async with aiofiles.open(session_file, 'w') as f:
            await f.write(json.dumps(session_data, indent=2))
        
        return session_data
    
    async def _search_static_context(self, query: str) -> List[Dict[str, Any]]:
        """Search static context files for relevant information."""
        results = []
        context_files = [
            "architecture.md", "patterns.md", "apis.md", 
            "frontend.md", "development.md"
        ]
        
        for filename in context_files:
            file_path = self.context_dir / filename
            if file_path.exists():
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    # Simple text search for now - could be enhanced with embeddings
                    if query.lower() in content.lower():
                        results.append({
                            "type": "static_context",
                            "file": filename,
                            "relevance": self._calculate_relevance(query, content),
                            "excerpt": self._extract_excerpt(query, content)
                        })
        
        return sorted(results, key=lambda x: x["relevance"], reverse=True)
    
    async def _search_codebase(self, query: str) -> List[Dict[str, Any]]:
        """Search codebase files for relevant code patterns."""
        results = []
        
        # Search backend Python files
        backend_files = list(self.project_root.glob("backend/**/*.py"))
        for file_path in backend_files[:10]:  # Limit for performance
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    if query.lower() in content.lower():
                        results.append({
                            "type": "code_file",
                            "path": str(file_path.relative_to(self.project_root)),
                            "relevance": self._calculate_relevance(query, content),
                            "excerpt": self._extract_excerpt(query, content)
                        })
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
        
        # Search frontend TypeScript files
        frontend_files = list(self.project_root.glob("frontend/**/*.{ts,tsx}"))
        for file_path in frontend_files[:10]:  # Limit for performance
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    if query.lower() in content.lower():
                        results.append({
                            "type": "code_file",
                            "path": str(file_path.relative_to(self.project_root)),
                            "relevance": self._calculate_relevance(query, content),
                            "excerpt": self._extract_excerpt(query, content)
                        })
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
        
        return sorted(results, key=lambda x: x["relevance"], reverse=True)[:5]
    
    async def _match_patterns(self, query: str) -> List[Dict[str, Any]]:
        """Match query against known patterns."""
        patterns = []
        
        # JWT patterns
        if any(term in query.lower() for term in ["jwt", "authentication", "token", "login"]):
            patterns.append({
                "type": "authentication",
                "pattern": "JWT Authentication",
                "context": "Uses JWT tokens with user_id claim, AuthGuardMiddleware",
                "files": ["backend/app/middleware/auth.py", "patterns.md"]
            })
        
        # CSRF patterns  
        if any(term in query.lower() for term in ["csrf", "cross-site", "security"]):
            patterns.append({
                "type": "security",
                "pattern": "CSRF Protection",
                "context": "CSRF tokens for state-changing operations",
                "files": ["backend/app/middleware/csrf.py", "patterns.md"]
            })
        
        # Database patterns
        if any(term in query.lower() for term in ["database", "sql", "migration", "schema"]):
            patterns.append({
                "type": "database",
                "pattern": "Database Schema",
                "context": "PostgreSQL with crm and leadgen schemas, SQLAlchemy async",
                "files": ["backend/app/db/", "architecture.md"]
            })
        
        return patterns
    
    async def _generate_suggestions(self, query: str, context_results: Dict[str, Any]) -> List[str]:
        """Generate helpful suggestions based on context."""
        suggestions = []
        
        # Based on query type
        if "error" in query.lower():
            suggestions.append("Check error patterns in session history")
            suggestions.append("Review similar errors in vector memory")
        
        if "api" in query.lower():
            suggestions.append("Review API endpoint documentation in apis.md")
            suggestions.append("Check authentication patterns for protected endpoints")
        
        if "database" in query.lower():
            suggestions.append("Review schema in backend/app/db/")
            suggestions.append("Check migration files for recent changes")
        
        # Based on results
        if not context_results["context_sources"]:
            suggestions.append("No existing context found - consider documenting this pattern")
        
        if context_results["relevant_files"]:
            suggestions.append(f"Review {len(context_results['relevant_files'])} relevant files found")
        
        return suggestions
    
    async def _get_file_context(self, file_path: str) -> Dict[str, Any]:
        """Get context information for a specific file."""
        full_path = self.project_root / file_path.lstrip("/")
        if not full_path.exists():
            return None
        
        try:
            async with aiofiles.open(full_path, 'r') as f:
                content = await f.read()
            
            context = {
                "file": file_path,
                "type": self._classify_file_type(file_path),
                "size": len(content),
                "lines": len(content.splitlines())
            }
            
            # Extract file-specific context
            if file_path.endswith('.py'):
                context["imports"] = self._extract_python_imports(content)
                context["functions"] = self._extract_python_functions(content)
            elif file_path.endswith(('.ts', '.tsx')):
                context["imports"] = self._extract_ts_imports(content)
                context["exports"] = self._extract_ts_exports(content)
            
            return context
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error type for targeted context loading."""
        error_lower = error_message.lower()
        
        if "authentication" in error_lower or "unauthorized" in error_lower:
            return "authentication"
        elif "database" in error_lower or "sql" in error_lower:
            return "database"
        elif "import" in error_lower or "module" in error_lower:
            return "import"
        elif "typescript" in error_lower or "type" in error_lower:
            return "typescript"
        elif "docker" in error_lower or "container" in error_lower:
            return "docker"
        else:
            return "generic"
    
    def _extract_file_paths(self, stack_trace: str) -> List[str]:
        """Extract file paths from stack trace."""
        # Match file paths in stack traces
        file_pattern = r'File "([^"]+)"'
        return re.findall(file_pattern, stack_trace)
    
    def _suggest_error_fixes(self, error_type: str, error_message: str) -> List[str]:
        """Suggest fixes based on error type."""
        suggestions = []
        
        if error_type == "authentication":
            suggestions = [
                "Check JWT token validity",
                "Verify user_id in token claims", 
                "Ensure AuthGuardMiddleware is applied",
                "Review token expiration settings"
            ]
        elif error_type == "database":
            suggestions = [
                "Check database connection",
                "Verify schema exists",
                "Review migration status",
                "Check SQL query syntax"
            ]
        elif error_type == "import":
            suggestions = [
                "Check module installation",
                "Verify import path",
                "Check virtual environment activation",
                "Review requirements.txt"
            ]
        elif error_type == "docker":
            suggestions = [
                "Check docker-compose.yml",
                "Verify container health",
                "Review environment variables",
                "Check port bindings"
            ]
        
        return suggestions
    
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score for content."""
        query_terms = query.lower().split()
        content_lower = content.lower()
        
        score = 0.0
        for term in query_terms:
            score += content_lower.count(term)
        
        # Normalize by content length
        return score / len(content) if content else 0.0
    
    def _extract_excerpt(self, query: str, content: str, context_lines: int = 2) -> str:
        """Extract relevant excerpt from content."""
        lines = content.splitlines()
        query_terms = query.lower().split()
        
        for i, line in enumerate(lines):
            if any(term in line.lower() for term in query_terms):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                return "\n".join(lines[start:end])
        
        # Return first few lines if no match
        return "\n".join(lines[:5])
    
    def _classify_file_type(self, file_path: str) -> str:
        """Classify file type."""
        if file_path.endswith('.py'):
            return "python"
        elif file_path.endswith(('.ts', '.tsx')):
            return "typescript"
        elif file_path.endswith('.sql'):
            return "sql"
        elif file_path.endswith(('.yml', '.yaml')):
            return "yaml"
        elif file_path.endswith('.md'):
            return "markdown"
        else:
            return "text"
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract Python import statements."""
        import_pattern = r'^(?:from\s+\S+\s+)?import\s+.+'
        return re.findall(import_pattern, content, re.MULTILINE)
    
    def _extract_python_functions(self, content: str) -> List[str]:
        """Extract Python function definitions."""
        func_pattern = r'^\s*def\s+(\w+)'
        return re.findall(func_pattern, content, re.MULTILINE)
    
    def _extract_ts_imports(self, content: str) -> List[str]:
        """Extract TypeScript import statements."""
        import_pattern = r'^import\s+.+$'
        return re.findall(import_pattern, content, re.MULTILINE)
    
    def _extract_ts_exports(self, content: str) -> List[str]:
        """Extract TypeScript export statements."""
        export_pattern = r'^export\s+.+$'
        return re.findall(export_pattern, content, re.MULTILINE)


@click.command()
@click.option('--query', '-q', help='Natural language query for context')
@click.option('--error', '-e', help='Error message to analyze')
@click.option('--file', '-f', help='File path to analyze')
@click.option('--session', '-s', is_flag=True, help='Show current session context')
@click.option('--task', help='Update current task in session')
@click.option('--org-id', default="1", help='Organization ID for vector memory')
def main(query, error, file, session, task, org_id):
    """War Room Context Loader - Dynamic context retrieval"""
    
    async def run():
        loader = ContextLoader()
        
        if query:
            results = await loader.query_context(query, org_id)
            click.echo(json.dumps(results, indent=2))
            
        elif error:
            results = await loader.load_error_context(error)
            click.echo(json.dumps(results, indent=2))
            
        elif file:
            results = await loader.load_file_context(file)
            if results:
                click.echo(json.dumps(results, indent=2))
            else:
                click.echo(f"File not found or unreadable: {file}")
                
        elif session:
            session_file = loader.context_dir / "sessions" / "current.json"
            if session_file.exists():
                with open(session_file) as f:
                    data = json.load(f)
                click.echo(json.dumps(data, indent=2))
            else:
                click.echo("No current session found")
                
        elif task:
            results = await loader.track_session_context(current_task=task)
            click.echo(f"Updated session task: {task}")
            click.echo(json.dumps(results, indent=2))
            
        else:
            click.echo("Specify --query, --error, --file, --session, or --task")
    
    asyncio.run(run())


if __name__ == "__main__":
    main()