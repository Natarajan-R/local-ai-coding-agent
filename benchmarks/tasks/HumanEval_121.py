"""HumanEval task HumanEval_121"""
from pathlib import Path

TASK = """Implement the function 'solution' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def solution(lst):
    \"\"\"Given a non-empty list of integers, return the sum of all of the odd elements that are in even positions.
    

    Examples
    solution([5, 8, 7, 1]) ==> 12
    solution([3, 3, 3, 3, 3]) ==> 9
    solution([30, 13, 24, 321]) ==>0
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef solution(lst):\n    """Given a non-empty list of integers, return the sum of all of the odd elements that are in even positions.\n    \n\n    Examples\n    solution([5, 8, 7, 1]) ==> 12\n    solution([3, 3, 3, 3, 3]) ==> 9\n    solution([30, 13, 24, 321]) ==>0\n    """\n',
    "test_solution.py": 'from solution import solution\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([5, 8, 7, 1])    == 12\n    assert candidate([3, 3, 3, 3, 3]) == 9\n    assert candidate([30, 13, 24, 321]) == 0\n    assert candidate([5, 9]) == 5\n    assert candidate([2, 4, 8]) == 0\n    assert candidate([30, 13, 23, 32]) == 23\n    assert candidate([3, 13, 2, 9]) == 3\n\n    # Check some edge cases that are easy to work out by hand.\n\n\n\ndef test_candidate():\n    check(solution)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import solution\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([5, 8, 7, 1])    == 12\n    assert candidate([3, 3, 3, 3, 3]) == 9\n    assert candidate([30, 13, 24, 321]) == 0\n    assert candidate([5, 9]) == 5\n    assert candidate([2, 4, 8]) == 0\n    assert candidate([30, 13, 23, 32]) == 23\n    assert candidate([3, 13, 2, 9]) == 3\n\n    # Check some edge cases that are easy to work out by hand.\n\n\n\ndef test_candidate():\n    check(solution)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
