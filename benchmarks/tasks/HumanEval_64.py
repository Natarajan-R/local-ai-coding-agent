"""HumanEval task HumanEval_64"""
from pathlib import Path

TASK = """Implement the function 'vowels_count' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

FIX = \"\"\"
Add more test cases.
\"\"\"

def vowels_count(s):
    \"\"\"Write a function vowels_count which takes a string representing
    a word as input and returns the number of vowels in the string.
    Vowels in this case are 'a', 'e', 'i', 'o', 'u'. Here, 'y' is also a
    vowel, but only when it is at the end of the given word.

    Example:
    >>> vowels_count("abcde")
    2
    >>> vowels_count("ACEDY")
    3
    \"\"\"

"""

FILES = {
    "solution.py": '\nFIX = """\nAdd more test cases.\n"""\n\ndef vowels_count(s):\n    """Write a function vowels_count which takes a string representing\n    a word as input and returns the number of vowels in the string.\n    Vowels in this case are \'a\', \'e\', \'i\', \'o\', \'u\'. Here, \'y\' is also a\n    vowel, but only when it is at the end of the given word.\n\n    Example:\n    >>> vowels_count("abcde")\n    2\n    >>> vowels_count("ACEDY")\n    3\n    """\n',
    "test_solution.py": 'from solution import vowels_count\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("abcde") == 2, "Test 1"\n    assert candidate("Alone") == 3, "Test 2"\n    assert candidate("key") == 2, "Test 3"\n    assert candidate("bye") == 1, "Test 4"\n    assert candidate("keY") == 2, "Test 5"\n    assert candidate("bYe") == 1, "Test 6"\n    assert candidate("ACEDY") == 3, "Test 7"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(vowels_count)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import vowels_count\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("abcde") == 2, "Test 1"\n    assert candidate("Alone") == 3, "Test 2"\n    assert candidate("key") == 2, "Test 3"\n    assert candidate("bye") == 1, "Test 4"\n    assert candidate("keY") == 2, "Test 5"\n    assert candidate("bYe") == 1, "Test 6"\n    assert candidate("ACEDY") == 3, "Test 7"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(vowels_count)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
