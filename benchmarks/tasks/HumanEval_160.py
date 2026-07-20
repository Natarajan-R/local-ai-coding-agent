"""HumanEval task HumanEval_160"""
from pathlib import Path

TASK = """Implement the function 'do_algebra' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def do_algebra(operator, operand):
    \"\"\"
    Given two lists operator, and operand. The first list has basic algebra operations, and 
    the second list is a list of integers. Use the two given lists to build the algebric 
    expression and return the evaluation of this expression.

    The basic algebra operations:
    Addition ( + ) 
    Subtraction ( - ) 
    Multiplication ( * ) 
    Floor division ( // ) 
    Exponentiation ( ** ) 

    Example:
    operator['+', '*', '-']
    array = [2, 3, 4, 5]
    result = 2 + 3 * 4 - 5
    => result = 9

    Note:
        The length of operator list is equal to the length of operand list minus one.
        Operand is a list of of non-negative integers.
        Operator list has at least one operator, and operand list has at least two operands.

    \"\"\"

"""

FILES = {
    "solution.py": '\ndef do_algebra(operator, operand):\n    """\n    Given two lists operator, and operand. The first list has basic algebra operations, and \n    the second list is a list of integers. Use the two given lists to build the algebric \n    expression and return the evaluation of this expression.\n\n    The basic algebra operations:\n    Addition ( + ) \n    Subtraction ( - ) \n    Multiplication ( * ) \n    Floor division ( // ) \n    Exponentiation ( ** ) \n\n    Example:\n    operator[\'+\', \'*\', \'-\']\n    array = [2, 3, 4, 5]\n    result = 2 + 3 * 4 - 5\n    => result = 9\n\n    Note:\n        The length of operator list is equal to the length of operand list minus one.\n        Operand is a list of of non-negative integers.\n        Operator list has at least one operator, and operand list has at least two operands.\n\n    """\n',
    "test_solution.py": 'from solution import do_algebra\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([\'**\', \'*\', \'+\'], [2, 3, 4, 5]) == 37\n    assert candidate([\'+\', \'*\', \'-\'], [2, 3, 4, 5]) == 9\n    assert candidate([\'//\', \'*\'], [7, 3, 4]) == 8, "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(do_algebra)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import do_algebra\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([\'**\', \'*\', \'+\'], [2, 3, 4, 5]) == 37\n    assert candidate([\'+\', \'*\', \'-\'], [2, 3, 4, 5]) == 9\n    assert candidate([\'//\', \'*\'], [7, 3, 4]) == 8, "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(do_algebra)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
