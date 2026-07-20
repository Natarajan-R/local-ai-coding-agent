"""HumanEval task HumanEval_118"""
from pathlib import Path

TASK = """Implement the function 'get_closest_vowel' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def get_closest_vowel(word):
    \"\"\"You are given a word. Your task is to find the closest vowel that stands between 
    two consonants from the right side of the word (case sensitive).
    
    Vowels in the beginning and ending doesn't count. Return empty string if you didn't
    find any vowel met the above condition. 

    You may assume that the given string contains English letter only.

    Example:
    get_closest_vowel("yogurt") ==> "u"
    get_closest_vowel("FULL") ==> "U"
    get_closest_vowel("quick") ==> ""
    get_closest_vowel("ab") ==> ""
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef get_closest_vowel(word):\n    """You are given a word. Your task is to find the closest vowel that stands between \n    two consonants from the right side of the word (case sensitive).\n    \n    Vowels in the beginning and ending doesn\'t count. Return empty string if you didn\'t\n    find any vowel met the above condition. \n\n    You may assume that the given string contains English letter only.\n\n    Example:\n    get_closest_vowel("yogurt") ==> "u"\n    get_closest_vowel("FULL") ==> "U"\n    get_closest_vowel("quick") ==> ""\n    get_closest_vowel("ab") ==> ""\n    """\n',
    "test_solution.py": 'from solution import get_closest_vowel\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("yogurt") == "u"\n    assert candidate("full") == "u"\n    assert candidate("easy") == ""\n    assert candidate("eAsy") == ""\n    assert candidate("ali") == ""\n    assert candidate("bad") == "a"\n    assert candidate("most") == "o"\n    assert candidate("ab") == ""\n    assert candidate("ba") == ""\n    assert candidate("quick") == ""\n    assert candidate("anime") == "i"\n    assert candidate("Asia") == ""\n    assert candidate("Above") == "o"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(get_closest_vowel)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import get_closest_vowel\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("yogurt") == "u"\n    assert candidate("full") == "u"\n    assert candidate("easy") == ""\n    assert candidate("eAsy") == ""\n    assert candidate("ali") == ""\n    assert candidate("bad") == "a"\n    assert candidate("most") == "o"\n    assert candidate("ab") == ""\n    assert candidate("ba") == ""\n    assert candidate("quick") == ""\n    assert candidate("anime") == "i"\n    assert candidate("Asia") == ""\n    assert candidate("Above") == "o"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(get_closest_vowel)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
