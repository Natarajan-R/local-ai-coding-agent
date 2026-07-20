"""HumanEval task HumanEval_70"""
from pathlib import Path

TASK = """Implement the function 'strange_sort_list' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def strange_sort_list(lst):
    '''
    Given list of integers, return list in strange order.
    Strange sorting, is when you start with the minimum value,
    then maximum of the remaining integers, then minimum and so on.

    Examples:
    strange_sort_list([1, 2, 3, 4]) == [1, 4, 2, 3]
    strange_sort_list([5, 5, 5, 5]) == [5, 5, 5, 5]
    strange_sort_list([]) == []
    '''

"""

FILES = {
    "solution.py": "\ndef strange_sort_list(lst):\n    '''\n    Given list of integers, return list in strange order.\n    Strange sorting, is when you start with the minimum value,\n    then maximum of the remaining integers, then minimum and so on.\n\n    Examples:\n    strange_sort_list([1, 2, 3, 4]) == [1, 4, 2, 3]\n    strange_sort_list([5, 5, 5, 5]) == [5, 5, 5, 5]\n    strange_sort_list([]) == []\n    '''\n",
    "test_solution.py": 'from solution import strange_sort_list\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1, 2, 3, 4]) == [1, 4, 2, 3]\n    assert candidate([5, 6, 7, 8, 9]) == [5, 9, 6, 8, 7]\n    assert candidate([1, 2, 3, 4, 5]) == [1, 5, 2, 4, 3]\n    assert candidate([5, 6, 7, 8, 9, 1]) == [1, 9, 5, 8, 6, 7]\n    assert candidate([5, 5, 5, 5]) == [5, 5, 5, 5]\n    assert candidate([]) == []\n    assert candidate([1,2,3,4,5,6,7,8]) == [1, 8, 2, 7, 3, 6, 4, 5]\n    assert candidate([0,2,2,2,5,5,-5,-5]) == [-5, 5, -5, 5, 0, 2, 2, 2]\n    assert candidate([111111]) == [111111]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(strange_sort_list)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import strange_sort_list\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1, 2, 3, 4]) == [1, 4, 2, 3]\n    assert candidate([5, 6, 7, 8, 9]) == [5, 9, 6, 8, 7]\n    assert candidate([1, 2, 3, 4, 5]) == [1, 5, 2, 4, 3]\n    assert candidate([5, 6, 7, 8, 9, 1]) == [1, 9, 5, 8, 6, 7]\n    assert candidate([5, 5, 5, 5]) == [5, 5, 5, 5]\n    assert candidate([]) == []\n    assert candidate([1,2,3,4,5,6,7,8]) == [1, 8, 2, 7, 3, 6, 4, 5]\n    assert candidate([0,2,2,2,5,5,-5,-5]) == [-5, 5, -5, 5, 0, 2, 2, 2]\n    assert candidate([111111]) == [111111]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(strange_sort_list)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
