"""HumanEval task HumanEval_12"""
from pathlib import Path

TASK = """Implement the function 'longest' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List, Optional


def longest(strings: List[str]) -> Optional[str]:
    \"\"\" Out of list of strings, return the longest one. Return the first one in case of multiple
    strings of the same length. Return None in case the input list is empty.
    >>> longest([])

    >>> longest(['a', 'b', 'c'])
    'a'
    >>> longest(['a', 'bb', 'ccc'])
    'ccc'
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List, Optional\n\n\ndef longest(strings: List[str]) -> Optional[str]:\n    """ Out of list of strings, return the longest one. Return the first one in case of multiple\n    strings of the same length. Return None in case the input list is empty.\n    >>> longest([])\n\n    >>> longest([\'a\', \'b\', \'c\'])\n    \'a\'\n    >>> longest([\'a\', \'bb\', \'ccc\'])\n    \'ccc\'\n    """\n',
    "test_solution.py": "from solution import longest\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == None\n    assert candidate(['x', 'y', 'z']) == 'x'\n    assert candidate(['x', 'yyy', 'zzzz', 'www', 'kkkk', 'abc']) == 'zzzz'\n\n\ndef test_candidate():\n    check(longest)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import longest\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == None\n    assert candidate(['x', 'y', 'z']) == 'x'\n    assert candidate(['x', 'yyy', 'zzzz', 'www', 'kkkk', 'abc']) == 'zzzz'\n\n\ndef test_candidate():\n    check(longest)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
