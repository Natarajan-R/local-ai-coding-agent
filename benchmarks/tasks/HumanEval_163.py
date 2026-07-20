"""HumanEval task HumanEval_163"""
from pathlib import Path

TASK = """Implement the function 'generate_integers' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def generate_integers(a, b):
    \"\"\"
    Given two positive integers a and b, return the even digits between a
    and b, in ascending order.

    For example:
    generate_integers(2, 8) => [2, 4, 6, 8]
    generate_integers(8, 2) => [2, 4, 6, 8]
    generate_integers(10, 14) => []
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef generate_integers(a, b):\n    """\n    Given two positive integers a and b, return the even digits between a\n    and b, in ascending order.\n\n    For example:\n    generate_integers(2, 8) => [2, 4, 6, 8]\n    generate_integers(8, 2) => [2, 4, 6, 8]\n    generate_integers(10, 14) => []\n    """\n',
    "test_solution.py": 'from solution import generate_integers\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(2, 10) == [2, 4, 6, 8], "Test 1"\n    assert candidate(10, 2) == [2, 4, 6, 8], "Test 2"\n    assert candidate(132, 2) == [2, 4, 6, 8], "Test 3"\n    assert candidate(17,89) == [], "Test 4"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(generate_integers)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import generate_integers\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(2, 10) == [2, 4, 6, 8], "Test 1"\n    assert candidate(10, 2) == [2, 4, 6, 8], "Test 2"\n    assert candidate(132, 2) == [2, 4, 6, 8], "Test 3"\n    assert candidate(17,89) == [], "Test 4"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(generate_integers)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
