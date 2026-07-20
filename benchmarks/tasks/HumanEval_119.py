"""HumanEval task HumanEval_119"""
from pathlib import Path

TASK = """Implement the function 'match_parens' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def match_parens(lst):
    '''
    You are given a list of two strings, both strings consist of open
    parentheses '(' or close parentheses ')' only.
    Your job is to check if it is possible to concatenate the two strings in
    some order, that the resulting string will be good.
    A string S is considered to be good if and only if all parentheses in S
    are balanced. For example: the string '(())()' is good, while the string
    '())' is not.
    Return 'Yes' if there's a way to make a good string, and return 'No' otherwise.

    Examples:
    match_parens(['()(', ')']) == 'Yes'
    match_parens([')', ')']) == 'No'
    '''

"""

FILES = {
    "solution.py": "\ndef match_parens(lst):\n    '''\n    You are given a list of two strings, both strings consist of open\n    parentheses '(' or close parentheses ')' only.\n    Your job is to check if it is possible to concatenate the two strings in\n    some order, that the resulting string will be good.\n    A string S is considered to be good if and only if all parentheses in S\n    are balanced. For example: the string '(())()' is good, while the string\n    '())' is not.\n    Return 'Yes' if there's a way to make a good string, and return 'No' otherwise.\n\n    Examples:\n    match_parens(['()(', ')']) == 'Yes'\n    match_parens([')', ')']) == 'No'\n    '''\n",
    "test_solution.py": "from solution import match_parens\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(['()(', ')']) == 'Yes'\n    assert candidate([')', ')']) == 'No'\n    assert candidate(['(()(())', '())())']) == 'No'\n    assert candidate([')())', '(()()(']) == 'Yes'\n    assert candidate(['(())))', '(()())((']) == 'Yes'\n    assert candidate(['()', '())']) == 'No'\n    assert candidate(['(()(', '()))()']) == 'Yes'\n    assert candidate(['((((', '((())']) == 'No'\n    assert candidate([')(()', '(()(']) == 'No'\n    assert candidate([')(', ')(']) == 'No'\n    \n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(['(', ')']) == 'Yes'\n    assert candidate([')', '(']) == 'Yes' \n\n\n\ndef test_candidate():\n    check(match_parens)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import match_parens\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(['()(', ')']) == 'Yes'\n    assert candidate([')', ')']) == 'No'\n    assert candidate(['(()(())', '())())']) == 'No'\n    assert candidate([')())', '(()()(']) == 'Yes'\n    assert candidate(['(())))', '(()())((']) == 'Yes'\n    assert candidate(['()', '())']) == 'No'\n    assert candidate(['(()(', '()))()']) == 'Yes'\n    assert candidate(['((((', '((())']) == 'No'\n    assert candidate([')(()', '(()(']) == 'No'\n    assert candidate([')(', ')(']) == 'No'\n    \n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(['(', ')']) == 'Yes'\n    assert candidate([')', '(']) == 'Yes' \n\n\n\ndef test_candidate():\n    check(match_parens)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
