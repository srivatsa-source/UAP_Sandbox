"""
UAP Dispatcher - API Middleman
Routes tasks between agents, manages handoffs, and orchestrates the ACT lifecycle.
Supports Groq and Ollama as LLM backends.
"""

import json
import os
from typing import Optional, Callable
from pathlib import Path

from protocol import StateManager, ACT


class AgentConfig:
    """Configuration for a specialized agent."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        system_prompt: str,
        model: str = "llama-3.3-70b-versatile",  # Updated Groq model
        backend: str = "groq"  # "groq" or "ollama"
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type  # planner, coder, designer, reviewer, etc.
        self.system_prompt = system_prompt
        self.model = model
        self.backend = backend


class Dispatcher:
    """
    Routes tasks to appropriate agents and manages ACT handoffs.
    This is the "traffic controller" for the UAP system.
    """
    
    def __init__(self, groq_api_key: Optional[str] = None, ollama_base_url: str = "http://localhost:11434"):
        self.state_manager = StateManager()
        self.agents: dict[str, AgentConfig] = {}
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.ollama_base_url = ollama_base_url
        
        # Load reflector prompt
        self.reflector_prompt = self._load_reflector_prompt()
    
    def _load_reflector_prompt(self) -> str:
        """Load the reflector prompt that instructs agents on UAP format."""
        prompt_path = Path(__file__).parent / "reflector_prompt.txt"
        if prompt_path.exists():
            return prompt_path.read_text()
        return "ERROR: reflector_prompt.txt not found"
    
    def register_agent(self, config: AgentConfig) -> None:
        """Register an agent configuration."""
        self.agents[config.agent_id] = config
        print(f"[Dispatcher] Registered agent: {config.agent_id} ({config.agent_type})")
    
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
                "answer": "ERROR: GROQ_API_KEY not set",
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
                "answer": "ERROR: requests package not installed. Run: pip install requests",
                "state_updates": {"context_summary": "Ollama API call failed - package not installed"}
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
    
    def _call_openai(self, prompt: str, model: str) -> str:
        """Call OpenAI API."""
        try:
            import requests
        except ImportError:
            return json.dumps({"answer": "ERROR: requests not installed", "state_updates": {}})
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return json.dumps({"answer": "ERROR: OPENAI_API_KEY not set", "state_updates": {}})
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
                timeout=120
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return json.dumps({"answer": f"ERROR: OpenAI call failed: {str(e)}", "state_updates": {}})
    
    def _call_anthropic(self, prompt: str, model: str) -> str:
        """Call Anthropic Claude API."""
        try:
            import requests
        except ImportError:
            return json.dumps({"answer": "ERROR: requests not installed", "state_updates": {}})
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return json.dumps({"answer": "ERROR: ANTHROPIC_API_KEY not set", "state_updates": {}})
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            return json.dumps({"answer": f"ERROR: Anthropic call failed: {str(e)}", "state_updates": {}})
    
    def _call_together(self, prompt: str, model: str) -> str:
        """Call Together AI API (OpenAI-compatible)."""
        try:
            import requests
        except ImportError:
            return json.dumps({"answer": "ERROR: requests not installed", "state_updates": {}})
        
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            return json.dumps({"answer": "ERROR: TOGETHER_API_KEY not set", "state_updates": {}})
        
        try:
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
                timeout=120
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return json.dumps({"answer": f"ERROR: Together call failed: {str(e)}", "state_updates": {}})
    
    def _call_openrouter(self, prompt: str, model: str) -> str:
        """Call OpenRouter API (OpenAI-compatible)."""
        try:
            import requests
        except ImportError:
            return json.dumps({"answer": "ERROR: requests not installed", "state_updates": {}})
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return json.dumps({"answer": "ERROR: OPENROUTER_API_KEY not set", "state_updates": {}})
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/uap-protocol"
                },
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
                timeout=120
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return json.dumps({"answer": f"ERROR: OpenRouter call failed: {str(e)}", "state_updates": {}})
    
    def _call_google(self, prompt: str, model: str) -> str:
        """Call Google Gemini API."""
        try:
            import requests
        except ImportError:
            return json.dumps({"answer": "ERROR: requests not installed", "state_updates": {}})
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return json.dumps({"answer": "ERROR: GOOGLE_API_KEY not set", "state_updates": {}})
        
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=120
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return json.dumps({"answer": f"ERROR: Google call failed: {str(e)}", "state_updates": {}})
    
    def _call_agent(self, agent: AgentConfig, prompt: str) -> str:
        """Route to appropriate backend."""
        if agent.backend == "groq":
            return self._call_groq(prompt, agent.model)
        elif agent.backend == "ollama":
            return self._call_ollama(prompt, agent.model)
        elif agent.backend == "openai":
            return self._call_openai(prompt, agent.model)
        elif agent.backend == "anthropic":
            return self._call_anthropic(prompt, agent.model)
        elif agent.backend == "together":
            return self._call_together(prompt, agent.model)
        elif agent.backend == "openrouter":
            return self._call_openrouter(prompt, agent.model)
        elif agent.backend == "google":
            return self._call_google(prompt, agent.model)
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
        import re
        
        # Strategy 1: Find JSON code block with answer/state_updates keys
        # Use greedy matching to get the outermost JSON object
        json_blocks = re.findall(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if "answer" in parsed or "state_updates" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
        
        # Strategy 2: Find JSON object containing required UAP keys
        # Look for balanced braces containing "answer" or "state_updates"
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
            raise ValueError(f"Agent {agent_id} not registered")
        
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
                    print(f"[Dispatcher] Auto-handoff to {next_agent}")
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
        
        print(f"[Dispatcher] Handoff: {handoff_data['handoff_context']['from_agent']} -> {to_agent_id}")
        print(f"[Dispatcher] Reason: {handoff_data['handoff_context']['reason']}")
        
        # Dispatch to receiving agent (no task = continue from ACT)
        return self.dispatch(
            agent_id=to_agent_id,
            session_id=session_id,
            task=None  # Key: no new task, agent continues from ACT
        )
    
    def validate_handshake(self, session_id: str) -> dict:
        """Validate that a proper ACT handshake occurred."""
        return self.state_manager.validate_handshake(session_id)

    # =========================================================================
    # CONVENIENCE METHODS FOR SIMPLIFIED USAGE
    # =========================================================================
    
    def start_session(self, objective: str = "") -> "ACT":
        """
        Start a new UAP session with an optional objective.
        Returns the ACT for the new session.
        """
        return self.state_manager.create_session(objective)
    
    def dispatch_task(
        self,
        session_id: str,
        task: str,
        agent_id: str = "planner",
        auto_handoff: bool = False
    ) -> dict:
        """
        Simplified task dispatch - sends a task to an agent and returns the result.
        
        Args:
            session_id: The session to use
            task: The task/prompt to send
            agent_id: Which agent to use (default: planner)
            auto_handoff: Whether to auto-handoff to next agent
        
        Returns:
            Dict with 'answer', 'state_updates', 'session_id'
        """
        result = self.dispatch(
            agent_id=agent_id,
            session_id=session_id,
            task=task,
            auto_handoff=auto_handoff
        )
        
        # Return simplified result
        return {
            "answer": result.get("response", "No response"),
            "state_updates": result.get("act", {}).get("context_summary", ""),
            "session_id": result.get("session_id", session_id),
            "handoff_info": result.get("handoff_info")
        }


# =============================================================================
# MANUAL TESTING UTILITIES
# =============================================================================

class MockAgent:
    """
    Mock agent for testing without LLM calls.
    Simulates agent responses for validating the handshake flow.
    """
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
    
    def generate_response(self, task: str, context: str = "") -> dict:
        """Generate a mock UAP-compliant response."""
        return {
            "answer": f"[{self.agent_id}] Completed work on: {task}",
            "state_updates": {
                "current_objective": task,
                "context_summary": f"[{self.agent_type}] processed task. {context}",
                "task_completed": task,
                "result_summary": "success",
                "handoff_reason": None,
                "next_agent_hint": None,
                "artifacts": {
                    "decisions": [f"Decision by {self.agent_id}"]
                }
            }
        }


def manual_handshake_test():
    """
    Manual test for validating ACT Handshake without LLM calls.
    This proves the protocol works before adding real agents.
    """
    print("=" * 60)
    print("UAP MANUAL HANDSHAKE TEST")
    print("=" * 60)
    
    # Setup
    manager = StateManager()
    
    # Step 1: Create session with initial task
    print("\n[Step 1] Creating session...")
    act = manager.create_session("Design and implement a samurai character")
    print(f"Session ID: {act.session_id}")
    
    # Step 2: Simulate Agent A (Designer) work
    print("\n[Step 2] Agent A (Designer) processing...")
    agent_a_updates = {
        "current_objective": "Design and implement a samurai character",
        "context_summary": "Designed 16x16 samurai sprite with red/white palette. Base pose complete. Ready for animation implementation.",
        "task_completed": "Character sprite design",
        "result_summary": "success",
        "handoff_reason": "Design complete, needs animation coding",
        "next_agent_hint": "coder",
        "artifacts": {
            "game_state": {
                "sprite_size": "16x16",
                "palette": ["#1a1a2e", "#e94560", "#f5f5f5"]
            },
            "decisions": ["Using 16x16 for retro aesthetic", "3-color palette for clarity"]
        }
    }
    manager.apply_state_updates(act.session_id, agent_a_updates, "agent_designer")
    print(f"Agent A updates applied. Handoff reason: {act.handoff_reason}")
    
    # Step 3: Simulate handoff to Agent B
    print("\n[Step 3] Preparing handoff to Agent B...")
    handoff_data = manager.prepare_handoff(act.session_id)
    print(f"Handoff from: {handoff_data['handoff_context']['from_agent']}")
    print(f"Context: {handoff_data['handoff_context']['context']}")
    
    # Step 4: Simulate Agent B (Coder) work - using ONLY the ACT
    print("\n[Step 4] Agent B (Coder) processing from ACT only...")
    agent_b_updates = {
        "context_summary": "Animation system implemented. 3-frame idle animation created based on designer specs (16x16, red/white palette). Spritesheet exported.",
        "task_completed": "Animation implementation",
        "result_summary": "success",
        "artifacts": {
            "code_snippets": [
                "class SamuraiSprite:\n    def __init__(self):\n        self.frames = load_spritesheet('samurai.png', 16, 16)\n        self.current_frame = 0"
            ],
            "files_modified": ["sprites/samurai.py", "assets/samurai.png"]
        }
    }
    manager.apply_state_updates(act.session_id, agent_b_updates, "agent_coder")
    print(f"Agent B updates applied.")
    
    # Step 5: Validate handshake
    print("\n[Step 5] Validating ACT Handshake...")
    validation = manager.validate_handshake(act.session_id)
    
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(json.dumps(validation, indent=2))
    
    # Save final state
    filepath = manager.save_session(act.session_id)
    print(f"\nSession saved to: {filepath}")
    
    return validation["valid"]


if __name__ == "__main__":
    success = manual_handshake_test()
    print(f"\n{'✓ HANDSHAKE VALID' if success else '✗ HANDSHAKE FAILED'}")
