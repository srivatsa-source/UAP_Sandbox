"""
UAP SEGMENT DASHBOARD v2.0
==========================
RETRO B/W CONSOLE INTERFACE
All major AI providers + Real email auth
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path
import sys
import os
import requests
import smtplib
import ssl
import random
import string
import hashlib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    page_icon="[_]",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# ALL AI PROVIDERS - Claude, GPT, Groq, etc.
# =============================================================================

PROVIDERS = {
    "anthropic": {
        "name": "ANTHROPIC",
        "display": "Claude AI",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "env_key": "ANTHROPIC_API_KEY",
        "signup": "https://console.anthropic.com"
    },
    "openai": {
        "name": "OPENAI",
        "display": "GPT Models",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "env_key": "OPENAI_API_KEY",
        "signup": "https://platform.openai.com/api-keys"
    },
    "groq": {
        "name": "GROQ",
        "display": "Groq Fast",
        "models": ["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "env_key": "GROQ_API_KEY",
        "signup": "https://console.groq.com"
    },
    "together": {
        "name": "TOGETHER",
        "display": "Together AI",
        "models": ["meta-llama/Llama-3-8b-chat-hf", "meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
        "env_key": "TOGETHER_API_KEY",
        "signup": "https://api.together.xyz"
    },
    "openrouter": {
        "name": "OPENROUTER",
        "display": "OpenRouter",
        "models": ["meta-llama/llama-3.1-8b-instruct:free", "google/gemma-2-9b-it:free", "mistralai/mistral-7b-instruct:free"],
        "env_key": "OPENROUTER_API_KEY",
        "signup": "https://openrouter.ai"
    },
    "google": {
        "name": "GOOGLE",
        "display": "Gemini",
        "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
        "env_key": "GOOGLE_API_KEY",
        "signup": "https://makersuite.google.com/app/apikey"
    },
    "mistral": {
        "name": "MISTRAL",
        "display": "Mistral AI",
        "models": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mistral-7b"],
        "env_key": "MISTRAL_API_KEY",
        "signup": "https://console.mistral.ai"
    },
    "cohere": {
        "name": "COHERE",
        "display": "Cohere",
        "models": ["command-r-plus", "command-r", "command-light"],
        "env_key": "COHERE_API_KEY",
        "signup": "https://dashboard.cohere.com/api-keys"
    },
    "huggingface": {
        "name": "HUGGINGFACE",
        "display": "HuggingFace",
        "models": ["meta-llama/Llama-2-7b-chat-hf", "google/flan-t5-large", "tiiuae/falcon-7b-instruct"],
        "env_key": "HF_API_KEY",
        "signup": "https://huggingface.co/settings/tokens"
    },
    "ollama": {
        "name": "OLLAMA",
        "display": "Local Ollama",
        "models": [],
        "env_key": None,
        "signup": "https://ollama.ai"
    }
}

SMTP_PROVIDERS = {
    "gmail": {"name": "GMAIL", "server": "smtp.gmail.com", "port": 587},
    "outlook": {"name": "OUTLOOK", "server": "smtp-mail.outlook.com", "port": 587},
    "yahoo": {"name": "YAHOO", "server": "smtp.mail.yahoo.com", "port": 587},
    "zoho": {"name": "ZOHO", "server": "smtp.zoho.com", "port": 587},
    "custom": {"name": "CUSTOM", "server": "", "port": 587}
}

AGENT_TYPES = {
    "planner": {"name": "PLANNER", "prompt": "You are a Planning Agent. Break down tasks step-by-step."},
    "coder": {"name": "CODER", "prompt": "You are a Coding Agent. Write clean, working code."},
    "reviewer": {"name": "REVIEWER", "prompt": "You are a Review Agent. Review code for quality."},
    "analyst": {"name": "ANALYST", "prompt": "You are an Analysis Agent. Analyze and document."}
}

# =============================================================================
# RETRO CONSOLE CSS - Pixelated B/W with CRT effects
# =============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=VT323&family=Press+Start+2P&display=swap');
    
    :root {
        --bg: #0a0a0a;
        --bg2: #111111;
        --bg3: #1a1a1a;
        --border: #2a2a2a;
        --dim: #444444;
        --text: #888888;
        --bright: #cccccc;
        --white: #ffffff;
    }
    
    * { 
        font-family: 'VT323', monospace !important; 
        image-rendering: pixelated;
    }
    
    /* Main background with CRT effect */
    .stApp {
        background: var(--bg);
        color: var(--text);
    }
    
    /* Scanlines overlay */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: repeating-linear-gradient(
            0deg,
            rgba(0,0,0,0.15),
            rgba(0,0,0,0.15) 1px,
            transparent 1px,
            transparent 2px
        );
        pointer-events: none;
        z-index: 9999;
    }
    
    /* CRT vignette */
    .stApp::after {
        content: "";
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.4) 100%);
        pointer-events: none;
        z-index: 9998;
    }
    
    /* Animations */
    @keyframes flicker {
        0%, 97%, 100% { opacity: 1; }
        98% { opacity: 0.85; }
        99% { opacity: 0.95; }
    }
    
    @keyframes blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
    }
    
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 2px var(--dim); }
        50% { box-shadow: 0 0 8px var(--dim); }
    }
    
    @keyframes typing {
        from { width: 0; }
        to { width: 100%; }
    }
    
    .blink { animation: blink 1s infinite; }
    .flicker { animation: flicker 3s infinite; }
    .pulse { animation: pulse 2s infinite; }
    
    /* Pixel box containers */
    .pixel-box {
        background: var(--bg2);
        border: 2px solid var(--border);
        padding: 16px;
        margin: 8px 0;
        position: relative;
    }
    
    .pixel-box::before {
        content: "";
        position: absolute;
        top: -2px; left: -2px; right: -2px; bottom: -2px;
        border: 1px solid var(--dim);
        pointer-events: none;
    }
    
    .pixel-box-glow {
        background: var(--bg2);
        border: 2px solid var(--dim);
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 0 15px rgba(100,100,100,0.1);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--bg) !important;
        border-right: 2px solid var(--border);
    }
    
    section[data-testid="stSidebar"]::before {
        content: "////////////////";
        display: block;
        color: var(--dim);
        font-size: 0.7rem;
        padding: 8px 16px;
        letter-spacing: 4px;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'VT323', monospace !important;
        color: var(--bright) !important;
        text-transform: uppercase;
        letter-spacing: 3px;
    }
    
    h1 { 
        font-size: 2rem !important; 
        border-bottom: 2px solid var(--border);
        padding-bottom: 12px;
        animation: flicker 4s infinite;
    }
    
    h2 { font-size: 1.5rem !important; color: var(--text) !important; }
    h3 { font-size: 1.2rem !important; color: var(--dim) !important; }
    
    p, span, label, div { color: var(--text) !important; }
    
    /* Buttons - pixel style */
    .stButton > button {
        font-family: 'VT323', monospace !important;
        font-size: 1.1rem !important;
        background: var(--bg2) !important;
        color: var(--text) !important;
        border: 2px solid var(--border) !important;
        border-radius: 0 !important;
        padding: 8px 20px !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        position: relative;
        transition: all 0.05s;
        box-shadow: 4px 4px 0 var(--bg);
    }
    
    .stButton > button::before {
        content: "> ";
        color: var(--dim);
    }
    
    .stButton > button:hover {
        background: var(--bg3) !important;
        color: var(--bright) !important;
        border-color: var(--dim) !important;
        transform: translate(2px, 2px);
        box-shadow: 2px 2px 0 var(--bg);
    }
    
    .stButton > button:active {
        transform: translate(4px, 4px);
        box-shadow: none;
    }
    
    /* Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        font-family: 'VT323', monospace !important;
        font-size: 1.1rem !important;
        background: var(--bg) !important;
        color: var(--bright) !important;
        border: 2px solid var(--border) !important;
        border-radius: 0 !important;
        caret-color: var(--bright);
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--dim) !important;
        box-shadow: 0 0 10px rgba(100,100,100,0.2) !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        background: var(--bg) !important;
    }
    
    /* Chat styling */
    .stChatMessage {
        background: var(--bg2) !important;
        border: 2px solid var(--border) !important;
        border-radius: 0 !important;
        margin: 4px 0;
    }
    
    [data-testid="stChatMessageContent"] {
        background: transparent !important;
    }
    
    .stChatInput > div {
        background: var(--bg) !important;
        border: 2px solid var(--border) !important;
        border-radius: 0 !important;
    }
    
    .stChatInput > div > div > input {
        background: var(--bg) !important;
        color: var(--bright) !important;
    }
    
    /* Metrics */
    div[data-testid="metric-container"] {
        background: var(--bg2) !important;
        border: 2px solid var(--border) !important;
        border-radius: 0 !important;
        padding: 10px !important;
    }
    
    div[data-testid="metric-container"] label {
        font-size: 0.85rem !important;
        color: var(--dim) !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        color: var(--bright) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg2) !important;
        border: 2px solid var(--border) !important;
        border-radius: 0 !important;
        color: var(--text) !important;
    }
    
    .streamlit-expanderContent {
        background: var(--bg) !important;
        border: 2px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 !important;
    }
    
    /* JSON display */
    .stJson {
        background: var(--bg) !important;
        border: 2px solid var(--border) !important;
        font-family: 'VT323', monospace !important;
        border-radius: 0 !important;
    }
    
    /* Status indicator */
    .status-on {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: var(--text);
        margin-right: 8px;
        animation: pulse 1.5s infinite;
    }
    
    .status-off {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: var(--border);
        margin-right: 8px;
    }
    
    /* Provider card */
    .prov-card {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-left: 3px solid var(--dim);
        padding: 6px 12px;
        margin: 3px 0;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
    }
    
    .prov-card.off {
        opacity: 0.4;
        border-left-color: var(--border);
    }
    
    /* Log line */
    .log-line {
        font-size: 0.9rem;
        padding: 3px 6px;
        margin: 2px 0;
        background: var(--bg);
        border-left: 2px solid var(--border);
        color: var(--dim);
    }
    
    .log-line .ts { color: var(--border); margin-right: 8px; }
    .log-line .arrow { color: var(--dim); margin: 0 6px; }
    
    /* Divider */
    hr {
        border: none;
        border-top: 1px dashed var(--border);
        margin: 16px 0;
    }
    
    /* Hide streamlit */
    #MainMenu, footer, header { visibility: hidden; }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border); }
    ::-webkit-scrollbar-thumb:hover { background: var(--dim); }
    
    /* ASCII header decoration */
    .ascii-deco {
        font-size: 0.6rem;
        color: var(--border);
        letter-spacing: 1px;
        line-height: 1.2;
        white-space: pre;
    }
    
    /* Terminal cursor */
    .cursor::after {
        content: "_";
        animation: blink 0.8s infinite;
        color: var(--bright);
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# EMAIL & VALIDATION FUNCTIONS
# =============================================================================

def generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(smtp_config: dict, to_email: str, code: str) -> tuple:
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_config['email']
        msg['To'] = to_email
        msg['Subject'] = 'UAP CONSOLE - VERIFICATION CODE'
        body = f"""
