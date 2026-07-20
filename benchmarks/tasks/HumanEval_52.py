"""HumanEval task HumanEval_52"""
from pathlib import Path

TASK = """Implement the function 'below_threshold' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def below_threshold(l: list, t: int):
    \"\"\"Return True if all numbers in the list l are below threshold t.
    >>> below_threshold([1, 2, 4, 10], 100)
    True
    >>> below_threshold([1, 20, 4, 10], 5)
    False
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef below_threshold(l: list, t: int):\n    """Return True if all numbers in the list l are below threshold t.\n    >>> below_threshold([1, 2, 4, 10], 100)\n    True\n    >>> below_threshold([1, 20, 4, 10], 5)\n    False\n    """\n',
    "test_solution.py": 'from solution import below_threshold\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 2, 4, 10], 100)\n    assert not candidate([1, 20, 4, 10], 5)\n    assert candidate([1, 20, 4, 10], 21)\n    assert candidate([1, 20, 4, 10], 22)\n    assert candidate([1, 8, 4, 10], 11)\n    assert not candidate([1, 8, 4, 10], 10)\n\n\n\ndef test_candidate():\n    check(below_threshold)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import below_threshold\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 2, 4, 10], 100)\n    assert not candidate([1, 20, 4, 10], 5)\n    assert candidate([1, 20, 4, 10], 21)\n    assert candidate([1, 20, 4, 10], 22)\n    assert candidate([1, 8, 4, 10], 11)\n    assert not candidate([1, 8, 4, 10], 10)\n\n\n\ndef test_candidate():\n    check(below_threshold)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
