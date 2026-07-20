"""HumanEval task HumanEval_45"""
from pathlib import Path

TASK = """Implement the function 'triangle_area' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def triangle_area(a, h):
    \"\"\"Given length of a side and high return area for a triangle.
    >>> triangle_area(5, 3)
    7.5
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef triangle_area(a, h):\n    """Given length of a side and high return area for a triangle.\n    >>> triangle_area(5, 3)\n    7.5\n    """\n',
    "test_solution.py": 'from solution import triangle_area\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(5, 3) == 7.5\n    assert candidate(2, 2) == 2.0\n    assert candidate(10, 8) == 40.0\n\n\n\ndef test_candidate():\n    check(triangle_area)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import triangle_area\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(5, 3) == 7.5\n    assert candidate(2, 2) == 2.0\n    assert candidate(10, 8) == 40.0\n\n\n\ndef test_candidate():\n    check(triangle_area)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
