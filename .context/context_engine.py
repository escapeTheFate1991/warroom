"""
War Room Context Engine - Phase 3

Main orchestrator for the intelligent context management system.
Integrates session tracking, auto-loading, freshness detection, and performance optimization.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from session.session_tracker import SessionTracker
from autoload.pattern_matcher import PatternMatcher
from autoload.trigger_engine import TriggerEngine, ContextSuggestion
from freshness.drift_detector import DriftDetector
from performance.cache_manager import CacheManager


@dataclass
class ContextLoadResult:
    """Result of context loading operation."""
    contexts_loaded: List[Dict[str, Any]]
    load_time_ms: float
    cache_hits: int
    cache_misses: int
    drift_alerts: List[Dict[str, Any]]
    session_updated: bool
    recommendations: List[str]


class ContextEngine:
    """Main context management engine for War Room development."""
    
    def __init__(self, project_root: str = "/home/eddy/Development/warroom"):
        self.project_root = Path(project_root)
        self.context_dir = self.project_root / ".context"
        self.context_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all subsystems
        self.session_tracker = SessionTracker(project_root)
        self.pattern_matcher = PatternMatcher(project_root)
        self.trigger_engine = TriggerEngine(project_root)
        self.drift_detector = DriftDetector(project_root)
        self.cache_manager = CacheManager(project_root)
        
        # Engine configuration
        self.config_file = self.context_dir / "engine_config.json"
        self.config = self._load_config()
        
        print(f"🤖 Context Engine initialized for {project_root}")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load engine configuration."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration
        default_config = {
            "auto_load_enabled": True,
            "drift_detection_enabled": True,
            "cache_enabled": True,
            "session_tracking_enabled": True,
            "max_contexts_per_load": 5,
            "cache_ttl_seconds": 3600,
            "drift_scan_interval_hours": 6,
            "performance_mode": "balanced"  # "fast", "balanced", "thorough"
        }
        
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save engine configuration."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def start_session(self, task_description: str = None) -> Dict[str, Any]:
        """Start new development session with context loading."""
        if not self.config["session_tracking_enabled"]:
            return {"status": "session tracking disabled"}
        
        # Start session
        self.session_tracker.start_session(task_description)
        
        # Auto-load context for task
        result = None
        if task_description and self.config["auto_load_enabled"]:
            result = self.load_context_for_task(task_description)
        
        return {
            "session_started": True,
            "session_id": self.session_tracker.current_session["session_id"],
            "task": task_description,
            "context_loaded": result is not None,
            "context_result": result
        }
    
    def load_context_for_error(self, error_message: str, file_path: str = None) -> ContextLoadResult:
        """Load relevant context for an error with full intelligence."""
        start_time = time.time()
        
        # Get suggestions from trigger engine
        suggestions = self.trigger_engine.trigger_from_error(error_message, file_path)
        
        # Load context with caching
        contexts_loaded = []
        cache_hits = 0
        cache_misses = 0
        
        for suggestion in suggestions[:self.config["max_contexts_per_load"]]:
            # Try cache first
            cached_content = self.cache_manager.get_content(
                suggestion.file_path, 
                self.config["cache_ttl_seconds"]
            )
            
            if cached_content:
                cache_hits += 1
            else:
                cache_misses += 1
                # Content loaded by cache manager on miss
                cached_content = self.cache_manager.get_content(suggestion.file_path)
            
            if cached_content:
                contexts_loaded.append({
                    "file": suggestion.file_path,
                    "relevance_score": suggestion.relevance_score,
                    "reason": suggestion.trigger_reason,
                    "content": cached_content,
                    "cached": cache_hits > cache_misses
                })
        
        # Check for drift alerts if enabled
        drift_alerts = []
        if self.config["drift_detection_enabled"]:
            for context in contexts_loaded:
                alerts = self.drift_detector.validate_context_file(context["file"])
                drift_alerts.extend([asdict(alert) for alert in alerts])
        
        # Generate recommendations
        recommendations = self._generate_recommendations(error_message, contexts_loaded, drift_alerts)
        
        # Update session
        session_updated = False
        if self.config["session_tracking_enabled"]:
            self.session_tracker.track_error(error_message, file_path)
            for context in contexts_loaded:
                self.session_tracker.track_context_loaded("error_context", context["file"])
            session_updated = True
        
        load_time = (time.time() - start_time) * 1000
        
        return ContextLoadResult(
            contexts_loaded=contexts_loaded,
            load_time_ms=load_time,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            drift_alerts=drift_alerts,
            session_updated=session_updated,
            recommendations=recommendations
        )
    
    def load_context_for_file(self, file_path: str) -> ContextLoadResult:
        """Load relevant context for file modification."""
        start_time = time.time()
        
        suggestions = self.trigger_engine.trigger_from_file(file_path)
        
        contexts_loaded = []
        cache_hits = 0
        cache_misses = 0
        
        for suggestion in suggestions[:self.config["max_contexts_per_load"]]:
            cached_content = self.cache_manager.get_content(suggestion.file_path)
            
            if cached_content:
                if suggestion.file_path in self.cache_manager.content_cache.cache:
                    cache_hits += 1
                else:
                    cache_misses += 1
                
                contexts_loaded.append({
                    "file": suggestion.file_path,
                    "relevance_score": suggestion.relevance_score,
                    "reason": suggestion.trigger_reason,
                    "content": cached_content
                })
        
        drift_alerts = []
        if self.config["drift_detection_enabled"]:
            for context in contexts_loaded:
                alerts = self.drift_detector.validate_context_file(context["file"])
                drift_alerts.extend([asdict(alert) for alert in alerts])
        
        recommendations = self._generate_recommendations(f"file:{file_path}", contexts_loaded, drift_alerts)
        
        session_updated = False
        if self.config["session_tracking_enabled"]:
            self.session_tracker.track_file_change(file_path)
            session_updated = True
        
        load_time = (time.time() - start_time) * 1000
        
        return ContextLoadResult(
            contexts_loaded=contexts_loaded,
            load_time_ms=load_time,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            drift_alerts=drift_alerts,
            session_updated=session_updated,
            recommendations=recommendations
        )
    
    def load_context_for_task(self, task_description: str) -> ContextLoadResult:
        """Load relevant context for development task."""
        start_time = time.time()
        
        suggestions = self.trigger_engine.trigger_from_task(task_description)
        
        contexts_loaded = []
        cache_hits = 0
        cache_misses = 0
        
        for suggestion in suggestions[:self.config["max_contexts_per_load"]]:
            cached_content = self.cache_manager.get_content(suggestion.file_path)
            
            if cached_content:
                contexts_loaded.append({
                    "file": suggestion.file_path,
                    "relevance_score": suggestion.relevance_score,
                    "reason": suggestion.trigger_reason,
                    "content": cached_content
                })
        
        drift_alerts = []
        recommendations = self._generate_recommendations(f"task:{task_description}", contexts_loaded, drift_alerts)
        
        session_updated = False
        if self.config["session_tracking_enabled"]:
            self.session_tracker.set_task(task_description)
            session_updated = True
        
        load_time = (time.time() - start_time) * 1000
        
        return ContextLoadResult(
            contexts_loaded=contexts_loaded,
            load_time_ms=load_time,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            drift_alerts=drift_alerts,
            session_updated=session_updated,
            recommendations=recommendations
        )
    
    def get_session_context(self) -> ContextLoadResult:
        """Get context based on current session state."""
        start_time = time.time()
        
        suggestions = self.trigger_engine.trigger_from_session_context()
        
        contexts_loaded = []
        for suggestion in suggestions[:self.config["max_contexts_per_load"]]:
            cached_content = self.cache_manager.get_content(suggestion.file_path)
            if cached_content:
                contexts_loaded.append({
                    "file": suggestion.file_path,
                    "relevance_score": suggestion.relevance_score,
                    "reason": suggestion.trigger_reason,
                    "content": cached_content
                })
        
        load_time = (time.time() - start_time) * 1000
        
        return ContextLoadResult(
            contexts_loaded=contexts_loaded,
            load_time_ms=load_time,
            cache_hits=0,
            cache_misses=0,
            drift_alerts=[],
            session_updated=False,
            recommendations=[]
        )
    
    def _generate_recommendations(self, trigger: str, contexts: List[Dict], 
                                drift_alerts: List[Dict]) -> List[str]:
        """Generate intelligent recommendations based on loaded context."""
        recommendations = []
        
        # Recommendations based on drift alerts
        high_priority_alerts = [a for a in drift_alerts if a["severity"] >= 8]
        if high_priority_alerts:
            recommendations.append(
                f"🚨 {len(high_priority_alerts)} high-priority context updates needed"
            )
        
        # Recommendations based on context relevance
        if contexts:
            avg_relevance = sum(c["relevance_score"] for c in contexts) / len(contexts)
            if avg_relevance < 0.5:
                recommendations.append("⚠️ Low relevance context - consider updating patterns")
        
        # Recommendations based on trigger type
        if "error" in trigger.lower():
            recommendations.append("💡 Check authentication.md for auth-related errors")
        elif "file:" in trigger:
            recommendations.append("📝 Consider adding file-specific patterns")
        elif "task:" in trigger:
            recommendations.append("🎯 Update task-based context patterns for better matching")
        
        return recommendations
    
    def run_maintenance(self, force_scan: bool = False) -> Dict[str, Any]:
        """Run maintenance tasks: drift detection, cache cleanup, etc."""
        start_time = time.time()
        maintenance_results = {}
        
        # Drift detection scan
        if self.config["drift_detection_enabled"] or force_scan:
            print("🔍 Running drift detection scan...")
            scan_stats = self.drift_detector.scan_codebase_patterns(force_scan)
            maintenance_results["drift_scan"] = scan_stats
        
        # Cache cleanup
        if self.config["cache_enabled"]:
            print("🧹 Cleaning up expired cache...")
            removed_entries = self.cache_manager.cleanup_expired_cache()
            maintenance_results["cache_cleanup"] = {"removed_entries": removed_entries}
        
        # Session summary
        if self.config["session_tracking_enabled"]:
            session_summary = self.session_tracker.get_session_summary()
            maintenance_results["session_summary"] = session_summary
        
        maintenance_time = time.time() - start_time
        maintenance_results["total_time_ms"] = maintenance_time * 1000
        
        return maintenance_results
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status and health metrics."""
        # Cache statistics
        cache_stats = self.cache_manager.get_cache_stats()
        
        # Drift summary
        drift_summary = self.drift_detector.get_drift_summary()
        
        # Session info
        session_summary = self.session_tracker.get_session_summary()
        
        # Performance metrics
        performance_score = self._calculate_performance_score(cache_stats, drift_summary)
        
        return {
            "engine_config": self.config,
            "cache_performance": cache_stats,
            "context_health": drift_summary,
            "current_session": session_summary,
            "performance_score": performance_score,
            "subsystems": {
                "session_tracking": self.config["session_tracking_enabled"],
                "auto_loading": self.config["auto_load_enabled"],
                "drift_detection": self.config["drift_detection_enabled"],
                "caching": self.config["cache_enabled"]
            },
            "status_generated_at": datetime.now().isoformat()
        }
    
    def _calculate_performance_score(self, cache_stats: Dict, drift_summary: Dict) -> int:
        """Calculate overall engine performance score (0-100)."""
        score = 100
        
        # Cache performance impact
        hit_rate = cache_stats["overall"]["hit_rate"]
        if hit_rate < 0.7:
            score -= (0.7 - hit_rate) * 50
        
        # Context health impact
        health_score = drift_summary.get("context_health_score", 100)
        score = (score + health_score) / 2
        
        return max(0, int(score))
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Run performance optimization."""
        print("⚡ Optimizing context engine performance...")
        
        # Cache warming
        common_files = [
            "authentication.md", "api-endpoints.md", "database-schema.md",
            "frontend-architecture.md", "backend-architecture.md", "patterns.md"
        ]
        self.cache_manager.warm_cache(common_files)
        
        # Pattern optimization (rebuild pattern cache)
        self.cache_manager.pattern_cache.clear()
        
        # Drift detection optimization
        drift_stats = self.drift_detector.scan_codebase_patterns(force_rescan=True)
        
        return {
            "cache_warmed": len(common_files),
            "pattern_cache_cleared": True,
            "drift_scan_completed": True,
            "optimization_completed_at": datetime.now().isoformat()
        }


# CLI Interface
if __name__ == "__main__":
    import sys
    
    engine = ContextEngine()
    
    if len(sys.argv) < 2:
        print("Usage: python context_engine.py [command] [args...]")
        print("\nCommands:")
        print("  start [task]           - Start session with optional task")
        print("  error 'message'        - Load context for error")
        print("  file 'path'           - Load context for file")
        print("  task 'description'    - Load context for task")
        print("  session               - Get session-based context")
        print("  status                - Show engine status")
        print("  maintenance           - Run maintenance tasks")
        print("  optimize              - Run performance optimization")
        print("\nExamples:")
        print("  python context_engine.py error 'JWT token expired'")
        print("  python context_engine.py file 'backend/app/auth/jwt.py'")
        print("  python context_engine.py task 'fix authentication bug'")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "start":
        task = sys.argv[2] if len(sys.argv) > 2 else None
        result = engine.start_session(task)
        print(f"✅ Session started: {result['session_id']}")
        if result.get('context_loaded'):
            print(f"📄 Loaded {len(result['context_result'].contexts_loaded)} contexts")
    
    elif command == "error":
        if len(sys.argv) < 3:
            print("Error: Please provide error message")
            sys.exit(1)
        
        error_msg = sys.argv[2]
        file_path = sys.argv[3] if len(sys.argv) > 3 else None
        
        result = engine.load_context_for_error(error_msg, file_path)
        print(f"📄 Loaded {len(result.contexts_loaded)} contexts in {result.load_time_ms:.1f}ms")
        print(f"🎯 Cache hit rate: {result.cache_hits}/{result.cache_hits + result.cache_misses}")
        
        if result.drift_alerts:
            print(f"⚠️  {len(result.drift_alerts)} drift alerts detected")
        
        for context in result.contexts_loaded:
            print(f"\n  📋 {context['file']} (score: {context['relevance_score']:.2f})")
            print(f"     {context['reason']}")
    
    elif command == "file":
        if len(sys.argv) < 3:
            print("Error: Please provide file path")
            sys.exit(1)
        
        file_path = sys.argv[2]
        result = engine.load_context_for_file(file_path)
        print(f"📄 Loaded {len(result.contexts_loaded)} contexts in {result.load_time_ms:.1f}ms")
        
        for context in result.contexts_loaded:
            print(f"  📋 {context['file']} (score: {context['relevance_score']:.2f})")
    
    elif command == "task":
        if len(sys.argv) < 3:
            print("Error: Please provide task description")
            sys.exit(1)
        
        task_desc = sys.argv[2]
        result = engine.load_context_for_task(task_desc)
        print(f"📄 Loaded {len(result.contexts_loaded)} contexts in {result.load_time_ms:.1f}ms")
        
        for context in result.contexts_loaded:
            print(f"  📋 {context['file']} (score: {context['relevance_score']:.2f})")
    
    elif command == "session":
        result = engine.get_session_context()
        print(f"📄 Session context: {len(result.contexts_loaded)} contexts")
        
        for context in result.contexts_loaded:
            print(f"  📋 {context['file']} - {context['reason']}")
    
    elif command == "status":
        status = engine.get_engine_status()
        print("🤖 Context Engine Status:")
        print(f"  Performance score: {status['performance_score']}/100")
        print(f"  Cache hit rate: {status['cache_performance']['overall']['hit_rate']:.2%}")
        print(f"  Context health: {status['context_health']['context_health_score']}/100")
        print(f"  Session duration: {status['current_session']['duration_hours']:.1f}h")
        
        subsystems = status['subsystems']
        enabled_count = sum(1 for enabled in subsystems.values() if enabled)
        print(f"  Active subsystems: {enabled_count}/4")
    
    elif command == "maintenance":
        print("🔧 Running maintenance tasks...")
        results = engine.run_maintenance(force_scan=True)
        print(f"✅ Maintenance completed in {results['total_time_ms']:.1f}ms")
        
        if 'drift_scan' in results:
            scan = results['drift_scan']
            print(f"   Scanned {scan.get('files_scanned', 0)} files")
            print(f"   Found {scan.get('new_patterns', 0)} new patterns")
    
    elif command == "optimize":
        print("⚡ Running performance optimization...")
        results = engine.optimize_performance()
        print("✅ Optimization completed:")
        print(f"   Warmed cache with {results['cache_warmed']} files")
        print(f"   Pattern cache refreshed")
        print(f"   Drift detection updated")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)