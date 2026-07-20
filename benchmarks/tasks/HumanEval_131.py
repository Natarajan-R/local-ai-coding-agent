"""HumanEval task HumanEval_131"""
from pathlib import Path

TASK = """Implement the function 'digits' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def digits(n):
    \"\"\"Given a positive integer n, return the product of the odd digits.
    Return 0 if all digits are even.
    For example:
    digits(1)  == 1
    digits(4)  == 0
    digits(235) == 15
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef digits(n):\n    """Given a positive integer n, return the product of the odd digits.\n    Return 0 if all digits are even.\n    For example:\n    digits(1)  == 1\n    digits(4)  == 0\n    digits(235) == 15\n    """\n',
    "test_solution.py": 'from solution import digits\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(5) == 5\n    assert candidate(54) == 5\n    assert candidate(120) ==1\n    assert candidate(5014) == 5\n    assert candidate(98765) == 315\n    assert candidate(5576543) == 2625\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(2468) == 0\n\n\n\ndef test_candidate():\n    check(digits)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import digits\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(5) == 5\n    assert candidate(54) == 5\n    assert candidate(120) ==1\n    assert candidate(5014) == 5\n    assert candidate(98765) == 315\n    assert candidate(5576543) == 2625\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(2468) == 0\n\n\n\ndef test_candidate():\n    check(digits)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
