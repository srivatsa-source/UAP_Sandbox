"""
UAP Dispatcher - API Middleman
Routes tasks between agents, manages handoffs, and orchestrates the ACT lifecycle.
Supports Groq and Ollama as LLM backends.
"""

import json
import re
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field

from uap.protocol import StateManager, ACT
from uap.config import get_config


@dataclass
class AgentConfig:
    """Configuration for a specialized agent."""
    agent_id: str
    agent_type: str  # planner, coder, designer, reviewer, debugger, etc.
    system_prompt: str
    model: str = "llama-3.1-8b-instant"
    backend: str = "groq"  # "groq" or "ollama"
    source: str = "builtin"  # "builtin", "github:user/repo", "local"
    metadata: dict = field(default_factory=dict)


class Dispatcher:
    """
    Routes tasks to appropriate agents and manages ACT handoffs.
    This is the "traffic controller" for the UAP system.
    """
    
    def __init__(
        self, 
        groq_api_key: Optional[str] = None, 
        ollama_base_url: str = "http://localhost:11434"
    ):
        self.state_manager = StateManager()
        self.agents: dict[str, AgentConfig] = {}
        
        # Load config
        config = get_config()
        self.groq_api_key = groq_api_key or config.get("groq_api_key")
        self.ollama_base_url = ollama_base_url or config.get("ollama_url", "http://localhost:11434")
        
        # Load reflector prompt
        self.reflector_prompt = self._load_reflector_prompt()
    
    def _load_reflector_prompt(self) -> str:
        """Load the reflector prompt that instructs agents on UAP format."""
        # First try package location
        prompt_path = Path(__file__).parent / "reflector_prompt.txt"
        if prompt_path.exists():
            return prompt_path.read_text()
        
        # Fallback to embedded minimal prompt
        return """
You are an agent in the Universal Agent Protocol (UAP).
Every response MUST include a JSON block:

```json
{
  "answer": "<your response>",
  "state_updates": {
    "context_summary": "<2-3 sentences for next agent - REQUIRED>",
    "task_completed": "<what you accomplished>",
    "result_summary": "success|partial|blocked",
    "handoff_reason": "<why to hand off, or null if done>",
    "next_agent_hint": "<agent type: planner|coder|reviewer|debugger|designer>",
    "artifacts": {
      "code_snippets": [],
      "decisions": [],
      "files_modified": []
    }
  }
}
```

The context_summary is CRITICAL - the next agent relies on it entirely.
"""
    
    def register_agent(self, config: AgentConfig) -> None:
        """Register an agent configuration."""
        self.agents[config.agent_id] = config
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    def list_agents(self) -> list[AgentConfig]:
        """List all registered agents."""
        return list(self.agents.values())
    
    def _build_agent_prompt(self, agent: AgentConfig, act: ACT, task: Optional[str] = None) -> str:
        """
        Build the full prompt for an agent, including:
        1. Agent's system prompt
        2. Reflector prompt (UAP instructions)
        3. Current ACT state
        4. Task (if new task, otherwise continue from ACT)
        """
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
            "Provide your response with the required JSON structure (answer + state_updates).\n"
        )
        
        return "\n".join(prompt_parts)
    
    def _call_groq(self, prompt: str, model: str) -> str:
        """Call Groq API."""
        try:
            from groq import Groq
        except ImportError:
            return json.dumps({
                "answer": "ERROR: groq package not installed. Run: pip install groq",
                "state_updates": {"context_summary": "Groq API call failed - package not installed"}
            })
        
        if not self.groq_api_key:
            return json.dumps({
                "answer": "ERROR: GROQ_API_KEY not set. Run: uap config set groq_api_key <your-key>",
                "state_updates": {"context_summary": "Groq API call failed - no API key"}
            })
        
        client = Groq(api_key=self.groq_api_key)
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048
        )
        
        return response.choices[0].message.content
    
    def _call_ollama(self, prompt: str, model: str) -> str:
        """Call Ollama API."""
        try:
            import requests
        except ImportError:
            return json.dumps({
                "answer": "ERROR: requests package not installed",
                "state_updates": {"context_summary": "Ollama API call failed"}
            })
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return json.dumps({
                "answer": f"ERROR: Ollama API call failed: {str(e)}",
                "state_updates": {"context_summary": f"Ollama API call failed: {str(e)}"}
            })
    
    def _call_agent(self, agent: AgentConfig, prompt: str) -> str:
        """Route to appropriate backend."""
        if agent.backend == "groq":
            return self._call_groq(prompt, agent.model)
        elif agent.backend == "ollama":
            return self._call_ollama(prompt, agent.model)
        else:
            return json.dumps({
                "answer": f"ERROR: Unknown backend: {agent.backend}",
                "state_updates": {"context_summary": f"Unknown backend: {agent.backend}"}
            })
    
    def _parse_agent_response(self, response: str) -> dict:
        """
        Parse agent response to extract JSON structure.
        Handles responses with JSON in code blocks or raw JSON.
        """
        # Strategy 1: Find JSON code block with answer/state_updates keys
        json_blocks = re.findall(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if "answer" in parsed or "state_updates" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
        
        # Strategy 2: Find JSON object containing required UAP keys
        try:
            start = response.find('{"answer"')
            if start == -1:
                start = response.find('{"state_updates"')
            if start == -1:
                start = response.find('{\n  "answer"')
            if start == -1:
                start = response.find('{\n    "answer"')
            
            if start != -1:
                # Find matching closing brace
                depth = 0
                for i, char in enumerate(response[start:]):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            json_str = response[start:start+i+1]
                            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Try parsing from first { to last }
        try:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                parsed = json.loads(response[start:end+1])
                if "answer" in parsed or "state_updates" in parsed:
                    return parsed
        except json.JSONDecodeError:
            pass
        
        # Fallback: wrap raw response
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
        auto_handoff: bool = False
    ) -> dict:
        """
        Dispatch a task to an agent.
        
        Args:
            agent_id: Which agent to use
            session_id: Existing session to continue, or None for new
            task: New task to perform (None = continue from ACT)
            auto_handoff: If True, automatically route to next agent if handoff requested
        
        Returns:
            Dict with 'response', 'act', and 'handoff_info'
        """
        # Get or create session
        if session_id:
            act = self.state_manager.get_session(session_id)
            if not act:
                raise ValueError(f"Session {session_id} not found")
        else:
            act = self.state_manager.create_session(task or "")
        
        # Get agent config
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not registered. Available: {list(self.agents.keys())}")
        
        # Build prompt and call agent
        prompt = self._build_agent_prompt(agent, act, task)
        raw_response = self._call_agent(agent, prompt)
        
        # Parse response
        parsed = self._parse_agent_response(raw_response)
        
        # Apply state updates
        if "state_updates" in parsed:
            self.state_manager.apply_state_updates(
                act.session_id,
                parsed["state_updates"],
                agent_id
            )
        
        # Save session
        self.state_manager.save_session(act.session_id)
        
        # Prepare result
        result = {
            "response": parsed.get("answer", raw_response),
            "act": act.to_dict(),
            "session_id": act.session_id,
            "raw_response": raw_response
        }
        
        # Check for handoff
        state_updates = parsed.get("state_updates", {})
        if state_updates.get("handoff_reason"):
            result["handoff_info"] = {
                "reason": state_updates["handoff_reason"],
                "next_agent_hint": state_updates.get("next_agent_hint", ""),
                "ready_for_handoff": True
            }
            
            # Auto-handoff if enabled
            if auto_handoff and state_updates.get("next_agent_hint"):
                next_agent = self._find_agent_by_type(state_updates["next_agent_hint"])
                if next_agent:
                    return self.dispatch(
                        agent_id=next_agent,
                        session_id=act.session_id,
                        auto_handoff=True
                    )
        
        return result
    
    def _find_agent_by_type(self, agent_type: str) -> Optional[str]:
        """Find an agent ID by type."""
        for agent_id, config in self.agents.items():
            if config.agent_type == agent_type:
                return agent_id
        return None
    
    def handoff(self, session_id: str, to_agent_id: str) -> dict:
        """
        Explicit handoff from current agent to another.
        This is the core "ACT Handshake" operation.
        """
        # Prepare handoff context
        handoff_data = self.state_manager.prepare_handoff(session_id)
        
        # Dispatch to receiving agent (no task = continue from ACT)
        return self.dispatch(
            agent_id=to_agent_id,
            session_id=session_id,
            task=None  # Key: no new task, agent continues from ACT
        )
    
    def run_chain(
        self, 
        task: str, 
        agents: list[str], 
        session_id: Optional[str] = None
    ) -> dict:
        """
        Run a chain of agents on a task.
        Each agent hands off to the next using the ACT.
        
        Args:
            task: The initial task
            agents: List of agent IDs to run in sequence
            session_id: Existing session or None for new
        
        Returns:
            Final result with full chain history
        """
        if not agents:
            raise ValueError("At least one agent required")
        
        chain_results = []
        current_session_id = session_id
        
        for i, agent_id in enumerate(agents):
            is_first = (i == 0)
            
            if is_first:
                # First agent gets the task
                result = self.dispatch(
                    agent_id=agent_id,
                    session_id=current_session_id,
                    task=task
                )
            else:
                # Subsequent agents handoff from previous
                result = self.handoff(
                    session_id=current_session_id,
                    to_agent_id=agent_id
                )
            
            current_session_id = result["session_id"]
            chain_results.append({
                "agent": agent_id,
                "response": result["response"][:500],  # Truncate for summary
                "handoff_info": result.get("handoff_info")
            })
        
        return {
            "session_id": current_session_id,
            "chain": chain_results,
            "final_act": result["act"],
            "validation": self.state_manager.validate_handshake(current_session_id)
        }
    
    def validate_handshake(self, session_id: str) -> dict:
        """Validate that a proper ACT handshake occurred."""
        return self.state_manager.validate_handshake(session_id)