========================================
UAP CONSOLE VERIFICATION
========================================

YOUR CODE: {code}

EXPIRES: 10 MINUTES

IF NOT REQUESTED, IGNORE.
========================================
        """
        msg.attach(MIMEText(body, 'plain'))
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            server.starttls(context=context)
            server.login(smtp_config['email'], smtp_config['password'])
            server.sendmail(smtp_config['email'], to_email, msg.as_string())
        return True, "CODE SENT"
    except smtplib.SMTPAuthenticationError:
        return False, "AUTH FAILED"
    except Exception as e:
        return False, f"ERROR: {str(e)[:40]}"

def hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

def load_user_data() -> dict:
    if USER_DATA_FILE.exists():
        try:
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"users": {}}

def save_user_data(data: dict):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_user_profile(email: str) -> dict:
    data = load_user_data()
    return data["users"].get(hash_email(email), {})

def save_user_profile(email: str, profile: dict):
    data = load_user_data()
    data["users"][hash_email(email)] = profile
    save_user_data(data)

# API Validators
def validate_anthropic(key: str) -> bool:
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
            timeout=10
        )
        return r.status_code in [200, 400, 429]
    except:
        return False

def validate_openai(key: str) -> bool:
    try:
        r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_groq(key: str) -> bool:
    try:
        r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_together(key: str) -> bool:
    try:
        r = requests.get("https://api.together.xyz/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_openrouter(key: str) -> bool:
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_google(key: str) -> bool:
    try:
        r = requests.get(f"https://generativelanguage.googleapis.com/v1/models?key={key}", timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_mistral(key: str) -> bool:
    try:
        r = requests.get("https://api.mistral.ai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_cohere(key: str) -> bool:
    try:
        r = requests.get("https://api.cohere.ai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_hf(key: str) -> bool:
    try:
        r = requests.get("https://huggingface.co/api/whoami", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def check_ollama() -> list:
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except:
        pass
    return []

VALIDATORS = {
    "anthropic": validate_anthropic,
    "openai": validate_openai,
    "groq": validate_groq,
    "together": validate_together,
    "openrouter": validate_openrouter,
    "google": validate_google,
    "mistral": validate_mistral,
    "cohere": validate_cohere,
    "huggingface": validate_hf
}

# =============================================================================
# SESSION STATE
# =============================================================================

def init_state():
    defaults = {
        "step": "login",
        "email": "",
        "smtp": {},
        "code": "",
        "api_keys": {},
        "providers": {},
        "agent_config": {},
        "messages": [],
        "state_mgr": None,
        "dispatcher": None,
        "act": None,
        "session": None,
        "transfers": [],
        "outputs": []
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
# LOGIN PAGE
# =============================================================================

def render_login():
    st.markdown("""
