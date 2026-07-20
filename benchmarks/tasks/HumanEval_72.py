"""HumanEval task HumanEval_72"""
from pathlib import Path

TASK = """Implement the function 'will_it_fly' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def will_it_fly(q,w):
    '''
    Write a function that returns True if the object q will fly, and False otherwise.
    The object q will fly if it's balanced (it is a palindromic list) and the sum of its elements is less than or equal the maximum possible weight w.

    Example:
    will_it_fly([1, 2], 5) ➞ False 
    # 1+2 is less than the maximum possible weight, but it's unbalanced.

    will_it_fly([3, 2, 3], 1) ➞ False
    # it's balanced, but 3+2+3 is more than the maximum possible weight.

    will_it_fly([3, 2, 3], 9) ➞ True
    # 3+2+3 is less than the maximum possible weight, and it's balanced.

    will_it_fly([3], 5) ➞ True
    # 3 is less than the maximum possible weight, and it's balanced.
    '''

"""

FILES = {
    "solution.py": "\ndef will_it_fly(q,w):\n    '''\n    Write a function that returns True if the object q will fly, and False otherwise.\n    The object q will fly if it's balanced (it is a palindromic list) and the sum of its elements is less than or equal the maximum possible weight w.\n\n    Example:\n    will_it_fly([1, 2], 5) ➞ False \n    # 1+2 is less than the maximum possible weight, but it's unbalanced.\n\n    will_it_fly([3, 2, 3], 1) ➞ False\n    # it's balanced, but 3+2+3 is more than the maximum possible weight.\n\n    will_it_fly([3, 2, 3], 9) ➞ True\n    # 3+2+3 is less than the maximum possible weight, and it's balanced.\n\n    will_it_fly([3], 5) ➞ True\n    # 3 is less than the maximum possible weight, and it's balanced.\n    '''\n",
    "test_solution.py": 'from solution import will_it_fly\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([3, 2, 3], 9) is True\n    assert candidate([1, 2], 5) is False\n    assert candidate([3], 5) is True\n    assert candidate([3, 2, 3], 1) is False\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 3], 6) is False\n    assert candidate([5], 5) is True\n\n\n\ndef test_candidate():\n    check(will_it_fly)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import will_it_fly\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([3, 2, 3], 9) is True\n    assert candidate([1, 2], 5) is False\n    assert candidate([3], 5) is True\n    assert candidate([3, 2, 3], 1) is False\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([1, 2, 3], 6) is False\n    assert candidate([5], 5) is True\n\n\n\ndef test_candidate():\n    check(will_it_fly)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
