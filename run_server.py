"""Cross-platform Python Live Server Launcher for CloudGuard AI.
Usage: python run_server.py
"""
import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def main():
    print("=" * 70)
    print("      CloudGuard AI — Intelligent Cloud Cost Platform")
    print("                     LIVE SERVER LAUNCHER")
    print("=" * 70)
    print(f"Working Directory: {PROJECT_ROOT}")

    # Check dependencies
    try:
        import streamlit
        import pandas
        import plotly
    except ImportError as e:
        print(f"\n[ERROR] Missing required library: {e.name}")
        print("Please install requirements using:")
        print("  pip install -r requirements.txt\n")
        sys.exit(1)

    app_path = PROJECT_ROOT / "app.py"
    if not app_path.exists():
        print(f"\n[ERROR] Main entrypoint not found at: {app_path}")
        sys.exit(1)

    # Command to run streamlit
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port=8501",
        "--server.runOnSave=true",
        "--server.headless=false",
        "--browser.gatherUsageStats=false"
    ]

    print("\nStarting live server with hot reloading...")
    print("  Local URL:    http://localhost:8501")
    print("  Live Reload:  Active (auto-updates when files change)")
    print("  Exit:         Press Ctrl+C to terminate\n")
    print("-" * 70)

    try:
        # Run streamlit process
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
    except KeyboardInterrupt:
        print("\n[INFO] CloudGuard AI server stopped cleanly.")
    except Exception as e:
        print(f"\n[ERROR] Server exited with error: {e}")

if __name__ == "__main__":
    main()
