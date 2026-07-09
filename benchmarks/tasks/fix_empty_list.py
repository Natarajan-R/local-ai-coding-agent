"""Benchmark task: fix a bug so tests pass."""
from pathlib import Path

TASK = (
    "The function `average` in stats.py crashes on an empty list with "
    "ZeroDivisionError. Fix it so it returns 0.0 for an empty list. "
    "Do not change the behaviour for non-empty lists. Make the tests pass."
)

FILES = {
    "stats.py": (
        "def average(values):\n"
        "    return sum(values) / len(values)\n"
    ),
    "test_stats.py": (
        "from stats import average\n\n\n"
        "def test_non_empty():\n"
        "    assert average([2, 4, 6]) == 4\n\n\n"
        "def test_empty():\n"
        "    assert average([]) == 0.0\n"
    ),
}


def check(workspace: Path) -> bool:
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pytest", "-q"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode == 0
