from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import json

class AgentProtocol(ABC):
    """
    Abstract base class for formatting agent requests and parsing agent responses.
    Decouples the communication protocol from the LLM provider implementation.
    """
    @abstractmethod
    def format_request(self, system_prompt: str, task: str, act_state: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]]]:
        """
        Formats the request for the LLM provider.
        Returns a tuple of: (prompt, system_instruction, tools)
        """
        pass

    @abstractmethod
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        Parses the raw response from the LLM provider into a standardized state_updates dictionary.
        """
        pass

class TextJSONProtocol(AgentProtocol):
    """
    Legacy protocol that expects the LLM to output a specific JSON payload.
    Uses a hardcoded reflector prompt appended to the system prompt.
    """
    def __init__(self):
        self.reflector_prompt = """
[UAP PROTOCOL INSTRUCTIONS]
You are part of the Universal Agent Protocol (UAP).
Your output must be EXACTLY one valid JSON object, and nothing else. Do not use Markdown formatting (```json) around the output.

The JSON MUST match this schema:
{
    "answer": "Your actual helpful response/message for the user or the next agent.",
    "state_updates": {
        "phase": "processing|validation|complete",
        "current_objective": "What is the current overarching goal",
        "context_summary": "Summary of what you did and discovered, to be passed to the next agent",
        "task_completed": "Short description of what you just finished (if applicable)",
        "result_summary": "success|partial|blocked",
        "handoff_reason": "If you need to hand off to another agent, explain why here",
        "next_agent_hint": "Name or type of agent to hand off to",
        "artifacts": {
            "key": "value - concrete data you want to save to the ACT state"
        }
    }
}
Failure to output raw JSON will break the system.
"""

    def format_request(self, system_prompt: str, task: str, act_state: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]]]:
        act_context = json.dumps(act_state, indent=2)
        prompt = (
            f"{system_prompt}\\n\\n"
            f"{self.reflector_prompt}\\n\\n"
            f"[CURRENT ACT STATE]\\n{act_context}\\n\\n"
            f"[NEW TASK]\\n{task}"
        )
        return prompt, None, None

    def parse_response(self, response: str) -> Dict[str, Any]:
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            return {
                "answer": f"Protocol Error: Agent failed to output valid JSON. Output was: {response[:200]}...",
                "state_updates": {"result_summary": "blocked", "context_summary": f"Parse error: {str(e)}"}
            }

class NativeToolProtocol(AgentProtocol):
    """
    Protocol that uses native function calling (tools) to return the state updates.
    """
    def __init__(self):
        self.state_update_tool = {
            "type": "function",
            "function": {
                "name": "uap_state_update",
                "description": "Output your response and update the UAP ACT state",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "Your actual helpful response/message for the user or the next agent."
                        },
                        "state_updates": {
                            "type": "object",
                            "properties": {
                                "phase": {"type": "string", "enum": ["processing", "validation", "complete"]},
                                "current_objective": {"type": "string"},
                                "context_summary": {"type": "string"},
                                "task_completed": {"type": "string"},
                                "result_summary": {"type": "string", "enum": ["success", "partial", "blocked"]},
                                "handoff_reason": {"type": "string"},
                                "next_agent_hint": {"type": "string"},
                                "artifacts": {"type": "object"}
                            }
                        }
                    },
                    "required": ["answer", "state_updates"]
                }
            }
        }

    def format_request(self, system_prompt: str, task: str, act_state: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]]]:
        act_context = json.dumps(act_state, indent=2)
        prompt = (
            f"[CURRENT ACT STATE]\\n{act_context}\\n\\n"
            f"[NEW TASK]\\n{task}"
        )
        return prompt, system_prompt, [self.state_update_tool]

    def parse_response(self, response: Any) -> Dict[str, Any]:
        # Typically the LLM provider will return the tool call JSON string here in this string-based 'response' abstraction.
        # This will need to be properly parsed depending on how the implementation returns the tool arguments.
        # For our first iteration, we can attempt to parse it as raw JSON.
        try:
            return json.loads(response)
        except Exception as e:
            return {
                "answer": "Protocol Error: Failed parsing native tool format.",
                "state_updates": {"result_summary": "blocked"}
            }
