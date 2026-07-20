"""HumanEval task HumanEval_24"""
from pathlib import Path

TASK = """Implement the function 'largest_divisor' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def largest_divisor(n: int) -> int:
    \"\"\" For a given number n, find the largest number that divides n evenly, smaller than n
    >>> largest_divisor(15)
    5
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef largest_divisor(n: int) -> int:\n    """ For a given number n, find the largest number that divides n evenly, smaller than n\n    >>> largest_divisor(15)\n    5\n    """\n',
    "test_solution.py": "from solution import largest_divisor\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(3) == 1\n    assert candidate(7) == 1\n    assert candidate(10) == 5\n    assert candidate(100) == 50\n    assert candidate(49) == 7\n\n\ndef test_candidate():\n    check(largest_divisor)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import largest_divisor\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(3) == 1\n    assert candidate(7) == 1\n    assert candidate(10) == 5\n    assert candidate(100) == 50\n    assert candidate(49) == 7\n\n\ndef test_candidate():\n    check(largest_divisor)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
