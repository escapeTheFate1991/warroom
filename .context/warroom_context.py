#!/usr/bin/env python3
"""
War Room Context CLI

Command-line interface for the intelligent context management system.
Provides easy access to all Phase 3 functionality.
"""

import sys
import os
from pathlib import Path

# Add context modules to path
sys.path.insert(0, str(Path(__file__).parent))

from context_engine import ContextEngine
from session.session_tracker import SessionTracker
from autoload.pattern_matcher import PatternMatcher
from autoload.trigger_engine import TriggerEngine
from freshness.drift_detector import DriftDetector
from performance.cache_manager import CacheManager


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "help" or command == "--help" or command == "-h":
            show_help()
        
        elif command == "start":
            handle_start_session()
        
        elif command == "error":
            handle_error_context()
        
        elif command == "file":
            handle_file_context()
        
        elif command == "task":
            handle_task_context()
        
        elif command == "session":
            handle_session_context()
        
        elif command == "status":
            handle_status()
        
        elif command == "maintenance":
            handle_maintenance()
        
        elif command == "optimize":
            handle_optimize()
        
        elif command == "patterns":
            handle_patterns()
        
        elif command == "drift":
            handle_drift()
        
        elif command == "cache":
            handle_cache()
        
        else:
            print(f"Unknown command: {command}")
            print("Run 'warroom_context help' for usage information.")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def show_help():
    """Show help information."""
    print("""
War Room Context Management System - Phase 3

USAGE:
    python warroom_context.py <command> [arguments]

COMMANDS:
    start [task]              Start new development session
    error 'message' [file]    Load context for error message
    file 'path'              Load context for file modification  
    task 'description'       Load context for development task
    session                  Get context based on current session
    
    status                   Show engine status and health
    maintenance              Run maintenance (drift scan, cleanup)
    optimize                 Run performance optimization
    
    patterns list            List all context patterns
    patterns add             Add new context pattern
    
    drift scan               Scan for context drift
    drift alerts             Show drift alerts
    drift summary            Show drift summary
    
    cache stats              Show cache statistics
    cache warm               Warm cache with common files
    cache clear              Clear all caches

EXAMPLES:
    # Start working on authentication bug
    python warroom_context.py start "fix JWT token expiration"
    
    # Load context for specific error
    python warroom_context.py error "JWT token has expired" backend/auth/jwt.py
    
    # Load context when modifying a file
    python warroom_context.py file backend/app/auth/middleware.py
    
    # Get session-based context recommendations
    python warroom_context.py session
    
    # Check system health
    python warroom_context.py status
    
    # Run maintenance tasks
    python warroom_context.py maintenance
""")


def handle_start_session():
    """Handle session start command."""
    engine = ContextEngine()
    
    task = None
    if len(sys.argv) > 2:
        task = " ".join(sys.argv[2:])
    
    result = engine.start_session(task)
    
    print(f"🚀 Started session: {result['session_id']}")
    if task:
        print(f"📋 Task: {task}")
    
    if result.get('context_loaded'):
        context_result = result['context_result']
        print(f"📄 Auto-loaded {len(context_result.contexts_loaded)} contexts:")
        for context in context_result.contexts_loaded:
            print(f"  • {context['file']} (relevance: {context['relevance_score']:.2f})")


def handle_error_context():
    """Handle error context loading."""
    if len(sys.argv) < 3:
        print("Error: Please provide error message")
        print("Usage: python warroom_context.py error 'error message' [file_path]")
        sys.exit(1)
    
    error_message = sys.argv[2]
    file_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    engine = ContextEngine()
    result = engine.load_context_for_error(error_message, file_path)
    
    print(f"🔍 Error Context Analysis")
    print(f"📄 Loaded {len(result.contexts_loaded)} contexts in {result.load_time_ms:.1f}ms")
    
    if result.cache_hits + result.cache_misses > 0:
        hit_rate = result.cache_hits / (result.cache_hits + result.cache_misses)
        print(f"⚡ Cache hit rate: {hit_rate:.1%} ({result.cache_hits}/{result.cache_hits + result.cache_misses})")
    
    if result.contexts_loaded:
        print("\n📋 Relevant Context:")
        for context in result.contexts_loaded:
            print(f"\n  📄 {context['file']} (score: {context['relevance_score']:.2f})")
            print(f"     Reason: {context['reason']}")
            
            # Show content preview
            content = context['content']
            if len(content) > 300:
                content = content[:300] + "..."
            print(f"     Preview: {content.replace(chr(10), ' ')}")
    
    if result.drift_alerts:
        print(f"\n⚠️  Drift Alerts ({len(result.drift_alerts)}):")
        for alert in result.drift_alerts:
            print(f"  • {alert['description']} (severity: {alert['severity']})")
    
    if result.recommendations:
        print(f"\n💡 Recommendations:")
        for rec in result.recommendations:
            print(f"  • {rec}")


