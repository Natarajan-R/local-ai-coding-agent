"""HumanEval task HumanEval_112"""
from pathlib import Path

TASK = """Implement the function 'reverse_delete' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def reverse_delete(s,c):
    \"\"\"Task
    We are given two strings s and c, you have to deleted all the characters in s that are equal to any character in c
    then check if the result string is palindrome.
    A string is called palindrome if it reads the same backward as forward.
    You should return a tuple containing the result string and True/False for the check.
    Example
    For s = "abcde", c = "ae", the result should be ('bcd',False)
    For s = "abcdef", c = "b"  the result should be ('acdef',False)
    For s = "abcdedcba", c = "ab", the result should be ('cdedc',True)
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef reverse_delete(s,c):\n    """Task\n    We are given two strings s and c, you have to deleted all the characters in s that are equal to any character in c\n    then check if the result string is palindrome.\n    A string is called palindrome if it reads the same backward as forward.\n    You should return a tuple containing the result string and True/False for the check.\n    Example\n    For s = "abcde", c = "ae", the result should be (\'bcd\',False)\n    For s = "abcdef", c = "b"  the result should be (\'acdef\',False)\n    For s = "abcdedcba", c = "ab", the result should be (\'cdedc\',True)\n    """\n',
    "test_solution.py": 'from solution import reverse_delete\ndef check(candidate):\n\n    assert candidate("abcde","ae") == (\'bcd\',False)\n    assert candidate("abcdef", "b") == (\'acdef\',False)\n    assert candidate("abcdedcba","ab") == (\'cdedc\',True)\n    assert candidate("dwik","w") == (\'dik\',False)\n    assert candidate("a","a") == (\'\',True)\n    assert candidate("abcdedcba","") == (\'abcdedcba\',True)\n    assert candidate("abcdedcba","v") == (\'abcdedcba\',True)\n    assert candidate("vabba","v") == (\'abba\',True)\n    assert candidate("mamma", "mia") == ("", True)\n\n\ndef test_candidate():\n    check(reverse_delete)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import reverse_delete\ndef check(candidate):\n\n    assert candidate("abcde","ae") == (\'bcd\',False)\n    assert candidate("abcdef", "b") == (\'acdef\',False)\n    assert candidate("abcdedcba","ab") == (\'cdedc\',True)\n    assert candidate("dwik","w") == (\'dik\',False)\n    assert candidate("a","a") == (\'\',True)\n    assert candidate("abcdedcba","") == (\'abcdedcba\',True)\n    assert candidate("abcdedcba","v") == (\'abcdedcba\',True)\n    assert candidate("vabba","v") == (\'abba\',True)\n    assert candidate("mamma", "mia") == ("", True)\n\n\ndef test_candidate():\n    check(reverse_delete)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
