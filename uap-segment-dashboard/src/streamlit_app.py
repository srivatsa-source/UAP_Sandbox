"""
UAP CONSOLE v3.2
================
Auto-handoff + Bigger task window + Fixed overlaps + Animations
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path
import sys
import os
import requests
import random
import string
import hashlib

# Path setup
SCRIPT_DIR = Path(__file__).parent.resolve()
DASHBOARD_ROOT = SCRIPT_DIR.parent.resolve()
UAP_ROOT = DASHBOARD_ROOT.parent.resolve()
sys.path.insert(0, str(UAP_ROOT))

from protocol import StateManager, ACT
from dispatcher import Dispatcher, AgentConfig

USER_DATA_FILE = DASHBOARD_ROOT / "user_data.json"

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="UAP CONSOLE",
    page_icon=">_",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# PROVIDERS CONFIG
# =============================================================================

PROVIDERS = {
    "groq": {
        "name": "GROQ",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "free": True,
        "env_key": "GROQ_API_KEY"
    },
    "openrouter": {
        "name": "OPENROUTER", 
        "models": ["meta-llama/llama-3.1-8b-instruct:free", "google/gemma-2-9b-it:free"],
        "free": True,
        "env_key": "OPENROUTER_API_KEY"
    },
    "together": {
        "name": "TOGETHER",
        "models": ["meta-llama/Llama-3-8b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
        "free": True,
        "env_key": "TOGETHER_API_KEY"
    },
    "anthropic": {
        "name": "CLAUDE",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        "free": False,
        "env_key": "ANTHROPIC_API_KEY"
    },
    "openai": {
        "name": "OPENAI",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "free": False,
        "env_key": "OPENAI_API_KEY"
    },
    "google": {
        "name": "GEMINI",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
        "free": False,
        "env_key": "GOOGLE_API_KEY"
    },
    "ollama": {
        "name": "OLLAMA",
        "models": [],
        "free": True,
        "env_key": None
    }
}

AGENT_TYPES = {
    "planner": {"name": "PLANNER", "prompt": "You are a Planning Agent. Break down tasks into clear steps.", "next": "coder"},
    "coder": {"name": "CODER", "prompt": "You are a Coding Agent. Write clean, efficient code.", "next": "reviewer"},
    "reviewer": {"name": "REVIEWER", "prompt": "You are a Review Agent. Review and improve code quality.", "next": "analyst"},
    "analyst": {"name": "ANALYST", "prompt": "You are an Analysis Agent. Analyze data and provide insights.", "next": "planner"}
}

# =============================================================================
# CONSOLE CSS - Retro terminal style with animations
# =============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap');
    
    *, *::before, *::after { box-sizing: border-box !important; }
    
    :root {
        --bg0: #0a0a0a;
        --bg1: #0f0f0f;
        --bg2: #151515;
        --bg3: #1a1a1a;
        --border: #252525;
        --dim: #3a3a3a;
        --text: #707070;
        --bright: #a0a0a0;
        --white: #d0d0d0;
        --glow: #505050;
    }
    
    /* ANIMATIONS */
    @keyframes flicker {
        0%, 100% { opacity: 1; }
        92% { opacity: 1; }
        93% { opacity: 0.8; }
        94% { opacity: 1; }
        97% { opacity: 0.9; }
    }
    
    @keyframes scanline {
        0% { transform: translateY(-100%); }
        100% { transform: translateY(100vh); }
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-10px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes pulse {
        0%, 100% { border-color: var(--border); }
        50% { border-color: var(--dim); }
    }
    
    @keyframes typing {
        from { width: 0; }
        to { width: 100%; }
    }
    
    html, body, .stApp {
        background: var(--bg0) !important;
        color: var(--text) !important;
        font-family: 'Share Tech Mono', 'Courier New', monospace !important;
    }
    
    /* Subtle CRT scanline effect - no flicker */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0,0,0,0.03) 2px,
            rgba(0,0,0,0.03) 4px
        );
        pointer-events: none;
        z-index: 9999;
    }
    
    * { font-family: 'Share Tech Mono', 'Courier New', monospace !important; }
    
    /* Headers with animation */
    h1 { 
        color: var(--white) !important; 
        font-size: 1.4rem !important;
        font-weight: 400 !important;
        letter-spacing: 3px !important;
        text-transform: uppercase !important;
        animation: fadeIn 0.5s ease-out;
    }
    
    h2 { 
        color: var(--bright) !important; 
        font-size: 1rem !important;
        font-weight: 400 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        animation: fadeIn 0.3s ease-out;
    }
    
    h3, h4 { 
        color: var(--text) !important; 
        font-size: 0.9rem !important;
        letter-spacing: 1px !important;
    }
    
    p, span, label, div { 
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--bg1) !important;
        border-right: 1px solid var(--border) !important;
        width: 260px !important;
    }
    
    section[data-testid="stSidebar"] > div:first-child {
        padding: 0.8rem !important;
    }
    
    /* Buttons with hover animation */
    .stButton > button {
        font-size: 0.8rem !important;
        font-weight: 400 !important;
        background: var(--bg2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        padding: 6px 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.15s ease !important;
    }
    
    .stButton > button:hover {
        background: var(--bg3) !important;
        color: var(--bright) !important;
        border-color: var(--dim) !important;
        box-shadow: 0 0 10px rgba(80,80,80,0.2) !important;
        transform: translateY(-1px) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        font-size: 0.85rem !important;
        background: var(--bg1) !important;
        color: var(--bright) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        padding: 8px 10px !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--dim) !important;
        box-shadow: 0 0 5px rgba(80,80,80,0.15) !important;
    }
    
    /* COMPLETELY HIDE CHAT AVATARS - Multiple selectors for thoroughness */
    div[data-testid="stChatMessage"] > div:first-child,
    div[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"],
    div[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"],
    div[data-testid="stChatMessage"] .stChatMessageAvatar,
    div[data-testid="stChatMessage"] svg,
    div[data-testid="stChatMessage"] img.stAvatar,
    .stChatMessage > div:first-child > div:first-child {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        max-width: 0 !important;
        max-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
        position: absolute !important;
        left: -9999px !important;
    }
    
    /* Chat message container - clean layout */
    div[data-testid="stChatMessage"] {
        background: var(--bg2) !important;
        border: 1px solid var(--border) !important;
        border-left: 3px solid var(--dim) !important;
        border-radius: 0 !important;
        padding: 12px 16px !important;
        margin: 8px 0 !important;
        display: flex !important;
        flex-direction: column !important;
        animation: slideIn 0.3s ease-out !important;
        gap: 0 !important;
    }
    
    div[data-testid="stChatMessage"]:hover {
        border-left-color: var(--text) !important;
    }
    
    /* Message content */
    div[data-testid="stChatMessageContent"] {
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        flex: 1 !important;
    }
    
    div[data-testid="stChatMessageContent"] p,
    div[data-testid="stChatMessageContent"] div {
        color: var(--bright) !important;
        font-size: 0.85rem !important;
        line-height: 1.7 !important;
        margin: 0 !important;
        padding: 0 !important;
        word-break: break-word !important;
    }
    
    /* Chat input */
    .stChatInput {
        padding: 6px 0 !important;
    }
    
    .stChatInput > div {
        background: var(--bg1) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stChatInput > div:focus-within {
        border-color: var(--dim) !important;
        animation: pulse 2s infinite !important;
    }
    
    .stChatInput textarea {
        font-size: 0.85rem !important;
        padding: 10px !important;
        color: var(--bright) !important;
    }
    
    /* HIDE dropdown arrow text */
    div[data-baseweb="select"] span[aria-hidden="true"],
    div[data-baseweb="select"] svg {
        font-size: 0 !important;
        color: transparent !important;
    }
    
    div[data-baseweb="select"] span[aria-hidden="true"]::after {
        content: "▼" !important;
        font-size: 0.7rem !important;
        color: var(--dim) !important;
    }
    
    /* Selectbox styling */
    div[data-baseweb="select"] > div {
        background: var(--bg1) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        min-height: 32px !important;
    }
    
    div[data-baseweb="select"] > div > div {
        padding: 4px 8px !important;
    }
    
    /* Dropdown menu */
    div[data-baseweb="popover"] {
        background: var(--bg2) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
    }
    
    div[data-baseweb="menu"] {
        background: var(--bg2) !important;
    }
    
    li[role="option"] {
        background: var(--bg2) !important;
        color: var(--text) !important;
        padding: 8px 12px !important;
    }
    
    li[role="option"]:hover {
        background: var(--bg3) !important;
        color: var(--bright) !important;
    }
    
    /* Metrics */
    div[data-testid="metric-container"] {
        background: var(--bg2) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        padding: 8px !important;
        animation: fadeIn 0.4s ease-out;
    }
    
    div[data-testid="metric-container"] label {
        color: var(--dim) !important;
        font-size: 0.65rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
    }
    
    div[data-testid="stMetricValue"] {
        color: var(--bright) !important;
        font-size: 1.3rem !important;
    }
    
    /* Hide delta indicator text */
    div[data-testid="stMetricDelta"] {
        display: none !important;
    }
    
    /* Expander */
    details {
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        background: var(--bg2) !important;
        margin: 4px 0 !important;
    }
    
    summary {
        padding: 8px 12px !important;
        font-size: 0.8rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        cursor: pointer !important;
        transition: background 0.2s !important;
    }
    
    summary:hover {
        background: var(--bg3) !important;
    }
    
    details > div {
        padding: 10px !important;
        background: var(--bg1) !important;
        animation: fadeIn 0.2s ease-out !important;
    }
    
    /* JSON */
    .stJson {
        background: var(--bg1) !important;
        border: 1px solid var(--border) !important;
        font-size: 0.75rem !important;
        border-radius: 0 !important;
    }
    
    /* Custom classes */
    .console-box {
        background: var(--bg1);
        border: 1px solid var(--border);
        padding: 10px 14px;
        margin: 4px 0;
        font-size: 0.8rem;
        animation: fadeIn 0.3s ease-out;
    }
    
    .status-tag {
        display: inline-block;
        padding: 2px 8px;
        margin: 2px 4px 2px 0;
        background: var(--bg2);
        border-left: 2px solid var(--dim);
        font-size: 0.75rem;
        color: var(--text);
        text-transform: uppercase;
        letter-spacing: 1px;
        animation: slideIn 0.2s ease-out;
    }
    
    .log-entry {
        font-size: 0.7rem;
        padding: 3px 8px;
        margin: 2px 0;
        background: var(--bg1);
        border-left: 2px solid var(--border);
        color: var(--dim);
        font-family: 'Share Tech Mono', monospace;
        animation: slideIn 0.15s ease-out;
    }
    
    .handoff-banner {
        background: var(--bg3);
        border: 1px solid var(--dim);
        border-left: 3px solid var(--text);
        padding: 6px 14px;
        font-size: 0.75rem;
        color: var(--bright);
        text-transform: uppercase;
        letter-spacing: 2px;
        animation: pulse 3s infinite;
    }
    
    /* Divider */
    hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 10px 0 !important;
    }
    
    /* Code */
    code {
        background: var(--bg2) !important;
        color: var(--bright) !important;
        padding: 2px 6px !important;
        font-size: 0.8rem !important;
        border-radius: 0 !important;
    }
    
    /* Hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden !important; }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg0); }
    ::-webkit-scrollbar-thumb { background: var(--border); }
    ::-webkit-scrollbar-thumb:hover { background: var(--dim); }
    
    /* Caption */
    .stCaption, small {
        color: var(--dim) !important;
        font-size: 0.7rem !important;
        letter-spacing: 1px !important;
    }
    
    /* Loading screen */
    .boot-screen {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: var(--bg0);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 10000;
        font-family: 'VT323', monospace;
    }
    
    .boot-text {
        color: var(--bright);
        font-size: 1.2rem;
        letter-spacing: 2px;
        animation: flicker 0.5s infinite;
    }
    
    .boot-cursor {
        display: inline-block;
        width: 10px;
        height: 1.2rem;
        background: var(--bright);
        animation: blink 0.8s infinite;
        margin-left: 4px;
    }
    
    /* Container animations */
    div[data-testid="stVerticalBlock"] > div {
        animation: fadeIn 0.2s ease-out;
    }
    
    /* Checkbox */
    .stCheckbox label {
        font-size: 0.8rem !important;
        letter-spacing: 1px !important;
    }
    
    .stCheckbox label span {
        color: var(--text) !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HELPERS
# =============================================================================

def hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()[:16]

def load_user_data() -> dict:
    if USER_DATA_FILE.exists():
        try:
            return json.load(open(USER_DATA_FILE))
        except:
            pass
    return {"users": {}}

def save_user_data(data: dict):
    json.dump(data, open(USER_DATA_FILE, 'w'), indent=2)

def get_user(email: str) -> dict:
    return load_user_data()["users"].get(hash_email(email), {})

def save_user(email: str, profile: dict):
    data = load_user_data()
    data["users"][hash_email(email)] = profile
    save_user_data(data)

# API Validators
def check_groq(key: str) -> bool:
    try:
        return requests.get("https://api.groq.com/openai/v1/models", 
                           headers={"Authorization": f"Bearer {key}"}, timeout=5).status_code == 200
    except: return False

def check_openrouter(key: str) -> bool:
    try:
        return requests.get("https://openrouter.ai/api/v1/models",
                           headers={"Authorization": f"Bearer {key}"}, timeout=5).status_code == 200
    except: return False

def check_together(key: str) -> bool:
    try:
        return requests.get("https://api.together.xyz/v1/models",
                           headers={"Authorization": f"Bearer {key}"}, timeout=5).status_code == 200
    except: return False

def check_anthropic(key: str) -> bool:
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                         headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                         json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                         timeout=10)
        return r.status_code in [200, 400, 429]
    except: return False

def check_openai(key: str) -> bool:
    try:
        return requests.get("https://api.openai.com/v1/models",
                           headers={"Authorization": f"Bearer {key}"}, timeout=5).status_code == 200
    except: return False

def check_google(key: str) -> bool:
    try:
        return requests.get(f"https://generativelanguage.googleapis.com/v1/models?key={key}", timeout=5).status_code == 200
    except: return False

def check_ollama() -> list:
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except: pass
    return []

VALIDATORS = {
    "groq": check_groq, "openrouter": check_openrouter, "together": check_together,
    "anthropic": check_anthropic, "openai": check_openai, "google": check_google
}

# =============================================================================
# STATS PAGE - Usage Analytics Dashboard
# =============================================================================

def render_stats_page():
    """Render usage statistics dashboard in retro terminal style."""
    from collections import Counter
    
    st.markdown("""
    <div style="
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 30px;
    ">
        <span style="font-size: 2rem;">📊</span>
        <div>
            <div style="color: #d0d0d0; font-size: 1.5rem; letter-spacing: 3px; font-family: 'VT323', monospace;">USAGE STATS</div>
            <div style="color: #3a3a3a; font-size: 0.75rem; letter-spacing: 2px;">SYSTEM ANALYTICS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Load all ACT session files
    act_dir = UAP_ROOT / "act_storage"
    act_files = list(act_dir.glob("*.json")) if act_dir.exists() else []
    
    sessions = []
    for f in act_files:
        try:
            data = json.loads(f.read_text())
            sessions.append(data)
        except:
            pass
    
    if not sessions:
        st.markdown("""
        <div class="console-box" style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 3rem; margin-bottom: 15px; opacity: 0.3;">📭</div>
            <div style="color: #505050; font-size: 1.1rem; letter-spacing: 2px; margin-bottom: 10px;">NO DATA YET</div>
            <div style="color: #3a3a3a; font-size: 0.8rem;">Run some tasks to see your stats</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Calculate stats
    total_sessions = len(sessions)
    total_tasks = sum(len(s.get("task_chain", [])) for s in sessions)
    total_handoffs = sum(len(s.get("handshake_log", [])) for s in sessions)
    
    # Agent usage counter
    agent_counts = Counter()
    for s in sessions:
        for log in s.get("handshake_log", []):
            agent = log.get("agent", "unknown")
            # Clean up agent names
            agent_name = agent.split("_")[0] if "_" in agent else agent
            agent_counts[agent_name] += 1
    
    # Provider usage
    provider_counts = Counter()
    for s in sessions:
        for log in s.get("handshake_log", []):
            agent = log.get("agent", "")
            if "_" in agent:
                provider = agent.split("_")[1] if len(agent.split("_")) > 1 else "unknown"
                provider_counts[provider] += 1
    
    # ===== OVERVIEW METRICS =====
    st.markdown("### 〉OVERVIEW")
    
    c1, c2, c3, c4 = st.columns(4)
    
    metrics = [
        ("SESSIONS", total_sessions, "📁"),
        ("TASKS", total_tasks, "✅"),
        ("HANDOFFS", total_handoffs, "🔄"),
        ("AVG/SESSION", round(total_tasks / max(total_sessions, 1), 1), "📈"),
    ]
    
    for col, (label, value, icon) in zip([c1, c2, c3, c4], metrics):
        with col:
            st.markdown(f"""
            <div class="console-box" style="text-align: center; padding: 20px;">
                <div style="font-size: 1.5rem; margin-bottom: 8px; opacity: 0.7;">{icon}</div>
                <div style="color: #d0d0d0; font-size: 2.5rem; font-family: 'VT323', monospace; line-height: 1;">{value}</div>
                <div style="color: #505050; font-size: 0.7rem; letter-spacing: 2px; margin-top: 8px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ===== AGENT USAGE =====
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.markdown("### 〉AGENT USAGE")
        
        if agent_counts:
            total_agent_calls = sum(agent_counts.values())
            
            st.markdown('<div class="console-box" style="padding: 20px;">', unsafe_allow_html=True)
            
            for agent, count in agent_counts.most_common(6):
                pct = int(count / total_agent_calls * 100)
                bar_width = max(pct, 5)  # Minimum bar width
                
                st.markdown(f"""
                <div style="margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span style="color: #a0a0a0; font-size: 0.85rem; letter-spacing: 1px; text-transform: uppercase;">{agent}</span>
                        <span style="color: #707070; font-size: 0.85rem;">{count} <span style="color: #3a3a3a;">({pct}%)</span></span>
                    </div>
                    <div style="background: #151515; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="
                            background: linear-gradient(90deg, #3a3a3a 0%, #505050 100%);
                            width: {bar_width}%;
                            height: 100%;
                            border-radius: 4px;
                            transition: width 0.5s ease;
                        "></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="console-box" style="text-align: center; padding: 40px; color: #3a3a3a;">
                No agent data available
            </div>
            """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### 〉PROVIDERS")
        
        if provider_counts:
            st.markdown('<div class="console-box" style="padding: 20px;">', unsafe_allow_html=True)
            
            for provider, count in provider_counts.most_common(5):
                st.markdown(f"""
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 0;
                    border-bottom: 1px solid #1a1a1a;
                ">
                    <span style="color: #a0a0a0; font-size: 0.85rem; letter-spacing: 1px; text-transform: uppercase;">{provider}</span>
                    <span style="
                        background: #1a1a1a;
                        color: #707070;
                        padding: 4px 12px;
                        font-size: 0.8rem;
                        font-family: 'VT323', monospace;
                    ">{count}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="console-box" style="text-align: center; padding: 40px; color: #3a3a3a;">
                No provider data
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ===== RECENT SESSIONS =====
    st.markdown("### 〉RECENT SESSIONS")
    
    sorted_sessions = sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)[:8]
    
    st.markdown('<div class="console-box" style="padding: 15px;">', unsafe_allow_html=True)
    
    for s in sorted_sessions:
        obj = s.get("current_objective", "No objective")
        obj_display = (obj[:50] + "...") if len(obj) > 50 else obj
        sid = s.get("session_id", "???")
        tasks = len(s.get("task_chain", []))
        handoffs = len(s.get("handshake_log", []))
        updated = s.get("updated_at", "")[:10]
        
        st.markdown(f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin-bottom: 8px;
            background: #0f0f0f;
            border: 1px solid #1a1a1a;
            border-radius: 4px;
        ">
            <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                    <span style="color: #3a3a3a; font-family: monospace; font-size: 0.75rem;">[{sid}]</span>
                    <span style="color: #505050; font-size: 0.7rem;">{updated}</span>
                </div>
                <div style="color: #707070; font-size: 0.85rem;">{obj_display}</div>
            </div>
            <div style="display: flex; gap: 15px; color: #3a3a3a; font-size: 0.75rem;">
                <span>📝 {tasks}</span>
                <span>🔄 {handoffs}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ===== ARTIFACTS SUMMARY =====
    st.markdown("### 〉ARTIFACTS")
    
    total_code = sum(len(s.get("artifacts", {}).get("code_snippets", [])) for s in sessions)
    total_decisions = sum(len(s.get("artifacts", {}).get("decisions", [])) for s in sessions)
    total_files = sum(len(s.get("artifacts", {}).get("files_modified", [])) for s in sessions)
    
    art_c1, art_c2, art_c3 = st.columns(3)
    
    artifact_metrics = [
        ("CODE SNIPPETS", total_code, "💻"),
        ("DECISIONS", total_decisions, "🎯"),
        ("FILES MODIFIED", total_files, "📄"),
    ]
    
    for col, (label, value, icon) in zip([art_c1, art_c2, art_c3], artifact_metrics):
        with col:
            st.markdown(f"""
            <div class="console-box" style="text-align: center; padding: 20px;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
                    <span style="font-size: 1.2rem; opacity: 0.7;">{icon}</span>
                    <span style="color: #d0d0d0; font-size: 1.8rem; font-family: 'VT323', monospace;">{value}</span>
                </div>
                <div style="color: #505050; font-size: 0.7rem; letter-spacing: 1px; margin-top: 8px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

# =============================================================================
# SESSION STATE
# =============================================================================

def init_state():
    defaults = {
        "step": "login", "email": "", "api_keys": {}, "providers": {},
        "agent_config": {}, "messages": [], "state_mgr": None, "dispatcher": None,
        "act": None, "session": None, "transfers": [], "auto_handoff": True,
        "current_task": "", "processing": False, "boot_done": False,
        "page": "main"  # "main" or "stats"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            if k == "state_mgr":
                st.session_state[k] = StateManager(storage_dir=str(UAP_ROOT / "act_storage"))
            elif k == "dispatcher":
                st.session_state[k] = Dispatcher()
                st.session_state[k].state_manager = st.session_state.state_mgr
            else:
                st.session_state[k] = v

# =============================================================================
# BOOT SCREEN - Retro console loading
# =============================================================================

def render_boot_screen():
    """Show retro console boot sequence"""
    import time
    
    boot_html = """
    <div id="boot-container" style="
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: #0a0a0a;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 99999;
        font-family: 'VT323', 'Courier New', monospace;
    ">
        <div style="max-width: 600px; width: 90%; color: #707070;">
            <pre style="color: #505050; font-size: 0.7rem; margin-bottom: 20px;">
╔══════════════════════════════════════════════════════════════╗
║  UAP CONSOLE v3.2 - Universal Agent Protocol                 ║
║  (c) 2026 Agent Swarm Initiative                             ║
╚══════════════════════════════════════════════════════════════╝
            </pre>
            <div id="boot-log" style="font-size: 0.9rem; line-height: 1.8;">
                <div class="boot-line" style="animation: fadeIn 0.3s ease-out;">
                    <span style="color: #3a3a3a;">[OK]</span> Initializing kernel...
                </div>
                <div class="boot-line" style="animation: fadeIn 0.3s ease-out 0.2s both;">
                    <span style="color: #3a3a3a;">[OK]</span> Loading state manager...
                </div>
                <div class="boot-line" style="animation: fadeIn 0.3s ease-out 0.4s both;">
                    <span style="color: #3a3a3a;">[OK]</span> Dispatcher ready...
                </div>
                <div class="boot-line" style="animation: fadeIn 0.3s ease-out 0.6s both;">
                    <span style="color: #3a3a3a;">[OK]</span> Agent protocols loaded...
                </div>
                <div class="boot-line" style="animation: fadeIn 0.3s ease-out 0.8s both;">
                    <span style="color: #a0a0a0;">[>>]</span> System ready.
                </div>
            </div>
            <div style="margin-top: 30px; animation: fadeIn 0.5s ease-out 1.2s both;">
                <span style="color: #a0a0a0;">PRESS ANY KEY TO CONTINUE</span>
                <span style="
                    display: inline-block;
                    width: 10px;
                    height: 1rem;
                    background: #a0a0a0;
                    animation: blink 0.7s infinite;
                    margin-left: 5px;
                    vertical-align: middle;
                "></span>
            </div>
        </div>
    </div>
    <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }
    </style>
    <script>
        document.addEventListener('keydown', function() {
            document.getElementById('boot-container').style.display = 'none';
        });
        document.addEventListener('click', function() {
            document.getElementById('boot-container').style.display = 'none';
        });
        setTimeout(function() {
            document.getElementById('boot-container').style.opacity = '0';
            document.getElementById('boot-container').style.transition = 'opacity 0.5s';
            setTimeout(function() {
                document.getElementById('boot-container').style.display = 'none';
            }, 500);
        }, 3000);
    </script>
    """
    
    st.components.v1.html(boot_html, height=0)

def show_loading(message: str = "PROCESSING"):
    """Show inline loading indicator"""
    return f"""
    <div class="console-box" style="display: flex; align-items: center; gap: 12px;">
        <div style="
            width: 8px; height: 8px;
            background: #707070;
            animation: pulse 0.6s infinite;
        "></div>
        <span style="color: #a0a0a0; letter-spacing: 2px; font-size: 0.8rem;">{message}</span>
        <span style="color: #3a3a3a;">...</span>
    </div>
    <style>
        @keyframes pulse {{
            0%, 100% {{ opacity: 0.3; }}
            50% {{ opacity: 1; }}
        }}
    </style>
    """

# =============================================================================
# LOGIN
# =============================================================================

def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# UAP CONSOLE")
        st.markdown("Universal Agent Protocol")
        st.markdown("---")
        
        st.markdown("### Login")
        email = st.text_input("Email", placeholder="you@example.com", label_visibility="collapsed")
        
        if email:
            user = get_user(email)
            if user.get("api_keys"):
                st.caption("Returning user - keys saved")
        
        if st.button("Continue", use_container_width=True):
            if email and "@" in email:
                st.session_state.email = email.lower().strip()
                user = get_user(email)
                if user.get("api_keys"):
                    st.session_state.api_keys = user["api_keys"]
                st.session_state.step = "connect"
                st.rerun()
            else:
                st.error("Enter valid email")

# =============================================================================
# CONNECT
# =============================================================================

def render_connect():
    st.markdown("# CONNECT PROVIDERS")
    st.markdown(f'<div class="console-box" style="display: inline-block;">{st.session_state.email}</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Auto-detect with loading animation
    auto = {}
    with st.spinner(""):
        for pid, pinfo in PROVIDERS.items():
            if pinfo.get("env_key"):
                key = os.environ.get(pinfo["env_key"], "")
                if key and pid in VALIDATORS and VALIDATORS[pid](key):
                    auto[pid] = key
                    st.session_state.api_keys[pid] = key
    
    ollama_models = check_ollama()
    
    if auto or ollama_models:
        st.markdown("### AUTO-DETECTED")
        detected_html = ""
        for pid in auto:
            detected_html += f'<span class="status-tag">{PROVIDERS[pid]["name"]}</span>'
        if ollama_models:
            detected_html += f'<span class="status-tag">OLLAMA ({len(ollama_models)})</span>'
        st.markdown(detected_html, unsafe_allow_html=True)
    
    st.markdown("### API KEYS")
    
    c1, c2 = st.columns(2)
    with c1:
        st.caption("FREE TIER")
        groq = st.text_input("GROQ", value=st.session_state.api_keys.get("groq", ""), type="password", key="k_groq")
        together = st.text_input("TOGETHER", value=st.session_state.api_keys.get("together", ""), type="password", key="k_tog")
        openrouter = st.text_input("OPENROUTER", value=st.session_state.api_keys.get("openrouter", ""), type="password", key="k_or")
    
    with c2:
        st.caption("PREMIUM")
        anthropic = st.text_input("CLAUDE", value=st.session_state.api_keys.get("anthropic", ""), type="password", key="k_ant")
        openai = st.text_input("OPENAI", value=st.session_state.api_keys.get("openai", ""), type="password", key="k_oai")
        google = st.text_input("GEMINI", value=st.session_state.api_keys.get("google", ""), type="password", key="k_goog")
    
    st.markdown("---")
    
    if st.button("CONNECT & LAUNCH", use_container_width=True, type="primary"):
        keys = {"groq": groq, "together": together, "openrouter": openrouter, 
                "anthropic": anthropic, "openai": openai, "google": google}
        keys = {k: v for k, v in keys.items() if v}
        
        # Show validation progress
        progress_placeholder = st.empty()
        progress_placeholder.markdown(show_loading("VALIDATING KEYS"), unsafe_allow_html=True)
        
        connected = {}
        for pid, key in keys.items():
            if pid in VALIDATORS and VALIDATORS[pid](key):
                connected[pid] = {"name": PROVIDERS[pid]["name"], "models": PROVIDERS[pid]["models"], "key": key}
        
        if ollama_models:
            connected["ollama"] = {"name": "OLLAMA", "models": ollama_models, "key": None}
        
        progress_placeholder.empty()
        
        if connected:
            st.session_state.api_keys = keys
            st.session_state.providers = connected
            save_user(st.session_state.email, {"api_keys": keys, "last": datetime.now().isoformat()})
            st.session_state.step = "main"
            st.rerun()
        else:
            st.error("NO VALID PROVIDERS FOUND")

# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    with st.sidebar:
        st.markdown("## UAP")
        st.markdown(f'<div class="console-box">{st.session_state.email[:24]}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.caption("ONLINE")
        providers_html = "".join([f'<span class="status-tag">{pinfo["name"]}</span>' for pinfo in st.session_state.providers.values()])
        st.markdown(providers_html, unsafe_allow_html=True)
        
        st.markdown("---")
        st.caption("AGENT MODELS")
        
        options = []
        for pid, pinfo in st.session_state.providers.items():
            for model in pinfo["models"][:2]:
                short = model.split("/")[-1][:12]
                options.append({"id": f"{pid}|{model}", "label": f"{pinfo['name'][:3]}/{short}", "p": pid, "m": model})
        
        if options:
            for atype, ainfo in AGENT_TYPES.items():
                curr = st.session_state.agent_config.get(atype, {})
                curr_id = f"{curr.get('provider', '')}|{curr.get('model', '')}"
                ids = [o["id"] for o in options]
                idx = ids.index(curr_id) if curr_id in ids else 0
                sel = st.selectbox(ainfo["name"], ids, format_func=lambda x: next((o["label"] for o in options if o["id"] == x), x), index=idx, key=f"a_{atype}")
                if sel:
                    p, m = sel.split("|", 1)
                    st.session_state.agent_config[atype] = {"provider": p, "model": m}
        
        st.markdown("---")
        st.caption("OPTIONS")
        st.session_state.auto_handoff = st.checkbox("AUTO-HANDOFF", value=st.session_state.auto_handoff)
        
        st.markdown("---")
        
        # Navigation buttons
        st.caption("NAVIGATE")
        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            if st.button("📊 STATS", use_container_width=True):
                st.session_state.page = "stats"
                st.rerun()
        with nav_col2:
            if st.button("💬 CHAT", use_container_width=True):
                st.session_state.page = "main"
                st.rerun()
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("NEW", use_container_width=True):
                st.session_state.session = None
                st.session_state.act = None
                st.session_state.messages = []
                st.session_state.transfers = []
                st.session_state.current_task = ""
                st.rerun()
        with c2:
            if st.button("OUT", use_container_width=True):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()

# =============================================================================
# MAIN - Bigger task window, smaller prompt
# =============================================================================

def register_agent(atype: str, provider: str, model: str) -> str:
    aid = f"{atype}_{provider}"
    cfg = AgentConfig(agent_id=aid, agent_type=atype, system_prompt=AGENT_TYPES[atype]["prompt"], model=model, backend=provider)
    try:
        st.session_state.dispatcher.register_agent(cfg)
    except: pass
    return aid

def set_env_key(pid: str, key: str):
    env_map = {"groq": "GROQ_API_KEY", "together": "TOGETHER_API_KEY", "openrouter": "OPENROUTER_API_KEY",
               "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}
    if pid in env_map and key:
        os.environ[env_map[pid]] = key

def process_task(agent_type: str, prompt: str, auto_handoff: bool = False):
    """Process a task with optional auto-handoff"""
    cfg = st.session_state.agent_config.get(agent_type, {})
    if not cfg:
        return {"error": "No model configured for " + agent_type}
    
    pid, model = cfg["provider"], cfg["model"]
    aid = register_agent(agent_type, pid, model)
    pinfo = st.session_state.providers.get(pid, {})
    set_env_key(pid, pinfo.get("key"))
    
    st.session_state.transfers.append({
        "t": datetime.now().strftime("%H:%M:%S"),
        "from": "USER" if not st.session_state.messages else agent_type.upper(),
        "to": agent_type.upper()
    })
    
    try:
        result = st.session_state.dispatcher.dispatch(
            agent_id=aid,
            session_id=st.session_state.session,
            task=prompt,
            auto_handoff=False
        )
        
        st.session_state.session = result["session_id"]
        st.session_state.act = st.session_state.state_mgr.get_session(result["session_id"])
        
        response = result.get("response", "No response")
        return {
            "response": response,
            "agent": f"{AGENT_TYPES[agent_type]['name']}/{pinfo.get('name', pid)}",
            "agent_type": agent_type,
            "handoff_info": result.get("handoff_info")
        }
    except Exception as e:
        return {"error": str(e)}

def render_main():
    st.markdown("# UAP CONSOLE")
    
    # Layout: big task area on left, state on right
    task_col, state_col = st.columns([4, 2])
    
    with task_col:
        # Compact header row
        h1, h2, h3 = st.columns([2, 2, 1])
        with h1:
            st.markdown("## TASK")
        with h2:
            agent_type = st.selectbox("Route", list(AGENT_TYPES.keys()), 
                                      format_func=lambda x: AGENT_TYPES[x]["name"],
                                      key="agent_sel", label_visibility="collapsed")
        with h3:
            cfg = st.session_state.agent_config.get(agent_type, {})
            if cfg:
                pinfo = st.session_state.providers.get(cfg.get("provider"), {})
                st.caption(pinfo.get("name", "?"))
        
        # Show auto-handoff status
        if st.session_state.auto_handoff:
            st.markdown('<div class="handoff-banner">AUTO-HANDOFF ENABLED</div>', unsafe_allow_html=True)
        
        # BIG task/response area - custom rendering to avoid avatar overlap
        task_container = st.container(height=420)
        with task_container:
            if not st.session_state.messages:
                st.markdown("""
                <div class="console-box" style="text-align: center; padding: 40px 20px; color: #3a3a3a;">
                    <div style="font-size: 1.5rem; margin-bottom: 10px;">_</div>
                    <div style="letter-spacing: 2px;">AWAITING INPUT</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for i, msg in enumerate(st.session_state.messages):
                    is_user = msg["role"] == "user"
                    prefix = "USER" if is_user else msg.get("agent", "AGENT")
                    border_color = "#3a3a3a" if is_user else "#505050"
                    
                    # Custom message box - no avatars
                    st.markdown(f"""
                    <div style="
                        background: #151515;
                        border: 1px solid #252525;
                        border-left: 3px solid {border_color};
                        padding: 12px 16px;
                        margin: 8px 0;
                        animation: slideIn 0.3s ease-out;
                    ">
                        <div style="
                            color: #505050;
                            font-size: 0.7rem;
                            letter-spacing: 2px;
                            margin-bottom: 6px;
                            text-transform: uppercase;
                        ">[{prefix}]</div>
                        <div style="
                            color: #a0a0a0;
                            font-size: 0.85rem;
                            line-height: 1.7;
                            white-space: pre-wrap;
                            word-break: break-word;
                        ">{msg["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Compact prompt input
        prompt = st.chat_input("Enter task...", key="task_input")
        
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.current_task = prompt
            
            # Process with selected agent
            result = process_task(agent_type, prompt)
            
            if "error" in result:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {result['error']}", "agent": "SYSTEM"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": result["response"], "agent": result["agent"]})
                
                # Auto-handoff chain
                if st.session_state.auto_handoff and result.get("handoff_info"):
                    next_agent = AGENT_TYPES[result["agent_type"]]["next"]
                    handoff_result = process_task(next_agent, f"Continue from previous: {result['response'][:500]}")
                    if "error" not in handoff_result:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": handoff_result["response"],
                            "agent": handoff_result["agent"]
                        })
            
            st.rerun()
    
    with state_col:
        st.markdown("## STATE")
        
        if st.session_state.act:
            act = st.session_state.act.to_dict()
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("TASKS", len(act.get("task_chain", [])))
            with c2:
                st.metric("XFERS", len(st.session_state.transfers))
            
            # Current objective
            with st.expander("OBJECTIVE", expanded=True):
                obj = act.get("current_objective", "")
                st.text(obj[:150] if obj else "None")
            
            # Transfer log
            st.caption("TRANSFER LOG")
            log_box = st.container(height=100)
            with log_box:
                for e in st.session_state.transfers[-6:]:
                    st.markdown(f'<div class="log-entry">[{e["t"]}] {e["from"]} → {e["to"]}</div>', unsafe_allow_html=True)
            
            # Raw state
            with st.expander("RAW"):
                st.json(act)
        else:
            st.markdown("""
            <div class="console-box" style="text-align: center; padding: 20px; color: #3a3a3a;">
                <div style="letter-spacing: 1px; font-size: 0.8rem;">NO ACTIVE STATE</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Save buttons
        c1, c2 = st.columns(2)
        with c1:
            if st.button("SAVE", use_container_width=True, disabled=not st.session_state.messages):
                out = UAP_ROOT / "local_outputs"
                out.mkdir(exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                (out / f"chat_{ts}.txt").write_text(
                    "\n\n".join([f"[{m.get('agent', m['role'].upper())}]\n{m['content']}" for m in st.session_state.messages]),
                    encoding="utf-8"
                )
                st.success("Saved")
        with c2:
            if st.button("STATE", use_container_width=True, disabled=not st.session_state.act):
                out = UAP_ROOT / "local_outputs"
                out.mkdir(exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                (out / f"state_{ts}.json").write_text(json.dumps(st.session_state.act.to_dict(), indent=2), encoding="utf-8")
                st.success("Saved")

# =============================================================================
# MAIN
# =============================================================================

def main():
    init_state()
    
    # Show boot screen on first load
    if not st.session_state.boot_done:
        render_boot_screen()
        st.session_state.boot_done = True
    
    if st.session_state.step == "login":
        render_login()
    elif st.session_state.step == "connect":
        render_connect()
    elif st.session_state.step == "main":
        render_sidebar()
        # Route to appropriate page
        if st.session_state.get("page") == "stats":
            render_stats_page()
        else:
            render_main()

if __name__ == "__main__":
    main()
