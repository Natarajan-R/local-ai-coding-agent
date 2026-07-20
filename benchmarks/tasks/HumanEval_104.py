"""HumanEval task HumanEval_104"""
from pathlib import Path

TASK = """Implement the function 'unique_digits' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def unique_digits(x):
    \"\"\"Given a list of positive integers x. return a sorted list of all 
    elements that hasn't any even digit.

    Note: Returned list should be sorted in increasing order.
    
    For example:
    >>> unique_digits([15, 33, 1422, 1])
    [1, 15, 33]
    >>> unique_digits([152, 323, 1422, 10])
    []
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef unique_digits(x):\n    """Given a list of positive integers x. return a sorted list of all \n    elements that hasn\'t any even digit.\n\n    Note: Returned list should be sorted in increasing order.\n    \n    For example:\n    >>> unique_digits([15, 33, 1422, 1])\n    [1, 15, 33]\n    >>> unique_digits([152, 323, 1422, 10])\n    []\n    """\n',
    "test_solution.py": 'from solution import unique_digits\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([15, 33, 1422, 1]) == [1, 15, 33]\n    assert candidate([152, 323, 1422, 10]) == []\n    assert candidate([12345, 2033, 111, 151]) == [111, 151]\n    assert candidate([135, 103, 31]) == [31, 135]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(unique_digits)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import unique_digits\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([15, 33, 1422, 1]) == [1, 15, 33]\n    assert candidate([152, 323, 1422, 10]) == []\n    assert candidate([12345, 2033, 111, 151]) == [111, 151]\n    assert candidate([135, 103, 31]) == [31, 135]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(unique_digits)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
