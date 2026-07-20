"""HumanEval task HumanEval_55"""
from pathlib import Path

TASK = """Implement the function 'fib' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def fib(n: int):
    \"\"\"Return n-th Fibonacci number.
    >>> fib(10)
    55
    >>> fib(1)
    1
    >>> fib(8)
    21
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef fib(n: int):\n    """Return n-th Fibonacci number.\n    >>> fib(10)\n    55\n    >>> fib(1)\n    1\n    >>> fib(8)\n    21\n    """\n',
    "test_solution.py": 'from solution import fib\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(10) == 55\n    assert candidate(1) == 1\n    assert candidate(8) == 21\n    assert candidate(11) == 89\n    assert candidate(12) == 144\n\n\n\ndef test_candidate():\n    check(fib)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import fib\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(10) == 55\n    assert candidate(1) == 1\n    assert candidate(8) == 21\n    assert candidate(11) == 89\n    assert candidate(12) == 144\n\n\n\ndef test_candidate():\n    check(fib)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
