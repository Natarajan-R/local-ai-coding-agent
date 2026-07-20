"""HumanEval task HumanEval_37"""
from pathlib import Path

TASK = """Implement the function 'sort_even' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def sort_even(l: list):
    \"\"\"This function takes a list l and returns a list l' such that
    l' is identical to l in the odd indicies, while its values at the even indicies are equal
    to the values of the even indicies of l, but sorted.
    >>> sort_even([1, 2, 3])
    [1, 2, 3]
    >>> sort_even([5, 6, 3, 4])
    [3, 6, 5, 4]
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef sort_even(l: list):\n    """This function takes a list l and returns a list l\' such that\n    l\' is identical to l in the odd indicies, while its values at the even indicies are equal\n    to the values of the even indicies of l, but sorted.\n    >>> sort_even([1, 2, 3])\n    [1, 2, 3]\n    >>> sort_even([5, 6, 3, 4])\n    [3, 6, 5, 4]\n    """\n',
    "test_solution.py": 'from solution import sort_even\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert tuple(candidate([1, 2, 3])) == tuple([1, 2, 3])\n    assert tuple(candidate([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])) == tuple([-10, 3, -5, 2, -3, 3, 5, 0, 9, 1, 123])\n    assert tuple(candidate([5, 8, -12, 4, 23, 2, 3, 11, 12, -10])) == tuple([-12, 8, 3, 4, 5, 2, 12, 11, 23, -10])\n\n\n\ndef test_candidate():\n    check(sort_even)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import sort_even\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert tuple(candidate([1, 2, 3])) == tuple([1, 2, 3])\n    assert tuple(candidate([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])) == tuple([-10, 3, -5, 2, -3, 3, 5, 0, 9, 1, 123])\n    assert tuple(candidate([5, 8, -12, 4, 23, 2, 3, 11, 12, -10])) == tuple([-12, 8, 3, 4, 5, 2, 12, 11, 23, -10])\n\n\n\ndef test_candidate():\n    check(sort_even)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
