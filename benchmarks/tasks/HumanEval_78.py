"""HumanEval task HumanEval_78"""
from pathlib import Path

TASK = """Implement the function 'hex_key' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def hex_key(num):
    \"\"\"You have been tasked to write a function that receives 
    a hexadecimal number as a string and counts the number of hexadecimal 
    digits that are primes (prime number, or a prime, is a natural number 
    greater than 1 that is not a product of two smaller natural numbers).
    Hexadecimal digits are 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E, F.
    Prime numbers are 2, 3, 5, 7, 11, 13, 17,...
    So you have to determine a number of the following digits: 2, 3, 5, 7, 
    B (=decimal 11), D (=decimal 13).
    Note: you may assume the input is always correct or empty string, 
    and symbols A,B,C,D,E,F are always uppercase.
    Examples:
    For num = "AB" the output should be 1.
    For num = "1077E" the output should be 2.
    For num = "ABED1A33" the output should be 4.
    For num = "123456789ABCDEF0" the output should be 6.
    For num = "2020" the output should be 2.
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef hex_key(num):\n    """You have been tasked to write a function that receives \n    a hexadecimal number as a string and counts the number of hexadecimal \n    digits that are primes (prime number, or a prime, is a natural number \n    greater than 1 that is not a product of two smaller natural numbers).\n    Hexadecimal digits are 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E, F.\n    Prime numbers are 2, 3, 5, 7, 11, 13, 17,...\n    So you have to determine a number of the following digits: 2, 3, 5, 7, \n    B (=decimal 11), D (=decimal 13).\n    Note: you may assume the input is always correct or empty string, \n    and symbols A,B,C,D,E,F are always uppercase.\n    Examples:\n    For num = "AB" the output should be 1.\n    For num = "1077E" the output should be 2.\n    For num = "ABED1A33" the output should be 4.\n    For num = "123456789ABCDEF0" the output should be 6.\n    For num = "2020" the output should be 2.\n    """\n',
    "test_solution.py": 'from solution import hex_key\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("AB") == 1, "First test error: " + str(candidate("AB"))      \n    assert candidate("1077E") == 2, "Second test error: " + str(candidate("1077E"))  \n    assert candidate("ABED1A33") == 4, "Third test error: " + str(candidate("ABED1A33"))      \n    assert candidate("2020") == 2, "Fourth test error: " + str(candidate("2020"))  \n    assert candidate("123456789ABCDEF0") == 6, "Fifth test error: " + str(candidate("123456789ABCDEF0"))      \n    assert candidate("112233445566778899AABBCCDDEEFF00") == 12, "Sixth test error: " + str(candidate("112233445566778899AABBCCDDEEFF00"))  \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([]) == 0\n\n\n\ndef test_candidate():\n    check(hex_key)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import hex_key\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("AB") == 1, "First test error: " + str(candidate("AB"))      \n    assert candidate("1077E") == 2, "Second test error: " + str(candidate("1077E"))  \n    assert candidate("ABED1A33") == 4, "Third test error: " + str(candidate("ABED1A33"))      \n    assert candidate("2020") == 2, "Fourth test error: " + str(candidate("2020"))  \n    assert candidate("123456789ABCDEF0") == 6, "Fifth test error: " + str(candidate("123456789ABCDEF0"))      \n    assert candidate("112233445566778899AABBCCDDEEFF00") == 12, "Sixth test error: " + str(candidate("112233445566778899AABBCCDDEEFF00"))  \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([]) == 0\n\n\n\ndef test_candidate():\n    check(hex_key)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
