"""HumanEval task HumanEval_161"""
from pathlib import Path

TASK = """Implement the function 'solve' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def solve(s):
    \"\"\"You are given a string s.
    if s[i] is a letter, reverse its case from lower to upper or vise versa, 
    otherwise keep it as it is.
    If the string contains no letters, reverse the string.
    The function should return the resulted string.
    Examples
    solve("1234") = "4321"
    solve("ab") = "AB"
    solve("#a@C") = "#A@c"
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef solve(s):\n    """You are given a string s.\n    if s[i] is a letter, reverse its case from lower to upper or vise versa, \n    otherwise keep it as it is.\n    If the string contains no letters, reverse the string.\n    The function should return the resulted string.\n    Examples\n    solve("1234") = "4321"\n    solve("ab") = "AB"\n    solve("#a@C") = "#A@c"\n    """\n',
    "test_solution.py": 'from solution import solve\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("AsDf") == "aSdF"\n    assert candidate("1234") == "4321"\n    assert candidate("ab") == "AB"\n    assert candidate("#a@C") == "#A@c"\n    assert candidate("#AsdfW^45") == "#aSDFw^45"\n    assert candidate("#6@2") == "2@6#"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("#$a^D") == "#$A^d"\n    assert candidate("#ccc") == "#CCC"\n\n    # Don\'t remove this line:\n\n\ndef test_candidate():\n    check(solve)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import solve\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("AsDf") == "aSdF"\n    assert candidate("1234") == "4321"\n    assert candidate("ab") == "AB"\n    assert candidate("#a@C") == "#A@c"\n    assert candidate("#AsdfW^45") == "#aSDFw^45"\n    assert candidate("#6@2") == "2@6#"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("#$a^D") == "#$A^d"\n    assert candidate("#ccc") == "#CCC"\n\n    # Don\'t remove this line:\n\n\ndef test_candidate():\n    check(solve)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
