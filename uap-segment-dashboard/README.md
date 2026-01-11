# 🔮 UAP Segment Dashboard

> **"Segment for Agents"** - A real-time dashboard to observe your AI swarm collaborate via the Universal Agent Protocol.

## Overview

The UAP Segment Dashboard is a Streamlit-based web interface for the Universal Agent Protocol (UAP). Watch the State Packet (ACT) evolve in real-time as multiple AI agents collaborate on complex tasks.

![Dashboard Preview](https://via.placeholder.com/800x400?text=UAP+Segment+Dashboard)

## ✨ Features

- **💬 Full Chat Interface**: Communicate with your AI swarm using `st.chat_message` and `st.chat_input`
- **📦 Live ACT Viewer**: Watch the State Packet evolve in real-time with `st.json()`
- **🤖 Multi-Agent Support**: Switch between Planner, Coder, Reviewer, and Designer agents
- **⚡ Auto-Handoff**: Enable automatic routing to suggested agents
- **🎨 Dark Theme**: Modern developer tool aesthetic with GitHub-inspired styling
- **🔄 Session Management**: Reset protocol and manage multiple sessions

## 🏗️ Project Structure

```
uap-segment-dashboard/
├── src/
│   ├── streamlit_app.py          # Main Streamlit application
│   ├── components/
│   │   ├── chat_interface.py     # Chat UI components
│   │   └── state_packet_viewer.py # ACT visualization
│   ├── models/
│   │   └── state_packet.py       # State packet data model
│   └── utils/
│       └── packet_handler.py     # ACT update handlers
├── config/
│   └── settings.py               # Theme & configuration
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Groq API key (or local Ollama installation)

### Installation

1. **Navigate to the dashboard directory:**
   ```bash
   cd uap-segment-dashboard
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your API key:**
   ```bash
   # Windows PowerShell
   $env:GROQ_API_KEY="your-groq-api-key"
   
   # Linux/Mac
   export GROQ_API_KEY="your-groq-api-key"
   ```

4. **Run the dashboard:**
   ```bash
   streamlit run src/streamlit_app.py
   ```

5. **Open your browser** to `http://localhost:8501`

## 🎯 Usage

### Basic Workflow

1. **Select an Agent**: Use the sidebar dropdown to choose which agent receives your messages
2. **Send a Message**: Type in the chat input to start a task
3. **Watch the ACT**: Observe the State Packet evolve in the right panel
4. **Follow Handoffs**: When an agent suggests a handoff, switch to the recommended agent

### UI Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  🔮 UAP Segment Dashboard                                        │
├─────────────────────────────┬────────────────────────────────────┤
│  SIDEBAR                    │  MAIN CONTENT                      │
│  ─────────                  │  ────────────                      │
│  🤖 Select Agent            │  ┌─────────────┬──────────────┐   │
│  ☑️ Auto-Handoff            │  │ 💬 Chat     │ 📦 Live ACT  │   │
│  🆕 New Session             │  │             │              │    │
│  🗑️ Reset All               │  │ User: ...   │ session_id   │   │
│                             │  │ Agent: ...  │ objective    │    │
│  📦 State Packet (ACT)      │  │             │ context      │    │
│  ├─ Objective               │  │             │ tasks: []    │    │
│  ├─ Context                 │  │             │ artifacts    │    │
│  └─ Full JSON               │  └─────────────┴──────────────┘   │
└─────────────────────────────┴────────────────────────────────────┘
```

### Agent Types

| Agent | Icon | Purpose |
|-------|------|---------|
| **Planner** | 📋 | Task breakdown, strategy, coordination |
| **Coder** | 💻 | Implementation, debugging, coding |
| **Reviewer** | 🔍 | Code review, testing, quality |
| **Designer** | 🎨 | UI/UX, visuals, pixel art |

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key | Required |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |

### Using Ollama Instead of Groq

Edit `config/settings.py`:

```python
DEFAULT_BACKEND = "ollama"
DEFAULT_OLLAMA_MODEL = "llama3"
```

## 🔗 Integration with UAP Protocol

This dashboard integrates directly with the UAP protocol files:

- **`protocol.py`**: `StateManager` and `ACT` classes for state management
- **`dispatcher.py`**: `Dispatcher` class for LLM routing and handoffs
- **`reflector_prompt.txt`**: Instructions for UAP-compliant agent responses

## 🤝 Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## 📄 License

MIT License - See LICENSE file for details.

## License
This project is licensed under the MIT License. See the LICENSE file for details.