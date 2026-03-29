from typing import Dict
from .base import LLMProvider

class ProviderRegistry:
    """Dynamic registry for UAP LLM providers."""
    
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        
    def register(self, backend: str, provider: LLMProvider) -> None:
        """Register a new LLM provider instance."""
        self._providers[backend] = provider
        
    def get(self, backend: str) -> LLMProvider:
        """Retrieve a provider by its backend name."""
        if backend not in self._providers:
            raise KeyError(f"Unknown backend: {backend}")
        return self._providers[backend]
        
    def list_backends(self) -> list[str]:
        """List all registered backend identifiers."""
        return list(self._providers.keys())

# Global registry instance
registry = ProviderRegistry()
