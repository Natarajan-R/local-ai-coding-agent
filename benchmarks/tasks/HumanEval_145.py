"""HumanEval task HumanEval_145"""
from pathlib import Path

TASK = """Implement the function 'order_by_points' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def order_by_points(nums):
    \"\"\"
    Write a function which sorts the given list of integers
    in ascending order according to the sum of their digits.
    Note: if there are several items with similar sum of their digits,
    order them based on their index in original list.

    For example:
    >>> order_by_points([1, 11, -1, -11, -12]) == [-1, -11, 1, -12, 11]
    >>> order_by_points([]) == []
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef order_by_points(nums):\n    """\n    Write a function which sorts the given list of integers\n    in ascending order according to the sum of their digits.\n    Note: if there are several items with similar sum of their digits,\n    order them based on their index in original list.\n\n    For example:\n    >>> order_by_points([1, 11, -1, -11, -12]) == [-1, -11, 1, -12, 11]\n    >>> order_by_points([]) == []\n    """\n',
    "test_solution.py": 'from solution import order_by_points\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1, 11, -1, -11, -12]) == [-1, -11, 1, -12, 11]\n    assert candidate([1234,423,463,145,2,423,423,53,6,37,3457,3,56,0,46]) == [0, 2, 3, 6, 53, 423, 423, 423, 1234, 145, 37, 46, 56, 463, 3457]\n    assert candidate([]) == []\n    assert candidate([1, -11, -32, 43, 54, -98, 2, -3]) == [-3, -32, -98, -11, 1, 2, 43, 54]\n    assert candidate([1,2,3,4,5,6,7,8,9,10,11]) == [1, 10, 2, 11, 3, 4, 5, 6, 7, 8, 9]\n    assert candidate([0,6,6,-76,-21,23,4]) == [-76, -21, 0, 4, 23, 6, 6]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(order_by_points)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import order_by_points\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1, 11, -1, -11, -12]) == [-1, -11, 1, -12, 11]\n    assert candidate([1234,423,463,145,2,423,423,53,6,37,3457,3,56,0,46]) == [0, 2, 3, 6, 53, 423, 423, 423, 1234, 145, 37, 46, 56, 463, 3457]\n    assert candidate([]) == []\n    assert candidate([1, -11, -32, 43, 54, -98, 2, -3]) == [-3, -32, -98, -11, 1, 2, 43, 54]\n    assert candidate([1,2,3,4,5,6,7,8,9,10,11]) == [1, 10, 2, 11, 3, 4, 5, 6, 7, 8, 9]\n    assert candidate([0,6,6,-76,-21,23,4]) == [-76, -21, 0, 4, 23, 6, 6]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(order_by_points)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
