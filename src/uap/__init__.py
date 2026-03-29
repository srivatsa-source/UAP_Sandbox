"""
UAP - Universal Agent Protocol
Minimalist Semantic Transport Layer.
"""

__version__ = "0.4.0"

from uap.core.protocol import ACT, StateManager
from uap.dispatcher import Dispatcher, AgentConfig

__all__ = [
    "ACT",
    "StateManager",
    "Dispatcher",
    "AgentConfig",
    "__version__",
]
