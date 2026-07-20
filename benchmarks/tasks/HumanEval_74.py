"""HumanEval task HumanEval_74"""
from pathlib import Path

TASK = """Implement the function 'total_match' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def total_match(lst1, lst2):
    '''
    Write a function that accepts two lists of strings and returns the list that has 
    total number of chars in the all strings of the list less than the other list.

    if the two lists have the same number of chars, return the first list.

    Examples
    total_match([], []) ➞ []
    total_match(['hi', 'admin'], ['hI', 'Hi']) ➞ ['hI', 'Hi']
    total_match(['hi', 'admin'], ['hi', 'hi', 'admin', 'project']) ➞ ['hi', 'admin']
    total_match(['hi', 'admin'], ['hI', 'hi', 'hi']) ➞ ['hI', 'hi', 'hi']
    total_match(['4'], ['1', '2', '3', '4', '5']) ➞ ['4']
    '''

"""

FILES = {
    "solution.py": "\ndef total_match(lst1, lst2):\n    '''\n    Write a function that accepts two lists of strings and returns the list that has \n    total number of chars in the all strings of the list less than the other list.\n\n    if the two lists have the same number of chars, return the first list.\n\n    Examples\n    total_match([], []) ➞ []\n    total_match(['hi', 'admin'], ['hI', 'Hi']) ➞ ['hI', 'Hi']\n    total_match(['hi', 'admin'], ['hi', 'hi', 'admin', 'project']) ➞ ['hi', 'admin']\n    total_match(['hi', 'admin'], ['hI', 'hi', 'hi']) ➞ ['hI', 'hi', 'hi']\n    total_match(['4'], ['1', '2', '3', '4', '5']) ➞ ['4']\n    '''\n",
    "test_solution.py": 'from solution import total_match\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([], []) == []\n    assert candidate([\'hi\', \'admin\'], [\'hi\', \'hi\']) == [\'hi\', \'hi\']\n    assert candidate([\'hi\', \'admin\'], [\'hi\', \'hi\', \'admin\', \'project\']) == [\'hi\', \'admin\']\n    assert candidate([\'4\'], [\'1\', \'2\', \'3\', \'4\', \'5\']) == [\'4\']\n    assert candidate([\'hi\', \'admin\'], [\'hI\', \'Hi\']) == [\'hI\', \'Hi\']\n    assert candidate([\'hi\', \'admin\'], [\'hI\', \'hi\', \'hi\']) == [\'hI\', \'hi\', \'hi\']\n    assert candidate([\'hi\', \'admin\'], [\'hI\', \'hi\', \'hii\']) == [\'hi\', \'admin\']\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([], [\'this\']) == []\n    assert candidate([\'this\'], []) == []\n\n\n\ndef test_candidate():\n    check(total_match)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import total_match\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([], []) == []\n    assert candidate([\'hi\', \'admin\'], [\'hi\', \'hi\']) == [\'hi\', \'hi\']\n    assert candidate([\'hi\', \'admin\'], [\'hi\', \'hi\', \'admin\', \'project\']) == [\'hi\', \'admin\']\n    assert candidate([\'4\'], [\'1\', \'2\', \'3\', \'4\', \'5\']) == [\'4\']\n    assert candidate([\'hi\', \'admin\'], [\'hI\', \'Hi\']) == [\'hI\', \'Hi\']\n    assert candidate([\'hi\', \'admin\'], [\'hI\', \'hi\', \'hi\']) == [\'hI\', \'hi\', \'hi\']\n    assert candidate([\'hi\', \'admin\'], [\'hI\', \'hi\', \'hii\']) == [\'hi\', \'admin\']\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([], [\'this\']) == []\n    assert candidate([\'this\'], []) == []\n\n\n\ndef test_candidate():\n    check(total_match)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
