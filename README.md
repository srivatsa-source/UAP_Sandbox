# UAP — Universal Agent Protocol

[![PyPI](https://img.shields.io/pypi/v/uap-protocol)](https://pypi.org/project/uap-protocol/)
[![Python](https://img.shields.io/pypi/pyversions/uap-protocol)](https://pypi.org/project/uap-protocol/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**The open standard for AI-agent interoperability.**

UAP standardises LLM-to-LLM data transfer through a persistent **Agent Context Token (ACT)** so agents can hand off work without losing context or re-prompting users. Think of it as *Segment for AI Agents*.

---

## Features

| Capability | Details |
|---|---|
| **11 LLM backends** | Groq, Gemini, OpenAI, Anthropic, Mistral, Together, OpenRouter, Ollama, LM Studio, llama.cpp, vLLM |
| **Local model management** | Auto-discover & monitor Ollama, LM Studio, llama.cpp, vLLM with one command |
| **ACT state protocol** | Portable JSON state packet that travels between agents |
| **Agent handoff & chaining** | Automatic multi-agent pipelines with full history |
| **Segment-style telemetry** | JSONL event logging with per-agent analytics |
| **Handoff visualiser** | Graphviz DAG, Plotly timeline, ASCII trace |
| **Fernet vault** | Encrypted secret storage for API keys |
| **MCP server** | 8 tools exposed over Model Context Protocol (stdio) |
| **Streamlit dashboard** | Chat, analytics, session management in a web UI |
| **OAuth identity** | Google OAuth for user identity & Gemini auth |

---

## Installation

```bash
# Core install
pip install uap-protocol

# With web dashboard
pip install uap-protocol[dashboard]

# Everything (all optional backends + MCP)
pip install uap-protocol[all]
```

### From source

```bash
git clone https://github.com/srivatsa-source/UAP_Sandbox.git
cd UAP_Sandbox/uap-protocol
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# 1. First-time setup — choose backend, enter API key
uap-run --setup

# 2. Create a task & let agents collaborate
uap new "Build a REST API with auth" --agents planner,coder,reviewer --auto

# 3. Launch the web dashboard
uap-run dashboard
```

---

## How It Works

```
 You ──▶ Task
          │
          ▼
   ┌────────────┐      ┌──────────────────────┐      ┌────────────┐
   │  Planner   │─────▶│   ACT (State Packet)  │─────▶│   Coder    │
   │            │      │                        │      │            │
   │ Breaks down│      │ • objective            │      │ Implements │
   │ the task   │      │ • context_summary      │      │ the code   │
   └────────────┘      │ • task_chain           │      └────────────┘
                       │ • artifacts            │            │
                       │ • handoff_reason       │            ▼
   ┌────────────┐      │ • next_agent_hint      │      ┌────────────┐
   │  Complete  │◀─────│                        │◀─────│  Reviewer  │
   └────────────┘      └──────────────────────┘      └────────────┘
```

1. **Submit a task** → UAP creates an ACT  
2. **Agent A processes** → updates the ACT with context, decisions, artifacts  
3. **Handoff** → Agent B reads the ACT and continues seamlessly  
4. **Chain continues** → each agent enriches the shared state  
5. **Done** → full history preserved in the ACT  

---

## CLI Reference

UAP exposes three entry points:

| Command | Purpose |
|---|---|
| `uap` | Primary Typer CLI — session, agent, config, auth, local model commands |
| `uap-run` | Interactive launcher — menu-driven setup, dashboard, chat |
| `uap-dashboard` | Streamlit web dashboard |

### Sessions

```bash
uap new "Your task" --agents planner,coder,reviewer       # Start session
uap new "Build a login page" --agents planner,coder --auto # Auto-chain
uap run <session_id> --agent coder                         # Continue session
uap status <session_id>                                    # Check progress
uap sessions list                                          # List all
uap sessions export <session_id> -o out.json               # Export
```

### Agents

```bash
uap agents list                          # Built-in + installed agents
uap agents info coder                    # Agent details
uap agents add github:user/repo          # Install from GitHub
uap agents remove my-agent               # Remove
uap agents search "python fastapi"       # Search GitHub
```

### Configuration

```bash
uap config list                           # View all settings
uap config set groq_api_key gsk_xxx       # Set a key
uap config set default_backend ollama     # Switch backend
uap config path                           # Show config file location
```

### Local Models

```bash
uap local status                          # All backends: online/offline, model counts
uap local models                          # List models across all backends
uap local models ollama                   # List models on a specific backend
uap local health                          # Health-check every backend with latency
```

### Authentication

```bash
uap auth login                            # Google OAuth login
uap auth whoami                           # Current identity
uap auth logout                           # Clear credentials
```

---

## Supported Backends

### Cloud

| Backend | Config key | Notes |
|---|---|---|
| Groq | `groq_api_key` | Default, fast free tier |
| Google Gemini | `gemini_api_key` | Also supports OAuth |
| OpenAI | `openai_api_key` | GPT-4o, o1, etc. |
| Anthropic | `anthropic_api_key` | Claude models |
| Mistral | `mistral_api_key` | |
| Together | `together_api_key` | |
| OpenRouter | `openrouter_api_key` | Multi-provider router |

### Local

| Backend | Default URL | Config key |
|---|---|---|
| Ollama | `http://localhost:11434` | `ollama_url` |
| LM Studio | `http://localhost:1234` | `lmstudio_url` |
| llama.cpp | `http://localhost:8080` | `llamacpp_url` |
| vLLM | `http://localhost:8000` | `vllm_url` |

```bash
# Switch to a local backend
uap config set default_backend ollama

# Override the default URL
uap config set lmstudio_url http://192.168.1.50:1234
```

---

## Built-in Agents

| Agent | Type | Role |
|---|---|---|
| `planner` | planner | Breaks down tasks, creates roadmaps |
| `coder` | coder | Writes production-ready code |
| `reviewer` | reviewer | Reviews code for bugs & improvements |
| `debugger` | debugger | Diagnoses and fixes issues |
| `designer` | designer | UI/UX specs and visual design |
| `documenter` | documenter | Writes docs and READMEs |
| `dockdesk_planner` | planner | DockDesk-specialised planning |
| `dockdesk_coder` | coder | DockDesk-specialised coding |
| `dockdesk_reviewer` | reviewer | DockDesk-specialised review |

---

## The ACT (Agent Context Token)

The ACT is the portable state packet that travels between agents:

```json
{
  "session_id": "abc12345",
  "current_objective": "Build user authentication API",
  "context_summary": "Planner designed 3-endpoint auth system ...",
  "task_chain": [
    { "agent": "planner", "task": "Designed API structure", "result": "success" }
  ],
  "artifacts": {
    "code_snippets": ["def login(...)..."],
    "decisions": ["Using JWT for auth"],
    "files_modified": ["auth/routes.py"]
  },
  "handoff_reason": "Design complete, ready for implementation",
  "next_agent_hint": "coder"
}
```

---

## MCP Server

UAP ships an MCP server that exposes 8 tools over **stdio** for IDE integrations:

```bash
# Run the MCP server
python -m uap.mcp_server
```

Tools: `uap_new_session`, `uap_run_agent`, `uap_session_status`, `uap_list_sessions`, `uap_list_agents`, `uap_get_config`, `uap_set_config`, `uap_local_status`.

---

## Telemetry & Analytics

UAP captures structured events in JSONL format:

```python
from uap import get_telemetry
t = get_telemetry()
t.track("agent_invoked", {"agent": "coder", "backend": "groq"})
```

View analytics in the Streamlit dashboard or query the JSONL files directly at `~/.uap/telemetry/`.

---

## Security

- **Fernet vault** encrypts API keys at rest (`~/.uap/vault.enc`)
- **OAuth** for Google identity — tokens stored locally, never committed
- Credentials are never logged or included in ACT packets

---

## Storage Layout

```
~/.uap/
├── config.yaml          # Settings (backend, model, URLs)
├── vault.enc            # Encrypted API keys (Fernet)
├── sessions/            # Saved ACT sessions
├── agents/index.json    # Installed agent registry
└── telemetry/           # JSONL event logs
```

---

## Development

```bash
git clone https://github.com/srivatsa-source/UAP_Sandbox.git
cd UAP_Sandbox/uap-protocol
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT
