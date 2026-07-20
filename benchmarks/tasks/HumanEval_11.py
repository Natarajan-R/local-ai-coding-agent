"""HumanEval task HumanEval_11"""
from pathlib import Path

TASK = """Implement the function 'string_xor' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def string_xor(a: str, b: str) -> str:
    \"\"\" Input are two strings a and b consisting only of 1s and 0s.
    Perform binary XOR on these inputs and return result also as a string.
    >>> string_xor('010', '110')
    '100'
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef string_xor(a: str, b: str) -> str:\n    """ Input are two strings a and b consisting only of 1s and 0s.\n    Perform binary XOR on these inputs and return result also as a string.\n    >>> string_xor(\'010\', \'110\')\n    \'100\'\n    """\n',
    "test_solution.py": "from solution import string_xor\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('111000', '101010') == '010010'\n    assert candidate('1', '1') == '0'\n    assert candidate('0101', '0000') == '0101'\n\n\ndef test_candidate():\n    check(string_xor)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import string_xor\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('111000', '101010') == '010010'\n    assert candidate('1', '1') == '0'\n    assert candidate('0101', '0000') == '0101'\n\n\ndef test_candidate():\n    check(string_xor)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
