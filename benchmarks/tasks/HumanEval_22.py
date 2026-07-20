"""HumanEval task HumanEval_22"""
from pathlib import Path

TASK = """Implement the function 'filter_integers' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List, Any


def filter_integers(values: List[Any]) -> List[int]:
    \"\"\" Filter given list of any python values only for integers
    >>> filter_integers(['a', 3.14, 5])
    [5]
    >>> filter_integers([1, 2, 3, 'abc', {}, []])
    [1, 2, 3]
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List, Any\n\n\ndef filter_integers(values: List[Any]) -> List[int]:\n    """ Filter given list of any python values only for integers\n    >>> filter_integers([\'a\', 3.14, 5])\n    [5]\n    >>> filter_integers([1, 2, 3, \'abc\', {}, []])\n    [1, 2, 3]\n    """\n',
    "test_solution.py": "from solution import filter_integers\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == []\n    assert candidate([4, {}, [], 23.2, 9, 'adasd']) == [4, 9]\n    assert candidate([3, 'c', 3, 3, 'a', 'b']) == [3, 3, 3]\n\n\ndef test_candidate():\n    check(filter_integers)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import filter_integers\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == []\n    assert candidate([4, {}, [], 23.2, 9, 'adasd']) == [4, 9]\n    assert candidate([3, 'c', 3, 3, 'a', 'b']) == [3, 3, 3]\n\n\ndef test_candidate():\n    check(filter_integers)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
