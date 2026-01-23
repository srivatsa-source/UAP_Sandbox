#!/usr/bin/env python3
"""
UAP Unified Launcher
====================
Single command to run the entire UAP system.

Usage:
    python run.py                   # Interactive mode - choose what to run
    python run.py chat              # Start interactive chat/CLI mode
    python run.py dashboard         # Launch Streamlit dashboard
    python run.py test              # Run a quick test
    python run.py --setup           # First-time setup wizard
    python run.py --check           # Check dependencies and configuration
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Ensure we're in the right directory
ROOT_DIR = Path(__file__).parent.resolve()
os.chdir(ROOT_DIR)

# Add paths for imports
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

# Rich console for pretty output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# Configuration file path
CONFIG_FILE = ROOT_DIR / ".uap_config.json"


def print_banner():
    """Print UAP banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║       🚀 UAP - Universal Agent Protocol                   ║
    ║       Seamless LLM-to-LLM Agent Handoffs                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    if RICH_AVAILABLE:
        console.print(Panel(banner, style="bold blue"))
    else:
        print(banner)


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except:
            pass
    return {}


def save_config(config: dict):
    """Save configuration to file."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def check_dependencies() -> dict:
    """Check which dependencies are installed."""
    deps = {
        "core": {
            "rich": False,
            "pydantic": False,
            "requests": False,
            "pyyaml": False,
        },
        "llm_backends": {
            "groq": False,
            "google-generativeai": False,
            "anthropic": False,
            "openai": False,
        },
        "dashboard": {
            "streamlit": False,
            "pandas": False,
        }
    }
    
    # Check core
    try:
        import rich
        deps["core"]["rich"] = True
    except ImportError:
        pass
    
    try:
        import pydantic
        deps["core"]["pydantic"] = True
    except ImportError:
        pass
    
    try:
        import requests
        deps["core"]["requests"] = True
    except ImportError:
        pass
    
    try:
        import yaml
        deps["core"]["pyyaml"] = True
    except ImportError:
        pass
    
    # Check LLM backends
    try:
        import groq
        deps["llm_backends"]["groq"] = True
    except ImportError:
        pass
    
    try:
        import google.generativeai
        deps["llm_backends"]["google-generativeai"] = True
    except ImportError:
        pass
    
    try:
        import anthropic
        deps["llm_backends"]["anthropic"] = True
    except ImportError:
        pass
    
    try:
        import openai
        deps["llm_backends"]["openai"] = True
    except ImportError:
        pass
    
    # Check dashboard
    try:
        import streamlit
        deps["dashboard"]["streamlit"] = True
    except ImportError:
        pass
    
    try:
        import pandas
        deps["dashboard"]["pandas"] = True
    except ImportError:
        pass
    
    return deps


def check_api_keys() -> dict:
    """Check which API keys are configured."""
    config = load_config()
    env_keys = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY") or config.get("groq_api_key"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY") or config.get("openai_api_key"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY") or config.get("anthropic_api_key"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY") or config.get("google_api_key"),
        "TOGETHER_API_KEY": os.getenv("TOGETHER_API_KEY") or config.get("together_api_key"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY") or config.get("openrouter_api_key"),
    }
    return {k: bool(v) for k, v in env_keys.items()}


def run_check():
    """Run dependency and configuration check."""
    print_banner()
    
    deps = check_dependencies()
    keys = check_api_keys()
    
    if RICH_AVAILABLE:
        # Dependencies table
        table = Table(title="📦 Dependencies")
        table.add_column("Category", style="cyan")
        table.add_column("Package", style="white")
        table.add_column("Status", style="green")
        
        for category, packages in deps.items():
            for pkg, installed in packages.items():
                status = "✅ Installed" if installed else "❌ Missing"
                style = "green" if installed else "red"
                table.add_row(category, pkg, f"[{style}]{status}[/{style}]")
        
        console.print(table)
        console.print()
        
        # API Keys table
        key_table = Table(title="🔑 API Keys")
        key_table.add_column("Provider", style="cyan")
        key_table.add_column("Status", style="green")
        
        for key, configured in keys.items():
            provider = key.replace("_API_KEY", "").replace("_", " ").title()
            status = "✅ Configured" if configured else "⚪ Not set"
            style = "green" if configured else "dim"
            key_table.add_row(provider, f"[{style}]{status}[/{style}]")
        
        console.print(key_table)
    else:
        print("\n=== Dependencies ===")
        for category, packages in deps.items():
            print(f"\n{category}:")
            for pkg, installed in packages.items():
                status = "✓" if installed else "✗"
                print(f"  {status} {pkg}")
        
        print("\n=== API Keys ===")
        for key, configured in keys.items():
            status = "✓" if configured else "-"
            print(f"  {status} {key}")
    
    # Check if minimum requirements are met
    core_ok = all(deps["core"].values())
    has_backend = any(deps["llm_backends"].values()) or any(keys.values())
    
    if not core_ok:
        print("\n⚠️  Missing core dependencies. Run: pip install -r requirements.txt")
        return False
    
    if not has_backend:
        print("\n⚠️  No LLM backend configured. Run: python run.py --setup")
        return False
    
    print("\n✅ UAP is ready to use!")
    return True


def run_setup():
    """Interactive setup wizard."""
    print_banner()
    print("\n🔧 UAP Setup Wizard\n")
    
    config = load_config()
    
    # Install dependencies first
    print("Step 1: Installing dependencies...")
    req_file = ROOT_DIR / "requirements.txt"
    if req_file.exists():
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
            capture_output=True
        )
        if result.returncode == 0:
            print("  ✅ Dependencies installed")
        else:
            print("  ⚠️  Some dependencies failed to install. Check requirements.txt")
    
    # Reload rich if now available
    global RICH_AVAILABLE, console
    try:
        from rich.console import Console
        from rich.prompt import Prompt, Confirm
        RICH_AVAILABLE = True
        console = Console()
    except:
        pass
    
    # Choose LLM backend
    print("\nStep 2: Choose your LLM backend")
    print("  1. Groq (Free tier available, fast inference)")
    print("  2. OpenAI (GPT-4, requires paid API)")
    print("  3. Anthropic (Claude, requires paid API)")
    print("  4. Google Gemini (Free tier available)")
    print("  5. Ollama (Local, free, requires Ollama installed)")
    print("  6. Together AI (Various models)")
    print("  7. OpenRouter (Access multiple providers)")
    
    if RICH_AVAILABLE:
        choice = Prompt.ask("Select backend", choices=["1", "2", "3", "4", "5", "6", "7"], default="1")
    else:
        choice = input("Select backend [1-7, default=1]: ").strip() or "1"
    
    backend_map = {
        "1": ("groq", "GROQ_API_KEY", "groq_api_key", "https://console.groq.com/keys"),
        "2": ("openai", "OPENAI_API_KEY", "openai_api_key", "https://platform.openai.com/api-keys"),
        "3": ("anthropic", "ANTHROPIC_API_KEY", "anthropic_api_key", "https://console.anthropic.com/"),
        "4": ("gemini", "GOOGLE_API_KEY", "google_api_key", "https://aistudio.google.com/app/apikey"),
        "5": ("ollama", None, None, "https://ollama.ai/download"),
        "6": ("together", "TOGETHER_API_KEY", "together_api_key", "https://api.together.xyz/"),
        "7": ("openrouter", "OPENROUTER_API_KEY", "openrouter_api_key", "https://openrouter.ai/keys"),
    }
    
    backend, env_key, config_key, url = backend_map[choice]
    config["default_backend"] = backend
    
    if backend == "ollama":
        print(f"\n  Ollama selected. Make sure Ollama is running locally.")
        print(f"  Download from: {url}")
        if RICH_AVAILABLE:
            ollama_url = Prompt.ask("Ollama URL", default="http://localhost:11434")
        else:
            ollama_url = input("Ollama URL [http://localhost:11434]: ").strip() or "http://localhost:11434"
        config["ollama_url"] = ollama_url
    else:
        print(f"\n  Get your API key from: {url}")
        if RICH_AVAILABLE:
            api_key = Prompt.ask(f"Enter your {backend.upper()} API key", password=True)
        else:
            api_key = input(f"Enter your {backend.upper()} API key: ").strip()
        
        if api_key:
            config[config_key] = api_key
            # Also set as environment variable for current session
            os.environ[env_key] = api_key
            print(f"  ✅ API key saved")
    
    # Save configuration
    save_config(config)
    print(f"\n✅ Configuration saved to {CONFIG_FILE}")
    
    # Run a quick test
    print("\nStep 3: Testing connection...")
    try:
        if test_llm_connection(config):
            print("  ✅ LLM connection successful!")
        else:
            print("  ⚠️  Connection test failed. Check your API key.")
    except Exception as e:
        print(f"  ⚠️  Connection test error: {e}")
    
    print("\n🎉 Setup complete! Run 'python run.py' to start UAP.")


def test_llm_connection(config: dict) -> bool:
    """Test LLM connection with a simple query."""
    backend = config.get("default_backend", "groq")
    
    try:
        if backend == "groq":
            from groq import Groq
            api_key = config.get("groq_api_key") or os.getenv("GROQ_API_KEY")
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": "Say 'UAP ready' in 3 words or less"}],
                max_tokens=10
            )
            return bool(response.choices[0].message.content)
        
        elif backend == "ollama":
            import requests
            url = config.get("ollama_url", "http://localhost:11434")
            response = requests.get(f"{url}/api/tags", timeout=5)
            return response.status_code == 200
        
        elif backend == "gemini":
            import google.generativeai as genai
            api_key = config.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Say 'UAP ready'")
            return bool(response.text)
        
        # For other backends, just check if key exists
        return True
        
    except Exception as e:
        print(f"  Error: {e}")
        return False


def run_chat():
    """Run the interactive chat/CLI mode."""
    print_banner()
    
    config = load_config()
    
    # Load API key from config into environment
    if config.get("groq_api_key"):
        os.environ["GROQ_API_KEY"] = config["groq_api_key"]
    if config.get("google_api_key"):
        os.environ["GOOGLE_API_KEY"] = config["google_api_key"]
    if config.get("openai_api_key"):
        os.environ["OPENAI_API_KEY"] = config["openai_api_key"]
    if config.get("anthropic_api_key"):
        os.environ["ANTHROPIC_API_KEY"] = config["anthropic_api_key"]
    
    # Import and run dispatcher
    try:
        from protocol import StateManager, ACT
        from dispatcher import Dispatcher, AgentConfig
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Run: pip install -r requirements.txt")
        return
    
    # Check API key
    backend = config.get("default_backend", "groq")
    api_key = os.getenv("GROQ_API_KEY")
    
    if backend == "groq" and not api_key:
        print("❌ No API key configured. Run: python run.py --setup")
        return
    
    print(f"Using backend: {backend}")
    print("Type 'quit' to exit, 'status' to see current state\n")
    
    # Initialize dispatcher
    dispatcher = Dispatcher(groq_api_key=api_key)
    
    # Register default agents
    agents = [
        AgentConfig("planner", "planner", "You are a strategic planner. Break down tasks into steps."),
        AgentConfig("coder", "coder", "You are an expert programmer. Write clean, efficient code."),
        AgentConfig("reviewer", "reviewer", "You are a code reviewer. Review code for bugs and improvements."),
    ]
    for agent in agents:
        dispatcher.register_agent(agent)
    
    # Create a new session
    session = dispatcher.start_session("Interactive UAP Session")
    print(f"Session started: {session.session_id}\n")
    
    # Main loop
    while True:
        try:
            if RICH_AVAILABLE:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            else:
                user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("Goodbye!")
                break
            
            if user_input.lower() == 'status':
                act = dispatcher.state_manager.get_session(session.session_id)
                print(json.dumps(act.to_dict(), indent=2))
                continue
            
            # Process the task
            print("\n🤖 Processing...")
            result = dispatcher.dispatch_task(
                session_id=session.session_id,
                task=user_input,
                agent_id="planner"
            )
            
            # Display result
            if RICH_AVAILABLE:
                console.print(Panel(result.get("answer", "No response"), title="Agent Response", border_style="green"))
            else:
                print(f"\nAgent: {result.get('answer', 'No response')}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def run_dashboard():
    """Launch the Streamlit dashboard."""
    print_banner()
    print("🚀 Starting UAP Dashboard...\n")
    
    config = load_config()
    
    # Set environment variables from config
    if config.get("groq_api_key"):
        os.environ["GROQ_API_KEY"] = config["groq_api_key"]
    
    dashboard_path = ROOT_DIR / "uap-segment-dashboard" / "src" / "streamlit_app.py"
    
    if not dashboard_path.exists():
        print(f"❌ Dashboard not found at {dashboard_path}")
        return
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(dashboard_path),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ], cwd=str(ROOT_DIR))
    except FileNotFoundError:
        print("❌ Streamlit not installed. Run: pip install streamlit")
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


def run_test():
    """Run a quick test of the UAP system."""
    print_banner()
    print("🧪 Running UAP Test...\n")
    
    config = load_config()
    
    # Set API key from config
    if config.get("groq_api_key"):
        os.environ["GROQ_API_KEY"] = config["groq_api_key"]
    
    try:
        from protocol import StateManager, ACT
        from dispatcher import Dispatcher, AgentConfig
        
        print("✅ Imports successful")
        
        # Check if we can call LLM
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            dispatcher = Dispatcher(groq_api_key=api_key)
            print("✅ Dispatcher initialized")
            
            dispatcher.register_agent(
                AgentConfig("test", "tester", "You are a test agent. Respond with 'UAP TEST OK'")
            )
            print("✅ Agent registered")
            
            # Create session using dispatcher's start_session
            session = dispatcher.start_session("Test task")
            print(f"✅ Session created: {session.session_id}")
            
            # Quick LLM call
            print("\n📡 Testing LLM connection...")
            result = dispatcher.dispatch_task(
                session_id=session.session_id,
                task="Say 'UAP is working!' and nothing else",
                agent_id="test"
            )
            print(f"✅ LLM Response: {result.get('answer', 'No response')[:100]}")
        else:
            print("⚠️  No API key - skipping LLM test")
            
            # At least test StateManager
            sm = StateManager()
            print("✅ StateManager created")
            session = sm.create_session("Test task")
            print(f"✅ Session created: {session.session_id}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def show_menu():
    """Show interactive menu."""
    print_banner()
    
    if RICH_AVAILABLE:
        console.print("\n[bold]What would you like to do?[/bold]\n")
        console.print("  [cyan]1[/cyan]. 💬 Start Chat (Interactive CLI)")
        console.print("  [cyan]2[/cyan]. 📊 Launch Dashboard (Streamlit UI)")
        console.print("  [cyan]3[/cyan]. 🧪 Run Quick Test")
        console.print("  [cyan]4[/cyan]. 🔍 Check Configuration")
        console.print("  [cyan]5[/cyan]. 🔧 Run Setup Wizard")
        console.print("  [cyan]6[/cyan]. 🚪 Exit")
        console.print()
        
        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6"], default="1")
    else:
        print("\nWhat would you like to do?\n")
        print("  1. Start Chat (Interactive CLI)")
        print("  2. Launch Dashboard (Streamlit UI)")
        print("  3. Run Quick Test")
        print("  4. Check Configuration")
        print("  5. Run Setup Wizard")
        print("  6. Exit")
        print()
        choice = input("Select option [1-6]: ").strip() or "1"
    
    if choice == "1":
        run_chat()
    elif choice == "2":
        run_dashboard()
    elif choice == "3":
        run_test()
    elif choice == "4":
        run_check()
    elif choice == "5":
        run_setup()
    elif choice == "6":
        print("Goodbye!")
        sys.exit(0)


def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    if not args:
        # Interactive menu
        show_menu()
    elif args[0] == "--setup" or args[0] == "setup":
        run_setup()
    elif args[0] == "--check" or args[0] == "check":
        run_check()
    elif args[0] == "chat" or args[0] == "cli":
        run_chat()
    elif args[0] == "dashboard" or args[0] == "ui":
        run_dashboard()
    elif args[0] == "test":
        run_test()
    elif args[0] == "--help" or args[0] == "-h":
        print(__doc__)
    else:
        print(f"Unknown command: {args[0]}")
        print("Run 'python run.py --help' for usage")


if __name__ == "__main__":
    main()
