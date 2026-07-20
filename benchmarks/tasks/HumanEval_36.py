"""HumanEval task HumanEval_36"""
from pathlib import Path

TASK = """Implement the function 'fizz_buzz' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def fizz_buzz(n: int):
    \"\"\"Return the number of times the digit 7 appears in integers less than n which are divisible by 11 or 13.
    >>> fizz_buzz(50)
    0
    >>> fizz_buzz(78)
    2
    >>> fizz_buzz(79)
    3
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef fizz_buzz(n: int):\n    """Return the number of times the digit 7 appears in integers less than n which are divisible by 11 or 13.\n    >>> fizz_buzz(50)\n    0\n    >>> fizz_buzz(78)\n    2\n    >>> fizz_buzz(79)\n    3\n    """\n',
    "test_solution.py": 'from solution import fizz_buzz\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(50) == 0\n    assert candidate(78) == 2\n    assert candidate(79) == 3\n    assert candidate(100) == 3\n    assert candidate(200) == 6\n    assert candidate(4000) == 192\n    assert candidate(10000) == 639\n    assert candidate(100000) == 8026\n\n\n\ndef test_candidate():\n    check(fizz_buzz)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import fizz_buzz\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(50) == 0\n    assert candidate(78) == 2\n    assert candidate(79) == 3\n    assert candidate(100) == 3\n    assert candidate(200) == 6\n    assert candidate(4000) == 192\n    assert candidate(10000) == 639\n    assert candidate(100000) == 8026\n\n\n\ndef test_candidate():\n    check(fizz_buzz)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
