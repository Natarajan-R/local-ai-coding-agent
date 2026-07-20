"""HumanEval task HumanEval_156"""
from pathlib import Path

TASK = """Implement the function 'int_to_mini_roman' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def int_to_mini_roman(number):
    \"\"\"
    Given a positive integer, obtain its roman numeral equivalent as a string,
    and return it in lowercase.
    Restrictions: 1 <= num <= 1000

    Examples:
    >>> int_to_mini_roman(19) == 'xix'
    >>> int_to_mini_roman(152) == 'clii'
    >>> int_to_mini_roman(426) == 'cdxxvi'
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef int_to_mini_roman(number):\n    """\n    Given a positive integer, obtain its roman numeral equivalent as a string,\n    and return it in lowercase.\n    Restrictions: 1 <= num <= 1000\n\n    Examples:\n    >>> int_to_mini_roman(19) == \'xix\'\n    >>> int_to_mini_roman(152) == \'clii\'\n    >>> int_to_mini_roman(426) == \'cdxxvi\'\n    """\n',
    "test_solution.py": "from solution import int_to_mini_roman\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(19) == 'xix'\n    assert candidate(152) == 'clii'\n    assert candidate(251) == 'ccli'\n    assert candidate(426) == 'cdxxvi'\n    assert candidate(500) == 'd'\n    assert candidate(1) == 'i'\n    assert candidate(4) == 'iv'\n    assert candidate(43) == 'xliii'\n    assert candidate(90) == 'xc'\n    assert candidate(94) == 'xciv'\n    assert candidate(532) == 'dxxxii'\n    assert candidate(900) == 'cm'\n    assert candidate(994) == 'cmxciv'\n    assert candidate(1000) == 'm'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(int_to_mini_roman)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import int_to_mini_roman\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(19) == 'xix'\n    assert candidate(152) == 'clii'\n    assert candidate(251) == 'ccli'\n    assert candidate(426) == 'cdxxvi'\n    assert candidate(500) == 'd'\n    assert candidate(1) == 'i'\n    assert candidate(4) == 'iv'\n    assert candidate(43) == 'xliii'\n    assert candidate(90) == 'xc'\n    assert candidate(94) == 'xciv'\n    assert candidate(532) == 'dxxxii'\n    assert candidate(900) == 'cm'\n    assert candidate(994) == 'cmxciv'\n    assert candidate(1000) == 'm'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(int_to_mini_roman)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
