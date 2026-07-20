"""HumanEval task HumanEval_123"""
from pathlib import Path

TASK = """Implement the function 'get_odd_collatz' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def get_odd_collatz(n):
    \"\"\"
    Given a positive integer n, return a sorted list that has the odd numbers in collatz sequence.

    The Collatz conjecture is a conjecture in mathematics that concerns a sequence defined
    as follows: start with any positive integer n. Then each term is obtained from the 
    previous term as follows: if the previous term is even, the next term is one half of 
    the previous term. If the previous term is odd, the next term is 3 times the previous
    term plus 1. The conjecture is that no matter what value of n, the sequence will always reach 1.

    Note: 
        1. Collatz(1) is [1].
        2. returned list sorted in increasing order.

    For example:
    get_odd_collatz(5) returns [1, 5] # The collatz sequence for 5 is [5, 16, 8, 4, 2, 1], so the odd numbers are only 1, and 5.
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef get_odd_collatz(n):\n    """\n    Given a positive integer n, return a sorted list that has the odd numbers in collatz sequence.\n\n    The Collatz conjecture is a conjecture in mathematics that concerns a sequence defined\n    as follows: start with any positive integer n. Then each term is obtained from the \n    previous term as follows: if the previous term is even, the next term is one half of \n    the previous term. If the previous term is odd, the next term is 3 times the previous\n    term plus 1. The conjecture is that no matter what value of n, the sequence will always reach 1.\n\n    Note: \n        1. Collatz(1) is [1].\n        2. returned list sorted in increasing order.\n\n    For example:\n    get_odd_collatz(5) returns [1, 5] # The collatz sequence for 5 is [5, 16, 8, 4, 2, 1], so the odd numbers are only 1, and 5.\n    """\n',
    "test_solution.py": 'from solution import get_odd_collatz\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(14) == [1, 5, 7, 11, 13, 17]\n    assert candidate(5) == [1, 5]\n    assert candidate(12) == [1, 3, 5], "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1) == [1], "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(get_odd_collatz)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import get_odd_collatz\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(14) == [1, 5, 7, 11, 13, 17]\n    assert candidate(5) == [1, 5]\n    assert candidate(12) == [1, 3, 5], "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1) == [1], "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(get_odd_collatz)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
