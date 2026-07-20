"""HumanEval task HumanEval_130"""
from pathlib import Path

TASK = """Implement the function 'tri' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def tri(n):
    \"\"\"Everyone knows Fibonacci sequence, it was studied deeply by mathematicians in 
    the last couple centuries. However, what people don't know is Tribonacci sequence.
    Tribonacci sequence is defined by the recurrence:
    tri(1) = 3
    tri(n) = 1 + n / 2, if n is even.
    tri(n) =  tri(n - 1) + tri(n - 2) + tri(n + 1), if n is odd.
    For example:
    tri(2) = 1 + (2 / 2) = 2
    tri(4) = 3
    tri(3) = tri(2) + tri(1) + tri(4)
           = 2 + 3 + 3 = 8 
    You are given a non-negative integer number n, you have to a return a list of the 
    first n + 1 numbers of the Tribonacci sequence.
    Examples:
    tri(3) = [1, 3, 2, 8]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef tri(n):\n    """Everyone knows Fibonacci sequence, it was studied deeply by mathematicians in \n    the last couple centuries. However, what people don\'t know is Tribonacci sequence.\n    Tribonacci sequence is defined by the recurrence:\n    tri(1) = 3\n    tri(n) = 1 + n / 2, if n is even.\n    tri(n) =  tri(n - 1) + tri(n - 2) + tri(n + 1), if n is odd.\n    For example:\n    tri(2) = 1 + (2 / 2) = 2\n    tri(4) = 3\n    tri(3) = tri(2) + tri(1) + tri(4)\n           = 2 + 3 + 3 = 8 \n    You are given a non-negative integer number n, you have to a return a list of the \n    first n + 1 numbers of the Tribonacci sequence.\n    Examples:\n    tri(3) = [1, 3, 2, 8]\n    """\n',
    "test_solution.py": 'from solution import tri\ndef check(candidate):\n\n    # Check some simple cases\n    \n    assert candidate(3) == [1, 3, 2.0, 8.0]\n    assert candidate(4) == [1, 3, 2.0, 8.0, 3.0]\n    assert candidate(5) == [1, 3, 2.0, 8.0, 3.0, 15.0]\n    assert candidate(6) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0]\n    assert candidate(7) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0]\n    assert candidate(8) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0, 5.0]\n    assert candidate(9) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0, 5.0, 35.0]\n    assert candidate(20) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0, 5.0, 35.0, 6.0, 48.0, 7.0, 63.0, 8.0, 80.0, 9.0, 99.0, 10.0, 120.0, 11.0]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(0) == [1]\n    assert candidate(1) == [1, 3]\n\n\ndef test_candidate():\n    check(tri)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import tri\ndef check(candidate):\n\n    # Check some simple cases\n    \n    assert candidate(3) == [1, 3, 2.0, 8.0]\n    assert candidate(4) == [1, 3, 2.0, 8.0, 3.0]\n    assert candidate(5) == [1, 3, 2.0, 8.0, 3.0, 15.0]\n    assert candidate(6) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0]\n    assert candidate(7) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0]\n    assert candidate(8) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0, 5.0]\n    assert candidate(9) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0, 5.0, 35.0]\n    assert candidate(20) == [1, 3, 2.0, 8.0, 3.0, 15.0, 4.0, 24.0, 5.0, 35.0, 6.0, 48.0, 7.0, 63.0, 8.0, 80.0, 9.0, 99.0, 10.0, 120.0, 11.0]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(0) == [1]\n    assert candidate(1) == [1, 3]\n\n\ndef test_candidate():\n    check(tri)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
