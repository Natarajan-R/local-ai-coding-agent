"""HumanEval task HumanEval_66"""
from pathlib import Path

TASK = """Implement the function 'digitSum' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def digitSum(s):
    \"\"\"Task
    Write a function that takes a string as input and returns the sum of the upper characters only'
    ASCII codes.

    Examples:
        digitSum("") => 0
        digitSum("abAB") => 131
        digitSum("abcCd") => 67
        digitSum("helloE") => 69
        digitSum("woArBld") => 131
        digitSum("aAaaaXa") => 153
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef digitSum(s):\n    """Task\n    Write a function that takes a string as input and returns the sum of the upper characters only\'\n    ASCII codes.\n\n    Examples:\n        digitSum("") => 0\n        digitSum("abAB") => 131\n        digitSum("abcCd") => 67\n        digitSum("helloE") => 69\n        digitSum("woArBld") => 131\n        digitSum("aAaaaXa") => 153\n    """\n',
    "test_solution.py": 'from solution import digitSum\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate("") == 0, "Error"\n    assert candidate("abAB") == 131, "Error"\n    assert candidate("abcCd") == 67, "Error"\n    assert candidate("helloE") == 69, "Error"\n    assert candidate("woArBld") == 131, "Error"\n    assert candidate("aAaaaXa") == 153, "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(" How are yOu?") == 151, "Error"\n    assert candidate("You arE Very Smart") == 327, "Error"\n\n\n\ndef test_candidate():\n    check(digitSum)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import digitSum\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate("") == 0, "Error"\n    assert candidate("abAB") == 131, "Error"\n    assert candidate("abcCd") == 67, "Error"\n    assert candidate("helloE") == 69, "Error"\n    assert candidate("woArBld") == 131, "Error"\n    assert candidate("aAaaaXa") == 153, "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(" How are yOu?") == 151, "Error"\n    assert candidate("You arE Very Smart") == 327, "Error"\n\n\n\ndef test_candidate():\n    check(digitSum)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
