"""HumanEval task HumanEval_30"""
from pathlib import Path

TASK = """Implement the function 'get_positive' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def get_positive(l: list):
    \"\"\"Return only positive numbers in the list.
    >>> get_positive([-1, 2, -4, 5, 6])
    [2, 5, 6]
    >>> get_positive([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])
    [5, 3, 2, 3, 9, 123, 1]
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef get_positive(l: list):\n    """Return only positive numbers in the list.\n    >>> get_positive([-1, 2, -4, 5, 6])\n    [2, 5, 6]\n    >>> get_positive([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])\n    [5, 3, 2, 3, 9, 123, 1]\n    """\n',
    "test_solution.py": 'from solution import get_positive\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([-1, -2, 4, 5, 6]) == [4, 5, 6]\n    assert candidate([5, 3, -5, 2, 3, 3, 9, 0, 123, 1, -10]) == [5, 3, 2, 3, 3, 9, 123, 1]\n    assert candidate([-1, -2]) == []\n    assert candidate([]) == []\n\n\n\ndef test_candidate():\n    check(get_positive)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import get_positive\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([-1, -2, 4, 5, 6]) == [4, 5, 6]\n    assert candidate([5, 3, -5, 2, 3, 3, 9, 0, 123, 1, -10]) == [5, 3, 2, 3, 3, 9, 123, 1]\n    assert candidate([-1, -2]) == []\n    assert candidate([]) == []\n\n\n\ndef test_candidate():\n    check(get_positive)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
