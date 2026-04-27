import json
import asyncio
import click
import sys
import importlib.metadata
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box
from rich.syntax import Syntax

from uap.oauth import run_cli_oauth_flow, get_user_info, get_cached_user_profile, generate_agent_card
from uap.core.vault import get_linked_agents
from uap.mcp_server import main as run_mcp_server
from uap.core.protocol import StateManager
from uap.dispatcher import Dispatcher

from uap.cli_ui import (
    console,
    render_header,
    chat_loop,
    render_success,
    render_error,
    thinking,
    SUNSET_THEME,
    sunset_gradient
)

try:
    VERSION = importlib.metadata.version("uap-protocol")
except Exception:
    VERSION = "0.4.0"

THEME_ORANGE = "#FF8C00"
THEME_LIGHT = "#FFA500"

def render_dashboard():
    user_info = get_cached_user_profile() or {}
    email = user_info.get("email", "Not logged in")
    
    # 1. IDENTITY PANEL
    identity_table = Table.grid(padding=(0, 2))
    identity_table.add_column(style=f"bold {THEME_LIGHT}", justify="right")
    identity_table.add_column(style="bold white")
    
    if user_info:
        identity_table.add_row("Status", "[bold #00E676]Authenticated[/]")
        identity_table.add_row("User", email)
    else:
        identity_table.add_row("Status", "[bold #FF4D6D]Unauthenticated[/]")
        identity_table.add_row("Action", "Run 'uap login'")
    
    identity_panel = Panel(
        identity_table, 
        title="[bold white]Identity[/]", 
        border_style="#6A0DAD", 
        box=box.ROUNDED, 
        height=6
    )

    # 2. CONTROL PLANE COMMANDS
    cmds_table = Table.grid(padding=(0, 2))
    cmds_table.add_column(style=f"bold {THEME_LIGHT}")
    cmds_table.add_column(style="dim white")
    cmds_table.add_row("uap start", "Boot MCP transport layer")
    cmds_table.add_row("uap login", "Authorize via OAuth")
    cmds_table.add_row("uap chat", "Launch interactive shell")
    cmds_table.add_row("uap status", "Refresh telemetry & endpoints")
    
    commands_panel = Panel(
        cmds_table, 
        title="[bold white]Control Plane[/]", 
        border_style="#6A0DAD", 
        box=box.ROUNDED, 
        height=6
    )

    # 3. ENDPOINT TELEMETRY (Providers)
    table = Table(show_header=True, header_style=f"bold {THEME_LIGHT}", box=box.SIMPLE_HEAD, expand=True)
    table.add_column("Provider")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Last Sync")

    agents = get_linked_agents(email) if user_info else {}
    provider_types = {"Gemini": "Remote API", "GPT-4": "Remote API", "Ollama": "Local Engine"}
    
    has_agents = False
    if agents:
        for p_id, info in agents.items():
            p_name = info['name']
            p_type = provider_types.get(p_name, "Extension")
            if info.get("linked"):
                status_text = "[bold #00E676]● ACTIVE[/]"
                linked_at = info.get("linked_at", "N/A").split('T')[0]
            else:
                status_text = "[dim #FF4D6D]○ OFFLINE[/]"
                linked_at = "-"
                
            table.add_row(f"[bold white]{p_name}[/]", f"[dim]{p_type}[/]", status_text, linked_at)
            has_agents = True

    if not has_agents:
        table.add_row("-", "-", "-", "-")

    providers_panel = Panel(
        table, 
        title="[bold white]Endpoint Telemetry[/]", 
        border_style="#6A0DAD", 
        box=box.ROUNDED
    )

    # LAYOUT ASSEMBLY
    render_header()
    console.print(Columns([identity_panel, commands_panel], expand=True))
    console.print(providers_panel)
    console.print()

@click.group(invoke_without_command=True)
@click.version_option(VERSION, prog_name="uap")
@click.pass_context
def cli(ctx):
    """Universal Agent Protocol — Sunset-powered agent CLI."""
    if ctx.invoked_subcommand is None:
        render_dashboard()

