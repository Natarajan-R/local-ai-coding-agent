"""HumanEval task HumanEval_149"""
from pathlib import Path

TASK = """Implement the function 'sorted_list_sum' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def sorted_list_sum(lst):
    \"\"\"Write a function that accepts a list of strings as a parameter,
    deletes the strings that have odd lengths from it,
    and returns the resulted list with a sorted order,
    The list is always a list of strings and never an array of numbers,
    and it may contain duplicates.
    The order of the list should be ascending by length of each word, and you
    should return the list sorted by that rule.
    If two words have the same length, sort the list alphabetically.
    The function should return a list of strings in sorted order.
    You may assume that all words will have the same length.
    For example:
    assert list_sort(["aa", "a", "aaa"]) => ["aa"]
    assert list_sort(["ab", "a", "aaa", "cd"]) => ["ab", "cd"]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef sorted_list_sum(lst):\n    """Write a function that accepts a list of strings as a parameter,\n    deletes the strings that have odd lengths from it,\n    and returns the resulted list with a sorted order,\n    The list is always a list of strings and never an array of numbers,\n    and it may contain duplicates.\n    The order of the list should be ascending by length of each word, and you\n    should return the list sorted by that rule.\n    If two words have the same length, sort the list alphabetically.\n    The function should return a list of strings in sorted order.\n    You may assume that all words will have the same length.\n    For example:\n    assert list_sort(["aa", "a", "aaa"]) => ["aa"]\n    assert list_sort(["ab", "a", "aaa", "cd"]) => ["ab", "cd"]\n    """\n',
    "test_solution.py": 'from solution import sorted_list_sum\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(["aa", "a", "aaa"]) == ["aa"]\n    assert candidate(["school", "AI", "asdf", "b"]) == ["AI", "asdf", "school"]\n    assert candidate(["d", "b", "c", "a"]) == []\n    assert candidate(["d", "dcba", "abcd", "a"]) == ["abcd", "dcba"]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(["AI", "ai", "au"]) == ["AI", "ai", "au"]\n    assert candidate(["a", "b", "b", "c", "c", "a"]) == []\n    assert candidate([\'aaaa\', \'bbbb\', \'dd\', \'cc\']) == ["cc", "dd", "aaaa", "bbbb"]\n\n\n\ndef test_candidate():\n    check(sorted_list_sum)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import sorted_list_sum\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(["aa", "a", "aaa"]) == ["aa"]\n    assert candidate(["school", "AI", "asdf", "b"]) == ["AI", "asdf", "school"]\n    assert candidate(["d", "b", "c", "a"]) == []\n    assert candidate(["d", "dcba", "abcd", "a"]) == ["abcd", "dcba"]\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(["AI", "ai", "au"]) == ["AI", "ai", "au"]\n    assert candidate(["a", "b", "b", "c", "c", "a"]) == []\n    assert candidate([\'aaaa\', \'bbbb\', \'dd\', \'cc\']) == ["cc", "dd", "aaaa", "bbbb"]\n\n\n\ndef test_candidate():\n    check(sorted_list_sum)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
