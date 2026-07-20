"""HumanEval task HumanEval_83"""
from pathlib import Path

TASK = """Implement the function 'starts_one_ends' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def starts_one_ends(n):
    \"\"\"
    Given a positive integer n, return the count of the numbers of n-digit
    positive integers that start or end with 1.
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef starts_one_ends(n):\n    """\n    Given a positive integer n, return the count of the numbers of n-digit\n    positive integers that start or end with 1.\n    """\n',
    "test_solution.py": 'from solution import starts_one_ends\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1) == 1\n    assert candidate(2) == 18\n    assert candidate(3) == 180\n    assert candidate(4) == 1800\n    assert candidate(5) == 18000\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(starts_one_ends)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import starts_one_ends\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1) == 1\n    assert candidate(2) == 18\n    assert candidate(3) == 180\n    assert candidate(4) == 1800\n    assert candidate(5) == 18000\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(starts_one_ends)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
