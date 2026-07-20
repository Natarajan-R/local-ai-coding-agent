"""HumanEval task HumanEval_49"""
from pathlib import Path

TASK = """Implement the function 'modp' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def modp(n: int, p: int):
    \"\"\"Return 2^n modulo p (be aware of numerics).
    >>> modp(3, 5)
    3
    >>> modp(1101, 101)
    2
    >>> modp(0, 101)
    1
    >>> modp(3, 11)
    8
    >>> modp(100, 101)
    1
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef modp(n: int, p: int):\n    """Return 2^n modulo p (be aware of numerics).\n    >>> modp(3, 5)\n    3\n    >>> modp(1101, 101)\n    2\n    >>> modp(0, 101)\n    1\n    >>> modp(3, 11)\n    8\n    >>> modp(100, 101)\n    1\n    """\n',
    "test_solution.py": 'from solution import modp\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(3, 5) == 3\n    assert candidate(1101, 101) == 2\n    assert candidate(0, 101) == 1\n    assert candidate(3, 11) == 8\n    assert candidate(100, 101) == 1\n    assert candidate(30, 5) == 4\n    assert candidate(31, 5) == 3\n\n\n\ndef test_candidate():\n    check(modp)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import modp\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(3, 5) == 3\n    assert candidate(1101, 101) == 2\n    assert candidate(0, 101) == 1\n    assert candidate(3, 11) == 8\n    assert candidate(100, 101) == 1\n    assert candidate(30, 5) == 4\n    assert candidate(31, 5) == 3\n\n\n\ndef test_candidate():\n    check(modp)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
