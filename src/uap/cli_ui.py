"""
cli_ui.py — Universal Agent Protocol (UAP) Interactive CLI
Aesthetic: Sunset Hue | Mascot: 🐱 Orange Cat | Inspired by Claude Code & GitHub Copilot
"""

from __future__ import annotations

import sys
import time
import asyncio
from typing import Optional, Generator
from contextlib import contextmanager

import click
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# ─────────────────────────────────────────────────────────────────────────────
# SUNSET THEME DEFINITION
# ─────────────────────────────────────────────────────────────────────────────

SUNSET_THEME = Theme(
    {
        # Core palette
        "sunset.dawn":      "bold #FFD580",   # warm amber yellow
        "sunset.gold":      "bold #FFA500",   # vivid orange (cat color)
        "sunset.orange":    "bold #FF6B35",   # deep orange
        "sunset.coral":     "bold #FF4D6D",   # coral-pink
        "sunset.pink":      "bold #FF85A1",   # soft pink
        "sunset.magenta":   "bold #E040FB",   # electric magenta
        "sunset.violet":    "bold #9C27B0",   # violet
        "sunset.purple":    "bold #6A0DAD",   # deep purple
        "sunset.dusk":      "bold #3D0066",   # near-black purple

        # Semantic roles
        "uap.header":       "#FF6B35 on default",
        "uap.prompt":       "bold #E040FB",
        "uap.user":         "#FFD580",
        "uap.agent":        "#FF85A1",
        "uap.system":       "dim #9C27B0",
        "uap.success":      "bold #00E676",
        "uap.warning":      "bold #FFA500",
        "uap.error":        "bold #FF4D6D",
        "uap.muted":        "dim #6A0DAD",
        "uap.border":       "#6A0DAD",
        "uap.thinking":     "italic #E040FB",
        "uap.command":      "bold #FFD580",
        "uap.key":          "bold #FF6B35",
        "uap.value":        "#FF85A1",
    }
)

console = Console(theme=SUNSET_THEME, highlight=False)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER BANNER
# ─────────────────────────────────────────────────────────────────────────────

UAP_ASCII = r"""
██╗   ██╗ █████╗ ██████╗ 
██║   ██║██╔══██╗██╔══██╗
██║   ██║███████║██████╔╝
██║   ██║██╔══██║██╔═══╝ 
╚██████╔╝██║  ██║██║     
 ╚═════╝ ╚═╝  ╚═╝╚═╝     
"""


def sunset_gradient(text: str) -> Text:
    """Apply a character-by-character sunset gradient to a string."""
    colors = [
        "#FFD580", "#FFC44D", "#FFA500",
        "#FF7F32", "#FF6B35", "#FF5050",
        "#FF4D6D", "#FF69B4", "#E040FB",
        "#9C27B0", "#6A0DAD",
    ]
    result = Text()
    n = max(len(text), 1)
    for i, ch in enumerate(text):
        color_idx = int(i / n * (len(colors) - 1))
        result.append(ch, style=Style(color=colors[color_idx], bold=True))
    return result


def render_header() -> None:
    """Render the full UAP header banner."""
    console.print()

    # Build gradient banner lines
    banner_lines = UAP_ASCII.strip("\n").split("\n")
    banner_text = Text()
    colors = [
        "#FFD580", "#FFA500", "#FF6B35",
        "#FF4D6D", "#E040FB", "#9C27B0",
    ]
    for i, line in enumerate(banner_lines):
        color = colors[i % len(colors)]
        banner_text.append(line + "\n", style=Style(color=color, bold=True))

    # Center banner
    logo_col = Align.center(banner_text, vertical="middle")

    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="center", min_width=50)
    grid.add_row(logo_col)

    console.print(
        Panel(
            Align.center(grid),
            border_style="uap.border",
            box=box.DOUBLE_EDGE,
            subtitle=sunset_gradient("Universal Agent Protocol  ·  v1.0.0"),
            subtitle_align="center",
            padding=(0, 2),
        )
    )

    tagline = Text()
    tagline.append("Agent orchestration at the speed of sunset", style="italic #FF85A1")
    console.print(Align.center(tagline))
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# SPINNER / LIVE THINKING STATE
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def thinking(label: str = "Agent is thinking") -> Generator:
    """
    Context manager that renders a live spinner while the agent processes.

    Usage:
        with thinking("Routing via MCP bridge"):
            result = dispatcher.dispatch(payload)
    """
    spinner_text = Text()
    spinner_text.append(label + "...", style="uap.thinking")

    spinner = Spinner("dots2", text=spinner_text, style="#E040FB")

    with Live(
        Align.left(spinner),
        console=console,
        refresh_per_second=12,
        transient=True,
    ):
        yield


