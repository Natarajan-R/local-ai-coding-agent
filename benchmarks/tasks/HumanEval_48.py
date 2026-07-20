"""HumanEval task HumanEval_48"""
from pathlib import Path

TASK = """Implement the function 'is_palindrome' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def is_palindrome(text: str):
    \"\"\"
    Checks if given string is a palindrome
    >>> is_palindrome('')
    True
    >>> is_palindrome('aba')
    True
    >>> is_palindrome('aaaaa')
    True
    >>> is_palindrome('zbcd')
    False
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef is_palindrome(text: str):\n    """\n    Checks if given string is a palindrome\n    >>> is_palindrome(\'\')\n    True\n    >>> is_palindrome(\'aba\')\n    True\n    >>> is_palindrome(\'aaaaa\')\n    True\n    >>> is_palindrome(\'zbcd\')\n    False\n    """\n',
    "test_solution.py": "from solution import is_palindrome\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate('') == True\n    assert candidate('aba') == True\n    assert candidate('aaaaa') == True\n    assert candidate('zbcd') == False\n    assert candidate('xywyx') == True\n    assert candidate('xywyz') == False\n    assert candidate('xywzx') == False\n\n\n\ndef test_candidate():\n    check(is_palindrome)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import is_palindrome\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate('') == True\n    assert candidate('aba') == True\n    assert candidate('aaaaa') == True\n    assert candidate('zbcd') == False\n    assert candidate('xywyx') == True\n    assert candidate('xywyz') == False\n    assert candidate('xywzx') == False\n\n\n\ndef test_candidate():\n    check(is_palindrome)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
