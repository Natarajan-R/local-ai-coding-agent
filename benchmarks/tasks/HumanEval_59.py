"""HumanEval task HumanEval_59"""
from pathlib import Path

TASK = """Implement the function 'largest_prime_factor' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def largest_prime_factor(n: int):
    \"\"\"Return the largest prime factor of n. Assume n > 1 and is not a prime.
    >>> largest_prime_factor(13195)
    29
    >>> largest_prime_factor(2048)
    2
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef largest_prime_factor(n: int):\n    """Return the largest prime factor of n. Assume n > 1 and is not a prime.\n    >>> largest_prime_factor(13195)\n    29\n    >>> largest_prime_factor(2048)\n    2\n    """\n',
    "test_solution.py": 'from solution import largest_prime_factor\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(15) == 5\n    assert candidate(27) == 3\n    assert candidate(63) == 7\n    assert candidate(330) == 11\n    assert candidate(13195) == 29\n\n\n\ndef test_candidate():\n    check(largest_prime_factor)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import largest_prime_factor\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(15) == 5\n    assert candidate(27) == 3\n    assert candidate(63) == 7\n    assert candidate(330) == 11\n    assert candidate(13195) == 29\n\n\n\ndef test_candidate():\n    check(largest_prime_factor)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
