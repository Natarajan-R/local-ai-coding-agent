"""HumanEval task HumanEval_14"""
from pathlib import Path

TASK = """Implement the function 'all_prefixes' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def all_prefixes(string: str) -> List[str]:
    \"\"\" Return list of all prefixes from shortest to longest of the input string
    >>> all_prefixes('abc')
    ['a', 'ab', 'abc']
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef all_prefixes(string: str) -> List[str]:\n    """ Return list of all prefixes from shortest to longest of the input string\n    >>> all_prefixes(\'abc\')\n    [\'a\', \'ab\', \'abc\']\n    """\n',
    "test_solution.py": "from solution import all_prefixes\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == []\n    assert candidate('asdfgh') == ['a', 'as', 'asd', 'asdf', 'asdfg', 'asdfgh']\n    assert candidate('WWW') == ['W', 'WW', 'WWW']\n\n\ndef test_candidate():\n    check(all_prefixes)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import all_prefixes\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == []\n    assert candidate('asdfgh') == ['a', 'as', 'asd', 'asdf', 'asdfg', 'asdfgh']\n    assert candidate('WWW') == ['W', 'WW', 'WWW']\n\n\ndef test_candidate():\n    check(all_prefixes)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
