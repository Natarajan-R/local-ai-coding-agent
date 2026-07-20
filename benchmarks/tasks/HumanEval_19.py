"""HumanEval task HumanEval_19"""
from pathlib import Path

TASK = """Implement the function 'sort_numbers' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def sort_numbers(numbers: str) -> str:
    \"\"\" Input is a space-delimited string of numberals from 'zero' to 'nine'.
    Valid choices are 'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight' and 'nine'.
    Return the string with numbers sorted from smallest to largest
    >>> sort_numbers('three one five')
    'one three five'
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef sort_numbers(numbers: str) -> str:\n    """ Input is a space-delimited string of numberals from \'zero\' to \'nine\'.\n    Valid choices are \'zero\', \'one\', \'two\', \'three\', \'four\', \'five\', \'six\', \'seven\', \'eight\' and \'nine\'.\n    Return the string with numbers sorted from smallest to largest\n    >>> sort_numbers(\'three one five\')\n    \'one three five\'\n    """\n',
    "test_solution.py": "from solution import sort_numbers\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == ''\n    assert candidate('three') == 'three'\n    assert candidate('three five nine') == 'three five nine'\n    assert candidate('five zero four seven nine eight') == 'zero four five seven eight nine'\n    assert candidate('six five four three two one zero') == 'zero one two three four five six'\n\n\ndef test_candidate():\n    check(sort_numbers)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import sort_numbers\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == ''\n    assert candidate('three') == 'three'\n    assert candidate('three five nine') == 'three five nine'\n    assert candidate('five zero four seven nine eight') == 'zero four five seven eight nine'\n    assert candidate('six five four three two one zero') == 'zero one two three four five six'\n\n\ndef test_candidate():\n    check(sort_numbers)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
