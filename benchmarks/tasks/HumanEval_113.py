"""HumanEval task HumanEval_113"""
from pathlib import Path

TASK = """Implement the function 'odd_count' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def odd_count(lst):
    \"\"\"Given a list of strings, where each string consists of only digits, return a list.
    Each element i of the output should be "the number of odd elements in the
    string i of the input." where all the i's should be replaced by the number
    of odd digits in the i'th string of the input.

    >>> odd_count(['1234567'])
    ["the number of odd elements 4n the str4ng 4 of the 4nput."]
    >>> odd_count(['3',"11111111"])
    ["the number of odd elements 1n the str1ng 1 of the 1nput.",
     "the number of odd elements 8n the str8ng 8 of the 8nput."]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef odd_count(lst):\n    """Given a list of strings, where each string consists of only digits, return a list.\n    Each element i of the output should be "the number of odd elements in the\n    string i of the input." where all the i\'s should be replaced by the number\n    of odd digits in the i\'th string of the input.\n\n    >>> odd_count([\'1234567\'])\n    ["the number of odd elements 4n the str4ng 4 of the 4nput."]\n    >>> odd_count([\'3\',"11111111"])\n    ["the number of odd elements 1n the str1ng 1 of the 1nput.",\n     "the number of odd elements 8n the str8ng 8 of the 8nput."]\n    """\n',
    "test_solution.py": 'from solution import odd_count\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([\'1234567\']) == ["the number of odd elements 4n the str4ng 4 of the 4nput."], "Test 1"\n    assert candidate([\'3\',"11111111"]) == ["the number of odd elements 1n the str1ng 1 of the 1nput.", "the number of odd elements 8n the str8ng 8 of the 8nput."], "Test 2"\n    assert candidate([\'271\', \'137\', \'314\']) == [\n        \'the number of odd elements 2n the str2ng 2 of the 2nput.\',\n        \'the number of odd elements 3n the str3ng 3 of the 3nput.\',\n        \'the number of odd elements 2n the str2ng 2 of the 2nput.\'\n    ]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(odd_count)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import odd_count\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([\'1234567\']) == ["the number of odd elements 4n the str4ng 4 of the 4nput."], "Test 1"\n    assert candidate([\'3\',"11111111"]) == ["the number of odd elements 1n the str1ng 1 of the 1nput.", "the number of odd elements 8n the str8ng 8 of the 8nput."], "Test 2"\n    assert candidate([\'271\', \'137\', \'314\']) == [\n        \'the number of odd elements 2n the str2ng 2 of the 2nput.\',\n        \'the number of odd elements 3n the str3ng 3 of the 3nput.\',\n        \'the number of odd elements 2n the str2ng 2 of the 2nput.\'\n    ]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(odd_count)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
