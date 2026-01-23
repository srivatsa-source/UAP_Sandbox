#!/usr/bin/env python3
"""
UAP Launcher - Run UAP from anywhere after pip install.

Usage:
    uap-run              # Interactive menu
    uap-run dashboard    # Launch web dashboard
    uap-run chat         # CLI chat mode
    uap-run test         # Quick test
    uap-run --setup      # Setup wizard
    uap-run --check      # Check configuration
"""

import os
import sys
import json
import subprocess
from pathlib import Path


def get_uap_home() -> Path:
    """Get UAP home directory (~/.uap)"""
    uap_home = Path.home() / ".uap"
    uap_home.mkdir(exist_ok=True)
    return uap_home


def get_config() -> dict:
    """Load configuration."""
    config_file = get_uap_home() / "config.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except:
            pass
    return {}


def save_config(config: dict):
    """Save configuration."""
    config_file = get_uap_home() / "config.json"
    config_file.write_text(json.dumps(config, indent=2))


def find_dashboard() -> Path:
    """Find the dashboard script."""
    pkg_dir = Path(__file__).parent
    
    # Possible locations
    locations = [
        pkg_dir / "dashboard_app.py",
        pkg_dir.parent.parent / "uap-segment-dashboard" / "src" / "streamlit_app.py",
        Path.cwd() / "uap-segment-dashboard" / "src" / "streamlit_app.py",
    ]
    
    for loc in locations:
        if loc.exists():
            return loc
    
    return None


def run_dashboard():
    """Launch the Streamlit dashboard."""
    dashboard_path = find_dashboard()
    
    if not dashboard_path:
        print("❌ Dashboard not found.")
        print("Install with: pip install uap-protocol[dashboard]")
        return 1
    
    # Load config into environment
    config = get_config()
    if config.get("groq_api_key"):
        os.environ["GROQ_API_KEY"] = config["groq_api_key"]
    if config.get("google_api_key"):
        os.environ["GOOGLE_API_KEY"] = config["google_api_key"]
    
    print("🚀 Starting UAP Dashboard...")
    print(f"   Dashboard: {dashboard_path}")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(dashboard_path),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ])
    except FileNotFoundError:
        print("❌ Streamlit not installed.")
        print("Install with: pip install uap-protocol[dashboard]")
        return 1
    
    return 0


def run_setup():
    """Interactive setup wizard."""
    try:
        from rich.console import Console
        from rich.prompt import Prompt
        from rich.panel import Panel
        console = Console()
        rich_available = True
    except ImportError:
        console = None
        rich_available = False
    
    print("\n" + "=" * 50)
    print("  🔧 UAP Setup Wizard")
    print("=" * 50 + "\n")
    
    config = get_config()
    
    # Choose backend
    print("Choose your LLM backend:\n")
    print("  1. Groq     (Free tier, fast)")
    print("  2. Gemini   (Free tier available)")
    print("  3. Ollama   (Local, free)")
    print("  4. OpenAI   (Paid)")
    print("  5. Claude   (Paid)")
    print()
    
    if rich_available:
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5"], default="1")
    else:
        choice = input("Select [1-5, default=1]: ").strip() or "1"
    
    backends = {
        "1": ("groq", "groq_api_key", "https://console.groq.com/keys"),
        "2": ("gemini", "google_api_key", "https://aistudio.google.com/app/apikey"),
        "3": ("ollama", None, "https://ollama.ai"),
        "4": ("openai", "openai_api_key", "https://platform.openai.com/api-keys"),
        "5": ("anthropic", "anthropic_api_key", "https://console.anthropic.com/"),
    }
    
    backend, key_name, url = backends[choice]
    config["default_backend"] = backend
    
    if key_name:
        print(f"\nGet your API key from: {url}")
        if rich_available:
            api_key = Prompt.ask("Enter API key", password=True)
        else:
            api_key = input("Enter API key: ").strip()
        
        if api_key:
            config[key_name] = api_key
            print("✅ API key saved")
    else:
        print(f"\nMake sure Ollama is running: {url}")
    
    save_config(config)
    print(f"\n✅ Configuration saved to {get_uap_home() / 'config.json'}")
    print("\n🎉 Setup complete! Run: uap-run dashboard")
    
    return 0


