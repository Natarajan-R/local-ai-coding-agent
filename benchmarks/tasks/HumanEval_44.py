"""HumanEval task HumanEval_44"""
from pathlib import Path

TASK = """Implement the function 'change_base' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def change_base(x: int, base: int):
    \"\"\"Change numerical base of input number x to base.
    return string representation after the conversion.
    base numbers are less than 10.
    >>> change_base(8, 3)
    '22'
    >>> change_base(8, 2)
    '1000'
    >>> change_base(7, 2)
    '111'
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef change_base(x: int, base: int):\n    """Change numerical base of input number x to base.\n    return string representation after the conversion.\n    base numbers are less than 10.\n    >>> change_base(8, 3)\n    \'22\'\n    >>> change_base(8, 2)\n    \'1000\'\n    >>> change_base(7, 2)\n    \'111\'\n    """\n',
    "test_solution.py": 'from solution import change_base\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(8, 3) == "22"\n    assert candidate(9, 3) == "100"\n    assert candidate(234, 2) == "11101010"\n    assert candidate(16, 2) == "10000"\n    assert candidate(8, 2) == "1000"\n    assert candidate(7, 2) == "111"\n    for x in range(2, 8):\n        assert candidate(x, x + 1) == str(x)\n\n\n\ndef test_candidate():\n    check(change_base)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import change_base\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(8, 3) == "22"\n    assert candidate(9, 3) == "100"\n    assert candidate(234, 2) == "11101010"\n    assert candidate(16, 2) == "10000"\n    assert candidate(8, 2) == "1000"\n    assert candidate(7, 2) == "111"\n    for x in range(2, 8):\n        assert candidate(x, x + 1) == str(x)\n\n\n\ndef test_candidate():\n    check(change_base)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
