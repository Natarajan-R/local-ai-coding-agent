"""HumanEval task HumanEval_101"""
from pathlib import Path

TASK = """Implement the function 'words_string' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def words_string(s):
    \"\"\"
    You will be given a string of words separated by commas or spaces. Your task is
    to split the string into words and return an array of the words.
    
    For example:
    words_string("Hi, my name is John") == ["Hi", "my", "name", "is", "John"]
    words_string("One, two, three, four, five, six") == ["One", "two", "three", "four", "five", "six"]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef words_string(s):\n    """\n    You will be given a string of words separated by commas or spaces. Your task is\n    to split the string into words and return an array of the words.\n    \n    For example:\n    words_string("Hi, my name is John") == ["Hi", "my", "name", "is", "John"]\n    words_string("One, two, three, four, five, six") == ["One", "two", "three", "four", "five", "six"]\n    """\n',
    "test_solution.py": 'from solution import words_string\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate("Hi, my name is John") == ["Hi", "my", "name", "is", "John"]\n    assert candidate("One, two, three, four, five, six") == ["One", "two", "three", "four", "five", "six"]\n    assert candidate("Hi, my name") == ["Hi", "my", "name"]\n    assert candidate("One,, two, three, four, five, six,") == ["One", "two", "three", "four", "five", "six"]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate("") == []\n    assert candidate("ahmed     , gamal") == ["ahmed", "gamal"]\n\n\n\ndef test_candidate():\n    check(words_string)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import words_string\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate("Hi, my name is John") == ["Hi", "my", "name", "is", "John"]\n    assert candidate("One, two, three, four, five, six") == ["One", "two", "three", "four", "five", "six"]\n    assert candidate("Hi, my name") == ["Hi", "my", "name"]\n    assert candidate("One,, two, three, four, five, six,") == ["One", "two", "three", "four", "five", "six"]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate("") == []\n    assert candidate("ahmed     , gamal") == ["ahmed", "gamal"]\n\n\n\ndef test_candidate():\n    check(words_string)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
