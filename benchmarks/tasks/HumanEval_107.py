"""HumanEval task HumanEval_107"""
from pathlib import Path

TASK = """Implement the function 'even_odd_palindrome' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def even_odd_palindrome(n):
    \"\"\"
    Given a positive integer n, return a tuple that has the number of even and odd
    integer palindromes that fall within the range(1, n), inclusive.

    Example 1:

        Input: 3
        Output: (1, 2)
        Explanation:
        Integer palindrome are 1, 2, 3. one of them is even, and two of them are odd.

    Example 2:

        Input: 12
        Output: (4, 6)
        Explanation:
        Integer palindrome are 1, 2, 3, 4, 5, 6, 7, 8, 9, 11. four of them are even, and 6 of them are odd.

    Note:
        1. 1 <= n <= 10^3
        2. returned tuple has the number of even and odd integer palindromes respectively.
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef even_odd_palindrome(n):\n    """\n    Given a positive integer n, return a tuple that has the number of even and odd\n    integer palindromes that fall within the range(1, n), inclusive.\n\n    Example 1:\n\n        Input: 3\n        Output: (1, 2)\n        Explanation:\n        Integer palindrome are 1, 2, 3. one of them is even, and two of them are odd.\n\n    Example 2:\n\n        Input: 12\n        Output: (4, 6)\n        Explanation:\n        Integer palindrome are 1, 2, 3, 4, 5, 6, 7, 8, 9, 11. four of them are even, and 6 of them are odd.\n\n    Note:\n        1. 1 <= n <= 10^3\n        2. returned tuple has the number of even and odd integer palindromes respectively.\n    """\n',
    "test_solution.py": 'from solution import even_odd_palindrome\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(123) == (8, 13)\n    assert candidate(12) == (4, 6)\n    assert candidate(3) == (1, 2)\n    assert candidate(63) == (6, 8)\n    assert candidate(25) == (5, 6)\n    assert candidate(19) == (4, 6)\n    assert candidate(9) == (4, 5), "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1) == (0, 1), "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(even_odd_palindrome)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import even_odd_palindrome\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(123) == (8, 13)\n    assert candidate(12) == (4, 6)\n    assert candidate(3) == (1, 2)\n    assert candidate(63) == (6, 8)\n    assert candidate(25) == (5, 6)\n    assert candidate(19) == (4, 6)\n    assert candidate(9) == (4, 5), "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1) == (0, 1), "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(even_odd_palindrome)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
