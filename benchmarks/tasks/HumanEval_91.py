"""HumanEval task HumanEval_91"""
from pathlib import Path

TASK = """Implement the function 'is_bored' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def is_bored(S):
    \"\"\"
    You'll be given a string of words, and your task is to count the number
    of boredoms. A boredom is a sentence that starts with the word "I".
    Sentences are delimited by '.', '?' or '!'.
   
    For example:
    >>> is_bored("Hello world")
    0
    >>> is_bored("The sky is blue. The sun is shining. I love this weather")
    1
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef is_bored(S):\n    """\n    You\'ll be given a string of words, and your task is to count the number\n    of boredoms. A boredom is a sentence that starts with the word "I".\n    Sentences are delimited by \'.\', \'?\' or \'!\'.\n   \n    For example:\n    >>> is_bored("Hello world")\n    0\n    >>> is_bored("The sky is blue. The sun is shining. I love this weather")\n    1\n    """\n',
    "test_solution.py": 'from solution import is_bored\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Hello world") == 0, "Test 1"\n    assert candidate("Is the sky blue?") == 0, "Test 2"\n    assert candidate("I love It !") == 1, "Test 3"\n    assert candidate("bIt") == 0, "Test 4"\n    assert candidate("I feel good today. I will be productive. will kill It") == 2, "Test 5"\n    assert candidate("You and I are going for a walk") == 0, "Test 6"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(is_bored)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import is_bored\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Hello world") == 0, "Test 1"\n    assert candidate("Is the sky blue?") == 0, "Test 2"\n    assert candidate("I love It !") == 1, "Test 3"\n    assert candidate("bIt") == 0, "Test 4"\n    assert candidate("I feel good today. I will be productive. will kill It") == 2, "Test 5"\n    assert candidate("You and I are going for a walk") == 0, "Test 6"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(is_bored)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
