"""
UAP CLI - Universal Agent Protocol Command Line Interface
Connect AI agents, share state, run tasks from your terminal.

Usage:
    uap new "Build a REST API"
    uap run <session_id> --agents planner,coder,reviewer
    uap agents list
    uap agents add github:user/repo
    uap config set groq_api_key <your-key>
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint
import json

app = typer.Typer(
    name="uap",
    help="Universal Agent Protocol - Connect AI agents via shared state",
    add_completion=False
)

console = Console()

# Sub-commands
agents_app = typer.Typer(help="Manage agents")
config_app = typer.Typer(help="Manage configuration")
sessions_app = typer.Typer(help="Manage sessions")
auth_app = typer.Typer(help="Authentication & agent linking")

app.add_typer(agents_app, name="agents")
app.add_typer(config_app, name="config")
app.add_typer(sessions_app, name="sessions")
app.add_typer(auth_app, name="auth")


# =============================================================================
# MAIN COMMANDS
# =============================================================================

@app.command()
def new(
    task: str = typer.Argument(..., help="The task to accomplish"),
    agents: str = typer.Option(
        "planner,coder,reviewer",
        "--agents", "-a",
        help="Comma-separated list of agents to use"
    ),
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Automatically chain all agents"
    )
):
    """
    Start a new UAP session with a task.
    
    Example:
        uap new "Build a REST API endpoint" --agents planner,coder
    """
    from uap.dispatcher import Dispatcher
    from uap.registry import AgentRegistry
    
    with console.status("[bold green]Initializing UAP..."):
        dispatcher = Dispatcher()
        registry = AgentRegistry()
        
        # Parse agents
        agent_list = [a.strip() for a in agents.split(",")]
        
        # Register agents
        for agent_id in agent_list:
            agent = registry.get(agent_id)
            if agent:
                dispatcher.register_agent(agent)
            else:
                console.print(f"[yellow]Warning: Agent '{agent_id}' not found, skipping[/yellow]")
        
        if not dispatcher.list_agents():
            console.print("[red]No valid agents found. Run 'uap agents list' to see available agents.[/red]")
            raise typer.Exit(1)
    
    console.print(f"\n[bold cyan]UAP Session Starting[/bold cyan]")
    console.print(f"Task: {task}")
    console.print(f"Agents: {', '.join(agent_list)}\n")
    
    if auto:
        # Run full chain automatically
        with console.status("[bold green]Running agent chain..."):
            result = dispatcher.run_chain(task, agent_list)
        
        _display_chain_result(result)
    else:
        # Run first agent only, show session ID for continuation
        first_agent = agent_list[0]
        
        with console.status(f"[bold green]Running {first_agent}..."):
            result = dispatcher.dispatch(agent_id=first_agent, task=task)
        
        _display_single_result(result, first_agent, agent_list)


@app.command()
def run(
    session_id: str = typer.Argument(..., help="Session ID to continue"),
    agent: str = typer.Option(
        None,
        "--agent", "-a",
        help="Specific agent to run (defaults to next suggested)"
    ),
    task: str = typer.Option(
        None,
        "--task", "-t",
        help="New task to add (optional)"
    )
):
    """
    Continue an existing session with an agent.
    
    Example:
        uap run abc123 --agent coder
        uap run abc123  # Uses suggested next agent
    """
    from uap.dispatcher import Dispatcher
    from uap.registry import AgentRegistry
    from uap.protocol import StateManager
    
    dispatcher = Dispatcher()
    registry = AgentRegistry()
    state_manager = StateManager()
    
    # Load session
    act = state_manager.get_session(session_id)
    if not act:
        console.print(f"[red]Session '{session_id}' not found[/red]")
        raise typer.Exit(1)
    
    # Determine agent
    if not agent:
        agent = act.next_agent_hint or "coder"
        console.print(f"[dim]Using suggested agent: {agent}[/dim]")
    
    # Get agent config
    agent_config = registry.get(agent)
    if not agent_config:
        console.print(f"[red]Agent '{agent}' not found[/red]")
        raise typer.Exit(1)
    
    dispatcher.register_agent(agent_config)
    
    with console.status(f"[bold green]Running {agent}..."):
        if task:
            result = dispatcher.dispatch(agent_id=agent, session_id=session_id, task=task)
        else:
            result = dispatcher.handoff(session_id=session_id, to_agent_id=agent)
    
    _display_single_result(result, agent, [])


@app.command()
def status(
    session_id: str = typer.Argument(..., help="Session ID to check")
):
    """
    Show the status of a session.
    
    Example:
        uap status abc123
    """
    from uap.protocol import StateManager
    
    state_manager = StateManager()
    act = state_manager.get_session(session_id)
    
    if not act:
        console.print(f"[red]Session '{session_id}' not found[/red]")
        raise typer.Exit(1)
    
    _display_act(act.to_dict())


@app.command()
def version():
    """Show UAP version."""
    from uap import __version__
    console.print(f"UAP v{__version__}")


# =============================================================================
# AGENTS COMMANDS
# =============================================================================

@agents_app.command("list")
def agents_list():
    """List all available agents."""
    from uap.registry import AgentRegistry
    
    registry = AgentRegistry()
    agents = registry.list_all()
    
    table = Table(title="Available Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Source", style="dim")
    table.add_column("Model", style="yellow")
    
    for agent in agents:
        table.add_row(
            agent.agent_id,
            agent.agent_type,
            agent.source,
            agent.model
        )
    
    console.print(table)


@agents_app.command("add")
def agents_add(
    repo: str = typer.Argument(..., help="GitHub repo (e.g., github:user/repo or user/repo)")
):
    """
    Install an agent from GitHub.
    
    Example:
        uap agents add github:awesome-dev/fastapi-agent
        uap agents add awesome-dev/fastapi-agent
    """
    from uap.registry import AgentRegistry
    
    registry = AgentRegistry()
    
    with console.status(f"[bold green]Installing agent from {repo}..."):
        try:
            agent = registry.install_from_github(repo)
            console.print(f"[green]✓ Installed agent: {agent.agent_id}[/green]")
            console.print(f"  Type: {agent.agent_type}")
            console.print(f"  Model: {agent.model}")
        except Exception as e:
            console.print(f"[red]Failed to install: {e}[/red]")
            raise typer.Exit(1)


@agents_app.command("remove")
def agents_remove(
    agent_id: str = typer.Argument(..., help="Agent ID to remove")
):
    """Remove an installed agent."""
    from uap.registry import AgentRegistry
    
    registry = AgentRegistry()
    
    try:
        if registry.uninstall(agent_id):
            console.print(f"[green]✓ Removed agent: {agent_id}[/green]")
        else:
            console.print(f"[yellow]Agent '{agent_id}' not found[/yellow]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@agents_app.command("info")
def agents_info(
    agent_id: str = typer.Argument(..., help="Agent ID to inspect")
):
    """Show detailed information about an agent."""
    from uap.registry import AgentRegistry
    
    registry = AgentRegistry()
    agent = registry.get(agent_id)
    
    if not agent:
        console.print(f"[red]Agent '{agent_id}' not found[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]{agent.agent_id}[/bold]\n\n"
        f"Type: {agent.agent_type}\n"
        f"Model: {agent.model}\n"
        f"Backend: {agent.backend}\n"
        f"Source: {agent.source}\n\n"
        f"[dim]System Prompt:[/dim]\n{agent.system_prompt[:500]}...",
        title="Agent Info"
    ))


@agents_app.command("search")
def agents_search(
    query: str = typer.Argument(..., help="Search query")
):
    """Search GitHub for UAP agents."""
    from uap.registry import AgentRegistry
    
    registry = AgentRegistry()
    
    with console.status("[bold green]Searching GitHub..."):
        results = registry.search_github(query)
    
    if not results:
        console.print("[yellow]No agents found[/yellow]")
        return
    
    table = Table(title="GitHub UAP Agents")
    table.add_column("Repo", style="cyan")
    table.add_column("Description")
    table.add_column("Stars", style="yellow")
    
    for r in results:
        table.add_row(r["repo"], r["description"][:50], str(r["stars"]))
    
    console.print(table)
    console.print("\n[dim]Install with: uap agents add <repo>[/dim]")


# =============================================================================
# CONFIG COMMANDS
# =============================================================================

@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="Config value")
):
    """
    Set a configuration value.
    
    Example:
        uap config set groq_api_key gsk_xxx
        uap config set default_backend ollama
    """
    from uap.config import set_config
    
    set_config(key, value)
    
    # Mask API keys in output
    display_value = value[:8] + "..." if "key" in key.lower() else value
    console.print(f"[green]✓ Set {key} = {display_value}[/green]")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Config key")
):
    """Get a configuration value."""
    from uap.config import get_config_value
    
    value = get_config_value(key)
    if value:
        # Mask API keys
        display_value = value[:8] + "..." if "key" in key.lower() and value else value
        console.print(f"{key} = {display_value}")
    else:
        console.print(f"[yellow]{key} is not set[/yellow]")


@config_app.command("list")
def config_list():
    """List all configuration values."""
    from uap.config import get_config
    
    config = get_config()
    
    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    
    for key, value in config.items():
        # Mask secrets
        if "key" in key.lower() and value:
            display = value[:8] + "..." if len(str(value)) > 8 else value
        else:
            display = str(value)
        table.add_row(key, display)
    
    console.print(table)


@config_app.command("path")
def config_path():
    """Show configuration file path."""
    from uap.config import get_config_path, get_uap_home
    
    console.print(f"UAP Home: {get_uap_home()}")
    console.print(f"Config: {get_config_path()}")


# =============================================================================
# AUTH COMMANDS - Gmail-Federated Agent Linking
# =============================================================================

@auth_app.command("login")
def auth_login():
    """
    Sign in with Google (Gmail identity anchor).
    
    This authenticates you via OAuth and enables Gemini access.
    Other agents can then be linked to your Gmail identity.
    
    Example:
        uap auth login
    """
    from uap.oauth import UAPOAuth
    
    oauth = UAPOAuth()
    
    with console.status("[bold green]Opening browser for Google sign-in..."):
        try:
            creds = oauth.authenticate()
            if creds:
                user_info = oauth.get_user_info(creds)
                email = user_info.get("email", "unknown")
                console.print(f"[green]✓ Signed in as {email}[/green]")
                console.print(f"[cyan]Gemini is now linked via OAuth[/cyan]")
                console.print(f"\n[dim]Link other agents: uap auth link openai[/dim]")
        except Exception as e:
            console.print(f"[red]Authentication failed: {e}[/red]")
            raise typer.Exit(1)


@auth_app.command("status")
def auth_status():
    """
    Show authentication status and linked agents.
    
    Example:
        uap auth status
    """
    from uap.oauth import UAPOAuth
    from uap.vault import get_linked_agents
    
    oauth = UAPOAuth()
    
    if not oauth.is_authenticated():
        console.print("[yellow]Not signed in[/yellow]")
        console.print("[dim]Sign in with: uap auth login[/dim]")
        return
    
    creds = oauth.load_credentials()
    user_info = oauth.get_user_info(creds)
    email = user_info.get("email", "unknown")
    
    console.print(f"[green]✓ Signed in as {email}[/green]\n")
    
    # Show linked agents
    linked = get_linked_agents(email)
    
    table = Table(title="Linked Agents")
    table.add_column("Agent", style="cyan")
    table.add_column("Provider")
    table.add_column("Status", style="green")
    table.add_column("Linked At", style="dim")
    
    for agent_id, info in linked.items():
        status = ""
        if info.get("oauth_based") and info.get("linked"):
            status = "[blue]OAUTH[/blue]"
        elif info.get("linked"):
            status = "[green]LINKED[/green]"
        else:
            status = "[red]NOT LINKED[/red]"
        
        table.add_row(
            info.get("name", agent_id),
            info.get("provider", ""),
            status,
            info.get("linked_at", "")[:16] if info.get("linked_at") else "-"
        )
    
    console.print(table)


@auth_app.command("link")
def auth_link(
    provider: str = typer.Argument(..., help="Provider to link (openai, anthropic, mistral, groq)"),
    api_key: str = typer.Option(None, "--key", "-k", help="API key (will prompt if not provided)")
):
    """
    Link an AI agent to your Gmail identity.
    
    The API key is encrypted and stored locally, tied to your Gmail.
    
    Example:
        uap auth link openai
        uap auth link anthropic --key sk-ant-xxx
    """
    from uap.oauth import UAPOAuth
    from uap.vault import store_credential, get_linked_agents
    
    PROVIDERS = {
        "openai": {"name": "GPT-4", "url": "https://platform.openai.com/api-keys"},
        "anthropic": {"name": "Claude", "url": "https://console.anthropic.com/settings/keys"},
        "mistral": {"name": "Mistral", "url": "https://console.mistral.ai/api-keys/"},
        "groq": {"name": "Groq", "url": "https://console.groq.com/keys"},
    }
    
    if provider.lower() == "gemini":
        console.print("[cyan]Gemini is linked via OAuth (uap auth login), not API key[/cyan]")
        return
    
    if provider.lower() not in PROVIDERS:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        console.print(f"[dim]Available: {', '.join(PROVIDERS.keys())}[/dim]")
        raise typer.Exit(1)
    
    # Check authentication
    oauth = UAPOAuth()
    if not oauth.is_authenticated():
        console.print("[yellow]Please sign in first: uap auth login[/yellow]")
        raise typer.Exit(1)
    
    creds = oauth.load_credentials()
    user_info = oauth.get_user_info(creds)
    email = user_info.get("email", "unknown")
    
    prov_info = PROVIDERS[provider.lower()]
    
    # Get API key
    if not api_key:
        console.print(f"\nTo link {prov_info['name']}, you need an API key from:")
        console.print(f"[cyan]{prov_info['url']}[/cyan]\n")
        api_key = typer.prompt("Enter API key", hide_input=True)
    
    if not api_key:
        console.print("[red]API key required[/red]")
        raise typer.Exit(1)
    
    # Store credential
    success = store_credential(email, provider.lower(), api_key, {
        "linked_via": "cli",
        "user_email": email
    })
    
    if success:
        console.print(f"[green]✓ {prov_info['name']} linked to {email}[/green]")
        console.print(f"[dim]Key encrypted and stored in ~/.uap/vault/[/dim]")
    else:
        console.print("[red]Failed to store credential[/red]")
        raise typer.Exit(1)


@auth_app.command("unlink")
def auth_unlink(
    provider: str = typer.Argument(..., help="Provider to unlink")
):
    """
    Unlink an agent from your Gmail identity.
    
    Example:
        uap auth unlink openai
    """
    from uap.oauth import UAPOAuth
    from uap.vault import unlink_agent, get_linked_agents
    
    if provider.lower() == "gemini":
        console.print("[yellow]Gemini is linked via OAuth. Use 'uap auth logout' to sign out.[/yellow]")
        return
    
    oauth = UAPOAuth()
    if not oauth.is_authenticated():
        console.print("[yellow]Not signed in[/yellow]")
        raise typer.Exit(1)
    
    creds = oauth.load_credentials()
    user_info = oauth.get_user_info(creds)
    email = user_info.get("email", "unknown")
    
    linked = get_linked_agents(email)
    if not linked.get(provider.lower(), {}).get("linked"):
        console.print(f"[yellow]{provider} is not linked[/yellow]")
        return
    
    if unlink_agent(email, provider.lower()):
        console.print(f"[green]✓ {provider} unlinked[/green]")
    else:
        console.print("[red]Failed to unlink[/red]")


@auth_app.command("logout")
def auth_logout():
    """
    Sign out and remove OAuth credentials.
    
    Note: Linked agent API keys are preserved.
    
    Example:
        uap auth logout
    """
    from uap.oauth import UAPOAuth
    
    oauth = UAPOAuth()
    
    if not oauth.is_authenticated():
        console.print("[yellow]Not signed in[/yellow]")
        return
    
    oauth.logout()
    console.print("[green]✓ Signed out[/green]")
    console.print("[dim]Linked agent API keys are preserved[/dim]")


@app.command()
def federated(
    task: str = typer.Argument(..., help="The task to accomplish"),
    start: str = typer.Option(
        "gemini",
        "--start", "-s",
        help="Starting agent (gemini, openai, anthropic, mistral, groq)"
    ),
    auto_handoff: bool = typer.Option(
        True,
        "--auto/--no-auto",
        help="Enable automatic agent handoff"
    ),
    max_steps: int = typer.Option(
        3,
        "--max-steps", "-m",
        help="Maximum handoff steps"
    )
):
    """
    Run a task using Gmail-federated agents.
    
    Uses real API calls to Claude, GPT, Gemini, etc. - all linked to your Gmail.
    Agents share context via ACT (Agent Context Token) and can hand off to each other.
    
    Example:
        uap federated "Analyze this code and suggest improvements"
        uap federated "Write a REST API" --start openai --max-steps 4
    """
    from uap.oauth import UAPOAuth
    from uap.vault import get_linked_agents, get_credential
    from uap.dispatcher import Dispatcher
    import hashlib
    from datetime import datetime
    
    # Agent info
    AGENT_INFO = {
        "gemini": {"name": "Gemini", "model": "gemini-1.5-flash"},
        "openai": {"name": "GPT-4", "model": "gpt-4-turbo"},
        "anthropic": {"name": "Claude", "model": "claude-3-sonnet-20240229"},
        "mistral": {"name": "Mistral", "model": "mistral-large-latest"},
        "groq": {"name": "Groq", "model": "llama-3.1-70b-versatile"},
    }
    
    # Check auth
    oauth = UAPOAuth()
    if not oauth.is_authenticated():
        console.print("[yellow]Please sign in first: uap auth login[/yellow]")
        raise typer.Exit(1)
    
    creds = oauth.load_credentials()
    user_info = oauth.get_user_info(creds)
    email = user_info.get("email", "unknown")
    
    console.print(f"[dim]Identity: {email}[/dim]\n")
    
    # Get linked agents
    linked = get_linked_agents(email)
    available = [aid for aid, info in linked.items() if info.get("linked")]
    
    if not available:
        console.print("[red]No agents linked[/red]")
        console.print("[dim]Link agents with: uap auth link openai[/dim]")
        raise typer.Exit(1)
    
    if start not in available:
        console.print(f"[red]{start} is not linked[/red]")
        console.print(f"[dim]Available: {', '.join(available)}[/dim]")
        raise typer.Exit(1)
    
    # Create ACT context
    act_id = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:12]
    console.print(f"[cyan]ACT:{act_id}[/cyan] - Shared context initialized\n")
    
    # Run chain
    dispatcher = Dispatcher(oauth_credentials=creds)
    current = start
    accumulated_context = ""
    chain = []
    
    for step in range(max_steps):
        if current not in available:
            console.print(f"[yellow]{current} not linked, stopping[/yellow]")
            break
        
        agent_name = linked[current]["name"]
        console.print(f"[bold cyan]{step + 1}. {agent_name}[/bold cyan]")
        
        # Build prompt
        other_agents = [AGENT_INFO[a]["name"] for a in available if a != current]
        prompt = f"""You are {agent_name} working in a multi-agent UAP system.

