"""HumanEval task HumanEval_34"""
from pathlib import Path

TASK = """Implement the function 'unique' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def unique(l: list):
    \"\"\"Return sorted unique elements in a list
    >>> unique([5, 3, 5, 2, 3, 3, 9, 0, 123])
    [0, 2, 3, 5, 9, 123]
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef unique(l: list):\n    """Return sorted unique elements in a list\n    >>> unique([5, 3, 5, 2, 3, 3, 9, 0, 123])\n    [0, 2, 3, 5, 9, 123]\n    """\n',
    "test_solution.py": 'from solution import unique\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([5, 3, 5, 2, 3, 3, 9, 0, 123]) == [0, 2, 3, 5, 9, 123]\n\n\n\ndef test_candidate():\n    check(unique)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import unique\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([5, 3, 5, 2, 3, 3, 9, 0, 123]) == [0, 2, 3, 5, 9, 123]\n\n\n\ndef test_candidate():\n    check(unique)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