def handle_file_context():
    """Handle file context loading."""
    if len(sys.argv) < 3:
        print("Error: Please provide file path")
        print("Usage: python warroom_context.py file 'path/to/file'")
        sys.exit(1)
    
    file_path = sys.argv[2]
    
    engine = ContextEngine()
    result = engine.load_context_for_file(file_path)
    
    print(f"📁 File Context for: {file_path}")
    print(f"📄 Loaded {len(result.contexts_loaded)} contexts in {result.load_time_ms:.1f}ms")
    
    if result.contexts_loaded:
        print("\n📋 Relevant Context:")
        for context in result.contexts_loaded:
            print(f"  📄 {context['file']} (score: {context['relevance_score']:.2f})")
            print(f"     {context['reason']}")
    else:
        print("\n💭 No specific context patterns matched this file.")
        print("    Consider adding patterns for this file type.")


def handle_task_context():
    """Handle task context loading."""
    if len(sys.argv) < 3:
        print("Error: Please provide task description")
        print("Usage: python warroom_context.py task 'task description'")
        sys.exit(1)
    
    task_description = " ".join(sys.argv[2:])
    
    engine = ContextEngine()
    result = engine.load_context_for_task(task_description)
    
    print(f"🎯 Task Context for: {task_description}")
    print(f"📄 Loaded {len(result.contexts_loaded)} contexts in {result.load_time_ms:.1f}ms")
    
    if result.contexts_loaded:
        print("\n📋 Relevant Context:")
        for context in result.contexts_loaded:
            print(f"  📄 {context['file']} (score: {context['relevance_score']:.2f})")
            print(f"     {context['reason']}")


def handle_session_context():
    """Handle session-based context."""
    engine = ContextEngine()
    result = engine.get_session_context()
    
    session_summary = engine.session_tracker.get_session_summary()
    
    print(f"📊 Session Context")
    print(f"Session: {session_summary['session_id']} ({session_summary['duration_hours']:.1f}h)")
    print(f"Task: {session_summary['current_task'] or 'None'}")
    print(f"Branch: {session_summary['git_branch']}")
    print(f"Files modified: {session_summary['files_modified_count']}")
    print(f"Errors: {session_summary['errors_count']} ({len(session_summary['unresolved_errors'])} unresolved)")
    
    if result.contexts_loaded:
        print(f"\n📋 Session-based Context ({len(result.contexts_loaded)}):")
        for context in result.contexts_loaded:
            print(f"  📄 {context['file']} (score: {context['relevance_score']:.2f})")
            print(f"     {context['reason']}")
    
    if session_summary['recent_files']:
        print(f"\n📁 Recent Files:")
        for file_path in session_summary['recent_files']:
            print(f"  • {file_path}")


def handle_status():
    """Handle status command."""
    engine = ContextEngine()
    status = engine.get_engine_status()
    
    print("🤖 War Room Context Engine Status")
    print("=" * 40)
    
    print(f"Performance Score: {status['performance_score']}/100")
    
    cache_perf = status['cache_performance']['overall']
    print(f"Cache Hit Rate: {cache_perf['hit_rate']:.1%} ({cache_perf['total_requests']} requests)")
    
    context_health = status['context_health']
    print(f"Context Health: {context_health['context_health_score']}/100")
    print(f"Tracked Patterns: {context_health['total_patterns']}")
    print(f"Recent Alerts: {context_health['recent_alerts']}")
    
    session = status['current_session']
    print(f"\nCurrent Session: {session['session_id']} ({session['duration_hours']:.1f}h)")
    print(f"Task: {session['current_task'] or 'None'}")
    print(f"Files Modified: {session['files_modified_count']}")
    print(f"Unresolved Errors: {len(session['unresolved_errors'])}")
    
    subsystems = status['subsystems']
    enabled_subsystems = [name for name, enabled in subsystems.items() if enabled]
    print(f"\nActive Subsystems: {len(enabled_subsystems)}/4")
    for name in enabled_subsystems:
        print(f"  ✅ {name.replace('_', ' ').title()}")
    
    disabled_subsystems = [name for name, enabled in subsystems.items() if not enabled]
    for name in disabled_subsystems:
        print(f"  ❌ {name.replace('_', ' ').title()}")


def handle_maintenance():
    """Handle maintenance command."""
    engine = ContextEngine()
    
    print("🔧 Running maintenance tasks...")
    results = engine.run_maintenance(force_scan=True)
    
    print(f"✅ Maintenance completed in {results['total_time_ms']:.1f}ms")
    
    if 'drift_scan' in results:
        scan = results['drift_scan']
        print(f"   📊 Drift scan: {scan.get('files_scanned', 0)} files scanned")
        print(f"   🆕 New patterns: {scan.get('new_patterns', 0)}")
        print(f"   🔄 Changed patterns: {scan.get('patterns_changed', 0)}")
    
    if 'cache_cleanup' in results:
        cleanup = results['cache_cleanup']
        print(f"   🧹 Cache cleanup: {cleanup['removed_entries']} entries removed")
    
    if 'session_summary' in results:
        session = results['session_summary']
        print(f"   📊 Session: {session['duration_hours']:.1f}h, {session['files_modified_count']} files modified")


