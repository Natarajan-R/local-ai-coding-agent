"""HumanEval task HumanEval_79"""
from pathlib import Path

TASK = """Implement the function 'decimal_to_binary' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def decimal_to_binary(decimal):
    \"\"\"You will be given a number in decimal form and your task is to convert it to
    binary format. The function should return a string, with each character representing a binary
    number. Each character in the string will be '0' or '1'.

    There will be an extra couple of characters 'db' at the beginning and at the end of the string.
    The extra characters are there to help with the format.

    Examples:
    decimal_to_binary(15)   # returns "db1111db"
    decimal_to_binary(32)   # returns "db100000db"
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef decimal_to_binary(decimal):\n    """You will be given a number in decimal form and your task is to convert it to\n    binary format. The function should return a string, with each character representing a binary\n    number. Each character in the string will be \'0\' or \'1\'.\n\n    There will be an extra couple of characters \'db\' at the beginning and at the end of the string.\n    The extra characters are there to help with the format.\n\n    Examples:\n    decimal_to_binary(15)   # returns "db1111db"\n    decimal_to_binary(32)   # returns "db100000db"\n    """\n',
    "test_solution.py": 'from solution import decimal_to_binary\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(0) == "db0db"\n    assert candidate(32) == "db100000db"\n    assert candidate(103) == "db1100111db"\n    assert candidate(15) == "db1111db", "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(decimal_to_binary)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import decimal_to_binary\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(0) == "db0db"\n    assert candidate(32) == "db100000db"\n    assert candidate(103) == "db1100111db"\n    assert candidate(15) == "db1111db", "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(decimal_to_binary)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
