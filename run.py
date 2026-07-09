#!/usr/bin/env python3
"""Convenience entry point so you can run the agent without installing it.

Usage:
    python run.py run "Create a hello world script"
    python run.py bench
"""
import sys
from pathlib import Path

# Make ``src`` importable when running from a checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agent.cli.main import app  # noqa: E402

if __name__ == "__main__":
    app()
