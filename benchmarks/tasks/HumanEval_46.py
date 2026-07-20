"""HumanEval task HumanEval_46"""
from pathlib import Path

TASK = """Implement the function 'fib4' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def fib4(n: int):
    \"\"\"The Fib4 number sequence is a sequence similar to the Fibbonacci sequnece that's defined as follows:
    fib4(0) -> 0
    fib4(1) -> 0
    fib4(2) -> 2
    fib4(3) -> 0
    fib4(n) -> fib4(n-1) + fib4(n-2) + fib4(n-3) + fib4(n-4).
    Please write a function to efficiently compute the n-th element of the fib4 number sequence.  Do not use recursion.
    >>> fib4(5)
    4
    >>> fib4(6)
    8
    >>> fib4(7)
    14
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef fib4(n: int):\n    """The Fib4 number sequence is a sequence similar to the Fibbonacci sequnece that\'s defined as follows:\n    fib4(0) -> 0\n    fib4(1) -> 0\n    fib4(2) -> 2\n    fib4(3) -> 0\n    fib4(n) -> fib4(n-1) + fib4(n-2) + fib4(n-3) + fib4(n-4).\n    Please write a function to efficiently compute the n-th element of the fib4 number sequence.  Do not use recursion.\n    >>> fib4(5)\n    4\n    >>> fib4(6)\n    8\n    >>> fib4(7)\n    14\n    """\n',
    "test_solution.py": 'from solution import fib4\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(5) == 4\n    assert candidate(8) == 28\n    assert candidate(10) == 104\n    assert candidate(12) == 386\n\n\n\ndef test_candidate():\n    check(fib4)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import fib4\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(5) == 4\n    assert candidate(8) == 28\n    assert candidate(10) == 104\n    assert candidate(12) == 386\n\n\n\ndef test_candidate():\n    check(fib4)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
