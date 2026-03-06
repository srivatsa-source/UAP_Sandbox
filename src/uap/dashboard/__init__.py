"""
UAP Dashboard - Streamlit-based console for the Universal Agent Protocol.
"""


def main():
    """Entry point for `uap-dashboard` command."""
    import subprocess
    import sys
    from pathlib import Path

    app_path = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)
