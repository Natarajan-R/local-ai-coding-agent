"""HumanEval task HumanEval_114"""
from pathlib import Path

TASK = """Implement the function 'minSubArraySum' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def minSubArraySum(nums):
    \"\"\"
    Given an array of integers nums, find the minimum sum of any non-empty sub-array
    of nums.
    Example
    minSubArraySum([2, 3, 4, 1, 2, 4]) == 1
    minSubArraySum([-1, -2, -3]) == -6
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef minSubArraySum(nums):\n    """\n    Given an array of integers nums, find the minimum sum of any non-empty sub-array\n    of nums.\n    Example\n    minSubArraySum([2, 3, 4, 1, 2, 4]) == 1\n    minSubArraySum([-1, -2, -3]) == -6\n    """\n',
    "test_solution.py": 'from solution import minSubArraySum\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([2, 3, 4, 1, 2, 4]) == 1, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-1, -2, -3]) == -6\n    assert candidate([-1, -2, -3, 2, -10]) == -14\n    assert candidate([-9999999999999999]) == -9999999999999999\n    assert candidate([0, 10, 20, 1000000]) == 0\n    assert candidate([-1, -2, -3, 10, -5]) == -6\n    assert candidate([100, -1, -2, -3, 10, -5]) == -6\n    assert candidate([10, 11, 13, 8, 3, 4]) == 3\n    assert candidate([100, -33, 32, -1, 0, -2]) == -33\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([-10]) == -10, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([7]) == 7\n    assert candidate([1, -1]) == -1\n\n\ndef test_candidate():\n    check(minSubArraySum)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import minSubArraySum\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([2, 3, 4, 1, 2, 4]) == 1, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-1, -2, -3]) == -6\n    assert candidate([-1, -2, -3, 2, -10]) == -14\n    assert candidate([-9999999999999999]) == -9999999999999999\n    assert candidate([0, 10, 20, 1000000]) == 0\n    assert candidate([-1, -2, -3, 10, -5]) == -6\n    assert candidate([100, -1, -2, -3, 10, -5]) == -6\n    assert candidate([10, 11, 13, 8, 3, 4]) == 3\n    assert candidate([100, -33, 32, -1, 0, -2]) == -33\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([-10]) == -10, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([7]) == 7\n    assert candidate([1, -1]) == -1\n\n\ndef test_candidate():\n    check(minSubArraySum)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
