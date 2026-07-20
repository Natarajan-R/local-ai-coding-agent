"""HumanEval task HumanEval_98"""
from pathlib import Path

TASK = """Implement the function 'count_upper' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def count_upper(s):
    \"\"\"
    Given a string s, count the number of uppercase vowels in even indices.
    
    For example:
    count_upper('aBCdEf') returns 1
    count_upper('abcdefg') returns 0
    count_upper('dBBE') returns 0
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef count_upper(s):\n    """\n    Given a string s, count the number of uppercase vowels in even indices.\n    \n    For example:\n    count_upper(\'aBCdEf\') returns 1\n    count_upper(\'abcdefg\') returns 0\n    count_upper(\'dBBE\') returns 0\n    """\n',
    "test_solution.py": "from solution import count_upper\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('aBCdEf')  == 1\n    assert candidate('abcdefg') == 0\n    assert candidate('dBBE') == 0\n    assert candidate('B')  == 0\n    assert candidate('U')  == 1\n    assert candidate('') == 0\n    assert candidate('EEEE') == 2\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(count_upper)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import count_upper\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('aBCdEf')  == 1\n    assert candidate('abcdefg') == 0\n    assert candidate('dBBE') == 0\n    assert candidate('B')  == 0\n    assert candidate('U')  == 1\n    assert candidate('') == 0\n    assert candidate('EEEE') == 2\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(count_upper)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
