"""HumanEval task HumanEval_20"""
from pathlib import Path

TASK = """Implement the function 'find_closest_elements' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List, Tuple


def find_closest_elements(numbers: List[float]) -> Tuple[float, float]:
    \"\"\" From a supplied list of numbers (of length at least two) select and return two that are the closest to each
    other and return them in order (smaller number, larger number).
    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2])
    (2.0, 2.2)
    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0])
    (2.0, 2.0)
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List, Tuple\n\n\ndef find_closest_elements(numbers: List[float]) -> Tuple[float, float]:\n    """ From a supplied list of numbers (of length at least two) select and return two that are the closest to each\n    other and return them in order (smaller number, larger number).\n    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2])\n    (2.0, 2.2)\n    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0])\n    (2.0, 2.0)\n    """\n',
    "test_solution.py": "from solution import find_closest_elements\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2]) == (3.9, 4.0)\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0]) == (5.0, 5.9)\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.2]) == (2.0, 2.2)\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.0]) == (2.0, 2.0)\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1]) == (2.2, 3.1)\n\n\n\ndef test_candidate():\n    check(find_closest_elements)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import find_closest_elements\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2]) == (3.9, 4.0)\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0]) == (5.0, 5.9)\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.2]) == (2.0, 2.2)\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.0]) == (2.0, 2.0)\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1]) == (2.2, 3.1)\n\n\n\ndef test_candidate():\n    check(find_closest_elements)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
