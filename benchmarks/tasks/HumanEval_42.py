"""HumanEval task HumanEval_42"""
from pathlib import Path

TASK = """Implement the function 'incr_list' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def incr_list(l: list):
    \"\"\"Return list with elements incremented by 1.
    >>> incr_list([1, 2, 3])
    [2, 3, 4]
    >>> incr_list([5, 3, 5, 2, 3, 3, 9, 0, 123])
    [6, 4, 6, 3, 4, 4, 10, 1, 124]
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef incr_list(l: list):\n    """Return list with elements incremented by 1.\n    >>> incr_list([1, 2, 3])\n    [2, 3, 4]\n    >>> incr_list([5, 3, 5, 2, 3, 3, 9, 0, 123])\n    [6, 4, 6, 3, 4, 4, 10, 1, 124]\n    """\n',
    "test_solution.py": 'from solution import incr_list\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([]) == []\n    assert candidate([3, 2, 1]) == [4, 3, 2]\n    assert candidate([5, 2, 5, 2, 3, 3, 9, 0, 123]) == [6, 3, 6, 3, 4, 4, 10, 1, 124]\n\n\n\ndef test_candidate():\n    check(incr_list)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import incr_list\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([]) == []\n    assert candidate([3, 2, 1]) == [4, 3, 2]\n    assert candidate([5, 2, 5, 2, 3, 3, 9, 0, 123]) == [6, 3, 6, 3, 4, 4, 10, 1, 124]\n\n\n\ndef test_candidate():\n    check(incr_list)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
