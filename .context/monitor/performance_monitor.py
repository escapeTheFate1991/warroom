#!/usr/bin/env python3
"""
Performance Monitor - Context system quality metrics and optimization

Monitors and optimizes the War Room context management system:
- Context quality metrics and degradation detection
- Usage analytics and pattern identification  
- System health monitoring and alerts
- Performance optimization recommendations

Integrates with War Room's monitoring infrastructure.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import statistics

import click
import aiofiles
import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.services.vector_memory import search_memory, get_memory_stats, health_check

logger = logging.getLogger(__name__)

@dataclass
class QualityMetric:
    """Quality metric measurement."""
    name: str
    value: float
    threshold: float
    status: str  # good, warning, critical
    timestamp: str
    details: Dict[str, Any]

@dataclass
class UsagePattern:
    """Usage pattern analysis."""
    pattern_type: str
    frequency: int
    success_rate: float
    avg_response_time: float
    common_queries: List[str]

@dataclass
class PerformanceAlert:
    """Performance alert."""
    severity: str  # low, medium, high, critical
    component: str
    message: str
    recommendation: str
    timestamp: str
    metrics: Dict[str, Any]


class PerformanceMonitor:
    """Context system performance monitoring and optimization."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.context_dir = self.project_root / ".context"
        self.monitor_dir = self.context_dir / "monitor"
        self.monitor_dir.mkdir(exist_ok=True)
        
        # Monitoring state
        self.metrics_history = []
        self.alerts_history = []
        
    async def collect_quality_metrics(self, org_id: str = "1") -> List[QualityMetric]:
        """Collect comprehensive quality metrics."""
        metrics = []
        timestamp = datetime.utcnow().isoformat()
        
        # Context coverage metric
        coverage_metric = await self._measure_context_coverage(org_id, timestamp)
        metrics.append(coverage_metric)
        
        # Context freshness metric
        freshness_metric = await self._measure_context_freshness(org_id, timestamp)
        metrics.append(freshness_metric)
        
        # Usage effectiveness metric
        effectiveness_metric = await self._measure_usage_effectiveness(org_id, timestamp)
        metrics.append(effectiveness_metric)
        
        # System health metric
        health_metric = await self._measure_system_health(timestamp)
        metrics.append(health_metric)
        
        # Session quality metric
        session_metric = await self._measure_session_quality(timestamp)
        metrics.append(session_metric)
        
        # AI generation quality metric
        ai_quality_metric = await self._measure_ai_quality(org_id, timestamp)
        metrics.append(ai_quality_metric)
        
        # Store metrics history
        self.metrics_history.extend(metrics)
        await self._store_metrics(metrics)
        
        return metrics
    
    async def analyze_usage_patterns(self, org_id: str = "1", days: int = 7) -> List[UsagePattern]:
        """Analyze context usage patterns."""
        patterns = []
        
        # Search for context requests in the last N days
        try:
            context_requests = await search_memory(org_id, "context_request", limit=100, score_threshold=0.1)
            
            # Group by request type
            request_types = {}
            for hit in context_requests:
                metadata = hit.get("payload", {}).get("metadata", {})
                context_type = metadata.get("context_type", "unknown")
                timestamp = metadata.get("timestamp", 0)
                
                # Filter by time window
                if time.time() - timestamp > days * 24 * 3600:
                    continue
                
                if context_type not in request_types:
                    request_types[context_type] = {
                        "requests": [],
                        "queries": []
                    }
                
                request_types[context_type]["requests"].append(metadata)
                request_types[context_type]["queries"].append(
                    metadata.get("request", "unknown")[:50]
                )
            
            # Analyze patterns for each type
            for context_type, data in request_types.items():
                if len(data["requests"]) < 3:  # Skip low-frequency patterns
                    continue
                
                pattern = UsagePattern(
                    pattern_type=context_type,
                    frequency=len(data["requests"]),
                    success_rate=self._calculate_success_rate(data["requests"]),
                    avg_response_time=self._calculate_avg_response_time(data["requests"]),
                    common_queries=list(set(data["queries"]))[:5]
                )
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"Error analyzing usage patterns: {e}")
        
        return patterns
    
    async def detect_performance_issues(self, metrics: List[QualityMetric], patterns: List[UsagePattern]) -> List[PerformanceAlert]:
        """Detect performance issues and generate alerts."""
        alerts = []
        timestamp = datetime.utcnow().isoformat()
        
        # Check quality metrics for issues
        for metric in metrics:
            if metric.status == "critical":
                alert = PerformanceAlert(
                    severity="critical",
                    component=metric.name,
                    message=f"{metric.name} is critically low: {metric.value:.2f} < {metric.threshold}",
                    recommendation=self._get_metric_recommendation(metric),
                    timestamp=timestamp,
                    metrics={"metric_value": metric.value, "threshold": metric.threshold}
                )
                alerts.append(alert)
            elif metric.status == "warning":
                alert = PerformanceAlert(
                    severity="medium",
                    component=metric.name,
                    message=f"{metric.name} is below optimal: {metric.value:.2f}",
                    recommendation=self._get_metric_recommendation(metric),
                    timestamp=timestamp,
                    metrics={"metric_value": metric.value, "threshold": metric.threshold}
                )
                alerts.append(alert)
        
        # Check usage patterns for issues
        for pattern in patterns:
            if pattern.success_rate < 0.7:
                alert = PerformanceAlert(
                    severity="high",
                    component="usage_effectiveness",
                    message=f"{pattern.pattern_type} has low success rate: {pattern.success_rate:.2f}",
                    recommendation=f"Review {pattern.pattern_type} context quality and relevance",
                    timestamp=timestamp,
                    metrics={
                        "pattern_type": pattern.pattern_type,
                        "success_rate": pattern.success_rate,
                        "frequency": pattern.frequency
                    }
                )
                alerts.append(alert)
            
            if pattern.avg_response_time > 5.0:  # 5 seconds threshold
                alert = PerformanceAlert(
                    severity="medium",
                    component="response_time",
                    message=f"{pattern.pattern_type} has slow response time: {pattern.avg_response_time:.2f}s",
                    recommendation="Optimize context loading and semantic search performance",
                    timestamp=timestamp,
                    metrics={
                        "pattern_type": pattern.pattern_type,
                        "avg_response_time": pattern.avg_response_time
                    }
                )
                alerts.append(alert)
        
        # Store alerts
        self.alerts_history.extend(alerts)
        await self._store_alerts(alerts)
        
        return alerts
    
    async def generate_optimization_recommendations(self, metrics: List[QualityMetric], patterns: List[UsagePattern]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Coverage optimization
        coverage_metric = next((m for m in metrics if m.name == "context_coverage"), None)
        if coverage_metric and coverage_metric.value < 0.8:
            recommendations.append({
                "type": "coverage_improvement",
                "priority": "high",
                "title": "Improve Context Coverage",
                "description": f"Context coverage is {coverage_metric.value:.2f}, target is 0.8+",
                "actions": [
                    "Run semantic indexing on unindexed files",
                    "Update context documentation for key modules",
                    "Add missing API endpoint documentation"
                ],
                "estimated_impact": "high",
                "effort": "medium"
            })
        
        # Freshness optimization
        freshness_metric = next((m for m in metrics if m.name == "context_freshness"), None)
        if freshness_metric and freshness_metric.value < 0.7:
            recommendations.append({
                "type": "freshness_improvement", 
                "priority": "medium",
                "title": "Update Stale Context",
                "description": f"Context freshness is {freshness_metric.value:.2f}, some context is outdated",
                "actions": [
                    "Re-index recently modified files",
                    "Update auto-generated documentation",
                    "Validate context accuracy"
                ],
                "estimated_impact": "medium",
                "effort": "low"
            })
        
        # Usage effectiveness optimization
        low_success_patterns = [p for p in patterns if p.success_rate < 0.7]
        if low_success_patterns:
            recommendations.append({
                "type": "effectiveness_improvement",
                "priority": "high",
                "title": "Improve Context Relevance",
                "description": f"{len(low_success_patterns)} request types have low success rates",
                "actions": [
                    "Review and improve semantic search thresholds",
                    "Enhance context classification accuracy",
                    "Add more targeted context sources"
                ],
                "estimated_impact": "high",
                "effort": "high",
                "affected_patterns": [p.pattern_type for p in low_success_patterns]
            })
        
        # Performance optimization
        slow_patterns = [p for p in patterns if p.avg_response_time > 3.0]
        if slow_patterns:
            recommendations.append({
                "type": "performance_optimization",
                "priority": "medium",
                "title": "Optimize Response Time",
                "description": f"{len(slow_patterns)} request types have slow response times",
                "actions": [
                    "Optimize vector search queries",
                    "Add caching for common requests",
                    "Improve embedding generation performance"
                ],
                "estimated_impact": "medium",
                "effort": "medium",
                "affected_patterns": [p.pattern_type for p in slow_patterns]
            })
        
        # AI quality optimization
        ai_metric = next((m for m in metrics if m.name == "ai_generation_quality"), None)
        if ai_metric and ai_metric.value < 0.8:
            recommendations.append({
                "type": "ai_quality_improvement",
                "priority": "medium",
                "title": "Improve AI Generation Quality",
                "description": f"AI generation quality is {ai_metric.value:.2f}, below target",
                "actions": [
                    "Review and improve pattern recognition algorithms",
                    "Update training data for context generation",
                    "Implement human feedback loops"
                ],
                "estimated_impact": "high",
                "effort": "high"
            })
        
        return recommendations
    
    async def create_performance_report(self, org_id: str = "1") -> Dict[str, Any]:
        """Create comprehensive performance report."""
        report_timestamp = datetime.utcnow().isoformat()
        
        # Collect current metrics
        metrics = await self.collect_quality_metrics(org_id)
        
        # Analyze usage patterns
        patterns = await self.analyze_usage_patterns(org_id)
        
        # Detect issues
        alerts = await self.detect_performance_issues(metrics, patterns)
        
        # Generate recommendations
        recommendations = await self.generate_optimization_recommendations(metrics, patterns)
        
        # Calculate trends
        trends = await self._calculate_metric_trends()
        
        # Create report
        report = {
            "timestamp": report_timestamp,
            "summary": {
                "overall_health": self._calculate_overall_health(metrics),
                "total_alerts": len(alerts),
                "critical_alerts": len([a for a in alerts if a.severity == "critical"]),
                "high_priority_recommendations": len([r for r in recommendations if r["priority"] == "high"])
            },
            "quality_metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "status": m.status,
                    "threshold": m.threshold,
                    "details": m.details
                }
                for m in metrics
            ],
            "usage_patterns": [
                {
                    "type": p.pattern_type,
                    "frequency": p.frequency,
                    "success_rate": p.success_rate,
                    "avg_response_time": p.avg_response_time,
                    "common_queries": p.common_queries
                }
                for p in patterns
            ],
            "alerts": [
                {
                    "severity": a.severity,
                    "component": a.component,
                    "message": a.message,
                    "recommendation": a.recommendation,
                    "metrics": a.metrics
                }
                for a in alerts
            ],
            "recommendations": recommendations,
            "trends": trends,
            "system_info": await self._get_system_info(org_id)
        }
        
        # Save report
        await self._save_performance_report(report)
        
        return report
    
    async def _measure_context_coverage(self, org_id: str, timestamp: str) -> QualityMetric:
        """Measure context coverage quality."""
        try:
            # Count indexed files vs total files
            code_memories = await search_memory(org_id, "code:", limit=200, score_threshold=0.1)
            
            # Count total relevant files
            python_files = len(list(self.project_root.glob("backend/**/*.py")))
            typescript_files = len(list(self.project_root.glob("frontend/**/*.{ts,tsx}")))
            sql_files = len(list(self.project_root.glob("backend/app/db/*.sql")))
            
            total_files = python_files + typescript_files + sql_files
            indexed_files = len(code_memories)
            
            coverage_ratio = indexed_files / total_files if total_files > 0 else 0.0
            
            status = "good" if coverage_ratio >= 0.8 else "warning" if coverage_ratio >= 0.6 else "critical"
            
            return QualityMetric(
                name="context_coverage",
                value=coverage_ratio,
                threshold=0.8,
                status=status,
                timestamp=timestamp,
                details={
                    "indexed_files": indexed_files,
                    "total_files": total_files,
                    "python_files": python_files,
                    "typescript_files": typescript_files,
                    "sql_files": sql_files
                }
            )
            
        except Exception as e:
            logger.error(f"Error measuring context coverage: {e}")
            return QualityMetric(
                name="context_coverage",
                value=0.0,
                threshold=0.8,
                status="critical",
                timestamp=timestamp,
                details={"error": str(e)}
            )
    
    async def _measure_context_freshness(self, org_id: str, timestamp: str) -> QualityMetric:
        """Measure context freshness quality."""
        try:
            # Check age of indexed content
            code_memories = await search_memory(org_id, "code:", limit=50, score_threshold=0.1)
            
            if not code_memories:
                return QualityMetric(
                    name="context_freshness",
                    value=0.0,
                    threshold=0.7,
                    status="critical",
                    timestamp=timestamp,
                    details={"reason": "no_indexed_content"}
                )
            
            # Calculate average age
            now = datetime.utcnow()
            ages = []
            
            for hit in code_memories:
                metadata = hit.get("payload", {}).get("metadata", {})
                indexed_at = metadata.get("indexed_at")
                
                if indexed_at:
                    try:
                        indexed_time = datetime.fromisoformat(indexed_at.replace('Z', '+00:00'))
                        age_hours = (now - indexed_time).total_seconds() / 3600
                        ages.append(age_hours)
                    except:
                        pass
            
            if not ages:
                avg_age_hours = 168  # Assume 1 week old
            else:
                avg_age_hours = statistics.mean(ages)
            
            # Convert to freshness score (1.0 = fresh, 0.0 = very old)
            # Fresh content (< 24 hours) = 1.0
            # Week old content = 0.7
            # Month old content = 0.3
            if avg_age_hours < 24:
                freshness = 1.0
            elif avg_age_hours < 168:  # 1 week
                freshness = 1.0 - (avg_age_hours - 24) / (168 - 24) * 0.3
            elif avg_age_hours < 720:  # 1 month
                freshness = 0.7 - (avg_age_hours - 168) / (720 - 168) * 0.4
            else:
                freshness = 0.3
            
            status = "good" if freshness >= 0.7 else "warning" if freshness >= 0.5 else "critical"
            
            return QualityMetric(
                name="context_freshness",
                value=freshness,
                threshold=0.7,
                status=status,
                timestamp=timestamp,
                details={
                    "avg_age_hours": avg_age_hours,
                    "samples_analyzed": len(ages),
                    "oldest_content_hours": max(ages) if ages else 0,
                    "freshest_content_hours": min(ages) if ages else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error measuring context freshness: {e}")
            return QualityMetric(
                name="context_freshness",
                value=0.0,
                threshold=0.7,
                status="critical",
                timestamp=timestamp,
                details={"error": str(e)}
            )
    
    async def _measure_usage_effectiveness(self, org_id: str, timestamp: str) -> QualityMetric:
        """Measure context usage effectiveness."""
        try:
            # Search for recent context requests and their outcomes
            requests = await search_memory(org_id, "context_request", limit=50, score_threshold=0.1)
            
            if not requests:
                return QualityMetric(
                    name="usage_effectiveness",
                    value=0.5,  # Neutral score when no data
                    threshold=0.7,
                    status="warning",
                    timestamp=timestamp,
                    details={"reason": "insufficient_data"}
                )
            
            # Analyze request success (simplified heuristic)
            successful_requests = 0
            total_requests = len(requests)
            
            for hit in requests:
                metadata = hit.get("payload", {}).get("metadata", {})
                sources_count = metadata.get("sources_count", 0)
                
                # Consider successful if context sources were found
                if sources_count > 0:
                    successful_requests += 1
            
            effectiveness = successful_requests / total_requests if total_requests > 0 else 0.0
            
            status = "good" if effectiveness >= 0.7 else "warning" if effectiveness >= 0.5 else "critical"
            
            return QualityMetric(
                name="usage_effectiveness",
                value=effectiveness,
                threshold=0.7,
                status=status,
                timestamp=timestamp,
                details={
                    "successful_requests": successful_requests,
                    "total_requests": total_requests,
                    "success_rate": effectiveness
                }
            )
            
        except Exception as e:
            logger.error(f"Error measuring usage effectiveness: {e}")
            return QualityMetric(
                name="usage_effectiveness",
                value=0.0,
                threshold=0.7,
                status="critical",
                timestamp=timestamp,
                details={"error": str(e)}
            )
    
    async def _measure_system_health(self, timestamp: str) -> QualityMetric:
        """Measure overall system health."""
        try:
            # Check vector memory health
            health_status = await health_check()
            
            if health_status.get("status") == "healthy":
                health_score = 1.0
                status = "good"
                details = {"vector_memory": "healthy"}
            else:
                health_score = 0.0
                status = "critical"
                details = {"vector_memory": "unhealthy", "error": health_status.get("error")}
            
            return QualityMetric(
                name="system_health",
                value=health_score,
                threshold=0.9,
                status=status,
                timestamp=timestamp,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Error measuring system health: {e}")
            return QualityMetric(
                name="system_health",
                value=0.0,
                threshold=0.9,
                status="critical",
                timestamp=timestamp,
                details={"error": str(e)}
            )
    
    async def _measure_session_quality(self, timestamp: str) -> QualityMetric:
        """Measure session management quality."""
        try:
            session_file = self.context_dir / "sessions" / "current.json"
            
            if not session_file.exists():
                return QualityMetric(
                    name="session_quality",
                    value=0.5,  # Neutral when no session
                    threshold=0.7,
                    status="warning",
                    timestamp=timestamp,
                    details={"reason": "no_active_session"}
                )
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Analyze session quality factors
            quality_factors = []
            details = {}
            
            # Context quality from session
            session_quality = session_data.get("context_quality", 0.5)
            quality_factors.append(session_quality)
            details["session_context_quality"] = session_quality
            
            # Error resolution rate
            errors = session_data.get("error_patterns", [])
            resolved_errors = [e for e in errors if e.get("resolved", False)]
            error_resolution_rate = len(resolved_errors) / len(errors) if errors else 1.0
            quality_factors.append(error_resolution_rate)
            details["error_resolution_rate"] = error_resolution_rate
            
            # Session age impact
            started_at = datetime.fromisoformat(session_data.get("started_at", ""))
            session_age_hours = (datetime.utcnow() - started_at).total_seconds() / 3600
            age_score = 1.0 if session_age_hours < 8 else 0.7 if session_age_hours < 24 else 0.3
            quality_factors.append(age_score)
            details["session_age_hours"] = session_age_hours
            details["age_score"] = age_score
            
            # Overall session quality
            overall_quality = statistics.mean(quality_factors)
            status = "good" if overall_quality >= 0.7 else "warning" if overall_quality >= 0.5 else "critical"
            
            return QualityMetric(
                name="session_quality",
                value=overall_quality,
                threshold=0.7,
                status=status,
                timestamp=timestamp,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Error measuring session quality: {e}")
            return QualityMetric(
                name="session_quality",
                value=0.0,
                threshold=0.7,
                status="critical",
                timestamp=timestamp,
                details={"error": str(e)}
            )
    
    async def _measure_ai_quality(self, org_id: str, timestamp: str) -> QualityMetric:
        """Measure AI generation quality."""
        try:
            # Search for AI-generated content and analyze quality indicators
            ai_analyses = await search_memory(org_id, "ai_analysis", limit=20, score_threshold=0.1)
            
            if not ai_analyses:
                return QualityMetric(
                    name="ai_generation_quality",
                    value=0.5,  # Neutral when no AI content
                    threshold=0.8,
                    status="warning",
                    timestamp=timestamp,
                    details={"reason": "no_ai_content"}
                )
            
            # Analyze confidence scores from AI analyses
            confidence_scores = []
            for hit in ai_analyses:
                metadata = hit.get("payload", {}).get("metadata", {})
                confidence = metadata.get("confidence", 0.5)
                confidence_scores.append(confidence)
            
            if not confidence_scores:
                avg_confidence = 0.5
            else:
                avg_confidence = statistics.mean(confidence_scores)
            
            status = "good" if avg_confidence >= 0.8 else "warning" if avg_confidence >= 0.6 else "critical"
            
            return QualityMetric(
                name="ai_generation_quality",
                value=avg_confidence,
                threshold=0.8,
                status=status,
                timestamp=timestamp,
                details={
                    "avg_confidence": avg_confidence,
                    "samples_analyzed": len(confidence_scores),
                    "min_confidence": min(confidence_scores) if confidence_scores else 0,
                    "max_confidence": max(confidence_scores) if confidence_scores else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error measuring AI quality: {e}")
            return QualityMetric(
                name="ai_generation_quality",
                value=0.0,
                threshold=0.8,
                status="critical",
                timestamp=timestamp,
                details={"error": str(e)}
            )
    
    def _calculate_success_rate(self, requests: List[Dict[str, Any]]) -> float:
        """Calculate success rate from request metadata."""
        if not requests:
            return 0.0
        
        successful = sum(1 for req in requests if req.get("sources_count", 0) > 0)
        return successful / len(requests)
    
    def _calculate_avg_response_time(self, requests: List[Dict[str, Any]]) -> float:
        """Calculate average response time (simulated)."""
        # This would need actual timing data in practice
        return 1.5  # Placeholder
    
    def _get_metric_recommendation(self, metric: QualityMetric) -> str:
        """Get recommendation for improving a metric."""
        recommendations = {
            "context_coverage": "Run semantic indexing on unindexed files and update documentation",
            "context_freshness": "Re-index recently modified files and update stale context",
            "usage_effectiveness": "Improve context relevance and search accuracy",
            "system_health": "Check service health and restart if necessary",
            "session_quality": "Review session objectives and resolve pending errors",
            "ai_generation_quality": "Review AI patterns and improve training data"
        }
        
        return recommendations.get(metric.name, "Review and optimize this component")
    
    def _calculate_overall_health(self, metrics: List[QualityMetric]) -> str:
        """Calculate overall system health status."""
        if not metrics:
            return "unknown"
        
        critical_count = sum(1 for m in metrics if m.status == "critical")
        warning_count = sum(1 for m in metrics if m.status == "warning")
        good_count = sum(1 for m in metrics if m.status == "good")
        
        if critical_count > 0:
            return "critical"
        elif warning_count > good_count:
            return "warning"
        else:
            return "good"
    
    async def _calculate_metric_trends(self) -> Dict[str, Any]:
        """Calculate metric trends over time."""
        # This would analyze historical data
        # For now, return placeholder trends
        return {
            "context_coverage": {"trend": "stable", "change_7d": 0.02},
            "context_freshness": {"trend": "improving", "change_7d": 0.15},
            "usage_effectiveness": {"trend": "declining", "change_7d": -0.08}
        }
    
    async def _get_system_info(self, org_id: str) -> Dict[str, Any]:
        """Get system information."""
        try:
            memory_stats = await get_memory_stats(org_id)
            return {
                "vector_memory": memory_stats,
                "context_dir_size": self._get_directory_size(self.context_dir),
                "python_version": sys.version,
                "platform": sys.platform
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get directory size in bytes."""
        total_size = 0
        try:
            for path in directory.rglob('*'):
                if path.is_file():
                    total_size += path.stat().st_size
        except Exception:
            pass
        return total_size
    
    async def _store_metrics(self, metrics: List[QualityMetric]):
        """Store metrics to disk."""
        try:
            metrics_file = self.monitor_dir / "metrics_history.jsonl"
            
            async with aiofiles.open(metrics_file, 'a') as f:
                for metric in metrics:
                    metric_data = {
                        "name": metric.name,
                        "value": metric.value,
                        "threshold": metric.threshold,
                        "status": metric.status,
                        "timestamp": metric.timestamp,
                        "details": metric.details
                    }
                    await f.write(json.dumps(metric_data) + '\n')
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    async def _store_alerts(self, alerts: List[PerformanceAlert]):
        """Store alerts to disk."""
        try:
            alerts_file = self.monitor_dir / "alerts_history.jsonl"
            
            async with aiofiles.open(alerts_file, 'a') as f:
                for alert in alerts:
                    alert_data = {
                        "severity": alert.severity,
                        "component": alert.component,
                        "message": alert.message,
                        "recommendation": alert.recommendation,
                        "timestamp": alert.timestamp,
                        "metrics": alert.metrics
                    }
                    await f.write(json.dumps(alert_data) + '\n')
        except Exception as e:
            logger.error(f"Error storing alerts: {e}")
    
    async def _save_performance_report(self, report: Dict[str, Any]):
        """Save performance report to disk."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            report_file = self.monitor_dir / f"performance_report_{timestamp}.json"
            
            async with aiofiles.open(report_file, 'w') as f:
                await f.write(json.dumps(report, indent=2))
                
            # Also save as latest report
            latest_file = self.monitor_dir / "latest_report.json"
            async with aiofiles.open(latest_file, 'w') as f:
                await f.write(json.dumps(report, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving performance report: {e}")


@click.command()
@click.option('--collect-metrics', is_flag=True, help='Collect quality metrics')
@click.option('--analyze-patterns', is_flag=True, help='Analyze usage patterns')
@click.option('--detect-issues', is_flag=True, help='Detect performance issues')
@click.option('--generate-report', is_flag=True, help='Generate full performance report')
@click.option('--monitor', is_flag=True, help='Continuous monitoring mode')
@click.option('--days', type=int, default=7, help='Days to analyze (default: 7)')
@click.option('--org-id', default="1", help='Organization ID')
def main(collect_metrics, analyze_patterns, detect_issues, generate_report, monitor, days, org_id):
    """War Room Performance Monitor - Context system quality metrics"""
    
    async def run():
        monitor_instance = PerformanceMonitor()
        
        if collect_metrics:
            metrics = await monitor_instance.collect_quality_metrics(org_id)
            click.echo(f"Collected {len(metrics)} quality metrics:")
            for metric in metrics:
                click.echo(f"  {metric.name}: {metric.value:.3f} ({metric.status})")
        
        elif analyze_patterns:
            patterns = await monitor_instance.analyze_usage_patterns(org_id, days)
            click.echo(f"Found {len(patterns)} usage patterns:")
            for pattern in patterns:
                click.echo(f"  {pattern.pattern_type}: {pattern.frequency} requests, {pattern.success_rate:.1%} success")
        
        elif detect_issues:
            metrics = await monitor_instance.collect_quality_metrics(org_id)
            patterns = await monitor_instance.analyze_usage_patterns(org_id, days)
            alerts = await monitor_instance.detect_performance_issues(metrics, patterns)
            
            click.echo(f"Detected {len(alerts)} performance issues:")
            for alert in alerts:
                click.echo(f"  [{alert.severity}] {alert.component}: {alert.message}")
        
        elif generate_report:
            report = await monitor_instance.create_performance_report(org_id)
            click.echo("Performance report generated:")
            click.echo(f"  Overall health: {report['summary']['overall_health']}")
            click.echo(f"  Total alerts: {report['summary']['total_alerts']}")
            click.echo(f"  High priority recommendations: {report['summary']['high_priority_recommendations']}")
            
        elif monitor:
            click.echo("Starting continuous monitoring...")
            while True:
                try:
                    metrics = await monitor_instance.collect_quality_metrics(org_id)
                    patterns = await monitor_instance.analyze_usage_patterns(org_id, 1)  # Last 24 hours
                    alerts = await monitor_instance.detect_performance_issues(metrics, patterns)
                    
                    critical_alerts = [a for a in alerts if a.severity == "critical"]
                    if critical_alerts:
                        click.echo(f"CRITICAL: {len(critical_alerts)} critical alerts detected!")
                        for alert in critical_alerts:
                            click.echo(f"  {alert.component}: {alert.message}")
                    
                    await asyncio.sleep(300)  # Check every 5 minutes
                    
                except KeyboardInterrupt:
                    click.echo("Monitoring stopped")
                    break
                except Exception as e:
                    click.echo(f"Monitoring error: {e}")
                    await asyncio.sleep(60)
        
        else:
            click.echo("Specify --collect-metrics, --analyze-patterns, --detect-issues, --generate-report, or --monitor")
    
    asyncio.run(run())


if __name__ == "__main__":
    main()