SHARED CONTEXT with: {', '.join(other_agents) if other_agents else 'None'}

TASK: {task}

CONTEXT FROM PREVIOUS AGENTS:
{accumulated_context if accumulated_context else '(You are first in chain)'}

Instructions:
1. Provide your contribution
2. If another agent's expertise would help, say: HANDOFF TO: [agent name]
3. Available agents: {', '.join(other_agents)}

Your response:"""
        
        # Call agent
        with console.status(f"[green]{agent_name} processing..."):
            try:
                model = AGENT_INFO[current]["model"]
                if current == "gemini":
                    response = dispatcher._call_gemini(prompt, model)
                elif current == "openai":
                    response = dispatcher._call_openai(prompt, model, email)
                elif current == "anthropic":
                    response = dispatcher._call_anthropic(prompt, model, email)
                elif current == "mistral":
                    response = dispatcher._call_mistral(prompt, model, email)
                elif current == "groq":
                    response = dispatcher._call_groq(prompt, model)
                else:
                    response = f"Unknown backend: {current}"
            except Exception as e:
                response = f"Error: {e}"
        
        # Display response
        console.print(Panel(
            response[:500] + ("..." if len(response) > 500 else ""),
            border_style="dim"
        ))
        
        chain.append({"agent": current, "response": response})
        accumulated_context += f"\n\n[{agent_name}]:\n{response}"
        
        # Check handoff
        if auto_handoff and "HANDOFF TO:" in response.upper():
            next_agent = None
            for aid, info in linked.items():
                if info.get("linked") and aid != current:
                    if info["name"].upper() in response.upper():
                        next_agent = aid
                        break
            
            if next_agent:
                next_name = linked[next_agent]["name"]
                console.print(f"[yellow]→ Handoff to {next_name}[/yellow]\n")
                current = next_agent
                continue
        
        break
    
    # Summary
    console.print(f"\n[bold green]✓ Complete[/bold green] - {len(chain)} agents processed")
    console.print(f"[dim]ACT:{act_id} contains shared context from: {', '.join(c['agent'] for c in chain)}[/dim]")


# =============================================================================
# SESSIONS COMMANDS
# =============================================================================

@sessions_app.command("list")
def sessions_list():
    """List all saved sessions."""
    from uap.protocol import StateManager
    
    state_manager = StateManager()
    sessions = state_manager.list_sessions()
    
    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return
    
    table = Table(title="Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Objective")
    table.add_column("Agents", style="green")
    table.add_column("Tasks", style="yellow")
    table.add_column("Updated")
    
    for s in sessions[:20]:  # Show last 20
        table.add_row(
            s["session_id"],
            s["objective"][:40] + "..." if len(s.get("objective", "")) > 40 else s.get("objective", ""),
            str(s.get("agents", 0)),
            str(s.get("tasks", 0)),
            s.get("updated", "")[:16]
        )
    
    console.print(table)


@sessions_app.command("show")
def sessions_show(
    session_id: str = typer.Argument(..., help="Session ID")
):
    """Show full session details."""
    from uap.protocol import StateManager
    
    state_manager = StateManager()
    act = state_manager.get_session(session_id)
    
    if not act:
        console.print(f"[red]Session '{session_id}' not found[/red]")
        raise typer.Exit(1)
    
    _display_act(act.to_dict())


@sessions_app.command("export")
def sessions_export(
    session_id: str = typer.Argument(..., help="Session ID"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path")
):
    """Export session to JSON file."""
    from uap.protocol import StateManager
    
    state_manager = StateManager()
    act = state_manager.get_session(session_id)
    
    if not act:
        console.print(f"[red]Session '{session_id}' not found[/red]")
        raise typer.Exit(1)
    
    output_path = output or f"{session_id}.json"
    with open(output_path, "w") as f:
        json.dump(act.to_dict(), f, indent=2)
    
    console.print(f"[green]✓ Exported to {output_path}[/green]")


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def _display_single_result(result: dict, agent: str, remaining_agents: list):
    """Display result from a single agent run."""
    console.print(Panel(
        result.get("response", "No response"),
        title=f"[bold green]{agent}[/bold green]",
        border_style="green"
    ))
    
    session_id = result.get("session_id", "")
    console.print(f"\n[bold]Session ID:[/bold] {session_id}")
    
    # Show handoff info
    handoff = result.get("handoff_info", {})
    if handoff.get("ready_for_handoff"):
        console.print(f"[yellow]→ Handoff requested:[/yellow] {handoff.get('reason', '')}")
        next_agent = handoff.get("next_agent_hint", "")
        if next_agent:
            console.print(f"[cyan]→ Suggested next:[/cyan] {next_agent}")
            console.print(f"\n[dim]Continue with: uap run {session_id} --agent {next_agent}[/dim]")
    
    # Show remaining agents
    if remaining_agents and len(remaining_agents) > 1:
        remaining = remaining_agents[1:]
        console.print(f"\n[dim]Remaining agents: {', '.join(remaining)}[/dim]")
        console.print(f"[dim]Run all: uap new \"{result.get('act', {}).get('current_objective', '')}\" --agents {','.join(remaining_agents)} --auto[/dim]")


def _display_chain_result(result: dict):
    """Display result from a full chain run."""
    console.print("\n[bold cyan]Agent Chain Complete[/bold cyan]\n")
    
    for i, step in enumerate(result.get("chain", []), 1):
        agent = step.get("agent", "unknown")
        response = step.get("response", "")[:300]
        
        console.print(f"[bold]{i}. {agent}[/bold]")
        console.print(Panel(response + "...", border_style="dim"))
    
    # Validation
    validation = result.get("validation", {})
    if validation.get("valid"):
        console.print("[bold green]✓ ACT Handshake Valid[/bold green]")
    else:
        console.print("[bold red]✗ Handshake Validation Failed[/bold red]")
    
    console.print(f"\n[bold]Session ID:[/bold] {result.get('session_id')}")
    console.print(f"[dim]View details: uap status {result.get('session_id')}[/dim]")


def _display_act(act: dict):
    """Display ACT details."""
    console.print(Panel(
        f"[bold]Objective:[/bold] {act.get('current_objective', 'N/A')}\n\n"
        f"[bold]Context:[/bold] {act.get('context_summary', 'N/A')}\n\n"
        f"[bold]Last Agent:[/bold] {act.get('origin_agent', 'N/A')}\n"
        f"[bold]Handoff Reason:[/bold] {act.get('handoff_reason', 'None')}\n"
        f"[bold]Next Agent Hint:[/bold] {act.get('next_agent_hint', 'None')}",
        title=f"Session: {act.get('session_id')}"
    ))
    
    # Task chain
    if act.get("task_chain"):
        console.print("\n[bold]Task Chain:[/bold]")
        for i, task in enumerate(act["task_chain"], 1):
            console.print(f"  {i}. [{task.get('agent')}] {task.get('task', '')[:60]}")
    
    # Artifacts
    artifacts = act.get("artifacts", {})
    if any(artifacts.values()):
        console.print("\n[bold]Artifacts:[/bold]")
        if artifacts.get("code_snippets"):
            console.print(f"  Code snippets: {len(artifacts['code_snippets'])}")
        if artifacts.get("decisions"):
            console.print(f"  Decisions: {len(artifacts['decisions'])}")
        if artifacts.get("files_modified"):
            console.print(f"  Files: {', '.join(artifacts['files_modified'])}")
    
    # Handshake log
    if act.get("handshake_log"):
        console.print(f"\n[bold]Handshake Log:[/bold] {len(act['handshake_log'])} entries")
        unique_agents = set(log.get("agent") for log in act["handshake_log"])
        console.print(f"  Agents: {', '.join(unique_agents)}")


if __name__ == "__main__":
    app()
