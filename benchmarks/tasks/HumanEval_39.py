"""HumanEval task HumanEval_39"""
from pathlib import Path

TASK = """Implement the function 'prime_fib' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def prime_fib(n: int):
    \"\"\"
    prime_fib returns n-th number that is a Fibonacci number and it's also prime.
    >>> prime_fib(1)
    2
    >>> prime_fib(2)
    3
    >>> prime_fib(3)
    5
    >>> prime_fib(4)
    13
    >>> prime_fib(5)
    89
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef prime_fib(n: int):\n    """\n    prime_fib returns n-th number that is a Fibonacci number and it\'s also prime.\n    >>> prime_fib(1)\n    2\n    >>> prime_fib(2)\n    3\n    >>> prime_fib(3)\n    5\n    >>> prime_fib(4)\n    13\n    >>> prime_fib(5)\n    89\n    """\n',
    "test_solution.py": 'from solution import prime_fib\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(1) == 2\n    assert candidate(2) == 3\n    assert candidate(3) == 5\n    assert candidate(4) == 13\n    assert candidate(5) == 89\n    assert candidate(6) == 233\n    assert candidate(7) == 1597\n    assert candidate(8) == 28657\n    assert candidate(9) == 514229\n    assert candidate(10) == 433494437\n\n\n\ndef test_candidate():\n    check(prime_fib)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import prime_fib\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(1) == 2\n    assert candidate(2) == 3\n    assert candidate(3) == 5\n    assert candidate(4) == 13\n    assert candidate(5) == 89\n    assert candidate(6) == 233\n    assert candidate(7) == 1597\n    assert candidate(8) == 28657\n    assert candidate(9) == 514229\n    assert candidate(10) == 433494437\n\n\n\ndef test_candidate():\n    check(prime_fib)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
