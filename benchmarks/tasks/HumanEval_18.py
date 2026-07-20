"""HumanEval task HumanEval_18"""
from pathlib import Path

TASK = """Implement the function 'how_many_times' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def how_many_times(string: str, substring: str) -> int:
    \"\"\" Find how many times a given substring can be found in the original string. Count overlaping cases.
    >>> how_many_times('', 'a')
    0
    >>> how_many_times('aaa', 'a')
    3
    >>> how_many_times('aaaa', 'aa')
    3
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef how_many_times(string: str, substring: str) -> int:\n    """ Find how many times a given substring can be found in the original string. Count overlaping cases.\n    >>> how_many_times(\'\', \'a\')\n    0\n    >>> how_many_times(\'aaa\', \'a\')\n    3\n    >>> how_many_times(\'aaaa\', \'aa\')\n    3\n    """\n',
    "test_solution.py": "from solution import how_many_times\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('', 'x') == 0\n    assert candidate('xyxyxyx', 'x') == 4\n    assert candidate('cacacacac', 'cac') == 4\n    assert candidate('john doe', 'john') == 1\n\n\ndef test_candidate():\n    check(how_many_times)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import how_many_times\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('', 'x') == 0\n    assert candidate('xyxyxyx', 'x') == 4\n    assert candidate('cacacacac', 'cac') == 4\n    assert candidate('john doe', 'john') == 1\n\n\ndef test_candidate():\n    check(how_many_times)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
