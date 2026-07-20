"""HumanEval task HumanEval_10"""
from pathlib import Path

TASK = """Implement the function 'make_palindrome' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def is_palindrome(string: str) -> bool:
    \"\"\" Test if given string is a palindrome \"\"\"
    return string == string[::-1]


def make_palindrome(string: str) -> str:
    \"\"\" Find the shortest palindrome that begins with a supplied string.
    Algorithm idea is simple:
    - Find the longest postfix of supplied string that is a palindrome.
    - Append to the end of the string reverse of a string prefix that comes before the palindromic suffix.
    >>> make_palindrome('')
    ''
    >>> make_palindrome('cat')
    'catac'
    >>> make_palindrome('cata')
    'catac'
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef is_palindrome(string: str) -> bool:\n    """ Test if given string is a palindrome """\n    return string == string[::-1]\n\n\ndef make_palindrome(string: str) -> str:\n    """ Find the shortest palindrome that begins with a supplied string.\n    Algorithm idea is simple:\n    - Find the longest postfix of supplied string that is a palindrome.\n    - Append to the end of the string reverse of a string prefix that comes before the palindromic suffix.\n    >>> make_palindrome(\'\')\n    \'\'\n    >>> make_palindrome(\'cat\')\n    \'catac\'\n    >>> make_palindrome(\'cata\')\n    \'catac\'\n    """\n',
    "test_solution.py": "from solution import make_palindrome\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == ''\n    assert candidate('x') == 'x'\n    assert candidate('xyz') == 'xyzyx'\n    assert candidate('xyx') == 'xyx'\n    assert candidate('jerry') == 'jerryrrej'\n\n\ndef test_candidate():\n    check(make_palindrome)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import make_palindrome\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == ''\n    assert candidate('x') == 'x'\n    assert candidate('xyz') == 'xyzyx'\n    assert candidate('xyx') == 'xyx'\n    assert candidate('jerry') == 'jerryrrej'\n\n\ndef test_candidate():\n    check(make_palindrome)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
