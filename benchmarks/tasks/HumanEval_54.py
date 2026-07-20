"""HumanEval task HumanEval_54"""
from pathlib import Path

TASK = """Implement the function 'same_chars' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def same_chars(s0: str, s1: str):
    \"\"\"
    Check if two words have the same characters.
    >>> same_chars('eabcdzzzz', 'dddzzzzzzzddeddabc')
    True
    >>> same_chars('abcd', 'dddddddabc')
    True
    >>> same_chars('dddddddabc', 'abcd')
    True
    >>> same_chars('eabcd', 'dddddddabc')
    False
    >>> same_chars('abcd', 'dddddddabce')
    False
    >>> same_chars('eabcdzzzz', 'dddzzzzzzzddddabc')
    False
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef same_chars(s0: str, s1: str):\n    """\n    Check if two words have the same characters.\n    >>> same_chars(\'eabcdzzzz\', \'dddzzzzzzzddeddabc\')\n    True\n    >>> same_chars(\'abcd\', \'dddddddabc\')\n    True\n    >>> same_chars(\'dddddddabc\', \'abcd\')\n    True\n    >>> same_chars(\'eabcd\', \'dddddddabc\')\n    False\n    >>> same_chars(\'abcd\', \'dddddddabce\')\n    False\n    >>> same_chars(\'eabcdzzzz\', \'dddzzzzzzzddddabc\')\n    False\n    """\n',
    "test_solution.py": "from solution import same_chars\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate('eabcdzzzz', 'dddzzzzzzzddeddabc') == True\n    assert candidate('abcd', 'dddddddabc') == True\n    assert candidate('dddddddabc', 'abcd') == True\n    assert candidate('eabcd', 'dddddddabc') == False\n    assert candidate('abcd', 'dddddddabcf') == False\n    assert candidate('eabcdzzzz', 'dddzzzzzzzddddabc') == False\n    assert candidate('aabb', 'aaccc') == False\n\n\n\ndef test_candidate():\n    check(same_chars)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import same_chars\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate('eabcdzzzz', 'dddzzzzzzzddeddabc') == True\n    assert candidate('abcd', 'dddddddabc') == True\n    assert candidate('dddddddabc', 'abcd') == True\n    assert candidate('eabcd', 'dddddddabc') == False\n    assert candidate('abcd', 'dddddddabcf') == False\n    assert candidate('eabcdzzzz', 'dddzzzzzzzddddabc') == False\n    assert candidate('aabb', 'aaccc') == False\n\n\n\ndef test_candidate():\n    check(same_chars)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
