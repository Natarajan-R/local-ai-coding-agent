"""HumanEval task HumanEval_150"""
from pathlib import Path

TASK = """Implement the function 'x_or_y' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def x_or_y(n, x, y):
    \"\"\"A simple program which should return the value of x if n is 
    a prime number and should return the value of y otherwise.

    Examples:
    for x_or_y(7, 34, 12) == 34
    for x_or_y(15, 8, 5) == 5
    
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef x_or_y(n, x, y):\n    """A simple program which should return the value of x if n is \n    a prime number and should return the value of y otherwise.\n\n    Examples:\n    for x_or_y(7, 34, 12) == 34\n    for x_or_y(15, 8, 5) == 5\n    \n    """\n',
    "test_solution.py": 'from solution import x_or_y\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(7, 34, 12) == 34\n    assert candidate(15, 8, 5) == 5\n    assert candidate(3, 33, 5212) == 33\n    assert candidate(1259, 3, 52) == 3\n    assert candidate(7919, -1, 12) == -1\n    assert candidate(3609, 1245, 583) == 583\n    assert candidate(91, 56, 129) == 129\n    assert candidate(6, 34, 1234) == 1234\n    \n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1, 2, 0) == 0\n    assert candidate(2, 2, 0) == 2\n\n\n\ndef test_candidate():\n    check(x_or_y)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import x_or_y\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(7, 34, 12) == 34\n    assert candidate(15, 8, 5) == 5\n    assert candidate(3, 33, 5212) == 33\n    assert candidate(1259, 3, 52) == 3\n    assert candidate(7919, -1, 12) == -1\n    assert candidate(3609, 1245, 583) == 583\n    assert candidate(91, 56, 129) == 129\n    assert candidate(6, 34, 1234) == 1234\n    \n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1, 2, 0) == 0\n    assert candidate(2, 2, 0) == 2\n\n\n\ndef test_candidate():\n    check(x_or_y)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
