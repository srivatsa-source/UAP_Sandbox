"""
UAP MCP Server — Model Context Protocol entry point.
Exposes the pure State Router as MCP tools over stdio transport.
"""

from __future__ import annotations

import json
import sys
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError as e:
    import sys
    print(f"DEBUG: {e}", file=sys.stderr)
    HAS_MCP = False

from uap.core.protocol import StateManager
from uap.dispatcher import Dispatcher, AgentConfig

def _build_server() -> "Server":
    """Construct and configure the minimal UAP MCP server."""
    server = Server("uap-protocol")
    dispatcher = Dispatcher()

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
            name="dispatch_raw",
            description="Dispatch a task to a dynamically defined UAP agent using OpenAI or Ollama backends.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "task": {"type": "string"},
                    "session_id": {"type": "string", "description": "Existing session ID (optional)."},
                    "backend": {"type": "string", "enum": ["openai", "ollama", "mock"], "default": "openai"},
                    "model": {"type": "string", "default": "gpt-4o"},
                    "system_prompt": {"type": "string", "description": "The agent's personality and instructions."},
                    "user_email": {"type": "string", "description": "The verified user email to pull API keys from the Keyring Vault. Required for OpenAI."}
                },
                "required": ["agent_id", "task", "system_prompt"],
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
            description="List all saved ACT sessions on disk.",
            inputSchema={"type": "object", "properties": {}},
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
    if name == "create_session":
        act = dispatcher.state_manager.create_session(args["objective"])
        dispatcher.state_manager.save_session(act.session_id)
        return {"session_id": act.session_id, "act": act.to_dict()}

    if name == "dispatch_raw":
        config_override = {
            "agent_id": args["agent_id"],
            "system_prompt": args["system_prompt"],
            "model": args.get("model", "gpt-4o"),
            "backend": args.get("backend", "openai")
        }
        return dispatcher.dispatch(
            agent_id=args["agent_id"],
            task=args["task"],
            session_id=args.get("session_id"),
            config_override=config_override,
            user_email=args.get("user_email")
        )

    if name == "get_session":
        act = dispatcher.state_manager.get_session(args["session_id"])
        if act:
            return act.to_dict()
        return {"error": f"Session {args['session_id']} not found"}

    if name == "list_sessions":
        return dispatcher.state_manager.list_sessions()

    return {"error": f"Unknown tool: {name}"}

async def _async_main():
    server = _build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

def main():
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