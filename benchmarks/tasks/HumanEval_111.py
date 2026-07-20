"""HumanEval task HumanEval_111"""
from pathlib import Path

TASK = """Implement the function 'histogram' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def histogram(test):
    \"\"\"Given a string representing a space separated lowercase letters, return a dictionary
    of the letter with the most repetition and containing the corresponding count.
    If several letters have the same occurrence, return all of them.
    
    Example:
    histogram('a b c') == {'a': 1, 'b': 1, 'c': 1}
    histogram('a b b a') == {'a': 2, 'b': 2}
    histogram('a b c a b') == {'a': 2, 'b': 2}
    histogram('b b b b a') == {'b': 4}
    histogram('') == {}

    \"\"\"

"""

FILES = {
    "solution.py": '\ndef histogram(test):\n    """Given a string representing a space separated lowercase letters, return a dictionary\n    of the letter with the most repetition and containing the corresponding count.\n    If several letters have the same occurrence, return all of them.\n    \n    Example:\n    histogram(\'a b c\') == {\'a\': 1, \'b\': 1, \'c\': 1}\n    histogram(\'a b b a\') == {\'a\': 2, \'b\': 2}\n    histogram(\'a b c a b\') == {\'a\': 2, \'b\': 2}\n    histogram(\'b b b b a\') == {\'b\': 4}\n    histogram(\'\') == {}\n\n    """\n',
    "test_solution.py": 'from solution import histogram\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'a b b a\') == {\'a\':2,\'b\': 2}, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'a b c a b\') == {\'a\': 2, \'b\': 2}, "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(\'a b c d g\') == {\'a\': 1, \'b\': 1, \'c\': 1, \'d\': 1, \'g\': 1}, "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate(\'r t g\') == {\'r\': 1,\'t\': 1,\'g\': 1}, "This prints if this assert fails 4 (good for debugging!)"\n    assert candidate(\'b b b b a\') == {\'b\': 4}, "This prints if this assert fails 5 (good for debugging!)"\n    assert candidate(\'r t g\') == {\'r\': 1,\'t\': 1,\'g\': 1}, "This prints if this assert fails 6 (good for debugging!)"\n    \n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'\') == {}, "This prints if this assert fails 7 (also good for debugging!)"\n    assert candidate(\'a\') == {\'a\': 1}, "This prints if this assert fails 8 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(histogram)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import histogram\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(\'a b b a\') == {\'a\':2,\'b\': 2}, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(\'a b c a b\') == {\'a\': 2, \'b\': 2}, "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(\'a b c d g\') == {\'a\': 1, \'b\': 1, \'c\': 1, \'d\': 1, \'g\': 1}, "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate(\'r t g\') == {\'r\': 1,\'t\': 1,\'g\': 1}, "This prints if this assert fails 4 (good for debugging!)"\n    assert candidate(\'b b b b a\') == {\'b\': 4}, "This prints if this assert fails 5 (good for debugging!)"\n    assert candidate(\'r t g\') == {\'r\': 1,\'t\': 1,\'g\': 1}, "This prints if this assert fails 6 (good for debugging!)"\n    \n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'\') == {}, "This prints if this assert fails 7 (also good for debugging!)"\n    assert candidate(\'a\') == {\'a\': 1}, "This prints if this assert fails 8 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(histogram)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
