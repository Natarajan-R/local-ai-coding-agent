"""HumanEval task HumanEval_92"""
from pathlib import Path

TASK = """Implement the function 'any_int' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def any_int(x, y, z):
    '''
    Create a function that takes 3 numbers.
    Returns true if one of the numbers is equal to the sum of the other two, and all numbers are integers.
    Returns false in any other cases.
    
    Examples
    any_int(5, 2, 7) ➞ True
    
    any_int(3, 2, 2) ➞ False

    any_int(3, -2, 1) ➞ True
    
    any_int(3.6, -2.2, 2) ➞ False
  

    
    '''

"""

FILES = {
    "solution.py": "\ndef any_int(x, y, z):\n    '''\n    Create a function that takes 3 numbers.\n    Returns true if one of the numbers is equal to the sum of the other two, and all numbers are integers.\n    Returns false in any other cases.\n    \n    Examples\n    any_int(5, 2, 7) ➞ True\n    \n    any_int(3, 2, 2) ➞ False\n\n    any_int(3, -2, 1) ➞ True\n    \n    any_int(3.6, -2.2, 2) ➞ False\n  \n\n    \n    '''\n",
    "test_solution.py": 'from solution import any_int\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(2, 3, 1)==True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(2.5, 2, 3)==False, "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(1.5, 5, 3.5)==False, "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate(2, 6, 2)==False, "This prints if this assert fails 4 (good for debugging!)"\n    assert candidate(4, 2, 2)==True, "This prints if this assert fails 5 (good for debugging!)"\n    assert candidate(2.2, 2.2, 2.2)==False, "This prints if this assert fails 6 (good for debugging!)"\n    assert candidate(-4, 6, 2)==True, "This prints if this assert fails 7 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(2,1,1)==True, "This prints if this assert fails 8 (also good for debugging!)"\n    assert candidate(3,4,7)==True, "This prints if this assert fails 9 (also good for debugging!)"\n    assert candidate(3.0,4,7)==False, "This prints if this assert fails 10 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(any_int)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import any_int\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(2, 3, 1)==True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(2.5, 2, 3)==False, "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate(1.5, 5, 3.5)==False, "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate(2, 6, 2)==False, "This prints if this assert fails 4 (good for debugging!)"\n    assert candidate(4, 2, 2)==True, "This prints if this assert fails 5 (good for debugging!)"\n    assert candidate(2.2, 2.2, 2.2)==False, "This prints if this assert fails 6 (good for debugging!)"\n    assert candidate(-4, 6, 2)==True, "This prints if this assert fails 7 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(2,1,1)==True, "This prints if this assert fails 8 (also good for debugging!)"\n    assert candidate(3,4,7)==True, "This prints if this assert fails 9 (also good for debugging!)"\n    assert candidate(3.0,4,7)==False, "This prints if this assert fails 10 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(any_int)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
