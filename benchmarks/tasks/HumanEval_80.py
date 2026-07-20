"""HumanEval task HumanEval_80"""
from pathlib import Path

TASK = """Implement the function 'is_happy' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def is_happy(s):
    \"\"\"You are given a string s.
    Your task is to check if the string is happy or not.
    A string is happy if its length is at least 3 and every 3 consecutive letters are distinct
    For example:
    is_happy(a) => False
    is_happy(aa) => False
    is_happy(abcd) => True
    is_happy(aabb) => False
    is_happy(adb) => True
    is_happy(xyy) => False
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef is_happy(s):\n    """You are given a string s.\n    Your task is to check if the string is happy or not.\n    A string is happy if its length is at least 3 and every 3 consecutive letters are distinct\n    For example:\n    is_happy(a) => False\n    is_happy(aa) => False\n    is_happy(abcd) => True\n    is_happy(aabb) => False\n    is_happy(adb) => True\n    is_happy(xyy) => False\n    """\n',
    "test_solution.py": 'from solution import is_happy\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("a") == False , "a"\n    assert candidate("aa") == False , "aa"\n    assert candidate("abcd") == True , "abcd"\n    assert candidate("aabb") == False , "aabb"\n    assert candidate("adb") == True , "adb"\n    assert candidate("xyy") == False , "xyy"\n    assert candidate("iopaxpoi") == True , "iopaxpoi"\n    assert candidate("iopaxioi") == False , "iopaxioi"\n\n\ndef test_candidate():\n    check(is_happy)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import is_happy\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("a") == False , "a"\n    assert candidate("aa") == False , "aa"\n    assert candidate("abcd") == True , "abcd"\n    assert candidate("aabb") == False , "aabb"\n    assert candidate("adb") == True , "adb"\n    assert candidate("xyy") == False , "xyy"\n    assert candidate("iopaxpoi") == True , "iopaxpoi"\n    assert candidate("iopaxioi") == False , "iopaxioi"\n\n\ndef test_candidate():\n    check(is_happy)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
