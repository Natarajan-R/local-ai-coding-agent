"""HumanEval task HumanEval_16"""
from pathlib import Path

TASK = """Implement the function 'count_distinct_characters' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def count_distinct_characters(string: str) -> int:
    \"\"\" Given a string, find out how many distinct characters (regardless of case) does it consist of
    >>> count_distinct_characters('xyzXYZ')
    3
    >>> count_distinct_characters('Jerry')
    4
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef count_distinct_characters(string: str) -> int:\n    """ Given a string, find out how many distinct characters (regardless of case) does it consist of\n    >>> count_distinct_characters(\'xyzXYZ\')\n    3\n    >>> count_distinct_characters(\'Jerry\')\n    4\n    """\n',
    "test_solution.py": "from solution import count_distinct_characters\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == 0\n    assert candidate('abcde') == 5\n    assert candidate('abcde' + 'cade' + 'CADE') == 5\n    assert candidate('aaaaAAAAaaaa') == 1\n    assert candidate('Jerry jERRY JeRRRY') == 5\n\n\ndef test_candidate():\n    check(count_distinct_characters)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import count_distinct_characters\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == 0\n    assert candidate('abcde') == 5\n    assert candidate('abcde' + 'cade' + 'CADE') == 5\n    assert candidate('aaaaAAAAaaaa') == 1\n    assert candidate('Jerry jERRY JeRRRY') == 5\n\n\ndef test_candidate():\n    check(count_distinct_characters)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