<div style="text-align: center; padding: 20px;">
<pre style="color: #555; font-size: 0.75rem; line-height: 1.3; font-family: 'Courier New', monospace; display: inline-block; text-align: left;">
+-----------------------------------------------+
|                                               |
|   U   U   AAA   PPPP                          |
|   U   U  A   A  P   P                         |
|   U   U  AAAAA  PPPP                          |
|   U   U  A   A  P                             |
|    UUU   A   A  P       CONSOLE               |
|                                               |
|       UNIVERSAL AGENT PROTOCOL v2.0           |
|                                               |
+-----------------------------------------------+
</pre>
</div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="pixel-box-glow">', unsafe_allow_html=True)
        st.markdown("## > SYSTEM LOGIN")
        st.markdown('<span class="cursor"></span>', unsafe_allow_html=True)
        
        email = st.text_input("ENTER EMAIL:", placeholder="user@domain.com", key="login_email")
        
        if email:
            profile = get_user_profile(email)
            if profile.get("verified"):
                st.markdown("`[RETURNING USER DETECTED]`")
        
        st.markdown("")
        
        if st.button("CONTINUE", use_container_width=True, key="login_btn"):
            if email and "@" in email:
                st.session_state.email = email.lower().strip()
                profile = get_user_profile(email)
                if profile.get("verified") and profile.get("api_keys"):
                    st.session_state.api_keys = profile.get("api_keys", {})
                    st.session_state.step = "connect"
                else:
                    st.session_state.step = "smtp"
                st.rerun()
            else:
                st.error("INVALID EMAIL")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("""
```
AUTHENTICATION PROTOCOL:
------------------------
1. EMAIL ENTRY
2. SMTP CONFIG
3. CODE VERIFY
4. PROVIDER CONNECT
```
        """)

