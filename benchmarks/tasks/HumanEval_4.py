"""HumanEval task HumanEval_4"""
from pathlib import Path

TASK = """Implement the function 'mean_absolute_deviation' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def mean_absolute_deviation(numbers: List[float]) -> float:
    \"\"\" For a given list of input numbers, calculate Mean Absolute Deviation
    around the mean of this dataset.
    Mean Absolute Deviation is the average absolute difference between each
    element and a centerpoint (mean in this case):
    MAD = average | x - x_mean |
    >>> mean_absolute_deviation([1.0, 2.0, 3.0, 4.0])
    1.0
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef mean_absolute_deviation(numbers: List[float]) -> float:\n    """ For a given list of input numbers, calculate Mean Absolute Deviation\n    around the mean of this dataset.\n    Mean Absolute Deviation is the average absolute difference between each\n    element and a centerpoint (mean in this case):\n    MAD = average | x - x_mean |\n    >>> mean_absolute_deviation([1.0, 2.0, 3.0, 4.0])\n    1.0\n    """\n',
    "test_solution.py": "from solution import mean_absolute_deviation\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert abs(candidate([1.0, 2.0, 3.0]) - 2.0/3.0) < 1e-6\n    assert abs(candidate([1.0, 2.0, 3.0, 4.0]) - 1.0) < 1e-6\n    assert abs(candidate([1.0, 2.0, 3.0, 4.0, 5.0]) - 6.0/5.0) < 1e-6\n\n\n\ndef test_candidate():\n    check(mean_absolute_deviation)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import mean_absolute_deviation\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert abs(candidate([1.0, 2.0, 3.0]) - 2.0/3.0) < 1e-6\n    assert abs(candidate([1.0, 2.0, 3.0, 4.0]) - 1.0) < 1e-6\n    assert abs(candidate([1.0, 2.0, 3.0, 4.0, 5.0]) - 6.0/5.0) < 1e-6\n\n\n\ndef test_candidate():\n    check(mean_absolute_deviation)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
