"""
Configuration settings for the UAP Dashboard
"""

import os
from pathlib import Path

from uap.protocol import get_uap_home

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

UAP_HOME = get_uap_home()

# Storage paths
ACT_STORAGE_DIR = UAP_HOME / "sessions"

# =============================================================================
# THEME CONFIGURATION - Dark Developer Theme
# =============================================================================

THEME = {
    "primaryColor": "#58a6ff",        # GitHub blue
    "backgroundColor": "#0d1117",      # Dark background
    "secondaryBackgroundColor": "#161b22",  # Slightly lighter
    "textColor": "#c9d1d9",           # Light gray text
    "font": "sans serif"
}

# Color palette (GitHub-inspired)
COLORS = {
    "primary": "#58a6ff",
    "success": "#238636",
    "warning": "#d29922",
    "error": "#da3633",
    "info": "#388bfd",
    "background": "#0d1117",
    "surface": "#161b22",
    "border": "#30363d",
    "text": "#c9d1d9",
    "text_muted": "#8b949e"
}

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

DEFAULT_AGENTS = {
    "planner": {
        "icon": "📋",
        "name": "Planner",
        "description": "Task breakdown and strategy",
        "model": "llama-3.1-8b-instant"
    },
    "coder": {
        "icon": "💻",
        "name": "Coder",
        "description": "Implementation and coding",
        "model": "llama-3.1-8b-instant"
    },
    "reviewer": {
        "icon": "🔍",
        "name": "Reviewer",
        "description": "Code review and testing",
        "model": "llama-3.1-8b-instant"
    },
    "designer": {
        "icon": "🎨",
        "name": "Designer",
        "description": "UI/UX and visual design",
        "model": "llama-3.1-8b-instant"
    }
}

# =============================================================================
# API CONFIGURATION
# =============================================================================

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

# Ollama (local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = "llama3"

# Default backend
DEFAULT_BACKEND = "groq"  # "groq" or "ollama"

# =============================================================================
# UI CONFIGURATION
# =============================================================================

UI_CONFIG = {
    "page_title": "UAP Segment Dashboard",
    "page_icon": "🔮",
    "layout": "wide",
    "sidebar_state": "expanded",
    "chat_column_ratio": 2,
    "act_column_ratio": 1,
    "max_messages_displayed": 100,
    "max_handshake_log_displayed": 10
}
