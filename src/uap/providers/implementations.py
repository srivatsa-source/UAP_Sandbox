import json
import os
from typing import Optional, List, Dict, Any

from .base import LLMProvider, ProviderCapability
from uap.core.config import get_config
from uap.core.vault import get_credential

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url
    
    @property
    def capabilities(self) -> set[ProviderCapability]:
        return set() # Basic text provider
        
    def call(self, prompt: str, model: str, user_email: Optional[str] = None, system_instruction: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None) -> str:
        try:
            import requests
        except ImportError:
            return json.dumps({
                "answer": "ERROR: requests package not installed",
                "state_updates": {"context_summary": "Ollama API call failed"}
            })
            
        config = get_config()
        base_url = self._base_url or config.get("ollama_url", "http://localhost:11434")
        
        try:
            # Prefix system instruction if provided since Ollama basic gen doesn't format it
            if system_instruction:
                prompt = f"{system_instruction}\n\n{prompt}"
                
            response = requests.post(
                f"{base_url}/api/generate",
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

class OpenAIProvider(LLMProvider):
    @property
    def capabilities(self) -> set[ProviderCapability]:
        return {ProviderCapability.TOOL_CALLING}
        
    def call(self, prompt: str, model: str, user_email: Optional[str] = None, system_instruction: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None) -> str:
        api_key = get_credential(user_email, "openai") if user_email else None
        
        # Fallback to general env api key if no vault credential is found, to avoid strictly mandating vault/user login
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            
        if not api_key:
            return json.dumps({
                "answer": "OpenAI not linked. Please provide an OPENAI_API_KEY env or link your OpenAI account in the UAP dashboard.",
                "state_updates": {"context_summary": "OpenAI agent not linked to user identity or missing env variable"}
            })
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            # Check if this protocol version wants to use tools for the output format
            if tools:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                    tools=[{"type": "function", "function": t["function"]} for t in tools if t.get("type") == "function"],
                    tool_choice={"type": "function", "function": {"name": tools[0]["function"]["name"]}} if tools else "auto"
                )
                # Ensure we have a tool call payload (we enforce it via tool_choice)
                message = response.choices[0].message
                if message.tool_calls:
                    return message.tool_calls[0].function.arguments
                else:
                    return message.content or ""
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048
                )
                return response.choices[0].message.content or ""
        except ImportError as e:
            if "openai" in str(e):
                return json.dumps({
                    "answer": "ERROR: openai package not installed. Run: pip install openai",
                    "state_updates": {"context_summary": "OpenAI SDK not installed"}
                })
            raise
        except Exception as e:
            return json.dumps({
                "answer": f"ERROR: OpenAI API call failed: {str(e)}",
                "state_updates": {"context_summary": f"OpenAI error: {str(e)}"}
            })

class AnthropicProvider(LLMProvider):
    @property
    def capabilities(self) -> set[ProviderCapability]:
        return {ProviderCapability.TOOL_CALLING}
        
    def call(self, prompt: str, model: str, user_email: Optional[str] = None, system_instruction: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None) -> str:
        api_key = get_credential(user_email, "anthropic") if user_email else None
        
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            
        if not api_key:
            return json.dumps({
                "answer": "Anthropic not linked. Please provide an ANTHROPIC_API_KEY env or link your Claude account.",
                "state_updates": {"context_summary": "Anthropic agent not linked"}
            })
        
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            messages = [{"role": "user", "content": prompt}]
            
            if tools:
                anthropic_tools = [{"name": t["function"]["name"], "description": t["function"].get("description", ""), "input_schema": t["function"].get("parameters", {})} for t in tools if t.get("type") == "function"]
                response = client.messages.create(
                    model=model,
                    max_tokens=2048,
                    system=system_instruction or "",
                    tools=anthropic_tools,
                    messages=messages
                )
                for block in response.content:
                    if block.type == "tool_use":
                        return json.dumps(block.input)
                return response.content[0].text if response.content else ""
            else:
                response = client.messages.create(
                    model=model,
                    max_tokens=2048,
                    system=system_instruction or "",
                    messages=messages
                )
                return response.content[0].text if response.content else ""
        except ImportError:
            return json.dumps({"answer": "ERROR: anthropic package not installed.", "state_updates": {"context_summary": "Anthropic SDK not installed"}})
        except Exception as e:
            return json.dumps({"answer": f"ERROR: Anthropic API call failed: {str(e)}", "state_updates": {"context_summary": f"Anthropic error: {str(e)}"} })

class MockProvider(LLMProvider):
    """
    Mock backend to demonstrate multi-agent handoffs visually
    without requiring API keys or downloading local LLMs.
    """
    @property
    def capabilities(self) -> set[ProviderCapability]:
        return {ProviderCapability.TOOL_CALLING}
        
    def call(self, prompt: str, model: str, user_email: Optional[str] = None, system_instruction: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None) -> str:
        import time
        time.sleep(1) # Simulate think time
        
        if "test_worker_01" in prompt or "You are the Worker" in prompt:
            # Simulate worker response ending the loop
            return json.dumps({
                "answer": f"Hello! [Mock Worker] here. I received your request and have completed the implementation based on the router's context.",
                "state_updates": {
                    "context_summary": "Worker finished execution of user's task.",
                    "task_completed": "Finished the routed task.",
                    "result_summary": "success",
                    "handoff_reason": None,
                    "next_agent_hint": None,
                    "artifacts": {}
                }
            })
        else:
            # Simulate router handing off to worker
            return json.dumps({
                "answer": f"Got it. I am the router. I am evaluating your task and realizing I need to hand this off to a worker agent.\nPassing context to `test_worker_01`...",
                "state_updates": {
                    "context_summary": "[Router Analysis] The user wants a task done. Handing off to the worker agent for execution.",
                    "task_completed": "Analyzed task intent.",
                    "result_summary": "partial",
                    "handoff_reason": "Needs execution by a worker.",
                    "next_agent_hint": "test_worker_01",
                    "artifacts": {}
                }
            })