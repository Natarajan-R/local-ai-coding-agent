"""HumanEval task HumanEval_51"""
from pathlib import Path

TASK = """Implement the function 'remove_vowels' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def remove_vowels(text):
    \"\"\"
    remove_vowels is a function that takes string and returns string without vowels.
    >>> remove_vowels('')
    ''
    >>> remove_vowels("abcdef\nghijklm")
    'bcdf\nghjklm'
    >>> remove_vowels('abcdef')
    'bcdf'
    >>> remove_vowels('aaaaa')
    ''
    >>> remove_vowels('aaBAA')
    'B'
    >>> remove_vowels('zbcd')
    'zbcd'
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef remove_vowels(text):\n    """\n    remove_vowels is a function that takes string and returns string without vowels.\n    >>> remove_vowels(\'\')\n    \'\'\n    >>> remove_vowels("abcdef\\nghijklm")\n    \'bcdf\\nghjklm\'\n    >>> remove_vowels(\'abcdef\')\n    \'bcdf\'\n    >>> remove_vowels(\'aaaaa\')\n    \'\'\n    >>> remove_vowels(\'aaBAA\')\n    \'B\'\n    >>> remove_vowels(\'zbcd\')\n    \'zbcd\'\n    """\n',
    "test_solution.py": 'from solution import remove_vowels\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(\'\') == \'\'\n    assert candidate("abcdef\\nghijklm") == \'bcdf\\nghjklm\'\n    assert candidate(\'fedcba\') == \'fdcb\'\n    assert candidate(\'eeeee\') == \'\'\n    assert candidate(\'acBAA\') == \'cB\'\n    assert candidate(\'EcBOO\') == \'cB\'\n    assert candidate(\'ybcd\') == \'ybcd\'\n\n\n\ndef test_candidate():\n    check(remove_vowels)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import remove_vowels\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(\'\') == \'\'\n    assert candidate("abcdef\\nghijklm") == \'bcdf\\nghjklm\'\n    assert candidate(\'fedcba\') == \'fdcb\'\n    assert candidate(\'eeeee\') == \'\'\n    assert candidate(\'acBAA\') == \'cB\'\n    assert candidate(\'EcBOO\') == \'cB\'\n    assert candidate(\'ybcd\') == \'ybcd\'\n\n\n\ndef test_candidate():\n    check(remove_vowels)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
