import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from uap.oauth import run_cli_oauth_flow, get_user_info, get_cached_user_profile
from uap.core.vault import get_linked_agents
from uap.mcp_server import main as run_mcp_server

console = Console()

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Universal Agent Protocol (UAP) - Minimalist Semantic Transport Layer."""
    if ctx.invoked_subcommand is None:
        console.print("[bold green]Universal Agent Protocol[/bold green]")
        console.print("Run [cyan]uap --help[/cyan] for commands.")

@cli.command()
def login():
    """Login with Google OAuth to verify identity."""
    console.print("[yellow]Starting Google OAuth flow...[/yellow]")
    with console.status("Waiting for authentication in browser..."):
        try:
            run_cli_oauth_flow()
            user_info = get_user_info()
            console.print(f"[bold green]Success![/bold green] Logged in as: [cyan]{user_info.get('email')}[/cyan]")
        except Exception as e:
            console.print(f"[bold red]Login failed:[/bold red] {e}")

@cli.command()
def status():
    """Show the current status of the UAP system and linked providers."""
    try:
        user_info = get_cached_user_profile()
        if not user_info:
            console.print("[yellow]Not logged in. Run 'uap login'.[/yellow]")
            return
            
        email = user_info.get("email", "Unknown")
        console.print(Panel(f"Identity: [bold cyan]{email}[/bold cyan]", title="- UAP Status -"))
        
        agents = get_linked_agents(email)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Provider")
        table.add_column("Status")
        table.add_column("Linked At")
        
        for p_id, info in agents.items():
            status_text = "[green]Linked[/green]" if info.get("linked") else "[red]Not Linked[/red]"
            linked_at = info.get("linked_at", "N/A") if info.get("linked") else "N/A"
            if linked_at != "N/A":
                linked_at = linked_at.split('T')[0] # just date for clean UI
            table.add_row(info["name"], status_text, linked_at)
            
        console.print(table)
        console.print("\n[dim]To link more providers, configure them programmatically or natively.[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error checking status:[/bold red] {e}")

@cli.command()
def start():
    """Start the UAP MCP Server on stdio."""
    run_mcp_server()

if __name__ == "__main__":
    cli()
