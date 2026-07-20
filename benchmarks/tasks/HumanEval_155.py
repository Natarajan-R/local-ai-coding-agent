"""HumanEval task HumanEval_155"""
from pathlib import Path

TASK = """Implement the function 'even_odd_count' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def even_odd_count(num):
    \"\"\"Given an integer. return a tuple that has the number of even and odd digits respectively.

     Example:
        even_odd_count(-12) ==> (1, 1)
        even_odd_count(123) ==> (1, 2)
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef even_odd_count(num):\n    """Given an integer. return a tuple that has the number of even and odd digits respectively.\n\n     Example:\n        even_odd_count(-12) ==> (1, 1)\n        even_odd_count(123) ==> (1, 2)\n    """\n',
    "test_solution.py": 'from solution import even_odd_count\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(7) == (0, 1)\n    assert candidate(-78) == (1, 1)\n    assert candidate(3452) == (2, 2)\n    assert candidate(346211) == (3, 3)\n    assert candidate(-345821) == (3, 3)\n    assert candidate(-2) == (1, 0)\n    assert candidate(-45347) == (2, 3)\n    assert candidate(0) == (1, 0)\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(even_odd_count)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import even_odd_count\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(7) == (0, 1)\n    assert candidate(-78) == (1, 1)\n    assert candidate(3452) == (2, 2)\n    assert candidate(346211) == (3, 3)\n    assert candidate(-345821) == (3, 3)\n    assert candidate(-2) == (1, 0)\n    assert candidate(-45347) == (2, 3)\n    assert candidate(0) == (1, 0)\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(even_odd_count)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
