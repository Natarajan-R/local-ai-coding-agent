"""HumanEval task HumanEval_157"""
from pathlib import Path

TASK = """Implement the function 'right_angle_triangle' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def right_angle_triangle(a, b, c):
    '''
    Given the lengths of the three sides of a triangle. Return True if the three
    sides form a right-angled triangle, False otherwise.
    A right-angled triangle is a triangle in which one angle is right angle or 
    90 degree.
    Example:
    right_angle_triangle(3, 4, 5) == True
    right_angle_triangle(1, 2, 3) == False
    '''

"""

FILES = {
    "solution.py": "\ndef right_angle_triangle(a, b, c):\n    '''\n    Given the lengths of the three sides of a triangle. Return True if the three\n    sides form a right-angled triangle, False otherwise.\n    A right-angled triangle is a triangle in which one angle is right angle or \n    90 degree.\n    Example:\n    right_angle_triangle(3, 4, 5) == True\n    right_angle_triangle(1, 2, 3) == False\n    '''\n",
    "test_solution.py": 'from solution import right_angle_triangle\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(3, 4, 5) == True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1, 2, 3) == False\n    assert candidate(10, 6, 8) == True\n    assert candidate(2, 2, 2) == False\n    assert candidate(7, 24, 25) == True\n    assert candidate(10, 5, 7) == False\n    assert candidate(5, 12, 13) == True\n    assert candidate(15, 8, 17) == True\n    assert candidate(48, 55, 73) == True\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1, 1, 1) == False, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(2, 2, 10) == False\n\n\n\ndef test_candidate():\n    check(right_angle_triangle)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import right_angle_triangle\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(3, 4, 5) == True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1, 2, 3) == False\n    assert candidate(10, 6, 8) == True\n    assert candidate(2, 2, 2) == False\n    assert candidate(7, 24, 25) == True\n    assert candidate(10, 5, 7) == False\n    assert candidate(5, 12, 13) == True\n    assert candidate(15, 8, 17) == True\n    assert candidate(48, 55, 73) == True\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1, 1, 1) == False, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(2, 2, 10) == False\n\n\n\ndef test_candidate():\n    check(right_angle_triangle)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
