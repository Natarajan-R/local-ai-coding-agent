"""HumanEval task HumanEval_99"""
from pathlib import Path

TASK = """Implement the function 'closest_integer' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def closest_integer(value):
    '''
    Create a function that takes a value (string) representing a number
    and returns the closest integer to it. If the number is equidistant
    from two integers, round it away from zero.

    Examples
    >>> closest_integer("10")
    10
    >>> closest_integer("15.3")
    15

    Note:
    Rounding away from zero means that if the given number is equidistant
    from two integers, the one you should return is the one that is the
    farthest from zero. For example closest_integer("14.5") should
    return 15 and closest_integer("-14.5") should return -15.
    '''

"""

FILES = {
    "solution.py": '\ndef closest_integer(value):\n    \'\'\'\n    Create a function that takes a value (string) representing a number\n    and returns the closest integer to it. If the number is equidistant\n    from two integers, round it away from zero.\n\n    Examples\n    >>> closest_integer("10")\n    10\n    >>> closest_integer("15.3")\n    15\n\n    Note:\n    Rounding away from zero means that if the given number is equidistant\n    from two integers, the one you should return is the one that is the\n    farthest from zero. For example closest_integer("14.5") should\n    return 15 and closest_integer("-14.5") should return -15.\n    \'\'\'\n',
    "test_solution.py": 'from solution import closest_integer\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("10") == 10, "Test 1"\n    assert candidate("14.5") == 15, "Test 2"\n    assert candidate("-15.5") == -16, "Test 3"\n    assert candidate("15.3") == 15, "Test 3"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("0") == 0, "Test 0"\n\n\n\ndef test_candidate():\n    check(closest_integer)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import closest_integer\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("10") == 10, "Test 1"\n    assert candidate("14.5") == 15, "Test 2"\n    assert candidate("-15.5") == -16, "Test 3"\n    assert candidate("15.3") == 15, "Test 3"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("0") == 0, "Test 0"\n\n\n\ndef test_candidate():\n    check(closest_integer)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
