# UAP — Universal Agent Protocol

[![PyPI](https://img.shields.io/pypi/v/uap-protocol)](https://pypi.org/project/uap-protocol/)

**The open standard for AI-agent interoperability.**

UAP is a minimalist Semantic Transport Layer designed to act as the \"SMTP for AI Agents.\" It standardizes LLM-to-LLM data transfer through a persistent **Agent Context Token (ACT)** so agents can hand off work without losing context or requiring redundant re-prompting.

---

## ⚡ Core Philosophy

The new architecture focuses 100% on **Identity (OAuth/Vault)** and **State Handoff (ACT)**, exposing execution solely over the Model Context Protocol (MCP).
- **No UI Bloat:** UAP runs purely as a backend binary/CLI.
- **Headless MCP Execution:** Agents are dynamically spawned via MCP calls rather than hardcoded subclasses.
- **Secure by Default:** Native OS Keyring ensures your API keys stay guarded.

## 🛠️ Installation

\\\ash
pip install "uap-protocol[mcp]"
\\\

## 🚀 Quick Start

1. **Verify Identity** (Google OAuth):
    \\\ash
    uap login
    \\\

2. **Check Agent/Provider Linking**:
    \\\ash
    uap status
    \\\

3. **Start the MCP Server Layer**:
    \\\ash
    uap start
    \\\

> *NOTE: uap start uses stdio for MCP. Connect it to an MCP-capable host such as Claude Desktop or VS Code.*

## 🔗 Architecture

UAP uses exactly two external dependencies for execution:
1. \openai\ (For remote, OpenAI-compatible backends)
2. \ollama\ (For local LLM evaluation)

Requests are received via \start\, parsed by \mcp_server.py\, validated against \keyring\ inside \ault.py\, and finally relayed by \dispatcher.py\.
