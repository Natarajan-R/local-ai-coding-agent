"""HumanEval task HumanEval_73"""
from pathlib import Path

TASK = """Implement the function 'smallest_change' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def smallest_change(arr):
    \"\"\"
    Given an array arr of integers, find the minimum number of elements that
    need to be changed to make the array palindromic. A palindromic array is an array that
    is read the same backwards and forwards. In one change, you can change one element to any other element.

    For example:
    smallest_change([1,2,3,5,4,7,9,6]) == 4
    smallest_change([1, 2, 3, 4, 3, 2, 2]) == 1
    smallest_change([1, 2, 3, 2, 1]) == 0
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef smallest_change(arr):\n    """\n    Given an array arr of integers, find the minimum number of elements that\n    need to be changed to make the array palindromic. A palindromic array is an array that\n    is read the same backwards and forwards. In one change, you can change one element to any other element.\n\n    For example:\n    smallest_change([1,2,3,5,4,7,9,6]) == 4\n    smallest_change([1, 2, 3, 4, 3, 2, 2]) == 1\n    smallest_change([1, 2, 3, 2, 1]) == 0\n    """\n',
    "test_solution.py": 'from solution import smallest_change\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,3,5,4,7,9,6]) == 4\n    assert candidate([1, 2, 3, 4, 3, 2, 2]) == 1\n    assert candidate([1, 4, 2]) == 1\n    assert candidate([1, 4, 4, 2]) == 1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 3, 2, 1]) == 0\n    assert candidate([3, 1, 1, 3]) == 0\n    assert candidate([1]) == 0\n    assert candidate([0, 1]) == 1\n\n\n\ndef test_candidate():\n    check(smallest_change)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import smallest_change\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,3,5,4,7,9,6]) == 4\n    assert candidate([1, 2, 3, 4, 3, 2, 2]) == 1\n    assert candidate([1, 4, 2]) == 1\n    assert candidate([1, 4, 4, 2]) == 1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 3, 2, 1]) == 0\n    assert candidate([3, 1, 1, 3]) == 0\n    assert candidate([1]) == 0\n    assert candidate([0, 1]) == 1\n\n\n\ndef test_candidate():\n    check(smallest_change)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
