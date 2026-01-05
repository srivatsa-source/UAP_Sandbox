"""
UAP Agent Registry
Discovers and loads agents from:
1. Built-in agents (bundled with package)
2. User-installed agents (~/.uap/agents/)
3. GitHub repos (on-demand installation)
"""

import json
import re
from pathlib import Path
from typing import Optional
import yaml

from uap.dispatcher import AgentConfig
from uap.protocol import get_uap_home


def get_agents_dir() -> Path:
    """Get agents directory (~/.uap/agents)"""
    agents_dir = get_uap_home() / "agents"
    agents_dir.mkdir(exist_ok=True)
    return agents_dir


def get_agents_index_path() -> Path:
    """Get agents index file path."""
    return get_agents_dir() / "index.json"


# =============================================================================
# BUILT-IN AGENTS
# =============================================================================

BUILTIN_AGENTS = {
    "planner": AgentConfig(
        agent_id="planner",
        agent_type="planner",
        system_prompt="""You are a technical project planner and architect.
Your role is to:
- Break down complex tasks into actionable subtasks
- Identify dependencies between tasks
- Estimate complexity and suggest agent routing
- Create implementation roadmaps

When you receive a task:
1. Analyze the requirements thoroughly
2. Break it into 3-5 discrete subtasks
3. Specify which agent type should handle each subtask
4. Provide clear acceptance criteria for each subtask

Always hand off to the appropriate specialist after planning.""",
        model="llama-3.1-8b-instant",
        backend="groq",
        source="builtin"
    ),
    
    "coder": AgentConfig(
        agent_id="coder",
        agent_type="coder",
        system_prompt="""You are an expert Python developer.
Your role is to:
- Write clean, production-ready code
- Follow best practices and PEP 8 style
- Include docstrings and type hints
- Handle edge cases and errors gracefully

When implementing:
1. Read the context_summary carefully for requirements
2. Check artifacts for any prior code or decisions
3. Write complete, functional code (not pseudocode)
4. Document any assumptions you make

Hand off to reviewer when code is ready for review.""",
        model="llama-3.1-8b-instant",
        backend="groq",
        source="builtin"
    ),
    
    "reviewer": AgentConfig(
        agent_id="reviewer",
        agent_type="reviewer",
        system_prompt="""You are a senior code reviewer.
Your role is to:
- Review code for correctness, security, and performance
- Check for edge cases and error handling
- Verify code meets the original requirements
- Suggest specific improvements with code examples

Review checklist:
1. Does the code solve the stated problem?
2. Are there any bugs or logic errors?
3. Is error handling adequate?
4. Are there security concerns?
5. Is the code maintainable and readable?

If issues found, hand off to debugger or back to coder.
If approved, mark task as complete.""",
        model="llama-3.1-8b-instant",
        backend="groq",
        source="builtin"
    ),
    
    "debugger": AgentConfig(
        agent_id="debugger",
        agent_type="debugger",
        system_prompt="""You are a debugging specialist.
Your role is to:
- Analyze error messages and stack traces
- Identify root causes of bugs
- Propose and implement fixes
- Add defensive code to prevent recurrence

Debugging process:
1. Read the error/issue description from context
2. Analyze any code snippets in artifacts
3. Identify the root cause
4. Implement a fix with explanation
5. Suggest tests to verify the fix

Hand off to reviewer after fixing, or back to coder if refactoring needed.""",
        model="llama-3.1-8b-instant",
        backend="groq",
        source="builtin"
    ),
    
    "designer": AgentConfig(
        agent_id="designer",
        agent_type="designer",
        system_prompt="""You are a UI/UX and visual designer.
Your role is to:
- Create visual designs and specifications
- Define color palettes, typography, and spacing
- Design component layouts and interactions
- Specify assets needed (icons, images, sprites)

For game design:
- Design sprites and animations (specify sizes, colors)
- Create UI layouts for menus and HUD
- Define visual feedback for game events

Always provide exact specifications (hex colors, pixel sizes, etc.)
Hand off to coder when designs are ready for implementation.""",
        model="llama-3.1-8b-instant",
        backend="groq",
        source="builtin"
    ),
    
    "documenter": AgentConfig(
        agent_id="documenter",
        agent_type="documenter",
        system_prompt="""You are a technical documentation specialist.
Your role is to:
- Write clear README files and API documentation
- Create usage examples and tutorials
- Document architecture decisions
- Generate inline code comments

Documentation standards:
1. Use Markdown format
2. Include code examples for every public function
3. Document parameters, return values, and exceptions
4. Add "Quick Start" sections for new users

Hand off when documentation is complete.""",
        model="llama-3.1-8b-instant",
        backend="groq",
        source="builtin"
    ),
}