def run_check():
    """Check dependencies and configuration."""
    print("\n" + "=" * 50)
    print("  🔍 UAP Configuration Check")
    print("=" * 50 + "\n")
    
    # Check dependencies
    deps = {
        "rich": False,
        "groq": False,
        "streamlit": False,
        "google-generativeai": False,
    }
    
    try:
        import rich
        deps["rich"] = True
    except ImportError:
        pass
    
    try:
        import groq
        deps["groq"] = True
    except ImportError:
        pass
    
    try:
        import streamlit
        deps["streamlit"] = True
    except ImportError:
        pass
    
    try:
        import google.generativeai
        deps["google-generativeai"] = True
    except ImportError:
        pass
    
    print("📦 Dependencies:")
    for pkg, installed in deps.items():
        status = "✅" if installed else "❌"
        print(f"   {status} {pkg}")
    
    # Check API keys
    config = get_config()
    print("\n🔑 API Keys:")
    
    keys = [
        ("GROQ_API_KEY", config.get("groq_api_key") or os.getenv("GROQ_API_KEY")),
        ("GOOGLE_API_KEY", config.get("google_api_key") or os.getenv("GOOGLE_API_KEY")),
        ("OPENAI_API_KEY", config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")),
    ]
    
    for name, value in keys:
        status = "✅" if value else "⚪"
        print(f"   {status} {name}")
    
    # Check dashboard
    print("\n📊 Dashboard:")
    dashboard = find_dashboard()
    if dashboard:
        print(f"   ✅ Found at {dashboard}")
    else:
        print("   ❌ Not found")
    
    print()
    return 0


def run_test():
    """Run a quick test."""
    print("\n🧪 Running UAP Test...\n")
    
    config = get_config()
    
    # Set env vars from config
    if config.get("groq_api_key"):
        os.environ["GROQ_API_KEY"] = config["groq_api_key"]
    
    try:
        # Try importing from package
        try:
            from uap.protocol import StateManager
        except ImportError:
            # Fallback to relative import
            pkg_dir = Path(__file__).parent
            sys.path.insert(0, str(pkg_dir.parent.parent))
            from protocol import StateManager
        
        print("✅ Protocol module loaded")
        
        sm = StateManager()
        print("✅ StateManager created")
        
        session = sm.create_session("Test session")
        print(f"✅ Session created: {session.session_id}")
        
        print("\n✅ All tests passed!")
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1


def show_menu():
    """Show interactive menu."""
    print("\n" + "=" * 50)
    print("  🚀 UAP - Universal Agent Protocol")
    print("=" * 50)
    print("\n  What would you like to do?\n")
    print("  1. 📊 Launch Dashboard")
    print("  2. 💬 Start Chat CLI")
    print("  3. 🧪 Run Test")
    print("  4. 🔍 Check Configuration")
    print("  5. 🔧 Setup Wizard")
    print("  6. 🚪 Exit")
    print()
    
    choice = input("  Select [1-6]: ").strip()
    
    if choice == "1":
        return run_dashboard()
    elif choice == "2":
        try:
            from uap.cli import app
            app()
        except ImportError:
            print("CLI not available. Run: pip install uap-protocol")
        return 0
    elif choice == "3":
        return run_test()
    elif choice == "4":
        return run_check()
    elif choice == "5":
        return run_setup()
    elif choice == "6":
        print("Goodbye!")
        return 0
    else:
        print("Invalid choice")
        return 1


def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    if not args:
        return show_menu()
    
    cmd = args[0].lower()
    
    if cmd in ["dashboard", "ui", "web"]:
        return run_dashboard()
    elif cmd in ["chat", "cli"]:
        try:
            from uap.cli import app
            app()
        except ImportError:
            print("CLI not available")
        return 0
    elif cmd in ["test"]:
        return run_test()
    elif cmd in ["--setup", "setup"]:
        return run_setup()
    elif cmd in ["--check", "check"]:
        return run_check()
    elif cmd in ["--help", "-h", "help"]:
        print(__doc__)
        return 0
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'uap-run --help' for usage")
        return 1


if __name__ == "__main__":
    sys.exit(main())
