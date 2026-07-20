"""HumanEval task HumanEval_23"""
from pathlib import Path

TASK = """Implement the function 'strlen' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def strlen(string: str) -> int:
    \"\"\" Return length of given string
    >>> strlen('')
    0
    >>> strlen('abc')
    3
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef strlen(string: str) -> int:\n    """ Return length of given string\n    >>> strlen(\'\')\n    0\n    >>> strlen(\'abc\')\n    3\n    """\n',
    "test_solution.py": "from solution import strlen\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == 0\n    assert candidate('x') == 1\n    assert candidate('asdasnakj') == 9\n\n\ndef test_candidate():\n    check(strlen)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import strlen\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == 0\n    assert candidate('x') == 1\n    assert candidate('asdasnakj') == 9\n\n\ndef test_candidate():\n    check(strlen)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