class AgentRegistry:
    """
    Central registry for discovering and managing agents.
    """
    
    def __init__(self):
        self.agents_dir = get_agents_dir()
        self._index: dict[str, dict] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load the agents index from disk."""
        index_path = get_agents_index_path()
        if index_path.exists():
            try:
                with open(index_path, "r") as f:
                    self._index = json.load(f)
            except json.JSONDecodeError:
                self._index = {}
        else:
            self._index = {}
    
    def _save_index(self) -> None:
        """Save the agents index to disk."""
        index_path = get_agents_index_path()
        with open(index_path, "w") as f:
            json.dump(self._index, f, indent=2)
    
    def list_builtin(self) -> list[AgentConfig]:
        """List all built-in agents."""
        return list(BUILTIN_AGENTS.values())
    
    def list_installed(self) -> list[dict]:
        """List all user-installed agents."""
        return list(self._index.values())
    
    def list_all(self) -> list[AgentConfig]:
        """List all available agents (builtin + installed)."""
        agents = list(BUILTIN_AGENTS.values())
        
        # Load installed agents
        for agent_id, info in self._index.items():
            try:
                agent = self._load_installed_agent(agent_id)
                if agent:
                    agents.append(agent)
            except Exception:
                continue
        
        return agents
    
    def get(self, agent_id: str) -> Optional[AgentConfig]:
        """Get an agent by ID."""
        # Check builtin first
        if agent_id in BUILTIN_AGENTS:
            return BUILTIN_AGENTS[agent_id]
        
        # Check installed
        if agent_id in self._index:
            return self._load_installed_agent(agent_id)
        
        return None
    
    def _load_installed_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Load an installed agent from disk."""
        agent_dir = self.agents_dir / agent_id
        manifest_path = agent_dir / "uap-agent.yaml"
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
            
            # Load system prompt
            prompt_file = manifest.get("prompt_file", "system.txt")
            prompt_path = agent_dir / prompt_file
            
            if prompt_path.exists():
                system_prompt = prompt_path.read_text()
            else:
                system_prompt = manifest.get("system_prompt", "")
            
            return AgentConfig(
                agent_id=manifest.get("name", agent_id),
                agent_type=manifest.get("type", "coder"),
                system_prompt=system_prompt,
                model=manifest.get("defaults", {}).get("model", "llama-3.1-8b-instant"),
                backend=manifest.get("defaults", {}).get("backend", "groq"),
                source=f"github:{self._index.get(agent_id, {}).get('repo', 'unknown')}",
                metadata=manifest.get("metadata", {})
            )
        except Exception:
            return None
    
    def install_from_github(self, repo: str) -> AgentConfig:
        """
        Install an agent from a GitHub repository.
        
        Args:
            repo: GitHub repo in format "owner/repo" or "github:owner/repo"
        
        Returns:
            Installed AgentConfig
        """
        import requests
        
        # Parse repo format
        repo = repo.replace("github:", "")
        if "/" not in repo:
            raise ValueError(f"Invalid repo format: {repo}. Use owner/repo")
        
        owner, repo_name = repo.split("/", 1)
        
        # Fetch uap-agent.yaml from repo
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/uap-agent.yaml"
        
        try:
            response = requests.get(raw_url, timeout=10)
            response.raise_for_status()
            manifest = yaml.safe_load(response.text)
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch agent manifest from {repo}: {e}")
        
        agent_id = manifest.get("name", repo_name)
        agent_dir = self.agents_dir / agent_id
        agent_dir.mkdir(exist_ok=True)
        
        # Save manifest
        manifest_path = agent_dir / "uap-agent.yaml"
        with open(manifest_path, "w") as f:
            yaml.safe_dump(manifest, f)
        
        # Fetch prompt file if specified
        prompt_file = manifest.get("prompt_file", "system.txt")
        prompt_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/{prompt_file}"
        
        try:
            response = requests.get(prompt_url, timeout=10)
            if response.ok:
                prompt_path = agent_dir / Path(prompt_file).name
                prompt_path.write_text(response.text)
        except requests.RequestException:
            pass  # Prompt file is optional
        
        # Update index
        self._index[agent_id] = {
            "repo": repo,
            "name": manifest.get("name", agent_id),
            "type": manifest.get("type", "coder"),
            "description": manifest.get("description", ""),
            "installed_at": __import__("datetime").datetime.now().isoformat()
        }
        self._save_index()
        
        return self._load_installed_agent(agent_id)
    
    def uninstall(self, agent_id: str) -> bool:
        """Uninstall an agent."""
        if agent_id in BUILTIN_AGENTS:
            raise ValueError(f"Cannot uninstall built-in agent: {agent_id}")
        
        if agent_id not in self._index:
            return False
        
        # Remove directory
        agent_dir = self.agents_dir / agent_id
        if agent_dir.exists():
            import shutil
            shutil.rmtree(agent_dir)
        
        # Remove from index
        del self._index[agent_id]
        self._save_index()
        
        return True
    
    def search_github(self, query: str) -> list[dict]:
        """
        Search GitHub for UAP agents.
        Searches for repos with 'uap-agent' topic or containing uap-agent.yaml.
        """
        import requests
        
        search_url = "https://api.github.com/search/repositories"
        params = {
            "q": f"{query} uap-agent in:name,description,readme",
            "sort": "stars",
            "per_page": 10
        }
        
        try:
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return [
                {
                    "repo": item["full_name"],
                    "description": item.get("description", ""),
                    "stars": item["stargazers_count"],
                    "url": item["html_url"]
                }
                for item in data.get("items", [])
            ]
        except requests.RequestException:
            return []


# Convenience function
def get_registry() -> AgentRegistry:
    """Get the global agent registry."""
    return AgentRegistry()
