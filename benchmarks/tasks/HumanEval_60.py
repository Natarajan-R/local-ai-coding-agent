"""HumanEval task HumanEval_60"""
from pathlib import Path

TASK = """Implement the function 'sum_to_n' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def sum_to_n(n: int):
    \"\"\"sum_to_n is a function that sums numbers from 1 to n.
    >>> sum_to_n(30)
    465
    >>> sum_to_n(100)
    5050
    >>> sum_to_n(5)
    15
    >>> sum_to_n(10)
    55
    >>> sum_to_n(1)
    1
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef sum_to_n(n: int):\n    """sum_to_n is a function that sums numbers from 1 to n.\n    >>> sum_to_n(30)\n    465\n    >>> sum_to_n(100)\n    5050\n    >>> sum_to_n(5)\n    15\n    >>> sum_to_n(10)\n    55\n    >>> sum_to_n(1)\n    1\n    """\n',
    "test_solution.py": 'from solution import sum_to_n\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(1) == 1\n    assert candidate(6) == 21\n    assert candidate(11) == 66\n    assert candidate(30) == 465\n    assert candidate(100) == 5050\n\n\n\ndef test_candidate():\n    check(sum_to_n)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import sum_to_n\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(1) == 1\n    assert candidate(6) == 21\n    assert candidate(11) == 66\n    assert candidate(30) == 465\n    assert candidate(100) == 5050\n\n\n\ndef test_candidate():\n    check(sum_to_n)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
