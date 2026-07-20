"""HumanEval task HumanEval_43"""
from pathlib import Path

TASK = """Implement the function 'pairs_sum_to_zero' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def pairs_sum_to_zero(l):
    \"\"\"
    pairs_sum_to_zero takes a list of integers as an input.
    it returns True if there are two distinct elements in the list that
    sum to zero, and False otherwise.
    >>> pairs_sum_to_zero([1, 3, 5, 0])
    False
    >>> pairs_sum_to_zero([1, 3, -2, 1])
    False
    >>> pairs_sum_to_zero([1, 2, 3, 7])
    False
    >>> pairs_sum_to_zero([2, 4, -5, 3, 5, 7])
    True
    >>> pairs_sum_to_zero([1])
    False
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef pairs_sum_to_zero(l):\n    """\n    pairs_sum_to_zero takes a list of integers as an input.\n    it returns True if there are two distinct elements in the list that\n    sum to zero, and False otherwise.\n    >>> pairs_sum_to_zero([1, 3, 5, 0])\n    False\n    >>> pairs_sum_to_zero([1, 3, -2, 1])\n    False\n    >>> pairs_sum_to_zero([1, 2, 3, 7])\n    False\n    >>> pairs_sum_to_zero([2, 4, -5, 3, 5, 7])\n    True\n    >>> pairs_sum_to_zero([1])\n    False\n    """\n',
    "test_solution.py": 'from solution import pairs_sum_to_zero\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 3, 5, 0]) == False\n    assert candidate([1, 3, -2, 1]) == False\n    assert candidate([1, 2, 3, 7]) == False\n    assert candidate([2, 4, -5, 3, 5, 7]) == True\n    assert candidate([1]) == False\n\n    assert candidate([-3, 9, -1, 3, 2, 30]) == True\n    assert candidate([-3, 9, -1, 3, 2, 31]) == True\n    assert candidate([-3, 9, -1, 4, 2, 30]) == False\n    assert candidate([-3, 9, -1, 4, 2, 31]) == False\n\n\n\ndef test_candidate():\n    check(pairs_sum_to_zero)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import pairs_sum_to_zero\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 3, 5, 0]) == False\n    assert candidate([1, 3, -2, 1]) == False\n    assert candidate([1, 2, 3, 7]) == False\n    assert candidate([2, 4, -5, 3, 5, 7]) == True\n    assert candidate([1]) == False\n\n    assert candidate([-3, 9, -1, 3, 2, 30]) == True\n    assert candidate([-3, 9, -1, 3, 2, 31]) == True\n    assert candidate([-3, 9, -1, 4, 2, 30]) == False\n    assert candidate([-3, 9, -1, 4, 2, 31]) == False\n\n\n\ndef test_candidate():\n    check(pairs_sum_to_zero)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
