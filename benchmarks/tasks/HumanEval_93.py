"""HumanEval task HumanEval_93"""
from pathlib import Path

TASK = """Implement the function 'encode' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def encode(message):
    \"\"\"
    Write a function that takes a message, and encodes in such a 
    way that it swaps case of all letters, replaces all vowels in 
    the message with the letter that appears 2 places ahead of that 
    vowel in the english alphabet. 
    Assume only letters. 
    
    Examples:
    >>> encode('test')
    'TGST'
    >>> encode('This is a message')
    'tHKS KS C MGSSCGG'
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef encode(message):\n    """\n    Write a function that takes a message, and encodes in such a \n    way that it swaps case of all letters, replaces all vowels in \n    the message with the letter that appears 2 places ahead of that \n    vowel in the english alphabet. \n    Assume only letters. \n    \n    Examples:\n    >>> encode(\'test\')\n    \'TGST\'\n    >>> encode(\'This is a message\')\n    \'tHKS KS C MGSSCGG\'\n    """\n',
    "test_solution.py": 'from solution import encode\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'TEST\') == \'tgst\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'Mudasir\') == \'mWDCSKR\', "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(\'YES\') == \'ygs\', "This prints if this assert fails 3 (good for debugging!)"\n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'This is a message\') == \'tHKS KS C MGSSCGG\', "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate("I DoNt KnOw WhAt tO WrItE") == \'k dQnT kNqW wHcT Tq wRkTg\', "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(encode)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import encode\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'TEST\') == \'tgst\', "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'Mudasir\') == \'mWDCSKR\', "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(\'YES\') == \'ygs\', "This prints if this assert fails 3 (good for debugging!)"\n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'This is a message\') == \'tHKS KS C MGSSCGG\', "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate("I DoNt KnOw WhAt tO WrItE") == \'k dQnT kNqW wHcT Tq wRkTg\', "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(encode)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
