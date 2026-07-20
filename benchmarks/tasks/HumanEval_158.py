"""HumanEval task HumanEval_158"""
from pathlib import Path

TASK = """Implement the function 'find_max' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def find_max(words):
    \"\"\"Write a function that accepts a list of strings.
    The list contains different words. Return the word with maximum number
    of unique characters. If multiple strings have maximum number of unique
    characters, return the one which comes first in lexicographical order.

    find_max(["name", "of", "string"]) == "string"
    find_max(["name", "enam", "game"]) == "enam"
    find_max(["aaaaaaa", "bb" ,"cc"]) == ""aaaaaaa"
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef find_max(words):\n    """Write a function that accepts a list of strings.\n    The list contains different words. Return the word with maximum number\n    of unique characters. If multiple strings have maximum number of unique\n    characters, return the one which comes first in lexicographical order.\n\n    find_max(["name", "of", "string"]) == "string"\n    find_max(["name", "enam", "game"]) == "enam"\n    find_max(["aaaaaaa", "bb" ,"cc"]) == ""aaaaaaa"\n    """\n',
    "test_solution.py": 'from solution import find_max\ndef check(candidate):\n\n    # Check some simple cases\n    assert (candidate(["name", "of", "string"]) == "string"), "t1"\n    assert (candidate(["name", "enam", "game"]) == "enam"), \'t2\'\n    assert (candidate(["aaaaaaa", "bb", "cc"]) == "aaaaaaa"), \'t3\'\n    assert (candidate(["abc", "cba"]) == "abc"), \'t4\'\n    assert (candidate(["play", "this", "game", "of","footbott"]) == "footbott"), \'t5\'\n    assert (candidate(["we", "are", "gonna", "rock"]) == "gonna"), \'t6\'\n    assert (candidate(["we", "are", "a", "mad", "nation"]) == "nation"), \'t7\'\n    assert (candidate(["this", "is", "a", "prrk"]) == "this"), \'t8\'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert (candidate(["b"]) == "b"), \'t9\'\n    assert (candidate(["play", "play", "play"]) == "play"), \'t10\'\n\n\n\ndef test_candidate():\n    check(find_max)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import find_max\ndef check(candidate):\n\n    # Check some simple cases\n    assert (candidate(["name", "of", "string"]) == "string"), "t1"\n    assert (candidate(["name", "enam", "game"]) == "enam"), \'t2\'\n    assert (candidate(["aaaaaaa", "bb", "cc"]) == "aaaaaaa"), \'t3\'\n    assert (candidate(["abc", "cba"]) == "abc"), \'t4\'\n    assert (candidate(["play", "this", "game", "of","footbott"]) == "footbott"), \'t5\'\n    assert (candidate(["we", "are", "gonna", "rock"]) == "gonna"), \'t6\'\n    assert (candidate(["we", "are", "a", "mad", "nation"]) == "nation"), \'t7\'\n    assert (candidate(["this", "is", "a", "prrk"]) == "this"), \'t8\'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert (candidate(["b"]) == "b"), \'t9\'\n    assert (candidate(["play", "play", "play"]) == "play"), \'t10\'\n\n\n\ndef test_candidate():\n    check(find_max)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
