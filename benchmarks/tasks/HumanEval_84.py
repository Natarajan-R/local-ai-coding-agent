"""HumanEval task HumanEval_84"""
from pathlib import Path

TASK = """Implement the function 'solve' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def solve(N):
    \"\"\"Given a positive integer N, return the total sum of its digits in binary.
    
    Example
        For N = 1000, the sum of digits will be 1 the output should be "1".
        For N = 150, the sum of digits will be 6 the output should be "110".
        For N = 147, the sum of digits will be 12 the output should be "1100".
    
    Variables:
        @N integer
             Constraints: 0 ≤ N ≤ 10000.
    Output:
         a string of binary number
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef solve(N):\n    """Given a positive integer N, return the total sum of its digits in binary.\n    \n    Example\n        For N = 1000, the sum of digits will be 1 the output should be "1".\n        For N = 150, the sum of digits will be 6 the output should be "110".\n        For N = 147, the sum of digits will be 12 the output should be "1100".\n    \n    Variables:\n        @N integer\n             Constraints: 0 ≤ N ≤ 10000.\n    Output:\n         a string of binary number\n    """\n',
    "test_solution.py": 'from solution import solve\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1000) == "1", "Error"\n    assert candidate(150) == "110", "Error"\n    assert candidate(147) == "1100", "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(333) == "1001", "Error"\n    assert candidate(963) == "10010", "Error"\n\n\n\ndef test_candidate():\n    check(solve)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import solve\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1000) == "1", "Error"\n    assert candidate(150) == "110", "Error"\n    assert candidate(147) == "1100", "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(333) == "1001", "Error"\n    assert candidate(963) == "10010", "Error"\n\n\n\ndef test_candidate():\n    check(solve)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
