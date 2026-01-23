"""
UAP Dashboard Launcher
======================
Launch the UAP Streamlit dashboard from anywhere.
"""

import os
import sys
import subprocess
from pathlib import Path


def find_dashboard() -> Path:
    """Find the dashboard script."""
    pkg_dir = Path(__file__).parent
    
    locations = [
        pkg_dir / "dashboard_app.py",
        pkg_dir.parent.parent / "uap-segment-dashboard" / "src" / "streamlit_app.py",
        Path.cwd() / "uap-segment-dashboard" / "src" / "streamlit_app.py",
    ]
    
    for loc in locations:
        if loc.exists():
            return loc
    
    return None


def main():
    """Launch the UAP Streamlit dashboard."""
    dashboard_path = find_dashboard()
    
    if not dashboard_path:
        print("❌ Dashboard not found.")
        print("\nMake sure you have the dashboard installed:")
        print("  pip install uap-protocol[dashboard]")
        print("\nOr run from the uap-protocol directory.")
        sys.exit(1)
    
    # Load config
    config_file = Path.home() / ".uap" / "config.json"
    if config_file.exists():
        import json
        try:
            config = json.loads(config_file.read_text())
            if config.get("groq_api_key"):
                os.environ["GROQ_API_KEY"] = config["groq_api_key"]
            if config.get("google_api_key"):
                os.environ["GOOGLE_API_KEY"] = config["google_api_key"]
        except:
            pass
    
    print("🚀 Starting UAP Dashboard...")
    print(f"   Location: {dashboard_path}\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(dashboard_path),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ])
    except FileNotFoundError:
        print("❌ Streamlit not installed.")
        print("Install with: pip install streamlit")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
