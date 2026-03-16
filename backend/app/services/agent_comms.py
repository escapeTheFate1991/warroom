"""
Agent Communication Service - Network-AI Integration for War Room

This service wraps Network-AI's blackboard and swarm guard scripts to provide
a clean async API for agent-to-agent communication within War Room.

Features:
- Agent message routing via Network-AI blackboard
- Budget tracking and token metering via swarm guard
- Task result sharing for organizational knowledge
- Permission checks and handoff validation
"""

import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Network-AI configuration
NETWORK_AI_DIR = Path.home() / ".openclaw/workspace/skills/network-ai"
SCRIPTS_DIR = NETWORK_AI_DIR / "scripts"

class AgentComms:
    """Agent-to-agent communication bus using Network-AI blackboard."""
    
    @staticmethod
    async def post_message(from_agent_id: int, to_agent_id: int, org_id: int, message: str, task_id: str = None) -> dict:
        """Post a message from one agent to another via blackboard."""
        key = f"msg:org_{org_id}:agent_{to_agent_id}:from_{from_agent_id}:{task_id or 'direct'}"
        payload = json.dumps({
            "from_agent": from_agent_id,
            "to_agent": to_agent_id,
            "org_id": org_id,
            "message": message,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Write to blackboard with 1-hour TTL
        result = AgentComms._run_blackboard("write", key, payload, ttl=3600)
        return result
    
    @staticmethod
    async def read_messages(agent_id: int, org_id: int) -> list:
        """Read all pending messages for an agent."""
        # List all blackboard entries, filter for this agent
        snapshot = AgentComms._run_blackboard("snapshot")
        if not snapshot.get("success", True):
            logger.error(f"Failed to read blackboard snapshot: {snapshot}")
            return []
        
        messages = []
        prefix = f"msg:org_{org_id}:agent_{agent_id}:"
        
        # Handle both dict format (single entry) and list format (multiple entries)
        entries = snapshot if isinstance(snapshot, list) else [snapshot]
        
        for entry in entries:
            if isinstance(entry, dict) and entry.get("key", "").startswith(prefix):
                messages.append(entry)
        
        return messages
    
    @staticmethod
    async def post_task_result(org_id: int, agent_id: int, task_id: str, result: dict) -> dict:
        """Post a completed task result to the org blackboard."""
        key = f"task:org_{org_id}:completed:{task_id}"
        payload = json.dumps({
            "agent_id": agent_id,
            "org_id": org_id,
            "task_id": task_id,
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        })
        return AgentComms._run_blackboard("write", key, payload)
    
    @staticmethod
    async def get_org_completed_tasks(org_id: int) -> list:
        """Get all completed tasks for the org (shared knowledge)."""
        snapshot = AgentComms._run_blackboard("snapshot")
        if not snapshot.get("success", True):
            logger.error(f"Failed to read blackboard snapshot: {snapshot}")
            return []
        
        prefix = f"task:org_{org_id}:completed:"
        
        # Handle both dict format (single entry) and list format (multiple entries)
        entries = snapshot if isinstance(snapshot, list) else [snapshot]
        
        return [e for e in entries if isinstance(e, dict) and e.get("key", "").startswith(prefix)]
    
    @staticmethod
    async def check_budget(task_id: str) -> dict:
        """Check remaining budget for a task."""
        return AgentComms._run_swarm_guard("budget-check", task_id=task_id)
    
    @staticmethod
    async def init_budget(task_id: str, budget: int = 10000, description: str = "") -> dict:
        """Initialize token budget for a task."""
        return AgentComms._run_swarm_guard("budget-init", task_id=task_id, budget=budget, description=description)
    
    @staticmethod
    async def intercept_handoff(task_id: str, from_agent: str, to_agent: str, message: str) -> dict:
        """Check if an agent-to-agent handoff is allowed."""
        return AgentComms._run_swarm_guard("intercept-handoff", task_id=task_id, from_agent=from_agent, to_agent=to_agent, message=message)
    
    @staticmethod
    def _run_blackboard(command: str, key: str = None, value: str = None, ttl: int = None) -> dict:
        """Execute a blackboard script command."""
        cmd = ["python3", str(SCRIPTS_DIR / "blackboard.py"), command]
        if key:
            cmd.append(key)
        if value:
            cmd.append(value)
        if ttl:
            cmd.extend(["--ttl", str(ttl)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=str(NETWORK_AI_DIR))
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"output": result.stdout.strip(), "success": True}
            else:
                logger.error(f"Blackboard command failed: {result.stderr}")
                return {"error": result.stderr.strip(), "success": False}
        except subprocess.TimeoutExpired:
            logger.error("Blackboard command timed out")
            return {"error": "Command timed out", "success": False}
        except Exception as e:
            logger.error(f"Blackboard command error: {e}")
            return {"error": str(e), "success": False}
    
    @staticmethod
    def _run_swarm_guard(command: str, **kwargs) -> dict:
        """Execute a swarm_guard script command."""
        cmd = ["python3", str(SCRIPTS_DIR / "swarm_guard.py"), command]
        for k, v in kwargs.items():
            cmd.extend([f"--{k.replace('_', '-')}", str(v)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=str(NETWORK_AI_DIR))
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"output": result.stdout.strip(), "success": True}
            else:
                logger.error(f"Swarm guard command failed: {result.stderr}")
                return {"error": result.stderr.strip(), "success": False}
        except subprocess.TimeoutExpired:
            logger.error("Swarm guard command timed out")
            return {"error": "Command timed out", "success": False}
        except Exception as e:
            logger.error(f"Swarm guard command error: {e}")
            return {"error": str(e), "success": False}