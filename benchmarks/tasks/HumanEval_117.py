"""HumanEval task HumanEval_117"""
from pathlib import Path

TASK = """Implement the function 'select_words' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def select_words(s, n):
    \"\"\"Given a string s and a natural number n, you have been tasked to implement 
    a function that returns a list of all words from string s that contain exactly 
    n consonants, in order these words appear in the string s.
    If the string s is empty then the function should return an empty list.
    Note: you may assume the input string contains only letters and spaces.
    Examples:
    select_words("Mary had a little lamb", 4) ==> ["little"]
    select_words("Mary had a little lamb", 3) ==> ["Mary", "lamb"]
    select_words("simple white space", 2) ==> []
    select_words("Hello world", 4) ==> ["world"]
    select_words("Uncle sam", 3) ==> ["Uncle"]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef select_words(s, n):\n    """Given a string s and a natural number n, you have been tasked to implement \n    a function that returns a list of all words from string s that contain exactly \n    n consonants, in order these words appear in the string s.\n    If the string s is empty then the function should return an empty list.\n    Note: you may assume the input string contains only letters and spaces.\n    Examples:\n    select_words("Mary had a little lamb", 4) ==> ["little"]\n    select_words("Mary had a little lamb", 3) ==> ["Mary", "lamb"]\n    select_words("simple white space", 2) ==> []\n    select_words("Hello world", 4) ==> ["world"]\n    select_words("Uncle sam", 3) ==> ["Uncle"]\n    """\n',
    "test_solution.py": 'from solution import select_words\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Mary had a little lamb", 4) == ["little"], "First test error: " + str(candidate("Mary had a little lamb", 4))      \n    assert candidate("Mary had a little lamb", 3) == ["Mary", "lamb"], "Second test error: " + str(candidate("Mary had a little lamb", 3))  \n    assert candidate("simple white space", 2) == [], "Third test error: " + str(candidate("simple white space", 2))      \n    assert candidate("Hello world", 4) == ["world"], "Fourth test error: " + str(candidate("Hello world", 4))  \n    assert candidate("Uncle sam", 3) == ["Uncle"], "Fifth test error: " + str(candidate("Uncle sam", 3))\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("", 4) == [], "1st edge test error: " + str(candidate("", 4))\n    assert candidate("a b c d e f", 1) == ["b", "c", "d", "f"], "2nd edge test error: " + str(candidate("a b c d e f", 1))\n\n\n\ndef test_candidate():\n    check(select_words)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import select_words\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Mary had a little lamb", 4) == ["little"], "First test error: " + str(candidate("Mary had a little lamb", 4))      \n    assert candidate("Mary had a little lamb", 3) == ["Mary", "lamb"], "Second test error: " + str(candidate("Mary had a little lamb", 3))  \n    assert candidate("simple white space", 2) == [], "Third test error: " + str(candidate("simple white space", 2))      \n    assert candidate("Hello world", 4) == ["world"], "Fourth test error: " + str(candidate("Hello world", 4))  \n    assert candidate("Uncle sam", 3) == ["Uncle"], "Fifth test error: " + str(candidate("Uncle sam", 3))\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("", 4) == [], "1st edge test error: " + str(candidate("", 4))\n    assert candidate("a b c d e f", 1) == ["b", "c", "d", "f"], "2nd edge test error: " + str(candidate("a b c d e f", 1))\n\n\n\ndef test_candidate():\n    check(select_words)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
