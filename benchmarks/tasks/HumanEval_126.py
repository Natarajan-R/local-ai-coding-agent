"""HumanEval task HumanEval_126"""
from pathlib import Path

TASK = """Implement the function 'is_sorted' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def is_sorted(lst):
    '''
    Given a list of numbers, return whether or not they are sorted
    in ascending order. If list has more than 1 duplicate of the same
    number, return False. Assume no negative numbers and only integers.

    Examples
    is_sorted([5]) ➞ True
    is_sorted([1, 2, 3, 4, 5]) ➞ True
    is_sorted([1, 3, 2, 4, 5]) ➞ False
    is_sorted([1, 2, 3, 4, 5, 6]) ➞ True
    is_sorted([1, 2, 3, 4, 5, 6, 7]) ➞ True
    is_sorted([1, 3, 2, 4, 5, 6, 7]) ➞ False
    is_sorted([1, 2, 2, 3, 3, 4]) ➞ True
    is_sorted([1, 2, 2, 2, 3, 4]) ➞ False
    '''

"""

FILES = {
    "solution.py": "\ndef is_sorted(lst):\n    '''\n    Given a list of numbers, return whether or not they are sorted\n    in ascending order. If list has more than 1 duplicate of the same\n    number, return False. Assume no negative numbers and only integers.\n\n    Examples\n    is_sorted([5]) ➞ True\n    is_sorted([1, 2, 3, 4, 5]) ➞ True\n    is_sorted([1, 3, 2, 4, 5]) ➞ False\n    is_sorted([1, 2, 3, 4, 5, 6]) ➞ True\n    is_sorted([1, 2, 3, 4, 5, 6, 7]) ➞ True\n    is_sorted([1, 3, 2, 4, 5, 6, 7]) ➞ False\n    is_sorted([1, 2, 2, 3, 3, 4]) ➞ True\n    is_sorted([1, 2, 2, 2, 3, 4]) ➞ False\n    '''\n",
    "test_solution.py": 'from solution import is_sorted\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([5]) == True\n    assert candidate([1, 2, 3, 4, 5]) == True\n    assert candidate([1, 3, 2, 4, 5]) == False\n    assert candidate([1, 2, 3, 4, 5, 6]) == True\n    assert candidate([1, 2, 3, 4, 5, 6, 7]) == True\n    assert candidate([1, 3, 2, 4, 5, 6, 7]) == False, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([]) == True, "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate([1]) == True, "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate([3, 2, 1]) == False, "This prints if this assert fails 4 (good for debugging!)"\n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 2, 2, 3, 4]) == False, "This prints if this assert fails 5 (good for debugging!)"\n    assert candidate([1, 2, 3, 3, 3, 4]) == False, "This prints if this assert fails 6 (good for debugging!)"\n    assert candidate([1, 2, 2, 3, 3, 4]) == True, "This prints if this assert fails 7 (good for debugging!)"\n    assert candidate([1, 2, 3, 4]) == True, "This prints if this assert fails 8 (good for debugging!)"\n\n\n\ndef test_candidate():\n    check(is_sorted)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import is_sorted\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([5]) == True\n    assert candidate([1, 2, 3, 4, 5]) == True\n    assert candidate([1, 3, 2, 4, 5]) == False\n    assert candidate([1, 2, 3, 4, 5, 6]) == True\n    assert candidate([1, 2, 3, 4, 5, 6, 7]) == True\n    assert candidate([1, 3, 2, 4, 5, 6, 7]) == False, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([]) == True, "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate([1]) == True, "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate([3, 2, 1]) == False, "This prints if this assert fails 4 (good for debugging!)"\n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 2, 2, 3, 4]) == False, "This prints if this assert fails 5 (good for debugging!)"\n    assert candidate([1, 2, 3, 3, 3, 4]) == False, "This prints if this assert fails 6 (good for debugging!)"\n    assert candidate([1, 2, 2, 3, 3, 4]) == True, "This prints if this assert fails 7 (good for debugging!)"\n    assert candidate([1, 2, 3, 4]) == True, "This prints if this assert fails 8 (good for debugging!)"\n\n\n\ndef test_candidate():\n    check(is_sorted)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
