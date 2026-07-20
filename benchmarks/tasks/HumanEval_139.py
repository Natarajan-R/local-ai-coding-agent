"""HumanEval task HumanEval_139"""
from pathlib import Path

TASK = """Implement the function 'special_factorial' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def special_factorial(n):
    \"\"\"The Brazilian factorial is defined as:
    brazilian_factorial(n) = n! * (n-1)! * (n-2)! * ... * 1!
    where n > 0

    For example:
    >>> special_factorial(4)
    288

    The function will receive an integer as input and should return the special
    factorial of this integer.
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef special_factorial(n):\n    """The Brazilian factorial is defined as:\n    brazilian_factorial(n) = n! * (n-1)! * (n-2)! * ... * 1!\n    where n > 0\n\n    For example:\n    >>> special_factorial(4)\n    288\n\n    The function will receive an integer as input and should return the special\n    factorial of this integer.\n    """\n',
    "test_solution.py": 'from solution import special_factorial\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(4) == 288, "Test 4"\n    assert candidate(5) == 34560, "Test 5"\n    assert candidate(7) == 125411328000, "Test 7"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1) == 1, "Test 1"\n\n\n\ndef test_candidate():\n    check(special_factorial)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import special_factorial\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(4) == 288, "Test 4"\n    assert candidate(5) == 34560, "Test 5"\n    assert candidate(7) == 125411328000, "Test 7"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1) == 1, "Test 1"\n\n\n\ndef test_candidate():\n    check(special_factorial)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
