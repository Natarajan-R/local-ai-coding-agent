"""HumanEval task HumanEval_116"""
from pathlib import Path

TASK = """Implement the function 'sort_array' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def sort_array(arr):
    \"\"\"
    In this Kata, you have to sort an array of non-negative integers according to
    number of ones in their binary representation in ascending order.
    For similar number of ones, sort based on decimal value.

    It must be implemented like this:
    >>> sort_array([1, 5, 2, 3, 4]) == [1, 2, 3, 4, 5]
    >>> sort_array([-2, -3, -4, -5, -6]) == [-6, -5, -4, -3, -2]
    >>> sort_array([1, 0, 2, 3, 4]) [0, 1, 2, 3, 4]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef sort_array(arr):\n    """\n    In this Kata, you have to sort an array of non-negative integers according to\n    number of ones in their binary representation in ascending order.\n    For similar number of ones, sort based on decimal value.\n\n    It must be implemented like this:\n    >>> sort_array([1, 5, 2, 3, 4]) == [1, 2, 3, 4, 5]\n    >>> sort_array([-2, -3, -4, -5, -6]) == [-6, -5, -4, -3, -2]\n    >>> sort_array([1, 0, 2, 3, 4]) [0, 1, 2, 3, 4]\n    """\n',
    "test_solution.py": 'from solution import sort_array\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,5,2,3,4]) == [1, 2, 4, 3, 5]\n    assert candidate([-2,-3,-4,-5,-6]) == [-4, -2, -6, -5, -3]\n    assert candidate([1,0,2,3,4]) == [0, 1, 2, 4, 3]\n    assert candidate([]) == []\n    assert candidate([2,5,77,4,5,3,5,7,2,3,4]) == [2, 2, 4, 4, 3, 3, 5, 5, 5, 7, 77]\n    assert candidate([3,6,44,12,32,5]) == [32, 3, 5, 6, 12, 44]\n    assert candidate([2,4,8,16,32]) == [2, 4, 8, 16, 32]\n    assert candidate([2,4,8,16,32]) == [2, 4, 8, 16, 32]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(sort_array)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import sort_array\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,5,2,3,4]) == [1, 2, 4, 3, 5]\n    assert candidate([-2,-3,-4,-5,-6]) == [-4, -2, -6, -5, -3]\n    assert candidate([1,0,2,3,4]) == [0, 1, 2, 4, 3]\n    assert candidate([]) == []\n    assert candidate([2,5,77,4,5,3,5,7,2,3,4]) == [2, 2, 4, 4, 3, 3, 5, 5, 5, 7, 77]\n    assert candidate([3,6,44,12,32,5]) == [32, 3, 5, 6, 12, 44]\n    assert candidate([2,4,8,16,32]) == [2, 4, 8, 16, 32]\n    assert candidate([2,4,8,16,32]) == [2, 4, 8, 16, 32]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(sort_array)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
