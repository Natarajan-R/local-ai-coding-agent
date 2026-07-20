"""HumanEval task HumanEval_57"""
from pathlib import Path

TASK = """Implement the function 'monotonic' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def monotonic(l: list):
    \"\"\"Return True is list elements are monotonically increasing or decreasing.
    >>> monotonic([1, 2, 4, 20])
    True
    >>> monotonic([1, 20, 4, 10])
    False
    >>> monotonic([4, 1, 0, -10])
    True
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef monotonic(l: list):\n    """Return True is list elements are monotonically increasing or decreasing.\n    >>> monotonic([1, 2, 4, 20])\n    True\n    >>> monotonic([1, 20, 4, 10])\n    False\n    >>> monotonic([4, 1, 0, -10])\n    True\n    """\n',
    "test_solution.py": 'from solution import monotonic\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 2, 4, 10]) == True\n    assert candidate([1, 2, 4, 20]) == True\n    assert candidate([1, 20, 4, 10]) == False\n    assert candidate([4, 1, 0, -10]) == True\n    assert candidate([4, 1, 1, 0]) == True\n    assert candidate([1, 2, 3, 2, 5, 60]) == False\n    assert candidate([1, 2, 3, 4, 5, 60]) == True\n    assert candidate([9, 9, 9, 9]) == True\n\n\n\ndef test_candidate():\n    check(monotonic)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import monotonic\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 2, 4, 10]) == True\n    assert candidate([1, 2, 4, 20]) == True\n    assert candidate([1, 20, 4, 10]) == False\n    assert candidate([4, 1, 0, -10]) == True\n    assert candidate([4, 1, 1, 0]) == True\n    assert candidate([1, 2, 3, 2, 5, 60]) == False\n    assert candidate([1, 2, 3, 4, 5, 60]) == True\n    assert candidate([9, 9, 9, 9]) == True\n\n\n\ndef test_candidate():\n    check(monotonic)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
