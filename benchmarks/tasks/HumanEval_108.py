"""HumanEval task HumanEval_108"""
from pathlib import Path

TASK = """Implement the function 'count_nums' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def count_nums(arr):
    \"\"\"
    Write a function count_nums which takes an array of integers and returns
    the number of elements which has a sum of digits > 0.
    If a number is negative, then its first signed digit will be negative:
    e.g. -123 has signed digits -1, 2, and 3.
    >>> count_nums([]) == 0
    >>> count_nums([-1, 11, -11]) == 1
    >>> count_nums([1, 1, 2]) == 3
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef count_nums(arr):\n    """\n    Write a function count_nums which takes an array of integers and returns\n    the number of elements which has a sum of digits > 0.\n    If a number is negative, then its first signed digit will be negative:\n    e.g. -123 has signed digits -1, 2, and 3.\n    >>> count_nums([]) == 0\n    >>> count_nums([-1, 11, -11]) == 1\n    >>> count_nums([1, 1, 2]) == 3\n    """\n',
    "test_solution.py": 'from solution import count_nums\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([]) == 0\n    assert candidate([-1, -2, 0]) == 0\n    assert candidate([1, 1, 2, -2, 3, 4, 5]) == 6\n    assert candidate([1, 6, 9, -6, 0, 1, 5]) == 5\n    assert candidate([1, 100, 98, -7, 1, -1]) == 4\n    assert candidate([12, 23, 34, -45, -56, 0]) == 5\n    assert candidate([-0, 1**0]) == 1\n    assert candidate([1]) == 1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(count_nums)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import count_nums\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([]) == 0\n    assert candidate([-1, -2, 0]) == 0\n    assert candidate([1, 1, 2, -2, 3, 4, 5]) == 6\n    assert candidate([1, 6, 9, -6, 0, 1, 5]) == 5\n    assert candidate([1, 100, 98, -7, 1, -1]) == 4\n    assert candidate([12, 23, 34, -45, -56, 0]) == 5\n    assert candidate([-0, 1**0]) == 1\n    assert candidate([1]) == 1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(count_nums)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
