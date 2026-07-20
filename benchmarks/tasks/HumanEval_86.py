"""HumanEval task HumanEval_86"""
from pathlib import Path

TASK = """Implement the function 'anti_shuffle' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def anti_shuffle(s):
    \"\"\"
    Write a function that takes a string and returns an ordered version of it.
    Ordered version of string, is a string where all words (separated by space)
    are replaced by a new word where all the characters arranged in
    ascending order based on ascii value.
    Note: You should keep the order of words and blank spaces in the sentence.

    For example:
    anti_shuffle('Hi') returns 'Hi'
    anti_shuffle('hello') returns 'ehllo'
    anti_shuffle('Hello World!!!') returns 'Hello !!!Wdlor'
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef anti_shuffle(s):\n    """\n    Write a function that takes a string and returns an ordered version of it.\n    Ordered version of string, is a string where all words (separated by space)\n    are replaced by a new word where all the characters arranged in\n    ascending order based on ascii value.\n    Note: You should keep the order of words and blank spaces in the sentence.\n\n    For example:\n    anti_shuffle(\'Hi\') returns \'Hi\'\n    anti_shuffle(\'hello\') returns \'ehllo\'\n    anti_shuffle(\'Hello World!!!\') returns \'Hello !!!Wdlor\'\n    """\n',
    "test_solution.py": "from solution import anti_shuffle\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Hi') == 'Hi'\n    assert candidate('hello') == 'ehllo'\n    assert candidate('number') == 'bemnru'\n    assert candidate('abcd') == 'abcd'\n    assert candidate('Hello World!!!') == 'Hello !!!Wdlor'\n    assert candidate('') == ''\n    assert candidate('Hi. My name is Mister Robot. How are you?') == '.Hi My aemn is Meirst .Rboot How aer ?ouy'\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(anti_shuffle)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import anti_shuffle\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Hi') == 'Hi'\n    assert candidate('hello') == 'ehllo'\n    assert candidate('number') == 'bemnru'\n    assert candidate('abcd') == 'abcd'\n    assert candidate('Hello World!!!') == 'Hello !!!Wdlor'\n    assert candidate('') == ''\n    assert candidate('Hi. My name is Mister Robot. How are you?') == '.Hi My aemn is Meirst .Rboot How aer ?ouy'\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(anti_shuffle)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