# =============================================================================
# SMTP SETUP
# =============================================================================

def render_smtp():
    st.markdown("# > SMTP CONFIG")
    st.markdown(f"`USER: {st.session_state.email}`")
    st.markdown("---")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="pixel-box">', unsafe_allow_html=True)
        
        provider = st.selectbox("PROVIDER:", list(SMTP_PROVIDERS.keys()), 
                               format_func=lambda x: SMTP_PROVIDERS[x]["name"])
        
        pinfo = SMTP_PROVIDERS[provider]
        
        if provider == "custom":
            server = st.text_input("SMTP SERVER:", placeholder="smtp.example.com")
            port = st.number_input("PORT:", value=587)
        else:
            server = pinfo["server"]
            port = pinfo["port"]
            st.markdown(f"`SERVER: {server}:{port}`")
        
        st.markdown("---")
        smtp_email = st.text_input("SENDER EMAIL:", value=st.session_state.email)
        smtp_pass = st.text_input("APP PASSWORD:", type="password")
        
        st.markdown("")
        
        if st.button("SEND CODE", use_container_width=True):
            if smtp_email and smtp_pass:
                cfg = {"server": server, "port": port, "email": smtp_email, "password": smtp_pass}
                code = generate_code()
                
                with st.spinner("TRANSMITTING..."):
                    ok, msg = send_verification_email(cfg, st.session_state.email, code)
                
                if ok:
                    st.session_state.smtp = cfg
                    st.session_state.code = code
                    st.session_state.step = "verify"
                    st.rerun()
                else:
                    st.error(msg)
        
        if st.button("BACK", use_container_width=True):
            st.session_state.step = "login"
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("GMAIL SETUP"):
            st.markdown("""
```
1. ENABLE 2FA
2. SECURITY > APP PASSWORDS
3. CREATE NEW PASSWORD
4. USE 16-CHAR CODE
```
            """)

