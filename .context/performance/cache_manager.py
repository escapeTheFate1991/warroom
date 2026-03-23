"""
Context Cache Manager

Provides efficient caching layer for sub-second context retrieval.
Implements LRU caching, content hashing, and cache invalidation.
"""

import json
import time
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, asdict
from collections import OrderedDict


@dataclass
class CacheEntry:
    """Represents a cached context entry."""
    key: str
    content: Any
    content_hash: str
    access_count: int
    created_at: float
    last_accessed: float
    file_path: Optional[str] = None
    tags: Optional[List[str]] = None


class LRUCache:
    """LRU (Least Recently Used) cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from cache and mark as recently used."""
        if key in self.cache:
            # Move to end (most recently used)
            entry = self.cache.pop(key)
            entry.last_accessed = time.time()
            entry.access_count += 1
            self.cache[key] = entry
            self.stats["hits"] += 1
            return entry
        else:
            self.stats["misses"] += 1
            return None
    
    def put(self, key: str, entry: CacheEntry):
        """Put item in cache, evicting LRU items if necessary."""
        if key in self.cache:
            # Update existing entry
            self.cache.pop(key)
        elif len(self.cache) >= self.max_size:
            # Evict least recently used item
            self.cache.popitem(last=False)
            self.stats["evictions"] += 1
        
        self.cache[key] = entry
    
    def invalidate(self, key: str) -> bool:
        """Remove item from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """Clear entire cache."""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "total_entries": len(self.cache),
            "max_size": self.max_size
        }


class CacheManager:
    """High-performance context cache manager."""
    
    def __init__(self, project_root: str = "/home/eddy/Development/warroom"):
        self.project_root = Path(project_root)
        self.context_dir = self.project_root / ".context"
        self.cache_dir = self.context_dir / "performance" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize caches for different content types
        self.content_cache = LRUCache(max_size=500)  # Context file contents
        self.pattern_cache = LRUCache(max_size=200)  # Pattern matching results
        self.index_cache = LRUCache(max_size=100)   # Search index results
        
        # Persistent cache metadata
        self.cache_metadata_file = self.cache_dir / "metadata.json"
        self.file_hashes_file = self.cache_dir / "file_hashes.json"
        
        self.file_hashes = self._load_file_hashes()
        
    def _load_file_hashes(self) -> Dict[str, str]:
        """Load file hashes for cache invalidation."""
        if self.file_hashes_file.exists():
            with open(self.file_hashes_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_file_hashes(self):
        """Save file hashes to disk."""
        with open(self.file_hashes_file, 'w') as f:
            json.dump(self.file_hashes, f, indent=2)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file contents."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""
    
    def _is_file_modified(self, file_path: Path) -> bool:
        """Check if file has been modified since last cache."""
        current_hash = self._calculate_file_hash(file_path)
        stored_hash = self.file_hashes.get(str(file_path))
        
        if stored_hash != current_hash:
            self.file_hashes[str(file_path)] = current_hash
            self._save_file_hashes()
            return True
        
        return False
    
    def get_content(self, file_path: str, cache_ttl: int = 3600) -> Optional[str]:
        """Get cached file content or load from disk."""
        cache_key = f"content:{file_path}"
        
        # Check if file exists
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = self.context_dir / file_path
        
        if not full_path.exists():
            return None
        
        # Check cache first
        cached_entry = self.content_cache.get(cache_key)
        
        # Validate cache entry
        if cached_entry:
            # Check TTL
            if time.time() - cached_entry.created_at < cache_ttl:
                # Check if file was modified
                if not self._is_file_modified(full_path):
                    return cached_entry.content
            
            # Cache invalid, remove it
            self.content_cache.invalidate(cache_key)
        
        # Load from disk and cache
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                content=content,
                content_hash=hashlib.md5(content.encode()).hexdigest(),
                access_count=1,
                created_at=time.time(),
                last_accessed=time.time(),
                file_path=str(full_path),
                tags=["content"]
            )
            
            self.content_cache.put(cache_key, entry)
            return content
        
        except Exception as e:
            print(f"Warning: Failed to load content from {full_path}: {e}")
            return None
    
    def cache_pattern_results(self, pattern: str, pattern_type: str, 
                            results: List[Any], ttl: int = 1800) -> str:
        """Cache pattern matching results."""
        cache_key = f"pattern:{pattern_type}:{hashlib.md5(pattern.encode()).hexdigest()}"
        
        entry = CacheEntry(
            key=cache_key,
            content=results,
            content_hash=hashlib.md5(str(results).encode()).hexdigest(),
            access_count=1,
            created_at=time.time(),
            last_accessed=time.time(),
            tags=["pattern", pattern_type]
        )
        
        self.pattern_cache.put(cache_key, entry)
        return cache_key
    
    def get_pattern_results(self, pattern: str, pattern_type: str, 
                          ttl: int = 1800) -> Optional[List[Any]]:
        """Get cached pattern matching results."""
        cache_key = f"pattern:{pattern_type}:{hashlib.md5(pattern.encode()).hexdigest()}"
        
        cached_entry = self.pattern_cache.get(cache_key)
        
        if cached_entry and time.time() - cached_entry.created_at < ttl:
            return cached_entry.content
        
        return None
    
    def cache_index_query(self, query: str, results: List[Any], 
                         index_type: str = "general", ttl: int = 900) -> str:
        """Cache search index query results."""
        cache_key = f"index:{index_type}:{hashlib.md5(query.encode()).hexdigest()}"
        
        entry = CacheEntry(
            key=cache_key,
            content=results,
            content_hash=hashlib.md5(str(results).encode()).hexdigest(),
            access_count=1,
            created_at=time.time(),
            last_accessed=time.time(),
            tags=["index", index_type]
        )
        
        self.index_cache.put(cache_key, entry)
        return cache_key
    
    def get_index_results(self, query: str, index_type: str = "general", 
                         ttl: int = 900) -> Optional[List[Any]]:
        """Get cached search index results."""
        cache_key = f"index:{index_type}:{hashlib.md5(query.encode()).hexdigest()}"
        
        cached_entry = self.index_cache.get(cache_key)
        
        if cached_entry and time.time() - cached_entry.created_at < ttl:
            return cached_entry.content
        
        return None
    
    def invalidate_by_file(self, file_path: str):
        """Invalidate all cache entries related to a file."""
        # Mark file as modified to invalidate content cache
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = self.context_dir / file_path
        
        if full_path.exists():
            self.file_hashes[str(full_path)] = "invalidated"
            self._save_file_hashes()
        
        # Invalidate pattern and index caches (they might be affected)
        self.pattern_cache.clear()
        self.index_cache.clear()
    
    def invalidate_by_tag(self, tag: str):
        """Invalidate all cache entries with specific tag."""
        caches = [self.content_cache, self.pattern_cache, self.index_cache]
        
        for cache in caches:
            keys_to_remove = []
            for key, entry in cache.cache.items():
                if entry.tags and tag in entry.tags:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                cache.invalidate(key)
    
    def warm_cache(self, file_paths: List[str]):
        """Pre-load cache with commonly used files."""
        print(f"🔥 Warming cache with {len(file_paths)} files...")
        
        loaded = 0
        for file_path in file_paths:
            content = self.get_content(file_path)
            if content:
                loaded += 1
        
        print(f"✅ Warmed cache with {loaded}/{len(file_paths)} files")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        content_stats = self.content_cache.get_stats()
        pattern_stats = self.pattern_cache.get_stats()
        index_stats = self.index_cache.get_stats()
        
        total_hits = content_stats["hits"] + pattern_stats["hits"] + index_stats["hits"]
        total_misses = content_stats["misses"] + pattern_stats["misses"] + index_stats["misses"]
        total_requests = total_hits + total_misses
        
        overall_hit_rate = total_hits / total_requests if total_requests > 0 else 0
        
        return {
            "overall": {
                "hit_rate": overall_hit_rate,
                "total_requests": total_requests,
                "total_hits": total_hits,
                "total_misses": total_misses
            },
            "content_cache": content_stats,
            "pattern_cache": pattern_stats,
            "index_cache": index_stats,
            "cache_sizes": {
                "content": len(self.content_cache.cache),
                "pattern": len(self.pattern_cache.cache),
                "index": len(self.index_cache.cache)
            },
            "file_hashes_tracked": len(self.file_hashes)
        }
    
    def cleanup_expired_cache(self, max_age_hours: int = 24):
        """Remove expired cache entries."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        caches = [
            ("content", self.content_cache),
            ("pattern", self.pattern_cache), 
            ("index", self.index_cache)
        ]
        
        removed_total = 0
        
        for cache_name, cache in caches:
            keys_to_remove = []
            
            for key, entry in cache.cache.items():
                if current_time - entry.created_at > max_age_seconds:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                cache.invalidate(key)
            
            removed_total += len(keys_to_remove)
        
        return removed_total
    
    def export_cache_metadata(self) -> Dict[str, Any]:
        """Export cache metadata for analysis."""
        metadata = {
            "export_time": datetime.now().isoformat(),
            "stats": self.get_cache_stats(),
            "entries": {}
        }
        
        # Export entry metadata (not content)
        caches = [
            ("content", self.content_cache),
            ("pattern", self.pattern_cache),
            ("index", self.index_cache)
        ]
        
        for cache_name, cache in caches:
            metadata["entries"][cache_name] = []
            
            for key, entry in cache.cache.items():
                metadata["entries"][cache_name].append({
                    "key": key,
                    "content_hash": entry.content_hash,
                    "access_count": entry.access_count,
                    "created_at": datetime.fromtimestamp(entry.created_at).isoformat(),
                    "last_accessed": datetime.fromtimestamp(entry.last_accessed).isoformat(),
                    "file_path": entry.file_path,
                    "tags": entry.tags
                })
        
        # Save metadata
        with open(self.cache_metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata


if __name__ == "__main__":
    # CLI interface for cache management
    import sys
    
    cache_manager = CacheManager()
    
    if len(sys.argv) < 2:
        print("Usage: python cache_manager.py [stats|warm|cleanup|clear|export]")
        print("Examples:")
        print("  python cache_manager.py stats      # Show cache statistics")
        print("  python cache_manager.py warm       # Warm cache with common files")
        print("  python cache_manager.py cleanup    # Remove expired entries")
        print("  python cache_manager.py clear      # Clear all caches")
        print("  python cache_manager.py export     # Export cache metadata")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "stats":
        stats = cache_manager.get_cache_stats()
        print("📊 Cache Statistics:")
        print(f"  Overall hit rate: {stats['overall']['hit_rate']:.2%}")
        print(f"  Total requests: {stats['overall']['total_requests']}")
        print(f"  Content cache: {stats['content_cache']['total_entries']}/{stats['content_cache']['max_size']} entries")
        print(f"  Pattern cache: {stats['pattern_cache']['total_entries']}/{stats['pattern_cache']['max_size']} entries") 
        print(f"  Index cache: {stats['index_cache']['total_entries']}/{stats['index_cache']['max_size']} entries")
        print(f"  File hashes tracked: {stats['file_hashes_tracked']}")
    
    elif command == "warm":
        # Warm cache with common context files
        common_files = [
            "architecture.md",
            "patterns.md", 
            "authentication.md",
            "api-endpoints.md",
            "frontend-architecture.md",
            "backend-architecture.md"
        ]
        cache_manager.warm_cache(common_files)
    
    elif command == "cleanup":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        removed = cache_manager.cleanup_expired_cache(hours)
        print(f"🧹 Cleaned up {removed} expired cache entries (>{hours}h old)")
    
    elif command == "clear":
        cache_manager.content_cache.clear()
        cache_manager.pattern_cache.clear()
        cache_manager.index_cache.clear()
        print("🗑️ Cleared all caches")
    
    elif command == "export":
        metadata = cache_manager.export_cache_metadata()
        print(f"📤 Exported cache metadata to {cache_manager.cache_metadata_file}")
        print(f"  Export includes {sum(len(entries) for entries in metadata['entries'].values())} entries")
    
    else:
        print(f"Unknown command: {command}")