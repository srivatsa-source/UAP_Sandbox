"""
UAP - Universal Agent Protocol
Connect AI agents, share state, run tasks from your terminal.

Usage:
    uap new "Build a REST API"
    uap run <session_id> --agents planner,coder,reviewer
    uap agents list
    uap agents add github:user/repo
"""

__version__ = "0.1.0"

from uap.protocol import ACT, StateManager
from uap.dispatcher import Dispatcher, AgentConfig
from uap.registry import AgentRegistry

__all__ = [
    "ACT",
    "StateManager", 
    "Dispatcher",
    "AgentConfig",
    "AgentRegistry",
    "__version__",
]
