"""HumanEval task HumanEval_136"""
from pathlib import Path

TASK = """Implement the function 'largest_smallest_integers' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def largest_smallest_integers(lst):
    '''
    Create a function that returns a tuple (a, b), where 'a' is
    the largest of negative integers, and 'b' is the smallest
    of positive integers in a list.
    If there is no negative or positive integers, return them as None.

    Examples:
    largest_smallest_integers([2, 4, 1, 3, 5, 7]) == (None, 1)
    largest_smallest_integers([]) == (None, None)
    largest_smallest_integers([0]) == (None, None)
    '''

"""

FILES = {
    "solution.py": "\ndef largest_smallest_integers(lst):\n    '''\n    Create a function that returns a tuple (a, b), where 'a' is\n    the largest of negative integers, and 'b' is the smallest\n    of positive integers in a list.\n    If there is no negative or positive integers, return them as None.\n\n    Examples:\n    largest_smallest_integers([2, 4, 1, 3, 5, 7]) == (None, 1)\n    largest_smallest_integers([]) == (None, None)\n    largest_smallest_integers([0]) == (None, None)\n    '''\n",
    "test_solution.py": 'from solution import largest_smallest_integers\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([2, 4, 1, 3, 5, 7]) == (None, 1)\n    assert candidate([2, 4, 1, 3, 5, 7, 0]) == (None, 1)\n    assert candidate([1, 3, 2, 4, 5, 6, -2]) == (-2, 1)\n    assert candidate([4, 5, 3, 6, 2, 7, -7]) == (-7, 2)\n    assert candidate([7, 3, 8, 4, 9, 2, 5, -9]) == (-9, 2)\n    assert candidate([]) == (None, None)\n    assert candidate([0]) == (None, None)\n    assert candidate([-1, -3, -5, -6]) == (-1, None)\n    assert candidate([-1, -3, -5, -6, 0]) == (-1, None)\n    assert candidate([-6, -4, -4, -3, 1]) == (-3, 1)\n    assert candidate([-6, -4, -4, -3, -100, 1]) == (-3, 1)\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\ndef test_candidate():\n    check(largest_smallest_integers)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import largest_smallest_integers\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([2, 4, 1, 3, 5, 7]) == (None, 1)\n    assert candidate([2, 4, 1, 3, 5, 7, 0]) == (None, 1)\n    assert candidate([1, 3, 2, 4, 5, 6, -2]) == (-2, 1)\n    assert candidate([4, 5, 3, 6, 2, 7, -7]) == (-7, 2)\n    assert candidate([7, 3, 8, 4, 9, 2, 5, -9]) == (-9, 2)\n    assert candidate([]) == (None, None)\n    assert candidate([0]) == (None, None)\n    assert candidate([-1, -3, -5, -6]) == (-1, None)\n    assert candidate([-1, -3, -5, -6, 0]) == (-1, None)\n    assert candidate([-6, -4, -4, -3, 1]) == (-3, 1)\n    assert candidate([-6, -4, -4, -3, -100, 1]) == (-3, 1)\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\ndef test_candidate():\n    check(largest_smallest_integers)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
