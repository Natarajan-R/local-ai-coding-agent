"""HumanEval task HumanEval_28"""
from pathlib import Path

TASK = """Implement the function 'concatenate' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def concatenate(strings: List[str]) -> str:
    \"\"\" Concatenate list of strings into a single string
    >>> concatenate([])
    ''
    >>> concatenate(['a', 'b', 'c'])
    'abc'
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef concatenate(strings: List[str]) -> str:\n    """ Concatenate list of strings into a single string\n    >>> concatenate([])\n    \'\'\n    >>> concatenate([\'a\', \'b\', \'c\'])\n    \'abc\'\n    """\n',
    "test_solution.py": "from solution import concatenate\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == ''\n    assert candidate(['x', 'y', 'z']) == 'xyz'\n    assert candidate(['x', 'y', 'z', 'w', 'k']) == 'xyzwk'\n\n\ndef test_candidate():\n    check(concatenate)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import concatenate\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([]) == ''\n    assert candidate(['x', 'y', 'z']) == 'xyz'\n    assert candidate(['x', 'y', 'z', 'w', 'k']) == 'xyzwk'\n\n\ndef test_candidate():\n    check(concatenate)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
