import asyncio
import json
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.text import Text
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

console = Console()

async def main():
    console.print(Panel("[bold #FFD580]UAP MCP Client Test: Real-Time Agent Handoff[/]", border_style="#E040FB"))
    
    server_params = StdioServerParameters(
        command="uap", 
        args=["start"],
        env=os.environ.copy()
    )
    
    console.print("[dim]Connecting to UAP MCP Server via stdio...[/dim]")
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            console.print("[bold #00E676]✓ Connection established[/]")
            
            await session.initialize()
            console.print("[bold #00E676]✓ MCP Protocol Handshake complete[/]\n")
            
            # Step 1: Create Session
            console.print("[bold #FFA500]► STEP 1: Creating UAP Session (ACT)[/]")
            create_res = await session.call_tool(
                "create_session", 
                arguments={"objective": "Analyze user request and build a mock feature"}
            )
            session_data = json.loads(create_res.content[0].text)
            session_id = session_data["session_id"]
            console.print(f"Session Created: [bold cyan]{session_id}[/]")
            console.print(JSON(json.dumps(session_data)))
            console.print()
            
            # Step 2: Dispatch to Router
            console.print("[bold #FFA500]► STEP 2: Dispatching task to Router Agent via MCP[/]")
            console.print("[dim]Simulating Claude Desktop handing a task to the UAP router over JSON-RPC...[/dim]")
            
            router_args = {
                "agent_id": "router_agent",
                "session_id": session_id,
                "task": "User wants to build a new feature. Please route appropriately.",
                "system_prompt": "You are the UAP router. Analyze the user's intent, summarize context, and hand off to the worker.",
                "backend": "mock",
                "model": "mock"
            }
            
            router_res = await session.call_tool("dispatch_raw", arguments=router_args)
            if router_res.isError:
                console.print(f"[bold red]Tool Call Error:[/] {router_res.content[0].text}")
                return
            
            try:
                router_data = json.loads(router_res.content[0].text)
            except json.JSONDecodeError:
                console.print(f"[bold red]JSON Error from Router:[/] {router_res.content[0].text}")
                return
            
            console.print(Panel(
                router_data["response"]["answer"], 
                title="[bold #FF6B35]Router Agent Response[/]", 
                border_style="#FF6B35"
            ))
            
            act_state = router_data["act"]
            
            # Extract only key fields of ACT to keep UI clean
            summary_act = {
                "session_id": act_state["session_id"],
                "phase": act_state["phase"],
                "task_chain": act_state["task_chain"],
                "context_summary": act_state["context_summary"],
                "handoff_reason": act_state["handoff_reason"],
                "next_agent_hint": act_state["next_agent_hint"]
            }
            
            console.print("[bold #FFD580]Updated ACT State (After Router):[/]")
            console.print(JSON(json.dumps(summary_act)))
            console.print()
            
            # Verify handoff requirement
            next_agent = act_state.get("next_agent_hint")
            if next_agent:
                console.print(f"[bold #00E676]Router requested handoff to:[/] [bold cyan]{next_agent}[/]\n")
                
                # Step 3: Dispatch to Worker
                console.print(f"[bold #FFA500]► STEP 3: Handoff to Worker Agent ({next_agent})[/]")
                console.print(f"[dim]Passing Session ID '{session_id}' to maintain protocol context...[/dim]")
                
                worker_args = {
                    "agent_id": next_agent,
                    "session_id": session_id,
                    "task": "Please continue the work based on the ACT.",
                    "system_prompt": "You are the Worker. Execute tasks based on router's context and return success.",
                    "backend": "mock",
                    "model": "mock"
                }
                
                worker_res = await session.call_tool("dispatch_raw", arguments=worker_args)
                try:
                    worker_data = json.loads(worker_res.content[0].text)
                except json.JSONDecodeError:
                    console.print(f"[bold red]JSON Error from Worker:[/] {worker_res.content[0].text}")
                    return
                
                console.print(Panel(
                    worker_data["response"]["answer"], 
                    title=f"[bold #FF4D6D]Worker Agent ({next_agent}) Response[/]", 
                    border_style="#FF4D6D"
                ))
                
                final_act = worker_data["act"]
                final_summary_act = {
                    "session_id": final_act["session_id"],
                    "phase": final_act["phase"],
                    "task_chain": final_act["task_chain"],
                    "context_summary": final_act["context_summary"],
                    "handoff_reason": final_act["handoff_reason"],
                    "next_agent_hint": final_act["next_agent_hint"]
                }
                
                console.print("[bold #FFD580]Final ACT State (After Worker):[/]")
                console.print(JSON(json.dumps(final_summary_act)))
                console.print()
            
            console.print("[bold #00E676]Success! Multi-agent handoff via MCP completed flawlessly.[/]")

if __name__ == "__main__":
    asyncio.run(main())
