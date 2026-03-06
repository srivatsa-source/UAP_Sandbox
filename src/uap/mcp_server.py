"""
UAP MCP Server — Model Context Protocol entry point.
Exposes the full dispatcher as 8 MCP tools over stdio transport.

Tools:
  1. create_session   — Create a new ACT session
  2. dispatch         — Send a task to a registered agent
  3. handoff          — Hand off an ACT to another agent
  4. run_chain        — Run a multi-agent chain
  5. get_session      — Retrieve an ACT by session ID
  6. list_sessions    — List all saved sessions
  7. list_agents      — List registered agents
  8. validate         — Validate a handshake
"""

from __future__ import annotations

import json
import sys
from typing import Any

# MCP SDK is an optional dependency; fail gracefully at import time.
try:
    from mcp.server import Server
    from mcp.server.stdio import run_stdio
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from uap.protocol import StateManager
from uap.dispatcher import Dispatcher, AgentConfig
from uap.agents import get_all_agents


def _build_server() -> "Server":
    """Construct and configure the MCP server with all 8 tools."""
    server = Server("uap-protocol")
    dispatcher = Dispatcher()
    
    # Pre-register all built-in agents
    for agent in get_all_agents():
        dispatcher.register_agent(agent)

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    TOOLS = [
        Tool(
            name="create_session",
            description="Create a new ACT (Agent Context Token) session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "objective": {
                        "type": "string",
                        "description": "The initial objective for the session.",
                    }
                },
                "required": ["objective"],
            },
        ),
        Tool(
            name="dispatch",
            description="Dispatch a task to a registered UAP agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent to dispatch to."},
                    "task": {"type": "string", "description": "The task description."},
                    "session_id": {"type": "string", "description": "Existing session ID (optional)."},
                },
                "required": ["agent_id", "task"],
            },
        ),
        Tool(
            name="handoff",
            description="Hand off an existing ACT session to another agent (ACT Handshake).",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session to hand off."},
                    "to_agent_id": {"type": "string", "description": "Receiving agent ID."},
                },
                "required": ["session_id", "to_agent_id"],
            },
        ),
        Tool(
            name="run_chain",
            description="Run a chain of agents on a task. Each agent hands off via the ACT.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The initial task."},
                    "agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered list of agent IDs.",
                    },
                },
                "required": ["task", "agents"],
            },
        ),
        Tool(
            name="get_session",
            description="Retrieve the ACT for a given session ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="list_sessions",
            description="List all saved ACT sessions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_agents",
            description="List all registered UAP agents.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="validate",
            description="Validate that a proper ACT handshake occurred in a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
    ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        result = _execute_tool(dispatcher, name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    return server


def _execute_tool(dispatcher: Dispatcher, name: str, args: dict[str, Any]) -> Any:
    """Route a tool call to the appropriate dispatcher method."""
    if name == "create_session":
        act = dispatcher.state_manager.create_session(args["objective"])
        dispatcher.state_manager.save_session(act.session_id)
        return {"session_id": act.session_id, "act": act.to_dict()}

    if name == "dispatch":
        return dispatcher.dispatch(
            agent_id=args["agent_id"],
            task=args["task"],
            session_id=args.get("session_id"),
        )

    if name == "handoff":
        return dispatcher.handoff(
            session_id=args["session_id"],
            to_agent_id=args["to_agent_id"],
        )

    if name == "run_chain":
        return dispatcher.run_chain(
            task=args["task"],
            agents=args["agents"],
        )

    if name == "get_session":
        act = dispatcher.state_manager.get_session(args["session_id"])
        if act:
            return act.to_dict()
        return {"error": f"Session {args['session_id']} not found"}

    if name == "list_sessions":
        return dispatcher.state_manager.list_sessions()

    if name == "list_agents":
        return dispatcher.list_agents()

    if name == "validate":
        return dispatcher.validate_handshake(args["session_id"])

    return {"error": f"Unknown tool: {name}"}


async def _async_main():
    """Async entry point for MCP stdio transport."""
    server = _build_server()
    await run_stdio(server)


def main():
    """CLI entry point (uap-mcp)."""
    if not HAS_MCP:
        print(
            "ERROR: The 'mcp' package is required for the MCP server.\n"
            "Install it with:  pip install 'uap-protocol[mcp]'",
            file=sys.stderr,
        )
        sys.exit(1)

    import asyncio
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
