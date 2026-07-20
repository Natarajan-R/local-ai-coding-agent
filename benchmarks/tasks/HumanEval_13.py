"""HumanEval task HumanEval_13"""
from pathlib import Path

TASK = """Implement the function 'greatest_common_divisor' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def greatest_common_divisor(a: int, b: int) -> int:
    \"\"\" Return a greatest common divisor of two integers a and b
    >>> greatest_common_divisor(3, 5)
    1
    >>> greatest_common_divisor(25, 15)
    5
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef greatest_common_divisor(a: int, b: int) -> int:\n    """ Return a greatest common divisor of two integers a and b\n    >>> greatest_common_divisor(3, 5)\n    1\n    >>> greatest_common_divisor(25, 15)\n    5\n    """\n',
    "test_solution.py": "from solution import greatest_common_divisor\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(3, 7) == 1\n    assert candidate(10, 15) == 5\n    assert candidate(49, 14) == 7\n    assert candidate(144, 60) == 12\n\n\ndef test_candidate():\n    check(greatest_common_divisor)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import greatest_common_divisor\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate(3, 7) == 1\n    assert candidate(10, 15) == 5\n    assert candidate(49, 14) == 7\n    assert candidate(144, 60) == 12\n\n\ndef test_candidate():\n    check(greatest_common_divisor)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
