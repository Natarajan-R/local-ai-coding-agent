"""HumanEval task HumanEval_89"""
from pathlib import Path

TASK = """Implement the function 'encrypt' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def encrypt(s):
    \"\"\"Create a function encrypt that takes a string as an argument and
    returns a string encrypted with the alphabet being rotated. 
    The alphabet should be rotated in a manner such that the letters 
    shift down by two multiplied to two places.
    For example:
    encrypt('hi') returns 'lm'
    encrypt('asdfghjkl') returns 'ewhjklnop'
    encrypt('gf') returns 'kj'
    encrypt('et') returns 'ix'
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef encrypt(s):\n    """Create a function encrypt that takes a string as an argument and\n    returns a string encrypted with the alphabet being rotated. \n    The alphabet should be rotated in a manner such that the letters \n    shift down by two multiplied to two places.\n    For example:\n    encrypt(\'hi\') returns \'lm\'\n    encrypt(\'asdfghjkl\') returns \'ewhjklnop\'\n    encrypt(\'gf\') returns \'kj\'\n    encrypt(\'et\') returns \'ix\'\n    """\n',
    "test_solution.py": 'from solution import encrypt\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'hi\') == \'lm\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'asdfghjkl\') == \'ewhjklnop\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'gf\') == \'kj\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'et\') == \'ix\', "This prints if this assert fails 1 (good for debugging!)"\n\n    assert candidate(\'faewfawefaewg\')==\'jeiajeaijeiak\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'hellomyfriend\')==\'lippsqcjvmirh\', "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(\'dxzdlmnilfuhmilufhlihufnmlimnufhlimnufhfucufh\')==\'hbdhpqrmpjylqmpyjlpmlyjrqpmqryjlpmqryjljygyjl\', "This prints if this assert fails 3 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'a\')==\'e\', "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(encrypt)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import encrypt\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'hi\') == \'lm\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'asdfghjkl\') == \'ewhjklnop\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'gf\') == \'kj\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'et\') == \'ix\', "This prints if this assert fails 1 (good for debugging!)"\n\n    assert candidate(\'faewfawefaewg\')==\'jeiajeaijeiak\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'hellomyfriend\')==\'lippsqcjvmirh\', "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(\'dxzdlmnilfuhmilufhlihufnmlimnufhlimnufhfucufh\')==\'hbdhpqrmpjylqmpyjlpmlyjrqpmqryjlpmqryjljygyjl\', "This prints if this assert fails 3 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'a\')==\'e\', "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(encrypt)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
