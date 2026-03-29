from abc import ABC, abstractmethod
from typing import Optional

class LLMProvider(ABC):
    """Base interface for all LLM providers in the UAP system."""
    
    @abstractmethod
    def call(self, prompt: str, model: str, user_email: Optional[str] = None) -> str:
        """Call the underlying LLM with a prompt and model, returning the raw text response."""
        pass
