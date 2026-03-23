"""
Context Drift Detection System

Detects when documented patterns drift from actual implementation.
Validates context accuracy against current code and alerts when updates are needed.
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
import subprocess
import re


@dataclass
class CodePattern:
    """Represents a code pattern found in the codebase."""
    pattern_type: str  # 'function', 'class', 'import', 'config'
    file_path: str
    pattern_name: str
    pattern_signature: str
    content_hash: str
    last_seen: str
    line_number: Optional[int] = None


@dataclass
class DriftAlert:
    """Represents a detected drift between context and code."""
    context_file: str
    drift_type: str  # 'missing_pattern', 'changed_pattern', 'new_pattern', 'outdated_context'
    description: str
    severity: int  # 1-10, 10 being critical
    suggested_action: str
    code_evidence: List[str]
    detected_at: str


class DriftDetector:
    """Detect when context documentation drifts from actual code."""
    
    def __init__(self, project_root: str = "/home/eddy/Development/warroom"):
        self.project_root = Path(project_root)
        self.context_dir = self.project_root / ".context"
        self.freshness_dir = self.context_dir / "freshness"
        self.freshness_dir.mkdir(parents=True, exist_ok=True)
        
        self.patterns_cache_file = self.freshness_dir / "code_patterns.json"
        self.drift_alerts_file = self.freshness_dir / "drift_alerts.json"
        
        self.known_patterns = self._load_known_patterns()
        self.drift_alerts = self._load_drift_alerts()
        
    def _load_known_patterns(self) -> List[CodePattern]:
        """Load previously discovered code patterns."""
        if self.patterns_cache_file.exists():
            with open(self.patterns_cache_file, 'r') as f:
                pattern_data = json.load(f)
                return [CodePattern(**p) for p in pattern_data]
        return []
    
    def _save_known_patterns(self):
        """Save discovered code patterns to cache."""
        pattern_data = [asdict(p) for p in self.known_patterns]
        with open(self.patterns_cache_file, 'w') as f:
            json.dump(pattern_data, f, indent=2)
    
    def _load_drift_alerts(self) -> List[DriftAlert]:
        """Load existing drift alerts."""
        if self.drift_alerts_file.exists():
            with open(self.drift_alerts_file, 'r') as f:
                alert_data = json.load(f)
                return [DriftAlert(**a) for a in alert_data]
        return []
    
    def _save_drift_alerts(self):
        """Save drift alerts to file."""
        alert_data = [asdict(a) for a in self.drift_alerts]
        with open(self.drift_alerts_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
    
    def scan_codebase_patterns(self, force_rescan: bool = False) -> Dict[str, int]:
        """Scan codebase for patterns and detect changes."""
        if not force_rescan and self._is_recent_scan():
            return {"status": "skipped", "reason": "recent scan exists"}
        
        stats = {
            "files_scanned": 0,
            "patterns_found": 0,
            "patterns_changed": 0,
            "new_patterns": 0
        }
        
        current_patterns = []
        
        # Scan Python files
        python_files = list(self.project_root.glob("backend/**/*.py"))
        for py_file in python_files:
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            patterns = self._scan_python_file(py_file)
            current_patterns.extend(patterns)
            stats["files_scanned"] += 1
            stats["patterns_found"] += len(patterns)
        
        # Scan TypeScript/JavaScript files
        js_files = list(self.project_root.glob("frontend/src/**/*.ts")) + \
                  list(self.project_root.glob("frontend/src/**/*.tsx"))
        for js_file in js_files:
            if "node_modules" in str(js_file) or ".next" in str(js_file):
                continue
                
            patterns = self._scan_js_file(js_file)
            current_patterns.extend(patterns)
            stats["files_scanned"] += 1
            stats["patterns_found"] += len(patterns)
        
        # Compare with known patterns to detect changes
        stats["patterns_changed"], stats["new_patterns"] = self._compare_patterns(current_patterns)
        
        # Update known patterns
        self.known_patterns = current_patterns
        self._save_known_patterns()
        
        return stats
    
    def _is_recent_scan(self) -> bool:
        """Check if a recent pattern scan exists."""
        if not self.patterns_cache_file.exists():
            return False
        
        # Check file modification time
        mod_time = datetime.fromtimestamp(self.patterns_cache_file.stat().st_mtime)
        return datetime.now() - mod_time < timedelta(hours=1)
    
    def _scan_python_file(self, file_path: Path) -> List[CodePattern]:
        """Scan Python file for patterns."""
        patterns = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            rel_path = str(file_path.relative_to(self.project_root))
            lines = content.split('\n')
            
            # Find function definitions
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Function patterns
                if line_stripped.startswith('def '):
                    func_match = re.match(r'def\s+(\w+)\s*\([^)]*\)', line_stripped)
                    if func_match:
                        func_name = func_match.group(1)
                        patterns.append(CodePattern(
                            pattern_type="function",
                            file_path=rel_path,
                            pattern_name=func_name,
                            pattern_signature=line_stripped,
                            content_hash=self._hash_string(line_stripped),
                            last_seen=datetime.now().isoformat(),
                            line_number=i + 1
                        ))
                
                # Class patterns
                elif line_stripped.startswith('class '):
                    class_match = re.match(r'class\s+(\w+)', line_stripped)
                    if class_match:
                        class_name = class_match.group(1)
                        patterns.append(CodePattern(
                            pattern_type="class",
                            file_path=rel_path,
                            pattern_name=class_name,
                            pattern_signature=line_stripped,
                            content_hash=self._hash_string(line_stripped),
                            last_seen=datetime.now().isoformat(),
                            line_number=i + 1
                        ))
                
                # Import patterns
                elif line_stripped.startswith(('import ', 'from ')):
                    patterns.append(CodePattern(
                        pattern_type="import",
                        file_path=rel_path,
                        pattern_name=line_stripped.split()[1] if 'import' in line_stripped else line_stripped.split()[1],
                        pattern_signature=line_stripped,
                        content_hash=self._hash_string(line_stripped),
                        last_seen=datetime.now().isoformat(),
                        line_number=i + 1
                    ))
        
        except Exception as e:
            print(f"Warning: Failed to scan {file_path}: {e}")
        
        return patterns
    
    def _scan_js_file(self, file_path: Path) -> List[CodePattern]:
        """Scan JavaScript/TypeScript file for patterns."""
        patterns = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            rel_path = str(file_path.relative_to(self.project_root))
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Function patterns
                func_match = re.match(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', line_stripped)
                if func_match:
                    func_name = func_match.group(1)
                    patterns.append(CodePattern(
                        pattern_type="function",
                        file_path=rel_path,
                        pattern_name=func_name,
                        pattern_signature=line_stripped,
                        content_hash=self._hash_string(line_stripped),
                        last_seen=datetime.now().isoformat(),
                        line_number=i + 1
                    ))
                
                # Arrow function patterns
                arrow_match = re.match(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=.*=>', line_stripped)
                if arrow_match:
                    func_name = arrow_match.group(1)
                    patterns.append(CodePattern(
                        pattern_type="function",
                        file_path=rel_path,
                        pattern_name=func_name,
                        pattern_signature=line_stripped,
                        content_hash=self._hash_string(line_stripped),
                        last_seen=datetime.now().isoformat(),
                        line_number=i + 1
                    ))
                
                # Component patterns (React)
                if line_stripped.startswith('export default function ') or \
                   re.match(r'const\s+\w+.*:\s*React\.FC', line_stripped):
                    comp_match = re.search(r'(?:function\s+(\w+)|const\s+(\w+))', line_stripped)
                    if comp_match:
                        comp_name = comp_match.group(1) or comp_match.group(2)
                        patterns.append(CodePattern(
                            pattern_type="component",
                            file_path=rel_path,
                            pattern_name=comp_name,
                            pattern_signature=line_stripped,
                            content_hash=self._hash_string(line_stripped),
                            last_seen=datetime.now().isoformat(),
                            line_number=i + 1
                        ))
                
                # Import patterns
                if line_stripped.startswith('import '):
                    import_match = re.match(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)', line_stripped)
                    if import_match:
                        import_source = import_match.group(1)
                        patterns.append(CodePattern(
                            pattern_type="import",
                            file_path=rel_path,
                            pattern_name=import_source,
                            pattern_signature=line_stripped,
                            content_hash=self._hash_string(line_stripped),
                            last_seen=datetime.now().isoformat(),
                            line_number=i + 1
                        ))
        
        except Exception as e:
            print(f"Warning: Failed to scan {file_path}: {e}")
        
        return patterns
    
    def _hash_string(self, text: str) -> str:
        """Generate hash for pattern content."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _compare_patterns(self, current_patterns: List[CodePattern]) -> Tuple[int, int]:
        """Compare current patterns with known patterns to detect changes."""
        known_by_key = {
            f"{p.file_path}:{p.pattern_type}:{p.pattern_name}": p 
            for p in self.known_patterns
        }
        
        current_by_key = {
            f"{p.file_path}:{p.pattern_type}:{p.pattern_name}": p 
            for p in current_patterns
        }
        
        patterns_changed = 0
        new_patterns = 0
        
        # Check for new patterns
        for key, current_pattern in current_by_key.items():
            if key not in known_by_key:
                new_patterns += 1
                self._create_drift_alert(
                    "new_pattern",
                    f"New {current_pattern.pattern_type} '{current_pattern.pattern_name}' found",
                    current_pattern
                )
            elif known_by_key[key].content_hash != current_pattern.content_hash:
                patterns_changed += 1
                self._create_drift_alert(
                    "changed_pattern", 
                    f"{current_pattern.pattern_type} '{current_pattern.pattern_name}' signature changed",
                    current_pattern,
                    old_pattern=known_by_key[key]
                )
        
        # Check for removed patterns
        for key, known_pattern in known_by_key.items():
            if key not in current_by_key:
                self._create_drift_alert(
                    "missing_pattern",
                    f"{known_pattern.pattern_type} '{known_pattern.pattern_name}' no longer found",
                    known_pattern
                )
        
        return patterns_changed, new_patterns
    
    def _create_drift_alert(self, drift_type: str, description: str, 
                           pattern: CodePattern, old_pattern: CodePattern = None):
        """Create a drift alert for detected changes."""
        severity = self._calculate_severity(drift_type, pattern)
        
        evidence = [pattern.pattern_signature]
        if old_pattern:
            evidence.append(f"Previous: {old_pattern.pattern_signature}")
        
        suggested_action = self._suggest_action(drift_type, pattern)
        
        alert = DriftAlert(
            context_file=self._find_relevant_context(pattern),
            drift_type=drift_type,
            description=description,
            severity=severity,
            suggested_action=suggested_action,
            code_evidence=evidence,
            detected_at=datetime.now().isoformat()
        )
        
        # Avoid duplicate alerts
        existing_alert = any(
            a.drift_type == drift_type and 
            a.description == description and
            datetime.now() - datetime.fromisoformat(a.detected_at) < timedelta(hours=24)
            for a in self.drift_alerts
        )
        
        if not existing_alert:
            self.drift_alerts.append(alert)
            self._save_drift_alerts()
    
    def _calculate_severity(self, drift_type: str, pattern: CodePattern) -> int:
        """Calculate severity score for drift alert."""
        base_severity = {
            "missing_pattern": 7,
            "changed_pattern": 6,
            "new_pattern": 4,
            "outdated_context": 5
        }.get(drift_type, 5)
        
        # Boost severity for auth/security related patterns
        if any(keyword in pattern.pattern_name.lower() for keyword in ['auth', 'jwt', 'token', 'security', 'password']):
            base_severity += 2
        
        # Boost severity for API endpoints
        if pattern.pattern_type in ['function'] and any(keyword in pattern.file_path for keyword in ['routes', 'api', 'endpoints']):
            base_severity += 1
        
        return min(base_severity, 10)
    
    def _suggest_action(self, drift_type: str, pattern: CodePattern) -> str:
        """Suggest action to address the drift."""
        actions = {
            "missing_pattern": f"Update context documentation to remove reference to {pattern.pattern_name}",
            "changed_pattern": f"Update context documentation for {pattern.pattern_name} to reflect new signature",
            "new_pattern": f"Add documentation for new {pattern.pattern_type} {pattern.pattern_name}",
            "outdated_context": "Review and update outdated context information"
        }
        
        return actions.get(drift_type, "Review and update context documentation")
    
    def _find_relevant_context(self, pattern: CodePattern) -> str:
        """Find the most relevant context file for a pattern."""
        # Simple heuristic - map file paths to context files
        if "auth" in pattern.file_path:
            return "authentication.md"
        elif "api" in pattern.file_path:
            return "api-endpoints.md"
        elif "models" in pattern.file_path:
            return "database-schema.md"
        elif "frontend" in pattern.file_path:
            return "frontend-architecture.md"
        elif "backend" in pattern.file_path:
            return "backend-architecture.md"
        else:
            return "general-patterns.md"
    
    def validate_context_file(self, context_file_path: str) -> List[DriftAlert]:
        """Validate a specific context file against current code."""
        alerts = []
        
        try:
            context_path = self.context_dir / context_file_path
            if not context_path.exists():
                return alerts
            
            with open(context_path, 'r') as f:
                context_content = f.read()
            
            # Find code references in context
            code_refs = re.findall(r'`([^`]+)`', context_content)  # Code in backticks
            function_refs = re.findall(r'(?:function|def)\s+(\w+)', context_content, re.IGNORECASE)
            
            # Check if referenced patterns still exist
            all_pattern_names = {p.pattern_name for p in self.known_patterns}
            
            for ref in code_refs + function_refs:
                if ref and ref not in all_pattern_names and len(ref) > 2:
                    alert = DriftAlert(
                        context_file=context_file_path,
                        drift_type="outdated_context",
                        description=f"Context references '{ref}' which no longer exists in code",
                        severity=6,
                        suggested_action=f"Remove or update reference to '{ref}' in context",
                        code_evidence=[f"Context mentions: {ref}"],
                        detected_at=datetime.now().isoformat()
                    )
                    alerts.append(alert)
        
        except Exception as e:
            print(f"Warning: Failed to validate context file {context_file_path}: {e}")
        
        return alerts
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of current drift status."""
        recent_alerts = [
            a for a in self.drift_alerts
            if datetime.now() - datetime.fromisoformat(a.detected_at) < timedelta(days=7)
        ]
        
        alert_by_severity = {}
        alert_by_type = {}
        
        for alert in recent_alerts:
            severity = alert.severity
            alert_type = alert.drift_type
            
            alert_by_severity[severity] = alert_by_severity.get(severity, 0) + 1
            alert_by_type[alert_type] = alert_by_type.get(alert_type, 0) + 1
        
        return {
            "total_patterns": len(self.known_patterns),
            "recent_alerts": len(recent_alerts),
            "alerts_by_severity": alert_by_severity,
            "alerts_by_type": alert_by_type,
            "high_priority_alerts": [a for a in recent_alerts if a.severity >= 8],
            "last_scan": max([p.last_seen for p in self.known_patterns], default="Never"),
            "context_health_score": self._calculate_health_score(recent_alerts)
        }
    
    def _calculate_health_score(self, alerts: List[DriftAlert]) -> int:
        """Calculate overall context health score (0-100)."""
        if not alerts:
            return 100
        
        penalty = sum(alert.severity for alert in alerts)
        max_possible_penalty = len(alerts) * 10
        
        health_score = max(0, 100 - int((penalty / max_possible_penalty) * 100))
        return health_score


if __name__ == "__main__":
    # CLI interface for drift detection
    import sys
    
    detector = DriftDetector()
    
    if len(sys.argv) < 2:
        print("Usage: python drift_detector.py [scan|validate|summary|alerts]")
        print("Examples:")
        print("  python drift_detector.py scan              # Scan codebase for changes")
        print("  python drift_detector.py validate auth.md  # Validate specific context file")
        print("  python drift_detector.py summary           # Show drift summary")
        print("  python drift_detector.py alerts            # Show recent alerts")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "scan":
        print("🔍 Scanning codebase for pattern changes...")
        stats = detector.scan_codebase_patterns(force_rescan=True)
        print(f"Scanned {stats['files_scanned']} files")
        print(f"Found {stats['patterns_found']} total patterns")
        print(f"Detected {stats['patterns_changed']} changed patterns")
        print(f"Found {stats['new_patterns']} new patterns")
    
    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python drift_detector.py validate <context_file>")
            sys.exit(1)
        
        context_file = sys.argv[2]
        alerts = detector.validate_context_file(context_file)
        
        if alerts:
            print(f"❌ Validation issues found in {context_file}:")
            for alert in alerts:
                print(f"  {alert.description} (severity: {alert.severity})")
                print(f"    Action: {alert.suggested_action}")
        else:
            print(f"✅ No validation issues found in {context_file}")
    
    elif command == "summary":
        summary = detector.get_drift_summary()
        print(f"📊 Context Health Summary:")
        print(f"  Total patterns tracked: {summary['total_patterns']}")
        print(f"  Recent alerts (7 days): {summary['recent_alerts']}")
        print(f"  Context health score: {summary['context_health_score']}/100")
        print(f"  Last scan: {summary['last_scan']}")
        
        if summary['high_priority_alerts']:
            print(f"\n🚨 High priority alerts ({len(summary['high_priority_alerts'])}):")
            for alert in summary['high_priority_alerts']:
                print(f"  {alert.description}")
    
    elif command == "alerts":
        recent_alerts = [
            a for a in detector.drift_alerts
            if datetime.now() - datetime.fromisoformat(a.detected_at) < timedelta(days=7)
        ]
        
        if recent_alerts:
            print("📋 Recent drift alerts:")
            for alert in sorted(recent_alerts, key=lambda a: a.severity, reverse=True):
                print(f"\n{alert.drift_type.upper()} (severity: {alert.severity})")
                print(f"  {alert.description}")
                print(f"  File: {alert.context_file}")
                print(f"  Action: {alert.suggested_action}")
        else:
            print("✅ No recent drift alerts")
    
    else:
        print(f"Unknown command: {command}")