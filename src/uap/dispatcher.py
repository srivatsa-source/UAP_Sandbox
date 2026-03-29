"""
UAP Dispatcher - API Middleman
Routes tasks to external agent models dynamically, acting as a stateless pipe
for the ACT lifecycle.
"""

import json
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from uap.core.protocol import StateManager, ACT
from uap.providers import registry

@dataclass
class AgentConfig:
    """Configuration for an external agent."""
    agent_id: str
    system_prompt: str
    model: str = "gpt-4o"
    backend: str = "openai"  # openai or ollama
    metadata: dict = field(default_factory=dict)

class Dispatcher:
    """
    Routes tasks to appropriate agents and manages ACT handoffs.
    Purely a state router.
    """
    
    def __init__(self):
        self.state_manager = StateManager()
        self.agents: dict[str, AgentConfig] = {}
        self.reflector_prompt = self._load_reflector_prompt()
    
    def _load_reflector_prompt(self) -> str:
        """Load the reflector prompt that instructs agents on UAP format."""
        return """
You are an agent participating in the Universal Agent Protocol (UAP).
Every response MUST include a JSON block exactly matching this schema:

```json
{
  "answer": "<your conversational response or code>",
  "state_updates": {
    "context_summary": "<2-3 sentences summarizing progress for the NEXT agent - CRITICAL>",
    "task_completed": "<what you accomplished in this turn>",
    "result_summary": "success|partial|blocked",
    "handoff_reason": "<why to hand off, or null if objective complete>",
    "next_agent_hint": "<suggested agent type/role for the next step>",
    "artifacts": {
      "code_snippets": [],
      "decisions": [],
      "files_modified": []
    }
  }
}
```
"""
    
    def register_agent(self, config: AgentConfig) -> None:
        self.agents[config.agent_id] = config
        
    def list_agents(self) -> list[AgentConfig]:
        return list(self.agents.values())

    def _build_agent_prompt(self, agent: AgentConfig, act: ACT, task: Optional[str] = None) -> str:
        act_json = json.dumps(act.to_dict(), indent=2)
        prompt_parts = [
            f"=== AGENT SYSTEM PROMPT ===\n{agent.system_prompt}\n",
            f"=== UAP PROTOCOL INSTRUCTIONS ===\n{self.reflector_prompt}\n",
            f"=== CURRENT ACT (Agent Context Token) ===\n```json\n{act_json}\n```\n",
        ]
        
        if task:
            prompt_parts.append(f"=== NEW TASK ===\n{task}\n")
        else:
            prompt_parts.append(
                f"=== CONTINUE FROM ACT ===\n"
                f"Objective: {act.current_objective}\n"
                f"Context: {act.context_summary}\n"
                f"Handoff Reason: {act.handoff_reason}\n"
                f"\nContinue the work based on the ACT above. No user re-prompting needed.\n"
            )
        
        prompt_parts.append(
            "\n=== YOUR RESPONSE ===\n"
            "Provide your response with the required JSON structure.\n"
        )
        return "\n".join(prompt_parts)
    
    def _call_agent(self, agent: AgentConfig, prompt: str, user_email: Optional[str] = None) -> str:
        """Route to appropriate backend dynamically via registry."""
        try:
            provider = registry.get(agent.backend)
        except KeyError:
            return json.dumps({
                "answer": f"ERROR: Unknown backend: {agent.backend}",
                "state_updates": {"context_summary": f"Unknown backend: {agent.backend}"}
            })
        return provider.call(prompt, agent.model, user_email)
    
    def _parse_agent_response(self, response: str) -> dict:
        json_blocks = re.findall(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if "answer" in parsed or "state_updates" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
        try:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                parsed = json.loads(response[start:end+1])
                if "answer" in parsed or "state_updates" in parsed:
                    return parsed
        except json.JSONDecodeError:
            pass
        
        return {
            "answer": response,
            "state_updates": {
                "context_summary": "Response did not follow UAP format - raw response captured",
                "task_completed": "Unknown - response parsing failed"
            }
        }
    
    def dispatch(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        task: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        user_email: Optional[str] = None
    ) -> dict:
        """
        Dispatch a task to an agent. Allows dynamic injection of agent config if not pre-registered.
        """
        if session_id:
            act = self.state_manager.get_session(session_id)
            if not act:
                raise ValueError(f"Session {session_id} not found")
        else:
            act = self.state_manager.create_session(task or "")
        
        if config_override:
            agent = AgentConfig(**config_override)
        else:
            agent = self.agents.get(agent_id)
            
        if not agent:
            raise ValueError(f"Agent {agent_id} not registered and no config_override provided.")
        
        prompt = self._build_agent_prompt(agent, act, task)
        raw_response = self._call_agent(agent, prompt, user_email=user_email)
        parsed = self._parse_agent_response(raw_response)
        
        if "state_updates" in parsed:
            updates = parsed["state_updates"]
            if "context_summary" in updates:
                act.context_summary = updates["context_summary"]
            if "handoff_reason" in updates:
                act.handoff_reason = updates["handoff_reason"]
            self.state_manager.save_session(act.session_id)
            
        return {
            "response": parsed,
            "act": act.to_dict()
        }

    def handoff(self, session_id: str, to_agent_id: str, config_override: Optional[Dict[str, Any]] = None, user_email: Optional[str] = None) -> dict:
        return self.dispatch(agent_id=to_agent_id, session_id=session_id, config_override=config_override, user_email=user_email)
