#!/usr/bin/env python3
"""
AI Context Generator - Intelligent pattern recognition and documentation

Automatically generates context documentation by analyzing:
- Code patterns and relationships
- API endpoint structures
- Database schema relationships  
- Error patterns and resolutions
- Development workflow patterns

Integrates with War Room's vector memory for persistent storage.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import click
import yaml
import aiofiles
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.services.vector_memory import store_memory, search_memory

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Result of AI code analysis."""
    file_path: str
    patterns: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    documentation: str
    confidence: float
    
@dataclass
class ContextUpdate:
    """Context documentation update."""
    target_file: str
    section: str
    content: str
    reason: str
    confidence: float


class AIContextGenerator:
    """AI-powered context generation and pattern recognition."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.context_dir = self.project_root / ".context"
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load context configuration."""
        config_path = self.context_dir / "context.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    async def analyze_codebase(self, org_id: str = "1") -> List[AnalysisResult]:
        """Analyze entire codebase for patterns and relationships."""
        results = []
        
        # Analyze Python backend files
        backend_files = list(self.project_root.glob("backend/**/*.py"))
        for file_path in backend_files:
            if "venv" not in str(file_path) and "__pycache__" not in str(file_path):
                result = await self._analyze_python_file(file_path)
                if result:
                    results.append(result)
        
        # Analyze TypeScript frontend files
        frontend_files = list(self.project_root.glob("frontend/**/*.{ts,tsx}"))
        for file_path in frontend_files:
            if "node_modules" not in str(file_path) and ".next" not in str(file_path):
                result = await self._analyze_typescript_file(file_path)
                if result:
                    results.append(result)
        
        # Analyze SQL schema files
        sql_files = list(self.project_root.glob("backend/app/db/*.sql"))
        for file_path in sql_files:
            result = await self._analyze_sql_file(file_path)
            if result:
                results.append(result)
        
        # Store analysis results in vector memory
        for result in results:
            await self._store_analysis_result(result, org_id)
        
        return results
    
    async def generate_api_documentation(self) -> Dict[str, Any]:
        """Generate API endpoint documentation from FastAPI code."""
        api_docs = {
            "endpoints": [],
            "auth_patterns": [],
            "request_patterns": [],
            "response_patterns": []
        }
        
        # Scan API route files
        api_files = list(self.project_root.glob("backend/app/api/*.py"))
        for file_path in api_files:
            endpoints = await self._extract_api_endpoints(file_path)
            api_docs["endpoints"].extend(endpoints)
        
        # Extract authentication patterns
        auth_patterns = await self._extract_auth_patterns()
        api_docs["auth_patterns"] = auth_patterns
        
        # Generate structured documentation
        doc_content = await self._generate_api_doc_content(api_docs)
        
        # Write to apis.md
        apis_file = self.context_dir / "apis.md"
        async with aiofiles.open(apis_file, 'w') as f:
            await f.write(doc_content)
        
        return api_docs
    
    async def generate_database_schema_docs(self) -> Dict[str, Any]:
        """Generate database schema documentation from SQL files."""
        schema_docs = {
            "tables": [],
            "relationships": [],
            "migrations": [],
            "patterns": []
        }
        
        # Analyze schema files
        schema_files = list(self.project_root.glob("backend/app/db/*.sql"))
        for file_path in schema_files:
            if "migration" in file_path.name:
                migration_info = await self._analyze_migration_file(file_path)
                schema_docs["migrations"].append(migration_info)
            else:
                table_info = await self._analyze_schema_file(file_path)
                if table_info:
                    schema_docs["tables"].extend(table_info["tables"])
                    schema_docs["relationships"].extend(table_info["relationships"])
        
        # Generate documentation
        doc_content = await self._generate_schema_doc_content(schema_docs)
        
        # Update architecture.md with schema info
        arch_file = self.context_dir / "architecture.md"
        if arch_file.exists():
            await self._update_architecture_schema_section(arch_file, doc_content)
        
        return schema_docs
    
    async def detect_error_patterns(self, org_id: str = "1") -> List[Dict[str, Any]]:
        """Detect common error patterns from session history and logs."""
        patterns = []
        
        # Search vector memory for error-related content
        error_memories = await search_memory(org_id, "error", limit=20, score_threshold=0.6)
        
        # Group similar errors
        error_groups = self._group_similar_errors(error_memories)
        
        # Generate pattern documentation
        for group in error_groups:
            pattern = {
                "error_type": group["type"],
                "frequency": group["count"],
                "description": group["description"],
                "common_causes": group["causes"],
                "solutions": group["solutions"],
                "prevention": group["prevention"]
            }
            patterns.append(pattern)
        
        # Store patterns in development.md
        await self._update_error_patterns_section(patterns)
        
        return patterns
    
    async def update_context_from_changes(self, changed_files: List[str], org_id: str = "1") -> List[ContextUpdate]:
        """Update context documentation based on file changes."""
        updates = []
        
        for file_path in changed_files:
            full_path = self.project_root / file_path.lstrip("/")
            if not full_path.exists():
                continue
            
            # Analyze the changed file
            if file_path.endswith('.py'):
                result = await self._analyze_python_file(full_path)
            elif file_path.endswith(('.ts', '.tsx')):
                result = await self._analyze_typescript_file(full_path)
            elif file_path.endswith('.sql'):
                result = await self._analyze_sql_file(full_path)
            else:
                continue
            
            if not result:
                continue
            
            # Determine what context needs updating
            context_updates = await self._determine_context_updates(result)
            updates.extend(context_updates)
            
            # Store updated analysis
            await self._store_analysis_result(result, org_id)
        
        # Apply high-confidence updates automatically
        auto_updates = [u for u in updates if u.confidence >= 0.8]
        for update in auto_updates:
            await self._apply_context_update(update)
        
        return updates
    
    async def _analyze_python_file(self, file_path: Path) -> Optional[AnalysisResult]:
        """Analyze a Python file for patterns."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
        
        patterns = []
        relationships = []
        
        # Extract API endpoint patterns
        if "/api/" in str(file_path):
            patterns.extend(self._extract_fastapi_patterns(content))
            relationships.extend(self._extract_api_relationships(content))
        
        # Extract service layer patterns
        if "/services/" in str(file_path):
            patterns.extend(self._extract_service_patterns(content))
            relationships.extend(self._extract_service_relationships(content))
        
        # Extract database patterns
        if "db.py" in str(file_path) or "/db/" in str(file_path):
            patterns.extend(self._extract_db_patterns(content))
            relationships.extend(self._extract_db_relationships(content))
        
        # Generate documentation
        documentation = self._generate_file_documentation(file_path, patterns, relationships)
        
        return AnalysisResult(
            file_path=str(file_path.relative_to(self.project_root)),
            patterns=patterns,
            relationships=relationships,
            documentation=documentation,
            confidence=0.85  # High confidence for pattern recognition
        )
    
    async def _analyze_typescript_file(self, file_path: Path) -> Optional[AnalysisResult]:
        """Analyze a TypeScript file for patterns."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
        
        patterns = []
        relationships = []
        
        # Extract React component patterns
        if file_path.suffix in ['.tsx', '.jsx']:
            patterns.extend(self._extract_react_patterns(content))
            relationships.extend(self._extract_react_relationships(content))
        
        # Extract API client patterns
        if "api" in str(file_path).lower() or "service" in str(file_path).lower():
            patterns.extend(self._extract_api_client_patterns(content))
            relationships.extend(self._extract_client_relationships(content))
        
        # Extract state management patterns
        if "store" in str(file_path).lower() or "zustand" in content:
            patterns.extend(self._extract_state_patterns(content))
        
        documentation = self._generate_file_documentation(file_path, patterns, relationships)
        
        return AnalysisResult(
            file_path=str(file_path.relative_to(self.project_root)),
            patterns=patterns,
            relationships=relationships,
            documentation=documentation,
            confidence=0.85
        )
    
    async def _analyze_sql_file(self, file_path: Path) -> Optional[AnalysisResult]:
        """Analyze a SQL file for schema patterns."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
        
        patterns = []
        relationships = []
        
        # Extract table definitions
        patterns.extend(self._extract_table_patterns(content))
        
        # Extract foreign key relationships
        relationships.extend(self._extract_fk_relationships(content))
        
        # Extract index patterns
        patterns.extend(self._extract_index_patterns(content))
        
        documentation = self._generate_file_documentation(file_path, patterns, relationships)
        
        return AnalysisResult(
            file_path=str(file_path.relative_to(self.project_root)),
            patterns=patterns,
            relationships=relationships,
            documentation=documentation,
            confidence=0.9  # Very high confidence for SQL parsing
        )
    
    def _extract_fastapi_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract FastAPI route patterns."""
        patterns = []
        
        # Find route decorators
        import re
        route_pattern = r'@router\.(get|post|put|delete|patch)\(([^)]+)\)'
        matches = re.findall(route_pattern, content)
        
        for method, params in matches:
            patterns.append({
                "type": "api_endpoint",
                "method": method.upper(),
                "details": params,
                "category": "fastapi"
            })
        
        # Find dependency injection patterns
        if "Depends(" in content:
            patterns.append({
                "type": "dependency_injection",
                "framework": "fastapi",
                "category": "architecture"
            })
        
        return patterns
    
    def _extract_api_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Extract API relationship patterns."""
        relationships = []
        
        # Database dependencies
        if "AsyncSession" in content and "db:" in content:
            relationships.append({
                "type": "database_dependency",
                "from": "api_endpoint",
                "to": "database",
                "pattern": "async_session"
            })
        
        # Service layer calls
        import re
        service_calls = re.findall(r'(\w+Service)\.(\w+)', content)
        for service, method in service_calls:
            relationships.append({
                "type": "service_dependency",
                "from": "api_endpoint",
                "to": service,
                "method": method
            })
        
        return relationships
    
    def _extract_service_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract service layer patterns."""
        patterns = []
        
        # Async methods
        if "async def" in content:
            patterns.append({
                "type": "async_service",
                "category": "architecture"
            })
        
        # Error handling patterns
        if "try:" in content and "except" in content:
            patterns.append({
                "type": "error_handling",
                "category": "reliability"
            })
        
        return patterns
    
    def _extract_service_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Extract service relationships."""
        relationships = []
        
        # Database access
        if "db.execute" in content or "session.execute" in content:
            relationships.append({
                "type": "database_access",
                "from": "service",
                "to": "database",
                "pattern": "sqlalchemy"
            })
        
        return relationships
    
    def _extract_db_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract database patterns."""
        patterns = []
        
        if "CREATE TABLE" in content:
            patterns.append({
                "type": "table_definition",
                "category": "schema"
            })
        
        if "ALTER TABLE" in content:
            patterns.append({
                "type": "schema_migration",
                "category": "migration"
            })
        
        return patterns
    
    def _extract_db_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Extract database relationships."""
        relationships = []
        
        import re
        fk_pattern = r'REFERENCES\s+(\w+)\((\w+)\)'
        matches = re.findall(fk_pattern, content)
        
        for table, column in matches:
            relationships.append({
                "type": "foreign_key",
                "from": "current_table",
                "to": table,
                "column": column
            })
        
        return relationships
    
    def _extract_react_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract React component patterns."""
        patterns = []
        
        if "useState" in content:
            patterns.append({
                "type": "react_state",
                "category": "frontend"
            })
        
        if "useEffect" in content:
            patterns.append({
                "type": "react_effect",
                "category": "frontend"
            })
        
        if "export default" in content:
            patterns.append({
                "type": "react_component",
                "category": "frontend"
            })
        
        return patterns
    
    def _extract_react_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Extract React relationships."""
        relationships = []
        
        # API calls
        if "fetch(" in content or "axios." in content:
            relationships.append({
                "type": "api_call",
                "from": "component",
                "to": "backend_api"
            })
        
        return relationships
    
    def _extract_api_client_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract API client patterns."""
        patterns = []
        
        if "fetch(" in content:
            patterns.append({
                "type": "fetch_api",
                "category": "http_client"
            })
        
        if "axios" in content:
            patterns.append({
                "type": "axios_client",
                "category": "http_client"
            })
        
        return patterns
    
    def _extract_client_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Extract client-side relationships."""
        relationships = []
        
        # Extract API endpoint calls
        import re
        api_calls = re.findall(r'[\'"`]/api/([^\'"`]+)[\'"`]', content)
        for endpoint in api_calls:
            relationships.append({
                "type": "api_endpoint_call",
                "from": "frontend",
                "to": f"/api/{endpoint}"
            })
        
        return relationships
    
    def _extract_state_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract state management patterns."""
        patterns = []
        
        if "useStore" in content or "create(" in content:
            patterns.append({
                "type": "zustand_store",
                "category": "state_management"
            })
        
        return patterns
    
    def _extract_table_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract SQL table patterns."""
        patterns = []
        
        import re
        table_matches = re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\S+)', content, re.IGNORECASE)
        for table in table_matches:
            patterns.append({
                "type": "table",
                "name": table,
                "category": "schema"
            })
        
        return patterns
    
    def _extract_fk_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Extract foreign key relationships."""
        relationships = []
        
        import re
        fk_pattern = r'(\w+)\s+.*?REFERENCES\s+(\w+)\((\w+)\)'
        matches = re.findall(fk_pattern, content, re.IGNORECASE)
        
        for column, ref_table, ref_column in matches:
            relationships.append({
                "type": "foreign_key",
                "from_column": column,
                "to_table": ref_table,
                "to_column": ref_column
            })
        
        return relationships
    
    def _extract_index_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract index patterns."""
        patterns = []
        
        import re
        index_matches = re.findall(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\S+)', content, re.IGNORECASE)
        for index in index_matches:
            patterns.append({
                "type": "index",
                "name": index,
                "category": "performance"
            })
        
        return patterns
    
    def _generate_file_documentation(self, file_path: Path, patterns: List[Dict], relationships: List[Dict]) -> str:
        """Generate documentation for a file."""
        doc = f"# {file_path.name}\n\n"
        doc += f"**Path:** {file_path}\n"
        doc += f"**Type:** {self._classify_file_type(file_path)}\n\n"
        
        if patterns:
            doc += "## Patterns\n\n"
            for pattern in patterns:
                doc += f"- **{pattern['type']}**: {pattern.get('category', 'general')}\n"
        
        if relationships:
            doc += "\n## Relationships\n\n"
            for rel in relationships:
                doc += f"- {rel['type']}: {rel.get('from', '?')} -> {rel.get('to', '?')}\n"
        
        doc += f"\n*Generated by AI Context Generator at {datetime.utcnow().isoformat()}*\n"
        
        return doc
    
    def _classify_file_type(self, file_path: Path) -> str:
        """Classify file type."""
        if "api" in str(file_path):
            return "API endpoint"
        elif "service" in str(file_path):
            return "Service layer"
        elif "db" in str(file_path):
            return "Database schema"
        elif file_path.suffix in ['.tsx', '.jsx']:
            return "React component"
        elif file_path.suffix == '.ts':
            return "TypeScript module"
        elif file_path.suffix == '.py':
            return "Python module"
        else:
            return "Unknown"
    
    async def _store_analysis_result(self, result: AnalysisResult, org_id: str):
        """Store analysis result in vector memory."""
        try:
            memory_text = f"File: {result.file_path}\n\n{result.documentation}"
            metadata = {
                "type": "ai_analysis",
                "file_path": result.file_path,
                "patterns": result.patterns,
                "relationships": result.relationships,
                "confidence": result.confidence,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            await store_memory(org_id, "ai_generator", memory_text, metadata)
            logger.info(f"Stored analysis for {result.file_path}")
            
        except Exception as e:
            logger.error(f"Failed to store analysis for {result.file_path}: {e}")
    
    def _group_similar_errors(self, error_memories: List[Dict]) -> List[Dict[str, Any]]:
        """Group similar errors for pattern detection."""
        # Simplified grouping by error keywords
        groups = {}
        
        for memory in error_memories:
            text = memory.get("payload", {}).get("text", "")
            error_type = self._classify_error_type(text)
            
            if error_type not in groups:
                groups[error_type] = {
                    "type": error_type,
                    "count": 0,
                    "examples": [],
                    "description": f"Common {error_type} errors",
                    "causes": [],
                    "solutions": [],
                    "prevention": []
                }
            
            groups[error_type]["count"] += 1
            groups[error_type]["examples"].append(text[:200])
        
        return list(groups.values())
    
    def _classify_error_type(self, error_text: str) -> str:
        """Classify error type from text."""
        text_lower = error_text.lower()
        
        if "authentication" in text_lower or "unauthorized" in text_lower:
            return "authentication"
        elif "database" in text_lower or "sql" in text_lower:
            return "database"
        elif "import" in text_lower or "module" in text_lower:
            return "import"
        elif "docker" in text_lower:
            return "docker"
        elif "typescript" in text_lower:
            return "typescript"
        else:
            return "generic"
    
    async def _extract_api_endpoints(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract API endpoint information."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        except:
            return []
        
        endpoints = []
        import re
        
        # Find FastAPI route decorators
        route_pattern = r'@router\.(get|post|put|delete|patch)\(([^)]+)\)'
        function_pattern = r'async def (\w+)\('
        
        routes = re.findall(route_pattern, content)
        functions = re.findall(function_pattern, content)
        
        for i, (method, params) in enumerate(routes):
            endpoint = {
                "method": method.upper(),
                "path": params.strip('"\''),
                "function": functions[i] if i < len(functions) else "unknown",
                "file": str(file_path.relative_to(self.project_root))
            }
            endpoints.append(endpoint)
        
        return endpoints
    
    async def _extract_auth_patterns(self) -> List[Dict[str, Any]]:
        """Extract authentication patterns."""
        patterns = []
        
        # Look for auth middleware
        auth_files = list(self.project_root.glob("**/auth*.py")) + \
                    list(self.project_root.glob("**/middleware*.py"))
        
        for file_path in auth_files:
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                
                if "JWT" in content or "jwt" in content:
                    patterns.append({
                        "type": "JWT authentication",
                        "file": str(file_path.relative_to(self.project_root)),
                        "description": "JWT token-based authentication"
                    })
                
                if "CSRF" in content or "csrf" in content:
                    patterns.append({
                        "type": "CSRF protection",
                        "file": str(file_path.relative_to(self.project_root)),
                        "description": "Cross-Site Request Forgery protection"
                    })
            except:
                continue
        
        return patterns
    
    async def _generate_api_doc_content(self, api_docs: Dict[str, Any]) -> str:
        """Generate API documentation content."""
        content = "# API Documentation\n\n"
        content += "*Auto-generated from codebase analysis*\n\n"
        
        content += "## Endpoints\n\n"
        for endpoint in api_docs["endpoints"]:
            content += f"### {endpoint['method']} {endpoint['path']}\n\n"
            content += f"**Function:** `{endpoint['function']}`\n"
            content += f"**File:** `{endpoint['file']}`\n\n"
        
        if api_docs["auth_patterns"]:
            content += "## Authentication\n\n"
            for pattern in api_docs["auth_patterns"]:
                content += f"- **{pattern['type']}**: {pattern['description']}\n"
                content += f"  - File: `{pattern['file']}`\n\n"
        
        content += f"\n*Generated at {datetime.utcnow().isoformat()}*\n"
        return content
    
    async def _analyze_migration_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a migration file."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        except:
            return {}
        
        return {
            "file": str(file_path.relative_to(self.project_root)),
            "name": file_path.stem,
            "tables_created": len(re.findall(r'CREATE TABLE', content, re.IGNORECASE)),
            "tables_altered": len(re.findall(r'ALTER TABLE', content, re.IGNORECASE)),
            "indexes_created": len(re.findall(r'CREATE INDEX', content, re.IGNORECASE))
        }
    
    async def _analyze_schema_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a schema file."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        except:
            return {}
        
        import re
        
        tables = []
        table_matches = re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\S+)', content, re.IGNORECASE)
        for table in table_matches:
            tables.append({"name": table, "type": "table"})
        
        relationships = []
        fk_matches = re.findall(r'REFERENCES\s+(\w+)\((\w+)\)', content, re.IGNORECASE)
        for ref_table, ref_column in fk_matches:
            relationships.append({
                "type": "foreign_key",
                "target_table": ref_table,
                "target_column": ref_column
            })
        
        return {
            "tables": tables,
            "relationships": relationships
        }
    
    async def _generate_schema_doc_content(self, schema_docs: Dict[str, Any]) -> str:
        """Generate schema documentation content."""
        content = "# Database Schema\n\n"
        content += "*Auto-generated from SQL analysis*\n\n"
        
        if schema_docs["tables"]:
            content += "## Tables\n\n"
            for table in schema_docs["tables"]:
                content += f"- `{table['name']}`\n"
        
        if schema_docs["relationships"]:
            content += "\n## Relationships\n\n"
            for rel in schema_docs["relationships"]:
                content += f"- Foreign key to `{rel['target_table']}.{rel['target_column']}`\n"
        
        if schema_docs["migrations"]:
            content += "\n## Migrations\n\n"
            for migration in schema_docs["migrations"]:
                content += f"- **{migration['name']}**: "
                content += f"{migration['tables_created']} tables created, "
                content += f"{migration['tables_altered']} altered\n"
        
        return content
    
    async def _update_architecture_schema_section(self, arch_file: Path, schema_content: str):
        """Update architecture.md with schema information."""
        try:
            async with aiofiles.open(arch_file, 'r') as f:
                content = await f.read()
            
            # Replace or append schema section
            if "## Database Schema" in content:
                # Replace existing section
                import re
                pattern = r'## Database Schema.*?(?=##|$)'
                content = re.sub(pattern, schema_content, content, flags=re.DOTALL)
            else:
                # Append new section
                content += f"\n\n{schema_content}"
            
            async with aiofiles.open(arch_file, 'w') as f:
                await f.write(content)
                
        except Exception as e:
            logger.error(f"Failed to update architecture.md: {e}")
    
    async def _update_error_patterns_section(self, patterns: List[Dict[str, Any]]):
        """Update development.md with error patterns."""
        dev_file = self.context_dir / "development.md"
        
        content = "# Common Error Patterns\n\n"
        content += "*Auto-detected from session history*\n\n"
        
        for pattern in patterns:
            content += f"## {pattern['error_type'].title()} Errors\n\n"
            content += f"**Frequency:** {pattern['frequency']} occurrences\n"
            content += f"**Description:** {pattern['description']}\n\n"
            
            if pattern['solutions']:
                content += "**Solutions:**\n"
                for solution in pattern['solutions']:
                    content += f"- {solution}\n"
                content += "\n"
        
        # Append to or create development.md
        try:
            if dev_file.exists():
                async with aiofiles.open(dev_file, 'r') as f:
                    existing = await f.read()
                if "# Common Error Patterns" not in existing:
                    content = existing + "\n\n" + content
            
            async with aiofiles.open(dev_file, 'w') as f:
                await f.write(content)
                
        except Exception as e:
            logger.error(f"Failed to update development.md: {e}")
    
    async def _determine_context_updates(self, result: AnalysisResult) -> List[ContextUpdate]:
        """Determine what context documentation needs updating."""
        updates = []
        
        # API endpoint changes
        api_patterns = [p for p in result.patterns if p["type"] == "api_endpoint"]
        if api_patterns and "/api/" in result.file_path:
            updates.append(ContextUpdate(
                target_file="apis.md",
                section="endpoints",
                content=f"New endpoint detected in {result.file_path}",
                reason="API endpoint addition/modification",
                confidence=0.9
            ))
        
        # Database schema changes
        db_patterns = [p for p in result.patterns if p["category"] == "schema"]
        if db_patterns and ("/db/" in result.file_path or result.file_path.endswith('.sql')):
            updates.append(ContextUpdate(
                target_file="architecture.md",
                section="database_schema",
                content=f"Schema changes in {result.file_path}",
                reason="Database schema modification",
                confidence=0.95
            ))
        
        return updates
    
    async def _apply_context_update(self, update: ContextUpdate):
        """Apply a context documentation update."""
        try:
            target_path = self.context_dir / update.target_file
            
            if target_path.exists():
                async with aiofiles.open(target_path, 'r') as f:
                    content = await f.read()
            else:
                content = f"# {update.target_file.split('.')[0].title()}\n\n"
            
            # Append update
            content += f"\n## Auto-Update: {update.section}\n\n"
            content += update.content
            content += f"\n\n*Updated automatically: {update.reason} (confidence: {update.confidence})*\n"
            
            async with aiofiles.open(target_path, 'w') as f:
                await f.write(content)
            
            logger.info(f"Applied context update to {update.target_file}")
            
        except Exception as e:
            logger.error(f"Failed to apply update to {update.target_file}: {e}")


@click.command()
@click.option('--analyze', is_flag=True, help='Analyze entire codebase')
@click.option('--api-docs', is_flag=True, help='Generate API documentation')
@click.option('--schema-docs', is_flag=True, help='Generate database schema docs')
@click.option('--error-patterns', is_flag=True, help='Detect error patterns')
@click.option('--watch-files', help='Update context for changed files (comma-separated)')
@click.option('--org-id', default="1", help='Organization ID for vector memory')
def main(analyze, api_docs, schema_docs, error_patterns, watch_files, org_id):
    """War Room AI Context Generator - Intelligent pattern recognition"""
    
    async def run():
        generator = AIContextGenerator()
        
        if analyze:
            results = await generator.analyze_codebase(org_id)
            click.echo(f"Analyzed {len(results)} files")
            for result in results[:5]:  # Show first 5
                click.echo(f"  {result.file_path}: {len(result.patterns)} patterns")
        
        elif api_docs:
            docs = await generator.generate_api_documentation()
            click.echo(f"Generated API docs: {len(docs['endpoints'])} endpoints")
            
        elif schema_docs:
            docs = await generator.generate_database_schema_docs()
            click.echo(f"Generated schema docs: {len(docs['tables'])} tables")
            
        elif error_patterns:
            patterns = await generator.detect_error_patterns(org_id)
            click.echo(f"Detected {len(patterns)} error patterns")
            
        elif watch_files:
            files = [f.strip() for f in watch_files.split(',')]
            updates = await generator.update_context_from_changes(files, org_id)
            click.echo(f"Generated {len(updates)} context updates")
            auto_applied = [u for u in updates if u.confidence >= 0.8]
            click.echo(f"Auto-applied {len(auto_applied)} high-confidence updates")
            
        else:
            click.echo("Specify --analyze, --api-docs, --schema-docs, --error-patterns, or --watch-files")
    
    asyncio.run(run())


if __name__ == "__main__":
    main()