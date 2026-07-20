"""HumanEval task HumanEval_82"""
from pathlib import Path

TASK = """Implement the function 'prime_length' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def prime_length(string):
    \"\"\"Write a function that takes a string and returns True if the string
    length is a prime number or False otherwise
    Examples
    prime_length('Hello') == True
    prime_length('abcdcba') == True
    prime_length('kittens') == True
    prime_length('orange') == False
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef prime_length(string):\n    """Write a function that takes a string and returns True if the string\n    length is a prime number or False otherwise\n    Examples\n    prime_length(\'Hello\') == True\n    prime_length(\'abcdcba\') == True\n    prime_length(\'kittens\') == True\n    prime_length(\'orange\') == False\n    """\n',
    "test_solution.py": "from solution import prime_length\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Hello') == True\n    assert candidate('abcdcba') == True\n    assert candidate('kittens') == True\n    assert candidate('orange') == False\n    assert candidate('wow') == True\n    assert candidate('world') == True\n    assert candidate('MadaM') == True\n    assert candidate('Wow') == True\n    assert candidate('') == False\n    assert candidate('HI') == True\n    assert candidate('go') == True\n    assert candidate('gogo') == False\n    assert candidate('aaaaaaaaaaaaaaa') == False\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate('Madam') == True\n    assert candidate('M') == False\n    assert candidate('0') == False\n\n\n\ndef test_candidate():\n    check(prime_length)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import prime_length\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Hello') == True\n    assert candidate('abcdcba') == True\n    assert candidate('kittens') == True\n    assert candidate('orange') == False\n    assert candidate('wow') == True\n    assert candidate('world') == True\n    assert candidate('MadaM') == True\n    assert candidate('Wow') == True\n    assert candidate('') == False\n    assert candidate('HI') == True\n    assert candidate('go') == True\n    assert candidate('gogo') == False\n    assert candidate('aaaaaaaaaaaaaaa') == False\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate('Madam') == True\n    assert candidate('M') == False\n    assert candidate('0') == False\n\n\n\ndef test_candidate():\n    check(prime_length)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
