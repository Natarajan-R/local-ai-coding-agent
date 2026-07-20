"""HumanEval task HumanEval_15"""
from pathlib import Path

TASK = """Implement the function 'string_sequence' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def string_sequence(n: int) -> str:
    \"\"\" Return a string containing space-delimited numbers starting from 0 upto n inclusive.
    >>> string_sequence(0)
    '0'
    >>> string_sequence(5)
    '0 1 2 3 4 5'
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef string_sequence(n: int) -> str:\n    """ Return a string containing space-delimited numbers starting from 0 upto n inclusive.\n    >>> string_sequence(0)\n    \'0\'\n    >>> string_sequence(5)\n    \'0 1 2 3 4 5\'\n    """\n',
    "test_solution.py": "from solution import string_sequence\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(0) == '0'\n    assert candidate(3) == '0 1 2 3'\n    assert candidate(10) == '0 1 2 3 4 5 6 7 8 9 10'\n\n\ndef test_candidate():\n    check(string_sequence)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import string_sequence\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(0) == '0'\n    assert candidate(3) == '0 1 2 3'\n    assert candidate(10) == '0 1 2 3 4 5 6 7 8 9 10'\n\n\ndef test_candidate():\n    check(string_sequence)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
