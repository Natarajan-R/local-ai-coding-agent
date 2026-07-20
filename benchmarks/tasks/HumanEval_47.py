"""HumanEval task HumanEval_47"""
from pathlib import Path

TASK = """Implement the function 'median' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def median(l: list):
    \"\"\"Return median of elements in the list l.
    >>> median([3, 1, 2, 4, 5])
    3
    >>> median([-10, 4, 6, 1000, 10, 20])
    15.0
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef median(l: list):\n    """Return median of elements in the list l.\n    >>> median([3, 1, 2, 4, 5])\n    3\n    >>> median([-10, 4, 6, 1000, 10, 20])\n    15.0\n    """\n',
    "test_solution.py": 'from solution import median\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([3, 1, 2, 4, 5]) == 3\n    assert candidate([-10, 4, 6, 1000, 10, 20]) == 8.0\n    assert candidate([5]) == 5\n    assert candidate([6, 5]) == 5.5\n    assert candidate([8, 1, 3, 9, 9, 2, 7]) == 7 \n\n\n\ndef test_candidate():\n    check(median)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import median\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([3, 1, 2, 4, 5]) == 3\n    assert candidate([-10, 4, 6, 1000, 10, 20]) == 8.0\n    assert candidate([5]) == 5\n    assert candidate([6, 5]) == 5.5\n    assert candidate([8, 1, 3, 9, 9, 2, 7]) == 7 \n\n\n\ndef test_candidate():\n    check(median)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
