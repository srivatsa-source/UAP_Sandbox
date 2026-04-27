"""
UAP Dispatcher - API Middleman
Routes tasks to external agent models dynamically, acting as a stateless pipe
for the ACT lifecycle.
"""

import json
import re
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from contextlib import AsyncExitStack

# MCP Client Protocol
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from uap.core.protocol import StateManager, ACT
from uap.core.agent_protocol import AgentProtocol, TextJSONProtocol, NativeToolProtocol
from uap.providers import registry

@dataclass
class AgentConfig:
    """Configuration for an external agent."""
    agent_id: str
    system_prompt: str
    model: str = "gpt-4o"
    backend: str = "openai"  # openai or ollama
    protocol: str = "text_json"  # text_json or native_tool
    metadata: dict = field(default_factory=dict)

class Dispatcher:
    """
    Routes tasks to appropriate agents and manages ACT handoffs.
    Purely a state router.
    """
    
    def __init__(self):
        self.state_manager = StateManager()
        self.agents: dict[str, AgentConfig] = {}
        self.protocols = {
            "text_json": TextJSONProtocol(),
            "native_tool": NativeToolProtocol()
        }
    
    def register_agent(self, config: AgentConfig) -> None:
        self.agents[config.agent_id] = config
        
    def list_agents(self) -> list[AgentConfig]:
        return list(self.agents.values())
    
    def dispatch(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        task: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        user_email: Optional[str] = None
    ) -> dict:
        """
        Dispatch a task to an agent. Allows dynamic injection of agent config if not pre-registered.
        """
        if session_id:
            act = self.state_manager.get_session(session_id)
            if not act:
                raise ValueError(f"Session {session_id} not found")
        else:
            task_str = task or ""
            act = self.state_manager.create_session(task_str)
        
        if config_override:
            agent = AgentConfig(**config_override)
        else:
            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not registered and no config_override provided.")
            
        protocol = self.protocols.get(agent.protocol, self.protocols["text_json"])
        
        try:
            provider = registry.get(agent.backend)
        except KeyError:
            return {
                "response": {
                    "answer": f"ERROR: Unknown backend: {agent.backend}",
                    "state_updates": {"context_summary": f"Unknown backend: {agent.backend}"}
                },
                "act": act.to_dict()
            }

        # Handle task continuation context
        task_str = task
        if not task_str:
            task_str = (
                f"=== CONTINUE FROM ACT ===\n"
                f"Objective: {act.current_objective}\n"
                f"Context: {act.context_summary}\n"
                f"Handoff Reason: {act.handoff_reason}\n"
                f"\nContinue the work based on the ACT above. No user re-prompting needed.\n"
            )

        prompt, sys_instr, tools = protocol.format_request(
            system_prompt=agent.system_prompt,
            task=task_str,
            act_state=act.to_dict()
        )
        
        raw_response = provider.call(
            prompt=prompt,
            model=agent.model,
            user_email=user_email,
            system_instruction=sys_instr,
            tools=tools
        )
        
        parsed = protocol.parse_response(raw_response)
        
        if "state_updates" in parsed:
            updates = parsed["state_updates"]
            act = self.state_manager.apply_state_updates(act.session_id, updates, agent.agent_id)
            if hasattr(self.state_manager, 'save_session'):
                self.state_manager.save_session(act.session_id)
            
        return {
            "response": parsed,
            "act": act.to_dict()
        }

    def handoff(self, session_id: str, to_agent_id: str, config_override: Optional[Dict[str, Any]] = None, user_email: Optional[str] = None) -> dict:
        return self.dispatch(agent_id=to_agent_id, session_id=session_id, config_override=config_override, user_email=user_email)

    async def list_mcp_tools(self, server_command: str, server_args: list[str]) -> list[dict]:
        """
        Connect to an external MCP server as a client and list available tools.
        This provides agents with an index of capabilities they can invoke via UAP.
        """
        server_params = StdioServerParameters(command=server_command, args=server_args)
        
        async with AsyncExitStack() as stack:
            # Create a stdio connection to the external MCP server
            stdio_transport = await stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            
            # Initialize an MCP client session
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            # Pull available tools
            tools_response = await session.list_tools()
            
            return [{"name": t.name, "description": t.description} for t in tools_response.tools]

    async def invoke_mcp_tool(
        self,
        session_id: str,
        agent_id: str,
        server_command: str,
        server_args: list[str],
        tool_name: str,
        tool_args: dict
    ) -> dict:
        """
        Invoke an MCP tool on behalf of an A2A agent, logging the execution to the ACT lineage.
        """
        act = self.state_manager.get_session(session_id)
        if not act:
            raise ValueError(f"Session {session_id} not found")
            
        server_params = StdioServerParameters(command=server_command, args=server_args)
        
        try:
            async with AsyncExitStack() as stack:
                stdio_transport = await stack.enter_async_context(stdio_client(server_params))
                read, write = stdio_transport
                
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                
                # Actually invoke the external tool
                result = await session.call_tool(tool_name, arguments=tool_args)
                
                tool_output = []
                for c in result.content:
                    if hasattr(c, "text"):
                        tool_output.append(c.text)
                    elif isinstance(c, dict) and "text" in c:
                        tool_output.append(c["text"])
                        
                # Log execution to ACT for transparent telemetry (A2A identity mapping)
                tool_usage = {
                    "tool": tool_name,
                    "args": tool_args,
                    "server": server_command,
                    "status": "success" if not result.isError else "error",
                    "output_preview": tool_output[0][:100] if tool_output else ""
                }
                
                self.state_manager.apply_state_updates(
                    session_id=session_id,
                    state_updates={"tool_usage": [tool_usage]},
                    agent_id=agent_id
                )
                self.state_manager.save_session(session_id)
                
                return {
                    "status": "success" if not result.isError else "error",
                    "result": tool_output
                }
                
        except Exception as e:
            # Always track failure in the ACT state
            tool_usage = {
                "tool": tool_name,
                "args": tool_args,
                "server": server_command,
                "status": "error",
                "error_details": str(e)
            }
            self.state_manager.apply_state_updates(
                session_id=session_id,
                state_updates={"tool_usage": [tool_usage]},
                agent_id=agent_id
            )
            self.state_manager.save_session(session_id)
            
            return {
                "status": "error",
                "error": str(e)
            }
