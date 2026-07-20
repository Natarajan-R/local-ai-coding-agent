"""HumanEval task HumanEval_146"""
from pathlib import Path

TASK = """Implement the function 'specialFilter' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def specialFilter(nums):
    \"\"\"Write a function that takes an array of numbers as input and returns 
    the number of elements in the array that are greater than 10 and both 
    first and last digits of a number are odd (1, 3, 5, 7, 9).
    For example:
    specialFilter([15, -73, 14, -15]) => 1 
    specialFilter([33, -2, -3, 45, 21, 109]) => 2
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef specialFilter(nums):\n    """Write a function that takes an array of numbers as input and returns \n    the number of elements in the array that are greater than 10 and both \n    first and last digits of a number are odd (1, 3, 5, 7, 9).\n    For example:\n    specialFilter([15, -73, 14, -15]) => 1 \n    specialFilter([33, -2, -3, 45, 21, 109]) => 2\n    """\n',
    "test_solution.py": 'from solution import specialFilter\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([5, -2, 1, -5]) == 0  \n    assert candidate([15, -73, 14, -15]) == 1\n    assert candidate([33, -2, -3, 45, 21, 109]) == 2\n    assert candidate([43, -12, 93, 125, 121, 109]) == 4\n    assert candidate([71, -2, -33, 75, 21, 19]) == 3\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1]) == 0              \n    assert candidate([]) == 0                   \n\n\n\ndef test_candidate():\n    check(specialFilter)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import specialFilter\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([5, -2, 1, -5]) == 0  \n    assert candidate([15, -73, 14, -15]) == 1\n    assert candidate([33, -2, -3, 45, 21, 109]) == 2\n    assert candidate([43, -12, 93, 125, 121, 109]) == 4\n    assert candidate([71, -2, -33, 75, 21, 19]) == 3\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1]) == 0              \n    assert candidate([]) == 0                   \n\n\n\ndef test_candidate():\n    check(specialFilter)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
