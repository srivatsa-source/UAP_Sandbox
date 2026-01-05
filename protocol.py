"""
UAP Protocol - State Manager
Handles Agent Context Token (ACT) creation, updates, and persistence.
The ACT is the "state packet" that enables LLM-to-LLM handoffs without user re-prompting.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Optional
from pathlib import Path


class ACT:
    """
    Agent Context Token - The persistent state packet for agent handoffs.
    Think of it as a "session passport" that any agent can read and continue from.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        
        # Core state fields
        self.task_chain: list[dict] = []  # History of tasks in this session
        self.current_objective: str = ""  # What we're trying to accomplish
        self.context_summary: str = ""  # Compressed context for the next agent
        
        # Handoff metadata
        self.origin_agent: str = ""  # Who created/last touched this ACT
        self.handoff_reason: str = ""  # Why we're passing to another agent
        self.next_agent_hint: str = ""  # Suggested next agent type
        
        # Artifacts - concrete outputs agents produce
        self.artifacts: dict[str, Any] = {
            "code_snippets": [],  # For DockDesk use case
            "game_state": {},     # For One-Hit Samurai use case
            "decisions": [],      # Key decisions made
            "files_modified": []  # Track file changes
        }
        
        # Validation tracking
        self.handshake_log: list[dict] = []  # Log of all agent touches
    
    def to_dict(self) -> dict:
        """Serialize ACT to dictionary for JSON export."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "task_chain": self.task_chain,
            "current_objective": self.current_objective,
            "context_summary": self.context_summary,
            "origin_agent": self.origin_agent,
            "handoff_reason": self.handoff_reason,
            "next_agent_hint": self.next_agent_hint,
            "artifacts": self.artifacts,
            "handshake_log": self.handshake_log
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ACT":
        """Deserialize ACT from dictionary."""
        act = cls(session_id=data.get("session_id"))
        act.created_at = data.get("created_at", act.created_at)
        act.updated_at = data.get("updated_at", act.updated_at)
        act.task_chain = data.get("task_chain", [])
        act.current_objective = data.get("current_objective", "")
        act.context_summary = data.get("context_summary", "")
        act.origin_agent = data.get("origin_agent", "")
        act.handoff_reason = data.get("handoff_reason", "")
        act.next_agent_hint = data.get("next_agent_hint", "")
        act.artifacts = data.get("artifacts", act.artifacts)
        act.handshake_log = data.get("handshake_log", [])
        return act


class StateManager:
    """
    Manages ACT lifecycle: create, update, persist, load.
    Acts as the central registry for all active sessions.
    """
    
    def __init__(self, storage_dir: str = "./act_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.active_sessions: dict[str, ACT] = {}
    
    def create_session(self, initial_objective: str = "") -> ACT:
        """Create a new ACT session."""
        act = ACT()
        act.current_objective = initial_objective
        self.active_sessions[act.session_id] = act
        return act
    
    def get_session(self, session_id: str) -> Optional[ACT]:
        """Retrieve an active session or load from storage."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Try loading from disk
        return self.load_session(session_id)
    
    def apply_state_updates(self, session_id: str, state_updates: dict, agent_id: str) -> ACT:
        """
        Apply state updates from an agent's response.
        This is called after every agent interaction.
        """
        act = self.get_session(session_id)
        if not act:
            raise ValueError(f"Session {session_id} not found")
        
        # Update timestamp
        act.updated_at = datetime.now().isoformat()
        
        # Apply updates from agent response
        if "current_objective" in state_updates:
            act.current_objective = state_updates["current_objective"]
        
        if "context_summary" in state_updates:
            act.context_summary = state_updates["context_summary"]
        
        if "task_completed" in state_updates:
            act.task_chain.append({
                "task": state_updates.get("task_completed"),
                "agent": agent_id,
                "timestamp": act.updated_at,
                "result_summary": state_updates.get("result_summary", "")
            })
        
        if "handoff_reason" in state_updates:
            act.handoff_reason = state_updates["handoff_reason"]
            act.next_agent_hint = state_updates.get("next_agent_hint", "")
        
        if "artifacts" in state_updates:
            for key, value in state_updates["artifacts"].items():
                if key in act.artifacts:
                    if isinstance(act.artifacts[key], list):
                        act.artifacts[key].extend(value if isinstance(value, list) else [value])
                    elif isinstance(act.artifacts[key], dict):
                        act.artifacts[key].update(value)
                    else:
                        act.artifacts[key] = value
        
        # Log the handshake
        act.handshake_log.append({
            "agent": agent_id,
            "timestamp": act.updated_at,
            "action": "state_update",
            "updates_applied": list(state_updates.keys())
        })
        
        act.origin_agent = agent_id
        return act
    
    def prepare_handoff(self, session_id: str) -> dict:
        """
        Prepare ACT for handoff to next agent.
        Returns the full context needed for the receiving agent.
        """
        act = self.get_session(session_id)
        if not act:
            raise ValueError(f"Session {session_id} not found")
        
        return {
            "act": act.to_dict(),
            "handoff_context": {
                "from_agent": act.origin_agent,
                "reason": act.handoff_reason,
                "suggested_agent": act.next_agent_hint,
                "objective": act.current_objective,
                "context": act.context_summary
            }
        }
    
    def save_session(self, session_id: str) -> str:
        """Persist ACT to disk."""
        act = self.get_session(session_id)
        if not act:
            raise ValueError(f"Session {session_id} not found")
        
        filepath = self.storage_dir / f"{session_id}.json"
        with open(filepath, "w") as f:
            json.dump(act.to_dict(), f, indent=2)
        
        return str(filepath)
    
    def load_session(self, session_id: str) -> Optional[ACT]:
        """Load ACT from disk."""
        filepath = self.storage_dir / f"{session_id}.json"
        if not filepath.exists():
            return None
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        act = ACT.from_dict(data)
        self.active_sessions[session_id] = act
        return act
    
    def validate_handshake(self, session_id: str) -> dict:
        """
        Validate that a proper handshake occurred.
        Returns validation report for the ACT Handshake test.
        """
        act = self.get_session(session_id)
        if not act:
            return {"valid": False, "error": "Session not found"}
        
        validation = {
            "valid": True,
            "session_id": session_id,
            "checks": {}
        }
        
        # Check 1: At least 2 agents touched this ACT
        unique_agents = set(log["agent"] for log in act.handshake_log)
        validation["checks"]["multi_agent"] = {
            "passed": len(unique_agents) >= 2,
            "agents": list(unique_agents),
            "message": f"{len(unique_agents)} agent(s) participated"
        }
        
        # Check 2: Context was preserved across handoff
        validation["checks"]["context_preserved"] = {
            "passed": bool(act.context_summary),
            "message": "Context summary exists" if act.context_summary else "No context summary"
        }
        
        # Check 3: Task chain shows progression
        validation["checks"]["task_progression"] = {
            "passed": len(act.task_chain) >= 1,
            "tasks": len(act.task_chain),
            "message": f"{len(act.task_chain)} task(s) completed"
        }
        
        # Overall validation
        validation["valid"] = all(
            check["passed"] for check in validation["checks"].values()
        )
        
        return validation


# Convenience function for quick testing
def create_test_session(objective: str) -> tuple[StateManager, ACT]:
    """Quick setup for testing the protocol."""
    manager = StateManager()
    act = manager.create_session(objective)
    return manager, act


if __name__ == "__main__":
    # Quick test
    manager, act = create_test_session("Build a pixel art character for One-Hit Samurai")
    print(f"Created session: {act.session_id}")
    print(json.dumps(act.to_dict(), indent=2))
