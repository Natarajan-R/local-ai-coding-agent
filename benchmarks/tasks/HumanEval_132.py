"""HumanEval task HumanEval_132"""
from pathlib import Path

TASK = """Implement the function 'is_nested' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def is_nested(string):
    '''
    Create a function that takes a string as input which contains only square brackets.
    The function should return True if and only if there is a valid subsequence of brackets 
    where at least one bracket in the subsequence is nested.

    is_nested('[[]]') ➞ True
    is_nested('[]]]]]]][[[[[]') ➞ False
    is_nested('[][]') ➞ False
    is_nested('[]') ➞ False
    is_nested('[[][]]') ➞ True
    is_nested('[[]][[') ➞ True
    '''

"""

FILES = {
    "solution.py": "\ndef is_nested(string):\n    '''\n    Create a function that takes a string as input which contains only square brackets.\n    The function should return True if and only if there is a valid subsequence of brackets \n    where at least one bracket in the subsequence is nested.\n\n    is_nested('[[]]') ➞ True\n    is_nested('[]]]]]]][[[[[]') ➞ False\n    is_nested('[][]') ➞ False\n    is_nested('[]') ➞ False\n    is_nested('[[][]]') ➞ True\n    is_nested('[[]][[') ➞ True\n    '''\n",
    "test_solution.py": 'from solution import is_nested\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'[[]]\') == True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'[]]]]]]][[[[[]\') == False\n    assert candidate(\'[][]\') == False\n    assert candidate((\'[]\')) == False\n    assert candidate(\'[[[[]]]]\') == True\n    assert candidate(\'[]]]]]]]]]]\') == False\n    assert candidate(\'[][][[]]\') == True\n    assert candidate(\'[[]\') == False\n    assert candidate(\'[]]\') == False\n    assert candidate(\'[[]][[\') == True\n    assert candidate(\'[[][]]\') == True\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'\') == False, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(\'[[[[[[[[\') == False\n    assert candidate(\']]]]]]]]\') == False\n\n\n\ndef test_candidate():\n    check(is_nested)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import is_nested\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'[[]]\') == True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'[]]]]]]][[[[[]\') == False\n    assert candidate(\'[][]\') == False\n    assert candidate((\'[]\')) == False\n    assert candidate(\'[[[[]]]]\') == True\n    assert candidate(\'[]]]]]]]]]]\') == False\n    assert candidate(\'[][][[]]\') == True\n    assert candidate(\'[[]\') == False\n    assert candidate(\'[]]\') == False\n    assert candidate(\'[[]][[\') == True\n    assert candidate(\'[[][]]\') == True\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'\') == False, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(\'[[[[[[[[\') == False\n    assert candidate(\']]]]]]]]\') == False\n\n\n\ndef test_candidate():\n    check(is_nested)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
