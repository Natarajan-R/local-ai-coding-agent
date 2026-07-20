"""HumanEval task HumanEval_75"""
from pathlib import Path

TASK = """Implement the function 'is_multiply_prime' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def is_multiply_prime(a):
    \"\"\"Write a function that returns true if the given number is the multiplication of 3 prime numbers
    and false otherwise.
    Knowing that (a) is less then 100. 
    Example:
    is_multiply_prime(30) == True
    30 = 2 * 3 * 5
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef is_multiply_prime(a):\n    """Write a function that returns true if the given number is the multiplication of 3 prime numbers\n    and false otherwise.\n    Knowing that (a) is less then 100. \n    Example:\n    is_multiply_prime(30) == True\n    30 = 2 * 3 * 5\n    """\n',
    "test_solution.py": 'from solution import is_multiply_prime\ndef check(candidate):\n\n    assert candidate(5) == False\n    assert candidate(30) == True\n    assert candidate(8) == True\n    assert candidate(10) == False\n    assert candidate(125) == True\n    assert candidate(3 * 5 * 7) == True\n    assert candidate(3 * 6 * 7) == False\n    assert candidate(9 * 9 * 9) == False\n    assert candidate(11 * 9 * 9) == False\n    assert candidate(11 * 13 * 7) == True\n\n\n\ndef test_candidate():\n    check(is_multiply_prime)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import is_multiply_prime\ndef check(candidate):\n\n    assert candidate(5) == False\n    assert candidate(30) == True\n    assert candidate(8) == True\n    assert candidate(10) == False\n    assert candidate(125) == True\n    assert candidate(3 * 5 * 7) == True\n    assert candidate(3 * 6 * 7) == False\n    assert candidate(9 * 9 * 9) == False\n    assert candidate(11 * 9 * 9) == False\n    assert candidate(11 * 13 * 7) == True\n\n\n\ndef test_candidate():\n    check(is_multiply_prime)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
