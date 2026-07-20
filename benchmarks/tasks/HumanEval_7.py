"""HumanEval task HumanEval_7"""
from pathlib import Path

TASK = """Implement the function 'filter_by_substring' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def filter_by_substring(strings: List[str], substring: str) -> List[str]:
    \"\"\" Filter an input list of strings only for ones that contain given substring
    >>> filter_by_substring([], 'a')
    []
    >>> filter_by_substring(['abc', 'bacd', 'cde', 'array'], 'a')
    ['abc', 'bacd', 'array']
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef filter_by_substring(strings: List[str], substring: str) -> List[str]:\n    """ Filter an input list of strings only for ones that contain given substring\n    >>> filter_by_substring([], \'a\')\n    []\n    >>> filter_by_substring([\'abc\', \'bacd\', \'cde\', \'array\'], \'a\')\n    [\'abc\', \'bacd\', \'array\']\n    """\n',
    "test_solution.py": "from solution import filter_by_substring\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([], 'john') == []\n    assert candidate(['xxx', 'asd', 'xxy', 'john doe', 'xxxAAA', 'xxx'], 'xxx') == ['xxx', 'xxxAAA', 'xxx']\n    assert candidate(['xxx', 'asd', 'aaaxxy', 'john doe', 'xxxAAA', 'xxx'], 'xx') == ['xxx', 'aaaxxy', 'xxxAAA', 'xxx']\n    assert candidate(['grunt', 'trumpet', 'prune', 'gruesome'], 'run') == ['grunt', 'prune']\n\n\ndef test_candidate():\n    check(filter_by_substring)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import filter_by_substring\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([], 'john') == []\n    assert candidate(['xxx', 'asd', 'xxy', 'john doe', 'xxxAAA', 'xxx'], 'xxx') == ['xxx', 'xxxAAA', 'xxx']\n    assert candidate(['xxx', 'asd', 'aaaxxy', 'john doe', 'xxxAAA', 'xxx'], 'xx') == ['xxx', 'aaaxxy', 'xxxAAA', 'xxx']\n    assert candidate(['grunt', 'trumpet', 'prune', 'gruesome'], 'run') == ['grunt', 'prune']\n\n\ndef test_candidate():\n    check(filter_by_substring)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