# =============================================================================
# VERIFY
# =============================================================================

def render_verify():
    st.markdown("# > VERIFY CODE")
    st.markdown(f"`TARGET: {st.session_state.email}`")
    st.markdown("---")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="pixel-box-glow">', unsafe_allow_html=True)
        st.markdown("### ENTER 6-DIGIT CODE")
        
        code = st.text_input("CODE:", max_chars=6, placeholder="000000")
        
        if st.button("VERIFY", use_container_width=True):
            if code == st.session_state.code:
                profile = get_user_profile(st.session_state.email)
                profile["verified"] = True
                profile["verified_at"] = datetime.now().isoformat()
                save_user_profile(st.session_state.email, profile)
                st.session_state.step = "connect"
                st.rerun()
            else:
                st.error("INVALID CODE")
        
        c_a, c_b = st.columns(2)
        with c_a:
            if st.button("RESEND", use_container_width=True):
                code = generate_code()
                ok, _ = send_verification_email(st.session_state.smtp, st.session_state.email, code)
                if ok:
                    st.session_state.code = code
                    st.success("SENT")
        with c_b:
            if st.button("BACK", use_container_width=True, key="v_back"):
                st.session_state.step = "smtp"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# CONNECT PROVIDERS
# =============================================================================

def render_connect():
    st.markdown("# > CONNECT PROVIDERS")
    st.markdown(f"`USER: {st.session_state.email} [VERIFIED]`")
    st.markdown("---")
    
    st.markdown("### ENTER API KEYS")
    st.markdown("`ADD KEYS FOR PROVIDERS YOU HAVE ACCOUNTS WITH`")
    st.markdown("")
    
    c1, c2 = st.columns(2)
    keys = {}
    
    with c1:
        st.markdown("#### PREMIUM")
        
        st.markdown("**ANTHROPIC** - Claude")
        keys["anthropic"] = st.text_input("KEY:", value=st.session_state.api_keys.get("anthropic", os.environ.get("ANTHROPIC_API_KEY", "")), type="password", key="k_anth")
        st.caption("[console.anthropic.com](https://console.anthropic.com)")
        
        st.markdown("**OPENAI** - GPT")
        keys["openai"] = st.text_input("KEY:", value=st.session_state.api_keys.get("openai", os.environ.get("OPENAI_API_KEY", "")), type="password", key="k_oai")
        st.caption("[platform.openai.com](https://platform.openai.com/api-keys)")
        
        st.markdown("**GOOGLE** - Gemini")
        keys["google"] = st.text_input("KEY:", value=st.session_state.api_keys.get("google", os.environ.get("GOOGLE_API_KEY", "")), type="password", key="k_goog")
        st.caption("[makersuite.google.com](https://makersuite.google.com)")
        
        st.markdown("**MISTRAL**")
        keys["mistral"] = st.text_input("KEY:", value=st.session_state.api_keys.get("mistral", os.environ.get("MISTRAL_API_KEY", "")), type="password", key="k_mist")
        
        st.markdown("**COHERE**")
        keys["cohere"] = st.text_input("KEY:", value=st.session_state.api_keys.get("cohere", os.environ.get("COHERE_API_KEY", "")), type="password", key="k_coh")
    
    with c2:
        st.markdown("#### FREE / OPEN")
        
        st.markdown("**GROQ** - Fast LLaMA")
        keys["groq"] = st.text_input("KEY:", value=st.session_state.api_keys.get("groq", os.environ.get("GROQ_API_KEY", "")), type="password", key="k_groq")
        st.caption("[console.groq.com](https://console.groq.com)")
        
        st.markdown("**TOGETHER AI**")
        keys["together"] = st.text_input("KEY:", value=st.session_state.api_keys.get("together", os.environ.get("TOGETHER_API_KEY", "")), type="password", key="k_tog")
        
        st.markdown("**OPENROUTER** - Free Tier")
        keys["openrouter"] = st.text_input("KEY:", value=st.session_state.api_keys.get("openrouter", os.environ.get("OPENROUTER_API_KEY", "")), type="password", key="k_or")
        
        st.markdown("**HUGGINGFACE**")
        keys["huggingface"] = st.text_input("KEY:", value=st.session_state.api_keys.get("huggingface", os.environ.get("HF_API_KEY", "")), type="password", key="k_hf")
        
        st.markdown("**OLLAMA** - Local")
        ollama_models = check_ollama()
        if ollama_models:
            st.success(f"ONLINE: {len(ollama_models)} MODELS")
        else:
            st.warning("OFFLINE - [ollama.ai](https://ollama.ai)")
    
    st.markdown("---")
    
    if st.button("CONNECT AND LAUNCH", use_container_width=True):
        st.session_state.api_keys = {k: v for k, v in keys.items() if v}
        
        connected = {}
        prg = st.progress(0, "VALIDATING...")
        
        providers_to_check = list(st.session_state.api_keys.items())
        total = len(providers_to_check) + 1
        
        for i, (pid, key) in enumerate(providers_to_check):
            prg.progress((i + 1) / total, f"CHECKING {pid.upper()}...")
            if pid in VALIDATORS and VALIDATORS[pid](key):
                connected[pid] = {"name": PROVIDERS[pid]["name"], "models": PROVIDERS[pid]["models"], "key": key}
        
        prg.progress(1.0, "CHECKING OLLAMA...")
        if ollama_models:
            connected["ollama"] = {"name": "OLLAMA", "models": ollama_models, "key": None}
        
        prg.empty()
        
        if connected:
            profile = get_user_profile(st.session_state.email)
            profile["api_keys"] = st.session_state.api_keys
            save_user_profile(st.session_state.email, profile)
            
            st.session_state.providers = connected
            st.session_state.step = "main"
            st.rerun()
        else:
            st.error("NO VALID PROVIDERS FOUND")

# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    with st.sidebar:
        st.markdown("## UAP CONSOLE")
        st.markdown(f"`{st.session_state.email[:20]}`")
        st.markdown("---")
        
        st.markdown("### ONLINE")
        for pid, pinfo in st.session_state.providers.items():
            st.markdown(f"""
            <div class="prov-card">
                <span class="status-on"></span>
                <span>{pinfo['name']}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### AGENT > MODEL")
        
        options = []
        for pid, pinfo in st.session_state.providers.items():
            for model in pinfo["models"][:4]:
                options.append({"id": f"{pid}|{model}", "label": f"{pinfo['name'][:6]}/{model[:18]}", "provider": pid, "model": model})
        
        if options:
            for atype, ainfo in AGENT_TYPES.items():
                curr = st.session_state.agent_config.get(atype, {})
                curr_id = f"{curr.get('provider', '')}|{curr.get('model', '')}"
                ids = [o["id"] for o in options]
                idx = ids.index(curr_id) if curr_id in ids else 0
                
                sel = st.selectbox(ainfo["name"], ids, format_func=lambda x: next((o["label"] for o in options if o["id"] == x), x[:25]), index=idx, key=f"sel_{atype}")
                if sel:
                    p, m = sel.split("|", 1)
                    st.session_state.agent_config[atype] = {"provider": p, "model": m}
        
        st.markdown("---")
        st.markdown("### SESSION")
        if st.session_state.session:
            st.code(st.session_state.session[:16], language=None)
        else:
            st.markdown("`NONE`")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("NEW", use_container_width=True, key="s_new"):
                st.session_state.session = None
                st.session_state.act = None
                st.session_state.transfers = []
                st.rerun()
        with c2:
            if st.button("RST", use_container_width=True, key="s_rst"):
                st.session_state.messages = []
                st.session_state.session = None
                st.session_state.act = None
                st.session_state.transfers = []
                st.rerun()
        
        st.markdown("---")
        if st.button("LOGOUT", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# =============================================================================
# HELPERS
# =============================================================================

def reg_agent(atype: str, provider: str, model: str) -> str:
    aid = f"{atype}_{provider}"
    cfg = AgentConfig(agent_id=aid, agent_type=atype, system_prompt=AGENT_TYPES[atype]["prompt"], model=model, backend=provider)
    try:
        st.session_state.dispatcher.register_agent(cfg)
    except:
        pass
    return aid

def log_xfer(frm: str, to: str, msg: str):
    st.session_state.transfers.append({
        "t": datetime.now().strftime("%H:%M:%S"),
        "from": frm,
        "to": to,
        "msg": msg[:25]
    })

def save_out(content: str, otype: str) -> str:
    d = UAP_ROOT / "local_outputs"
    d.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = d / f"{otype}_{ts}.txt"
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    st.session_state.outputs.append({"t": ts, "type": otype, "path": str(fp), "prev": content[:40]})
    return str(fp)

# =============================================================================
# MAIN DASHBOARD
# =============================================================================

def render_main():
    st.markdown("# UAP CONSOLE")
    st.markdown('<span class="flicker">`SYSTEM READY`</span> <span class="blink">_</span>', unsafe_allow_html=True)
    st.markdown("---")
    
    chat_col, state_col = st.columns([3, 2])
    
    with chat_col:
        st.markdown("## > TERMINAL")
        
        atype = st.selectbox("ROUTE:", list(AGENT_TYPES.keys()), format_func=lambda x: AGENT_TYPES[x]["name"], key="main_agent")
        cfg = st.session_state.agent_config.get(atype, {})
        
        if cfg:
            pinfo = st.session_state.providers.get(cfg.get("provider"), {})
            st.markdown(f'`> {pinfo.get("name", "?")} / {cfg.get("model", "?")[:30]}`')
        
        chat_container = st.container(height=350)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if m.get("agent"):
                        st.caption(f"[{m['agent']}]")
        
        if prompt := st.chat_input(">_", key="chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            if not cfg:
                st.session_state.messages.append({"role": "assistant", "content": "ERROR: SELECT MODEL", "agent": "SYSTEM"})
            else:
                pid, mdl = cfg["provider"], cfg["model"]
                aid = reg_agent(atype, pid, mdl)
                log_xfer("USER", f"{atype.upper()}", prompt[:20])
                
                try:
                    pinfo = st.session_state.providers.get(pid, {})
                    key = pinfo.get("key")
                    if key:
                        env_map = {
                            "groq": "GROQ_API_KEY", "together": "TOGETHER_API_KEY",
                            "openrouter": "OPENROUTER_API_KEY", "huggingface": "HF_API_KEY",
                            "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
                            "google": "GOOGLE_API_KEY", "mistral": "MISTRAL_API_KEY",
                            "cohere": "COHERE_API_KEY"
                        }
                        if pid in env_map:
                            os.environ[env_map[pid]] = key
                    
                    result = st.session_state.dispatcher.dispatch(
                        agent_id=aid,
                        session_id=st.session_state.session,
                        task=prompt,
                        auto_handoff=False
                    )
                    st.session_state.session = result["session_id"]
                    st.session_state.act = st.session_state.state_mgr.get_session(result["session_id"])
                    
                    resp = result.get("response", "NO RESPONSE")
                    agent_label = f"{AGENT_TYPES[atype]['name']}/{pinfo.get('name', pid)}"
                    st.session_state.messages.append({"role": "assistant", "content": resp, "agent": agent_label})
                    log_xfer(atype.upper(), "USER", "RESP")
                    
                except Exception as e:
                    st.session_state.messages.append({"role": "assistant", "content": f"ERROR: {e}", "agent": "SYSTEM"})
            
            st.rerun()
    
    with state_col:
        st.markdown("## > STATE PACKET")
        
        if st.session_state.act:
            act = st.session_state.act.to_dict()
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("TASKS", len(act.get("task_chain", [])))
            with c2:
                st.metric("XFERS", len(st.session_state.transfers))
            
            with st.expander("OBJECTIVE", expanded=True):
                obj = act.get("current_objective", "NONE")
                st.text(obj[:80] if obj else "NONE")
            
            st.markdown("#### TRANSFER LOG")
            log_box = st.container(height=100)
            with log_box:
                for e in st.session_state.transfers[-6:]:
                    st.markdown(f'<div class="log-line"><span class="ts">[{e["t"]}]</span>{e["from"]}<span class="arrow">-></span>{e["to"]}</div>', unsafe_allow_html=True)
            
            with st.expander("RAW ACT"):
                st.json(act)
        else:
            st.markdown("`NO STATE`")
        
        st.markdown("---")
        st.markdown("#### OUTPUT")
        
        if st.session_state.messages:
            if st.button("SAVE CHAT", use_container_width=True, key="save_chat"):
                txt = "\n\n".join([f"[{m['role'].upper()}] {m['content']}" for m in st.session_state.messages])
                p = save_out(txt, "chat")
                st.success(f"SAVED")
        
        if st.session_state.act:
            if st.button("SAVE STATE", use_container_width=True, key="save_state"):
                p = save_out(json.dumps(st.session_state.act.to_dict(), indent=2), "state")
                st.success("SAVED")
        
        if st.session_state.outputs:
            st.markdown("**RECENT:**")
            for o in reversed(st.session_state.outputs[-3:]):
                with st.expander(f"{o['type']}_{o['t'][:8]}"):
                    st.text(o['prev'][:50])

# =============================================================================
# MAIN
# =============================================================================

def main():
    init_state()
    step = st.session_state.step
    
    if step == "login":
        render_login()
    elif step == "smtp":
        render_smtp()
    elif step == "verify":
        render_verify()
    elif step == "connect":
        render_connect()
    elif step == "main":
        render_sidebar()
        render_main()

if __name__ == "__main__":
    main()
