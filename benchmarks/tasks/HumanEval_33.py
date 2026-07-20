"""HumanEval task HumanEval_33"""
from pathlib import Path

TASK = """Implement the function 'sort_third' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def sort_third(l: list):
    \"\"\"This function takes a list l and returns a list l' such that
    l' is identical to l in the indicies that are not divisible by three, while its values at the indicies that are divisible by three are equal
    to the values of the corresponding indicies of l, but sorted.
    >>> sort_third([1, 2, 3])
    [1, 2, 3]
    >>> sort_third([5, 6, 3, 4, 8, 9, 2])
    [2, 6, 3, 4, 8, 9, 5]
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef sort_third(l: list):\n    """This function takes a list l and returns a list l\' such that\n    l\' is identical to l in the indicies that are not divisible by three, while its values at the indicies that are divisible by three are equal\n    to the values of the corresponding indicies of l, but sorted.\n    >>> sort_third([1, 2, 3])\n    [1, 2, 3]\n    >>> sort_third([5, 6, 3, 4, 8, 9, 2])\n    [2, 6, 3, 4, 8, 9, 5]\n    """\n',
    "test_solution.py": 'from solution import sort_third\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert tuple(candidate([1, 2, 3])) == tuple(sort_third([1, 2, 3]))\n    assert tuple(candidate([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])) == tuple(sort_third([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10]))\n    assert tuple(candidate([5, 8, -12, 4, 23, 2, 3, 11, 12, -10])) == tuple(sort_third([5, 8, -12, 4, 23, 2, 3, 11, 12, -10]))\n    assert tuple(candidate([5, 6, 3, 4, 8, 9, 2])) == tuple([2, 6, 3, 4, 8, 9, 5])\n    assert tuple(candidate([5, 8, 3, 4, 6, 9, 2])) == tuple([2, 8, 3, 4, 6, 9, 5])\n    assert tuple(candidate([5, 6, 9, 4, 8, 3, 2])) == tuple([2, 6, 9, 4, 8, 3, 5])\n    assert tuple(candidate([5, 6, 3, 4, 8, 9, 2, 1])) == tuple([2, 6, 3, 4, 8, 9, 5, 1])\n\n\n\ndef test_candidate():\n    check(sort_third)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import sort_third\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert tuple(candidate([1, 2, 3])) == tuple(sort_third([1, 2, 3]))\n    assert tuple(candidate([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])) == tuple(sort_third([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10]))\n    assert tuple(candidate([5, 8, -12, 4, 23, 2, 3, 11, 12, -10])) == tuple(sort_third([5, 8, -12, 4, 23, 2, 3, 11, 12, -10]))\n    assert tuple(candidate([5, 6, 3, 4, 8, 9, 2])) == tuple([2, 6, 3, 4, 8, 9, 5])\n    assert tuple(candidate([5, 8, 3, 4, 6, 9, 2])) == tuple([2, 8, 3, 4, 6, 9, 5])\n    assert tuple(candidate([5, 6, 9, 4, 8, 3, 2])) == tuple([2, 6, 9, 4, 8, 3, 5])\n    assert tuple(candidate([5, 6, 3, 4, 8, 9, 2, 1])) == tuple([2, 6, 3, 4, 8, 9, 5, 1])\n\n\n\ndef test_candidate():\n    check(sort_third)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
