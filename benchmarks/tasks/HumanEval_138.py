"""HumanEval task HumanEval_138"""
from pathlib import Path

TASK = """Implement the function 'is_equal_to_sum_even' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def is_equal_to_sum_even(n):
    \"\"\"Evaluate whether the given number n can be written as the sum of exactly 4 positive even numbers
    Example
    is_equal_to_sum_even(4) == False
    is_equal_to_sum_even(6) == False
    is_equal_to_sum_even(8) == True
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef is_equal_to_sum_even(n):\n    """Evaluate whether the given number n can be written as the sum of exactly 4 positive even numbers\n    Example\n    is_equal_to_sum_even(4) == False\n    is_equal_to_sum_even(6) == False\n    is_equal_to_sum_even(8) == True\n    """\n',
    "test_solution.py": 'from solution import is_equal_to_sum_even\ndef check(candidate):\n    assert candidate(4) == False\n    assert candidate(6) == False\n    assert candidate(8) == True\n    assert candidate(10) == True\n    assert candidate(11) == False\n    assert candidate(12) == True\n    assert candidate(13) == False\n    assert candidate(16) == True\n\n\ndef test_candidate():\n    check(is_equal_to_sum_even)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import is_equal_to_sum_even\ndef check(candidate):\n    assert candidate(4) == False\n    assert candidate(6) == False\n    assert candidate(8) == True\n    assert candidate(10) == True\n    assert candidate(11) == False\n    assert candidate(12) == True\n    assert candidate(13) == False\n    assert candidate(16) == True\n\n\ndef test_candidate():\n    check(is_equal_to_sum_even)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
