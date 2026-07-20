"""HumanEval task HumanEval_8"""
from pathlib import Path

TASK = """Implement the function 'sum_product' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List, Tuple


def sum_product(numbers: List[int]) -> Tuple[int, int]:
    \"\"\" For a given list of integers, return a tuple consisting of a sum and a product of all the integers in a list.
    Empty sum should be equal to 0 and empty product should be equal to 1.
    >>> sum_product([])
    (0, 1)
    >>> sum_product([1, 2, 3, 4])
    (10, 24)
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List, Tuple\n\n\ndef sum_product(numbers: List[int]) -> Tuple[int, int]:\n    """ For a given list of integers, return a tuple consisting of a sum and a product of all the integers in a list.\n    Empty sum should be equal to 0 and empty product should be equal to 1.\n    >>> sum_product([])\n    (0, 1)\n    >>> sum_product([1, 2, 3, 4])\n    (10, 24)\n    """\n',
    "test_solution.py": "from solution import sum_product\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == (0, 1)\n    assert candidate([1, 1, 1]) == (3, 1)\n    assert candidate([100, 0]) == (100, 0)\n    assert candidate([3, 5, 7]) == (3 + 5 + 7, 3 * 5 * 7)\n    assert candidate([10]) == (10, 10)\n\n\ndef test_candidate():\n    check(sum_product)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import sum_product\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == (0, 1)\n    assert candidate([1, 1, 1]) == (3, 1)\n    assert candidate([100, 0]) == (100, 0)\n    assert candidate([3, 5, 7]) == (3 + 5 + 7, 3 * 5 * 7)\n    assert candidate([10]) == (10, 10)\n\n\ndef test_candidate():\n    check(sum_product)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
