"""HumanEval task HumanEval_35"""
from pathlib import Path

TASK = """Implement the function 'max_element' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def max_element(l: list):
    \"\"\"Return maximum element in the list.
    >>> max_element([1, 2, 3])
    3
    >>> max_element([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])
    123
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef max_element(l: list):\n    """Return maximum element in the list.\n    >>> max_element([1, 2, 3])\n    3\n    >>> max_element([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])\n    123\n    """\n',
    "test_solution.py": 'from solution import max_element\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 2, 3]) == 3\n    assert candidate([5, 3, -5, 2, -3, 3, 9, 0, 124, 1, -10]) == 124\n\n\ndef test_candidate():\n    check(max_element)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import max_element\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 2, 3]) == 3\n    assert candidate([5, 3, -5, 2, -3, 3, 9, 0, 124, 1, -10]) == 124\n\n\ndef test_candidate():\n    check(max_element)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
