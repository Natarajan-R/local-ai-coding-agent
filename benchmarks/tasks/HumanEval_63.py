"""HumanEval task HumanEval_63"""
from pathlib import Path

TASK = """Implement the function 'fibfib' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def fibfib(n: int):
    \"\"\"The FibFib number sequence is a sequence similar to the Fibbonacci sequnece that's defined as follows:
    fibfib(0) == 0
    fibfib(1) == 0
    fibfib(2) == 1
    fibfib(n) == fibfib(n-1) + fibfib(n-2) + fibfib(n-3).
    Please write a function to efficiently compute the n-th element of the fibfib number sequence.
    >>> fibfib(1)
    0
    >>> fibfib(5)
    4
    >>> fibfib(8)
    24
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef fibfib(n: int):\n    """The FibFib number sequence is a sequence similar to the Fibbonacci sequnece that\'s defined as follows:\n    fibfib(0) == 0\n    fibfib(1) == 0\n    fibfib(2) == 1\n    fibfib(n) == fibfib(n-1) + fibfib(n-2) + fibfib(n-3).\n    Please write a function to efficiently compute the n-th element of the fibfib number sequence.\n    >>> fibfib(1)\n    0\n    >>> fibfib(5)\n    4\n    >>> fibfib(8)\n    24\n    """\n',
    "test_solution.py": 'from solution import fibfib\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(2) == 1\n    assert candidate(1) == 0\n    assert candidate(5) == 4\n    assert candidate(8) == 24\n    assert candidate(10) == 81\n    assert candidate(12) == 274\n    assert candidate(14) == 927\n\n\n\ndef test_candidate():\n    check(fibfib)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import fibfib\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(2) == 1\n    assert candidate(1) == 0\n    assert candidate(5) == 4\n    assert candidate(8) == 24\n    assert candidate(10) == 81\n    assert candidate(12) == 274\n    assert candidate(14) == 927\n\n\n\ndef test_candidate():\n    check(fibfib)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
