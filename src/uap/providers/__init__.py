from .base import LLMProvider
from .registry import registry
from .implementations import (
    OllamaProvider,
    OpenAIProvider,
    AnthropicProvider,
    MockProvider
)

def _initialize_registry():
    """Register all core UAP backends."""
    registry.register("ollama", OllamaProvider())
    registry.register("openai", OpenAIProvider())
    registry.register("anthropic", AnthropicProvider())
    registry.register("mock", MockProvider())

# Initialize automatically when imported
_initialize_registry()

__all__ = ["LLMProvider", "registry"]