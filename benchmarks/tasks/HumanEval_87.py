"""HumanEval task HumanEval_87"""
from pathlib import Path

TASK = """Implement the function 'get_row' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def get_row(lst, x):
    \"\"\"
    You are given a 2 dimensional data, as a nested lists,
    which is similar to matrix, however, unlike matrices,
    each row may contain a different number of columns.
    Given lst, and integer x, find integers x in the list,
    and return list of tuples, [(x1, y1), (x2, y2) ...] such that
    each tuple is a coordinate - (row, columns), starting with 0.
    Sort coordinates initially by rows in ascending order.
    Also, sort coordinates of the row by columns in descending order.
    
    Examples:
    get_row([
      [1,2,3,4,5,6],
      [1,2,3,4,1,6],
      [1,2,3,4,5,1]
    ], 1) == [(0, 0), (1, 4), (1, 0), (2, 5), (2, 0)]
    get_row([], 1) == []
    get_row([[], [1], [1, 2, 3]], 3) == [(2, 2)]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef get_row(lst, x):\n    """\n    You are given a 2 dimensional data, as a nested lists,\n    which is similar to matrix, however, unlike matrices,\n    each row may contain a different number of columns.\n    Given lst, and integer x, find integers x in the list,\n    and return list of tuples, [(x1, y1), (x2, y2) ...] such that\n    each tuple is a coordinate - (row, columns), starting with 0.\n    Sort coordinates initially by rows in ascending order.\n    Also, sort coordinates of the row by columns in descending order.\n    \n    Examples:\n    get_row([\n      [1,2,3,4,5,6],\n      [1,2,3,4,1,6],\n      [1,2,3,4,5,1]\n    ], 1) == [(0, 0), (1, 4), (1, 0), (2, 5), (2, 0)]\n    get_row([], 1) == []\n    get_row([[], [1], [1, 2, 3]], 3) == [(2, 2)]\n    """\n',
    "test_solution.py": 'from solution import get_row\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([\n        [1,2,3,4,5,6],\n        [1,2,3,4,1,6],\n        [1,2,3,4,5,1]\n    ], 1) == [(0, 0), (1, 4), (1, 0), (2, 5), (2, 0)]\n    assert candidate([\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6]\n    ], 2) == [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]\n    assert candidate([\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,1,3,4,5,6],\n        [1,2,1,4,5,6],\n        [1,2,3,1,5,6],\n        [1,2,3,4,1,6],\n        [1,2,3,4,5,1]\n    ], 1) == [(0, 0), (1, 0), (2, 1), (2, 0), (3, 2), (3, 0), (4, 3), (4, 0), (5, 4), (5, 0), (6, 5), (6, 0)]\n    assert candidate([], 1) == []\n    assert candidate([[1]], 2) == []\n    assert candidate([[], [1], [1, 2, 3]], 3) == [(2, 2)]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(get_row)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import get_row\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([\n        [1,2,3,4,5,6],\n        [1,2,3,4,1,6],\n        [1,2,3,4,5,1]\n    ], 1) == [(0, 0), (1, 4), (1, 0), (2, 5), (2, 0)]\n    assert candidate([\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6]\n    ], 2) == [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]\n    assert candidate([\n        [1,2,3,4,5,6],\n        [1,2,3,4,5,6],\n        [1,1,3,4,5,6],\n        [1,2,1,4,5,6],\n        [1,2,3,1,5,6],\n        [1,2,3,4,1,6],\n        [1,2,3,4,5,1]\n    ], 1) == [(0, 0), (1, 0), (2, 1), (2, 0), (3, 2), (3, 0), (4, 3), (4, 0), (5, 4), (5, 0), (6, 5), (6, 0)]\n    assert candidate([], 1) == []\n    assert candidate([[1]], 2) == []\n    assert candidate([[], [1], [1, 2, 3]], 3) == [(2, 2)]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(get_row)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
