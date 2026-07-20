"""HumanEval task HumanEval_144"""
from pathlib import Path

TASK = """Implement the function 'simplify' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def simplify(x, n):
    \"\"\"Your task is to implement a function that will simplify the expression
    x * n. The function returns True if x * n evaluates to a whole number and False
    otherwise. Both x and n, are string representation of a fraction, and have the following format,
    <numerator>/<denominator> where both numerator and denominator are positive whole numbers.

    You can assume that x, and n are valid fractions, and do not have zero as denominator.

    simplify("1/5", "5/1") = True
    simplify("1/6", "2/1") = False
    simplify("7/10", "10/2") = False
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef simplify(x, n):\n    """Your task is to implement a function that will simplify the expression\n    x * n. The function returns True if x * n evaluates to a whole number and False\n    otherwise. Both x and n, are string representation of a fraction, and have the following format,\n    <numerator>/<denominator> where both numerator and denominator are positive whole numbers.\n\n    You can assume that x, and n are valid fractions, and do not have zero as denominator.\n\n    simplify("1/5", "5/1") = True\n    simplify("1/6", "2/1") = False\n    simplify("7/10", "10/2") = False\n    """\n',
    "test_solution.py": 'from solution import simplify\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("1/5", "5/1") == True, \'test1\'\n    assert candidate("1/6", "2/1") == False, \'test2\'\n    assert candidate("5/1", "3/1") == True, \'test3\'\n    assert candidate("7/10", "10/2") == False, \'test4\'\n    assert candidate("2/10", "50/10") == True, \'test5\'\n    assert candidate("7/2", "4/2") == True, \'test6\'\n    assert candidate("11/6", "6/1") == True, \'test7\'\n    assert candidate("2/3", "5/2") == False, \'test8\'\n    assert candidate("5/2", "3/5") == False, \'test9\'\n    assert candidate("2/4", "8/4") == True, \'test10\'\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("2/4", "4/2") == True, \'test11\'\n    assert candidate("1/5", "5/1") == True, \'test12\'\n    assert candidate("1/5", "1/5") == False, \'test13\'\n\n\n\ndef test_candidate():\n    check(simplify)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import simplify\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("1/5", "5/1") == True, \'test1\'\n    assert candidate("1/6", "2/1") == False, \'test2\'\n    assert candidate("5/1", "3/1") == True, \'test3\'\n    assert candidate("7/10", "10/2") == False, \'test4\'\n    assert candidate("2/10", "50/10") == True, \'test5\'\n    assert candidate("7/2", "4/2") == True, \'test6\'\n    assert candidate("11/6", "6/1") == True, \'test7\'\n    assert candidate("2/3", "5/2") == False, \'test8\'\n    assert candidate("5/2", "3/5") == False, \'test9\'\n    assert candidate("2/4", "8/4") == True, \'test10\'\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("2/4", "4/2") == True, \'test11\'\n    assert candidate("1/5", "5/1") == True, \'test12\'\n    assert candidate("1/5", "1/5") == False, \'test13\'\n\n\n\ndef test_candidate():\n    check(simplify)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
