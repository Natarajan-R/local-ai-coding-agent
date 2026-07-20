"""HumanEval task HumanEval_97"""
from pathlib import Path

TASK = """Implement the function 'multiply' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def multiply(a, b):
    \"\"\"Complete the function that takes two integers and returns 
    the product of their unit digits.
    Assume the input is always valid.
    Examples:
    multiply(148, 412) should return 16.
    multiply(19, 28) should return 72.
    multiply(2020, 1851) should return 0.
    multiply(14,-15) should return 20.
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef multiply(a, b):\n    """Complete the function that takes two integers and returns \n    the product of their unit digits.\n    Assume the input is always valid.\n    Examples:\n    multiply(148, 412) should return 16.\n    multiply(19, 28) should return 72.\n    multiply(2020, 1851) should return 0.\n    multiply(14,-15) should return 20.\n    """\n',
    "test_solution.py": 'from solution import multiply\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(148, 412) == 16, "First test error: " + str(candidate(148, 412))                    \n    assert candidate(19, 28) == 72, "Second test error: " + str(candidate(19, 28))           \n    assert candidate(2020, 1851) == 0, "Third test error: " + str(candidate(2020, 1851))\n    assert candidate(14,-15) == 20, "Fourth test error: " + str(candidate(14,-15))      \n    assert candidate(76, 67) == 42, "Fifth test error: " + str(candidate(76, 67))      \n    assert candidate(17, 27) == 49, "Sixth test error: " + str(candidate(17, 27))      \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(0, 1) == 0, "1st edge test error: " + str(candidate(0, 1))\n    assert candidate(0, 0) == 0, "2nd edge test error: " + str(candidate(0, 0))\n\n\n\ndef test_candidate():\n    check(multiply)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import multiply\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(148, 412) == 16, "First test error: " + str(candidate(148, 412))                    \n    assert candidate(19, 28) == 72, "Second test error: " + str(candidate(19, 28))           \n    assert candidate(2020, 1851) == 0, "Third test error: " + str(candidate(2020, 1851))\n    assert candidate(14,-15) == 20, "Fourth test error: " + str(candidate(14,-15))      \n    assert candidate(76, 67) == 42, "Fifth test error: " + str(candidate(76, 67))      \n    assert candidate(17, 27) == 49, "Sixth test error: " + str(candidate(17, 27))      \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(0, 1) == 0, "1st edge test error: " + str(candidate(0, 1))\n    assert candidate(0, 0) == 0, "2nd edge test error: " + str(candidate(0, 0))\n\n\n\ndef test_candidate():\n    check(multiply)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
