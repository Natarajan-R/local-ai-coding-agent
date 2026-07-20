"""HumanEval task HumanEval_122"""
from pathlib import Path

TASK = """Implement the function 'add_elements' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def add_elements(arr, k):
    \"\"\"
    Given a non-empty array of integers arr and an integer k, return
    the sum of the elements with at most two digits from the first k elements of arr.

    Example:

        Input: arr = [111,21,3,4000,5,6,7,8,9], k = 4
        Output: 24 # sum of 21 + 3

    Constraints:
        1. 1 <= len(arr) <= 100
        2. 1 <= k <= len(arr)
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef add_elements(arr, k):\n    """\n    Given a non-empty array of integers arr and an integer k, return\n    the sum of the elements with at most two digits from the first k elements of arr.\n\n    Example:\n\n        Input: arr = [111,21,3,4000,5,6,7,8,9], k = 4\n        Output: 24 # sum of 21 + 3\n\n    Constraints:\n        1. 1 <= len(arr) <= 100\n        2. 1 <= k <= len(arr)\n    """\n',
    "test_solution.py": 'from solution import add_elements\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,-2,-3,41,57,76,87,88,99], 3) == -4\n    assert candidate([111,121,3,4000,5,6], 2) == 0\n    assert candidate([11,21,3,90,5,6,7,8,9], 4) == 125\n    assert candidate([111,21,3,4000,5,6,7,8,9], 4) == 24, "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1], 1) == 1, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(add_elements)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import add_elements\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,-2,-3,41,57,76,87,88,99], 3) == -4\n    assert candidate([111,121,3,4000,5,6], 2) == 0\n    assert candidate([11,21,3,90,5,6,7,8,9], 4) == 125\n    assert candidate([111,21,3,4000,5,6,7,8,9], 4) == 24, "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1], 1) == 1, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(add_elements)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
