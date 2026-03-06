"""
UAP Visuals — Neuron-themed immersive terminal experience.

Provides animated ASCII art banners, red/pink gradient rendering,
neuron-network connection motifs, styled prompts, and ambient effects
for all UAP CLI entry points.

Color theme: Warm orange → Coral → Hot pink → Magenta → Soft rose
Motif: Neural network nodes (◉) connected by axon lines (━/┃)
"""

import sys
import time
import random
import threading
from typing import Optional, List, Tuple

# ---------------------------------------------------------------------------
# Dependency detection (graceful degradation)
# ---------------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.style import Style
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.live import Live
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import pyfiglet
    PYFIGLET_AVAILABLE = True
except ImportError:
    PYFIGLET_AVAILABLE = False

try:
    from blessed import Terminal
    BLESSED_AVAILABLE = True
except ImportError:
    BLESSED_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants — Orange / Coral / Pink / Magenta palette
# ---------------------------------------------------------------------------

__version__ = "0.2.0"

# 24-bit RGB gradient stops: burnt orange → orange → coral → hot pink → magenta → rose
GRADIENT_STOPS: List[Tuple[int, int, int]] = [
    (200, 80,  10),   # burnt orange
    (240, 120, 20),   # warm orange
    (255, 150, 50),   # bright orange
    (255, 120, 70),   # orange-coral
    (255, 100, 100),  # coral
    (255, 90,  130),  # coral-pink
    (255, 105, 160),  # hot pink
    (240, 80,  180),  # pink-magenta
    (210, 60,  200),  # magenta
    (255, 160, 210),  # soft rose
]

# Fallback 256-color indices (for terminals without truecolor)
GRADIENT_256 = [130, 166, 208, 209, 210, 204, 205, 206, 200, 201, 213, 219]

# Emoji-free neuron symbols (Unicode, renders everywhere)
NODE       = "◉"
NODE_DIM   = "◎"
NODE_SMALL = "●"
AXON_H     = "━"
AXON_V     = "┃"
BRANCH_R   = "┣"
BRANCH_L   = "┫"
CORNER_TL  = "┏"
CORNER_TR  = "┓"
CORNER_BL  = "┗"
CORNER_BR  = "┛"
TEE_D      = "┳"
TEE_U      = "┻"
ARROW      = "▸"
PULSE      = "⬤"

# Figlet font preference (ansi_shadow = clean box-drawing block chars, Gemini-like)
FIGLET_FONTS = ["ansi_shadow", "slant", "big", "standard"]


# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------

def _lerp_rgb(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Linearly interpolate between two RGB colors."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def _gradient_color(position: float) -> Tuple[int, int, int]:
    """Get an RGB color from the gradient at position [0.0, 1.0]."""
    n = len(GRADIENT_STOPS) - 1
    idx = position * n
    lo = int(idx)
    hi = min(lo + 1, n)
    t = idx - lo
    return _lerp_rgb(GRADIENT_STOPS[lo], GRADIENT_STOPS[hi], t)


def _ansi_fg(r: int, g: int, b: int) -> str:
    """ANSI 24-bit foreground escape."""
    return f"\033[38;2;{r};{g};{b}m"


def _ansi_reset() -> str:
    return "\033[0m"


def gradient_line(text: str, position: float = 0.5) -> str:
    """Color an entire line with a single gradient color (ANSI)."""
    r, g, b = _gradient_color(position)
    return f"{_ansi_fg(r, g, b)}{text}{_ansi_reset()}"


def gradient_text_chars(text: str, start: float = 0.0, end: float = 1.0) -> str:
    """Apply per-character gradient from start→end positions in the palette."""
    if not text:
        return text
    result = []
    n = max(len(text) - 1, 1)
    for i, ch in enumerate(text):
        t = start + (end - start) * (i / n)
        r, g, b = _gradient_color(t)
        result.append(f"{_ansi_fg(r, g, b)}{ch}")
    result.append(_ansi_reset())
    return "".join(result)


def rich_gradient_style(position: float) -> "Style":
    """Return a Rich Style at a gradient position."""
    r, g, b = _gradient_color(position)
    return Style(color=f"rgb({r},{g},{b})")


def rich_gradient_text(text: str, start: float = 0.0, end: float = 1.0) -> "Text":
    """Create a Rich Text object with per-character gradient."""
    rt = Text()
    n = max(len(text) - 1, 1)
    for i, ch in enumerate(text):
        t = start + (end - start) * (i / n)
        r, g, b = _gradient_color(t)
        rt.append(ch, style=Style(color=f"rgb({r},{g},{b})"))
    return rt


# ---------------------------------------------------------------------------
# ASCII art banner generation
# ---------------------------------------------------------------------------

# Handcrafted wide fallback (ansi_shadow with extra letter spacing)
_FALLBACK_BANNER = (
    "██╗   ██╗         █████╗         ██████╗ \n"
    "██║   ██║        ██╔══██╗        ██╔══██╗\n"
    "██║   ██║        ███████║        ██████╔╝\n"
    "██║   ██║        ██╔══██║        ██╔═══╝ \n"
    "╚██████╔╝        ██║  ██║        ██║     \n"
    " ╚═════╝         ╚═╝  ╚═╝        ╚═╝     "
)


def _generate_figlet(text: str = "U  A  P") -> str:
    """Generate large ASCII art text via pyfiglet.
    
    Default is 'U  A  P' (extra spaces = wider letter spacing,
    produces a clean Gemini-CLI-like banner at ~41 chars wide).
    """
    if not PYFIGLET_AVAILABLE:
        return _FALLBACK_BANNER
    for font in FIGLET_FONTS:
        try:
            art = pyfiglet.figlet_format(text, font=font, width=200)
            if art.strip():
                return art.rstrip("\n")
        except Exception:
            continue
    return _FALLBACK_BANNER


def _center_block(text: str, width: int) -> str:
    """Center every line of a multi-line string."""
    lines = text.split("\n")
    return "\n".join(line.center(width) for line in lines)


def _build_neuron_line(width: int, density: float = 0.15) -> str:
    """Build a neuron axon connection line that fits `width` columns."""
    parts = []
    pos = 0
    # Start with a node
    parts.append(NODE)
    pos += 1
    while pos < width - 1:
        # Random segment of axon lines
        seg_len = random.randint(3, 8)
        seg_len = min(seg_len, width - pos - 1)
        parts.append(AXON_H * seg_len)
        pos += seg_len
        if pos < width - 1:
            parts.append(NODE if random.random() < 0.6 else NODE_DIM)
            pos += 1
    return "".join(parts)[:width]


def _build_vertical_connectors(width: int, node_positions: List[int]) -> str:
    """Build a line of vertical connectors at given positions."""
    line = list(" " * width)
    for p in node_positions:
        if 0 <= p < width:
            line[p] = AXON_V
    return "".join(line)


def build_full_banner(width: int = 80) -> List[str]:
    """
    Build a clean, Gemini-CLI-inspired UAP banner.
    
    Layout:
      (blank)
      <figlet art, indented>
      (blank)
      <thin separator>
      <tagline>
      (blank)
    
    Returns a list of plain-text lines. Callers apply gradient coloring.
    """
    # Generate figlet text with wide letter spacing
    figlet_raw = _generate_figlet()
    figlet_lines = figlet_raw.split("\n")
    
    # Clean up trailing whitespace / empty lines
    figlet_lines = [ln.rstrip() for ln in figlet_lines]
    while figlet_lines and not figlet_lines[-1].strip():
        figlet_lines.pop()
    
    # Effective width
    max_figlet_width = max((len(ln) for ln in figlet_lines), default=0)
    effective_width = max(width, max_figlet_width + 10)
    
    lines: List[str] = []
    
    # Top spacer
    lines.append("")
    
    # Figlet art — indented 4 spaces
    indent = 4
    for fl in figlet_lines:
        lines.append(" " * indent + fl)
    
    # Blank line
    lines.append("")
    
    # Thin separator (━━━ not a busy neuron line)
    sep_width = min(max_figlet_width + indent, effective_width - 4)
    lines.append(" " * indent + AXON_H * sep_width)
    
    # Taglines
    lines.append(f"    Universal Agent Protocol  v{__version__}")
    lines.append(f"    Connecting Agentic Interfaces")
    lines.append("")
    
    return lines


# ---------------------------------------------------------------------------
# Tips section (Gemini-CLI style)
# ---------------------------------------------------------------------------

TIPS = [
    f"    {ARROW} Route tasks across LLM agents seamlessly",
    f"    {ARROW} Type  /agents  to list available backends",
    f"    {ARROW} Type  /help    for the full command reference",
]


def _build_tips() -> List[str]:
    """Build the tips section (Gemini-CLI style)."""
    lines = []
    lines.append("")
    lines.append(f"    Getting started")
    lines.append("")
    for tip in TIPS:
        lines.append(tip)
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Animated banner rendering
# ---------------------------------------------------------------------------

def _typing_delay(char: str) -> float:
    """Variable delay per character for natural typing feel."""
    if char in ("\n",):
        return 0.008
    if char in (" ",):
        return 0.005
    if char in (NODE, NODE_DIM, AXON_H):
        return 0.003
    return 0.012


def animate_banner(console: Optional["Console"] = None, width: int = 80, skip_animation: bool = False):
    """
    Render the full animated neuron-themed UAP banner.
    
    Each line gets per-character horizontal gradient coloring.
    A subtle vertical offset shifts the hue per row.
    
    Args:
        console: Rich Console instance (optional, falls back to raw ANSI)
        width: Terminal width for the banner
        skip_animation: If True, print instantly (no animation)
    """
    if skip_animation:
        static_banner(console, width)
        return
    
    banner_lines = build_full_banner(width)
    tip_lines = _build_tips()
    
    total = len(banner_lines) + len(tip_lines)
    
    # Hide cursor during animation
    sys.stdout.write("\033[?25l")  # hide cursor
    sys.stdout.flush()
    
    try:
        # Phase 1-3: Banner with per-character gradient + typing effect
        for idx, line in enumerate(banner_lines):
            row_t = idx / max(len(banner_lines) - 1, 1)  # 0→1 vertical
            # Each row's gradient band shifts down the palette
            band_start = row_t * 0.35   # start point shifts per row
            band_end   = band_start + 0.65
            band_end   = min(band_end, 1.0)
            
            stripped = line.rstrip()
            n = max(len(stripped) - 1, 1)
            
            for ci, ch in enumerate(stripped):
                # Horizontal gradient within this row's band
                h_t = ci / n if n > 0 else 0.5
                t = band_start + (band_end - band_start) * h_t
                r, g, b = _gradient_color(t)
                sys.stdout.write(f"{_ansi_fg(r, g, b)}{ch}")
                sys.stdout.flush()
                time.sleep(_typing_delay(ch))
            
            sys.stdout.write(_ansi_reset() + "\n")
            sys.stdout.flush()
        
        # Small pause before tips
        time.sleep(0.15)
        
        # Phase 4: Tips with softer gradient and slightly faster typing
        for idx, line in enumerate(tip_lines):
            t = 0.5 + 0.5 * (idx / max(len(tip_lines) - 1, 1))
            
            stripped = line.rstrip()
            n = max(len(stripped) - 1, 1)
            for ci, ch in enumerate(stripped):
                h_t = ci / n if n > 0 else 0.5
                # Tips use a narrow band near position t
                ct = t - 0.1 + 0.2 * h_t
                ct = max(0.0, min(ct, 1.0))
                r, g, b = _gradient_color(ct)
                sys.stdout.write(f"{_ansi_fg(r, g, b)}{ch}")
                sys.stdout.flush()
                time.sleep(0.006)
            
            sys.stdout.write(_ansi_reset() + "\n")
            sys.stdout.flush()
        
    finally:
        # Restore cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def static_banner(console: Optional["Console"] = None, width: int = 80):
    """Render the banner instantly (no animation) with per-character gradient colors."""
    banner_lines = build_full_banner(width)
    tip_lines = _build_tips()
    all_lines = banner_lines + tip_lines
    total = len(all_lines)
    
    for idx, line in enumerate(all_lines):
        row_t = idx / max(total - 1, 1)
        band_start = row_t * 0.35
        band_end = min(band_start + 0.65, 1.0)
        
        if RICH_AVAILABLE and console:
            rt = Text()
            stripped = line.rstrip()
            n = max(len(stripped) - 1, 1)
            for ci, ch in enumerate(stripped):
                h_t = ci / n if n > 0 else 0.5
                t = band_start + (band_end - band_start) * h_t
                r, g, b = _gradient_color(t)
                rt.append(ch, style=Style(color=f"rgb({r},{g},{b})"))
            console.print(rt, highlight=False)
        else:
            print(gradient_text_chars(line, start=band_start, end=band_end))


def compact_header(console: Optional["Console"] = None):
    """Single-line UAP header for subcommand invocations."""
    header = f" {NODE} UAP v{__version__} {AXON_H * 3} Universal Agent Protocol {AXON_H * 3} {NODE}"
    if RICH_AVAILABLE and console:
        console.print(rich_gradient_text(header, start=0.2, end=0.7), highlight=False)
        console.print()
    else:
        print(gradient_text_chars(header, start=0.2, end=0.7))
        print()


# ---------------------------------------------------------------------------
# Styled prompts and input
# ---------------------------------------------------------------------------

def neuron_prompt_str() -> str:
    """Return the styled UAP prompt string for Rich Prompt.ask()."""
    return f"[rgb(255,140,50)]{NODE}[/rgb(255,140,50)] [bold rgb(255,105,160)]uap[/bold rgb(255,105,160)] [rgb(210,60,200)]{ARROW}[/rgb(210,60,200)]"


def neuron_prompt_ansi() -> str:
    """Return the styled UAP prompt string using ANSI escapes."""
    return (
        f"{_ansi_fg(255, 140, 50)}{NODE}{_ansi_reset()} "
        f"{_ansi_fg(255, 105, 160)}uap{_ansi_reset()} "
        f"{_ansi_fg(210, 60, 200)}{ARROW}{_ansi_reset()} "
    )


def get_input(prompt_text: Optional[str] = None, use_rich: bool = True) -> str:
    """
    Get user input with the neuron-themed prompt.
    
    Args:
        prompt_text: Optional override for prompt text
        use_rich: Use Rich Prompt if available
    """
    if use_rich and RICH_AVAILABLE:
        return Prompt.ask(prompt_text or neuron_prompt_str())
    else:
        return input(prompt_text or neuron_prompt_ansi()).strip()


# ---------------------------------------------------------------------------
# Styled menu
# ---------------------------------------------------------------------------

def styled_menu(console: Optional["Console"], options: List[Tuple[str, str]], 
                title: str = "What would you like to do?") -> str:
    """
    Render a neuron-themed interactive menu.
    
    Args:
        console: Rich Console
        options: List of (key, description) tuples, e.g. [("1", "Start Chat")]
        title: Menu title
    
    Returns:
        The selected key string
    """
    if RICH_AVAILABLE and console:
        console.print()
        # Title
        console.print(
            rich_gradient_text(f"  {title}", start=0.3, end=0.6),
            highlight=False
        )
        console.print()
        
        # Options
        for i, (key, desc) in enumerate(options):
            t = 0.2 + 0.6 * (i / max(len(options) - 1, 1))
            r, g, b = _gradient_color(t)
            node_color = f"rgb({r},{g},{b})"
            console.print(
                f"  [{node_color}]{NODE}[/{node_color}] "
                f"[bold rgb(255,200,220)]{key}[/bold rgb(255,200,220)]"
                f"[rgb(180,180,180)].[/rgb(180,180,180)] "
                f"[rgb(255,220,230)]{desc}[/rgb(255,220,230)]"
            )
        
        console.print()
        
        # Input
        valid_keys = [k for k, _ in options]
        choice = Prompt.ask(
            neuron_prompt_str(),
            choices=valid_keys,
            default=valid_keys[0]
        )
        return choice
    else:
        # Plain fallback
        print(f"\n  {title}\n")
        for key, desc in options:
            print(f"  {NODE} {key}. {desc}")
        print()
        return input(neuron_prompt_ansi()).strip()


# ---------------------------------------------------------------------------
# Input bar (Gemini-CLI style bottom bar)
# ---------------------------------------------------------------------------

def input_bar(console: Optional["Console"], width: int = 70) -> None:
    """
    Render the TOP half of a Gemini-CLI-style bordered chat input box.
    
    After calling this, use ``get_chat_input()`` to collect the user's
    message (it renders the prompt + bottom border automatically).
    """
    if width < 40:
        width = 40
    inner = width - 2  # space between left/right borders
    
    # Top border with hint
    hint = " Type your message or /help "
    padding = inner - len(hint) - 1
    if padding < 0:
        hint = ""
        padding = inner - 1
    
    top = f"  {CORNER_TL}{AXON_H}{hint}{AXON_H * padding}{CORNER_TR}"
    
    if RICH_AVAILABLE and console:
        console.print(rich_gradient_text(top, start=0.2, end=0.6), highlight=False)
    else:
        print(gradient_text_chars(top, start=0.2, end=0.6))


def _input_bottom_border(width: int = 70) -> str:
    """Return the bottom border string for the chat input box."""
    inner = max(width - 2, 38)
    return f"  {CORNER_BL}{AXON_H * (inner)}{CORNER_BR}"


def get_chat_input(console: Optional["Console"] = None, width: int = 70) -> str:
    """
    Gemini-CLI-style bordered chat input.
    
    Draws a box around the user's input area:
    ┏━ Type your message or /help ━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃ ◉ uap ▸  <user types here>                            ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """
    if width < 40:
        width = 40
    inner = max(width - 2, 38)
    
    # ── Top border ──
    hint = " Type your message or /help "
    pad = inner - len(hint) - 1
    if pad < 0:
        hint = ""
        pad = inner - 1
    top = f"  {CORNER_TL}{AXON_H}{hint}{AXON_H * pad}{CORNER_TR}"
    
    if RICH_AVAILABLE and console:
        console.print(rich_gradient_text(top, start=0.15, end=0.55), highlight=False)
    else:
        print(gradient_text_chars(top, start=0.15, end=0.55))
    
    # ── Prompt line — left border  ◉ uap ▸  [input]   right border ──
    left_border_ansi = (
        f"  {_ansi_fg(*_gradient_color(0.2))}{AXON_V}{_ansi_reset()} "
    )
    prompt_inner = (
        f"{_ansi_fg(255, 140, 50)}{NODE}{_ansi_reset()} "
        f"{_ansi_fg(255, 105, 160)}uap{_ansi_reset()} "
        f"{_ansi_fg(210, 60, 200)}{ARROW}{_ansi_reset()} "
    )
    
    try:
        user_text = input(left_border_ansi + prompt_inner).strip()
    except (EOFError, KeyboardInterrupt):
        user_text = ""
    
    # ── Bottom border ──
    bottom = f"  {CORNER_BL}{AXON_H * inner}{CORNER_BR}"
    if RICH_AVAILABLE and console:
        console.print(rich_gradient_text(bottom, start=0.15, end=0.55), highlight=False)
    else:
        print(gradient_text_chars(bottom, start=0.15, end=0.55))
    
    return user_text


# ---------------------------------------------------------------------------
# Status bar (persistent bottom info)
# ---------------------------------------------------------------------------

def status_bar(console: Optional["Console"], session_id: str = "no session",
               backend: str = "none", context_pct: int = 100, width: int = 70):
    """Render a status bar with session info."""
    left = f" {NODE_SMALL} sandbox"
    mid = f"({session_id})"
    right = f"{NODE_SMALL} {backend} ({context_pct}% context left)"
    
    # Pad to width
    spacing = width - len(left) - len(mid) - len(right)
    spacing = max(spacing, 2)
    bar = f"{left}{' ' * (spacing // 2)}{mid}{' ' * (spacing - spacing // 2)}{right}"
    
    if RICH_AVAILABLE and console:
        console.print(
            bar,
            style=Style(color="rgb(180,100,80)", dim=True),
            highlight=False
        )
    else:
        r, g, b = 150, 60, 80
        print(f"{_ansi_fg(r, g, b)}{bar}{_ansi_reset()}")


# ---------------------------------------------------------------------------
# Processing spinner / pulse
# ---------------------------------------------------------------------------

class NeuronSpinner:
    """
    A context manager that shows a neuron-pulse spinner during processing.
    
    Usage:
        with NeuronSpinner(console, "Processing..."):
            do_work()
    """
    
    PULSE_FRAMES = [
        f"  {NODE}   ",
        f"  {NODE}{AXON_H}  ",
        f"  {NODE}{AXON_H}{AXON_H} ",
        f"  {NODE}{AXON_H}{AXON_H}{NODE}",
        f"   {AXON_H}{AXON_H}{NODE}",
        f"    {AXON_H}{NODE}",
        f"     {NODE}  ",
        f"    {AXON_H}{NODE}",
        f"   {AXON_H}{AXON_H}{NODE}",
        f"  {NODE}{AXON_H}{AXON_H}{NODE}",
        f"  {NODE}{AXON_H}  ",
        f"  {NODE}   ",
    ]
    
    def __init__(self, console: Optional["Console"] = None, message: str = "Processing..."):
        self.console = console
        self.message = message
        self._stop = threading.Event()
        self._thread = None
    
    def _animate(self):
        """Background animation loop."""
        idx = 0
        colors = [
            (255, 150, 50),
            (255, 120, 70),
            (255, 100, 100),
            (255, 90, 130),
            (255, 105, 160),
            (240, 80, 180),
            (255, 105, 160),
            (255, 90, 130),
            (255, 100, 100),
            (255, 120, 70),
        ]
        
        while not self._stop.is_set():
            frame = self.PULSE_FRAMES[idx % len(self.PULSE_FRAMES)]
            r, g, b = colors[idx % len(colors)]
            
            line = f"\r{_ansi_fg(r, g, b)}{frame} {self.message}{_ansi_reset()}"
            sys.stdout.write(line)
            sys.stdout.flush()
            
            idx += 1
            self._stop.wait(0.12)
        
        # Clear line
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
    
    def __enter__(self):
        if RICH_AVAILABLE and self.console:
            # Use Rich's built-in status but with our theme
            self._rich_status = self.console.status(
                f"[rgb(255,140,50)]{NODE}[/rgb(255,140,50)] "
                f"[rgb(255,105,160)]{self.message}[/rgb(255,105,160)]",
                spinner="dots",
                spinner_style="rgb(255,140,50)"
            )
            self._rich_status.__enter__()
        else:
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
        return self
    
    def __exit__(self, *args):
        if RICH_AVAILABLE and self.console and hasattr(self, '_rich_status'):
            self._rich_status.__exit__(*args)
        else:
            self._stop.set()
            if self._thread:
                self._thread.join(timeout=1)


# ---------------------------------------------------------------------------
# Fade transition
# ---------------------------------------------------------------------------

def fade_transition(console: Optional["Console"] = None, width: int = 70):
    """Quick fade effect between screens (3 frames)."""
    frames = [
        AXON_H * width,
        (NODE_DIM + AXON_H * 4) * (width // 5),
        (NODE + AXON_H * 4) * (width // 5),
    ]
    
    brightness_levels = [0.2, 0.5, 0.8]
    
    for frame, brightness in zip(frames, brightness_levels):
        r, g, b = _gradient_color(brightness)
        sys.stdout.write(f"\r{_ansi_fg(r, g, b)}{frame[:width]}{_ansi_reset()}")
        sys.stdout.flush()
        time.sleep(0.08)
    
    # Clear
    sys.stdout.write("\r" + " " * width + "\r")
    sys.stdout.flush()
    print()


# ---------------------------------------------------------------------------
# Themed Rich panels & tables
# ---------------------------------------------------------------------------

# Theme colors for consistent styling across all CLI interfaces
THEME = {
    "panel_border":    "rgb(255,120,70)",
    "panel_title":     "bold rgb(255,105,160)",
    "success":         "rgb(255,160,210)",
    "warning":         "rgb(255,200,100)",
    "error":           "bold rgb(255,80,80)",
    "info":            "rgb(240,80,180)",
    "dim":             "rgb(180,100,80)",
    "accent":          "rgb(210,60,200)",
    "table_header":    "bold rgb(255,130,90)",
    "table_row_1":     "rgb(255,160,210)",
    "table_row_2":     "rgb(240,130,170)",
    "status_spinner":  "rgb(255,140,50)",
    "prompt_node":     "rgb(255,140,50)",
    "prompt_text":     "bold rgb(255,105,160)",
    "prompt_arrow":    "rgb(210,60,200)",
}


def themed_panel(content: str, title: str = "", subtitle: str = "",
                 console: Optional["Console"] = None) -> Optional["Panel"]:
    """Create a Rich Panel with neuron theme."""
    if not RICH_AVAILABLE:
        print(f"--- {title} ---")
        print(content)
        if subtitle:
            print(f"--- {subtitle} ---")
        return None
    
    return Panel(
        content,
        title=f"[{THEME['panel_title']}]{title}[/{THEME['panel_title']}]" if title else None,
        subtitle=f"[{THEME['dim']}]{subtitle}[/{THEME['dim']}]" if subtitle else None,
        border_style=THEME["panel_border"],
        padding=(1, 2),
    )


def themed_table(title: str = "", columns: Optional[List[Tuple[str, str]]] = None) -> "Table":
    """
    Create a Rich Table with neuron theme.
    
    Args:
        title: Table title
        columns: List of (name, style_key) tuples
    """
    table = Table(
        title=f"[{THEME['panel_title']}]{title}[/{THEME['panel_title']}]" if title else None,
        border_style=THEME["panel_border"],
        header_style=THEME["table_header"],
        title_style=THEME["panel_title"],
    )
    
    if columns:
        for name, style_key in columns:
            table.add_column(name, style=THEME.get(style_key, THEME["table_row_1"]))
    
    return table


# ---------------------------------------------------------------------------
# Startup animation controller
# ---------------------------------------------------------------------------

def show_startup(console: Optional["Console"] = None, animate: bool = True, 
                 compact: bool = False, width: int = 80):
    """
    Main entry point for showing the UAP startup visual.
    
    Args:
        console: Rich Console
        animate: Whether to use the full typing animation
        compact: Show compact single-line header instead of full banner 
        width: Terminal width
    """
    if compact:
        compact_header(console)
        return
    
    # Get terminal width if possible
    if RICH_AVAILABLE and console:
        try:
            width = min(console.width, 90)
        except Exception:
            pass
    elif BLESSED_AVAILABLE:
        try:
            term = Terminal()
            width = min(term.width, 90)
        except Exception:
            pass
    
    width = max(width, 50)  # Minimum width
    
    if animate:
        animate_banner(console, width)
    else:
        static_banner(console, width)


# ---------------------------------------------------------------------------
# Quick test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== UAP Visuals Test ===\n")
    
    if RICH_AVAILABLE:
        c = Console()
    else:
        c = None
    
    # Test animated banner
    show_startup(c, animate=True)
    
    print("\n--- Compact header ---")
    compact_header(c)
    
    print("--- Spinner test ---")
    with NeuronSpinner(c, "Testing neuron pulse..."):
        time.sleep(2)
    
    print("--- Fade transition ---")
    fade_transition(c)
    
    print("--- Status bar ---")
    status_bar(c, session_id="abc123", backend="gemini/2.0")
    
    print("\n--- Themed panel ---")
    if RICH_AVAILABLE and c:
        p = themed_panel("Hello from UAP!", title="Test Panel")
        c.print(p)
    
    print("\nDone!")