@cli.command()
@click.option("--provider", type=click.Choice(['openai', 'anthropic', 'ollama', 'mock']), help="LLM Provider to use")
def chat(provider):
    """Start an interactive UAP chat session."""
    import uuid
    import os
    from uap.dispatcher import Dispatcher
    from uap.core.vault import get_linked_agents, store_credential

    user_info = get_cached_user_profile() or {}
    email = user_info.get("email", "local_user")
    
    if not provider:
        console.print(Text("  Choose LLM Provider for this session:", style="bold #FFD580"))
        provider = click.prompt("  Provider [openai/anthropic/ollama/mock]", default="anthropic")
    
    # Store CLI inputted key if they don't have it set and they aren't using Mock or Ollama
    if provider in ["openai", "anthropic"]:
        from uap.core.vault import get_credential
        if not get_credential(email, provider) and not os.environ.get(f"{provider.upper()}_API_KEY"):
            api_key = click.prompt(f"Enter API key for {provider}", hide_input=True)
            store_credential(email, provider, api_key)
            render_success(f"{provider.upper()} API Key saved to Vault securely.")

    dispatcher = Dispatcher()
    
    model_map = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "ollama": "llama3",
        "mock": "mock"
    }
    
    protocol_map = {
        "openai": "native_tool",
        "anthropic": "native_tool",
        "ollama": "text_json",
        "mock": "text_json"
    }
    
    # Provide REAL configuration
    router_agent_config = {
        "agent_id": "router_agent",
        "system_prompt": "You are the UAP router. Analyze the user's intent, summarize context, and hand off to the test_worker_01.",
        "model": model_map.get(provider, "mock"),
        "backend": provider,
        "protocol": protocol_map.get(provider, "text_json")
    }

    worker_agent_config = {
        "agent_id": "test_worker_01",
        "system_prompt": "You are the Worker. Execute tasks based on router's context and return success.",
        "model": model_map.get(provider, "mock"),
        "backend": provider,
        "protocol": protocol_map.get(provider, "text_json")
    }

    console.print(f"[dim]Booting UAP Pipeline -> [bold green]{provider.upper()}[/] using {protocol_map.get(provider, 'text_json')}...[/dim]\n")

    def _dispatch_prompt(prompt: str):
        session_id = None
        sm = dispatcher.state_manager
        sessions = sm.list_sessions()
        if sessions:
            session_id = sessions[-1]["session_id"]
            
        current_agent = "router_agent"
        loop_limit = 5
        
        for _ in range(loop_limit):
            with thinking(f"Awaiting {current_agent}..."):
                config = router_agent_config if current_agent == "router_agent" else worker_agent_config
                
                res = dispatcher.dispatch(
                    agent_id=current_agent,
                    session_id=session_id,
                    task=prompt,
                    config_override=config
                )
            
            prompt = None # Task is only provided on the first turn
            session_id = res["act"]["session_id"]
            
            answer = res.get("response", {}).get("answer", "No answer parsed.")
            updates = res.get("response", {}).get("state_updates", {})
            act_dict = res.get("act", {})
            
            next_agent = updates.get("next_agent_hint")
            handoff_reason = updates.get("handoff_reason")
            
            yield current_agent, answer, act_dict
            
            if handoff_reason and next_agent:
                current_agent = next_agent
                continue
            else:
                break

    def _state_provider() -> dict:
        sm = dispatcher.state_manager
        sessions = sm.list_sessions()
        if sessions:
            return sm.get_session(sessions[-1]["session_id"]).to_dict()
        return {"status": "No active ACT yet"}

    def _oauth_provider():
        try:
            from uap.oauth import run_cli_oauth_flow, get_user_info
            run_cli_oauth_flow()
            user_info = get_user_info()
            return True if user_info and user_info.get("email") else False
        except Exception as e:
            render_error(f"OAuth failed: {e}")
            return False

    chat_loop(
        dispatcher=_dispatch_prompt,
        state_provider=_state_provider,
        handoff_log_provider=lambda: [],
        oauth_provider=_oauth_provider
    )

@cli.command()
def login():
    """Login with Google OAuth to verify identity."""
    render_header()
    console.print(Text("  Initiating OAuth 2.0 flow...", style="bold #FFD580"))
    with thinking("Awaiting cryptograph validation"):
        try:
            run_cli_oauth_flow()
            user_info = get_user_info()
            render_success(f"Identity verified: {user_info.get('email')}")
        except Exception as e:
            render_error(f"Sequence failed: {e}")

@cli.command()
def status():
    """Show the current status of the UAP system and linked providers."""       
    render_dashboard()

@cli.command()
def start():
    """Start the UAP MCP Server on stdio."""
    from rich.console import Console as RichConsole
    err_console = RichConsole(stderr=True)
    # Using stderr so we don't corrupt the JSON-RPC stream on stdout
    err_console.print(f"\n[bold {THEME_ORANGE}]⚡ UAP MCP Server is active and listening on[/] [bold green]stdio[/]")
    err_console.print("[dim white]Awaiting JSON-RPC payloads from an MCP client (e.g., Claude Desktop, VS Code)...[/]")
    err_console.print("[dim]Press Ctrl+C to terminate.[/]\n")
    run_mcp_server()

@cli.command()
def agent_card():
    """Display the A2A Agent Card for the current user."""
    render_header()
    card = generate_agent_card()
    card_json = json.dumps(card, indent=2)
    syntax = Syntax(card_json, "json", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="A2A Agent Card", border_style="#E040FB", box=box.ROUNDED))

@cli.command()
@click.argument("server_command")
@click.argument("server_args", nargs=-1)
def discover_mcp(server_command, server_args):
    """Discover tools exposed by an external MCP server."""
    render_header()
    dispatcher = Dispatcher()
    console.print(f"[{THEME_LIGHT}]Connecting to external MCP server ({server_command})...[/]")
    
    try:
        with thinking("Discovering tools"):
            tools = asyncio.run(dispatcher.list_mcp_tools(server_command, list(server_args)))
        
        if not tools:
            console.print("[yellow]No tools discovered on this server.[/]")
            return
            
        table = Table(title="Discovered Tools", box=box.SIMPLE_HEAD)
        table.add_column("Tool Name", style="bold #00E676")
        table.add_column("Description", style="dim")
        
        for t in tools:
            table.add_row(t.get("name"), t.get("description", "")[:100])
        
        console.print(table)
    except Exception as e:
        render_error(f"Failed to discover tools: {e}")

@cli.command()
def sessions():
    """List active UAP sessions and their ACT states."""
    render_header()
    manager = StateManager()
    sessions = manager.list_sessions()
    
    if not sessions:
        console.print("[yellow]No active UAP sessions found.[/]")
        return
        
    table = Table(title="UAP Sessions (ACT State)", box=box.SIMPLE_HEAD)
    table.add_column("Session ID", style="bold #FFC44D")
    table.add_column("Objective", style="white")
    table.add_column("Agents", justify="right")
    table.add_column("Tasks", justify="right")
    table.add_column("Updated", style="dim")
    
    for s in sessions:
        table.add_row(
            s.get("session_id"), 
            s.get("objective") or "<none>", 
            str(s.get("agents", 0)), 
            str(s.get("tasks", 0)), 
            str(s.get("updated", ""))[:19]
        )
        
    console.print(table)

if __name__ == "__main__":
    cli()
