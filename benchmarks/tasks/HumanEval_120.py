"""HumanEval task HumanEval_120"""
from pathlib import Path

TASK = """Implement the function 'maximum' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def maximum(arr, k):
    \"\"\"
    Given an array arr of integers and a positive integer k, return a sorted list 
    of length k with the maximum k numbers in arr.

    Example 1:

        Input: arr = [-3, -4, 5], k = 3
        Output: [-4, -3, 5]

    Example 2:

        Input: arr = [4, -4, 4], k = 2
        Output: [4, 4]

    Example 3:

        Input: arr = [-3, 2, 1, 2, -1, -2, 1], k = 1
        Output: [2]

    Note:
        1. The length of the array will be in the range of [1, 1000].
        2. The elements in the array will be in the range of [-1000, 1000].
        3. 0 <= k <= len(arr)
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef maximum(arr, k):\n    """\n    Given an array arr of integers and a positive integer k, return a sorted list \n    of length k with the maximum k numbers in arr.\n\n    Example 1:\n\n        Input: arr = [-3, -4, 5], k = 3\n        Output: [-4, -3, 5]\n\n    Example 2:\n\n        Input: arr = [4, -4, 4], k = 2\n        Output: [4, 4]\n\n    Example 3:\n\n        Input: arr = [-3, 2, 1, 2, -1, -2, 1], k = 1\n        Output: [2]\n\n    Note:\n        1. The length of the array will be in the range of [1, 1000].\n        2. The elements in the array will be in the range of [-1000, 1000].\n        3. 0 <= k <= len(arr)\n    """\n',
    "test_solution.py": 'from solution import maximum\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([-3, -4, 5], 3) == [-4, -3, 5]\n    assert candidate([4, -4, 4], 2) == [4, 4]\n    assert candidate([-3, 2, 1, 2, -1, -2, 1], 1) == [2]\n    assert candidate([123, -123, 20, 0 , 1, 2, -3], 3) == [2, 20, 123]\n    assert candidate([-123, 20, 0 , 1, 2, -3], 4) == [0, 1, 2, 20]\n    assert candidate([5, 15, 0, 3, -13, -8, 0], 7) == [-13, -8, 0, 0, 3, 5, 15]\n    assert candidate([-1, 0, 2, 5, 3, -10], 2) == [3, 5]\n    assert candidate([1, 0, 5, -7], 1) == [5]\n    assert candidate([4, -4], 2) == [-4, 4]\n    assert candidate([-10, 10], 2) == [-10, 10]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 3, -23, 243, -400, 0], 0) == []\n\n\n\ndef test_candidate():\n    check(maximum)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import maximum\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([-3, -4, 5], 3) == [-4, -3, 5]\n    assert candidate([4, -4, 4], 2) == [4, 4]\n    assert candidate([-3, 2, 1, 2, -1, -2, 1], 1) == [2]\n    assert candidate([123, -123, 20, 0 , 1, 2, -3], 3) == [2, 20, 123]\n    assert candidate([-123, 20, 0 , 1, 2, -3], 4) == [0, 1, 2, 20]\n    assert candidate([5, 15, 0, 3, -13, -8, 0], 7) == [-13, -8, 0, 0, 3, 5, 15]\n    assert candidate([-1, 0, 2, 5, 3, -10], 2) == [3, 5]\n    assert candidate([1, 0, 5, -7], 1) == [5]\n    assert candidate([4, -4], 2) == [-4, 4]\n    assert candidate([-10, 10], 2) == [-10, 10]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 3, -23, 243, -400, 0], 0) == []\n\n\n\ndef test_candidate():\n    check(maximum)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
