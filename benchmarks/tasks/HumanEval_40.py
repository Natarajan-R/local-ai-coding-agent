"""HumanEval task HumanEval_40"""
from pathlib import Path

TASK = """Implement the function 'triples_sum_to_zero' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def triples_sum_to_zero(l: list):
    \"\"\"
    triples_sum_to_zero takes a list of integers as an input.
    it returns True if there are three distinct elements in the list that
    sum to zero, and False otherwise.

    >>> triples_sum_to_zero([1, 3, 5, 0])
    False
    >>> triples_sum_to_zero([1, 3, -2, 1])
    True
    >>> triples_sum_to_zero([1, 2, 3, 7])
    False
    >>> triples_sum_to_zero([2, 4, -5, 3, 9, 7])
    True
    >>> triples_sum_to_zero([1])
    False
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef triples_sum_to_zero(l: list):\n    """\n    triples_sum_to_zero takes a list of integers as an input.\n    it returns True if there are three distinct elements in the list that\n    sum to zero, and False otherwise.\n\n    >>> triples_sum_to_zero([1, 3, 5, 0])\n    False\n    >>> triples_sum_to_zero([1, 3, -2, 1])\n    True\n    >>> triples_sum_to_zero([1, 2, 3, 7])\n    False\n    >>> triples_sum_to_zero([2, 4, -5, 3, 9, 7])\n    True\n    >>> triples_sum_to_zero([1])\n    False\n    """\n',
    "test_solution.py": 'from solution import triples_sum_to_zero\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 3, 5, 0]) == False\n    assert candidate([1, 3, 5, -1]) == False\n    assert candidate([1, 3, -2, 1]) == True\n    assert candidate([1, 2, 3, 7]) == False\n    assert candidate([1, 2, 5, 7]) == False\n    assert candidate([2, 4, -5, 3, 9, 7]) == True\n    assert candidate([1]) == False\n    assert candidate([1, 3, 5, -100]) == False\n    assert candidate([100, 3, 5, -100]) == False\n\n\n\ndef test_candidate():\n    check(triples_sum_to_zero)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import triples_sum_to_zero\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([1, 3, 5, 0]) == False\n    assert candidate([1, 3, 5, -1]) == False\n    assert candidate([1, 3, -2, 1]) == True\n    assert candidate([1, 2, 3, 7]) == False\n    assert candidate([1, 2, 5, 7]) == False\n    assert candidate([2, 4, -5, 3, 9, 7]) == True\n    assert candidate([1]) == False\n    assert candidate([1, 3, 5, -100]) == False\n    assert candidate([100, 3, 5, -100]) == False\n\n\n\ndef test_candidate():\n    check(triples_sum_to_zero)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
