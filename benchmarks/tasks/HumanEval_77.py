"""HumanEval task HumanEval_77"""
from pathlib import Path

TASK = """Implement the function 'iscube' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def iscube(a):
    '''
    Write a function that takes an integer a and returns True 
    if this ingeger is a cube of some integer number.
    Note: you may assume the input is always valid.
    Examples:
    iscube(1) ==> True
    iscube(2) ==> False
    iscube(-1) ==> True
    iscube(64) ==> True
    iscube(0) ==> True
    iscube(180) ==> False
    '''

"""

FILES = {
    "solution.py": "\ndef iscube(a):\n    '''\n    Write a function that takes an integer a and returns True \n    if this ingeger is a cube of some integer number.\n    Note: you may assume the input is always valid.\n    Examples:\n    iscube(1) ==> True\n    iscube(2) ==> False\n    iscube(-1) ==> True\n    iscube(64) ==> True\n    iscube(0) ==> True\n    iscube(180) ==> False\n    '''\n",
    "test_solution.py": 'from solution import iscube\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(1) == True, "First test error: " + str(candidate(1))\n    assert candidate(2) == False, "Second test error: " + str(candidate(2))\n    assert candidate(-1) == True, "Third test error: " + str(candidate(-1))\n    assert candidate(64) == True, "Fourth test error: " + str(candidate(64))\n    assert candidate(180) == False, "Fifth test error: " + str(candidate(180))\n    assert candidate(1000) == True, "Sixth test error: " + str(candidate(1000))\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(0) == True, "1st edge test error: " + str(candidate(0))\n    assert candidate(1729) == False, "2nd edge test error: " + str(candidate(1728))\n\n\n\ndef test_candidate():\n    check(iscube)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import iscube\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(1) == True, "First test error: " + str(candidate(1))\n    assert candidate(2) == False, "Second test error: " + str(candidate(2))\n    assert candidate(-1) == True, "Third test error: " + str(candidate(-1))\n    assert candidate(64) == True, "Fourth test error: " + str(candidate(64))\n    assert candidate(180) == False, "Fifth test error: " + str(candidate(180))\n    assert candidate(1000) == True, "Sixth test error: " + str(candidate(1000))\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(0) == True, "1st edge test error: " + str(candidate(0))\n    assert candidate(1729) == False, "2nd edge test error: " + str(candidate(1728))\n\n\n\ndef test_candidate():\n    check(iscube)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
