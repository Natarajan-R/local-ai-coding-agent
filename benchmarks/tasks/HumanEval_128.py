"""HumanEval task HumanEval_128"""
from pathlib import Path

TASK = """Implement the function 'prod_signs' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def prod_signs(arr):
    \"\"\"
    You are given an array arr of integers and you need to return
    sum of magnitudes of integers multiplied by product of all signs
    of each number in the array, represented by 1, -1 or 0.
    Note: return None for empty arr.

    Example:
    >>> prod_signs([1, 2, 2, -4]) == -9
    >>> prod_signs([0, 1]) == 0
    >>> prod_signs([]) == None
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef prod_signs(arr):\n    """\n    You are given an array arr of integers and you need to return\n    sum of magnitudes of integers multiplied by product of all signs\n    of each number in the array, represented by 1, -1 or 0.\n    Note: return None for empty arr.\n\n    Example:\n    >>> prod_signs([1, 2, 2, -4]) == -9\n    >>> prod_signs([0, 1]) == 0\n    >>> prod_signs([]) == None\n    """\n',
    "test_solution.py": 'from solution import prod_signs\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1, 2, 2, -4]) == -9\n    assert candidate([0, 1]) == 0\n    assert candidate([1, 1, 1, 2, 3, -1, 1]) == -10\n    assert candidate([]) == None\n    assert candidate([2, 4,1, 2, -1, -1, 9]) == 20\n    assert candidate([-1, 1, -1, 1]) == 4\n    assert candidate([-1, 1, 1, 1]) == -4\n    assert candidate([-1, 1, 1, 0]) == 0\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(prod_signs)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import prod_signs\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1, 2, 2, -4]) == -9\n    assert candidate([0, 1]) == 0\n    assert candidate([1, 1, 1, 2, 3, -1, 1]) == -10\n    assert candidate([]) == None\n    assert candidate([2, 4,1, 2, -1, -1, 9]) == 20\n    assert candidate([-1, 1, -1, 1]) == 4\n    assert candidate([-1, 1, 1, 1]) == -4\n    assert candidate([-1, 1, 1, 0]) == 0\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(prod_signs)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
