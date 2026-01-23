# UAP - Universal Agent Protocol

**Connect AI agents, share state, run tasks from your terminal.**

UAP is like "Segment for AI Agents" – it standardizes LLM-to-LLM data transfer using a persistent **State Packet** (Agent Context Token - ACT) so agents can hand off work without losing context or re-prompting users.

## Installation

### Option 1: pip install (Recommended)

```bash
# Basic install
pip install uap-protocol

# With dashboard (web UI)
pip install uap-protocol[dashboard]

# Full install (all LLM backends)
pip install uap-protocol[all]
```

After installing, run from anywhere:

```bash
uap-run              # Interactive menu
uap-run dashboard    # Web dashboard with stats
uap-run chat         # CLI chat mode
uap-run --setup      # First-time setup
```

### Option 2: From source

```bash
# Clone and install
git clone https://github.com/uap-protocol/uap.git
cd uap
pip install -r requirements.txt

# Run with local script
python run.py              # Interactive menu
python run.py dashboard    # Web dashboard
python run.py --setup      # Setup wizard
```

### Windows Users

```powershell
# After cloning, use the batch launcher:
.\uap.bat              # Interactive menu
.\uap.bat dashboard    # Web dashboard
.\uap.bat --setup      # Setup wizard
```

## Quick Start

```bash
# 1. Setup (choose LLM backend, enter API key)
uap-run --setup

# 2. Launch dashboard
uap-run dashboard

# 3. Or use CLI
uap-run chat
```

## How It Works

1. **You submit a task** → UAP creates an ACT (Agent Context Token)
2. **Agent A processes** → Updates the ACT with context, decisions, artifacts
3. **Handoff to Agent B** → Agent B reads ACT and continues WITHOUT re-prompting you
4. **Chain continues** → Each agent adds to the shared state
5. **Task completes** → Full history preserved in ACT

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Planner    │────▶│  Shared State   │────▶│    Coder     │
│              │     │     (ACT)       │     │              │
│ Breaks down  │     │                 │     │ Implements   │
│ the task     │     │ • Objective     │     │ the code     │
└──────────────┘     │ • Context       │     └──────────────┘
                     │ • Artifacts     │            │
                     │ • Decisions     │            ▼
┌──────────────┐     │ • Task Chain    │     ┌──────────────┐
│   Complete   │◀────│                 │◀────│   Reviewer   │
│              │     └─────────────────┘     │              │
│ All agents   │                             │ Reviews &    │
│ contributed  │                             │ approves     │
└──────────────┘                             └──────────────┘
```

## Dashboard Features

- **💬 Chat Interface** - Interactive task console with agent handoffs
- **📊 Stats Page** - Usage analytics, agent breakdown, session history
- **🔄 Auto-Handoff** - Automatic agent chaining for complex tasks
- **💾 State Export** - Save sessions as JSON for later use

## Alternative: Package Commands

If you prefer, you can also install UAP as a package and use the CLI commands:

```bash
# Install UAP as package
pip install -e .

# Set your API key
uap config set groq_api_key gsk_your_key_here

# Run a task with multiple agents
uap new "Build a REST API endpoint for user authentication" --agents planner,coder,reviewer --auto
```

## Commands

### Session Management

```bash
# Start new session
uap new "Your task description" --agents planner,coder,reviewer

# Auto-chain all agents
uap new "Build a login page" --agents planner,coder,reviewer --auto

# Continue existing session
uap run abc123 --agent coder

# Check session status
uap status abc123

# List all sessions
uap sessions list

# Export session
uap sessions export abc123 -o my-session.json
```

### Agent Management

```bash
# List available agents
uap agents list

# Install agent from GitHub
uap agents add github:awesome-dev/fastapi-agent
uap agents add user/repo-name

# Remove installed agent
uap agents remove my-agent

# Get agent details
uap agents info coder

# Search GitHub for agents
uap agents search "python fastapi"
```

### Configuration

```bash
# Set API key
uap config set groq_api_key gsk_xxx

# Set default backend
uap config set default_backend ollama

# Set Ollama URL
uap config set ollama_url http://localhost:11434

# View all config
uap config list

# Show config file location
uap config path
```

## Built-in Agents

| Agent | Type | Description |
|-------|------|-------------|
| `planner` | planner | Breaks down tasks, creates roadmaps |
| `coder` | coder | Writes production-ready code |
| `reviewer` | reviewer | Reviews code for bugs and improvements |
| `debugger` | debugger | Diagnoses and fixes issues |
| `designer` | designer | Creates UI/UX specs and visual designs |
| `documenter` | documenter | Writes documentation and READMEs |

## Creating Custom Agents

Create a GitHub repo with this structure:

```
my-uap-agent/
├── uap-agent.yaml     # Agent manifest (required)
├── system.txt         # System prompt
└── README.md
```

**uap-agent.yaml:**
```yaml
name: fastapi-expert
version: 1.0.0
type: coder
description: "Specialized FastAPI developer"

prompt_file: system.txt

defaults:
  backend: groq
  model: llama-3.1-70b-versatile

capabilities:
  - python
  - fastapi
  - sqlalchemy
```

Then install it:
```bash
uap agents add github:yourname/my-uap-agent
```

## The ACT (Agent Context Token)

The ACT is the "passport" that carries state between agents:

```json
{
  "session_id": "abc12345",
  "current_objective": "Build user authentication API",
  "context_summary": "Planner designed 3-endpoint auth system. Need login, register, logout endpoints with JWT tokens.",
  "task_chain": [
    {"agent": "planner", "task": "Designed API structure", "result": "success"}
  ],
  "artifacts": {
    "code_snippets": ["def login(...)..."],
    "decisions": ["Using JWT for auth", "Password hashing with bcrypt"],
    "files_modified": ["auth/routes.py"]
  },
  "handoff_reason": "Design complete, ready for implementation",
  "next_agent_hint": "coder"
}
```

## Backends

UAP supports multiple LLM backends:

- **Groq** (default): Fast inference, requires API key
- **Ollama**: Local models, no API key needed

```bash
# Use Groq (default)
uap config set default_backend groq
uap config set groq_api_key gsk_xxx

# Use Ollama
uap config set default_backend ollama
uap config set ollama_url http://localhost:11434
```

## Storage

UAP stores data in `~/.uap/`:

```
~/.uap/
├── config.yaml      # Your configuration
├── sessions/        # Saved ACT sessions
│   ├── abc123.json
│   └── def456.json
└── agents/          # Installed agents
    └── index.json
```

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/uap-protocol/uap
cd uap
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
