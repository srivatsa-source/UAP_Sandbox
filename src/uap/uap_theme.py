"""
uap_theme.py — Sunset Hue Theme for Universal Agent Protocol CLI
Import and pass SUNSET_THEME into any rich.console.Console instance.
"""

from rich.theme import Theme
from rich.style import Style

# ─────────────────────────────────────────────────────────────────────────────
# PALETTE REFERENCE
# ─────────────────────────────────────────────────────────────────────────────
#
#   Dawn Yellow  #FFD580  ████
#   Gold Orange  #FFC44D  ████
#   Vivid Orange #FFA500  ████  ← Cat color
#   Deep Orange  #FF7F32  ████
#   Sunset Red   #FF6B35  ████
#   Coral        #FF5050  ████
#   Coral Pink   #FF4D6D  ████
#   Bubblegum    #FF69B4  ████
#   Soft Pink    #FF85A1  ████
#   Magenta      #E040FB  ████  ← Prompt color
#   Violet       #9C27B0  ████
#   Deep Purple  #6A0DAD  ████
#   Night Purple #3D0066  ████
#
# ─────────────────────────────────────────────────────────────────────────────

PALETTE = {
    "dawn":       "#FFD580",
    "gold":       "#FFC44D",
    "orange":     "#FFA500",
    "deep_orange":"#FF7F32",
    "sunset":     "#FF6B35",
    "coral_red":  "#FF5050",
    "coral":      "#FF4D6D",
    "bubblegum":  "#FF69B4",
    "pink":       "#FF85A1",
    "magenta":    "#E040FB",
    "violet":     "#9C27B0",
    "purple":     "#6A0DAD",
    "dusk":       "#3D0066",
}

# ─────────────────────────────────────────────────────────────────────────────
# GRADIENT STOPS — ordered sunrise → dusk
# Used by cli_ui.sunset_gradient()
# ─────────────────────────────────────────────────────────────────────────────

GRADIENT_STOPS = [
    PALETTE["dawn"],
    PALETTE["gold"],
    PALETTE["orange"],
    PALETTE["deep_orange"],
    PALETTE["sunset"],
    PALETTE["coral_red"],
    PALETTE["coral"],
    PALETTE["bubblegum"],
    PALETTE["magenta"],
    PALETTE["violet"],
    PALETTE["purple"],
]

# ─────────────────────────────────────────────────────────────────────────────
# RICH THEME
# ─────────────────────────────────────────────────────────────────────────────

SUNSET_THEME = Theme(
    {
        # ── Raw palette styles ────────────────────────────────────────
        "sunset.dawn":     f"bold {PALETTE['dawn']}",
        "sunset.gold":     f"bold {PALETTE['gold']}",
        "sunset.orange":   f"bold {PALETTE['orange']}",
        "sunset.coral":    f"bold {PALETTE['coral']}",
        "sunset.pink":     f"bold {PALETTE['pink']}",
        "sunset.magenta":  f"bold {PALETTE['magenta']}",
        "sunset.violet":   f"bold {PALETTE['violet']}",
        "sunset.purple":   f"bold {PALETTE['purple']}",
        "sunset.dusk":     f"bold {PALETTE['dusk']}",

        # ── Semantic / component roles ────────────────────────────────
        "uap.header":      f"{PALETTE['sunset']} on default",
        "uap.prompt":      f"bold {PALETTE['magenta']}",
        "uap.user":        PALETTE["dawn"],
        "uap.agent":       PALETTE["pink"],
        "uap.system":      f"dim {PALETTE['violet']}",

        # Status
        "uap.success":     "bold #00E676",
        "uap.warning":     f"bold {PALETTE['orange']}",
        "uap.error":       f"bold {PALETTE['coral']}",

        # UI chrome
        "uap.muted":       f"dim {PALETTE['purple']}",
        "uap.border":      PALETTE["purple"],
        "uap.thinking":    f"italic {PALETTE['magenta']}",
        "uap.command":     f"bold {PALETTE['dawn']}",
        "uap.key":         f"bold {PALETTE['sunset']}",
        "uap.value":       PALETTE["pink"],

        # Markdown overrides (rich uses these names internally)
        "markdown.h1":     f"bold {PALETTE['orange']}",
        "markdown.h2":     f"bold {PALETTE['sunset']}",
        "markdown.h3":     f"bold {PALETTE['coral']}",
        "markdown.code":   f"{PALETTE['dawn']} on #1A0033",
        "markdown.link":   f"underline {PALETTE['magenta']}",
    }
)

# ─────────────────────────────────────────────────────────────────────────────
# BOX STYLES (pass to rich.panel.Panel or rich.table.Table)
# ─────────────────────────────────────────────────────────────────────────────

BORDER_STYLES = {
    "act":     PALETTE["violet"],      # ACT panel border
    "handoff": PALETTE["magenta"],     # Handoff log border
    "agent":   PALETTE["sunset"],      # Agent response border
    "user":    PALETTE["dawn"],        # User message border
    "error":   PALETTE["coral"],       # Error panel border
    "success": "#00E676",              # Success panel border
    "header":  PALETTE["purple"],      # Main header border
}

__all__ = [
    "PALETTE",
    "GRADIENT_STOPS",
    "SUNSET_THEME",
    "BORDER_STYLES",
]
