"""HumanEval task HumanEval_29"""
from pathlib import Path

TASK = """Implement the function 'filter_by_prefix' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def filter_by_prefix(strings: List[str], prefix: str) -> List[str]:
    \"\"\" Filter an input list of strings only for ones that start with a given prefix.
    >>> filter_by_prefix([], 'a')
    []
    >>> filter_by_prefix(['abc', 'bcd', 'cde', 'array'], 'a')
    ['abc', 'array']
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef filter_by_prefix(strings: List[str], prefix: str) -> List[str]:\n    """ Filter an input list of strings only for ones that start with a given prefix.\n    >>> filter_by_prefix([], \'a\')\n    []\n    >>> filter_by_prefix([\'abc\', \'bcd\', \'cde\', \'array\'], \'a\')\n    [\'abc\', \'array\']\n    """\n',
    "test_solution.py": "from solution import filter_by_prefix\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([], 'john') == []\n    assert candidate(['xxx', 'asd', 'xxy', 'john doe', 'xxxAAA', 'xxx'], 'xxx') == ['xxx', 'xxxAAA', 'xxx']\n\n\ndef test_candidate():\n    check(filter_by_prefix)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import filter_by_prefix\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([], 'john') == []\n    assert candidate(['xxx', 'asd', 'xxy', 'john doe', 'xxxAAA', 'xxx'], 'xxx') == ['xxx', 'xxxAAA', 'xxx']\n\n\ndef test_candidate():\n    check(filter_by_prefix)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
