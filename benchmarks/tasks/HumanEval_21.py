"""HumanEval task HumanEval_21"""
from pathlib import Path

TASK = """Implement the function 'rescale_to_unit' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def rescale_to_unit(numbers: List[float]) -> List[float]:
    \"\"\" Given list of numbers (of at least two elements), apply a linear transform to that list,
    such that the smallest number will become 0 and the largest will become 1
    >>> rescale_to_unit([1.0, 2.0, 3.0, 4.0, 5.0])
    [0.0, 0.25, 0.5, 0.75, 1.0]
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef rescale_to_unit(numbers: List[float]) -> List[float]:\n    """ Given list of numbers (of at least two elements), apply a linear transform to that list,\n    such that the smallest number will become 0 and the largest will become 1\n    >>> rescale_to_unit([1.0, 2.0, 3.0, 4.0, 5.0])\n    [0.0, 0.25, 0.5, 0.75, 1.0]\n    """\n',
    "test_solution.py": "from solution import rescale_to_unit\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([2.0, 49.9]) == [0.0, 1.0]\n    assert candidate([100.0, 49.9]) == [1.0, 0.0]\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0]) == [0.0, 0.25, 0.5, 0.75, 1.0]\n    assert candidate([2.0, 1.0, 5.0, 3.0, 4.0]) == [0.25, 0.0, 1.0, 0.5, 0.75]\n    assert candidate([12.0, 11.0, 15.0, 13.0, 14.0]) == [0.25, 0.0, 1.0, 0.5, 0.75]\n\n\ndef test_candidate():\n    check(rescale_to_unit)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import rescale_to_unit\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([2.0, 49.9]) == [0.0, 1.0]\n    assert candidate([100.0, 49.9]) == [1.0, 0.0]\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0]) == [0.0, 0.25, 0.5, 0.75, 1.0]\n    assert candidate([2.0, 1.0, 5.0, 3.0, 4.0]) == [0.25, 0.0, 1.0, 0.5, 0.75]\n    assert candidate([12.0, 11.0, 15.0, 13.0, 14.0]) == [0.25, 0.0, 1.0, 0.5, 0.75]\n\n\ndef test_candidate():\n    check(rescale_to_unit)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
