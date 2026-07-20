"""HumanEval task HumanEval_85"""
from pathlib import Path

TASK = """Implement the function 'add' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def add(lst):
    \"\"\"Given a non-empty list of integers lst. add the even elements that are at odd indices..


    Examples:
        add([4, 2, 6, 7]) ==> 2 
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef add(lst):\n    """Given a non-empty list of integers lst. add the even elements that are at odd indices..\n\n\n    Examples:\n        add([4, 2, 6, 7]) ==> 2 \n    """\n',
    "test_solution.py": 'from solution import add\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([4, 88]) == 88\n    assert candidate([4, 5, 6, 7, 2, 122]) == 122\n    assert candidate([4, 0, 6, 7]) == 0\n    assert candidate([4, 4, 6, 8]) == 12\n\n    # Check some edge cases that are easy to work out by hand.\n    \n\n\ndef test_candidate():\n    check(add)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import add\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([4, 88]) == 88\n    assert candidate([4, 5, 6, 7, 2, 122]) == 122\n    assert candidate([4, 0, 6, 7]) == 0\n    assert candidate([4, 4, 6, 8]) == 12\n\n    # Check some edge cases that are easy to work out by hand.\n    \n\n\ndef test_candidate():\n    check(add)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