# ─────────────────────────────────────────────────────────────────────────────
# PANELS — ACT Summary, Handoff Log, Status
# ─────────────────────────────────────────────────────────────────────────────

def render_act_panel(state: dict) -> None:
    """
    Render an Agent Context Token (ACT) summary panel.

    Args:
        state: dict from protocol.State.to_dict()
    """
    table = Table.grid(padding=(0, 2), expand=True)
    table.add_column(style="uap.key",   min_width=20)
    table.add_column(style="uap.value", min_width=30)

    for key, val in state.items():
        label = Text(str(key).replace("_", " ").title(), style="uap.key")
        value = Text(str(val), style="uap.value")
        table.add_row(label, value)

    title_text = Text()
    title_text.append("Agent Context Token", style="bold #FFA500")

    console.print(
        Panel(
            table,
            title=title_text,
            border_style="#9C27B0",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def render_handoff_panel(log: list[dict]) -> None:
    """
    Render the A2A handoff log as a panel.

    Args:
        log: list of handoff dicts with keys 'from_agent', 'to_agent', 'reason', 'ts'
    """
    table = Table(
        show_header=True,
        header_style="bold #FFD580",
        border_style="#6A0DAD",
        box=box.SIMPLE_HEAVY,
        expand=True,
    )
    table.add_column("Time",       style="#9C27B0",  max_width=10)
    table.add_column("From",       style="#FF6B35",  min_width=14)
    table.add_column("To",         style="#FF4D6D",  min_width=14)
    table.add_column("Reason",     style="#FF85A1")

    for entry in log:
        table.add_row(
            str(entry.get("ts", "—")),
            str(entry.get("from_agent", "—")),
            str(entry.get("to_agent", "—")),
            str(entry.get("reason", "—")),
        )

    title_text = Text()
    title_text.append("A2A Handoff Log", style="bold #E040FB")

    console.print(
        Panel(
            table,
            title=title_text,
            border_style="#E040FB",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def render_agent_response(agent_name: str, markdown_body: str) -> None:
    """
    Render a Markdown agent response inside a sunset-styled panel.

    Args:
        agent_name:    Display name of the responding agent.
        markdown_body: Full Markdown string to render.
    """
    title = Text()
    title.append(agent_name, style="bold #FF6B35")

    console.print(
        Panel(
            Markdown(markdown_body),
            title=title,
            title_align="left",
            border_style="#FF6B35",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()


def render_user_message(text: str) -> None:
    """Echo the user's message in a subtle right-aligned panel."""
    msg = Text()
    msg.append("You  ", style="bold #FFD580")
    msg.append(text, style="#FFD580")

    console.print(
        Panel(
            msg,
            border_style="#FFD580",
            box=box.SIMPLE,
            padding=(0, 2),
        )
    )
    console.print()


def render_error(message: str) -> None:
    console.print(
        Panel(
            Text(f"ERROR: {message}", style="uap.error"),
            border_style="uap.error",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


def render_success(message: str) -> None:
    console.print(
        Panel(
            Text(f"SUCCESS: {message}", style="uap.success"),
            border_style="uap.success",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# SLASH COMMAND HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def handle_slash_status(state_provider) -> None:
    """Show current ACT from the protocol state."""
    try:
        state_dict = state_provider()
    except Exception:
        state_dict = {
            "session_id":   "demo-0001",
            "active_agent": "uap-core",
            "mcp_status":   "idle",
            "a2a_status":   "idle",
            "token_budget": "4096 / 8192",
            "uptime":       "00:04:12",
        }
    render_act_panel(state_dict)


def handle_slash_login(oauth_provider=None) -> None:
    """Trigger Gmail OAuth login flow."""
    console.print()
    console.print(Text("  Initiating Gmail OAuth flow...", style="bold #FFD580"))
    console.print(Text("  Opening browser for authorization...", style="uap.muted"))

    if oauth_provider:
        try:
            with thinking("Waiting for OAuth callback"):
                result = oauth_provider()
            if result:
                render_success("Gmail authenticated successfully.")
            else:
                render_error("OAuth flow returned no credentials.")
        except Exception as exc:
            render_error(f"OAuth error: {exc}")
    else:
        # Demo / stub path
        time.sleep(1.2)
        render_success("Demo: OAuth stub complete. Connect a real oauth_provider to activate.")


def handle_slash_help() -> None:
    """Print available slash commands."""
    table = Table(
        show_header=False,
        box=box.SIMPLE,
        border_style="#6A0DAD",
        padding=(0, 2),
        expand=False,
    )
    table.add_column(style="uap.command", min_width=14)
    table.add_column(style="#FF85A1")

    commands = [
        ("/status",  "Show Agent Context Token (ACT) and session state"),
        ("/login",   "Authenticate with Gmail via OAuth"),
        ("/handoff", "Display A2A agent handoff log"),
        ("/clear",   "Clear the terminal screen"),
        ("/help",    "Show this help panel"),
        ("/exit",    "Exit the UAP chat session"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)

    title = Text()
    title.append("Slash Commands", style="bold #FFA500")

    console.print(
        Panel(table, title=title, border_style="#9C27B0", box=box.ROUNDED, padding=(1, 2))
    )


# ─────────────────────────────────────────────────────────────────────────────
# STYLED PROMPT HELPER
# ─────────────────────────────────────────────────────────────────────────────

def styled_prompt() -> str:
    """
    Return the styled prompt string for input().

    Rich doesn't control input() prompts directly, so we use ANSI escape codes
    to match the sunset palette for a cohesive feel.
    """
    RESET   = "\033[0m"
    MAGENTA = "\033[38;2;224;64;251m"
    ORANGE  = "\033[38;2;255;165;0m"
    BOLD    = "\033[1m"
    return f"\n{BOLD}{ORANGE}uap{RESET} {BOLD}{MAGENTA}>>{RESET} "


# ─────────────────────────────────────────────────────────────────────────────
# CORE CHAT LOOP
# ─────────────────────────────────────────────────────────────────────────────

def chat_loop(
    dispatcher=None,
    state_provider=None,
    handoff_log_provider=None,
    oauth_provider=None,
) -> None:
    """
    Persistent interactive chat loop.

    Args:
        dispatcher:           Callable(user_input: str) -> str (Markdown)
                              If None, a stub echo dispatcher is used.
        state_provider:       Callable() -> dict   — wraps protocol.State
        handoff_log_provider: Callable() -> list   — wraps dispatcher's log
        oauth_provider:       Callable() -> bool   — Gmail OAuth
    """
    render_header()

    # Tips bar
    console.print(
        Rule(
            Text("Type a message to begin  ·  /help for commands  ·  /exit to quit",
                 style="dim #9C27B0"),
            style="#3D0066",
        )
    )
    console.print()

    # Fallback stub dispatcher
    def _stub_dispatcher(user_input: str) -> str:
        return (
            f"### UAP Echo (stub)\n\n"
            f"You said: **{user_input}**\n\n"
            f"> Connect a real `dispatcher.dispatch` function to enable agent routing.\n\n"
            f"```\nMCP Bridge: idle\nA2A Router: idle\n```"
        )

    dispatch_fn = dispatcher if dispatcher else _stub_dispatcher

    while True:
        try:
            raw = input(styled_prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            console.print()
            console.print(Text("\nSession ended. Goodbye!\n", style="bold #FF6B35"))
            break

        if not raw:
            continue

        # ── Slash commands ──────────────────────────────────────────────
        cmd = raw.lower()

        if cmd in ("/exit", "/quit", "/q"):
            console.print(Text("\nSession ended. Goodbye!\n", style="bold #FF6B35"))
            break

        if cmd == "/clear":
            console.clear()
            render_header()
            continue

        if cmd == "/help":
            handle_slash_help()
            continue

        if cmd == "/status":
            handle_slash_status(state_provider or (lambda: {}))
            continue

        if cmd == "/login":
            handle_slash_login(oauth_provider)
            continue

        if cmd == "/handoff":
            log = handoff_log_provider() if handoff_log_provider else []
            if log:
                render_handoff_panel(log)
            else:
                console.print(Text("  No handoff events recorded yet.", style="uap.muted"))
            continue

        # ── Agent dispatch ──────────────────────────────────────────────
        render_user_message(raw)

        try:
            responses = dispatch_fn(raw)
            # If it returns a string (legacy), wrap it in a list
            if isinstance(responses, str):
                with thinking("Routing through MCP/A2A bridge"):
                    render_agent_response("UAP Agent", responses)
            else:
                # Expecting a generator of (agent_name, text, act_dict)
                for agent_name, response_md, act_dict in responses:
                    render_agent_response(agent_name, response_md)
                    if act_dict:
                        render_act_panel(act_dict)
        except Exception as exc:
            render_error(f"Dispatch error: {exc}")
            continue


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — for use by dispatcher.py / protocol.py
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Console
    "console",
    "SUNSET_THEME",
    # Rendering helpers
    "render_header",
    "render_agent_response",
    "render_user_message",
    "render_act_panel",
    "render_handoff_panel",
    "render_error",
    "render_success",
    "sunset_gradient",
    # Context manager
    "thinking",
    # Chat entrypoint
    "chat_loop",
]

