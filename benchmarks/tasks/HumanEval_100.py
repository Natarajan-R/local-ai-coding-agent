"""HumanEval task HumanEval_100"""
from pathlib import Path

TASK = """Implement the function 'make_a_pile' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def make_a_pile(n):
    \"\"\"
    Given a positive integer n, you have to make a pile of n levels of stones.
    The first level has n stones.
    The number of stones in the next level is:
        - the next odd number if n is odd.
        - the next even number if n is even.
    Return the number of stones in each level in a list, where element at index
    i represents the number of stones in the level (i+1).

    Examples:
    >>> make_a_pile(3)
    [3, 5, 7]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef make_a_pile(n):\n    """\n    Given a positive integer n, you have to make a pile of n levels of stones.\n    The first level has n stones.\n    The number of stones in the next level is:\n        - the next odd number if n is odd.\n        - the next even number if n is even.\n    Return the number of stones in each level in a list, where element at index\n    i represents the number of stones in the level (i+1).\n\n    Examples:\n    >>> make_a_pile(3)\n    [3, 5, 7]\n    """\n',
    "test_solution.py": 'from solution import make_a_pile\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(3) == [3, 5, 7], "Test 3"\n    assert candidate(4) == [4,6,8,10], "Test 4"\n    assert candidate(5) == [5, 7, 9, 11, 13]\n    assert candidate(6) == [6, 8, 10, 12, 14, 16]\n    assert candidate(8) == [8, 10, 12, 14, 16, 18, 20, 22]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(make_a_pile)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import make_a_pile\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(3) == [3, 5, 7], "Test 3"\n    assert candidate(4) == [4,6,8,10], "Test 4"\n    assert candidate(5) == [5, 7, 9, 11, 13]\n    assert candidate(6) == [6, 8, 10, 12, 14, 16]\n    assert candidate(8) == [8, 10, 12, 14, 16, 18, 20, 22]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(make_a_pile)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
