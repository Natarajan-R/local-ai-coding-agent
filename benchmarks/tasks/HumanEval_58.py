"""HumanEval task HumanEval_58"""
from pathlib import Path

TASK = """Implement the function 'common' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def common(l1: list, l2: list):
    \"\"\"Return sorted unique common elements for two lists.
    >>> common([1, 4, 3, 34, 653, 2, 5], [5, 7, 1, 5, 9, 653, 121])
    [1, 5, 653]
    >>> common([5, 3, 2, 8], [3, 2])
    [2, 3]

    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef common(l1: list, l2: list):\n    """Return sorted unique common elements for two lists.\n    >>> common([1, 4, 3, 34, 653, 2, 5], [5, 7, 1, 5, 9, 653, 121])\n    [1, 5, 653]\n    >>> common([5, 3, 2, 8], [3, 2])\n    [2, 3]\n\n    """\n',
    "test_solution.py": 'from solution import common\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 4, 3, 34, 653, 2, 5], [5, 7, 1, 5, 9, 653, 121]) == [1, 5, 653]\n    assert candidate([5, 3, 2, 8], [3, 2]) == [2, 3]\n    assert candidate([4, 3, 2, 8], [3, 2, 4]) == [2, 3, 4]\n    assert candidate([4, 3, 2, 8], []) == []\n\n\n\ndef test_candidate():\n    check(common)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import common\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 4, 3, 34, 653, 2, 5], [5, 7, 1, 5, 9, 653, 121]) == [1, 5, 653]\n    assert candidate([5, 3, 2, 8], [3, 2]) == [2, 3]\n    assert candidate([4, 3, 2, 8], [3, 2, 4]) == [2, 3, 4]\n    assert candidate([4, 3, 2, 8], []) == []\n\n\n\ndef test_candidate():\n    check(common)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
