from .base import LLMProvider
from .registry import registry
from .implementations import (
    OllamaProvider,
    OpenAIProvider
)

def _initialize_registry():
    """Register all core UAP backends."""
    registry.register("ollama", OllamaProvider())
    registry.register("openai", OpenAIProvider())

# Initialize automatically when imported
_initialize_registry()

__all__ = ["LLMProvider", "registry"]