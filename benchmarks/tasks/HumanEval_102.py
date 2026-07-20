"""HumanEval task HumanEval_102"""
from pathlib import Path

TASK = """Implement the function 'choose_num' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def choose_num(x, y):
    \"\"\"This function takes two positive numbers x and y and returns the
    biggest even integer number that is in the range [x, y] inclusive. If 
    there's no such number, then the function should return -1.

    For example:
    choose_num(12, 15) = 14
    choose_num(13, 12) = -1
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef choose_num(x, y):\n    """This function takes two positive numbers x and y and returns the\n    biggest even integer number that is in the range [x, y] inclusive. If \n    there\'s no such number, then the function should return -1.\n\n    For example:\n    choose_num(12, 15) = 14\n    choose_num(13, 12) = -1\n    """\n',
    "test_solution.py": 'from solution import choose_num\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(12, 15) == 14\n    assert candidate(13, 12) == -1\n    assert candidate(33, 12354) == 12354\n    assert candidate(5234, 5233) == -1\n    assert candidate(6, 29) == 28\n    assert candidate(27, 10) == -1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(7, 7) == -1\n    assert candidate(546, 546) == 546\n\n\n\ndef test_candidate():\n    check(choose_num)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import choose_num\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(12, 15) == 14\n    assert candidate(13, 12) == -1\n    assert candidate(33, 12354) == 12354\n    assert candidate(5234, 5233) == -1\n    assert candidate(6, 29) == 28\n    assert candidate(27, 10) == -1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(7, 7) == -1\n    assert candidate(546, 546) == 546\n\n\n\ndef test_candidate():\n    check(choose_num)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
