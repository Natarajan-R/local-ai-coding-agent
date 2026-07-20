"""HumanEval task HumanEval_143"""
from pathlib import Path

TASK = """Implement the function 'words_in_sentence' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def words_in_sentence(sentence):
    \"\"\"
    You are given a string representing a sentence,
    the sentence contains some words separated by a space,
    and you have to return a string that contains the words from the original sentence,
    whose lengths are prime numbers,
    the order of the words in the new string should be the same as the original one.

    Example 1:
        Input: sentence = "This is a test"
        Output: "is"

    Example 2:
        Input: sentence = "lets go for swimming"
        Output: "go for"

    Constraints:
        * 1 <= len(sentence) <= 100
        * sentence contains only letters
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef words_in_sentence(sentence):\n    """\n    You are given a string representing a sentence,\n    the sentence contains some words separated by a space,\n    and you have to return a string that contains the words from the original sentence,\n    whose lengths are prime numbers,\n    the order of the words in the new string should be the same as the original one.\n\n    Example 1:\n        Input: sentence = "This is a test"\n        Output: "is"\n\n    Example 2:\n        Input: sentence = "lets go for swimming"\n        Output: "go for"\n\n    Constraints:\n        * 1 <= len(sentence) <= 100\n        * sentence contains only letters\n    """\n',
    "test_solution.py": 'from solution import words_in_sentence\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("This is a test") == "is"\n    assert candidate("lets go for swimming") == "go for"\n    assert candidate("there is no place available here") == "there is no place"\n    assert candidate("Hi I am Hussein") == "Hi am Hussein"\n    assert candidate("go for it") == "go for it"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("here") == ""\n    assert candidate("here is") == "is"\n\n\n\ndef test_candidate():\n    check(words_in_sentence)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import words_in_sentence\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("This is a test") == "is"\n    assert candidate("lets go for swimming") == "go for"\n    assert candidate("there is no place available here") == "there is no place"\n    assert candidate("Hi I am Hussein") == "Hi am Hussein"\n    assert candidate("go for it") == "go for it"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("here") == ""\n    assert candidate("here is") == "is"\n\n\n\ndef test_candidate():\n    check(words_in_sentence)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
