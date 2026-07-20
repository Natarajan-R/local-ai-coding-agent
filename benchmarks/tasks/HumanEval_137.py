"""HumanEval task HumanEval_137"""
from pathlib import Path

TASK = """Implement the function 'compare_one' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def compare_one(a, b):
    \"\"\"
    Create a function that takes integers, floats, or strings representing
    real numbers, and returns the larger variable in its given variable type.
    Return None if the values are equal.
    Note: If a real number is represented as a string, the floating point might be . or ,

    compare_one(1, 2.5) ➞ 2.5
    compare_one(1, "2,3") ➞ "2,3"
    compare_one("5,1", "6") ➞ "6"
    compare_one("1", 1) ➞ None
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef compare_one(a, b):\n    """\n    Create a function that takes integers, floats, or strings representing\n    real numbers, and returns the larger variable in its given variable type.\n    Return None if the values are equal.\n    Note: If a real number is represented as a string, the floating point might be . or ,\n\n    compare_one(1, 2.5) ➞ 2.5\n    compare_one(1, "2,3") ➞ "2,3"\n    compare_one("5,1", "6") ➞ "6"\n    compare_one("1", 1) ➞ None\n    """\n',
    "test_solution.py": 'from solution import compare_one\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(1, 2) == 2\n    assert candidate(1, 2.5) == 2.5\n    assert candidate(2, 3) == 3\n    assert candidate(5, 6) == 6\n    assert candidate(1, "2,3") == "2,3"\n    assert candidate("5,1", "6") == "6"\n    assert candidate("1", "2") == "2"\n    assert candidate("1", 1) == None\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(compare_one)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import compare_one\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(1, 2) == 2\n    assert candidate(1, 2.5) == 2.5\n    assert candidate(2, 3) == 3\n    assert candidate(5, 6) == 6\n    assert candidate(1, "2,3") == "2,3"\n    assert candidate("5,1", "6") == "6"\n    assert candidate("1", "2") == "2"\n    assert candidate("1", 1) == None\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(compare_one)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
