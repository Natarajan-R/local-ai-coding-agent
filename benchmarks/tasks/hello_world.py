"""Benchmark task: create a hello-world script from scratch."""
from pathlib import Path

TASK = "Create a file named hello.py that prints exactly: Hello, World!"

# Initial files to seed into the workspace before the agent runs.
FILES: dict[str, str] = {}


def check(workspace: Path) -> bool:
    """Return True if the task was solved correctly."""
    import subprocess

    target = workspace / "hello.py"
    if not target.exists():
        return False
    result = subprocess.run(
        ["python", str(target)], capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip() == "Hello, World!"
