"""
UAP CLI - Universal Agent Protocol Command Line Interface
Built with Click for Gmail OAuth authentication.

Usage:
    uap-cli login      # Authenticate with Google
    uap-cli logout     # Clear credentials
    uap-cli whoami     # Show current user
    uap-cli new "task" # Start a new task
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="0.2.0", prog_name="uap-cli")
def cli():
    """UAP - Universal Agent Protocol
    
    Connect AI agents via Gmail OAuth identity.
    """
    pass


@cli.command()
@click.option('--force', '-f', is_flag=True, help='Force re-authentication')
def login(force: bool):
    """Authenticate with your Google account.
    
    Opens a browser window for Google OAuth consent.
    Credentials are saved to ~/.uap/credentials.json
    """
    from uap.oauth import (
        is_authenticated,
        run_cli_oauth_flow,
        get_user_info,
        clear_credentials,
        get_valid_credentials
    )
    
    if is_authenticated() and not force:
        console.print("[yellow]Already authenticated.[/yellow]")
        console.print("Use --force to re-authenticate.")
        
        # Show current user
        credentials = get_valid_credentials()
        if credentials:
            user_info = get_user_info(credentials)
            console.print(f"\n[green]Logged in as:[/green] {user_info.get('email')}")
        return
    
    if force:
        clear_credentials()
    
    console.print("[cyan]Opening browser for Google authentication...[/cyan]")
    console.print("[dim]Please complete the sign-in flow in your browser.[/dim]\n")
    
    try:
        credentials = run_cli_oauth_flow()
        
        # Fetch user info
        user_info = get_user_info(credentials)
        
        console.print(Panel(
            f"[bold green]✓ Authentication successful![/bold green]\n\n"
            f"Email: [cyan]{user_info.get('email')}[/cyan]\n"
            f"Name: {user_info.get('name', 'N/A')}",
            title="Welcome to UAP",
            border_style="green"
        ))
        
        console.print("\n[dim]Credentials saved to ~/.uap/credentials.json[/dim]")
        
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise click.Abort()


@cli.command()
def logout():
    """Clear stored credentials and log out."""
    from uap.oauth import clear_credentials, get_cached_user_profile
    
    profile = get_cached_user_profile()
    email = profile.get('email', 'unknown') if profile else 'unknown'
    
    if clear_credentials():
        console.print(f"[green]✓ Logged out successfully[/green]")
        console.print(f"[dim]Cleared credentials for {email}[/dim]")
    else:
        console.print("[yellow]No credentials to clear.[/yellow]")


@cli.command()
def whoami():
    """Show current authenticated user."""
    from uap.oauth import (
        is_authenticated,
        get_valid_credentials,
        get_user_info,
        get_cached_user_profile
    )
    
    if not is_authenticated():
        console.print("[yellow]Not authenticated.[/yellow]")
        console.print("Run [cyan]uap-cli login[/cyan] to authenticate.")
        return
    
    # Try cached profile first
    profile = get_cached_user_profile()
    
    if not profile:
        credentials = get_valid_credentials()
        if credentials:
            profile = get_user_info(credentials)
    
    if profile and 'email' in profile:
        table = Table(title="Current User", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        
        table.add_row("Email", profile.get('email', 'N/A'))
        table.add_row("Name", profile.get('name', 'N/A'))
        user_id = profile.get('id', 'N/A')
        table.add_row("User ID", (user_id[:16] + "...") if len(user_id) > 16 else user_id)
        
        console.print(table)
    else:
        console.print("[red]Could not fetch user info.[/red]")


@cli.command()
@click.argument('task')
@click.option('--agents', '-a', default='planner,coder,reviewer', 
              help='Comma-separated list of agents')
@click.option('--auto', is_flag=True, help='Auto-chain all agents')
def new(task: str, agents: str, auto: bool):
    """Start a new UAP session with a task.
    
    Example:
        uap-cli new "Build a REST API" --agents planner,coder
    """
    from uap.oauth import is_authenticated, get_valid_credentials, get_cached_user_profile
    from uap.dispatcher import Dispatcher
    from uap.registry import AgentRegistry
    
    if not is_authenticated():
        console.print("[red]Not authenticated.[/red]")
        console.print("Run [cyan]uap-cli login[/cyan] first.")
        raise click.Abort()
    
    # Get user email for session association
    profile = get_cached_user_profile()
    user_email = profile.get('email', 'unknown') if profile else 'unknown'
    
    console.print(f"[dim]User: {user_email}[/dim]")
    console.print(f"[cyan]Task:[/cyan] {task}")
    console.print(f"[cyan]Agents:[/cyan] {agents}\n")
    
    # Initialize dispatcher with OAuth credentials
    credentials = get_valid_credentials()
    dispatcher = Dispatcher(oauth_credentials=credentials)
    registry = AgentRegistry()
    
    # Parse and register agents
    agent_list = [a.strip() for a in agents.split(",")]
    
    for agent_id in agent_list:
        agent = registry.get(agent_id)
        if agent:
            dispatcher.register_agent(agent)
        else:
            console.print(f"[yellow]Warning: Agent '{agent_id}' not found[/yellow]")
    
    if not dispatcher.list_agents():
        console.print("[red]No valid agents found.[/red]")
        raise click.Abort()
    
    if auto:
        with console.status("[bold green]Running agent chain..."):
            result = dispatcher.run_chain(task, agent_list)
        
        console.print(Panel(
            f"Session: [cyan]{result['session_id']}[/cyan]\n"
            f"Agents: {len(result['chain'])} completed\n"
            f"Valid: {'✓' if result['validation']['valid'] else '✗'}",
            title="Chain Complete",
            border_style="green"
        ))
    else:
        first_agent = agent_list[0]
        
        with console.status(f"[bold green]Running {first_agent}..."):
            result = dispatcher.dispatch(agent_id=first_agent, task=task)
        
        console.print(Panel(
            f"Session: [cyan]{result['session_id']}[/cyan]\n"
            f"Agent: {first_agent}\n\n"
            f"Continue with:\n[dim]uap-cli run {result['session_id']} --agent coder[/dim]",
            title="Task Started",
            border_style="green"
        ))


@cli.command()
@click.argument('session_id')
@click.option('--agent', '-a', help='Agent to run')
def run(session_id: str, agent: str):
    """Continue an existing session."""
    from uap.oauth import is_authenticated, get_valid_credentials
    from uap.dispatcher import Dispatcher
    from uap.registry import AgentRegistry
    from uap.protocol import StateManager
    
    if not is_authenticated():
        console.print("[red]Not authenticated. Run 'uap-cli login' first.[/red]")
        raise click.Abort()
    
    credentials = get_valid_credentials()
    dispatcher = Dispatcher(oauth_credentials=credentials)
    registry = AgentRegistry()
    state_manager = StateManager()
    
    # Load session
    act = state_manager.get_session(session_id)
    if not act:
        console.print(f"[red]Session '{session_id}' not found.[/red]")
        raise click.Abort()
    
    # Determine agent
    if not agent:
        agent = act.next_agent_hint or "coder"
        console.print(f"[dim]Using suggested agent: {agent}[/dim]")
    
    agent_config = registry.get(agent)
    if not agent_config:
        console.print(f"[red]Agent '{agent}' not found.[/red]")
        raise click.Abort()
    
    dispatcher.register_agent(agent_config)
    
    with console.status(f"[bold green]Running {agent}..."):
        result = dispatcher.handoff(session_id=session_id, to_agent_id=agent)
    
    console.print(f"\n[bold]Response:[/bold]")
    console.print(result.get('response', 'No response')[:500])


@cli.command()
def sessions():
    """List all saved sessions."""
    from uap.oauth import is_authenticated, get_cached_user_profile
    from uap.protocol import StateManager
    
    if not is_authenticated():
        console.print("[yellow]Not authenticated.[/yellow]")
    
    profile = get_cached_user_profile()
    user_email = profile.get('email') if profile else None
    
    state_manager = StateManager()
    all_sessions = state_manager.list_sessions()
    
    if not all_sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return
    
    table = Table(title=f"UAP Sessions{' for ' + user_email if user_email else ''}")
    table.add_column("ID", style="cyan")
    table.add_column("Objective")
    table.add_column("Agents", justify="right")
    table.add_column("Updated")
    
    for session in all_sessions[:10]:
        objective = session.get('objective', '')
        table.add_row(
            session.get('session_id', 'N/A'),
            (objective[:40] + "...") if objective else "N/A",
            str(session.get('agents', 0)),
            session.get('updated', 'N/A')[:10]
        )
    
    console.print(table)


@cli.command()
def status():
    """Show UAP system status."""
    from uap.oauth import is_authenticated, get_cached_user_profile, get_credentials_path
    from uap.protocol import get_uap_home, get_sessions_dir
    
    table = Table(title="UAP System Status", show_header=False)
    table.add_column("Item", style="cyan")
    table.add_column("Status")
    
    # Authentication
    if is_authenticated():
        profile = get_cached_user_profile()
        email = profile.get('email', 'authenticated') if profile else 'authenticated'
        table.add_row("Auth", f"[green]✓ {email}[/green]")
    else:
        table.add_row("Auth", "[red]✗ Not logged in[/red]")
    
    # Paths
    table.add_row("UAP Home", str(get_uap_home()))
    table.add_row("Credentials", str(get_credentials_path()))
    table.add_row("Sessions Dir", str(get_sessions_dir()))
    
    # Session count
    sessions_dir = get_sessions_dir()
    session_count = len(list(sessions_dir.glob("*.json")))
    table.add_row("Sessions", str(session_count))
    
    console.print(table)


@cli.command()
def setup():
    """Interactive setup for OAuth client credentials."""
    from uap.oauth import get_client_secrets_path
    import json
    
    console.print(Panel(
        "[bold]UAP OAuth Setup[/bold]\n\n"
        "To use Gmail OAuth, you need a Google Cloud project with OAuth credentials.\n\n"
        "[cyan]Steps:[/cyan]\n"
        "1. Go to https://console.cloud.google.com/\n"
        "2. Create a new project or select existing\n"
        "3. Enable 'Google+ API' (for user info)\n"
        "4. Go to 'Credentials' → 'Create Credentials' → 'OAuth Client ID'\n"
        "5. Select 'Desktop app' for CLI usage\n"
        "6. Copy the Client ID and Client Secret",
        title="Setup Instructions",
        border_style="blue"
    ))
    
    client_id = click.prompt("\nEnter your Client ID", type=str)
    client_secret = click.prompt("Enter your Client Secret", type=str, hide_input=True)
    
    if not client_id or not client_secret:
        console.print("[red]Client ID and Secret are required.[/red]")
        raise click.Abort()
    
    secrets = {
        "installed": {
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080", "urn:ietf:wg:oauth:2.0:oob"]
        }
    }
    
    secrets_path = get_client_secrets_path()
    
    with open(secrets_path, "w") as f:
        json.dump(secrets, f, indent=2)
    
    console.print(f"\n[green]✓ Client secrets saved to:[/green] {secrets_path}")
    console.print("\nYou can now run: [cyan]uap-cli login[/cyan]")


def main():
    """Entry point for uap-cli."""
    cli()


if __name__ == "__main__":
    main()
