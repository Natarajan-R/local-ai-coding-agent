"""HumanEval task HumanEval_65"""
from pathlib import Path

TASK = """Implement the function 'circular_shift' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def circular_shift(x, shift):
    \"\"\"Circular shift the digits of the integer x, shift the digits right by shift
    and return the result as a string.
    If shift > number of digits, return digits reversed.
    >>> circular_shift(12, 1)
    "21"
    >>> circular_shift(12, 2)
    "12"
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef circular_shift(x, shift):\n    """Circular shift the digits of the integer x, shift the digits right by shift\n    and return the result as a string.\n    If shift > number of digits, return digits reversed.\n    >>> circular_shift(12, 1)\n    "21"\n    >>> circular_shift(12, 2)\n    "12"\n    """\n',
    "test_solution.py": 'from solution import circular_shift\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(100, 2) == "001"\n    assert candidate(12, 2) == "12"\n    assert candidate(97, 8) == "79"\n    assert candidate(12, 1) == "21", "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(11, 101) == "11", "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(circular_shift)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import circular_shift\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(100, 2) == "001"\n    assert candidate(12, 2) == "12"\n    assert candidate(97, 8) == "79"\n    assert candidate(12, 1) == "21", "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(11, 101) == "11", "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(circular_shift)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