def handle_optimize():
    """Handle optimization command."""
    engine = ContextEngine()
    
    print("⚡ Running performance optimization...")
    results = engine.optimize_performance()
    
    print("✅ Optimization completed:")
    print(f"   🔥 Cache warmed with {results['cache_warmed']} common files")
    print(f"   🗑️  Pattern cache cleared and rebuilt")
    print(f"   🔍 Drift detection refreshed")


def handle_patterns():
    """Handle pattern commands."""
    if len(sys.argv) < 3:
        print("Usage: python warroom_context.py patterns [list|add]")
        sys.exit(1)
    
    subcommand = sys.argv[2]
    matcher = PatternMatcher()
    
    if subcommand == "list":
        print("📋 Context Patterns:")
        for pattern in matcher.patterns:
            print(f"\n  {pattern.pattern_type.upper()}: {pattern.description}")
            print(f"    Pattern: {pattern.pattern}")
            print(f"    Priority: {pattern.priority}")
            print(f"    Files: {', '.join(pattern.context_files)}")
    
    elif subcommand == "add":
        # Interactive pattern addition
        print("Adding new context pattern...")
        pattern_type = input("Pattern type (error/filepath/import/keyword): ")
        pattern = input("Pattern (regex): ")
        description = input("Description: ")
        priority = int(input("Priority (1-10): "))
        context_files = input("Context files (comma-separated): ").split(",")
        context_files = [f.strip() for f in context_files]
        
        matcher.add_pattern(pattern, pattern_type, context_files, priority, description)
        print("✅ Pattern added successfully")
    
    else:
        print(f"Unknown patterns subcommand: {subcommand}")


def handle_drift():
    """Handle drift detection commands."""
    if len(sys.argv) < 3:
        print("Usage: python warroom_context.py drift [scan|alerts|summary]")
        sys.exit(1)
    
    subcommand = sys.argv[2]
    detector = DriftDetector()
    
    if subcommand == "scan":
        print("🔍 Scanning codebase for drift...")
        stats = detector.scan_codebase_patterns(force_rescan=True)
        print(f"✅ Scanned {stats['files_scanned']} files")
        print(f"   Found {stats['patterns_found']} patterns")
        print(f"   {stats['new_patterns']} new patterns")
        print(f"   {stats['patterns_changed']} changed patterns")
    
    elif subcommand == "alerts":
        from datetime import datetime, timedelta
        recent_alerts = [
            a for a in detector.drift_alerts
            if datetime.now() - datetime.fromisoformat(a.detected_at) < timedelta(days=7)
        ]
        
        if recent_alerts:
            print(f"⚠️  Drift Alerts ({len(recent_alerts)} recent):")
            for alert in sorted(recent_alerts, key=lambda a: a.severity, reverse=True):
                print(f"\n  {alert.drift_type.upper()} (severity: {alert.severity}/10)")
                print(f"    {alert.description}")
                print(f"    File: {alert.context_file}")
                print(f"    Action: {alert.suggested_action}")
        else:
            print("✅ No recent drift alerts")
    
    elif subcommand == "summary":
        summary = detector.get_drift_summary()
        print("📊 Drift Detection Summary:")
        print(f"   Total patterns: {summary['total_patterns']}")
        print(f"   Context health: {summary['context_health_score']}/100")
        print(f"   Recent alerts: {summary['recent_alerts']}")
        print(f"   Last scan: {summary['last_scan']}")
        
        if summary['high_priority_alerts']:
            print(f"\n🚨 High Priority Alerts ({len(summary['high_priority_alerts'])}):")
            for alert in summary['high_priority_alerts']:
                print(f"   • {alert.description}")
    
    else:
        print(f"Unknown drift subcommand: {subcommand}")


def handle_cache():
    """Handle cache commands."""
    if len(sys.argv) < 3:
        print("Usage: python warroom_context.py cache [stats|warm|clear]")
        sys.exit(1)
    
    subcommand = sys.argv[2]
    cache_manager = CacheManager()
    
    if subcommand == "stats":
        stats = cache_manager.get_cache_stats()
        print("📊 Cache Statistics:")
        print(f"   Overall hit rate: {stats['overall']['hit_rate']:.1%}")
        print(f"   Total requests: {stats['overall']['total_requests']}")
        print(f"\n   Content cache: {stats['content_cache']['total_entries']}/{stats['content_cache']['max_size']}")
        print(f"   Pattern cache: {stats['pattern_cache']['total_entries']}/{stats['pattern_cache']['max_size']}")
        print(f"   Index cache: {stats['index_cache']['total_entries']}/{stats['index_cache']['max_size']}")
        print(f"\n   File hashes tracked: {stats['file_hashes_tracked']}")
    
    elif subcommand == "warm":
        common_files = [
            "authentication.md", "api-endpoints.md", "database-schema.md",
            "frontend-architecture.md", "backend-architecture.md", "patterns.md"
        ]
        cache_manager.warm_cache(common_files)
    
    elif subcommand == "clear":
        cache_manager.content_cache.clear()
        cache_manager.pattern_cache.clear() 
        cache_manager.index_cache.clear()
        print("🗑️ All caches cleared")
    
    else:
        print(f"Unknown cache subcommand: {subcommand}")


if __name__ == "__main__":
    main()