#!/usr/bin/env python3
"""
Semantic Code Indexing - Live codebase understanding via embeddings

Creates and maintains semantic search indexes for:
- Source code files and patterns
- API endpoints and relationships
- Database schema and migrations
- Documentation and comments

Integrates with War Room's vector memory and FastEmbed service.
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
import httpx
from dataclasses import dataclass
import hashlib

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.services.vector_memory import store_memory, search_memory, _get_embedding

logger = logging.getLogger(__name__)

@dataclass
class IndexedFile:
    """Represents an indexed file."""
    path: str
    content_hash: str
    embedding_id: str
    metadata: Dict[str, Any]
    indexed_at: str

@dataclass
class SearchResult:
    """Semantic search result."""
    path: str
    relevance: float
    excerpt: str
    metadata: Dict[str, Any]


class SemanticIndexer:
    """Semantic code indexing and search system."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.context_dir = self.project_root / ".context"
        self.indexes_dir = self.context_dir / "indexes"
        self.indexes_dir.mkdir(exist_ok=True)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load context configuration."""
        config_path = self.context_dir / "context.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    async def build_index(self, org_id: str = "1") -> Dict[str, Any]:
        """Build semantic index of entire codebase."""
        stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "embeddings_created": 0,
            "errors": []
        }
        
        # Load existing index
        existing_index = await self._load_index("code_embeddings")
        
        # Process Python files
        python_files = list(self.project_root.glob("backend/**/*.py"))
        for file_path in python_files:
            if self._should_skip_file(file_path):
                stats["files_skipped"] += 1
                continue
                
            try:
                indexed = await self._index_file(file_path, existing_index, org_id)
                if indexed:
                    stats["files_processed"] += 1
                    stats["embeddings_created"] += 1
            except Exception as e:
                error_msg = f"Error indexing {file_path}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        # Process TypeScript files
        typescript_files = list(self.project_root.glob("frontend/**/*.{ts,tsx}"))
        for file_path in typescript_files:
            if self._should_skip_file(file_path):
                stats["files_skipped"] += 1
                continue
                
            try:
                indexed = await self._index_file(file_path, existing_index, org_id)
                if indexed:
                    stats["files_processed"] += 1
                    stats["embeddings_created"] += 1
            except Exception as e:
                error_msg = f"Error indexing {file_path}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        # Process SQL files
        sql_files = list(self.project_root.glob("backend/app/db/*.sql"))
        for file_path in sql_files:
            try:
                indexed = await self._index_file(file_path, existing_index, org_id)
                if indexed:
                    stats["files_processed"] += 1
                    stats["embeddings_created"] += 1
            except Exception as e:
                error_msg = f"Error indexing {file_path}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        # Save updated index
        await self._save_index("code_embeddings", existing_index)
        
        # Build API endpoint index
        api_stats = await self._build_api_index(org_id)
        stats.update(api_stats)
        
        return stats
    
    async def search_code(self, query: str, limit: int = 10, org_id: str = "1") -> List[SearchResult]:
        """Search codebase using semantic similarity."""
        try:
            # Search in vector memory using War Room's system
            memory_results = await search_memory(org_id, f"code: {query}", limit=limit, score_threshold=0.6)
            
            results = []
            for hit in memory_results:
                payload = hit.get("payload", {})
                metadata = payload.get("metadata", {})
                
                # Only include code-related results
                if metadata.get("type") == "code_index":
                    results.append(SearchResult(
                        path=metadata.get("file_path", "unknown"),
                        relevance=hit.get("score", 0.0),
                        excerpt=self._extract_excerpt(payload.get("text", ""), query),
                        metadata=metadata
                    ))
            
            return sorted(results, key=lambda x: x.relevance, reverse=True)
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def search_apis(self, query: str, limit: int = 5, org_id: str = "1") -> List[SearchResult]:
        """Search API endpoints semantically."""
        try:
            memory_results = await search_memory(org_id, f"api: {query}", limit=limit, score_threshold=0.7)
            
            results = []
            for hit in memory_results:
                payload = hit.get("payload", {})
                metadata = payload.get("metadata", {})
                
                if metadata.get("type") == "api_index":
                    results.append(SearchResult(
                        path=metadata.get("endpoint", "unknown"),
                        relevance=hit.get("score", 0.0),
                        excerpt=payload.get("text", ""),
                        metadata=metadata
                    ))
            
            return sorted(results, key=lambda x: x.relevance, reverse=True)
            
        except Exception as e:
            logger.error(f"API search failed: {e}")
            return []
    
    async def get_file_context(self, file_path: str, org_id: str = "1") -> Dict[str, Any]:
        """Get comprehensive context for a specific file."""
        context = {
            "file_info": {},
            "related_files": [],
            "api_endpoints": [],
            "dependencies": [],
            "usage_patterns": []
        }
        
        # Get file info from index
        full_path = self.project_root / file_path.lstrip("/")
        if full_path.exists():
            context["file_info"] = await self._analyze_file(full_path)
        
        # Find related files via semantic search
        file_name = Path(file_path).stem
        related = await self.search_code(file_name, limit=5, org_id=org_id)
        context["related_files"] = [
            {"path": r.path, "relevance": r.relevance, "reason": "semantic similarity"}
            for r in related if r.path != file_path
        ]
        
        # Find API endpoints if this is an API file
        if "/api/" in file_path:
            api_results = await self.search_apis(file_name, org_id=org_id)
            context["api_endpoints"] = [
                {"endpoint": r.path, "relevance": r.relevance, "description": r.excerpt}
                for r in api_results
            ]
        
        # Extract dependencies
        if full_path.exists():
            context["dependencies"] = await self._extract_dependencies(full_path)
        
        return context
    
    async def update_file_index(self, file_path: str, org_id: str = "1") -> bool:
        """Update index for a single file (when file changes)."""
        full_path = self.project_root / file_path.lstrip("/")
        if not full_path.exists():
            return False
        
        try:
            # Load existing index
            existing_index = await self._load_index("code_embeddings")
            
            # Remove old entry if exists
            file_key = str(full_path.relative_to(self.project_root))
            if file_key in existing_index:
                del existing_index[file_key]
            
            # Add new entry
            indexed = await self._index_file(full_path, existing_index, org_id)
            
            # Save updated index
            await self._save_index("code_embeddings", existing_index)
            
            logger.info(f"Updated index for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update index for {file_path}: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        stats = {
            "code_index_size": 0,
            "api_index_size": 0,
            "last_updated": None,
            "coverage": {}
        }
        
        # Code index stats
        code_index = await self._load_index("code_embeddings")
        stats["code_index_size"] = len(code_index)
        
        if code_index:
            timestamps = [item.get("indexed_at") for item in code_index.values()]
            stats["last_updated"] = max(timestamps) if timestamps else None
        
        # API index stats
        api_index = await self._load_index("api_embeddings")
        stats["api_index_size"] = len(api_index)
        
        # Coverage analysis
        total_python = len(list(self.project_root.glob("backend/**/*.py")))
        total_typescript = len(list(self.project_root.glob("frontend/**/*.{ts,tsx}")))
        total_sql = len(list(self.project_root.glob("backend/app/db/*.sql")))
        
        indexed_python = len([f for f in code_index.keys() if f.endswith('.py')])
        indexed_typescript = len([f for f in code_index.keys() if f.endswith(('.ts', '.tsx'))])
        indexed_sql = len([f for f in code_index.keys() if f.endswith('.sql')])
        
        stats["coverage"] = {
            "python": f"{indexed_python}/{total_python}" if total_python > 0 else "0/0",
            "typescript": f"{indexed_typescript}/{total_typescript}" if total_typescript > 0 else "0/0",
            "sql": f"{indexed_sql}/{total_sql}" if total_sql > 0 else "0/0"
        }
        
        return stats
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during indexing."""
        skip_patterns = [
            "venv", "__pycache__", "node_modules", ".next", ".git",
            "test_", "_test", ".test.", "tests/", "/tests/",
            ".min.", "vendor/", "dist/", "build/"
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    async def _index_file(self, file_path: Path, existing_index: Dict, org_id: str) -> bool:
        """Index a single file."""
        try:
            # Read file content
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
        except Exception as e:
            logger.error(f"Cannot read {file_path}: {e}")
            return False
        
        # Calculate content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        file_key = str(file_path.relative_to(self.project_root))
        
        # Skip if already indexed and unchanged
        if file_key in existing_index:
            if existing_index[file_key].get("content_hash") == content_hash:
                return False
        
        # Prepare content for embedding
        indexed_content = await self._prepare_content_for_embedding(file_path, content)
        
        if not indexed_content:
            return False
        
        # Store in vector memory
        try:
            memory_id = await store_memory(
                org_id=org_id,
                user_id="semantic_indexer",
                text=f"code: {indexed_content}",
                metadata={
                    "type": "code_index",
                    "file_path": file_key,
                    "file_type": self._get_file_type(file_path),
                    "content_hash": content_hash,
                    "size": len(content),
                    "lines": len(content.splitlines()),
                    "indexed_at": datetime.utcnow().isoformat()
                }
            )
            
            # Update local index
            existing_index[file_key] = {
                "content_hash": content_hash,
                "embedding_id": memory_id,
                "metadata": {
                    "file_type": self._get_file_type(file_path),
                    "size": len(content),
                    "lines": len(content.splitlines())
                },
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding for {file_path}: {e}")
            return False
    
    async def _prepare_content_for_embedding(self, file_path: Path, content: str) -> str:
        """Prepare file content for semantic embedding."""
        if len(content.strip()) == 0:
            return ""
        
        file_type = self._get_file_type(file_path)
        
        # Extract meaningful content based on file type
        if file_type == "python":
            return self._extract_python_essence(content, file_path)
        elif file_type == "typescript":
            return self._extract_typescript_essence(content, file_path)
        elif file_type == "sql":
            return self._extract_sql_essence(content, file_path)
        else:
            # For other files, use the content as-is but limit length
            return content[:2000]
    
    def _extract_python_essence(self, content: str, file_path: Path) -> str:
        """Extract semantic essence from Python file."""
        essence_parts = [f"Python file: {file_path.name}"]
        
        # Extract docstrings
        import re
        docstring_pattern = r'"""([^"]+)"""'
        docstrings = re.findall(docstring_pattern, content, re.DOTALL)
        for doc in docstrings[:2]:  # First 2 docstrings
            essence_parts.append(f"Documentation: {doc.strip()[:200]}")
        
        # Extract function/class definitions
        func_pattern = r'^\s*(?:async\s+)?def\s+(\w+)'
        class_pattern = r'^\s*class\s+(\w+)'
        
        functions = re.findall(func_pattern, content, re.MULTILINE)
        classes = re.findall(class_pattern, content, re.MULTILINE)
        
        if classes:
            essence_parts.append(f"Classes: {', '.join(classes)}")
        if functions:
            essence_parts.append(f"Functions: {', '.join(functions[:10])}")  # First 10 functions
        
        # Extract imports to understand dependencies
        import_pattern = r'^(?:from\s+\S+\s+)?import\s+(.+)$'
        imports = re.findall(import_pattern, content, re.MULTILINE)
        if imports:
            essence_parts.append(f"Imports: {', '.join(imports[:5])}")  # First 5 imports
        
        # Add path context
        if "/api/" in str(file_path):
            essence_parts.append("API endpoint handler")
        elif "/services/" in str(file_path):
            essence_parts.append("Business logic service")
        elif "/db/" in str(file_path):
            essence_parts.append("Database layer")
        
        return " | ".join(essence_parts)
    
    def _extract_typescript_essence(self, content: str, file_path: Path) -> str:
        """Extract semantic essence from TypeScript file."""
        essence_parts = [f"TypeScript file: {file_path.name}"]
        
        import re
        
        # Extract component names
        if file_path.suffix in ['.tsx', '.jsx']:
            comp_pattern = r'export\s+(?:default\s+)?(?:function\s+)?(\w+)'
            components = re.findall(comp_pattern, content)
            if components:
                essence_parts.append(f"React component: {components[0]}")
        
        # Extract function names
        func_pattern = r'(?:export\s+)?(?:const|function)\s+(\w+)'
        functions = re.findall(func_pattern, content)
        if functions:
            essence_parts.append(f"Functions: {', '.join(functions[:5])}")
        
        # Extract imports
        import_pattern = r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        imports = re.findall(import_pattern, content)
        if imports:
            essence_parts.append(f"Dependencies: {', '.join(imports[:5])}")
        
        # Extract API calls
        api_pattern = r'[\'"`]/api/([^\'"`]+)[\'"`]'
        apis = re.findall(api_pattern, content)
        if apis:
            essence_parts.append(f"API calls: {', '.join(apis[:3])}")
        
        # Add context
        if "component" in str(file_path).lower():
            essence_parts.append("UI component")
        elif "page" in str(file_path).lower():
            essence_parts.append("Next.js page")
        elif "api" in str(file_path).lower():
            essence_parts.append("API client")
        
        return " | ".join(essence_parts)
    
    def _extract_sql_essence(self, content: str, file_path: Path) -> str:
        """Extract semantic essence from SQL file."""
        essence_parts = [f"SQL file: {file_path.name}"]
        
        import re
        
        # Extract table operations
        create_tables = re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\S+)', content, re.IGNORECASE)
        alter_tables = re.findall(r'ALTER TABLE\s+(\S+)', content, re.IGNORECASE)
        
        if create_tables:
            essence_parts.append(f"Creates tables: {', '.join(create_tables)}")
        if alter_tables:
            essence_parts.append(f"Modifies tables: {', '.join(set(alter_tables))}")
        
        # Extract index creation
        indexes = re.findall(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\S+)', content, re.IGNORECASE)
        if indexes:
            essence_parts.append(f"Creates indexes: {', '.join(indexes)}")
        
        # Detect migration vs schema
        if "migration" in file_path.name.lower():
            essence_parts.append("Database migration")
        else:
            essence_parts.append("Schema definition")
        
        return " | ".join(essence_parts)
    
    def _get_file_type(self, file_path: Path) -> str:
        """Get file type for categorization."""
        if file_path.suffix == '.py':
            return "python"
        elif file_path.suffix in ['.ts', '.tsx']:
            return "typescript"
        elif file_path.suffix == '.sql':
            return "sql"
        elif file_path.suffix in ['.js', '.jsx']:
            return "javascript"
        elif file_path.suffix in ['.yml', '.yaml']:
            return "yaml"
        else:
            return "other"
    
    async def _build_api_index(self, org_id: str) -> Dict[str, Any]:
        """Build semantic index of API endpoints."""
        stats = {"api_endpoints_indexed": 0, "api_errors": []}
        
        # Find API route files
        api_files = list(self.project_root.glob("backend/app/api/*.py"))
        
        api_index = {}
        
        for file_path in api_files:
            try:
                endpoints = await self._extract_api_endpoints(file_path)
                for endpoint in endpoints:
                    # Create embedding for API endpoint
                    endpoint_text = f"API endpoint: {endpoint['method']} {endpoint['path']} - {endpoint.get('description', '')} in {endpoint['file']}"
                    
                    try:
                        memory_id = await store_memory(
                            org_id=org_id,
                            user_id="semantic_indexer",
                            text=f"api: {endpoint_text}",
                            metadata={
                                "type": "api_index",
                                "method": endpoint["method"],
                                "path": endpoint["path"],
                                "endpoint": f"{endpoint['method']} {endpoint['path']}",
                                "function": endpoint.get("function"),
                                "file": endpoint["file"],
                                "indexed_at": datetime.utcnow().isoformat()
                            }
                        )
                        
                        endpoint_key = f"{endpoint['method']}:{endpoint['path']}"
                        api_index[endpoint_key] = {
                            "embedding_id": memory_id,
                            "metadata": endpoint,
                            "indexed_at": datetime.utcnow().isoformat()
                        }
                        
                        stats["api_endpoints_indexed"] += 1
                        
                    except Exception as e:
                        error_msg = f"Failed to index API endpoint {endpoint['path']}: {e}"
                        logger.error(error_msg)
                        stats["api_errors"].append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error processing API file {file_path}: {e}"
                logger.error(error_msg)
                stats["api_errors"].append(error_msg)
        
        # Save API index
        await self._save_index("api_embeddings", api_index)
        
        return stats
    
    async def _extract_api_endpoints(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract API endpoint information from FastAPI file."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        except:
            return []
        
        import re
        endpoints = []
        
        # Find FastAPI route decorators and their functions
        route_pattern = r'@router\.(get|post|put|delete|patch)\(([^)]+)\)'
        func_pattern = r'async def (\w+)\([^)]*\):'
        
        routes = re.finditer(route_pattern, content)
        functions = re.findall(func_pattern, content)
        
        func_index = 0
        for route_match in routes:
            method = route_match.group(1).upper()
            params = route_match.group(2).strip('"\'')
            
            # Extract path from params (simple parsing)
            path = params.split(',')[0].strip('"\'') if ',' in params else params.strip('"\'')
            
            endpoint = {
                "method": method,
                "path": path,
                "function": functions[func_index] if func_index < len(functions) else "unknown",
                "file": str(file_path.relative_to(self.project_root))
            }
            
            # Try to extract docstring/description
            func_start = route_match.end()
            func_content = content[func_start:func_start + 500]
            docstring_match = re.search(r'"""([^"]+)"""', func_content)
            if docstring_match:
                endpoint["description"] = docstring_match.group(1).strip()[:100]
            
            endpoints.append(endpoint)
            func_index += 1
        
        return endpoints
    
    async def _load_index(self, index_name: str) -> Dict[str, Any]:
        """Load index from disk."""
        index_path = self.indexes_dir / f"{index_name}.json"
        if index_path.exists():
            try:
                async with aiofiles.open(index_path, 'r') as f:
                    content = await f.read()
                return json.loads(content) if content.strip() else {}
            except Exception as e:
                logger.error(f"Failed to load index {index_name}: {e}")
        return {}
    
    async def _save_index(self, index_name: str, index_data: Dict[str, Any]):
        """Save index to disk."""
        index_path = self.indexes_dir / f"{index_name}.json"
        try:
            async with aiofiles.open(index_path, 'w') as f:
                await f.write(json.dumps(index_data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save index {index_name}: {e}")
    
    async def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a file and return comprehensive info."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
        except Exception:
            return {}
        
        return {
            "path": str(file_path.relative_to(self.project_root)),
            "name": file_path.name,
            "type": self._get_file_type(file_path),
            "size": len(content),
            "lines": len(content.splitlines()),
            "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
    
    async def _extract_dependencies(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract file dependencies."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
        except Exception:
            return []
        
        dependencies = []
        import re
        
        if file_path.suffix == '.py':
            # Python imports
            import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+(.+)$'
            imports = re.findall(import_pattern, content, re.MULTILINE)
            for module, items in imports:
                dependencies.append({
                    "type": "python_import",
                    "module": module or items.split('.')[0],
                    "items": items
                })
        
        elif file_path.suffix in ['.ts', '.tsx']:
            # TypeScript imports
            import_pattern = r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
            imports = re.findall(import_pattern, content)
            for module in imports:
                dependencies.append({
                    "type": "typescript_import",
                    "module": module
                })
        
        return dependencies
    
    def _extract_excerpt(self, content: str, query: str, context_lines: int = 2) -> str:
        """Extract relevant excerpt from content."""
        if not content or not query:
            return content[:200] if content else ""
        
        lines = content.splitlines()
        query_terms = query.lower().split()
        
        # Find the most relevant line
        best_line_idx = 0
        best_score = 0
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            score = sum(term in line_lower for term in query_terms)
            if score > best_score:
                best_score = score
                best_line_idx = i
        
        # Extract context around best line
        start = max(0, best_line_idx - context_lines)
        end = min(len(lines), best_line_idx + context_lines + 1)
        
        excerpt_lines = lines[start:end]
        excerpt = "\n".join(excerpt_lines)
        
        # Limit length
        if len(excerpt) > 300:
            excerpt = excerpt[:300] + "..."
        
        return excerpt


@click.command()
@click.option('--build', is_flag=True, help='Build semantic index of codebase')
@click.option('--search', '-s', help='Search codebase semantically')
@click.option('--search-apis', help='Search API endpoints')
@click.option('--file-context', '-f', help='Get context for specific file')
@click.option('--update-file', help='Update index for specific file')
@click.option('--stats', is_flag=True, help='Show indexing statistics')
@click.option('--limit', '-l', default=10, help='Limit search results')
@click.option('--org-id', default="1", help='Organization ID for vector memory')
def main(build, search, search_apis, file_context, update_file, stats, limit, org_id):
    """War Room Semantic Code Indexer - Live codebase understanding"""
    
    async def run():
        indexer = SemanticIndexer()
        
        if build:
            click.echo("Building semantic index...")
            results = await indexer.build_index(org_id)
            click.echo(f"Processed {results['files_processed']} files")
            click.echo(f"Created {results['embeddings_created']} embeddings")
            click.echo(f"Skipped {results['files_skipped']} files")
            if results['errors']:
                click.echo(f"Errors: {len(results['errors'])}")
        
        elif search:
            results = await indexer.search_code(search, limit, org_id)
            click.echo(f"Found {len(results)} results for '{search}':")
            for i, result in enumerate(results, 1):
                click.echo(f"\n{i}. {result.path} (relevance: {result.relevance:.3f})")
                click.echo(f"   {result.excerpt[:100]}...")
        
        elif search_apis:
            results = await indexer.search_apis(search_apis, limit, org_id)
            click.echo(f"Found {len(results)} API results for '{search_apis}':")
            for i, result in enumerate(results, 1):
                click.echo(f"\n{i}. {result.path} (relevance: {result.relevance:.3f})")
                click.echo(f"   {result.excerpt}")
        
        elif file_context:
            context = await indexer.get_file_context(file_context, org_id)
            click.echo(json.dumps(context, indent=2))
        
        elif update_file:
            success = await indexer.update_file_index(update_file, org_id)
            if success:
                click.echo(f"Updated index for {update_file}")
            else:
                click.echo(f"Failed to update index for {update_file}")
        
        elif stats:
            statistics = await indexer.get_index_stats()
            click.echo(json.dumps(statistics, indent=2))
        
        else:
            click.echo("Specify --build, --search, --search-apis, --file-context, --update-file, or --stats")
    
    asyncio.run(run())


if __name__ == "__main__":
    main()