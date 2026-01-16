"""
UAP Protocol Dashboard - Gmail-Federated Agent Linking
Link Claude, GPT, Mistral etc. to your Gmail identity via email verification.
All agents share the same ACT context space.
"""

import streamlit as st
import sys
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Add UAP module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from uap.oauth import UAPOAuth
from uap.vault import get_linked_agents, store_credential, unlink_agent, get_credential
from uap.dispatcher import Dispatcher, AgentConfig
from uap.protocol import StateManager

# Page config
st.set_page_config(
    page_title="UAP Protocol",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #e0e0e0; }
    h1, h2, h3 { color: #ffffff !important; font-family: 'Consolas', monospace !important; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    
    .uap-card { background: #151515; border: 1px solid #333; border-radius: 4px; padding: 16px; margin: 8px 0; }
    .uap-card-header { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; font-family: 'Consolas', monospace; }
    
    /* Agent linking cards */
    .agent-link-card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 4px; padding: 16px; margin: 8px 0; font-family: 'Consolas', monospace; }
    .agent-link-card.linked { border-left: 3px solid #8f8; }
    .agent-link-card.unlinked { border-left: 3px solid #444; }
    .agent-name { color: #ddd; font-size: 16px; font-weight: bold; }
    .agent-provider { color: #666; font-size: 11px; }
    .agent-status { font-size: 11px; margin-top: 8px; padding: 4px 8px; border-radius: 3px; display: inline-block; }
    .agent-status.linked { background: #1a2a1a; color: #8f8; border: 1px solid #3a5a3a; }
    .agent-status.unlinked { background: #2a1a1a; color: #f88; border: 1px solid #5a3a3a; }
    .agent-status.oauth { background: #1a1a2a; color: #88f; border: 1px solid #3a3a5a; }
    
    /* Handshake flow */
    .handshake-flow { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 8px; padding: 16px; background: #0d0d0d; border-radius: 4px; }
    .flow-node { background: #1a1a1a; border: 1px solid #333; border-radius: 4px; padding: 10px 20px; font-family: 'Consolas', monospace; font-size: 12px; color: #888; }
    .flow-node.active { border-color: #8f8; color: #8f8; background: #1a2a1a; }
    .flow-node.done { border-color: #555; color: #777; }
    .flow-arrow { color: #444; font-size: 18px; }
    
    /* Shared context */
    .context-box { background: #0a0a0a; border: 2px dashed #2a2a2a; border-radius: 8px; padding: 20px; margin: 12px 0; }
    .context-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; }
    .context-value { color: #aaa; font-family: 'Consolas', monospace; font-size: 12px; }
    
    /* Activity log */
    .activity-log { background: #0d0d0d; border: 1px solid #222; border-radius: 4px; padding: 12px; font-family: 'Consolas', monospace; font-size: 11px; max-height: 300px; overflow-y: auto; }
    .log-entry { padding: 6px 0; border-bottom: 1px solid #1a1a1a; }
    .log-entry.handshake { background: #0a150a; margin: 2px -12px; padding: 6px 12px; }
    
    /* Output panel */
    .output-panel { background: #0d0d0d; border: 1px solid #222; border-radius: 4px; padding: 16px; max-height: 400px; overflow-y: auto; }
    .output-section { margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #1a1a1a; }
    .output-agent { color: #8f8; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .output-text { color: #ccc; font-size: 13px; line-height: 1.6; white-space: pre-wrap; font-family: 'Consolas', monospace; }
    
    /* Buttons & inputs */
    .stButton > button { background: #222 !important; border: 1px solid #444 !important; color: #ccc !important; font-family: 'Consolas', monospace !important; }
    .stButton > button:hover { background: #333 !important; border-color: #555 !important; }
    .stTextArea > div > div > textarea, .stTextInput > div > div > input { background: #151515 !important; border: 1px solid #333 !important; color: #ddd !important; font-family: 'Consolas', monospace !important; }
    
    .user-email { background: #1a1a1a; border: 1px solid #333; border-radius: 3px; padding: 8px 12px; font-family: 'Consolas', monospace; font-size: 12px; color: #aaa; }
    
    /* Link modal */
    .link-instructions { background: #151515; border: 1px solid #333; border-radius: 4px; padding: 16px; margin: 12px 0; }
    .link-instructions ol { color: #888; margin-left: 20px; }
    .link-instructions li { margin: 8px 0; }
    .link-instructions a { color: #88f; }
    
    #MainMenu, footer, header { visibility: hidden; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #111; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# Initialize OAuth
oauth = UAPOAuth()

# Agent definitions with API key URLs
AGENT_INFO = {
    "gemini": {
        "name": "Gemini",
        "provider": "Google",
        "model": "gemini-1.5-flash",
        "key_url": None,  # OAuth-based, no key needed
        "description": "Connected via your Google account (OAuth)"
    },
    "openai": {
        "name": "GPT-4",
        "provider": "OpenAI",
        "model": "gpt-4-turbo",
        "key_url": "https://platform.openai.com/api-keys",
        "description": "Create an API key at OpenAI platform"
    },
    "anthropic": {
        "name": "Claude",
        "provider": "Anthropic",
        "model": "claude-3-sonnet-20240229",
        "key_url": "https://console.anthropic.com/settings/keys",
        "description": "Create an API key at Anthropic console"
    },
    "mistral": {
        "name": "Mistral",
        "provider": "Mistral AI",
        "model": "mistral-large-latest",
        "key_url": "https://console.mistral.ai/api-keys/",
        "description": "Create an API key at Mistral console"
    },
    "groq": {
        "name": "Groq",
        "provider": "Groq",
        "model": "llama-3.1-70b-versatile",
        "key_url": "https://console.groq.com/keys",
        "description": "Create an API key at Groq console"
    }
}

# Session state
for key in ["activity_log", "handshake_chain", "outputs", "shared_context"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key != "shared_context" else {}
for key in ["active_agent", "processing", "auto_handoff", "linking_agent", "show_link_modal"]:
    if key not in st.session_state:
        st.session_state[key] = True if key == "auto_handoff" else (False if key in ["processing", "show_link_modal"] else None)


def log(agent: str, msg: str, is_handshake: bool = False):
    st.session_state.activity_log.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "msg": msg,
        "handshake": is_handshake
    })
    st.session_state.activity_log = st.session_state.activity_log[:100]


def generate_act_id() -> str:
    return hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:12]


def render_login():
    st.markdown("""
    <div style="text-align: center; padding: 80px 20px;">
        <h1 style="font-size: 56px; margin-bottom: 8px; letter-spacing: 4px;">UAP</h1>
        <p style="color: #555; font-size: 12px; letter-spacing: 3px;">UNIFIED AGENT PROTOCOL</p>
        <p style="color: #444; font-size: 11px; margin-top: 30px;">Gmail-Federated Multi-Agent System</p>
        <div style="margin: 50px 0; color: #333;">───────────────────</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Sign in with Google", use_container_width=True):
            try:
                creds = oauth.authenticate()
                if creds:
                    st.session_state.credentials = creds
                    st.session_state.user_info = oauth.get_user_info(creds)
                    log("system", "Identity verified")
                    st.rerun()
            except Exception as e:
                st.error(f"Auth failed: {e}")


def render_link_agent_modal(agent_id: str, email: str):
    """Render the agent linking modal"""
    agent = AGENT_INFO[agent_id]
    
    st.markdown(f"### Link {agent['name']} to your UAP")
    
    if agent_id == "gemini":
        st.success("Gemini is automatically linked via your Google OAuth!")
        if st.button("Close"):
            st.session_state.show_link_modal = False
            st.session_state.linking_agent = None
            st.rerun()
        return
    
    st.markdown(f"""
    <div class="link-instructions">
        <p style="color: #aaa; margin-bottom: 12px;">To link {agent['name']}, you need an API key from {agent['provider']}:</p>
        <ol>
            <li>Go to <a href="{agent['key_url']}" target="_blank">{agent['key_url']}</a></li>
            <li>Create a new API key (or use an existing one)</li>
            <li>Copy the key and paste it below</li>
            <li>The key will be encrypted and stored locally, linked to <strong>{email}</strong></li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    api_key = st.text_input(
        f"{agent['name']} API Key",
        type="password",
        placeholder=f"Enter your {agent['provider']} API key...",
        key=f"link_key_{agent_id}"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Link Agent", use_container_width=True, disabled=not api_key):
            if api_key:
                success = store_credential(email, agent_id, api_key, {
                    "linked_via": "manual_entry",
                    "user_email": email
                })
                if success:
                    log("system", f"{agent['name']} linked to {email}")
                    st.success(f"{agent['name']} linked successfully!")
                    st.session_state.show_link_modal = False
                    st.session_state.linking_agent = None
                    st.rerun()
                else:
                    st.error("Failed to store credential")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_link_modal = False
            st.session_state.linking_agent = None
            st.rerun()


def render_sidebar(email: str):
    with st.sidebar:
        st.markdown(f'<div class="user-email">{email}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Handoff settings
        st.markdown('<div class="uap-card"><div class="uap-card-header">Handoff Mode</div></div>', unsafe_allow_html=True)
        st.session_state.auto_handoff = st.checkbox("Auto-Handoff", value=st.session_state.auto_handoff)
        if st.session_state.auto_handoff:
            st.session_state.max_handoffs = st.slider("Max Steps", 2, 6, 3)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Linked agents section
        st.markdown('<div class="uap-card"><div class="uap-card-header">Linked Agents</div></div>', unsafe_allow_html=True)
        
        linked_agents = get_linked_agents(email)
        
        for agent_id, status in linked_agents.items():
            agent_info = AGENT_INFO.get(agent_id, {})
            is_linked = status.get("linked", False)
            is_oauth = status.get("oauth_based", False)
            is_active = st.session_state.active_agent == agent_id
            
            card_class = "linked" if is_linked else "unlinked"
            if is_active:
                card_class = "linked"
            
            if is_oauth and is_linked:
                status_class = "oauth"
                status_text = "OAUTH"
            elif is_linked:
                status_class = "linked"
                status_text = "LINKED"
            else:
                status_class = "unlinked"
                status_text = "NOT LINKED"
            
            st.markdown(f"""
            <div class="agent-link-card {card_class}">
                <div class="agent-name">{status.get('name', agent_id)}</div>
                <div class="agent-provider">{status.get('provider', 'Unknown')}</div>
                <div class="agent-status {status_class}">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Link/Unlink buttons
            if not is_linked and not is_oauth:
                if st.button(f"Link {status.get('name', agent_id)}", key=f"link_{agent_id}", use_container_width=True):
                    st.session_state.linking_agent = agent_id
                    st.session_state.show_link_modal = True
                    st.rerun()
            elif is_linked and not is_oauth:
                if st.button(f"Unlink", key=f"unlink_{agent_id}", use_container_width=True):
                    unlink_agent(email, agent_id)
                    log("system", f"{status.get('name', agent_id)} unlinked")
                    st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Sign Out", use_container_width=True):
            oauth.logout()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


def render_handshake_flow(email: str):
    st.markdown('<div class="uap-card"><div class="uap-card-header">Agent Handshake Flow</div></div>', unsafe_allow_html=True)
    
    if st.session_state.handshake_chain:
        linked = get_linked_agents(email)
        html = '<div class="handshake-flow">'
        for i, node in enumerate(st.session_state.handshake_chain):
            aid = node["agent"]
            status = node["status"]
            name = linked.get(aid, {}).get("name", aid)
            
            cls = "active" if status == "active" else "done"
            html += f'<div class="flow-node {cls}">{name}</div>'
            
            if i < len(st.session_state.handshake_chain) - 1:
                html += '<span class="flow-arrow">→</span>'
        
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="handshake-flow" style="color: #444;">No handshakes yet - execute a task</div>', unsafe_allow_html=True)


def render_shared_context():
    st.markdown('<div class="uap-card"><div class="uap-card-header">Shared Context (ACT)</div></div>', unsafe_allow_html=True)
    
    ctx = st.session_state.shared_context
    
    if ctx:
        st.markdown(f"""
        <div class="context-box">
            <div class="context-label">ACT ID</div>
            <div class="context-value">{ctx.get('id', 'N/A')}</div>
            <br>
            <div class="context-label">Task</div>
            <div class="context-value">{ctx.get('task', 'None')[:100]}...</div>
            <br>
            <div class="context-label">Agents in Chain</div>
            <div class="context-value">{' → '.join(ctx.get('agents_chain', [])) or 'None'}</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Full Context Data"):
            st.json(ctx)
    else:
        st.markdown('<div class="context-box" style="text-align: center; color: #444;">Context space empty</div>', unsafe_allow_html=True)


def render_activity_log():
    st.markdown('<div class="uap-card"><div class="uap-card-header">Activity Log</div></div>', unsafe_allow_html=True)
    
    html = '<div class="activity-log">'
    for e in st.session_state.activity_log[:30]:
        entry_class = "handshake" if e.get("handshake") else ""
        html += f'<div class="log-entry {entry_class}"><span style="color:#444">{e["time"]}</span> <span style="color:#888">[{e["agent"]}]</span> <span style="color:#666">{e["msg"]}</span></div>'
    if not st.session_state.activity_log:
        html += '<div style="color:#444;padding:20px;text-align:center">No activity</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_outputs(email: str):
    st.markdown('<div class="uap-card"><div class="uap-card-header">Agent Outputs</div></div>', unsafe_allow_html=True)
    
    if st.session_state.outputs:
        linked = get_linked_agents(email)
        import html as h
        html = '<div class="output-panel">'
        for o in st.session_state.outputs:
            name = linked.get(o['agent'], {}).get('name', o['agent'])
            safe_text = h.escape(o['text'])
            html += f'<div class="output-section"><div class="output-agent">{name}</div><div class="output-text">{safe_text}</div></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="output-panel" style="text-align:center;color:#444;padding:40px">Awaiting outputs</div>', unsafe_allow_html=True)


def call_real_agent(agent_id: str, email: str, task: str, context: str, credentials) -> str:
    """Call a real agent via its API"""
    agent_info = AGENT_INFO.get(agent_id, {})
    linked = get_linked_agents(email)
    
    if not linked.get(agent_id, {}).get("linked"):
        return f"ERROR: {agent_info.get('name', agent_id)} is not linked. Please link it first."
    
    # Build prompt with context
    other_agents = [AGENT_INFO[a]["name"] for a in linked if linked[a]["linked"] and a != agent_id]
    
    prompt = f"""You are {agent_info['name']} working in a multi-agent UAP (Unified Agent Protocol) system.

SHARED CONTEXT with other agents: {', '.join(other_agents) if other_agents else 'None'}

TASK: {task}

CONTEXT FROM PREVIOUS AGENTS:
{context if context else '(You are the first agent in the chain)'}

Instructions:
1. Provide your contribution to the task
2. If another agent's expertise would help, say: HANDOFF TO: [agent name]
3. Available agents for handoff: {', '.join(other_agents)}

Your response:"""
    
    try:
        # Get OAuth creds for Gemini
        oauth_creds = None
        if agent_id == "gemini" and credentials:
            oauth_creds = credentials
        
        # Create dispatcher
        dispatcher = Dispatcher(oauth_credentials=oauth_creds)
        
        # Direct backend call
        if agent_id == "gemini":
            return dispatcher._call_gemini(prompt, agent_info["model"])
        elif agent_id == "openai":
            return dispatcher._call_openai(prompt, agent_info["model"], email)
        elif agent_id == "anthropic":
            return dispatcher._call_anthropic(prompt, agent_info["model"], email)
        elif agent_id == "mistral":
            return dispatcher._call_mistral(prompt, agent_info["model"], email)
        elif agent_id == "groq":
            return dispatcher._call_groq(prompt, agent_info["model"])
        else:
            return f"ERROR: Unknown agent backend: {agent_id}"
            
    except Exception as e:
        return f"ERROR calling {agent_info.get('name', agent_id)}: {str(e)}"


def determine_handoff(response: str, current: str, linked_agents: dict) -> str:
    """Check if agent suggests handoff"""
    text = response.upper()
    
    if "HANDOFF TO:" in text:
        for aid, status in linked_agents.items():
            if status.get("linked") and aid != current:
                name = status.get("name", aid).upper()
                if name in text:
                    return aid
    return None


def process_task(task: str, start_agent: str, email: str, credentials):
    """Process task through real agents with shared context"""
    st.session_state.processing = True
    st.session_state.handshake_chain = []
    st.session_state.outputs = []
    
    # Initialize shared context
    act_id = generate_act_id()
    st.session_state.shared_context = {
        "id": act_id,
        "task": task,
        "accumulated_context": "",
        "agents_chain": [],
        "owner": email,
        "created_at": datetime.now().isoformat()
    }
    
    log("system", f"Created ACT:{act_id[:8]}")
    
    linked = get_linked_agents(email)
    current = start_agent
    max_handoffs = st.session_state.get('max_handoffs', 3)
    
    for _ in range(max_handoffs):
        if not linked.get(current, {}).get("linked"):
            log("system", f"{current} not linked - stopping")
            break
        
        # Add to chain
        st.session_state.handshake_chain.append({"agent": current, "status": "active"})
        st.session_state.active_agent = current
        st.session_state.shared_context["agents_chain"].append(current)
        
        agent_name = linked.get(current, {}).get("name", current)
        log(agent_name, "Processing...")
        
        # Call real agent
        context = st.session_state.shared_context["accumulated_context"]
        response = call_real_agent(current, email, task, context, credentials)
        
        # Update chain
        st.session_state.handshake_chain[-1]["status"] = "done"
        
        # Store output
        st.session_state.outputs.append({"agent": current, "text": response})
        
        # Update shared context
        st.session_state.shared_context["accumulated_context"] += f"\n\n[{agent_name}]:\n{response}"
        
        log(agent_name, "Done")
        
        # Check for handoff
        if st.session_state.auto_handoff:
            next_agent = determine_handoff(response, current, linked)
            if next_agent:
                next_name = linked.get(next_agent, {}).get("name", next_agent)
                log(agent_name, f"Handoff → {next_name}", True)
                current = next_agent
                continue
        
        break
    
    log("system", f"Complete - {len(st.session_state.handshake_chain)} agents")
    st.session_state.processing = False
    st.session_state.active_agent = None


def render_main(email: str, credentials):
    # Check for link modal
    if st.session_state.show_link_modal and st.session_state.linking_agent:
        render_link_agent_modal(st.session_state.linking_agent, email)
        return
    
    render_sidebar(email)
    
    st.markdown("""
    <h1 style="margin-bottom: 4px;">UAP Protocol</h1>
    <p style="color: #555; font-size: 11px; letter-spacing: 2px; margin-bottom: 20px;">
        GMAIL-FEDERATED MULTI-AGENT SYSTEM
    </p>
    """, unsafe_allow_html=True)
    
    # Handshake flow
    render_handshake_flow(email)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Task input
    linked = get_linked_agents(email)
    available_agents = [aid for aid, status in linked.items() if status.get("linked")]
    
    if not available_agents:
        st.warning("No agents linked. Please link at least one agent from the sidebar.")
        return
    
    col1, col2 = st.columns([3, 1])
    with col1:
        task = st.text_area("Task", placeholder="Enter task for agents...", height=80, label_visibility="collapsed")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        start = st.selectbox(
            "Start Agent",
            available_agents,
            format_func=lambda x: linked[x].get("name", x),
            label_visibility="collapsed"
        )
        if st.button("Execute", use_container_width=True, disabled=st.session_state.processing):
            if task.strip():
                process_task(task.strip(), start, email, credentials)
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Main panels
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        render_outputs(email)
        st.markdown("<br>", unsafe_allow_html=True)
        render_activity_log()
    
    with col_right:
        render_shared_context()


def main():
    if not oauth.is_authenticated():
        render_login()
    else:
        if 'credentials' not in st.session_state:
            creds = oauth.load_credentials()
            if creds:
                st.session_state.credentials = creds
                st.session_state.user_info = oauth.get_user_info(creds)
        
        email = st.session_state.get('user_info', {}).get('email', 'unknown@example.com')
        credentials = st.session_state.get('credentials')
        
        render_main(email, credentials)


if __name__ == "__main__":
    main()
