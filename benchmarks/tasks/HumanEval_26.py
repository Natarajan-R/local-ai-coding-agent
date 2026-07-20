"""HumanEval task HumanEval_26"""
from pathlib import Path

TASK = """Implement the function 'remove_duplicates' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def remove_duplicates(numbers: List[int]) -> List[int]:
    \"\"\" From a list of integers, remove all elements that occur more than once.
    Keep order of elements left the same as in the input.
    >>> remove_duplicates([1, 2, 3, 2, 4])
    [1, 3, 4]
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef remove_duplicates(numbers: List[int]) -> List[int]:\n    """ From a list of integers, remove all elements that occur more than once.\n    Keep order of elements left the same as in the input.\n    >>> remove_duplicates([1, 2, 3, 2, 4])\n    [1, 3, 4]\n    """\n',
    "test_solution.py": "from solution import remove_duplicates\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == []\n    assert candidate([1, 2, 3, 4]) == [1, 2, 3, 4]\n    assert candidate([1, 2, 3, 2, 4, 3, 5]) == [1, 4, 5]\n\n\ndef test_candidate():\n    check(remove_duplicates)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import remove_duplicates\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == []\n    assert candidate([1, 2, 3, 4]) == [1, 2, 3, 4]\n    assert candidate([1, 2, 3, 2, 4, 3, 5]) == [1, 4, 5]\n\n\ndef test_candidate():\n    check(remove_duplicates)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
