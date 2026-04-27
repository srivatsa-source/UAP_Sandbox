from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Dict, Any, Set, List
from dataclasses import dataclass
import enum

class ProviderCapability(enum.Enum):
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    AUDIO = "audio"

@dataclass
class UAPEvent:
    """Base class for all execution events."""
    agent_id: str

@dataclass
class TokenStreamEvent(UAPEvent):
    """Fired when an agent generates a text token."""
    chunk: str

@dataclass
class StateUpdateEvent(UAPEvent):
    """Fired when the ACT state is mutated."""
    state_diff: Dict[str, Any]

@dataclass
class HandoffEvent(UAPEvent):
    """Fired when an agent requests a handoff."""
    next_agent: str
    reason: str

class LLMProvider(ABC):
    """Base interface for all LLM providers in the UAP system."""
    
    @property
    def capabilities(self) -> Set[ProviderCapability]:
        """Return the set of capabilities supported by this provider."""
        return set()
    
    @abstractmethod
    def call(self, prompt: str, model: str, user_email: Optional[str] = None, system_instruction: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Call the underlying LLM with a prompt and model, returning the raw text response.
        Optionally supports system instruction and native tools if the provider supports TOOL_CALLING.
        """
        pass

    async def stream(self, prompt: str, model: str, agent_id: str, user_email: Optional[str] = None, system_instruction: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[UAPEvent, None]:
        """Stream the execution flow of the underlying LLM yielding standardized UAPEvents."""
        # Fallback simulation using the sync 'call' method for providers not yet updated
        response = self.call(prompt, model, user_email, system_instruction, tools)
        tokens = response.split(" ")
        for token in tokens:
            yield TokenStreamEvent(agent_id=agent_id, chunk=token + " ")
