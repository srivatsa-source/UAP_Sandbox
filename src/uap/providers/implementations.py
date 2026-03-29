import json
import os
from typing import Optional

from .base import LLMProvider
from uap.core.config import get_config
from uap.core.vault import get_credential

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url
        
    def call(self, prompt: str, model: str, user_email: Optional[str] = None) -> str:
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
    def call(self, prompt: str, model: str, user_email: Optional[str] = None) -> str:
        api_key = get_credential(user_email, "openai") if user_email else None
        if not api_key:
            return json.dumps({
                "answer": "OpenAI not linked. Please link your OpenAI account in the UAP dashboard.",
                "state_updates": {"context_summary": "OpenAI agent not linked to user identity"}
            })
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048
            )
            return response.choices[0].message.content
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