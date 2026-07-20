"""HumanEval task HumanEval_135"""
from pathlib import Path

TASK = """Implement the function 'can_arrange' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def can_arrange(arr):
    \"\"\"Create a function which returns the largest index of an element which
    is not greater than or equal to the element immediately preceding it. If
    no such element exists then return -1. The given array will not contain
    duplicate values.

    Examples:
    can_arrange([1,2,4,3,5]) = 3
    can_arrange([1,2,3]) = -1
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef can_arrange(arr):\n    """Create a function which returns the largest index of an element which\n    is not greater than or equal to the element immediately preceding it. If\n    no such element exists then return -1. The given array will not contain\n    duplicate values.\n\n    Examples:\n    can_arrange([1,2,4,3,5]) = 3\n    can_arrange([1,2,3]) = -1\n    """\n',
    "test_solution.py": 'from solution import can_arrange\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,4,3,5])==3\n    assert candidate([1,2,4,5])==-1\n    assert candidate([1,4,2,5,6,7,8,9,10])==2\n    assert candidate([4,8,5,7,3])==4\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([])==-1\n\n\n\ndef test_candidate():\n    check(can_arrange)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import can_arrange\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,4,3,5])==3\n    assert candidate([1,2,4,5])==-1\n    assert candidate([1,4,2,5,6,7,8,9,10])==2\n    assert candidate([4,8,5,7,3])==4\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([])==-1\n\n\n\ndef test_candidate():\n    check(can_arrange)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
