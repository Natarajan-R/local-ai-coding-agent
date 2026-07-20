"""HumanEval task HumanEval_125"""
from pathlib import Path

TASK = """Implement the function 'split_words' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def split_words(txt):
    '''
    Given a string of words, return a list of words split on whitespace, if no whitespaces exists in the text you
    should split on commas ',' if no commas exists you should return the number of lower-case letters with odd order in the
    alphabet, ord('a') = 0, ord('b') = 1, ... ord('z') = 25
    Examples
    split_words("Hello world!") ➞ ["Hello", "world!"]
    split_words("Hello,world!") ➞ ["Hello", "world!"]
    split_words("abcdef") == 3 
    '''

"""

FILES = {
    "solution.py": '\ndef split_words(txt):\n    \'\'\'\n    Given a string of words, return a list of words split on whitespace, if no whitespaces exists in the text you\n    should split on commas \',\' if no commas exists you should return the number of lower-case letters with odd order in the\n    alphabet, ord(\'a\') = 0, ord(\'b\') = 1, ... ord(\'z\') = 25\n    Examples\n    split_words("Hello world!") ➞ ["Hello", "world!"]\n    split_words("Hello,world!") ➞ ["Hello", "world!"]\n    split_words("abcdef") == 3 \n    \'\'\'\n',
    "test_solution.py": 'from solution import split_words\ndef check(candidate):\n\n    assert candidate("Hello world!") == ["Hello","world!"]\n    assert candidate("Hello,world!") == ["Hello","world!"]\n    assert candidate("Hello world,!") == ["Hello","world,!"]\n    assert candidate("Hello,Hello,world !") == ["Hello,Hello,world","!"]\n    assert candidate("abcdef") == 3\n    assert candidate("aaabb") == 2\n    assert candidate("aaaBb") == 1\n    assert candidate("") == 0\n\n\ndef test_candidate():\n    check(split_words)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import split_words\ndef check(candidate):\n\n    assert candidate("Hello world!") == ["Hello","world!"]\n    assert candidate("Hello,world!") == ["Hello","world!"]\n    assert candidate("Hello world,!") == ["Hello","world,!"]\n    assert candidate("Hello,Hello,world !") == ["Hello,Hello,world","!"]\n    assert candidate("abcdef") == 3\n    assert candidate("aaabb") == 2\n    assert candidate("aaaBb") == 1\n    assert candidate("") == 0\n\n\ndef test_candidate():\n    check(split_words)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
