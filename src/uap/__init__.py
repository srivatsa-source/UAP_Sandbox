"""
UAP - Universal Agent Protocol
Connect AI agents, share state, run tasks from your terminal.

Usage:
    uap new "Build a REST API"
    uap run <session_id> --agents planner,coder,reviewer
    uap agents list
    uap agents add github:user/repo
"""

__version__ = "0.3.0"

from uap.protocol import ACT, StateManager
from uap.dispatcher import Dispatcher, AgentConfig
from uap.registry import AgentRegistry
from uap.telemetry import TelemetryCollector, get_telemetry
from uap.agents import get_all_agents, get_core_agents, get_dockdesk_agents

__all__ = [
    "ACT",
    "StateManager",
    "Dispatcher",
    "AgentConfig",
    "AgentRegistry",
    "TelemetryCollector",
    "get_telemetry",
    "get_all_agents",
    "get_core_agents",
    "get_dockdesk_agents",
    "__version__",
]
