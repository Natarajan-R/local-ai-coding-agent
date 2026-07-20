"""HumanEval task HumanEval_134"""
from pathlib import Path

TASK = """Implement the function 'check_if_last_char_is_a_letter' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def check_if_last_char_is_a_letter(txt):
    '''
    Create a function that returns True if the last character
    of a given string is an alphabetical character and is not
    a part of a word, and False otherwise.
    Note: "word" is a group of characters separated by space.

    Examples:
    check_if_last_char_is_a_letter("apple pie") ➞ False
    check_if_last_char_is_a_letter("apple pi e") ➞ True
    check_if_last_char_is_a_letter("apple pi e ") ➞ False
    check_if_last_char_is_a_letter("") ➞ False 
    '''

"""

FILES = {
    "solution.py": '\ndef check_if_last_char_is_a_letter(txt):\n    \'\'\'\n    Create a function that returns True if the last character\n    of a given string is an alphabetical character and is not\n    a part of a word, and False otherwise.\n    Note: "word" is a group of characters separated by space.\n\n    Examples:\n    check_if_last_char_is_a_letter("apple pie") ➞ False\n    check_if_last_char_is_a_letter("apple pi e") ➞ True\n    check_if_last_char_is_a_letter("apple pi e ") ➞ False\n    check_if_last_char_is_a_letter("") ➞ False \n    \'\'\'\n',
    "test_solution.py": 'from solution import check_if_last_char_is_a_letter\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("apple") == False\n    assert candidate("apple pi e") == True\n    assert candidate("eeeee") == False\n    assert candidate("A") == True\n    assert candidate("Pumpkin pie ") == False\n    assert candidate("Pumpkin pie 1") == False\n    assert candidate("") == False\n    assert candidate("eeeee e ") == False\n    assert candidate("apple pie") == False\n    assert candidate("apple pi e ") == False\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(check_if_last_char_is_a_letter)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import check_if_last_char_is_a_letter\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("apple") == False\n    assert candidate("apple pi e") == True\n    assert candidate("eeeee") == False\n    assert candidate("A") == True\n    assert candidate("Pumpkin pie ") == False\n    assert candidate("Pumpkin pie 1") == False\n    assert candidate("") == False\n    assert candidate("eeeee e ") == False\n    assert candidate("apple pie") == False\n    assert candidate("apple pi e ") == False\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(check_if_last_char_is_a_letter)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
