"""HumanEval task HumanEval_25"""
from pathlib import Path

TASK = """Implement the function 'factorize' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def factorize(n: int) -> List[int]:
    \"\"\" Return list of prime factors of given integer in the order from smallest to largest.
    Each of the factors should be listed number of times corresponding to how many times it appeares in factorization.
    Input number should be equal to the product of all factors
    >>> factorize(8)
    [2, 2, 2]
    >>> factorize(25)
    [5, 5]
    >>> factorize(70)
    [2, 5, 7]
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef factorize(n: int) -> List[int]:\n    """ Return list of prime factors of given integer in the order from smallest to largest.\n    Each of the factors should be listed number of times corresponding to how many times it appeares in factorization.\n    Input number should be equal to the product of all factors\n    >>> factorize(8)\n    [2, 2, 2]\n    >>> factorize(25)\n    [5, 5]\n    >>> factorize(70)\n    [2, 5, 7]\n    """\n',
    "test_solution.py": "from solution import factorize\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(2) == [2]\n    assert candidate(4) == [2, 2]\n    assert candidate(8) == [2, 2, 2]\n    assert candidate(3 * 19) == [3, 19]\n    assert candidate(3 * 19 * 3 * 19) == [3, 3, 19, 19]\n    assert candidate(3 * 19 * 3 * 19 * 3 * 19) == [3, 3, 3, 19, 19, 19]\n    assert candidate(3 * 19 * 19 * 19) == [3, 19, 19, 19]\n    assert candidate(3 * 2 * 3) == [2, 3, 3]\n\n\ndef test_candidate():\n    check(factorize)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import factorize\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(2) == [2]\n    assert candidate(4) == [2, 2]\n    assert candidate(8) == [2, 2, 2]\n    assert candidate(3 * 19) == [3, 19]\n    assert candidate(3 * 19 * 3 * 19) == [3, 3, 19, 19]\n    assert candidate(3 * 19 * 3 * 19 * 3 * 19) == [3, 3, 3, 19, 19, 19]\n    assert candidate(3 * 19 * 19 * 19) == [3, 19, 19, 19]\n    assert candidate(3 * 2 * 3) == [2, 3, 3]\n\n\ndef test_candidate():\n    check(factorize)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
