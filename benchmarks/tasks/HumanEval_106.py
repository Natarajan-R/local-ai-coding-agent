"""HumanEval task HumanEval_106"""
from pathlib import Path

TASK = """Implement the function 'f' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def f(n):
    \"\"\" Implement the function f that takes n as a parameter,
    and returns a list of size n, such that the value of the element at index i is the factorial of i if i is even
    or the sum of numbers from 1 to i otherwise.
    i starts from 1.
    the factorial of i is the multiplication of the numbers from 1 to i (1 * 2 * ... * i).
    Example:
    f(5) == [1, 2, 6, 24, 15]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef f(n):\n    """ Implement the function f that takes n as a parameter,\n    and returns a list of size n, such that the value of the element at index i is the factorial of i if i is even\n    or the sum of numbers from 1 to i otherwise.\n    i starts from 1.\n    the factorial of i is the multiplication of the numbers from 1 to i (1 * 2 * ... * i).\n    Example:\n    f(5) == [1, 2, 6, 24, 15]\n    """\n',
    "test_solution.py": 'from solution import f\ndef check(candidate):\n\n    assert candidate(5) == [1, 2, 6, 24, 15]\n    assert candidate(7) == [1, 2, 6, 24, 15, 720, 28]\n    assert candidate(1) == [1]\n    assert candidate(3) == [1, 2, 6]\n\n\ndef test_candidate():\n    check(f)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import f\ndef check(candidate):\n\n    assert candidate(5) == [1, 2, 6, 24, 15]\n    assert candidate(7) == [1, 2, 6, 24, 15, 720, 28]\n    assert candidate(1) == [1]\n    assert candidate(3) == [1, 2, 6]\n\n\ndef test_candidate():\n    check(f)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
